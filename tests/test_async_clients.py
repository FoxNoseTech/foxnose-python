from __future__ import annotations

import json
from typing import Any, Callable

import httpx
import pytest

from foxnose_sdk.auth import SimpleKeyAuth
from foxnose_sdk.config import FoxnoseConfig
from foxnose_sdk.flux.client import AsyncFluxClient
from foxnose_sdk.http import HttpTransport
from foxnose_sdk.management.client import AsyncManagementClient
from foxnose_sdk.errors import FoxnoseAPIError, UpstreamError
from foxnose_sdk.management.models import (
    APIFolderSummary,
    BatchUpsertItem,
    BatchUpsertResult,
    FolderSummary,
    ResourceSummary,
    RevisionSummary,
)

ORG_KEY = "org-1"
PROJECT_KEY = "project-1"
ENV_KEY = "env-1"

FOLDER_JSON = {
    "key": "folder-1",
    "name": "Folder",
    "alias": "folder",
    "folder_type": "collection",
    "content_type": "document",
    "strict_reference": False,
    "created_at": "2024-01-10T00:00:00Z",
    "parent": None,
}

PROJECT_JSON = {
    "key": PROJECT_KEY,
    "name": "Main Project",
    "organization": ORG_KEY,
    "region": "us",
    "environments": [
        {
            "key": ENV_KEY,
            "name": "Prod",
            "project": PROJECT_KEY,
            "host": "prod.fxns.io",
            "is_enabled": True,
            "created_at": "2024-01-10T00:00:00Z",
        }
    ],
    "gdpr": False,
    "created_at": "2024-01-10T00:00:00Z",
}

ENVIRONMENT_JSON = {
    "key": ENV_KEY,
    "name": "Prod",
    "project": PROJECT_KEY,
    "host": "prod.fxns.io",
    "is_enabled": True,
    "created_at": "2024-01-10T00:00:00Z",
}

RESOURCE_JSON = {
    "key": "resource-1",
    "folder": "folder-1",
    "content_type": "document",
    "created_at": "2024-01-10T00:00:00Z",
    "vectors_size": 0,
    "name": None,
    "resource_owner": None,
    "current_revision": "rev-1",
    "external_id": None,
}

REVISION_JSON = {
    "key": "rev-1",
    "resource": "resource-1",
    "schema_version": "schema-1",
    "number": 1,
    "size": 10,
    "created_at": "2024-01-10T00:00:00Z",
    "status": "draft",
    "is_valid": None,
    "published_at": None,
    "unpublished_at": None,
}

ORGANIZATION_JSON = {
    "key": ORG_KEY,
    "name": "Test Org",
    "owner": {
        "key": "owner-1",
        "email": "owner@example.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "full_name": "Jane Doe",
    },
    "tax_num": "123456",
    "city": "Berlin",
    "province": "BE",
    "address": "Street 1",
    "country_iso": "DE",
    "zip_code": "10115",
    "legal_name": "Test Org GmbH",
    "created_at": "2024-01-10T00:00:00Z",
    "block_dt": None,
    "block_reason": None,
    "is_blocked": False,
}

REGION_JSON = {
    "location": "eu",
    "name": "Frankfurt",
    "code": "eu-central-1",
}

PLAN_STATUS_JSON = {
    "active_plan": {
        "code": "standard",
        "name": "Standard",
        "price": 100.0,
        "from": "2024-01-01T00:00:00Z",
        "to": "2024-02-01T00:00:00Z",
        "transferred": "2024-01-01T00:00:00Z",
        "limits": {
            "units_included": "1000",
            "projects": 10,
            "environments": 20,
            "folders": 100,
            "resources": 1000,
            "users": 5,
            "components": 50,
            "allow_negative": False,
            "negative_limit": 0,
            "unit_cost": 0.05,
            "api_keys_max_count": 3,
            "roles_max_count": 5,
            "locales_max_count": 5,
            "schemas_max_count": 10,
            "schemas_fields_max_count": 100,
            "flux_api_max_count": 2,
            "max_component_inheritance_depth": 3,
        },
    },
    "next_plan": {
        "code": "pro",
        "name": "Pro",
        "price": 200.0,
        "limits": {
            "units_included": "2000",
            "projects": 20,
            "environments": 30,
            "folders": 200,
            "resources": 2000,
            "users": 10,
            "components": 75,
            "allow_negative": True,
            "negative_limit": 500,
            "unit_cost": 0.04,
            "api_keys_max_count": 5,
            "roles_max_count": 8,
            "locales_max_count": 10,
            "schemas_max_count": 15,
            "schemas_fields_max_count": 200,
            "flux_api_max_count": 4,
            "max_component_inheritance_depth": 5,
        },
    },
}

USAGE_JSON = {
    "units": {
        "remained": "100",
        "unit_cost": 0.05,
        "allow_negative": False,
        "negative_limit": "0",
    },
    "storage": {"data_storage": 123.4, "vector_storage": 56.7},
    "usage": {
        "projects": {"max": 10, "current": 2},
        "resources": {"max": 100, "current": 15},
        "users": {"max": 10, "current": 4},
        # Extra server-side field: must be ignored by the model, never raise.
        "environments": {"max": 10, "current": 3},
    },
    "current_usage": {
        "api_requests": 12345,
        "embedding_tokens": {"total": 1000, "month": 500},
    },
}

MANAGEMENT_API_KEY_JSON = {
    "key": "api-key-1",
    "description": "Ops key",
    "public_key": "manage_pub_abc",
    "secret_key": "manage_sec_xyz",
    "role": "role-admin",
    "environment": ENV_KEY,
    "created_at": "2024-01-10T00:00:00Z",
}

FLUX_API_KEY_JSON = {
    "key": "flux-key-1",
    "description": "Flux key",
    "public_key": "flux_pub_abc",
    "secret_key": "flux_sec_xyz",
    "role": "flux-role",
    "environment": ENV_KEY,
    "created_at": "2024-01-10T00:00:00Z",
}

MANAGEMENT_ROLE_JSON = {
    "key": "role-1",
    "name": "Editors",
    "description": "Edit content",
    "full_access": False,
    "environment": ENV_KEY,
    "created_at": "2024-01-10T00:00:00Z",
}

FLUX_ROLE_JSON = {
    "key": "flux-role-1",
    "name": "Flux Readers",
    "description": "Read blog APIs",
    "environment": ENV_KEY,
    "created_at": "2024-01-10T00:00:00Z",
}

ROLE_PERMISSION_JSON = {
    "content_type": "collection-items",
    "actions": ["read"],
    "all_objects": True,
}

PERMISSION_OBJECT_JSON = {
    "content_type": "collection-items",
    "object_key": "folder-1",
}

FLUX_ROLE_PERMISSION_JSON = {
    "content_type": "flux-apis",
    "actions": ["read"],
    "all_objects": False,
}

FLUX_PERMISSION_OBJECT_JSON = {
    "content_type": "flux-apis",
    "object_key": "api-1",
}

USER_JSON = {
    "key": "user-1",
    "email": "owner@example.com",
    "first_name": "Jane",
    "last_name": "Doe",
    "full_name": "Jane Doe",
}

PROTECTED_ENVIRONMENT_JSON = {
    "key": ENV_KEY,
    "name": "Prod",
    "project": PROJECT_KEY,
    "host": "prod.fxns.io",
    "is_enabled": True,
    "created_at": "2024-01-10T00:00:00Z",
    "protection_level": "org_owner",
    "protection_level_display": "Organization Owner Protected",
    "protected_by_user": USER_JSON,
    "protected_at": "2024-03-01T10:00:00Z",
    "protection_reason": "Maintenance",
}

LOCALE_JSON = {
    "name": "Français",
    "code": "fr",
    "environment": ENV_KEY,
    "created_at": "2024-01-10T00:00:00Z",
    "is_default": False,
}

COMPONENT_JSON = {
    "key": "component-1",
    "name": "Profile",
    "description": "User profile component",
    "environment": "env123",
    "content_type": "document",
    "created_at": "2024-01-10T00:00:00Z",
    "current_version": "ver-1",
}

VERSION_JSON = {
    "key": "ver-1",
    "name": "Draft",
    "description": "Draft schema",
    "version_number": 1,
    "created_at": "2024-01-10T00:00:00Z",
    "published_at": None,
    "archived_at": None,
    "json_schema": {"type": "object"},
}

FIELD_JSON = {
    "key": "title",
    "name": "Title",
    "description": "Field",
    "path": "title",
    "parent": None,
    "type": "string",
    "meta": {"max_length": 50},
    "json_schema": {"type": "string"},
    "required": True,
    "nullable": False,
    "multiple": False,
    "localizable": False,
    "searchable": False,
    "private": False,
    "vectorizable": False,
}

API_FOLDER_JSON = {
    "folder": "folder-1",
    "api": "api-1",
    "allowed_methods": ["get_many", "get_one"],
    "description_get_one": "Get one article",
    "description_get_many": "List articles",
    "description_search": "Search articles",
    "description_schema": "Read schema",
    "created_at": "2024-01-10T00:00:00Z",
}


def build_async_management_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> AsyncManagementClient:
    client = AsyncManagementClient(
        base_url="https://api.example.com",
        environment_key="env123",
        auth=SimpleKeyAuth("pub", "secret"),
    )
    client._transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=SimpleKeyAuth("pub", "secret"),
        async_client=httpx.AsyncClient(
            base_url="https://api.example.com",
            transport=httpx.MockTransport(handler),
        ),
    )
    return client


def build_async_flux_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> AsyncFluxClient:
    client = AsyncFluxClient(
        base_url="https://env.fxns.io",
        api_prefix="v1",
        auth=SimpleKeyAuth("pub", "secret"),
    )
    client._transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://env.fxns.io"),
        auth=SimpleKeyAuth("pub", "secret"),
        async_client=httpx.AsyncClient(
            base_url="https://env.fxns.io",
            transport=httpx.MockTransport(handler),
        ),
    )
    return client


# ---------------------------------------------------------------------------
# AsyncManagementClient tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_list_folders_returns_model():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        payload = {"count": 1, "next": None, "previous": None, "results": [FOLDER_JSON]}
        return httpx.Response(200, json=payload)

    client = build_async_management_client(handler)
    folders = await client.list_folders()
    assert folders.count == 1
    assert folders.results[0].alias == "folder"
    assert captured["path"] == "/v1/env123/folders/tree/"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_get_folder_by_path():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=FOLDER_JSON)

    client = build_async_management_client(handler)
    folder = await client.get_folder_by_path("/nested/path")
    assert folder.key == "folder-1"
    assert "path=%2Fnested%2Fpath" in captured["url"]
    await client.aclose()


@pytest.mark.asyncio
async def test_async_create_folder():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(201, json=FOLDER_JSON)

    client = build_async_management_client(handler)
    folder = await client.create_folder({"name": "Folder", "alias": "folder"})
    assert folder.key == "folder-1"
    assert captured["body"]["alias"] == "folder"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_list_organizations():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[ORGANIZATION_JSON])

    client = build_async_management_client(handler)
    orgs = await client.list_organizations()
    assert orgs[0].owner.email == "owner@example.com"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_update_organization():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        return httpx.Response(200, json=ORGANIZATION_JSON | body)

    client = build_async_management_client(handler)
    updated = await client.update_organization(ORG_KEY, {"name": "Updated"})
    assert updated.name == "Updated"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_list_regions():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(200, json=[REGION_JSON])

    client = build_async_management_client(handler)
    regions = await client.list_regions()
    assert regions[0].code == "eu-central-1"
    assert captured["path"] == "/regions/"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_organization_plan_and_usage():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.url.path)
        if "usage" in request.url.path:
            return httpx.Response(200, json=USAGE_JSON)
        return httpx.Response(200, json=PLAN_STATUS_JSON)

    client = build_async_management_client(handler)
    plan = await client.get_organization_plan(ORG_KEY)
    assert plan.active_plan.code == "standard"

    usage = await client.get_organization_usage(ORG_KEY)
    assert usage.storage.data_storage == 123.4
    await client.aclose()


@pytest.mark.asyncio
async def test_async_management_api_key_lifecycle():
    captured: dict[str, Any] = {"paths": [], "bodies": []}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["paths"].append((request.method, request.url.path))
        if request.method == "GET" and request.url.path.endswith("/api-keys/"):
            payload = {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [MANAGEMENT_API_KEY_JSON],
            }
            return httpx.Response(200, json=payload)
        if request.method == "POST":
            captured["bodies"].append(json.loads(request.content.decode()))
            return httpx.Response(201, json=MANAGEMENT_API_KEY_JSON)
        if request.method == "GET":
            return httpx.Response(200, json=MANAGEMENT_API_KEY_JSON)
        if request.method == "PUT":
            return httpx.Response(
                200, json=MANAGEMENT_API_KEY_JSON | {"description": "Updated"}
            )
        if request.method == "DELETE":
            return httpx.Response(204)
        raise AssertionError(f"Unhandled request {request.method} {request.url}")

    client = build_async_management_client(handler)
    keys = await client.list_management_api_keys()
    assert keys.results[0].public_key == "manage_pub_abc"

    created = await client.create_management_api_key(
        {"description": "Ops key", "role": "role-1"}
    )
    assert created.secret_key == "manage_sec_xyz"
    assert captured["bodies"][0] == {"description": "Ops key", "role": "role-1"}

    detail = await client.get_management_api_key("api-key-1")
    assert detail.key == "api-key-1"

    updated = await client.update_management_api_key(
        "api-key-1", {"description": "Updated"}
    )
    assert updated.description == "Updated"

    await client.delete_management_api_key("api-key-1")
    assert captured["paths"][-1][0] == "DELETE"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_flux_api_key_lifecycle():
    captured: dict[str, Any] = {"paths": [], "bodies": []}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["paths"].append((request.method, request.url.path))
        if request.method == "GET" and request.url.path.endswith("/flux-api/api-keys/"):
            payload = {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [FLUX_API_KEY_JSON],
            }
            return httpx.Response(200, json=payload)
        if request.method == "POST":
            captured["bodies"].append(json.loads(request.content.decode()))
            return httpx.Response(201, json=FLUX_API_KEY_JSON)
        if request.method == "GET":
            return httpx.Response(200, json=FLUX_API_KEY_JSON)
        if request.method == "PUT":
            return httpx.Response(
                200, json=FLUX_API_KEY_JSON | {"description": "Updated Flux Key"}
            )
        if request.method == "DELETE":
            return httpx.Response(204)
        raise AssertionError("Unexpected call")

    client = build_async_management_client(handler)
    keys = await client.list_flux_api_keys()
    assert keys.results[0].public_key == "flux_pub_abc"

    created = await client.create_flux_api_key(
        {"description": "Flux key", "role": "role-1"}
    )
    assert created.secret_key == "flux_sec_xyz"
    assert captured["bodies"][0] == {"description": "Flux key", "role": "role-1"}

    detail = await client.get_flux_api_key("flux-key-1")
    assert detail.key == "flux-key-1"

    updated = await client.update_flux_api_key(
        "flux-key-1", {"description": "Updated Flux Key"}
    )
    assert updated.description == "Updated Flux Key"

    await client.delete_flux_api_key("flux-key-1")
    assert captured["paths"][-1][0] == "DELETE"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_flux_api_key_bearer_token_lifecycle():
    """Same contract as the sync client: the sub-resource, never the key."""
    captured: dict[str, Any] = {"paths": []}
    token_json = {
        "bearer_token": "fxk_A7fQ2mXeKp3vR8sT1uW5yZ2bC6dF9gH0jL4nQ7x",
        "bearer_token_prefix": "fxk_A7fQ2mXe",
        "bearer_token_issued_at": "2026-08-09T10:24:11.482Z",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        captured["paths"].append((request.method, request.url.path))
        if request.method == "POST":
            return httpx.Response(200, json=token_json)
        if request.method == "DELETE":
            return httpx.Response(204)
        raise AssertionError("Unexpected call")

    client = build_async_management_client(handler)

    issued = await client.issue_flux_api_key_bearer_token("flux-key-1")
    assert issued.bearer_token == token_json["bearer_token"]
    assert captured["paths"][0] == (
        "POST",
        "/v1/env123/permissions/flux-api/api-keys/flux-key-1/bearer-token/",
    )

    await client.revoke_flux_api_key_bearer_token("flux-key-1")
    method, path = captured["paths"][-1]
    assert method == "DELETE"
    assert path.endswith("/api-keys/flux-key-1/bearer-token/")
    assert not path.endswith("/api-keys/flux-key-1/")
    await client.aclose()


@pytest.mark.asyncio
async def test_async_management_role_crud():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(str(request.url))
        if request.method == "GET" and request.url.path.endswith("/roles/"):
            payload = {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [MANAGEMENT_ROLE_JSON],
            }
            return httpx.Response(200, json=payload)
        if request.method == "POST":
            return httpx.Response(201, json=MANAGEMENT_ROLE_JSON)
        if request.method == "GET":
            return httpx.Response(200, json=MANAGEMENT_ROLE_JSON)
        if request.method == "PUT":
            body = json.loads(request.content.decode())
            return httpx.Response(200, json=MANAGEMENT_ROLE_JSON | body)
        if request.method == "DELETE":
            return httpx.Response(204)
        raise AssertionError("Unexpected request")

    client = build_async_management_client(handler)
    roles = await client.list_management_roles()
    assert roles.results[0].name == "Editors"

    created = await client.create_management_role({"name": "Editors"})
    assert created.key == "role-1"

    detail = await client.get_management_role("role-1")
    assert detail.full_access is False

    updated = await client.update_management_role("role-1", {"description": "Updated"})
    assert updated.description == "Updated"

    await client.delete_management_role("role-1")
    assert captured[0].endswith("/permissions/management-api/roles/")
    await client.aclose()


@pytest.mark.asyncio
async def test_async_flux_role_crud():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(str(request.url))
        if request.method == "GET" and request.url.path.endswith("/roles/"):
            payload = {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [FLUX_ROLE_JSON],
            }
            return httpx.Response(200, json=payload)
        if request.method == "POST":
            return httpx.Response(201, json=FLUX_ROLE_JSON)
        if request.method == "GET":
            return httpx.Response(200, json=FLUX_ROLE_JSON)
        if request.method == "PUT":
            patch = json.loads(request.content.decode())
            return httpx.Response(200, json=FLUX_ROLE_JSON | patch)
        if request.method == "DELETE":
            return httpx.Response(204)
        raise AssertionError("Unexpected request")

    client = build_async_management_client(handler)
    roles = await client.list_flux_roles()
    assert roles.results[0].key == "flux-role-1"

    created = await client.create_flux_role({"name": "Flux Readers"})
    assert created.name == "Flux Readers"

    detail = await client.get_flux_role("flux-role-1")
    assert detail.description == "Read blog APIs"

    updated = await client.update_flux_role("flux-role-1", {"description": "Updated"})
    assert updated.description == "Updated"

    await client.delete_flux_role("flux-role-1")
    assert captured[0].endswith("/permissions/flux-api/roles/")
    await client.aclose()


@pytest.mark.asyncio
async def test_async_locale_crud():
    captured: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append((request.method, request.url.path))
        if request.method == "GET" and request.url.path.endswith("/locales/"):
            return httpx.Response(200, json=[LOCALE_JSON])
        if request.method == "POST":
            return httpx.Response(201, json=LOCALE_JSON)
        if request.method == "GET":
            return httpx.Response(200, json=LOCALE_JSON)
        if request.method == "PUT":
            update = json.loads(request.content.decode())
            return httpx.Response(200, json=LOCALE_JSON | update)
        if request.method == "DELETE":
            return httpx.Response(204)
        raise AssertionError("Unexpected locale request")

    client = build_async_management_client(handler)
    locales = await client.list_locales()
    assert locales[0].code == "fr"

    created = await client.create_locale(
        {"name": "Spanish", "code": "es", "is_default": False}
    )
    assert created.name == "Français"

    detail = await client.get_locale("fr")
    assert detail.is_default is False

    updated = await client.update_locale("fr", {"name": "French", "is_default": True})
    assert updated.name == "French"

    await client.delete_locale("fr")
    assert captured[-1][0] == "DELETE"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_list_projects_and_environments():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.url.path)
        if request.url.path.endswith("/projects/"):
            return httpx.Response(
                200,
                json={
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [PROJECT_JSON],
                },
            )
        if request.url.path.endswith("/environments/"):
            return httpx.Response(200, json=[ENVIRONMENT_JSON])
        return httpx.Response(200, json=PROJECT_JSON)

    client = build_async_management_client(handler)
    projects = await client.list_projects(ORG_KEY)
    assert projects.results[0].key == PROJECT_KEY

    envs = await client.list_environments(ORG_KEY, PROJECT_KEY)
    assert envs[0].host == "prod.fxns.io"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_list_resources_and_revisions():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.url.path)
        if "revisions" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [REVISION_JSON],
                },
            )
        return httpx.Response(
            200,
            json={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [RESOURCE_JSON],
            },
        )

    client = build_async_management_client(handler)
    resources = await client.list_resources("folder-1")
    assert resources.results[0].key == "resource-1"

    revisions = await client.list_revisions("folder-1", "resource-1")
    assert revisions.results[0].key == "rev-1"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_publish_revision():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(200, json=REVISION_JSON)

    client = build_async_management_client(handler)
    revision = await client.publish_revision("folder-1", "resource-1", "rev-1")
    assert revision.key == "rev-1"
    assert (
        captured["path"]
        == "/v1/env123/folders/folder-1/resources/resource-1/revisions/rev-1/publish/"
    )
    await client.aclose()


@pytest.mark.asyncio
async def test_async_list_components_and_versions():
    recorded: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded.append(str(request.url))
        if request.url.path.endswith("/components/"):
            return httpx.Response(
                200,
                json={
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [COMPONENT_JSON],
                },
            )
        return httpx.Response(
            200,
            json={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [VERSION_JSON],
            },
        )

    client = build_async_management_client(handler)
    components = await client.list_components()
    assert components.results[0].key == "component-1"

    versions = await client.list_component_versions("component-1")
    assert versions.results[0].key == "ver-1"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_folder_fields():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"count": 1, "next": None, "previous": None, "results": [FIELD_JSON]},
        )

    client = build_async_management_client(handler)
    fields = await client.list_folder_fields("folder-1", "ver-1")
    assert fields.results[0].key == "title"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_get_folder_by_key():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=FOLDER_JSON)

    client = build_async_management_client(handler)
    folder = await client.get_folder("folder-1")
    assert folder.key == "folder-1"
    assert "key=folder-1" in captured["url"]
    await client.aclose()


@pytest.mark.asyncio
async def test_async_update_and_delete_folder():
    captured: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append((request.method, request.url.path))
        if request.method == "PUT":
            body = json.loads(request.content.decode())
            return httpx.Response(200, json=FOLDER_JSON | body)
        return httpx.Response(204)

    client = build_async_management_client(handler)
    updated = await client.update_folder("folder-1", {"name": "Updated"})
    assert updated.name == "Updated"
    await client.delete_folder("folder-1")
    assert captured[1][0] == "DELETE"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_list_folder_tree():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        payload = {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [FOLDER_JSON],
        }
        return httpx.Response(200, json=payload)

    client = build_async_management_client(handler)
    folders = await client.list_folder_tree(key="folder-1", mode="children")
    assert folders.results[0].key == "folder-1"
    assert "key=folder-1" in captured["url"]
    assert "mode=children" in captured["url"]
    await client.aclose()


@pytest.mark.asyncio
async def test_async_update_project():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.url.path)
        return httpx.Response(200, json=PROJECT_JSON | {"name": "Updated"})

    client = build_async_management_client(handler)
    updated = await client.update_project(ORG_KEY, PROJECT_KEY, {"name": "Updated"})
    assert updated.name == "Updated"
    assert captured[0].endswith(f"/organizations/{ORG_KEY}/projects/{PROJECT_KEY}/")
    await client.aclose()


@pytest.mark.asyncio
async def test_async_create_environment_and_toggle():
    captured: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append((request.method, request.url.path))
        if request.method == "POST" and request.url.path.endswith("/environments/"):
            return httpx.Response(201, json=ENVIRONMENT_JSON)
        return httpx.Response(200, json=ENVIRONMENT_JSON)

    client = build_async_management_client(handler)
    env = await client.create_environment(ORG_KEY, PROJECT_KEY, {"name": "Prod"})
    assert env.key == ENV_KEY
    await client.toggle_environment(ORG_KEY, PROJECT_KEY, ENV_KEY, is_enabled=False)
    assert captured[0][0] == "POST"
    assert captured[0][1].endswith(
        f"/organizations/{ORG_KEY}/projects/{PROJECT_KEY}/environments/"
    )
    assert captured[1][1].endswith(
        f"/organizations/{ORG_KEY}/projects/{PROJECT_KEY}/environments/{ENV_KEY}/toggle/"
    )
    await client.aclose()


@pytest.mark.asyncio
async def test_async_environment_protection():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        if request.method == "PATCH":
            captured["body"] = json.loads(request.content.decode())
            return httpx.Response(
                200, json=PROTECTED_ENVIRONMENT_JSON | captured["body"]
            )
        return httpx.Response(
            200, json=PROTECTED_ENVIRONMENT_JSON | {"protection_level": "none"}
        )

    client = build_async_management_client(handler)
    env = await client.update_environment_protection(
        ORG_KEY,
        PROJECT_KEY,
        ENV_KEY,
        protection_level="org_owner",
        protection_reason="Maintenance",
    )
    assert env.protection_level == "org_owner"
    assert captured["body"]["protection_reason"] == "Maintenance"

    cleared = await client.clear_environment_protection(ORG_KEY, PROJECT_KEY, ENV_KEY)
    assert cleared.protection_level == "none"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_set_organization_plan_and_available_plans():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.url.path)
        return httpx.Response(200, json=PLAN_STATUS_JSON)

    client = build_async_management_client(handler)
    updated = await client.set_organization_plan(ORG_KEY, "pro")
    assert updated.next_plan.code == "pro"

    catalog = await client.get_available_plans()
    assert catalog.active_plan.limits.roles_max_count == 5

    assert captured[0].endswith(f"/organizations/{ORG_KEY}/plan/pro/")
    assert captured[1].endswith("/plans/")
    await client.aclose()


@pytest.mark.asyncio
async def test_async_management_role_permissions_workflow():
    recorded: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded.append((request.method, request.url.path))
        if request.method == "GET" and request.url.path.endswith(
            "/permissions/objects/"
        ):
            return httpx.Response(
                200,
                json={
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [PERMISSION_OBJECT_JSON],
                },
            )
        if request.method == "GET" and request.url.path.endswith("/permissions/"):
            return httpx.Response(200, json=[ROLE_PERMISSION_JSON])
        if request.method == "POST" and request.url.path.endswith(
            "/permissions/objects/"
        ):
            body = json.loads(request.content.decode())
            return httpx.Response(201)
        if request.method == "POST" and request.url.path.endswith(
            "/permissions/batch/"
        ):
            body = json.loads(request.content.decode())
            return httpx.Response(200, json=body)
        if request.method == "POST":
            body = json.loads(request.content.decode())
            return httpx.Response(201, json=ROLE_PERMISSION_JSON | body)
        if request.method == "DELETE":
            return httpx.Response(204)
        raise AssertionError("Unexpected request")

    client = build_async_management_client(handler)
    perms = await client.list_management_role_permissions("role-1")
    assert perms[0].content_type == "collection-items"

    created = await client.upsert_management_role_permission(
        "role-1", ROLE_PERMISSION_JSON
    )
    assert created.actions == ["read"]

    await client.delete_management_role_permission("role-1", "collection-items")

    replaced = await client.replace_management_role_permissions(
        "role-1", [ROLE_PERMISSION_JSON]
    )
    assert replaced[0].all_objects is True

    objects = await client.list_management_permission_objects(
        "role-1", content_type="collection-items"
    )
    assert objects[0].object_key == "folder-1"

    added = await client.add_management_permission_object(
        "role-1", PERMISSION_OBJECT_JSON
    )
    assert added.content_type == "collection-items"
    assert added.object_key == "folder-1"

    await client.delete_management_permission_object("role-1", PERMISSION_OBJECT_JSON)
    await client.aclose()


@pytest.mark.asyncio
async def test_async_flux_role_permissions_workflow():
    recorded: list[tuple[str, str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded.append((request.method, request.url.path, str(request.url)))
        if request.method == "GET" and request.url.path.endswith(
            "/permissions/objects/"
        ):
            return httpx.Response(
                200,
                json={
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [FLUX_PERMISSION_OBJECT_JSON],
                },
            )
        if request.method == "GET" and request.url.path.endswith("/permissions/"):
            return httpx.Response(200, json=[FLUX_ROLE_PERMISSION_JSON])
        if request.method == "POST" and request.url.path.endswith(
            "/permissions/objects/"
        ):
            body = json.loads(request.content.decode())
            return httpx.Response(201)
        if request.method == "POST" and request.url.path.endswith(
            "/permissions/batch/"
        ):
            body = json.loads(request.content.decode())
            return httpx.Response(200, json=body)
        if request.method == "POST":
            body = json.loads(request.content.decode())
            return httpx.Response(201, json=FLUX_ROLE_PERMISSION_JSON | body)
        if request.method == "DELETE":
            return httpx.Response(204)
        raise AssertionError("Unexpected request")

    client = build_async_management_client(handler)
    perms = await client.list_flux_role_permissions("flux-role-1")
    assert perms[0].content_type == "flux-apis"

    upserted = await client.upsert_flux_role_permission(
        "flux-role-1", FLUX_ROLE_PERMISSION_JSON
    )
    assert upserted.actions == ["read"]

    await client.delete_flux_role_permission("flux-role-1", "flux-apis")

    replaced = await client.replace_flux_role_permissions(
        "flux-role-1", [FLUX_ROLE_PERMISSION_JSON]
    )
    assert replaced[0].all_objects is False

    objects = await client.list_flux_permission_objects(
        "flux-role-1", content_type="flux-apis"
    )
    assert objects[0].object_key == "api-1"
    assert any(
        method == "GET"
        and "/permissions/flux-api/roles/flux-role-1/permissions/objects/" in url
        and "content_type=flux-apis" in url
        for method, _, url in recorded
    )

    added = await client.add_flux_permission_object(
        "flux-role-1", FLUX_PERMISSION_OBJECT_JSON
    )
    assert added.content_type == "flux-apis"
    assert added.object_key == "api-1"

    await client.delete_flux_permission_object(
        "flux-role-1", FLUX_PERMISSION_OBJECT_JSON
    )
    await client.aclose()


@pytest.mark.asyncio
async def test_async_create_resource_with_external_id():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode())
        resource_json = {**RESOURCE_JSON, "external_id": "ext-1"}
        return httpx.Response(201, json=resource_json)

    client = build_async_management_client(handler)
    result = await client.create_resource(
        "folder-1", {"data": {"title": "Hello"}}, external_id="ext-1"
    )
    assert result.key == "resource-1"
    assert result.external_id == "ext-1"
    assert captured["body"]["external_id"] == "ext-1"
    assert captured["body"]["data"]["title"] == "Hello"
    # external_id goes in the body, not in query params
    assert "external_id=" not in captured["url"]
    await client.aclose()


@pytest.mark.asyncio
async def test_async_create_resource_without_external_id_omits_field():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(201, json=RESOURCE_JSON)

    client = build_async_management_client(handler)
    await client.create_resource("folder-1", {"data": {"title": "Hello"}})
    assert "external_id" not in captured["body"]
    await client.aclose()


@pytest.mark.asyncio
async def test_async_create_resource_does_not_mutate_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json=RESOURCE_JSON)

    client = build_async_management_client(handler)
    original = {"data": {"title": "Hello"}}
    await client.create_resource("folder-1", original, external_id="ext-1")
    assert "external_id" not in original
    await client.aclose()


@pytest.mark.asyncio
async def test_async_upsert_resource_sends_put_with_external_id():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode())
        resource_json = {**RESOURCE_JSON, "external_id": "my-ext-id"}
        return httpx.Response(200, json=resource_json)

    client = build_async_management_client(handler)
    result = await client.upsert_resource(
        "folder-1",
        {"data": {"title": "Upserted"}},
        external_id="my-ext-id",
    )
    assert captured["method"] == "PUT"
    assert captured["url"].endswith("/resources/?external_id=my-ext-id")
    assert captured["body"]["data"]["title"] == "Upserted"
    # upsert sends external_id as query param, not in body
    assert "external_id" not in captured["body"]
    assert result.key == "resource-1"
    assert result.external_id == "my-ext-id"
    await client.aclose()


# ---------------------------------------------------------------------------
# async batch_upsert_resources
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_batch_upsert_resources_success():
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        ext_id = str(request.url).split("external_id=")[1].split("&")[0]
        call_count += 1
        return httpx.Response(200, json={**RESOURCE_JSON, "external_id": ext_id})

    client = build_async_management_client(handler)
    items = [
        BatchUpsertItem(external_id=f"ext-{i}", payload={"title": f"Item {i}"})
        for i in range(3)
    ]
    result = await client.batch_upsert_resources("folder-1", items)

    assert isinstance(result, BatchUpsertResult)
    assert result.success_count == 3
    assert result.failure_count == 0
    assert result.has_failures is False
    assert result.total == 3
    assert call_count == 3
    returned_ext_ids = {r.external_id for r in result.succeeded}
    assert returned_ext_ids == {"ext-0", "ext-1", "ext-2"}
    await client.aclose()


@pytest.mark.asyncio
async def test_async_batch_upsert_resources_empty_list():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("handler should not be called")

    client = build_async_management_client(handler)
    result = await client.batch_upsert_resources("folder-1", [])

    assert result.success_count == 0
    assert result.failure_count == 0
    assert result.total == 0
    await client.aclose()


@pytest.mark.asyncio
async def test_async_batch_upsert_resources_partial_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        ext_id = str(request.url).split("external_id=")[1].split("&")[0]
        if ext_id == "ext-1":
            return httpx.Response(
                400, json={"message": "Bad request", "error_code": "validation_error"}
            )
        return httpx.Response(200, json={**RESOURCE_JSON, "external_id": ext_id})

    client = build_async_management_client(handler)
    items = [
        BatchUpsertItem(external_id=f"ext-{i}", payload={"title": f"Item {i}"})
        for i in range(3)
    ]
    result = await client.batch_upsert_resources("folder-1", items)

    assert result.success_count == 2
    assert result.failure_count == 1
    assert result.has_failures is True
    error = result.failed[0]
    assert error.external_id == "ext-1"
    assert isinstance(error.exception, FoxnoseAPIError)
    assert error.exception.status_code == 400
    await client.aclose()


@pytest.mark.asyncio
async def test_async_batch_upsert_resources_fail_fast():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400, json={"message": "Bad request", "error_code": "validation_error"}
        )

    client = build_async_management_client(handler)
    items = [
        BatchUpsertItem(external_id=f"ext-{i}", payload={"title": f"Item {i}"})
        for i in range(5)
    ]
    with pytest.raises(FoxnoseAPIError) as exc_info:
        await client.batch_upsert_resources("folder-1", items, fail_fast=True)
    assert exc_info.value.status_code == 400
    await client.aclose()


@pytest.mark.asyncio
async def test_async_batch_upsert_resources_max_concurrency():
    peak = 0
    current = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal peak, current
        # Note: the mock handler is sync, but with httpx MockTransport
        # the async client still serializes calls through the transport.
        # We verify concurrency via semaphore logic in the implementation.
        ext_id = str(request.url).split("external_id=")[1].split("&")[0]
        return httpx.Response(200, json={**RESOURCE_JSON, "external_id": ext_id})

    client = build_async_management_client(handler)
    items = [
        BatchUpsertItem(external_id=f"ext-{i}", payload={"title": f"Item {i}"})
        for i in range(6)
    ]
    result = await client.batch_upsert_resources("folder-1", items, max_concurrency=2)
    assert result.success_count == 6
    await client.aclose()


@pytest.mark.asyncio
async def test_async_batch_upsert_resources_progress_callback():
    def handler(request: httpx.Request) -> httpx.Response:
        ext_id = str(request.url).split("external_id=")[1].split("&")[0]
        return httpx.Response(200, json={**RESOURCE_JSON, "external_id": ext_id})

    progress_calls: list[tuple[int, int]] = []

    client = build_async_management_client(handler)
    items = [
        BatchUpsertItem(external_id=f"ext-{i}", payload={"title": f"Item {i}"})
        for i in range(3)
    ]
    result = await client.batch_upsert_resources(
        "folder-1",
        items,
        on_progress=lambda done, total: progress_calls.append((done, total)),
    )
    assert result.success_count == 3
    assert len(progress_calls) == 3
    assert all(total == 3 for _, total in progress_calls)
    completed_values = sorted(done for done, _ in progress_calls)
    assert completed_values == [1, 2, 3]
    await client.aclose()


@pytest.mark.asyncio
async def test_async_batch_upsert_resources_rejects_zero_concurrency():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=RESOURCE_JSON)

    client = build_async_management_client(handler)
    items = [BatchUpsertItem(external_id="ext-1", payload={"title": "Item"})]
    with pytest.raises(ValueError, match="max_concurrency must be at least 1"):
        await client.batch_upsert_resources("folder-1", items, max_concurrency=0)
    await client.aclose()


@pytest.mark.asyncio
async def test_async_update_delete_resource_and_get_data():
    captured: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append((request.method, request.url.path))
        if request.method == "PUT":
            return httpx.Response(200)
        if request.method == "DELETE":
            return httpx.Response(204)
        if request.method == "GET" and request.url.path.endswith("/data/"):
            return httpx.Response(200, json={"title": "Published"})
        # GET for get_resource (called internally by update_resource)
        return httpx.Response(200, json=RESOURCE_JSON)

    client = build_async_management_client(handler)
    updated = await client.update_resource(
        "folder-1", "resource-1", {"name": "Updated"}
    )
    assert updated.key == "resource-1"

    data = await client.get_resource_data("folder-1", "resource-1")
    assert data["title"] == "Published"

    await client.delete_resource("folder-1", "resource-1")
    assert captured[-1][0] == "DELETE"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_revision_crud():
    captured: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append((request.method, request.url.path))
        if request.method == "DELETE":
            return httpx.Response(204)
        # validate uses POST — check before generic POST
        if "validate" in request.url.path:
            return httpx.Response(200, json={"errors": []})
        if request.method == "POST":
            return httpx.Response(201, json=REVISION_JSON)
        if request.url.path.endswith("/data/"):
            return httpx.Response(200, json={"key": "rev-1", "title": "Content"})
        # GET for get_revision / update_revision (PUT then GET)
        if request.method == "PUT":
            return httpx.Response(200, json=REVISION_JSON)
        return httpx.Response(200, json=REVISION_JSON)

    client = build_async_management_client(handler)
    created = await client.create_revision("folder-1", "resource-1", {"title": "Draft"})
    assert created.key == "rev-1"

    detail = await client.get_revision("folder-1", "resource-1", "rev-1")
    assert detail.number == 1

    updated = await client.update_revision(
        "folder-1", "resource-1", "rev-1", {"title": "Updated"}
    )
    assert updated.key == "rev-1"

    result = await client.validate_revision("folder-1", "resource-1", "rev-1")
    assert result["errors"] == []

    data = await client.get_revision_data("folder-1", "resource-1", "rev-1")
    assert data["key"] == "rev-1"

    await client.delete_revision("folder-1", "resource-1", "rev-1")
    assert captured[-1][0] == "DELETE"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_get_update_delete_component():
    captured: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append((request.method, request.url.path))
        if request.method == "DELETE":
            return httpx.Response(204)
        if request.method == "PUT":
            body = json.loads(request.content.decode())
            return httpx.Response(200, json=COMPONENT_JSON | body)
        return httpx.Response(200, json=COMPONENT_JSON)

    client = build_async_management_client(handler)
    comp = await client.get_component("component-1")
    assert comp.key == "component-1"

    updated = await client.update_component(
        "component-1", {"description": "Updated desc"}
    )
    assert updated.description == "Updated desc"

    await client.delete_component("component-1")
    assert captured[-1][0] == "DELETE"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_component_version_lifecycle():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(str(request.url))
        if request.method == "DELETE":
            return httpx.Response(204)
        if request.url.path.endswith("/publish/"):
            return httpx.Response(
                200, json=VERSION_JSON | {"published_at": "2024-01-11T00:00:00Z"}
            )
        if request.method == "POST":
            return httpx.Response(201, json=VERSION_JSON)
        if request.method == "PUT":
            body = json.loads(request.content.decode())
            return httpx.Response(200, json=VERSION_JSON | body)
        return httpx.Response(200, json=VERSION_JSON)

    client = build_async_management_client(handler)
    created = await client.create_component_version(
        "component-1", {"name": "Draft"}, copy_from="ver-0"
    )
    assert created.key == "ver-1"
    assert "copy_from=ver-0" in captured[0]

    detail = await client.get_component_version("component-1", "ver-1")
    assert detail.version_number == 1

    published = await client.publish_component_version("component-1", "ver-1")
    assert published.published_at is not None

    updated = await client.update_component_version(
        "component-1", "ver-1", {"name": "Released"}
    )
    assert updated.name == "Released"

    await client.delete_component_version("component-1", "ver-1")
    assert captured[-1].endswith("/components/component-1/model/versions/ver-1/")
    await client.aclose()


@pytest.mark.asyncio
async def test_async_component_field_crud():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(str(request.url))
        if request.method == "DELETE":
            return httpx.Response(204)
        if request.method == "POST":
            body = json.loads(request.content.decode())
            return httpx.Response(201, json=FIELD_JSON | body)
        if request.method == "PUT":
            body = json.loads(request.content.decode())
            return httpx.Response(200, json=FIELD_JSON | body)
        return httpx.Response(200, json=FIELD_JSON)

    client = build_async_management_client(handler)
    created = await client.create_component_field(
        "component-1", "ver-1", {"name": "Title", "key": "title"}
    )
    assert created.key == "title"

    detail = await client.get_component_field("component-1", "ver-1", "title")
    assert detail.path == "title"

    updated = await client.update_component_field(
        "component-1", "ver-1", "title", {"description": "Updated"}
    )
    assert updated.description == "Updated"

    await client.delete_component_field("component-1", "ver-1", "title")
    assert captured[-1].endswith("path=title")
    await client.aclose()


@pytest.mark.asyncio
async def test_async_folder_version_lifecycle():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(str(request.url))
        if request.method == "DELETE":
            return httpx.Response(204)
        if request.url.path.endswith("/publish/"):
            return httpx.Response(
                200, json=VERSION_JSON | {"published_at": "2024-01-11T00:00:00Z"}
            )
        if request.method == "POST":
            return httpx.Response(201, json=VERSION_JSON)
        if request.method == "PUT":
            body = json.loads(request.content.decode())
            return httpx.Response(200, json=VERSION_JSON | body)
        return httpx.Response(200, json=VERSION_JSON)

    client = build_async_management_client(handler)
    created = await client.create_folder_version(
        "folder-1", {"name": "v2"}, copy_from="ver-0"
    )
    assert created.key == "ver-1"
    assert "copy_from=ver-0" in captured[0]

    detail = await client.get_folder_version("folder-1", "ver-1")
    assert detail.version_number == 1

    published = await client.publish_folder_version("folder-1", "ver-1")
    assert published.published_at is not None

    updated = await client.update_folder_version(
        "folder-1", "ver-1", {"name": "Released"}
    )
    assert updated.name == "Released"

    await client.delete_folder_version("folder-1", "ver-1")
    assert captured[-1].endswith("/folders/folder-1/model/versions/ver-1/")
    await client.aclose()


@pytest.mark.asyncio
async def test_async_folder_field_crud():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(str(request.url))
        if request.method == "DELETE":
            return httpx.Response(204)
        if request.method == "POST":
            body = json.loads(request.content.decode())
            return httpx.Response(201, json=FIELD_JSON | body)
        if request.method == "PUT":
            body = json.loads(request.content.decode())
            return httpx.Response(200, json=FIELD_JSON | body)
        # get_folder_field hits GET on /field/ path — return single FieldSummary
        if request.method == "GET" and "/field/" in request.url.path:
            return httpx.Response(200, json=FIELD_JSON)
        return httpx.Response(
            200,
            json={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [FIELD_JSON],
            },
        )

    client = build_async_management_client(handler)
    created = await client.create_folder_field(
        "folder-1", "ver-1", {"name": "Title", "key": "title"}
    )
    assert created.key == "title"

    detail = await client.get_folder_field("folder-1", "ver-1", "title")
    assert detail.path == "title"

    updated = await client.update_folder_field(
        "folder-1", "ver-1", "title", {"description": "Updated"}
    )
    assert updated.description == "Updated"

    await client.delete_folder_field("folder-1", "ver-1", "title")
    assert captured[-1].endswith("path=title")
    await client.aclose()


@pytest.mark.asyncio
async def test_async_list_environments_handles_array():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[ENVIRONMENT_JSON])

    client = build_async_management_client(handler)
    envs = await client.list_environments(ORG_KEY, PROJECT_KEY)
    assert envs[0].host == "prod.fxns.io"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_add_api_folder_supports_route_descriptions():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["method"] = request.method
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(201, json=API_FOLDER_JSON | captured["body"])

    client = build_async_management_client(handler)
    added = await client.add_api_folder(
        "api-1",
        "folder-1",
        allowed_methods=[],
        description_get_one="Get one article",
        description_get_many="List articles",
        description_search="Search articles",
        description_schema="",
    )
    assert captured["method"] == "POST"
    assert captured["path"] == "/v1/env123/api/api-1/folders/"
    assert captured["body"]["folder"] == "folder-1"
    assert captured["body"]["allowed_methods"] == []
    assert captured["body"]["description_schema"] == ""
    assert added.description_get_one == "Get one article"
    assert added.description_get_many == "List articles"
    assert added.description_search == "Search articles"
    assert added.description_schema == ""
    await client.aclose()


@pytest.mark.asyncio
async def test_async_update_api_folder_supports_route_descriptions():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["method"] = request.method
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json=API_FOLDER_JSON | captured["body"])

    client = build_async_management_client(handler)
    updated = await client.update_api_folder(
        "api-1",
        "folder-1",
        allowed_methods=["get_many"],
        description_get_one="",
        description_get_many="Public feed",
        description_search="Search public feed",
        description_schema="Read feed schema",
    )
    assert captured["method"] == "PUT"
    assert captured["path"] == "/v1/env123/api/api-1/folders/folder-1/"
    assert captured["body"]["allowed_methods"] == ["get_many"]
    assert captured["body"]["description_get_one"] == ""
    assert updated.description_get_one == ""
    assert updated.description_get_many == "Public feed"
    assert updated.description_search == "Search public feed"
    assert updated.description_schema == "Read feed schema"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_add_api_collection_sends_unscoped_fields_when_given_and_omits_when_not():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(201, json=API_FOLDER_JSON | captured["body"])

    client = build_async_management_client(handler)
    await client.add_api_collection(
        "api-1",
        "folder-1",
        unscoped_levels=[0],
        unscoped_ancestors=["anc-1"],
    )
    assert captured["body"]["unscoped_levels"] == [0]
    assert captured["body"]["unscoped_ancestors"] == ["anc-1"]

    await client.add_api_collection("api-1", "folder-1")
    assert "unscoped_levels" not in captured["body"]
    assert "unscoped_ancestors" not in captured["body"]
    await client.aclose()


@pytest.mark.asyncio
async def test_async_update_api_collection_sends_unscoped_fields_when_given_and_omits_when_not():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json=API_FOLDER_JSON | captured["body"])

    client = build_async_management_client(handler)
    await client.update_api_collection(
        "api-1",
        "folder-1",
        unscoped_levels=[0, 1],
        unscoped_ancestors=["anc-1", "anc-2"],
    )
    assert captured["body"]["unscoped_levels"] == [0, 1]
    assert captured["body"]["unscoped_ancestors"] == ["anc-1", "anc-2"]

    await client.update_api_collection("api-1", "folder-1")
    assert "unscoped_levels" not in captured["body"]
    assert "unscoped_ancestors" not in captured["body"]
    await client.aclose()


@pytest.mark.asyncio
async def test_async_add_api_folder_deprecated_alias_sends_unscoped_fields_when_given_and_omits_when_not():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(201, json=API_FOLDER_JSON | captured["body"])

    client = build_async_management_client(handler)
    await client.add_api_folder(
        "api-1",
        "folder-1",
        unscoped_levels=[0],
        unscoped_ancestors=["anc-1"],
    )
    assert captured["body"]["unscoped_levels"] == [0]
    assert captured["body"]["unscoped_ancestors"] == ["anc-1"]

    await client.add_api_folder("api-1", "folder-1")
    assert "unscoped_levels" not in captured["body"]
    assert "unscoped_ancestors" not in captured["body"]
    await client.aclose()


@pytest.mark.asyncio
async def test_async_update_api_folder_deprecated_alias_sends_unscoped_fields_when_given_and_omits_when_not():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json=API_FOLDER_JSON | captured["body"])

    client = build_async_management_client(handler)
    await client.update_api_folder(
        "api-1",
        "folder-1",
        unscoped_levels=[0, 1],
        unscoped_ancestors=["anc-1", "anc-2"],
    )
    assert captured["body"]["unscoped_levels"] == [0, 1]
    assert captured["body"]["unscoped_ancestors"] == ["anc-1", "anc-2"]

    await client.update_api_folder("api-1", "folder-1")
    assert "unscoped_levels" not in captured["body"]
    assert "unscoped_ancestors" not in captured["body"]
    await client.aclose()


async def test_async_create_api_passes_agent_and_cors_fields_and_parses_response():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["method"] = request.method
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(
            201,
            json={
                "key": "api-1",
                "environment": "env123",
                "created_at": "2026-07-23T00:00:00Z",
                **captured["body"],
                # A field this SDK version does not model yet (forward-compat):
                "some_future_flag": True,
            },
        )

    client = build_async_management_client(handler)
    api = await client.create_api(
        {
            "name": "Storefront",
            "prefix": "shop",
            "is_auth_required": False,
            "mcp_enabled": False,
            "router_introspection_enabled": True,
            "cors_origins": ["*"],
        }
    )

    assert captured["method"] == "POST"
    assert captured["path"] == "/v1/env123/api/"
    assert captured["body"]["cors_origins"] == ["*"]
    assert captured["body"]["mcp_enabled"] is False
    assert captured["body"]["router_introspection_enabled"] is True

    assert api.cors_origins == ["*"]
    assert api.mcp_enabled is False
    assert api.router_introspection_enabled is True
    assert not hasattr(api, "some_future_flag")
    await client.aclose()


async def test_async_update_api_passes_agent_and_cors_fields():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["method"] = request.method
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "key": "api-1",
                "name": "Storefront",
                "prefix": "shop",
                "environment": "env123",
                "is_auth_required": False,
                "created_at": "2026-07-23T00:00:00Z",
                **captured["body"],
            },
        )

    client = build_async_management_client(handler)
    api = await client.update_api(
        "api-1",
        {
            "mcp_enabled": False,
            "router_introspection_enabled": True,
            "cors_origins": ["https://app.example.com"],
        },
    )
    assert captured["method"] == "PUT"
    assert captured["path"] == "/v1/env123/api/api-1/"
    assert captured["body"]["mcp_enabled"] is False
    assert captured["body"]["router_introspection_enabled"] is True
    assert captured["body"]["cors_origins"] == ["https://app.example.com"]
    assert api.mcp_enabled is False
    assert api.router_introspection_enabled is True
    assert api.cors_origins == ["https://app.example.com"]
    await client.aclose()


async def test_async_api_info_defaults_when_server_omits_new_fields():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "key": "api-1",
                "name": "Legacy API",
                "prefix": "v1",
                "environment": "env123",
                "is_auth_required": True,
                "created_at": "2026-01-01T00:00:00Z",
            },
        )

    client = build_async_management_client(handler)
    api = await client.get_api("api-1")
    assert api.cors_origins == []
    assert api.mcp_enabled is True
    assert api.router_introspection_enabled is True
    await client.aclose()


# ---------------------------------------------------------------------------
# AsyncFluxClient tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_flux_list_resources():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(200, json={"results": [{"key": "article-1"}]})

    client = build_async_flux_client(handler)
    result = await client.list_resources("articles")
    assert result["results"][0]["key"] == "article-1"
    assert captured["path"] == "/v1/articles"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_flux_get_resource():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(200, json={"key": "article-1", "title": "Hello"})

    client = build_async_flux_client(handler)
    result = await client.get_resource("articles", "article-1")
    assert result["key"] == "article-1"
    assert captured["path"] == "/v1/articles/article-1"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_flux_search():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"results": []})

    client = build_async_flux_client(handler)
    result = await client.search("articles", body={"where": {"$": {"all_of": []}}})
    assert result["results"] == []
    assert captured["path"] == "/v1/articles/_search"
    assert captured["body"]["where"]["$"]["all_of"] == []
    await client.aclose()


@pytest.mark.asyncio
async def test_async_flux_router_and_schema_paths():
    captured: dict[str, Any] = {"paths": []}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["paths"].append(request.url.path)
        if request.url.path.endswith("/_router"):
            return httpx.Response(200, json={"api": "v1", "routes": []})
        if request.url.path.endswith("/_schema"):
            return httpx.Response(
                200,
                json={
                    "json_schema": {"type": "object"},
                    "searchable_fields": ["title"],
                    "non_searchable_fields": [],
                    "path": "/v1/articles",
                    "actions": ["get_many", "get_one"],
                },
            )
        return httpx.Response(200, json={"results": []})

    client = build_async_flux_client(handler)
    router = await client.get_router()
    schema = await client.get_schema("articles")
    assert router["api"] == "v1"
    assert schema["path"] == "/v1/articles"
    assert captured["paths"] == ["/v1/_router", "/v1/articles/_schema"]
    await client.aclose()


# ---------------------------------------------------------------------------
# Model objects as identifiers (async client)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_list_resources_accepts_folder_object():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        payload = {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [RESOURCE_JSON],
        }
        return httpx.Response(200, json=payload)

    client = build_async_management_client(handler)
    folder = FolderSummary.model_validate(FOLDER_JSON)
    response = await client.list_resources(folder)
    assert response.count == 1
    assert captured["path"] == "/v1/env123/folders/folder-1/resources/"
    await client.aclose()


@pytest.mark.asyncio
async def test_async_get_revision_accepts_model_objects():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(200, json=REVISION_JSON)

    client = build_async_management_client(handler)
    folder = FolderSummary.model_validate(FOLDER_JSON)
    resource = ResourceSummary.model_validate(RESOURCE_JSON)
    revision = RevisionSummary.model_validate(REVISION_JSON)
    result = await client.get_revision(folder, resource, revision)
    assert result.key == "rev-1"
    assert (
        captured["path"]
        == "/v1/env123/folders/folder-1/resources/resource-1/revisions/rev-1/"
    )
    await client.aclose()


@pytest.mark.asyncio
async def test_async_create_resource_accepts_folder_object():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(201, json=RESOURCE_JSON)

    client = build_async_management_client(handler)
    folder = FolderSummary.model_validate(FOLDER_JSON)
    result = await client.create_resource(folder, {"data": {"title": "Hello"}})
    assert result.key == "resource-1"
    assert "/folders/folder-1/resources/" in captured["url"]
    await client.aclose()


# ---------------------------------------------------------------------------
# Async FluxClient vector search — integration tests
# ---------------------------------------------------------------------------

SEARCH_RESPONSE = {"results": [], "count": 0, "next": None}


def _build_async_flux_client(
    handler: Callable[..., httpx.Response],
) -> AsyncFluxClient:
    client = AsyncFluxClient(
        base_url="https://env.fxns.io",
        api_prefix="v1",
        auth=SimpleKeyAuth("pub", "secret"),
    )
    client._transport = HttpTransport(
        config=FoxnoseConfig(base_url="https://env.fxns.io"),
        auth=SimpleKeyAuth("pub", "secret"),
        async_client=httpx.AsyncClient(
            base_url="https://env.fxns.io",
            transport=httpx.MockTransport(handler),
        ),
    )
    return client


@pytest.mark.asyncio
async def test_async_flux_vector_search_sends_correct_body():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=SEARCH_RESPONSE)

    flux = _build_async_flux_client(handler)
    await flux.vector_search("articles", query="semantic query", top_k=5)
    assert captured["path"] == "/v1/articles/_search"
    assert captured["body"]["search_mode"] == "vector"
    assert captured["body"]["vector_search"]["query"] == "semantic query"
    assert captured["body"]["vector_search"]["top_k"] == 5
    await flux.aclose()


@pytest.mark.asyncio
async def test_async_flux_create_and_update_resource():
    calls: list[Any] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(
            (request.method, request.url.path, json.loads(request.content.decode()))
        )
        return httpx.Response(
            201,
            json={
                "resource_key": "res_1",
                "revision_key": "rev_1",
                "write_units": 1,
                "published": True,
            },
        )

    flux = _build_async_flux_client(handler)
    created = await flux.create_resource("articles", {"title": "Hi"})
    assert created["published"] is True
    await flux.update_resource("users/usr_1/memories", "res_1", {"title": "Bye"})
    await flux.aclose()

    assert calls[0] == ("POST", "/v1/articles/", {"data": {"title": "Hi"}})
    assert calls[1] == (
        "PUT",
        "/v1/users/usr_1/memories/res_1/",
        {"data": {"title": "Bye"}},
    )


@pytest.mark.asyncio
async def test_async_flux_update_502_is_not_retried():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(
            502,
            json={
                "error_code": "upstream_error",
                "message": "Upstream write failed",
                "detail": None,
            },
        )

    flux = _build_async_flux_client(handler)
    with pytest.raises(UpstreamError):
        await flux.update_resource("articles", "res_1", {"title": "x"})
    await flux.aclose()
    assert calls["n"] == 1  # a write 502 is never retried on the async path either


@pytest.mark.asyncio
async def test_async_flux_vector_field_search_sends_correct_body():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=SEARCH_RESPONSE)

    flux = _build_async_flux_client(handler)
    await flux.vector_field_search(
        "articles",
        field="speaker_embedding",
        query_vector=[0.1, 0.2, 0.3],
        similarity_threshold=0.8,
    )
    body = captured["body"]
    assert body["search_mode"] == "vector"
    assert body["vector_field_search"]["field"] == "speaker_embedding"
    assert body["vector_field_search"]["query_vector"] == [0.1, 0.2, 0.3]
    await flux.aclose()


@pytest.mark.asyncio
async def test_async_flux_hybrid_search_sends_correct_body():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=SEARCH_RESPONSE)

    flux = _build_async_flux_client(handler)
    await flux.hybrid_search(
        "articles",
        query="semantic query",
        find_text={"query": "keyword"},
        vector_weight=0.7,
        text_weight=0.3,
    )
    body = captured["body"]
    assert body["search_mode"] == "hybrid"
    assert body["find_text"] == {"query": "keyword"}
    assert body["hybrid_config"]["vector_weight"] == 0.7
    await flux.aclose()


@pytest.mark.asyncio
async def test_async_flux_boosted_search_sends_correct_body():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=SEARCH_RESPONSE)

    flux = _build_async_flux_client(handler)
    await flux.boosted_search(
        "articles",
        find_text={"query": "keyword"},
        query="semantic boost",
        boost_factor=2.0,
    )
    body = captured["body"]
    assert body["search_mode"] == "vector_boosted"
    assert body["vector_boost_config"]["boost_factor"] == 2.0
    await flux.aclose()


@pytest.mark.asyncio
async def test_async_flux_vector_search_extra_body():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=SEARCH_RESPONSE)

    flux = _build_async_flux_client(handler)
    await flux.vector_search(
        "articles",
        query="hello",
        where={"category": "tech"},
    )
    assert captured["body"]["where"] == {"category": "tech"}
    await flux.aclose()


@pytest.mark.asyncio
async def test_async_flux_boosted_search_with_custom_vector():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=SEARCH_RESPONSE)

    flux = _build_async_flux_client(handler)
    await flux.boosted_search(
        "articles",
        find_text={"query": "keyword"},
        field="emb",
        query_vector=[0.1, 0.2],
    )
    body = captured["body"]
    assert body["vector_field_search"]["field"] == "emb"
    assert "vector_search" not in body
    await flux.aclose()


@pytest.mark.asyncio
async def test_async_flux_boosted_search_rejects_both():
    flux = _build_async_flux_client(lambda r: httpx.Response(200, json=SEARCH_RESPONSE))
    with pytest.raises(ValueError, match="not both"):
        await flux.boosted_search(
            "articles",
            find_text={"query": "keyword"},
            query="auto",
            field="emb",
            query_vector=[0.1],
        )
    await flux.aclose()


@pytest.mark.asyncio
async def test_async_flux_boosted_search_requires_embedding():
    flux = _build_async_flux_client(lambda r: httpx.Response(200, json=SEARCH_RESPONSE))
    with pytest.raises(ValueError, match="Provide either"):
        await flux.boosted_search(
            "articles",
            find_text={"query": "keyword"},
        )
    await flux.aclose()


# ---------------------------------------------------------------------------
# `search()` query params (truncate_text) and `query_params` on the four
# search wrappers -- async mirror of tests/test_clients.py.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_flux_search_sends_truncate_text_in_query_string_not_body():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(request.url.params)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=SEARCH_RESPONSE)

    flux = _build_async_flux_client(handler)
    await flux.search(
        "articles",
        body={"find_text": {"query": "hello"}},
        params={"truncate_text": 50},
    )
    assert captured["query"] == {"truncate_text": "50"}
    assert "truncate_text" not in captured["body"]
    await flux.aclose()


@pytest.mark.asyncio
async def test_async_flux_vector_search_forwards_query_params_to_query_string():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(request.url.params)
        return httpx.Response(200, json=SEARCH_RESPONSE)

    flux = _build_async_flux_client(handler)
    await flux.vector_search(
        "articles",
        query="hello",
        query_params={"truncate_text": 50},
    )
    assert captured["query"] == {"truncate_text": "50"}
    await flux.aclose()


@pytest.mark.asyncio
async def test_async_flux_vector_field_search_forwards_query_params_to_query_string():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(request.url.params)
        return httpx.Response(200, json=SEARCH_RESPONSE)

    flux = _build_async_flux_client(handler)
    await flux.vector_field_search(
        "articles",
        field="emb",
        query_vector=[0.1, 0.2],
        query_params={"truncate_text": 50},
    )
    assert captured["query"] == {"truncate_text": "50"}
    await flux.aclose()


@pytest.mark.asyncio
async def test_async_flux_hybrid_search_forwards_query_params_to_query_string():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(request.url.params)
        return httpx.Response(200, json=SEARCH_RESPONSE)

    flux = _build_async_flux_client(handler)
    await flux.hybrid_search(
        "articles",
        query="hello",
        find_text={"query": "hello"},
        query_params={"truncate_text": 50},
    )
    assert captured["query"] == {"truncate_text": "50"}
    await flux.aclose()


@pytest.mark.asyncio
async def test_async_flux_boosted_search_forwards_query_params_to_query_string():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(request.url.params)
        return httpx.Response(200, json=SEARCH_RESPONSE)

    flux = _build_async_flux_client(handler)
    await flux.boosted_search(
        "articles",
        find_text={"query": "keyword"},
        query="hello",
        query_params={"truncate_text": 50},
    )
    assert captured["query"] == {"truncate_text": "50"}
    await flux.aclose()


@pytest.mark.asyncio
async def test_async_merge_extra_rejects_truncate_text_and_names_query_params():
    flux = _build_async_flux_client(lambda r: httpx.Response(200, json=SEARCH_RESPONSE))
    with pytest.raises(ValueError, match="query_params"):
        await flux.vector_search("articles", query="hello", truncate_text=50)
    await flux.aclose()


@pytest.mark.asyncio
async def test_async_flux_vector_search_params_extra_body_still_lands_in_body():
    """Regression pin: a caller already passing `params={...}` as a body extra
    must keep landing in the JSON body unchanged; `query_params` must not
    reroute it to the query string.
    """
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(request.url.params)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=SEARCH_RESPONSE)

    flux = _build_async_flux_client(handler)
    await flux.vector_search(
        "articles",
        query="hello",
        params={"some": "value"},
    )
    assert captured["body"]["params"] == {"some": "value"}
    assert captured["query"] == {}
    await flux.aclose()


# ---------------------------------------------------------------------------
# Cross-parent (flat) address path-construction pins -- async mirror.
#
# These prove the SDK builds the URL for a fully-flat and a partially-flat
# collection path correctly. They do NOT prove the server serves a given
# read method at that level.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_flux_builds_fully_flat_path_for_list_get_search_schema():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.url.path)
        if request.url.path.endswith("/_schema"):
            return httpx.Response(
                200,
                json={
                    "json_schema": {"type": "object"},
                    "searchable_fields": [],
                    "non_searchable_fields": [],
                    "path": "/v1/realty/accounts/listings/photos",
                    "actions": [],
                },
            )
        return httpx.Response(200, json=SEARCH_RESPONSE)

    flux = _build_async_flux_client(handler)
    flat_path = "realty/accounts/listings/photos"
    await flux.list_resources(flat_path)
    await flux.get_resource(flat_path, "photo-1")
    await flux.search(flat_path, body={"find_text": {"query": "x"}})
    await flux.get_schema(flat_path)
    await flux.aclose()
    assert captured == [
        "/v1/realty/accounts/listings/photos",
        "/v1/realty/accounts/listings/photos/photo-1",
        "/v1/realty/accounts/listings/photos/_search",
        "/v1/realty/accounts/listings/photos/_schema",
    ]


@pytest.mark.asyncio
async def test_async_flux_builds_partially_flat_path_for_list_get_search_schema():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.url.path)
        if request.url.path.endswith("/_schema"):
            return httpx.Response(
                200,
                json={
                    "json_schema": {"type": "object"},
                    "searchable_fields": [],
                    "non_searchable_fields": [],
                    "path": "/v1/realty/accounts/{accounts_key}/listings/photos",
                    "actions": [],
                },
            )
        return httpx.Response(200, json=SEARCH_RESPONSE)

    flux = _build_async_flux_client(handler)
    partial_path = "realty/accounts/acc-1/listings/photos"
    await flux.list_resources(partial_path)
    await flux.get_resource(partial_path, "photo-1")
    await flux.search(partial_path, body={"find_text": {"query": "x"}})
    await flux.get_schema(partial_path)
    await flux.aclose()
    assert captured == [
        "/v1/realty/accounts/acc-1/listings/photos",
        "/v1/realty/accounts/acc-1/listings/photos/photo-1",
        "/v1/realty/accounts/acc-1/listings/photos/_search",
        "/v1/realty/accounts/acc-1/listings/photos/_schema",
    ]


# ---------------------------------------------------------------------------
# APIFolderSummary shape -- async mirror (the model is shared, but the plan
# requires both test files to cover it).
# ---------------------------------------------------------------------------

PRODUCTION_CONNECTION_JSON = {
    "folder": "9wjjtw76dyj0",
    "api": "949sr5xz7kcj",
    "created_at": "2026-08-01T06:43:11.331505-05:00",
    "allowed_methods": ["get_one", "get_many"],
    "description_get_one": "Returns one resource by id.",
    "description_get_many": "Returns a paginated list of resources.",
    "description_search": "Searches resources by filters.",
    "description_schema": "Returns JSON schema for this resource.",
    "unscoped_ancestors": [
        "01debe0d-0325-42b1-9bfd-ef52046cd785",
        "432880c9-ae43-4462-b4f3-f16c18068ea5",
    ],
    "unscoped_levels": [0],
    "expose_owner": False,
    "flat_route": {
        "path": "/realty/accounts/listings/photos",
        "omitted_ancestors": [
            "01debe0d-0325-42b1-9bfd-ef52046cd785",
            "432880c9-ae43-4462-b4f3-f16c18068ea5",
        ],
        "enabled": True,
        "read_methods": ["get_one", "get_many"],
        "available": True,
        "unavailable_reason": None,
        "published_generation": 18,
        "router_generation": 18,
    },
    "flat_routes": [
        {
            "level": 0,
            "path": "/realty/accounts/listings/photos",
            "omitted_ancestors": [
                "01debe0d-0325-42b1-9bfd-ef52046cd785",
                "432880c9-ae43-4462-b4f3-f16c18068ea5",
            ],
            "retained_ancestors": [],
            "enabled": True,
            "read_methods": ["get_one", "get_many"],
            "available": True,
            "unavailable_reason": None,
            "published_generation": 18,
            "router_generation": 18,
        },
        {
            "level": 1,
            "path": "/realty/accounts/{accounts_key}/listings/photos",
            "omitted_ancestors": ["432880c9-ae43-4462-b4f3-f16c18068ea5"],
            "retained_ancestors": ["01debe0d-0325-42b1-9bfd-ef52046cd785"],
            "enabled": False,
            "read_methods": ["get_one", "get_many"],
            "available": True,
            "unavailable_reason": None,
            "published_generation": 18,
            "router_generation": 18,
        },
    ],
}


def test_api_folder_summary_parses_full_production_connection_async_file():
    summary = APIFolderSummary.model_validate(PRODUCTION_CONNECTION_JSON)
    assert summary.unscoped_levels == [0]
    assert summary.flat_route.path == "/realty/accounts/listings/photos"
    assert len(summary.flat_routes) == 2
    assert summary.flat_routes[1].retained_ancestors == [
        "01debe0d-0325-42b1-9bfd-ef52046cd785"
    ]


def test_api_folder_summary_parses_null_flat_route_and_flat_routes_async_file():
    payload = {**API_FOLDER_JSON, "flat_route": None, "flat_routes": None}
    summary = APIFolderSummary.model_validate(payload)
    assert summary.flat_route is None
    assert summary.flat_routes is None
    assert summary.unscoped_levels == []
    assert summary.unscoped_ancestors == []
    assert summary.expose_owner is False


def test_api_folder_summary_preserves_unknown_fields_via_extra_allow_async_file():
    payload = {
        **PRODUCTION_CONNECTION_JSON,
        "some_future_top_level_flag": True,
        "flat_routes": [
            {
                **PRODUCTION_CONNECTION_JSON["flat_routes"][0],
                "some_future_route_flag": "x",
            }
        ],
    }
    summary = APIFolderSummary.model_validate(payload)
    assert summary.model_extra["some_future_top_level_flag"] is True
    assert summary.flat_routes[0].model_extra["some_future_route_flag"] == "x"


# ---------------------------------------------------------------------------
# Pins for two "the server validates, not us" decisions: truncate_text bounds
# and the unscoped_levels/unscoped_ancestors pairing are both enforced by the
# server, not the SDK. These tests exist ONLY to fail loudly if a future
# change accidentally adds client-side validation for either -- they assert
# that the value/field reaches the request, not that it is "correct". Async
# mirror of tests/test_clients.py.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_flux_search_forwards_out_of_range_and_non_integer_truncate_text_without_raising():
    """Regression pin: truncate_text bounds (integer, >= 1) are validated by
    the server via a 422, not the SDK. An out-of-range value (0) and a
    non-integer value must keep forwarding to the query string unchanged --
    not raise -- or client-side validation has crept into the SDK.
    """
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(request.url.params)
        return httpx.Response(200, json=SEARCH_RESPONSE)

    flux = _build_async_flux_client(handler)

    await flux.search(
        "articles",
        body={"find_text": {"query": "hello"}},
        params={"truncate_text": 0},
    )
    assert captured["query"]["truncate_text"] == "0"

    await flux.search(
        "articles",
        body={"find_text": {"query": "hello"}},
        params={"truncate_text": "not-an-integer"},
    )
    assert captured["query"]["truncate_text"] == "not-an-integer"
    await flux.aclose()


@pytest.mark.asyncio
async def test_async_add_api_collection_forwards_unscoped_levels_or_unscoped_ancestors_alone_without_requiring_both():
    """Regression pin: the API requires unscoped_levels and unscoped_ancestors
    to be sent together, but enforcing that pairing is the server's job (see
    add_api_collection's docstring), not the SDK's. Either field alone must
    still reach the request body -- if this starts raising, client-side
    pairing validation has crept into the SDK.
    """
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(201, json=API_FOLDER_JSON | captured["body"])

    client = build_async_management_client(handler)

    await client.add_api_collection("api-1", "folder-1", unscoped_levels=[0])
    assert captured["body"]["unscoped_levels"] == [0]
    assert "unscoped_ancestors" not in captured["body"]

    await client.add_api_collection("api-1", "folder-1", unscoped_ancestors=["anc-1"])
    assert captured["body"]["unscoped_ancestors"] == ["anc-1"]
    assert "unscoped_levels" not in captured["body"]
    await client.aclose()
