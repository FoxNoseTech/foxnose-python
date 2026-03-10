from __future__ import annotations

import base64
import datetime as dt
import hashlib
from typing import Callable, Mapping
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from ..errors import FoxnoseAuthError
from .base import AuthStrategy, RequestData, ensure_bytes


Clock = Callable[[], dt.datetime]


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.timezone.utc)


class SecureKeyAuth(AuthStrategy):
    """
    Implements the ``Secure <public>:<signature>`` header used by both APIs.

    The signature uses ECDSA P-256 over ``<path>|<sha256(body)>|<timestamp>``.
    """

    def __init__(
        self,
        public_key: str,
        private_key: str,
        *,
        clock: Clock | None = None,
    ) -> None:
        if not public_key or not private_key:
            raise ValueError("public_key and private_key are required")
        self._public_key = public_key
        self._clock = clock or _utcnow
        try:
            private_bytes = base64.b64decode(private_key)
            self._private_key = serialization.load_der_private_key(
                private_bytes, password=None
            )
        except Exception as exc:  # pragma: no cover - cryptography provides details
            raise FoxnoseAuthError("Failed to load private key") from exc

    def build_headers(self, request: RequestData) -> Mapping[str, str]:
        body = ensure_bytes(request.body)
        timestamp = self._clock().astimezone(dt.timezone.utc).replace(microsecond=0)
        timestamp_str = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        parsed = urlparse(request.url)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        body_hash = hashlib.sha256(body).hexdigest()
        data_to_sign = f"{path}|{body_hash}|{timestamp_str}".encode("utf-8")
        signature = self._private_key.sign(data_to_sign, ec.ECDSA(hashes.SHA256()))
        signature_b64 = base64.b64encode(signature).decode("ascii")
        return {
            "Authorization": f"Secure {self._public_key}:{signature_b64}",
            "Date": timestamp_str,
        }


class SimpleKeyAuth(AuthStrategy):
    """Adds ``Authorization: Simple`` headers for development usage."""

    def __init__(self, public_key: str, secret_key: str) -> None:
        if not public_key or not secret_key:
            raise ValueError("public_key and secret_key are required")
        self._public_key = public_key
        self._secret_key = secret_key

    def build_headers(self, request: RequestData) -> Mapping[str, str]:  # noqa: D401
        del request
        return {"Authorization": f"Simple {self._public_key}:{self._secret_key}"}
