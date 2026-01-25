from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

import httpx


@dataclass
class PoolLimits:
    max_connections: int = 100
    max_keepalive: int = 20
    keepalive_expiry: float = 30.0

    def to_httpx_limits(self) -> httpx.Limits:
        return httpx.Limits(
            max_connections=self.max_connections,
            max_keepalive_connections=self.max_keepalive,
            keepalive_expiry=self.keepalive_expiry,
        )


@dataclass
class ProxyConfig:
    url: str
    auth: tuple[str, str] | None = None

    def to_httpx_proxy(self) -> str:
        if not self.auth:
            return self.url
        parsed = urlparse(self.url)
        netloc = f"{self.auth[0]}:{self.auth[1]}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
        return urlunparse(parsed._replace(netloc=netloc))
