"""Wire-behaviour coverage for the Collection/Folder method surface (sync).

Complements test_collections_methods.py by exercising every request-building
method that the smoke tests do not touch: api-collection get/update, schema
version CRUD, schema field get/update/delete, and the deprecated /folders/
aliases for all of the above. Each test asserts the HTTP method, path and
(where relevant) body/query the SDK puts on the wire.
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
from foxnose_sdk.management.client import ManagementClient


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


def build_management_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> ManagementClient:
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


# ----- canonical API ↔ Collection association -----


def test_add_api_collection_includes_all_descriptions():
    cap: dict = {}
    client = build_management_client(
        capturing(httpx.Response(201, json=API_COLLECTION_JSON), cap)
    )
    client.add_api_collection(
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
    assert cap["body"]["folder"] == "coll-1"
    assert cap["body"]["description_get_one"] == "one"
    assert cap["body"]["description_get_many"] == "many"
    assert cap["body"]["description_search"] == "search"
    assert cap["body"]["description_schema"] == "schema"


def test_get_api_collection_hits_subpath():
    cap: dict = {}
    client = build_management_client(
        capturing(httpx.Response(200, json=API_COLLECTION_JSON), cap)
    )
    client.get_api_collection("my-api", "coll-1")
    assert cap["method"] == "GET"
    assert cap["path"] == f"/v1/{ENV_KEY}/api/my-api/collections/coll-1/"


def test_update_api_collection_puts_descriptions():
    cap: dict = {}
    client = build_management_client(
        capturing(httpx.Response(200, json=API_COLLECTION_JSON), cap)
    )
    client.update_api_collection(
        "my-api",
        "coll-1",
        allowed_methods=["get_one", "get_many"],
        description_get_one="one",
        description_get_many="many",
        description_search="search",
        description_schema="schema",
    )
    assert cap["method"] == "PUT"
    assert cap["path"] == f"/v1/{ENV_KEY}/api/my-api/collections/coll-1/"
    assert cap["body"]["allowed_methods"] == ["get_one", "get_many"]
    assert cap["body"]["description_schema"] == "schema"


# ----- canonical Collection schema versions -----


def test_list_collection_versions_hits_versions_base():
    cap: dict = {}
    client = build_management_client(
        capturing(httpx.Response(200, json=EMPTY_LIST), cap)
    )
    client.list_collection_versions("coll-1")
    assert cap["method"] == "GET"
    assert cap["path"] == f"/v1/{ENV_KEY}/collections/coll-1/model/versions/"


def test_create_collection_version_passes_copy_from():
    cap: dict = {}
    client = build_management_client(
        capturing(httpx.Response(201, json=VERSION_JSON), cap)
    )
    client.create_collection_version("coll-1", {"name": "v2"}, copy_from="v1")
    assert cap["method"] == "POST"
    assert cap["path"] == f"/v1/{ENV_KEY}/collections/coll-1/model/versions/"
    assert "copy_from=v1" in cap["url"]
    assert cap["body"]["name"] == "v2"


def test_get_collection_version_include_schema_query():
    cap: dict = {}
    client = build_management_client(
        capturing(httpx.Response(200, json=VERSION_JSON), cap)
    )
    client.get_collection_version("coll-1", "v1", include_schema=True)
    assert cap["method"] == "GET"
    assert cap["path"] == f"/v1/{ENV_KEY}/collections/coll-1/model/versions/v1/"
    assert "include_schema=true" in cap["url"]


def test_update_collection_version_puts_payload():
    cap: dict = {}
    client = build_management_client(
        capturing(httpx.Response(200, json=VERSION_JSON), cap)
    )
    client.update_collection_version("coll-1", "v1", {"name": "renamed"})
    assert cap["method"] == "PUT"
    assert cap["path"] == f"/v1/{ENV_KEY}/collections/coll-1/model/versions/v1/"
    assert cap["body"]["name"] == "renamed"


def test_delete_collection_version_deletes():
    cap: dict = {}
    client = build_management_client(capturing(httpx.Response(204), cap))
    client.delete_collection_version("coll-1", "v1")
    assert cap["method"] == "DELETE"
    assert cap["path"] == f"/v1/{ENV_KEY}/collections/coll-1/model/versions/v1/"


# ----- canonical Collection schema fields -----


def test_get_collection_field_query_path():
    cap: dict = {}
    client = build_management_client(
        capturing(httpx.Response(200, json=FIELD_JSON), cap)
    )
    client.get_collection_field("coll-1", "v1", "title")
    assert cap["method"] == "GET"
    assert (
        cap["path"]
        == f"/v1/{ENV_KEY}/collections/coll-1/model/versions/v1/schema/tree/field/"
    )
    assert "path=title" in cap["url"]


def test_update_collection_field_puts_payload():
    cap: dict = {}
    client = build_management_client(
        capturing(httpx.Response(200, json=FIELD_JSON), cap)
    )
    client.update_collection_field("coll-1", "v1", "title", {"required": True})
    assert cap["method"] == "PUT"
    assert "path=title" in cap["url"]
    assert cap["body"]["required"] is True


def test_delete_collection_field_deletes_with_path():
    cap: dict = {}
    client = build_management_client(capturing(httpx.Response(204), cap))
    client.delete_collection_field("coll-1", "v1", "title")
    assert cap["method"] == "DELETE"
    assert "path=title" in cap["url"]


# ----- deprecated /folders/ aliases: association -----


def test_list_api_folders_hits_legacy_url(_silence_deprecations):
    cap: dict = {}
    client = build_management_client(
        capturing(httpx.Response(200, json=EMPTY_LIST), cap)
    )
    client.list_api_folders("my-api")
    assert cap["path"] == f"/v1/{ENV_KEY}/api/my-api/folders/"


def test_get_api_folder_hits_legacy_url(_silence_deprecations):
    cap: dict = {}
    client = build_management_client(
        capturing(httpx.Response(200, json=API_COLLECTION_JSON), cap)
    )
    client.get_api_folder("my-api", "coll-1")
    assert cap["path"] == f"/v1/{ENV_KEY}/api/my-api/folders/coll-1/"


def test_remove_api_folder_deletes_legacy_url(_silence_deprecations):
    cap: dict = {}
    client = build_management_client(capturing(httpx.Response(204), cap))
    client.remove_api_folder("my-api", "coll-1")
    assert cap["method"] == "DELETE"
    assert cap["path"] == f"/v1/{ENV_KEY}/api/my-api/folders/coll-1/"


# ----- deprecated /folders/ aliases: collection CRUD -----


def test_get_folder_alias(_silence_deprecations):
    cap: dict = {}
    client = build_management_client(
        capturing(httpx.Response(200, json=COLLECTION_JSON), cap)
    )
    client.get_folder("coll-1")
    assert cap["path"] == f"/v1/{ENV_KEY}/folders/tree/folder/"
    assert "key=coll-1" in cap["url"]


def test_update_folder_alias(_silence_deprecations):
    cap: dict = {}
    client = build_management_client(
        capturing(httpx.Response(200, json=COLLECTION_JSON), cap)
    )
    client.update_folder("coll-1", {"name": "Renamed"})
    assert cap["method"] == "PUT"
    assert cap["path"] == f"/v1/{ENV_KEY}/folders/tree/folder/"
    assert cap["body"]["name"] == "Renamed"


def test_delete_folder_alias(_silence_deprecations):
    cap: dict = {}
    client = build_management_client(capturing(httpx.Response(204), cap))
    client.delete_folder("coll-1")
    assert cap["method"] == "DELETE"
    assert cap["path"] == f"/v1/{ENV_KEY}/folders/tree/folder/"


# ----- deprecated /folders/ aliases: schema versions -----


def test_list_folder_versions_alias(_silence_deprecations):
    cap: dict = {}
    client = build_management_client(
        capturing(httpx.Response(200, json=EMPTY_LIST), cap)
    )
    client.list_folder_versions("coll-1")
    assert cap["path"] == f"/v1/{ENV_KEY}/folders/coll-1/model/versions/"


def test_get_folder_version_alias(_silence_deprecations):
    cap: dict = {}
    client = build_management_client(
        capturing(httpx.Response(200, json=VERSION_JSON), cap)
    )
    client.get_folder_version("coll-1", "v1", include_schema=False)
    assert cap["path"] == f"/v1/{ENV_KEY}/folders/coll-1/model/versions/v1/"
    assert "include_schema=false" in cap["url"]


def test_update_folder_version_alias(_silence_deprecations):
    cap: dict = {}
    client = build_management_client(
        capturing(httpx.Response(200, json=VERSION_JSON), cap)
    )
    client.update_folder_version("coll-1", "v1", {"name": "x"})
    assert cap["method"] == "PUT"
    assert cap["path"] == f"/v1/{ENV_KEY}/folders/coll-1/model/versions/v1/"


def test_delete_folder_version_alias(_silence_deprecations):
    cap: dict = {}
    client = build_management_client(capturing(httpx.Response(204), cap))
    client.delete_folder_version("coll-1", "v1")
    assert cap["method"] == "DELETE"
    assert cap["path"] == f"/v1/{ENV_KEY}/folders/coll-1/model/versions/v1/"


# ----- deprecated /folders/ aliases: schema fields -----


def test_get_folder_field_alias(_silence_deprecations):
    cap: dict = {}
    client = build_management_client(
        capturing(httpx.Response(200, json=FIELD_JSON), cap)
    )
    client.get_folder_field("coll-1", "v1", "title")
    assert (
        cap["path"]
        == f"/v1/{ENV_KEY}/folders/coll-1/model/versions/v1/schema/tree/field/"
    )
    assert "path=title" in cap["url"]


def test_update_folder_field_alias(_silence_deprecations):
    cap: dict = {}
    client = build_management_client(
        capturing(httpx.Response(200, json=FIELD_JSON), cap)
    )
    client.update_folder_field("coll-1", "v1", "title", {"required": True})
    assert cap["method"] == "PUT"
    assert "path=title" in cap["url"]


def test_delete_folder_field_alias(_silence_deprecations):
    cap: dict = {}
    client = build_management_client(capturing(httpx.Response(204), cap))
    client.delete_folder_field("coll-1", "v1", "title")
    assert cap["method"] == "DELETE"
    assert "path=title" in cap["url"]
