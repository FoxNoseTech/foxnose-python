from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, MutableMapping


@dataclass
class RetryConfig:
    """
    Controls HTTP retry behavior for idempotent requests.

    Attributes:
        attempts: Total number of attempts (original request + retries).
        backoff_factor: Multiplier for exponential backoff delays.
        status_codes: Response statuses that should be retried.
        methods: HTTP methods that are eligible for retrying.
    """

    attempts: int = 3
    backoff_factor: float = 0.5
    status_codes: tuple[int, ...] = (408, 425, 429, 500, 502, 503, 504)
    methods: tuple[str, ...] = ("GET", "HEAD", "OPTIONS", "PUT", "DELETE")

    def as_dict(self) -> MutableMapping[str, object]:
        """Expose the configuration as a mutable mapping for debugging."""
        return {
            "attempts": self.attempts,
            "backoff_factor": self.backoff_factor,
            "status_codes": self.status_codes,
            "methods": self.methods,
        }


DEFAULT_USER_AGENT = "foxnose-sdk/0.1.0"


@dataclass
class FoxnoseConfig:
    """
    General transport-level configuration shared by all clients.

    Attributes:
        base_url: Root URL (including scheme) for the API.
        timeout: Request timeout in seconds.
        default_headers: Headers applied to every request (lower priority than per-call headers).
        user_agent: User agent string reported to the API.
    """

    base_url: str
    timeout: float = 30.0
    default_headers: Mapping[str, str] | None = None
    user_agent: str = field(default_factory=lambda: DEFAULT_USER_AGENT)

    def __post_init__(self) -> None:
        if not self.base_url:
            raise ValueError("base_url must be provided")
        # Avoid accidental double slashes when joining paths.
        self.base_url = self.base_url.rstrip("/")
