from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class FoxnoseError(Exception):
    """Base class for all SDK errors."""


@dataclass
class FoxnoseAPIError(FoxnoseError):
    """Raised when the API responds with an error status."""

    message: str
    status_code: int
    error_code: str | None = None
    detail: Any | None = None
    response_headers: Mapping[str, str] | None = None
    response_body: Any | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        code = f", error_code={self.error_code}" if self.error_code else ""
        return f"{self.message} (status={self.status_code}{code})"


class FoxnoseAuthError(FoxnoseError):
    """Raised when authentication headers cannot be generated."""


class FoxnoseTransportError(FoxnoseError):
    """Raised when the HTTP layer fails before receiving a response."""
