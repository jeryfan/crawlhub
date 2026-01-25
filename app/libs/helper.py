import json
import secrets
import time
from typing import Any, Optional, Union, cast
import uuid
import logging
from zoneinfo import available_timezones
from fastapi import Request

from configs import app_config
from models.account import Account
from extensions.ext_redis import redis_client


logger = logging.getLogger(__name__)


def extract_remote_ip(request: Request) -> str:
    if request.headers.get("CF-Connecting-IP"):
        return cast(str, request.headers.get("CF-Connecting-IP"))
    elif request.headers.get("X-Forwarded-For"):
        return cast(str, request.headers.get("X-Forwarded-For"))
    else:
        return cast(str, request.client.host if request.client else "")


def generate_refresh_token(length: int = 64):
    token = secrets.token_hex(length)
    return token


def timezone(timezone_string):
    if timezone_string and timezone_string in available_timezones():
        return timezone_string

    error = f"{timezone_string} is not a valid timezone."
    raise ValueError(error)


def get_doc_type_by_extension(extension: str) -> str:
    extension = extension.lower()
    if extension in ["pdf"]:
        return "pdf"
    elif extension in ["doc", "docx"]:
        return "word"
    elif extension in ["xls", "xlsx"]:
        return "excel"
    elif extension in ["ppt", "pptx"]:
        return "ppt"
    elif extension in ["md", "markdown"]:
        return "markdown"
    elif extension in ["txt"]:
        return "text"
    elif extension in ["html", "htm"]:
        return "html"
    else:
        return "others"


class TokenManager:
    @classmethod
    def generate_token(
        cls,
        token_type: str,
        account: Optional["Account"] = None,
        email: str | None = None,
        additional_data: dict | None = None,
    ) -> str:
        if account is None and email is None:
            raise ValueError("Account or email must be provided")

        account_id = account.id if account else None
        account_email = account.email if account else email

        if account_id:
            old_token = cls._get_current_token_for_account(account_id, token_type)
            if old_token:
                if isinstance(old_token, bytes):
                    old_token = old_token.decode("utf-8")
                cls.revoke_token(old_token, token_type)

        token = str(uuid.uuid4())
        token_data = {
            "account_id": account_id,
            "email": account_email,
            "token_type": token_type,
        }
        if additional_data:
            token_data.update(additional_data)

        expiry_minutes = app_config.model_dump().get(f"{token_type.upper()}_TOKEN_EXPIRY_MINUTES")
        if expiry_minutes is None:
            raise ValueError(f"Expiry minutes for {token_type} token is not set")
        token_key = cls._get_token_key(token, token_type)
        expiry_seconds = int(expiry_minutes * 60)
        redis_client.setex(token_key, expiry_seconds, json.dumps(token_data))

        if account_id:
            cls._set_current_token_for_account(account_id, token, token_type, expiry_minutes)

        return token

    @classmethod
    def _get_token_key(cls, token: str, token_type: str) -> str:
        return f"{token_type}:token:{token}"

    @classmethod
    def revoke_token(cls, token: str, token_type: str):
        token_key = cls._get_token_key(token, token_type)
        redis_client.delete(token_key)

    @classmethod
    def get_token_data(cls, token: str, token_type: str) -> dict[str, Any] | None:
        key = cls._get_token_key(token, token_type)
        token_data_json = redis_client.get(key)
        if token_data_json is None:
            logger.warning("%s token %s not found with key %s", token_type, token, key)
            return None
        token_data: dict[str, Any] | None = json.loads(token_data_json)
        return token_data

    @classmethod
    def _get_current_token_for_account(cls, account_id: str, token_type: str) -> str | None:
        key = cls._get_account_token_key(account_id, token_type)
        current_token: str | None = redis_client.get(key)
        return current_token

    @classmethod
    def _set_current_token_for_account(
        cls,
        account_id: str,
        token: str,
        token_type: str,
        expiry_minutes: Union[int, float],
    ):
        key = cls._get_account_token_key(account_id, token_type)
        expiry_seconds = int(expiry_minutes * 60)
        redis_client.setex(key, expiry_seconds, token)

    @classmethod
    def _get_account_token_key(cls, account_id: str, token_type: str) -> str:
        return f"{token_type}:account:{account_id}"


class RateLimiter:
    def __init__(self, prefix: str, max_attempts: int, time_window: int):
        self.prefix = prefix
        self.max_attempts = max_attempts
        self.time_window = time_window

    def _get_key(self, identifier: str) -> str:
        return f"{self.prefix}:{identifier}"

    def is_rate_limited(self, identifier: str) -> bool:
        key = self._get_key(identifier)
        current_time = int(time.time())
        window_start_time = current_time - self.time_window

        redis_client.zremrangebyscore(key, "-inf", window_start_time)
        attempts = redis_client.zcard(key)

        if attempts and int(attempts) >= self.max_attempts:
            return True
        return False

    def increment_rate_limit(self, identifier: str):
        key = self._get_key(identifier)
        current_time = int(time.time())

        redis_client.zadd(key, {current_time: current_time})
        redis_client.expire(key, self.time_window * 2)

    def check_and_increment(self, identifier: str) -> tuple[bool, int]:
        """
        Check rate limit and increment counter atomically.
        Returns (is_limited, current_count).
        """
        key = self._get_key(identifier)
        current_time = int(time.time())

        try:
            redis_client.zremrangebyscore(key, "-inf", current_time - self.time_window)
            current_count = redis_client.zcard(key)

            if current_count and int(current_count) >= self.max_attempts:
                return True, int(current_count)

            redis_client.zadd(key, {f"{current_time}:{time.time_ns()}": current_time})
            redis_client.expire(key, self.time_window)

            return False, int(current_count) + 1
        except Exception as e:
            logger.warning(f"Redis rate limit check failed: {e}")
            return False, 0
