from __future__ import annotations

import base64
import datetime as dt
import hashlib

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from foxnose_sdk.auth import JWTAuth, SecureKeyAuth, SimpleKeyAuth
from foxnose_sdk.auth.base import RequestData


def _generate_keys() -> tuple[str, str, ec.EllipticCurvePublicKey]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_der = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key = private_key.public_key()
    compressed = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.CompressedPoint,
    )
    return (
        base64.b64encode(compressed).decode("ascii"),
        base64.b64encode(private_der).decode("ascii"),
        public_key,
    )


def test_secure_auth_produces_verifiable_signature():
    public_key, private_key, public_obj = _generate_keys()
    fixed_time = dt.datetime(2024, 2, 20, 18, 0, 0, tzinfo=dt.timezone.utc)
    auth = SecureKeyAuth(public_key=public_key, private_key=private_key, clock=lambda: fixed_time)
    body = b'{"hello":"world"}'
    request = RequestData(
        method="POST",
        url="https://example.com/api/test?foo=bar",
        path="/api/test?foo=bar",
        body=body,
    )
    headers = auth.build_headers(request)

    assert headers["Date"] == "2024-02-20T18:00:00Z"
    assert headers["Authorization"].startswith(f"Secure {public_key}:")

    signature_b64 = headers["Authorization"].split(":", 1)[1]
    signature = base64.b64decode(signature_b64)
    body_hash = hashlib.sha256(body).hexdigest()
    expected = f"/api/test?foo=bar|{body_hash}|2024-02-20T18:00:00Z".encode("utf-8")
    public_obj.verify(signature, expected, ec.ECDSA(hashes.SHA256()))


def test_simple_key_auth_header():
    auth = SimpleKeyAuth("pub", "secret")
    headers = auth.build_headers(
        RequestData(method="GET", url="https://example.com", path="/", body=b"")
    )
    assert headers["Authorization"] == "Simple pub:secret"


def test_jwt_auth_raises_on_empty_token():
    auth = JWTAuth.from_static_token("token123")
    headers = auth.build_headers(
        RequestData(method="GET", url="https://example.com", path="/", body=b"")
    )
    assert headers["Authorization"] == "Bearer token123"
    with pytest.raises(ValueError):
        JWTAuth.from_static_token("").build_headers(
            RequestData(method="GET", url="https://example.com", path="/", body=b"")
        )
