import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, DefaultFieldsMixin


class ProxyStatus(str, enum.Enum):
    """代理状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    COOLDOWN = "cooldown"


class ProxyProtocol(str, enum.Enum):
    """代理协议"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


class Proxy(DefaultFieldsMixin, Base):
    """代理配置"""

    __tablename__ = "crawlhub_proxies"

    host: Mapped[str] = mapped_column(String(255), nullable=False, comment="主机地址")
    port: Mapped[int] = mapped_column(Integer, nullable=False, comment="端口")
    protocol: Mapped[ProxyProtocol] = mapped_column(
        Enum(ProxyProtocol), default=ProxyProtocol.HTTP, comment="协议"
    )
    username: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="用户名")
    password: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="密码")
    status: Mapped[ProxyStatus] = mapped_column(
        Enum(ProxyStatus), default=ProxyStatus.ACTIVE, comment="状态"
    )
    last_check_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="最后检测时间"
    )
    success_rate: Mapped[float] = mapped_column(Float, default=1.0, comment="成功率")
    fail_count: Mapped[int] = mapped_column(Integer, default=0, comment="连续失败次数")

    @property
    def url(self) -> str:
        """获取代理 URL"""
        if self.username and self.password:
            return f"{self.protocol.value}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol.value}://{self.host}:{self.port}"

    def __repr__(self) -> str:
        return f"<Proxy {self.host}:{self.port}>"
