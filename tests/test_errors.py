from __future__ import annotations

from typing import Any

import httpx
import pytest

from foxnose_sdk.auth import SimpleKeyAuth
from foxnose_sdk.config import FoxnoseConfig, RetryConfig
from foxnose_sdk.errors import (
    FoxnoseAPIError,
    PlanExhausted,
    PlanLimitExceeded,
    RateLimitExceeded,
    SpendCapExceeded,
    _header_lookup,
)
from foxnose_sdk.http import HttpTransport


def _transport(
    handler,
    *,
    retry_config: RetryConfig | None = None,
) -> HttpTransport:
    return HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=SimpleKeyAuth("pub", "secret"),
        retry_config=retry_config,
        sync_client=httpx.Client(
            base_url="https://api.example.com",
            transport=httpx.MockTransport(handler),
        ),
    )


def _async_transport(
    handler,
    *,
    retry_config: RetryConfig | None = None,
) -> HttpTransport:
    return HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=SimpleKeyAuth("pub", "secret"),
        retry_config=retry_config,
        async_client=httpx.AsyncClient(
            base_url="https://api.example.com",
            transport=httpx.MockTransport(handler),
        ),
    )


def test_402_spend_cap_reached_maps_to_spend_cap_exceeded():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            402,
            json={
                "error_code": "spend_cap_reached",
                "cap_usd": 100.0,
                "cycle_resets_at": "2026-08-01T00:00:00Z",
                "raise_cap_url": "https://app.example.com/billing",
            },
        )

    transport = _transport(handler)
    with pytest.raises(SpendCapExceeded) as exc:
        transport.request("GET", "/v1/test")
    err = exc.value
    assert isinstance(err, FoxnoseAPIError)
    assert err.status_code == 402
    assert err.error_code == "spend_cap_reached"
    assert err.cap_usd == 100.0
    assert err.cycle_resets_at == "2026-08-01T00:00:00Z"
    assert err.raise_cap_url == "https://app.example.com/billing"
    # Body has no top-level message; a default is supplied.
    assert err.message == "Spend cap reached"


def test_402_spend_cap_null_cap_usd():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            402,
            json={
                "error_code": "spend_cap_reached",
                "cap_usd": None,
                "cycle_resets_at": "2026-08-01T00:00:00Z",
                "raise_cap_url": "https://app.example.com/billing",
            },
        )

    transport = _transport(handler)
    with pytest.raises(SpendCapExceeded) as exc:
        transport.request("GET", "/v1/test")
    assert exc.value.cap_usd is None


def test_402_plan_exhausted_maps_to_plan_exhausted():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            402,
            json={
                "error_code": "plan_exhausted",
                "axis": "retrievals",
                "window_resets_at": "2026-08-01T00:00:00Z",
                "upgrade_url": "https://app.example.com/upgrade",
            },
        )

    transport = _transport(handler)
    with pytest.raises(PlanExhausted) as exc:
        transport.request("GET", "/v1/test")
    err = exc.value
    assert isinstance(err, FoxnoseAPIError)
    assert err.axis == "retrievals"
    assert err.window_resets_at == "2026-08-01T00:00:00Z"
    assert err.upgrade_url == "https://app.example.com/upgrade"
    assert err.message == "Plan allowance exhausted"


def test_402_is_not_retried():
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return httpx.Response(
            402,
            json={
                "error_code": "plan_exhausted",
                "axis": "writes",
                "window_resets_at": "2026-08-01T00:00:00Z",
                "upgrade_url": "https://app.example.com/upgrade",
            },
        )

    transport = _transport(handler, retry_config=RetryConfig(attempts=3, backoff_factor=0))
    with pytest.raises(PlanExhausted):
        transport.request("GET", "/v1/test")
    assert attempts["count"] == 1


def test_403_plan_limit_exceeded_with_upgrade_url():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "message": "Plan limit exceeded",
                "error_code": "plan_limit_exceeded",
                "detail": {
                    "entity": "collections",
                    "current": 10,
                    "limit": 10,
                    "upgrade_url": "https://app.example.com/upgrade",
                },
            },
        )

    transport = _transport(handler)
    with pytest.raises(PlanLimitExceeded) as exc:
        transport.request("GET", "/v1/test")
    err = exc.value
    assert isinstance(err, FoxnoseAPIError)
    assert err.entity == "collections"
    assert err.current == 10
    assert err.limit == 10
    assert err.upgrade_url == "https://app.example.com/upgrade"
    assert err.message == "Plan limit exceeded"


def test_403_plan_limit_exceeded_without_upgrade_url():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "message": "Plan limit exceeded",
                "error_code": "plan_limit_exceeded",
                "detail": {
                    "entity": "projects",
                    "current": 3,
                    "limit": 3,
                },
            },
        )

    transport = _transport(handler)
    with pytest.raises(PlanLimitExceeded) as exc:
        transport.request("GET", "/v1/test")
    err = exc.value
    assert err.entity == "projects"
    assert err.current == 3
    assert err.limit == 3
    assert err.upgrade_url is None


def test_429_rate_limited_on_post_not_retried():
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return httpx.Response(
            429,
            json={"error_code": "rate_limited", "message": "Rate limit exceeded"},
            headers={"Retry-After": "42"},
        )

    transport = _transport(handler, retry_config=RetryConfig(attempts=3, backoff_factor=0))
    with pytest.raises(RateLimitExceeded) as exc:
        transport.request("POST", "/v1/test", json_body={"data": "x"})
    err = exc.value
    assert isinstance(err, FoxnoseAPIError)
    # POST is not a retryable method: raised on the first attempt.
    assert attempts["count"] == 1
    # Retry-After parsed case-insensitively from a real httpx response header.
    assert err.retry_after == 42.0


def test_429_rate_limited_on_get_retried_then_raises():
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return httpx.Response(
            429,
            json={"error_code": "rate_limited", "message": "Rate limit exceeded"},
            headers={"Retry-After": "0"},
        )

    transport = _transport(handler, retry_config=RetryConfig(attempts=3, backoff_factor=0))
    with pytest.raises(RateLimitExceeded):
        transport.request("GET", "/v1/test")
    assert attempts["count"] == 3


def test_429_rate_limited_malformed_retry_after():
    """A non-numeric Retry-After header parses to retry_after=None, not an error."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"error_code": "rate_limited", "message": "Rate limit exceeded"},
            headers={"Retry-After": "not-a-number"},
        )

    transport = _transport(handler, retry_config=RetryConfig(attempts=1, backoff_factor=0))
    with pytest.raises(RateLimitExceeded) as exc:
        transport.request("POST", "/v1/test", json_body={"data": "x"})
    assert exc.value.retry_after is None


def test_header_lookup_edge_cases():
    # No headers at all.
    assert _header_lookup(None, "Retry-After") is None
    assert _header_lookup({}, "Retry-After") is None
    # Present headers but the target is absent.
    assert _header_lookup({"Content-Type": "application/json"}, "Retry-After") is None
    # Case-insensitive match.
    assert _header_lookup({"retry-after": "5"}, "Retry-After") == "5"


def test_429_unknown_code_stays_generic():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"error_code": "insufficient_units", "message": "No units left"},
        )

    transport = _transport(handler, retry_config=RetryConfig(attempts=1, backoff_factor=0))
    with pytest.raises(FoxnoseAPIError) as exc:
        transport.request("GET", "/v1/test")
    assert type(exc.value) is FoxnoseAPIError
    assert exc.value.error_code == "insufficient_units"


def test_402_unknown_code_stays_generic():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            402,
            json={"error_code": "something_new", "message": "Payment issue"},
        )

    transport = _transport(handler)
    with pytest.raises(FoxnoseAPIError) as exc:
        transport.request("GET", "/v1/test")
    assert type(exc.value) is FoxnoseAPIError


@pytest.mark.parametrize("body", [b"null", b"[]", b'"a bare string"'])
def test_malformed_body_on_mapped_status_falls_through(body: bytes):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            402,
            content=body,
            headers={"Content-Type": "application/json"},
        )

    transport = _transport(handler)
    with pytest.raises(FoxnoseAPIError) as exc:
        transport.request("GET", "/v1/test")
    # error_code cannot be read from a non-object body, so it stays generic.
    assert type(exc.value) is FoxnoseAPIError
    assert exc.value.status_code == 402


def test_base_except_catches_each_subclass():
    cases: list[tuple[int, dict[str, Any], dict[str, str] | None]] = [
        (
            402,
            {"error_code": "spend_cap_reached", "cap_usd": 5.0},
            None,
        ),
        (
            402,
            {"error_code": "plan_exhausted", "axis": "writes"},
            None,
        ),
        (
            403,
            {
                "message": "Plan limit exceeded",
                "error_code": "plan_limit_exceeded",
                "detail": {"entity": "roles", "current": 1, "limit": 1},
            },
            None,
        ),
        (
            429,
            {"error_code": "rate_limited", "message": "Rate limit exceeded"},
            {"Retry-After": "1"},
        ),
    ]
    for status_code, json_body, headers in cases:
        def handler(request: httpx.Request, _json=json_body, _status=status_code, _headers=headers) -> httpx.Response:
            return httpx.Response(_status, json=_json, headers=_headers)

        transport = _transport(handler, retry_config=RetryConfig(attempts=1, backoff_factor=0))
        with pytest.raises(FoxnoseAPIError):
            transport.request("GET", "/v1/test")


@pytest.mark.asyncio
async def test_async_402_spend_cap_reached():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            402,
            json={
                "error_code": "spend_cap_reached",
                "cap_usd": 250.0,
                "cycle_resets_at": "2026-09-01T00:00:00Z",
                "raise_cap_url": "https://app.example.com/billing",
            },
        )

    transport = _async_transport(handler)
    with pytest.raises(SpendCapExceeded) as exc:
        await transport.arequest("GET", "/v1/test")
    assert exc.value.cap_usd == 250.0


@pytest.mark.asyncio
async def test_async_429_rate_limited_retry_after():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"error_code": "rate_limited", "message": "Rate limit exceeded"},
            headers={"Retry-After": "7"},
        )

    transport = _async_transport(
        handler, retry_config=RetryConfig(attempts=1, backoff_factor=0)
    )
    with pytest.raises(RateLimitExceeded) as exc:
        await transport.arequest("POST", "/v1/test", json_body={"x": 1})
    assert exc.value.retry_after == 7.0
