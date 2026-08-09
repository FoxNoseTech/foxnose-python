"""Smoke tests for the Collection method surface.

Covers the canonical Collection methods (list/get/create/update/delete +
api-association + versions + fields) and the one-shot DeprecationWarning
emitted by the corresponding Folder-named aliases.

Verifies wire-compat: canonical methods hit /v1/{env}/collections/...
while deprecated folder methods still hit /v1/{env}/folders/...
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
from foxnose_sdk.management.client import ManagementClient


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


@pytest.fixture(autouse=True)
def _reset_warned():
    _deprecation._warned.clear()
    yield
    _deprecation._warned.clear()


# ----- canonical Collection CRUD -----


def test_list_collections_hits_collections_tree():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(
            200,
            json={"count": 0, "next": None, "previous": None, "results": []},
        )

    client = build_management_client(handler)
    result = client.list_collections()
    assert isinstance(result, CollectionList)
    assert captured["path"] == f"/v1/{ENV_KEY}/collections/tree/"


def test_get_collection_passes_key_query_param():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=FOLDER_JSON)

    client = build_management_client(handler)
    coll = client.get_collection("coll-1")
    assert isinstance(coll, CollectionSummary)
    assert f"/v1/{ENV_KEY}/collections/tree/collection/" in captured["url"]
    assert "key=coll-1" in captured["url"]


def test_get_collection_by_path():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=FOLDER_JSON)

    client = build_management_client(handler)
    client.get_collection_by_path("/nested/path")
    assert "path=%2Fnested%2Fpath" in captured["url"]


def test_list_collection_tree_children_mode():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={"count": 0, "next": None, "previous": None, "results": []},
        )

    client = build_management_client(handler)
    client.list_collection_tree(key="coll-1", mode="children")
    assert "key=coll-1" in captured["url"]
    assert "mode=children" in captured["url"]


def test_create_collection_posts_to_collections_tree():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["method"] = request.method
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(201, json=FOLDER_JSON)

    client = build_management_client(handler)
    coll = client.create_collection(
        {
            "name": "Articles",
            "alias": "articles",
            "folder_type": "collection",
            "content_type": "document",
        }
    )
    assert coll.key == "coll-1"
    assert captured["method"] == "POST"
    assert captured["path"] == f"/v1/{ENV_KEY}/collections/tree/"
    # Wire field name folder_type is preserved.
    assert captured["body"]["folder_type"] == "collection"


def test_update_collection_puts_to_tree_item():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        return httpx.Response(200, json=FOLDER_JSON)

    client = build_management_client(handler)
    client.update_collection("coll-1", {"name": "Renamed"})
    assert captured["method"] == "PUT"
    assert f"/v1/{ENV_KEY}/collections/tree/collection/" in captured["url"]
    assert "key=coll-1" in captured["url"]


def test_delete_collection_deletes_at_tree_item():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        return httpx.Response(204)

    client = build_management_client(handler)
    client.delete_collection("coll-1")
    assert captured["method"] == "DELETE"
    assert f"/v1/{ENV_KEY}/collections/tree/collection/" in captured["url"]


# ----- canonical API ↔ Collection association -----


def test_add_api_collection_posts_with_folder_wire_field():
    """Wire-compat: POST body uses the legacy `folder` field name."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(201, json=API_FOLDER_JSON)

    client = build_management_client(handler)
    res = client.add_api_collection("my-api", "coll-1", allowed_methods=["get_one"])
    assert isinstance(res, APICollectionSummary)
    assert captured["path"] == f"/v1/{ENV_KEY}/api/my-api/collections/"
    assert captured["body"]["folder"] == "coll-1"


def test_list_api_collections_returns_list_model():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"count": 0, "next": None, "previous": None, "results": []},
        )

    client = build_management_client(handler)
    res = client.list_api_collections("my-api")
    assert isinstance(res, APICollectionList)


def test_remove_api_collection_hits_collection_subpath():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        return httpx.Response(204)

    client = build_management_client(handler)
    client.remove_api_collection("my-api", "coll-1")
    assert captured["method"] == "DELETE"
    assert f"/v1/{ENV_KEY}/api/my-api/collections/coll-1/" in captured["url"]


# ----- canonical Collection schema versions + fields -----


def test_publish_collection_version_hits_publish_subpath():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        return httpx.Response(
            200, json={**VERSION_JSON, "published_at": "2026-01-11T00:00:00Z"}
        )

    client = build_management_client(handler)
    client.publish_collection_version("coll-1", "v1")
    assert captured["method"] == "POST"
    assert (
        f"/v1/{ENV_KEY}/collections/coll-1/model/versions/v1/publish/"
        in captured["url"]
    )


def test_list_collection_fields_hits_collection_schema_tree():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(
            200,
            json={"count": 0, "next": None, "previous": None, "results": []},
        )

    client = build_management_client(handler)
    client.list_collection_fields("coll-1", "v1")
    assert (
        captured["path"]
        == f"/v1/{ENV_KEY}/collections/coll-1/model/versions/v1/schema/tree/"
    )


def test_create_collection_field_posts_payload():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(201, json=FIELD_JSON)

    client = build_management_client(handler)
    client.create_collection_field("coll-1", "v1", {"name": "title", "type": "string"})
    assert captured["body"]["name"] == "title"


# ----- deprecation warnings -----


def test_list_folders_emits_deprecation_warning():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"count": 0, "next": None, "previous": None, "results": []},
        )

    client = build_management_client(handler)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        client.list_folders()
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(deprecations) == 1
    msg = str(deprecations[0].message)
    assert "list_folders" in msg
    assert "list_collections" in msg


def test_list_folders_still_hits_legacy_folders_url():
    """Deprecated aliases keep their original wire behaviour (hit /folders/)."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(
            200,
            json={"count": 0, "next": None, "previous": None, "results": []},
        )

    client = build_management_client(handler)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        client.list_folders()
    assert captured["path"] == f"/v1/{ENV_KEY}/folders/tree/"


def test_add_api_folder_emits_deprecation_warning():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json=API_FOLDER_JSON)

    client = build_management_client(handler)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        client.add_api_folder("my-api", "coll-1", allowed_methods=["get_one"])
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert deprecations
    assert "add_api_folder" in str(deprecations[0].message)


def test_publish_folder_version_emits_deprecation_warning():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={**VERSION_JSON, "published_at": "2026-01-11T00:00:00Z"}
        )

    client = build_management_client(handler)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        client.publish_folder_version("coll-1", "v1")
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert deprecations
    assert "publish_folder_version" in str(deprecations[0].message)


def test_list_folder_fields_emits_deprecation_warning():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"count": 0, "next": None, "previous": None, "results": []},
        )

    client = build_management_client(handler)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        client.list_folder_fields("coll-1", "v1")
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert deprecations
    assert "list_folder_fields" in str(deprecations[0].message)


def test_deprecation_warning_once_per_process_per_method():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"count": 0, "next": None, "previous": None, "results": []},
        )

    client = build_management_client(handler)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        client.list_folders()
        client.list_folders()
        client.list_folders()
    deprecations = [
        w
        for w in caught
        if issubclass(w.category, DeprecationWarning)
        and "list_folders" in str(w.message)
    ]
    assert len(deprecations) == 1
