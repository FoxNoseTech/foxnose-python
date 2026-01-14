from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from foxnose_sdk.auth import SimpleKeyAuth
from foxnose_sdk.config import FoxnoseConfig, RetryConfig
from foxnose_sdk.errors import FoxnoseAPIError, FoxnoseTransportError
from foxnose_sdk.http import HttpTransport


def _mock_response(json_data: Any, status_code: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=status_code, json=json_data)

    return httpx.MockTransport(handler)


def test_transport_sends_headers_and_parses_json():
    auth = SimpleKeyAuth("pub", "secret")
    received = {}

    def handler(request: httpx.Request) -> httpx.Response:
        received["auth"] = request.headers["Authorization"]
        assert request.method == "GET"
        assert request.url.path == "/v1/test"
        return httpx.Response(200, json={"ok": True})

    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        sync_client=httpx.Client(base_url="https://api.example.com", transport=httpx.MockTransport(handler)),
    )

    data = transport.request("GET", "/v1/test")
    assert data == {"ok": True}
    assert received["auth"] == "Simple pub:secret"


def test_transport_retries_and_succeeds():
    auth = SimpleKeyAuth("pub", "secret")
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(500, json={"message": "try again"})
        return httpx.Response(200, json={"ok": True})

    retry = RetryConfig(attempts=2, backoff_factor=0)
    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        retry_config=retry,
        sync_client=httpx.Client(base_url="https://api.example.com", transport=httpx.MockTransport(handler)),
    )
    data = transport.request("GET", "/v1/test")
    assert data == {"ok": True}
    assert attempts["count"] == 2


def test_transport_raises_api_error():
    auth = SimpleKeyAuth("pub", "secret")
    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        sync_client=httpx.Client(
            base_url="https://api.example.com",
            transport=_mock_response({"message": "nope", "error_code": "oops"}, status_code=404),
        ),
    )
    with pytest.raises(FoxnoseAPIError) as exc:
        transport.request("GET", "/v1/test")
    assert exc.value.status_code == 404
    assert exc.value.error_code == "oops"


@pytest.mark.asyncio
async def test_async_transport_request():
    auth = SimpleKeyAuth("pub", "secret")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"async": True})

    mock = httpx.MockTransport(handler)
    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        async_client=httpx.AsyncClient(base_url="https://api.example.com", transport=mock),
    )
    data = await transport.arequest("GET", "/v1/test")
    assert data == {"async": True}


def test_transport_raises_on_transport_error():
    auth = SimpleKeyAuth("pub", "secret")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TransportError("boom")

    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        retry_config=RetryConfig(attempts=1),
        sync_client=httpx.Client(base_url="https://api.example.com", transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(FoxnoseTransportError):
        transport.request("GET", "/v1/test")
