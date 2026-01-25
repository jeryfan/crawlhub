import json
from dataclasses import dataclass, field, replace
from typing import Any


@dataclass(frozen=True)
class Request:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    timeout: float = 30.0

    def with_headers(self, **headers: str) -> "Request":
        return replace(self, headers={**self.headers, **headers})

    def with_timeout(self, timeout: float) -> "Request":
        return replace(self, timeout=timeout)

    def with_body(self, body: bytes) -> "Request":
        return replace(self, body=body)


@dataclass(frozen=True)
class Response:
    status_code: int
    headers: dict[str, str]
    body: bytes
    latency_ms: int
    request: Request

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    def json(self) -> Any:
        return json.loads(self.body)

    def text(self) -> str:
        return self.body.decode("utf-8")


@dataclass
class StreamChunk:
    data: bytes
    status_code: int | None = None
    headers: dict[str, str] | None = None

    @property
    def is_first(self) -> bool:
        return self.headers is not None
