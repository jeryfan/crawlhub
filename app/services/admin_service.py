import base64
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from configs import app_config
from constants.languages import language_timezone_mapping
from exceptions.common import (
    AccountBannedError,
    AccountForbiddenError,
    AccountNotFoundError,
    InvalidCredentialsError,
)
from extensions.ext_redis import redis_client, redis_fallback
from libs.datetime_utils import naive_utc_now
from libs.helper import RateLimiter, TokenManager
from libs.passport import PassportService
from libs.password import compare_password, hash_password, valid_password
from libs.token import _generate_token, generate_csrf_token
from models.account import (
    AccountStatus,
)
from models.admin import Admin, AdminStatus
from schemas.auth import TokenPair
from services.base_service import BaseService

logger = logging.getLogger(__name__)

REFRESH_TOKEN_PREFIX = "refresh_token:"
ACCOUNT_REFRESH_TOKEN_PREFIX = "account_refresh_token:"
REFRESH_TOKEN_EXPIRY = timedelta(days=app_config.REFRESH_TOKEN_EXPIRE_DAYS)


class AdminService(BaseService):
    reset_password_rate_limiter = RateLimiter(
        prefix="reset_password_rate_limit", max_attempts=1, time_window=60 * 1
    )
    email_register_rate_limiter = RateLimiter(
        prefix="email_register_rate_limit", max_attempts=1, time_window=60 * 1
    )
    email_code_login_rate_limiter = RateLimiter(
        prefix="email_code_login_rate_limit", max_attempts=3, time_window=300 * 1
    )
    email_code_account_deletion_rate_limiter = RateLimiter(
        prefix="email_code_account_deletion_rate_limit",
        max_attempts=1,
        time_window=60 * 1,
    )
    change_email_rate_limiter = RateLimiter(
        prefix="change_email_rate_limit", max_attempts=1, time_window=60 * 1
    )
    LOGIN_MAX_ERROR_LIMITS: int = 5

    owner_transfer_rate_limiter = RateLimiter(
        prefix="owner_transfer_rate_limit", max_attempts=1, time_window=60 * 1
    )

    FORGOT_PASSWORD_MAX_ERROR_LIMITS = 5
    CHANGE_EMAIL_MAX_ERROR_LIMITS = 5
    OWNER_TRANSFER_MAX_ERROR_LIMITS = 5
    EMAIL_REGISTER_MAX_ERROR_LIMITS = 5

    @staticmethod
    def _get_refresh_token_key(refresh_token: str) -> str:
        return f"{REFRESH_TOKEN_PREFIX}{refresh_token}"

    @staticmethod
    def _get_account_refresh_token_key(account_id: str) -> str:
        return f"{ACCOUNT_REFRESH_TOKEN_PREFIX}{account_id}"

    @staticmethod
    async def _store_refresh_token(refresh_token: str, account_id: str):
        redis_client.setex(
            AdminService._get_refresh_token_key(refresh_token),
            REFRESH_TOKEN_EXPIRY,
            account_id,
        )

        redis_client.setex(
            AdminService._get_account_refresh_token_key(account_id),
            REFRESH_TOKEN_EXPIRY,
            refresh_token,
        )

    @staticmethod
    def _delete_refresh_token(refresh_token: str, account_id: str):
        redis_client.delete(AdminService._get_refresh_token_key(refresh_token))
        redis_client.delete(AdminService._get_account_refresh_token_key(account_id))

    async def load_admin(self, user_id: str) -> None | Admin:
        account = await self.db.get(Admin, user_id)
        if not account:
            return None

        if account.status == AdminStatus.BANNED:
            raise AccountBannedError()

        if naive_utc_now() - account.last_active_at > timedelta(minutes=10):
            account.last_active_at = naive_utc_now()
            await self.db.commit()

        await self.db.refresh(account)
        return account

    @staticmethod
    def get_account_jwt_token(account: Admin) -> str:
        exp_dt = datetime.now(UTC) + timedelta(minutes=app_config.ACCESS_TOKEN_EXPIRE_MINUTES)
        exp = int(exp_dt.timestamp())
        payload = {
            "user_id": account.id,
            "exp": exp,
        }

        token: str = PassportService().issue(payload)
        return token

    async def authenticate(self, email: str, password: str | None = None):
        account = await self.db.scalar(select(Admin).where(Admin.email == email).limit(1))
        if not account:
            raise AccountNotFoundError()

        if account.status == AccountStatus.BANNED:
            raise AccountBannedError()

        if password:
            # set password and password_salt
            salt = secrets.token_bytes(16)
            base64_salt = base64.b64encode(salt).decode()
            password_hashed = hash_password(password, salt)
            base64_password_hashed = base64.b64encode(password_hashed).decode()
            account.password = base64_password_hashed
            account.password_salt = base64_salt

        if account.password is None or not compare_password(
            password, account.password, account.password_salt
        ):
            raise InvalidCredentialsError()

        if account.status == AccountStatus.PENDING:
            account.status = AccountStatus.ACTIVE
            account.initialized_at = naive_utc_now()

        await self.db.commit()

        return account

    async def update_account_password(self, account, password, new_password):
        """update account password"""
        if account.password and not compare_password(
            password, account.password, account.password_salt
        ):
            raise InvalidCredentialsError()

        # may be raised
        valid_password(new_password)

        # generate password salt
        salt = secrets.token_bytes(16)
        base64_salt = base64.b64encode(salt).decode()

        # encrypt password with salt
        password_hashed = hash_password(new_password, salt)
        base64_password_hashed = base64.b64encode(password_hashed).decode()
        account.password = base64_password_hashed
        account.password_salt = base64_salt
        self.db.add(account)
        await self.db.commit()
        return account

    async def create_account(
        self,
        email: str,
        name: str,
        interface_language: str,
        password: str | None = None,
    ) -> Admin:
        """create account"""

        password_to_set = None
        salt_to_set = None
        if password:
            valid_password(password)

            # generate password salt
            salt = secrets.token_bytes(16)
            base64_salt = base64.b64encode(salt).decode()

            # encrypt password with salt
            password_hashed = hash_password(password, salt)
            base64_password_hashed = base64.b64encode(password_hashed).decode()

            password_to_set = base64_password_hashed
            salt_to_set = base64_salt

        account = Admin(
            email=email,
            name=name,
            password=password_to_set,
            password_salt=salt_to_set,
            timezone=language_timezone_mapping.get(interface_language, "UTC"),
        )

        self.db.add(account)
        await self.db.commit()
        return account

    @staticmethod
    def delete_account(account: Admin):
        """Delete account. This method only adds a task to the queue for deletion."""
        pass

    async def close_account(self, account: Admin):
        """Close account"""
        account.status = AdminStatus.BANNED
        await self.db.commit()

    async def update_account(self, account, **kwargs):
        """Update account fields"""
        account = await self.db.merge(account)
        for field, value in kwargs.items():
            if hasattr(account, field):
                setattr(account, field, value)
            else:
                raise AttributeError(f"Invalid field: {field}")

        await self.db.commit()
        return account

    async def update_login_info(self, account: Admin, *, ip_address: str):
        """Update last login time and ip"""
        account.last_login_at = naive_utc_now()
        account.last_login_ip = ip_address
        self.db.add(account)
        await self.db.commit()

    async def login(self, account: Admin, *, ip_address: str | None = None) -> TokenPair:
        if ip_address:
            await self.update_login_info(account=account, ip_address=ip_address)

        if account.status == AccountStatus.PENDING:
            account.status = AccountStatus.ACTIVE
            await self.db.commit()

        access_token = AdminService.get_account_jwt_token(account=account)
        refresh_token = _generate_token()
        csrf_token = generate_csrf_token(account.id)

        await self._store_refresh_token(refresh_token, account.id)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            csrf_token=csrf_token,
        )

    @staticmethod
    def logout(*, account: Admin):
        refresh_token = redis_client.get(AdminService._get_account_refresh_token_key(account.id))
        if refresh_token:
            AdminService._delete_refresh_token(refresh_token.decode("utf-8"), account.id)

    async def refresh_token(self, refresh_token: str) -> TokenPair:
        # Verify the refresh token
        account_id = redis_client.get(AdminService._get_refresh_token_key(refresh_token))
        if not account_id:
            raise ValueError("Invalid refresh token")

        account = await self.load_admin(account_id.decode("utf-8"))
        if not account:
            raise ValueError("Invalid account")

        # Generate new access token and refresh token
        new_access_token = AdminService.get_account_jwt_token(account)
        new_refresh_token = _generate_token()

        AdminService._delete_refresh_token(refresh_token, account.id)
        await self._store_refresh_token(new_refresh_token, account.id)
        csrf_token = generate_csrf_token(account.id)

        return TokenPair(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            csrf_token=csrf_token,
        )

    async def load_logged_in_account(self, *, account_id: str):
        return self.load_admin(account_id)

    @classmethod
    def revoke_reset_password_token(cls, token: str):
        TokenManager.revoke_token(token, "reset_password")

    @classmethod
    def revoke_email_register_token(cls, token: str):
        TokenManager.revoke_token(token, "email_register")

    @classmethod
    def revoke_change_email_token(cls, token: str):
        TokenManager.revoke_token(token, "change_email")

    @classmethod
    def revoke_owner_transfer_token(cls, token: str):
        TokenManager.revoke_token(token, "owner_transfer")

    @classmethod
    def get_reset_password_data(cls, token: str) -> dict[str, Any] | None:
        return TokenManager.get_token_data(token, "reset_password")

    @classmethod
    def get_email_register_data(cls, token: str) -> dict[str, Any] | None:
        return TokenManager.get_token_data(token, "email_register")

    @classmethod
    def get_change_email_data(cls, token: str) -> dict[str, Any] | None:
        return TokenManager.get_token_data(token, "change_email")

    @classmethod
    def is_account_in_freeze(cls, email: str) -> bool:
        # if app_config.BILLING_ENABLED and BillingService.is_email_in_freeze(email):
        #     return True
        return False

    @staticmethod
    @redis_fallback(default_return=None)
    def add_login_error_rate_limit(email: str):
        key = f"login_error_rate_limit:{email}"
        count = redis_client.get(key)
        if count is None:
            count = 0
        count = int(count) + 1
        redis_client.setex(key, app_config.LOGIN_LOCKOUT_DURATION, count)

    @staticmethod
    @redis_fallback(default_return=False)
    def is_login_error_rate_limit(email: str) -> bool:
        key = f"login_error_rate_limit:{email}"
        count = redis_client.get(key)
        if count is None:
            return False

        count = int(count)
        if count > AdminService.LOGIN_MAX_ERROR_LIMITS:
            return True
        return False

    @staticmethod
    @redis_fallback(default_return=None)
    def reset_login_error_rate_limit(email: str):
        key = f"login_error_rate_limit:{email}"
        redis_client.delete(key)

    @staticmethod
    @redis_fallback(default_return=None)
    def add_forgot_password_error_rate_limit(email: str):
        key = f"forgot_password_error_rate_limit:{email}"
        count = redis_client.get(key)
        if count is None:
            count = 0
        count = int(count) + 1
        redis_client.setex(key, app_config.FORGOT_PASSWORD_LOCKOUT_DURATION, count)

    @staticmethod
    @redis_fallback(default_return=False)
    def is_forgot_password_error_rate_limit(email: str) -> bool:
        key = f"forgot_password_error_rate_limit:{email}"
        count = redis_client.get(key)
        if count is None:
            return False

        count = int(count)
        if count > AdminService.FORGOT_PASSWORD_MAX_ERROR_LIMITS:
            return True
        return False

    @staticmethod
    @redis_fallback(default_return=None)
    def reset_forgot_password_error_rate_limit(email: str):
        key = f"forgot_password_error_rate_limit:{email}"
        redis_client.delete(key)

    @staticmethod
    @redis_fallback(default_return=None)
    def add_owner_transfer_error_rate_limit(email: str):
        key = f"owner_transfer_error_rate_limit:{email}"
        count = redis_client.get(key)
        if count is None:
            count = 0
        count = int(count) + 1
        redis_client.setex(key, app_config.OWNER_TRANSFER_LOCKOUT_DURATION, count)

    @staticmethod
    @redis_fallback(default_return=False)
    def is_owner_transfer_error_rate_limit(email: str) -> bool:
        key = f"owner_transfer_error_rate_limit:{email}"
        count = redis_client.get(key)
        if count is None:
            return False
        count = int(count)
        if count > AdminService.OWNER_TRANSFER_MAX_ERROR_LIMITS:
            return True
        return False

    @staticmethod
    @redis_fallback(default_return=None)
    def reset_owner_transfer_error_rate_limit(email: str):
        key = f"owner_transfer_error_rate_limit:{email}"
        redis_client.delete(key)

    async def get_user_through_email(self, email: str) -> Admin | None:
        account = await self.db.scalar(select(Admin).where(Admin.email == email).limit(1))
        if not account:
            return None

        if account.status == AccountStatus.BANNED:
            raise AccountForbiddenError()

        return account
