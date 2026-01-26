from __future__ import annotations

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
        sync_client=httpx.Client(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
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
        sync_client=httpx.Client(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
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
            transport=_mock_response(
                {"message": "nope", "error_code": "oops"}, status_code=404
            ),
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
        async_client=httpx.AsyncClient(
            base_url="https://api.example.com", transport=mock
        ),
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
        sync_client=httpx.Client(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    with pytest.raises(FoxnoseTransportError):
        transport.request("GET", "/v1/test")


def test_transport_retries_on_transport_error_then_succeeds():
    """Test that transport errors trigger retry and can succeed on subsequent attempt."""
    auth = SimpleKeyAuth("pub", "secret")
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise httpx.TransportError("temporary failure")
        return httpx.Response(200, json={"recovered": True})

    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        retry_config=RetryConfig(attempts=3, backoff_factor=0),
        sync_client=httpx.Client(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    data = transport.request("GET", "/v1/test")
    assert data == {"recovered": True}
    assert attempts["count"] == 2


def test_transport_respects_retry_after_header():
    """Test that Retry-After header is respected for delay calculation."""
    auth = SimpleKeyAuth("pub", "secret")
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(
                503,
                json={"message": "overloaded"},
                headers={"Retry-After": "0"},
            )
        return httpx.Response(200, json={"ok": True})

    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        retry_config=RetryConfig(attempts=2, backoff_factor=0),
        sync_client=httpx.Client(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    data = transport.request("GET", "/v1/test")
    assert data == {"ok": True}
    assert attempts["count"] == 2


def test_transport_does_not_retry_post_by_default():
    """POST requests should not be retried by default (not in retry methods)."""
    auth = SimpleKeyAuth("pub", "secret")
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return httpx.Response(500, json={"message": "error"})

    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        retry_config=RetryConfig(attempts=3, backoff_factor=0),
        sync_client=httpx.Client(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    with pytest.raises(FoxnoseAPIError):
        transport.request("POST", "/v1/test", json_body={"data": "test"})
    assert attempts["count"] == 1


def test_transport_uses_default_headers():
    """Test that default headers from config are included in requests."""
    auth = SimpleKeyAuth("pub", "secret")
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        return httpx.Response(200, json={"ok": True})

    transport = HttpTransport(
        config=FoxnoseConfig(
            base_url="https://api.example.com",
            default_headers={"X-Custom-Header": "custom-value"},
        ),
        auth=auth,
        sync_client=httpx.Client(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    transport.request("GET", "/v1/test")
    assert captured["headers"]["x-custom-header"] == "custom-value"


def test_transport_request_headers_override_defaults():
    """Test that per-request headers override default headers."""
    auth = SimpleKeyAuth("pub", "secret")
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        return httpx.Response(200, json={"ok": True})

    transport = HttpTransport(
        config=FoxnoseConfig(
            base_url="https://api.example.com",
            default_headers={"X-Custom": "default"},
        ),
        auth=auth,
        sync_client=httpx.Client(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    transport.request("GET", "/v1/test", headers={"X-Custom": "override"})
    assert captured["headers"]["x-custom"] == "override"


def test_transport_handles_empty_response():
    """Test that empty response body returns None when parsing JSON."""
    auth = SimpleKeyAuth("pub", "secret")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, content=b"")

    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        sync_client=httpx.Client(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    result = transport.request("DELETE", "/v1/test")
    assert result is None


def test_transport_returns_text_on_json_decode_error():
    """Test that non-JSON response returns text instead of raising."""
    auth = SimpleKeyAuth("pub", "secret")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"plain text response")

    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        sync_client=httpx.Client(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    result = transport.request("GET", "/v1/test")
    assert result == "plain text response"


def test_transport_api_error_with_non_json_body():
    """Test API error handling when response body is not valid JSON."""
    auth = SimpleKeyAuth("pub", "secret")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=b"Internal Server Error")

    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        sync_client=httpx.Client(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    with pytest.raises(FoxnoseAPIError) as exc:
        transport.request("GET", "/v1/test")
    assert exc.value.status_code == 500
    assert exc.value.response_body == "Internal Server Error"


def test_transport_close_owned_client():
    """Test that close() properly closes client when transport owns it."""
    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
    )
    assert transport._owns_client is True
    transport.close()


@pytest.mark.asyncio
async def test_async_transport_aclose_owned_client():
    """Test that aclose() properly closes async client when transport owns it."""
    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
    )
    assert transport._owns_async_client is True
    await transport.aclose()


@pytest.mark.asyncio
async def test_async_transport_retries_and_succeeds():
    """Test async retry loop with successful recovery."""
    auth = SimpleKeyAuth("pub", "secret")
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(500, json={"message": "try again"})
        return httpx.Response(200, json={"async_ok": True})

    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        retry_config=RetryConfig(attempts=2, backoff_factor=0),
        async_client=httpx.AsyncClient(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    data = await transport.arequest("GET", "/v1/test")
    assert data == {"async_ok": True}
    assert attempts["count"] == 2


@pytest.mark.asyncio
async def test_async_transport_raises_api_error():
    """Test that async transport raises FoxnoseAPIError on HTTP errors."""
    auth = SimpleKeyAuth("pub", "secret")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403, json={"message": "forbidden", "error_code": "auth_failed"}
        )

    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        async_client=httpx.AsyncClient(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    with pytest.raises(FoxnoseAPIError) as exc:
        await transport.arequest("GET", "/v1/test")
    assert exc.value.status_code == 403
    assert exc.value.error_code == "auth_failed"


@pytest.mark.asyncio
async def test_async_transport_retries_on_transport_error():
    """Test async retry on transport errors."""
    auth = SimpleKeyAuth("pub", "secret")
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise httpx.TransportError("network error")
        return httpx.Response(200, json={"recovered": True})

    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        retry_config=RetryConfig(attempts=3, backoff_factor=0),
        async_client=httpx.AsyncClient(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    data = await transport.arequest("GET", "/v1/test")
    assert data == {"recovered": True}
    assert attempts["count"] == 2


@pytest.mark.asyncio
async def test_async_transport_exceeds_retry_attempts():
    """Test that async transport raises after exhausting retry attempts."""
    auth = SimpleKeyAuth("pub", "secret")
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return httpx.Response(500, json={"message": "always fail"})

    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        retry_config=RetryConfig(attempts=3, backoff_factor=0),
        async_client=httpx.AsyncClient(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    with pytest.raises(FoxnoseAPIError):
        await transport.arequest("GET", "/v1/test")
    assert attempts["count"] == 3


@pytest.mark.asyncio
async def test_async_transport_respects_retry_after():
    """Test that async transport respects Retry-After header."""
    auth = SimpleKeyAuth("pub", "secret")
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(
                429,
                json={"message": "rate limited"},
                headers={"Retry-After": "0"},
            )
        return httpx.Response(200, json={"ok": True})

    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        retry_config=RetryConfig(attempts=2, backoff_factor=0),
        async_client=httpx.AsyncClient(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    data = await transport.arequest("GET", "/v1/test")
    assert data == {"ok": True}


def test_transport_exceeds_retry_on_transport_error():
    """Test that transport raises FoxnoseTransportError after exhausting retries on network errors."""
    auth = SimpleKeyAuth("pub", "secret")
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        raise httpx.TransportError("persistent network failure")

    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        retry_config=RetryConfig(attempts=3, backoff_factor=0),
        sync_client=httpx.Client(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    with pytest.raises(FoxnoseTransportError):
        transport.request("GET", "/v1/test")
    assert attempts["count"] == 3


@pytest.mark.asyncio
async def test_async_transport_exceeds_retry_on_transport_error():
    """Test async transport raises FoxnoseTransportError after exhausting retries."""
    auth = SimpleKeyAuth("pub", "secret")
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        raise httpx.TransportError("persistent network failure")

    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        retry_config=RetryConfig(attempts=3, backoff_factor=0),
        async_client=httpx.AsyncClient(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    with pytest.raises(FoxnoseTransportError):
        await transport.arequest("GET", "/v1/test")
    assert attempts["count"] == 3


def test_transport_parse_json_false_returns_response():
    """Test that parse_json=False returns raw response object."""
    auth = SimpleKeyAuth("pub", "secret")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": "test"})

    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        sync_client=httpx.Client(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    result = transport.request("GET", "/v1/test", parse_json=False)
    assert isinstance(result, httpx.Response)
    assert result.status_code == 200


def test_transport_handles_invalid_retry_after_header():
    """Test that invalid (non-numeric) Retry-After header is handled gracefully."""
    auth = SimpleKeyAuth("pub", "secret")
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(
                503,
                json={"message": "overloaded"},
                headers={"Retry-After": "invalid-not-a-number"},
            )
        return httpx.Response(200, json={"ok": True})

    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        retry_config=RetryConfig(attempts=2, backoff_factor=0),
        sync_client=httpx.Client(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    data = transport.request("GET", "/v1/test")
    assert data == {"ok": True}
    assert attempts["count"] == 2


@pytest.mark.asyncio
async def test_async_transport_handles_invalid_retry_after_header():
    """Test that invalid Retry-After header is handled in async transport."""
    auth = SimpleKeyAuth("pub", "secret")
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(
                429,
                json={"message": "rate limited"},
                headers={"Retry-After": "Wed, 21 Oct 2025 07:28:00 GMT"},
            )
        return httpx.Response(200, json={"ok": True})

    transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=auth,
        retry_config=RetryConfig(attempts=2, backoff_factor=0),
        async_client=httpx.AsyncClient(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    data = await transport.arequest("GET", "/v1/test")
    assert data == {"ok": True}
