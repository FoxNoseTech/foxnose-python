from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .base import AuthStrategy, RequestData


class TokenProvider(Protocol):
    """Provides access tokens for JWT auth."""

    def get_token(self) -> str:
        """Return the latest access token string."""


@dataclass
class StaticTokenProvider:
    """Simple token provider that always returns the same token."""

    token: str

    def get_token(self) -> str:
        return self.token


class JWTAuth(AuthStrategy):
    """Adds ``Authorization: Bearer`` headers using a token provider."""

    def __init__(self, provider: TokenProvider, *, scheme: str = "Bearer") -> None:
        self._provider = provider
        self._scheme = scheme

    def build_headers(self, request: RequestData) -> dict[str, str]:
        del request  # unused but kept for a consistent signature
        token = self._provider.get_token()
        if not token:
            raise ValueError("Token provider returned an empty token")
        return {"Authorization": f"{self._scheme} {token}"}

    @classmethod
    def from_static_token(cls, token: str, *, scheme: str = "Bearer") -> "JWTAuth":
        """Convenience constructor for scripts with manual token management."""
        return cls(StaticTokenProvider(token=token), scheme=scheme)
