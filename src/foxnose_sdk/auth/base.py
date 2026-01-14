from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from ..errors import FoxnoseAuthError


@dataclass(frozen=True, slots=True)
class RequestData:
    """Immutable view of the outbound request used when applying auth."""

    method: str
    url: str
    path: str
    body: bytes


class AuthStrategy(Protocol):
    """Protocol implemented by every authentication strategy."""

    def build_headers(self, request: RequestData) -> Mapping[str, str]:
        """Return headers that should be merged into the request."""


class AnonymousAuth:
    """Placeholder auth strategy when no credentials are required."""

    def build_headers(self, request: RequestData) -> Mapping[str, str]:  # noqa: D401
        return {}


def ensure_bytes(payload: bytes | bytearray | memoryview | None) -> bytes:
    """Normalize payloads so authentication code always sees bytes."""
    if payload is None:
        return b""
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, bytearray):
        return bytes(payload)
    if isinstance(payload, memoryview):
        return payload.tobytes()
    raise FoxnoseAuthError("Unsupported payload type for signing")
