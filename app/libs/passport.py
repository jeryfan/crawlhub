from typing import Any

import jwt

from configs import app_config
from exceptions.common import (
    InvalidTokenError,
    InvalidTokenSignatureError,
    TokenExpiredError,
)


class PassportService:
    """JWT Token 服务

    提供 JWT Token 的签发和验证功能，用于用户身份认证
    """

    def __init__(self):
        self.sk = app_config.SECRET_KEY

    def issue(self, payload: dict[str, Any]) -> str:
        """签发 JWT Token

        Args:
            payload: Token 载荷，包含用户信息和过期时间等

        Returns:
            str: 编码后的 JWT Token 字符串
        """
        return jwt.encode(payload, self.sk, algorithm="HS256")

    def verify(self, token) -> dict[str, Any]:
        """验证并解码 JWT Token

        Args:
            token: 待验证的 JWT Token 字符串

        Returns:
            Dict[str, Any]: 解码后的 Token 载荷

        Raises:
            HTTPException: Token 过期、签名无效或格式错误时抛出 401 异常
        """
        try:
            return jwt.decode(token, self.sk, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError()
        except jwt.InvalidSignatureError:
            raise InvalidTokenSignatureError()
        except jwt.DecodeError:
            raise InvalidTokenError()
        except jwt.PyJWTError:
            raise InvalidTokenError()
