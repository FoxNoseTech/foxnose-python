"""Behavioural tests for the post-composite-removal contract.

Covers both the model-shape guarantees (no legacy folder_type / component
fields) and the active rejection of legacy kwargs on the client surface
and on the BatchUpsertItem model.
"""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from foxnose_sdk.management.client import (
    AsyncManagementClient,
    ManagementClient,
)
from foxnose_sdk.management.models import (
    BatchUpsertItem,
    CollectionSummary,
    FolderSummary,
    ResourceSummary,
)


# ---------------------------------------------------------------------------
# Model shape: no legacy fields exposed
# ---------------------------------------------------------------------------


def test_folder_summary_no_folder_type():
    assert "folder_type" not in FolderSummary.model_fields


def test_collection_summary_no_folder_type():
    assert "folder_type" not in CollectionSummary.model_fields


def test_resource_summary_no_component():
    assert "component" not in ResourceSummary.model_fields


# ---------------------------------------------------------------------------
# BatchUpsertItem must REJECT legacy component kwarg, not silently drop it.
# ---------------------------------------------------------------------------


def test_batch_upsert_item_rejects_legacy_component():
    """BatchUpsertItem must REJECT (not silently drop) the legacy ``component``
    kwarg so downstream callers get a clear ValidationError instead of a
    confusing silent no-op."""
    with pytest.raises(ValidationError):
        BatchUpsertItem(
            component="cmp-xyz",
            external_id="ext-1",
            payload={"data": {}},
        )


def test_batch_upsert_item_accepts_supported_fields():
    """Sanity check the model still accepts the supported shape."""
    item = BatchUpsertItem(external_id="ext-1", payload={"data": {"title": "Hi"}})
    assert item.external_id == "ext-1"
    assert item.payload == {"data": {"title": "Hi"}}


# ---------------------------------------------------------------------------
# Client method signatures must not accept `component=` anymore.
# ---------------------------------------------------------------------------


def test_create_resource_signature_no_component():
    """The sync ManagementClient.create_resource must not accept a ``component``
    kwarg. Passing it should raise TypeError at call time (Python signature
    enforcement)."""
    sig = inspect.signature(ManagementClient.create_resource)
    assert "component" not in sig.parameters, (
        f"create_resource must not accept `component` kwarg; "
        f"parameters: {list(sig.parameters)}"
    )


def test_upsert_resource_signature_no_component():
    sig = inspect.signature(ManagementClient.upsert_resource)
    assert "component" not in sig.parameters, (
        f"upsert_resource must not accept `component` kwarg; "
        f"parameters: {list(sig.parameters)}"
    )


def test_async_create_resource_signature_no_component():
    sig = inspect.signature(AsyncManagementClient.create_resource)
    assert "component" not in sig.parameters, (
        f"AsyncManagementClient.create_resource must not accept `component` kwarg; "
        f"parameters: {list(sig.parameters)}"
    )


def test_async_upsert_resource_signature_no_component():
    sig = inspect.signature(AsyncManagementClient.upsert_resource)
    assert "component" not in sig.parameters, (
        f"AsyncManagementClient.upsert_resource must not accept `component` kwarg; "
        f"parameters: {list(sig.parameters)}"
    )


# ---------------------------------------------------------------------------
# URL behaviour: create_resource must not put `component=` in the request URL.
# Uses the existing httpx.MockTransport pattern from tests/test_clients.py.
# ---------------------------------------------------------------------------


def test_create_resource_url_does_not_include_component():
    """When ManagementClient.create_resource issues its POST, the resulting
    URL must NOT contain ``component=`` — even if some forwarded-config layer
    or stale environment variable somehow tried to inject it."""
    import httpx

    from foxnose_sdk.auth import SimpleKeyAuth
    from foxnose_sdk.config import FoxnoseConfig
    from foxnose_sdk.http import HttpTransport

    captured_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_urls.append(str(request.url))
        return httpx.Response(
            201,
            json={
                "key": "resource-1",
                "folder": "folder-1",
                "content_type": "document",
                "created_at": "2024-01-10T00:00:00Z",
                "vectors_size": 0,
                "name": None,
                "resource_owner": None,
                "current_revision": "rev-1",
                "external_id": None,
            },
        )

    client = ManagementClient(
        base_url="https://api.example.com",
        environment_key="env123",
        auth=SimpleKeyAuth("pub", "secret"),
    )
    client._transport = HttpTransport(  # type: ignore[attr-defined]
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=SimpleKeyAuth("pub", "secret"),
        sync_client=httpx.Client(
            base_url="https://api.example.com",
            transport=httpx.MockTransport(handler),
        ),
    )

    client.create_resource("folder-1", {"data": {"title": "Hello"}})

    assert captured_urls, "expected create_resource to issue an HTTP request"
    assert "component=" not in captured_urls[0], (
        f"create_resource URL must not include component=; got {captured_urls[0]}"
    )
