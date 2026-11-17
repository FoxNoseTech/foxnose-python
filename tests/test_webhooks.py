"""Outbound webhooks on the Management clients.

The payloads mirror core's ``webhooks/serializers.py``, ``webhooks/views.py`` and
``webhooks/services.py``.
"""

from __future__ import annotations

import inspect
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable

import httpx
import pytest
from pydantic import ValidationError

from foxnose_sdk import (
    WebhookEndpointLimitExceeded,
    WebhookEndpointNotActive,
    WebhookEndpointNotFound,
    WebhookEndpointNotSubscribed,
    WebhookEventNotFound,
)
from foxnose_sdk.auth import SimpleKeyAuth
from foxnose_sdk.config import FoxnoseConfig, RetryConfig
from foxnose_sdk.errors import FoxnoseAPIError, FoxnoseTransportError
from foxnose_sdk.http import HttpTransport
from foxnose_sdk.management.client import AsyncManagementClient, ManagementClient
from foxnose_sdk.management.models import (
    WebhookAttemptList,
    WebhookEndpoint,
    WebhookEndpointCreated,
    WebhookEndpointDeliveryList,
    WebhookEndpointList,
    WebhookEventDetail,
    WebhookEventList,
    WebhookEventTypeList,
    WebhookRecovery,
    WebhookRedeliveryResult,
    WebhookSecret,
    WebhookSecretRotation,
    WebhookTestEvent,
)

ENV = "env-1"
ENDPOINT = "3f6c2a8e-91d4-4b7a-a5e2-0c9d8b7f1e23"
EVENT = "evt_01JCX3Q9W2B5V7RZ0D4K6M8P1T"
ROOT = f"/v1/{ENV}/webhooks"
EP = f"{ROOT}/endpoints/{ENDPOINT}"
EV = f"{ROOT}/events/{EVENT}"

SECRET = "whsec_MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw8Gx5FN2xCTE="
NEW_SECRET = "whsec_Q2b7Fz1kR8nYc4Lm0VtX9pWs3dHj6GaEuKo5NiBrT1A="

ENDPOINT_BODY = {
    "id": ENDPOINT,
    "url": "https://hooks.example.com/foxnose",
    "description": "Search index sync",
    "event_types": ["revision.published", "resource.deleted"],
    "collection_keys": ["mK8nP3tYvBcX"],
    "payload_mode": "content",
    "version": 1,
    "status": "active",
    "disabled_reason": None,
    "failing_since": None,
    "disabled_at": None,
    "created_at": "2026-11-12T09:30:12.418226+00:00",
    "updated_at": "2026-11-12T09:30:12.418226+00:00",
}

PAGE_OF_ENDPOINTS = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [{**ENDPOINT_BODY, "stats_24h": {"attempts": 42, "succeeded": 41}}],
}

DELIVERY = {
    "id": "9b1e7c42-5d3a-4f8e-b2c6-7a0d1e9f3c85",
    "endpoint": {"id": ENDPOINT, "deleted": False},
    "status": "pending",
    "attempts": 2,
    "last_status_code": 503,
    "last_error": None,
    "created_at": "2026-11-12T09:41:07.530114+00:00",
    "finished_at": None,
    "next_attempt_at": "2026-11-12T09:41:28.902311+00:00",
}

PAGE_OF_DELIVERIES = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [
        {
            **DELIVERY,
            "event_id": EVENT,
            "event": {"id": EVENT, "type": "revision.published", "test": False},
        }
    ],
}

EVENT_ITEM = {
    "id": EVENT,
    "type": "revision.published",
    "created_at": "2026-11-12T09:41:07.512000+00:00",
    "test": False,
    "collection_key": "mK8nP3tYvBcX",
}

PAGE_OF_EVENTS = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [
        {**EVENT_ITEM, "delivery_counts": {"pending": 1, "succeeded": 1, "dead": 0}}
    ],
}

EVENT_DETAIL = {
    **EVENT_ITEM,
    "envelope": {
        "id": EVENT,
        "type": "revision.published",
        "version": 1,
        "timestamp": "2026-11-12T09:41:07.512Z",
        "test": False,
        "environment": {"key": ENV, "project": "p9x8y7z6"},
        "data": {"collection": {"key": "mK8nP3tYvBcX"}},
    },
    "deliveries": [DELIVERY],
}

PAGE_OF_ATTEMPTS = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [
        {
            "id": "7e2a9c4d-1b8f-4d6a-9e3c-5a0b7d2f8c61",
            "delivery_id": DELIVERY["id"],
            "endpoint": {"id": ENDPOINT, "deleted": True},
            "created_at": "2026-11-12T09:41:13.640981+00:00",
            "status_code": 503,
            "latency_ms": 212,
            "error_class": None,
            "response_excerpt": "upstream unavailable",
        }
    ],
}

REDELIVERED = {
    "event_id": EVENT,
    "deliveries": [
        {"id": "2a7d4f9c-8e1b-4c3a-b6d5-9f0e2a8c7b13", "endpoint_id": ENDPOINT}
    ],
    "skipped": [
        {"endpoint_id": "5c9e1a7b-3d2f-4b8a-8c6e-1f4d7a0b9e52", "reason": "paused"}
    ],
}

EVENT_TYPES = {
    "results": [
        {
            "name": "resource.created",
            "description": "A resource is created.",
            "collection_scoped": True,
            "schemas": {
                "references": {"type": "object"},
                "content": {"type": "object"},
            },
        }
    ]
}

Handler = Callable[[httpx.Request], httpx.Response]


def management_client(handler: Handler, *, is_async: bool, attempts: int = 2):
    client_cls = AsyncManagementClient if is_async else ManagementClient
    client = client_cls(
        base_url="https://api.example.com",
        environment_key=ENV,
        auth=SimpleKeyAuth("pub", "secret"),
    )
    http_client = (httpx.AsyncClient if is_async else httpx.Client)(
        base_url="https://api.example.com", transport=httpx.MockTransport(handler)
    )
    client._transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=SimpleKeyAuth("pub", "secret"),
        retry_config=RetryConfig(attempts=attempts, backoff_factor=0),
        **{"async_client" if is_async else "sync_client": http_client},
    )
    return client


async def run(call: Callable[[Any], Any], client: Any) -> Any:
    """Run ``call`` on a sync or async client alike."""
    result = call(client)
    return await result if inspect.isawaitable(result) else result


both = pytest.mark.parametrize("is_async", [False, True], ids=["sync", "async"])

CALLS = [
    pytest.param(
        lambda c: c.list_webhook_endpoints(params={"status": "active", "limit": 5}),
        "GET",
        f"{ROOT}/endpoints/",
        {"status": "active", "limit": "5"},
        200,
        PAGE_OF_ENDPOINTS,
        WebhookEndpointList,
        id="list_webhook_endpoints",
    ),
    pytest.param(
        lambda c: c.create_webhook_endpoint(
            url="https://hooks.example.com/foxnose", event_types=["resource.deleted"]
        ),
        "POST",
        f"{ROOT}/endpoints/",
        {},
        201,
        {**ENDPOINT_BODY, "secret": SECRET},
        WebhookEndpointCreated,
        id="create_webhook_endpoint",
    ),
    pytest.param(
        lambda c: c.get_webhook_endpoint(ENDPOINT),
        "GET",
        f"{EP}/",
        {},
        200,
        ENDPOINT_BODY,
        WebhookEndpoint,
        id="get_webhook_endpoint",
    ),
    pytest.param(
        lambda c: c.update_webhook_endpoint(ENDPOINT, status="paused"),
        "PATCH",
        f"{EP}/",
        {},
        200,
        {**ENDPOINT_BODY, "status": "paused"},
        WebhookEndpoint,
        id="update_webhook_endpoint",
    ),
    pytest.param(
        lambda c: c.list_webhook_endpoint_deliveries(ENDPOINT, params={"offset": 10}),
        "GET",
        f"{EP}/deliveries/",
        {"offset": "10"},
        200,
        PAGE_OF_DELIVERIES,
        WebhookEndpointDeliveryList,
        id="list_webhook_endpoint_deliveries",
    ),
    pytest.param(
        lambda c: c.get_webhook_endpoint_secret(ENDPOINT),
        "GET",
        f"{EP}/secret/",
        {},
        200,
        {"secret": SECRET},
        WebhookSecret,
        id="get_webhook_endpoint_secret",
    ),
    pytest.param(
        lambda c: c.rotate_webhook_endpoint_secret(ENDPOINT),
        "POST",
        f"{EP}/secret/rotate/",
        {},
        200,
        {
            "secret": NEW_SECRET,
            "previous_secret_expires_at": "2026-11-13T10:02:51+00:00",
        },
        WebhookSecretRotation,
        id="rotate_webhook_endpoint_secret",
    ),
    pytest.param(
        lambda c: c.send_webhook_test_event(ENDPOINT, "revision.published"),
        "POST",
        f"{EP}/test/",
        {},
        202,
        {"event_id": EVENT, "delivery_id": DELIVERY["id"]},
        WebhookTestEvent,
        id="send_webhook_test_event",
    ),
    pytest.param(
        lambda c: c.recover_webhook_deliveries(ENDPOINT, since="2026-11-10T00:00:00Z"),
        "POST",
        f"{EP}/recover/",
        {},
        202,
        {"requeued": 37, "more": False},
        WebhookRecovery,
        id="recover_webhook_deliveries",
    ),
    pytest.param(
        lambda c: c.list_webhook_events(
            params={"type": "resource.deleted", "test": "false"}
        ),
        "GET",
        f"{ROOT}/events/",
        {"type": "resource.deleted", "test": "false"},
        200,
        PAGE_OF_EVENTS,
        WebhookEventList,
        id="list_webhook_events",
    ),
    pytest.param(
        lambda c: c.get_webhook_event(EVENT),
        "GET",
        f"{EV}/",
        {},
        200,
        EVENT_DETAIL,
        WebhookEventDetail,
        id="get_webhook_event",
    ),
    pytest.param(
        lambda c: c.list_webhook_event_attempts(EVENT),
        "GET",
        f"{EV}/attempts/",
        {},
        200,
        PAGE_OF_ATTEMPTS,
        WebhookAttemptList,
        id="list_webhook_event_attempts",
    ),
    pytest.param(
        lambda c: c.redeliver_webhook_event(EVENT),
        "POST",
        f"{EV}/redeliver/",
        {},
        202,
        REDELIVERED,
        WebhookRedeliveryResult,
        id="redeliver_webhook_event",
    ),
    pytest.param(
        lambda c: c.list_webhook_event_types(),
        "GET",
        f"{ROOT}/event-types/",
        {},
        200,
        EVENT_TYPES,
        WebhookEventTypeList,
        id="list_webhook_event_types",
    ),
]


@both
@pytest.mark.parametrize("call, method, path, query, status, payload, model", CALLS)
async def test_webhook_call(
    is_async, call, method, path, query, status, payload, model
):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["query"] = dict(request.url.params)
        return httpx.Response(status, json=payload)

    result = await run(call, management_client(handler, is_async=is_async))

    assert seen == {"method": method, "path": path, "query": query}
    assert isinstance(result, model)
    # every wire field is parsed, not only the ones a test names
    assert set(payload) <= set(result.model_dump())


@both
async def test_delete_webhook_endpoint(is_async):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["call"] = (request.method, request.url.path)
        return httpx.Response(204)

    client = management_client(handler, is_async=is_async)
    assert await run(lambda c: c.delete_webhook_endpoint(ENDPOINT), client) is None
    assert seen["call"] == ("DELETE", f"{EP}/")


@both
async def test_create_sends_only_what_was_given(is_async):
    bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(201, json={**ENDPOINT_BODY, "secret": SECRET})

    client = management_client(handler, is_async=is_async)
    await run(
        lambda c: c.create_webhook_endpoint(
            url="https://hooks.example.com/foxnose", event_types=("resource.deleted",)
        ),
        client,
    )
    await run(
        lambda c: c.create_webhook_endpoint(
            url="https://hooks.example.com/foxnose",
            event_types=["resource.deleted"],
            description="Sync",
            collection_keys=["mK8nP3tYvBcX"],
            payload_mode="content",
            version=1,
        ),
        client,
    )
    assert bodies == [
        {
            "url": "https://hooks.example.com/foxnose",
            "event_types": ["resource.deleted"],
        },
        {
            "url": "https://hooks.example.com/foxnose",
            "event_types": ["resource.deleted"],
            "description": "Sync",
            "collection_keys": ["mK8nP3tYvBcX"],
            "payload_mode": "content",
            "version": 1,
        },
    ]


@both
async def test_update_sends_only_the_changed_fields(is_async):
    bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=ENDPOINT_BODY)

    client = management_client(handler, is_async=is_async)
    await run(
        lambda c: c.update_webhook_endpoint(
            ENDPOINT, description="", collection_keys=[], status="active"
        ),
        client,
    )
    assert bodies == [{"description": "", "collection_keys": [], "status": "active"}]


@both
async def test_action_bodies(is_async):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.path, json.loads(request.content)))
        if request.url.path.endswith("/rotate/"):
            return httpx.Response(200, json={"secret": NEW_SECRET})
        if request.url.path.endswith("/test/"):
            return httpx.Response(202, json={"event_id": EVENT, "delivery_id": "d"})
        if request.url.path.endswith("/recover/"):
            return httpx.Response(202, json={"requeued": 0, "more": False})
        return httpx.Response(202, json=REDELIVERED)

    client = management_client(handler, is_async=is_async)
    rotation = await run(
        lambda c: c.rotate_webhook_endpoint_secret(ENDPOINT, expire_previous_now=True),
        client,
    )
    assert rotation.previous_secret_expires_at is None
    await run(lambda c: c.send_webhook_test_event(ENDPOINT, "resource.created"), client)
    since = datetime(2026, 11, 10, tzinfo=timezone.utc)
    await run(lambda c: c.recover_webhook_deliveries(ENDPOINT, since=since), client)
    await run(lambda c: c.redeliver_webhook_event(EVENT), client)
    await run(lambda c: c.redeliver_webhook_event(EVENT, endpoint_id=ENDPOINT), client)
    assert seen == [
        (f"{EP}/secret/rotate/", {"expire_previous_now": True}),
        (f"{EP}/test/", {"event_type": "resource.created"}),
        (f"{EP}/recover/", {"since": "2026-11-10T00:00:00+00:00"}),
        (f"{EV}/redeliver/", {}),
        (f"{EV}/redeliver/", {"endpoint_id": ENDPOINT}),
    ]


@both
async def test_nested_shapes_are_parsed(is_async):
    def handler(request: httpx.Request) -> httpx.Response:
        payloads = {
            f"{EP}/deliveries/": PAGE_OF_DELIVERIES,
            f"{EV}/": EVENT_DETAIL,
            f"{EV}/attempts/": PAGE_OF_ATTEMPTS,
            f"{ROOT}/events/": PAGE_OF_EVENTS,
            f"{ROOT}/endpoints/": PAGE_OF_ENDPOINTS,
        }
        return httpx.Response(200, json=payloads[request.url.path])

    client = management_client(handler, is_async=is_async)
    endpoint = (await run(lambda c: c.list_webhook_endpoints(), client)).results[0]
    assert endpoint.stats_24h.attempts == 42 and endpoint.stats_24h.succeeded == 41
    delivery = (
        await run(lambda c: c.list_webhook_endpoint_deliveries(ENDPOINT), client)
    ).results[0]
    assert delivery.event.type == "revision.published" and not delivery.event.test
    assert delivery.endpoint.deleted is False
    detail = await run(lambda c: c.get_webhook_event(EVENT), client)
    assert detail.envelope["data"]["collection"]["key"] == "mK8nP3tYvBcX"
    assert detail.deliveries[0].next_attempt_at is not None
    summary = (await run(lambda c: c.list_webhook_events(), client)).results[0]
    assert summary.delivery_counts.pending == 1 and summary.delivery_counts.dead == 0
    attempt = (
        await run(lambda c: c.list_webhook_event_attempts(EVENT), client)
    ).results[0]
    assert attempt.endpoint.deleted is True and attempt.latency_ms == 212


@both
async def test_a_deleted_endpoint_event_may_be_missing(is_async):
    body = {
        **PAGE_OF_DELIVERIES,
        "results": [{**PAGE_OF_DELIVERIES["results"][0], "event": None}],
    }
    client = management_client(
        lambda _: httpx.Response(200, json=body), is_async=is_async
    )
    page = await run(lambda c: c.list_webhook_endpoint_deliveries(ENDPOINT), client)
    assert page.results[0].event is None


@both
async def test_event_types_carry_both_schemas(is_async):
    client = management_client(
        lambda _: httpx.Response(200, json=EVENT_TYPES), is_async=is_async
    )
    types = await run(lambda c: c.list_webhook_event_types(), client)
    assert types.results[0].collection_scoped is True
    assert types.results[0].schemas.content == {"type": "object"}


@both
async def test_ids_are_quoted_in_the_path(is_async):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.raw_path.decode())
        return httpx.Response(200, json=EVENT_DETAIL)

    client = management_client(handler, is_async=is_async)
    await run(lambda c: c.get_webhook_event("evt/../x"), client)
    assert seen == [f"{ROOT}/events/evt%2F..%2Fx/"]


# -- errors ---------------------------------------------------------------------------

ERRORS = [
    (404, "webhook_endpoint_not_found", None, WebhookEndpointNotFound),
    (404, "webhook_event_not_found", None, WebhookEventNotFound),
    (409, "limit_exceeded", None, WebhookEndpointLimitExceeded),
    (409, "endpoint_not_active", {"reason": "paused"}, WebhookEndpointNotActive),
    (409, "endpoint_not_subscribed", None, WebhookEndpointNotSubscribed),
]


@both
@pytest.mark.parametrize("status, code, detail, exc_type", ERRORS)
async def test_api_errors_are_typed(is_async, status, code, detail, exc_type):
    body = {"message": "refused", "error_code": code, "detail": detail}
    client = management_client(
        lambda _: httpx.Response(status, json=body), is_async=is_async
    )
    with pytest.raises(exc_type) as caught:
        await run(lambda c: c.get_webhook_endpoint(ENDPOINT), client)
    assert isinstance(caught.value, FoxnoseAPIError)
    assert caught.value.status_code == status
    assert caught.value.error_code == code


@both
async def test_not_active_and_not_subscribed_keep_their_detail(is_async):
    skipped = [{"endpoint_id": ENDPOINT, "reason": "paused"}]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/recover/"):
            body = {
                "message": "m",
                "error_code": "endpoint_not_active",
                "detail": {"reason": "deleted"},
            }
        else:
            body = {
                "message": "m",
                "error_code": "endpoint_not_subscribed",
                "detail": {"skipped": skipped},
            }
        return httpx.Response(409, json=body)

    client = management_client(handler, is_async=is_async)
    with pytest.raises(WebhookEndpointNotActive) as not_active:
        await run(
            lambda c: c.recover_webhook_deliveries(
                ENDPOINT, since="2026-11-10T00:00:00Z"
            ),
            client,
        )
    assert not_active.value.reason == "deleted" and not_active.value.skipped == []
    with pytest.raises(WebhookEndpointNotSubscribed) as not_subscribed:
        await run(lambda c: c.redeliver_webhook_event(EVENT), client)
    assert not_subscribed.value.skipped == skipped


@both
@pytest.mark.parametrize("detail", [None, "text", ["x"], {"skipped": "x"}])
async def test_a_malformed_detail_does_not_break_the_mapping(is_async, detail):
    body = {"message": "m", "error_code": "endpoint_not_active", "detail": detail}
    client = management_client(
        lambda _: httpx.Response(409, json=body), is_async=is_async
    )
    with pytest.raises(WebhookEndpointNotActive) as caught:
        await run(lambda c: c.redeliver_webhook_event(EVENT), client)
    assert caught.value.skipped == []


@both
async def test_validation_errors_stay_api_errors_with_code_and_detail(is_async):
    body = {
        "message": "The URL is not allowed",
        "error_code": "invalid_url",
        "detail": {"field": "url", "reason": "scheme"},
    }
    client = management_client(
        lambda _: httpx.Response(400, json=body), is_async=is_async
    )
    with pytest.raises(FoxnoseAPIError) as caught:
        await run(
            lambda c: c.create_webhook_endpoint(url="http://x", event_types=["a"]),
            client,
        )
    assert type(caught.value) is FoxnoseAPIError
    assert caught.value.error_code == "invalid_url"
    assert caught.value.detail == {"field": "url", "reason": "scheme"}


# -- writes are not repeated ----------------------------------------------------------


@both
@pytest.mark.parametrize(
    "call",
    [
        lambda c: c.create_webhook_endpoint(
            url="https://x.example.com", event_types=["a"]
        ),
        lambda c: c.rotate_webhook_endpoint_secret(ENDPOINT),
        lambda c: c.send_webhook_test_event(ENDPOINT, "resource.created"),
        lambda c: c.recover_webhook_deliveries(ENDPOINT, since="2026-11-10T00:00:00Z"),
        lambda c: c.redeliver_webhook_event(EVENT),
    ],
    ids=["create", "rotate", "test", "recover", "redeliver"],
)
async def test_a_lost_connection_is_not_retried_on_a_write(is_async, call):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise httpx.ConnectError("lost", request=request)

    client = management_client(handler, is_async=is_async, attempts=3)
    with pytest.raises(FoxnoseTransportError):
        await run(call, client)
    assert len(calls) == 1


# -- secrets stay out of repr, errors and logs ----------------------------------------


@both
async def test_secrets_are_hidden_from_repr(is_async):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/endpoints/"):
            return httpx.Response(201, json={**ENDPOINT_BODY, "secret": SECRET})
        if request.url.path.endswith("/rotate/"):
            return httpx.Response(200, json={"secret": NEW_SECRET})
        return httpx.Response(200, json={"secret": SECRET})

    client = management_client(handler, is_async=is_async)
    created = await run(
        lambda c: c.create_webhook_endpoint(
            url="https://x.example.com", event_types=["a"]
        ),
        client,
    )
    revealed = await run(lambda c: c.get_webhook_endpoint_secret(ENDPOINT), client)
    rotated = await run(lambda c: c.rotate_webhook_endpoint_secret(ENDPOINT), client)
    assert created.secret == SECRET and revealed.secret == SECRET
    assert rotated.secret == NEW_SECRET
    for model in (created, revealed, rotated):
        for text in (repr(model), str(model)):
            assert SECRET not in text and NEW_SECRET not in text
    assert SECRET not in repr(created.model_dump(exclude={"secret"}))


def test_a_response_that_fails_to_parse_does_not_quote_the_secret():
    with pytest.raises(ValidationError) as caught:
        WebhookEndpointCreated.model_validate({"id": 1, "secret": SECRET})
    assert SECRET not in str(caught.value)
    with pytest.raises(ValidationError) as caught:
        WebhookSecretRotation.model_validate(
            {"secret": SECRET, "previous_secret_expires_at": "nope"}
        )
    assert SECRET not in str(caught.value)
    with pytest.raises(ValidationError) as caught:
        WebhookSecret.model_validate({"secret": ["x", SECRET]})
    assert SECRET not in str(caught.value)


@both
async def test_a_secret_reaches_no_log(is_async, caplog):
    client = management_client(
        lambda _: httpx.Response(200, json={"secret": SECRET}), is_async=is_async
    )
    with caplog.at_level(logging.DEBUG):
        await run(lambda c: c.get_webhook_endpoint_secret(ENDPOINT), client)
    assert SECRET not in caplog.text


def test_an_attempt_hides_the_response_excerpt_from_repr():
    attempt = WebhookAttemptList.model_validate(PAGE_OF_ATTEMPTS).results[0]
    assert attempt.response_excerpt == "upstream unavailable"
    assert "upstream unavailable" not in repr(attempt)


def test_a_field_the_server_adds_is_kept():
    endpoint = WebhookEndpoint.model_validate({**ENDPOINT_BODY, "region": "eu"})
    assert endpoint.model_dump()["region"] == "eu"


def test_sync_and_async_clients_have_the_same_webhook_methods():
    def names(cls):
        return {n for n in dir(cls) if "webhook" in n and not n.startswith("_")}

    assert names(ManagementClient) == names(AsyncManagementClient)
    assert len(names(ManagementClient)) == 15
