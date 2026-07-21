"""Async wire-behaviour coverage for the Collection/Folder method surface.

Mirrors test_collection_methods_wire.py on AsyncManagementClient, covering the
async request-building paths the smoke tests do not touch.
"""

from __future__ import annotations

import json
import warnings
from typing import Callable

import httpx
import pytest

from foxnose_sdk import _deprecation
from foxnose_sdk.auth import SimpleKeyAuth
from foxnose_sdk.config import FoxnoseConfig
from foxnose_sdk.http import HttpTransport
from foxnose_sdk.management.client import AsyncManagementClient


ENV_KEY = "env123"

COLLECTION_JSON = {
    "key": "coll-1",
    "name": "Articles",
    "alias": "articles",
    "folder_type": "collection",
    "content_type": "document",
    "strict_reference": False,
    "created_at": "2026-01-10T00:00:00Z",
    "parent": None,
}

API_COLLECTION_JSON = {
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

EMPTY_LIST = {"count": 0, "next": None, "previous": None, "results": []}


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


def capturing(response: httpx.Response, store: dict) -> Callable:
    def handler(request: httpx.Request) -> httpx.Response:
        store["method"] = request.method
        store["url"] = str(request.url)
        store["path"] = request.url.path
        if request.content:
            store["body"] = json.loads(request.content.decode())
        return response

    return handler


@pytest.fixture(autouse=True)
def _reset_warned():
    _deprecation._warned.clear()
    yield
    _deprecation._warned.clear()


@pytest.fixture
def _silence_deprecations():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield


# ----- canonical Collection CRUD (async) -----


async def test_get_collection_by_path_async():
    cap: dict = {}
    client = build_async_management_client(
        capturing(httpx.Response(200, json=COLLECTION_JSON), cap)
    )
    await client.get_collection_by_path("/nested/path")
    assert cap["path"] == f"/v1/{ENV_KEY}/collections/tree/collection/"
    assert "path=%2Fnested%2Fpath" in cap["url"]


async def test_list_collection_tree_async_children_mode():
    cap: dict = {}
    client = build_async_management_client(
        capturing(httpx.Response(200, json=EMPTY_LIST), cap)
    )
    await client.list_collection_tree(key="coll-1", mode="children")
    assert "key=coll-1" in cap["url"]
    assert "mode=children" in cap["url"]


async def test_update_collection_async_puts_to_tree_item():
    cap: dict = {}
    client = build_async_management_client(
        capturing(httpx.Response(200, json=COLLECTION_JSON), cap)
    )
    await client.update_collection("coll-1", {"name": "Renamed"})
    assert cap["method"] == "PUT"
    assert cap["path"] == f"/v1/{ENV_KEY}/collections/tree/collection/"
    assert "key=coll-1" in cap["url"]


# ----- canonical API ↔ Collection association (async) -----


async def test_add_api_collection_async_all_descriptions():
    cap: dict = {}
    client = build_async_management_client(
        capturing(httpx.Response(201, json=API_COLLECTION_JSON), cap)
    )
    await client.add_api_collection(
        "my-api",
        "coll-1",
        allowed_methods=["get_one"],
        description_get_one="one",
        description_get_many="many",
        description_search="search",
        description_schema="schema",
    )
    assert cap["method"] == "POST"
    assert cap["path"] == f"/v1/{ENV_KEY}/api/my-api/collections/"
    assert cap["body"]["description_schema"] == "schema"


async def test_get_api_collection_async():
    cap: dict = {}
    client = build_async_management_client(
        capturing(httpx.Response(200, json=API_COLLECTION_JSON), cap)
    )
    await client.get_api_collection("my-api", "coll-1")
    assert cap["path"] == f"/v1/{ENV_KEY}/api/my-api/collections/coll-1/"


async def test_update_api_collection_async_descriptions():
    cap: dict = {}
    client = build_async_management_client(
        capturing(httpx.Response(200, json=API_COLLECTION_JSON), cap)
    )
    await client.update_api_collection(
        "my-api",
        "coll-1",
        allowed_methods=["get_one"],
        description_get_one="one",
        description_get_many="many",
        description_search="search",
        description_schema="schema",
    )
    assert cap["method"] == "PUT"
    assert cap["path"] == f"/v1/{ENV_KEY}/api/my-api/collections/coll-1/"


async def test_remove_api_collection_async():
    cap: dict = {}
    client = build_async_management_client(capturing(httpx.Response(204), cap))
    await client.remove_api_collection("my-api", "coll-1")
    assert cap["method"] == "DELETE"
    assert cap["path"] == f"/v1/{ENV_KEY}/api/my-api/collections/coll-1/"


# ----- canonical Collection schema versions (async) -----


async def test_list_collection_versions_async():
    cap: dict = {}
    client = build_async_management_client(
        capturing(httpx.Response(200, json=EMPTY_LIST), cap)
    )
    await client.list_collection_versions("coll-1")
    assert cap["path"] == f"/v1/{ENV_KEY}/collections/coll-1/model/versions/"


async def test_create_collection_version_async_copy_from():
    cap: dict = {}
    client = build_async_management_client(
        capturing(httpx.Response(201, json=VERSION_JSON), cap)
    )
    await client.create_collection_version("coll-1", {"name": "v2"}, copy_from="v1")
    assert cap["method"] == "POST"
    assert "copy_from=v1" in cap["url"]


async def test_get_collection_version_async_include_schema():
    cap: dict = {}
    client = build_async_management_client(
        capturing(httpx.Response(200, json=VERSION_JSON), cap)
    )
    await client.get_collection_version("coll-1", "v1", include_schema=True)
    assert "include_schema=true" in cap["url"]


async def test_update_collection_version_async():
    cap: dict = {}
    client = build_async_management_client(
        capturing(httpx.Response(200, json=VERSION_JSON), cap)
    )
    await client.update_collection_version("coll-1", "v1", {"name": "renamed"})
    assert cap["method"] == "PUT"
    assert cap["path"] == f"/v1/{ENV_KEY}/collections/coll-1/model/versions/v1/"


async def test_delete_collection_version_async():
    cap: dict = {}
    client = build_async_management_client(capturing(httpx.Response(204), cap))
    await client.delete_collection_version("coll-1", "v1")
    assert cap["method"] == "DELETE"
    assert cap["path"] == f"/v1/{ENV_KEY}/collections/coll-1/model/versions/v1/"


# ----- canonical Collection schema fields (async) -----


async def test_create_collection_field_async():
    cap: dict = {}
    client = build_async_management_client(
        capturing(httpx.Response(201, json=FIELD_JSON), cap)
    )
    await client.create_collection_field("coll-1", "v1", {"name": "title"})
    assert cap["method"] == "POST"
    assert (
        cap["path"]
        == f"/v1/{ENV_KEY}/collections/coll-1/model/versions/v1/schema/tree/"
    )


async def test_get_collection_field_async():
    cap: dict = {}
    client = build_async_management_client(
        capturing(httpx.Response(200, json=FIELD_JSON), cap)
    )
    await client.get_collection_field("coll-1", "v1", "title")
    assert "path=title" in cap["url"]


async def test_update_collection_field_async():
    cap: dict = {}
    client = build_async_management_client(
        capturing(httpx.Response(200, json=FIELD_JSON), cap)
    )
    await client.update_collection_field("coll-1", "v1", "title", {"required": True})
    assert cap["method"] == "PUT"
    assert "path=title" in cap["url"]


async def test_delete_collection_field_async():
    cap: dict = {}
    client = build_async_management_client(capturing(httpx.Response(204), cap))
    await client.delete_collection_field("coll-1", "v1", "title")
    assert cap["method"] == "DELETE"
    assert "path=title" in cap["url"]


# ----- deprecated /folders/ aliases (async) -----


async def test_list_api_folders_async_legacy_url(_silence_deprecations):
    cap: dict = {}
    client = build_async_management_client(
        capturing(httpx.Response(200, json=EMPTY_LIST), cap)
    )
    await client.list_api_folders("my-api")
    assert cap["path"] == f"/v1/{ENV_KEY}/api/my-api/folders/"


async def test_get_api_folder_async_legacy_url(_silence_deprecations):
    cap: dict = {}
    client = build_async_management_client(
        capturing(httpx.Response(200, json=API_COLLECTION_JSON), cap)
    )
    await client.get_api_folder("my-api", "coll-1")
    assert cap["path"] == f"/v1/{ENV_KEY}/api/my-api/folders/coll-1/"


async def test_remove_api_folder_async_legacy_url(_silence_deprecations):
    cap: dict = {}
    client = build_async_management_client(capturing(httpx.Response(204), cap))
    await client.remove_api_folder("my-api", "coll-1")
    assert cap["method"] == "DELETE"
    assert cap["path"] == f"/v1/{ENV_KEY}/api/my-api/folders/coll-1/"


async def test_list_folder_versions_async_legacy_url(_silence_deprecations):
    cap: dict = {}
    client = build_async_management_client(
        capturing(httpx.Response(200, json=EMPTY_LIST), cap)
    )
    await client.list_folder_versions("coll-1")
    assert cap["path"] == f"/v1/{ENV_KEY}/folders/coll-1/model/versions/"
