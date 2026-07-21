"""Tests for sync_collection_component + NestedFieldMeta.

Mirrors the TS SDK's coverage:
- routing/body-shape for ManagementClient.sync_collection_component
- AsyncManagementClient.sync_collection_component
- NestedFieldMeta helper (required fields, defaults, .to_meta())
- client-side invariant: to_versions keys must be a subset of field_paths
"""

from __future__ import annotations

import json
from typing import Any, Callable

import httpx
import pytest
from pydantic import ValidationError

from foxnose_sdk.auth import SimpleKeyAuth
from foxnose_sdk.config import FoxnoseConfig
from foxnose_sdk.http import HttpTransport
from foxnose_sdk.management import (
    AsyncManagementClient,
    ManagementClient,
    NestedFieldMeta,
    SyncComponentResponse,
)


ENV_KEY = "env123"

SYNC_OK_JSON: dict[str, Any] = {
    "synced_paths": ["seo"],
    "skipped": [{"path": "hero", "reason": "auto_update_mode"}],
    "schema_version": "ver-new-12345",
}


def _build_client(handler: Callable[[httpx.Request], httpx.Response]) -> ManagementClient:
    client = ManagementClient(
        base_url="https://api.example.com",
        environment_key=ENV_KEY,
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
    return client


def _build_async_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> AsyncManagementClient:
    client = AsyncManagementClient(
        base_url="https://api.example.com",
        environment_key=ENV_KEY,
        auth=SimpleKeyAuth("pub", "secret"),
    )
    client._transport = HttpTransport(  # type: ignore[attr-defined]
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=SimpleKeyAuth("pub", "secret"),
        async_client=httpx.AsyncClient(
            base_url="https://api.example.com",
            transport=httpx.MockTransport(handler),
        ),
    )
    return client


# ----------------------------------------------------------------------
# sync_collection_component — sync client
# ----------------------------------------------------------------------


def test_sync_collection_component_empty_body_hits_endpoint():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["method"] = request.method
        captured["body"] = json.loads(request.content.decode() or "{}")
        return httpx.Response(200, json=SYNC_OK_JSON)

    client = _build_client(handler)
    result = client.sync_collection_component("articles")

    assert captured["method"] == "POST"
    assert captured["path"] == f"/v1/{ENV_KEY}/collections/articles/sync_component/"
    assert captured["body"] == {}
    assert isinstance(result, SyncComponentResponse)
    assert result.synced_paths == ["seo"]
    assert result.skipped[0].path == "hero"
    assert result.skipped[0].reason == "auto_update_mode"
    assert result.schema_version == "ver-new-12345"


def test_sync_collection_component_field_paths_only():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode() or "{}")
        return httpx.Response(200, json=SYNC_OK_JSON)

    client = _build_client(handler)
    client.sync_collection_component("articles", field_paths=["seo"])
    assert captured["body"] == {"field_paths": ["seo"]}


def test_sync_collection_component_field_paths_and_to_versions():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode() or "{}")
        return httpx.Response(200, json=SYNC_OK_JSON)

    client = _build_client(handler)
    client.sync_collection_component(
        "articles",
        field_paths=["seo", "hero"],
        to_versions={"seo": "ver-target-abc"},
    )
    assert captured["body"] == {
        "field_paths": ["seo", "hero"],
        "to_versions": {"seo": "ver-target-abc"},
    }


def test_sync_collection_component_rejects_to_versions_extras_subset():
    """Client-side invariant: to_versions keys must be a subset of field_paths."""
    # No HTTP call expected — handler should never run.
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("HTTP request must not be issued")

    client = _build_client(handler)
    with pytest.raises(ValueError) as exc:
        client.sync_collection_component(
            "articles",
            field_paths=["seo"],
            to_versions={"hero": "ver-something"},
        )
    assert "hero" in str(exc.value)


def test_sync_collection_component_accepts_to_versions_alone():
    """to_versions without field_paths is fine — server treats it as 'sync only these'."""
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode() or "{}")
        return httpx.Response(200, json=SYNC_OK_JSON)

    client = _build_client(handler)
    client.sync_collection_component(
        "articles",
        to_versions={"seo": "ver-target-abc"},
    )
    assert captured["body"] == {"to_versions": {"seo": "ver-target-abc"}}


def test_sync_collection_component_accepts_collection_summary_ref():
    """The collection_key argument can also be a model object with a `key` attribute."""
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(200, json=SYNC_OK_JSON)

    client = _build_client(handler)

    class _CollectionRef:
        key = "articles"

    client.sync_collection_component(_CollectionRef())  # type: ignore[arg-type]
    assert captured["path"] == f"/v1/{ENV_KEY}/collections/articles/sync_component/"


# ----------------------------------------------------------------------
# sync_collection_component — async client
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_sync_collection_component_hits_same_endpoint():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content.decode() or "{}")
        return httpx.Response(200, json=SYNC_OK_JSON)

    client = _build_async_client(handler)
    result = await client.sync_collection_component(
        "articles", field_paths=["seo"], to_versions={"seo": "ver-target-abc"}
    )
    assert captured["path"] == f"/v1/{ENV_KEY}/collections/articles/sync_component/"
    assert captured["body"] == {
        "field_paths": ["seo"],
        "to_versions": {"seo": "ver-target-abc"},
    }
    assert isinstance(result, SyncComponentResponse)


@pytest.mark.asyncio
async def test_async_sync_collection_component_rejects_to_versions_extras_subset():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("HTTP request must not be issued")

    client = _build_async_client(handler)
    with pytest.raises(ValueError):
        await client.sync_collection_component(
            "articles",
            field_paths=["seo"],
            to_versions={"hero": "ver-something"},
        )


# ----------------------------------------------------------------------
# NestedFieldMeta helper
# ----------------------------------------------------------------------


def test_nested_field_meta_required_fields():
    """component AND component_version are required; auto_update defaults to False."""
    with pytest.raises(ValidationError):
        NestedFieldMeta(component="cmp-abc123")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        NestedFieldMeta(component_version="ver-abc123")  # type: ignore[call-arg]


def test_nested_field_meta_defaults_auto_update_false():
    meta = NestedFieldMeta(component="cmp-abc123", component_version="ver-def456")
    assert meta.auto_update is False
    assert meta.to_meta() == {
        "component": "cmp-abc123",
        "component_version": "ver-def456",
        "auto_update": False,
    }


def test_nested_field_meta_explicit_auto_update_true():
    meta = NestedFieldMeta(
        component="cmp-abc123", component_version="ver-def456", auto_update=True
    )
    assert meta.to_meta()["auto_update"] is True


def test_nested_field_meta_short_uid_rejected():
    """component_version too short → ValidationError (min_length=6)."""
    with pytest.raises(ValidationError):
        NestedFieldMeta(component="cmp-abc123", component_version="x")


def test_nested_field_meta_accepts_extra_keys():
    """extra=allow → callers can attach title/description/etc."""
    meta = NestedFieldMeta(
        component="cmp-abc123",
        component_version="ver-def456",
        title="Hero block",  # type: ignore[call-arg]
    )
    assert meta.to_meta()["title"] == "Hero block"


# ----------------------------------------------------------------------
# SyncComponentResponse parsing
# ----------------------------------------------------------------------


def test_sync_component_response_parses_minimal_payload():
    r = SyncComponentResponse.model_validate(
        {"synced_paths": [], "skipped": [], "schema_version": None}
    )
    assert r.synced_paths == []
    assert r.skipped == []
    assert r.schema_version is None


def test_sync_component_response_skipped_items_typed():
    r = SyncComponentResponse.model_validate(
        {
            "synced_paths": ["seo"],
            "skipped": [
                {"path": "hero", "reason": "auto_update_mode"},
                {"path": "footer", "reason": "already_at_target"},
            ],
            "schema_version": "ver-new-12345",
        }
    )
    assert [s.reason for s in r.skipped] == [
        "auto_update_mode",
        "already_at_target",
    ]
