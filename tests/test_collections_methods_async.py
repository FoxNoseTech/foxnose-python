"""Async parity tests for the Collection method surface.

Mirrors test_collections_methods.py with async invocation. Ensures every
canonical method exists and behaves on AsyncManagementClient + every legacy
folder method still emits the DeprecationWarning while hitting the legacy
/folders/ URL.
"""

from __future__ import annotations

import json
import warnings
from typing import Any, Callable

import httpx
import pytest

from foxnose_sdk import _deprecation
from foxnose_sdk.auth import SimpleKeyAuth
from foxnose_sdk.config import FoxnoseConfig
from foxnose_sdk.http import HttpTransport
from foxnose_sdk.management import (
    APICollectionList,
    APICollectionSummary,
    CollectionList,
    CollectionSummary,
)
from foxnose_sdk.management.client import AsyncManagementClient


ENV_KEY = "env123"


FOLDER_JSON = {
    "key": "coll-1",
    "name": "Articles",
    "alias": "articles",
    "folder_type": "collection",
    "content_type": "document",
    "strict_reference": False,
    "created_at": "2026-01-10T00:00:00Z",
    "parent": None,
}

API_FOLDER_JSON = {
    "folder": "coll-1",
    "api": "my-api",
    "allowed_methods": ["get_one"],
    "description_get_one": None,
    "description_get_many": None,
    "description_search": None,
    "description_schema": None,
    "created_at": "2026-01-10T00:00:00Z",
}

VERSION_JSON = {
    "key": "v1",
    "name": "v1",
    "description": None,
    "version_number": 1,
    "created_at": "2026-01-10T00:00:00Z",
    "published_at": None,
    "archived_at": None,
}

FIELD_JSON = {
    "key": "field-1",
    "name": "title",
    "description": None,
    "path": "title",
    "parent": None,
    "type": "string",
    "meta": {},
    "required": False,
    "nullable": True,
    "multiple": False,
    "localizable": False,
    "searchable": False,
    "private": False,
}


def build_async_management_client(
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


@pytest.fixture(autouse=True)
def _reset_warned():
    _deprecation._warned.clear()
    yield
    _deprecation._warned.clear()


# ----- canonical Collection CRUD (async) -----


async def test_list_collections_async_hits_collections_tree():
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["path"] = req.url.path
        return httpx.Response(
            200,
            json={"count": 0, "next": None, "previous": None, "results": []},
        )

    client = build_async_management_client(handler)
    result = await client.list_collections()
    assert isinstance(result, CollectionList)
    assert captured["path"] == f"/v1/{ENV_KEY}/collections/tree/"


async def test_get_collection_async_passes_key():
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        return httpx.Response(200, json=FOLDER_JSON)

    client = build_async_management_client(handler)
    res = await client.get_collection("coll-1")
    assert isinstance(res, CollectionSummary)
    assert f"/v1/{ENV_KEY}/collections/tree/collection/" in captured["url"]
    assert "key=coll-1" in captured["url"]


async def test_create_collection_async_posts():
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["method"] = req.method
        captured["path"] = req.url.path
        captured["body"] = json.loads(req.content.decode())
        return httpx.Response(201, json=FOLDER_JSON)

    client = build_async_management_client(handler)
    await client.create_collection(
        {
            "name": "Articles",
            "alias": "articles",
            "folder_type": "collection",
            "content_type": "document",
        }
    )
    assert captured["method"] == "POST"
    assert captured["path"] == f"/v1/{ENV_KEY}/collections/tree/"
    # Wire-compat: payload still carries folder_type wire field
    assert captured["body"]["folder_type"] == "collection"


async def test_delete_collection_async_deletes_at_tree_item():
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        captured["method"] = req.method
        return httpx.Response(204)

    client = build_async_management_client(handler)
    await client.delete_collection("coll-1")
    assert captured["method"] == "DELETE"
    assert f"/v1/{ENV_KEY}/collections/tree/collection/" in captured["url"]


# ----- canonical API ↔ Collection (async) -----


async def test_add_api_collection_async_uses_folder_wire_field():
    """Wire-compat: POST body uses the legacy 'folder' field name."""
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["path"] = req.url.path
        captured["body"] = json.loads(req.content.decode())
        return httpx.Response(201, json=API_FOLDER_JSON)

    client = build_async_management_client(handler)
    res = await client.add_api_collection(
        "my-api", "coll-1", allowed_methods=["get_one"]
    )
    assert isinstance(res, APICollectionSummary)
    assert captured["path"] == f"/v1/{ENV_KEY}/api/my-api/collections/"
    assert captured["body"]["folder"] == "coll-1"


async def test_list_api_collections_async():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"count": 0, "next": None, "previous": None, "results": []},
        )

    client = build_async_management_client(handler)
    res = await client.list_api_collections("my-api")
    assert isinstance(res, APICollectionList)


# ----- canonical Collection schema versions + fields (async) -----


async def test_publish_collection_version_async():
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        return httpx.Response(
            200, json={**VERSION_JSON, "published_at": "2026-01-11T00:00:00Z"}
        )

    client = build_async_management_client(handler)
    await client.publish_collection_version("coll-1", "v1")
    assert (
        f"/v1/{ENV_KEY}/collections/coll-1/model/versions/v1/publish/"
        in captured["url"]
    )


async def test_list_collection_fields_async_hits_schema_tree():
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["path"] = req.url.path
        return httpx.Response(
            200,
            json={"count": 0, "next": None, "previous": None, "results": []},
        )

    client = build_async_management_client(handler)
    await client.list_collection_fields("coll-1", "v1")
    assert (
        captured["path"]
        == f"/v1/{ENV_KEY}/collections/coll-1/model/versions/v1/schema/tree/"
    )


# ----- deprecation warnings (async) -----


async def test_list_folders_async_emits_deprecation_warning():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"count": 0, "next": None, "previous": None, "results": []},
        )

    client = build_async_management_client(handler)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        await client.list_folders()
    deprecations = [
        w for w in caught if issubclass(w.category, DeprecationWarning)
    ]
    assert len(deprecations) == 1
    assert "list_folders" in str(deprecations[0].message)


async def test_list_folders_async_still_hits_legacy_url():
    """Async deprecated alias keeps its original wire behaviour (/folders/)."""
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["path"] = req.url.path
        return httpx.Response(
            200,
            json={"count": 0, "next": None, "previous": None, "results": []},
        )

    client = build_async_management_client(handler)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        await client.list_folders()
    assert captured["path"] == f"/v1/{ENV_KEY}/folders/tree/"


async def test_add_api_folder_async_emits_warning():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json=API_FOLDER_JSON)

    client = build_async_management_client(handler)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        await client.add_api_folder("my-api", "coll-1", allowed_methods=["get_one"])
    deprecations = [
        w for w in caught if issubclass(w.category, DeprecationWarning)
    ]
    assert deprecations
    assert "add_api_folder" in str(deprecations[0].message)


async def test_publish_folder_version_async_emits_warning():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={**VERSION_JSON, "published_at": "2026-01-11T00:00:00Z"}
        )

    client = build_async_management_client(handler)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        await client.publish_folder_version("coll-1", "v1")
    deprecations = [
        w for w in caught if issubclass(w.category, DeprecationWarning)
    ]
    assert deprecations
    assert "publish_folder_version" in str(deprecations[0].message)
