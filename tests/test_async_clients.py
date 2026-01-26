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
from foxnose_sdk.management.models import (
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
    "component": None,
    "resource_owner": None,
    "current_revision": "rev-1",
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
        "environments": {"max": 10, "current": 3},
        "folders": {"max": 20, "current": 5},
        "resources": {"max": 100, "current": 15},
        "users": {"max": 10, "current": 4},
        "components": {"max": 30, "current": 10},
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
    "content_type": "resources",
    "actions": ["read", "update"],
    "all_objects": True,
}

PERMISSION_OBJECT_JSON = {
    "content_type": "folder-items",
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
    captured: dict[str, Any] = {"paths": []}

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

    created = await client.create_management_api_key({"description": "Ops key"})
    assert created.secret_key == "manage_sec_xyz"

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
    captured: dict[str, Any] = {"paths": []}

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

    created = await client.create_flux_api_key({"description": "Flux key"})
    assert created.secret_key == "flux_sec_xyz"

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
            return httpx.Response(200, json=[PERMISSION_OBJECT_JSON])
        if request.method == "GET" and request.url.path.endswith("/permissions/"):
            return httpx.Response(200, json=[ROLE_PERMISSION_JSON])
        if request.method == "POST" and request.url.path.endswith(
            "/permissions/objects/"
        ):
            body = json.loads(request.content.decode())
            return httpx.Response(201, json=PERMISSION_OBJECT_JSON | body)
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
    assert perms[0].content_type == "resources"

    created = await client.upsert_management_role_permission(
        "role-1", ROLE_PERMISSION_JSON
    )
    assert created.actions == ["read", "update"]

    await client.delete_management_role_permission("role-1", "resources")

    replaced = await client.replace_management_role_permissions(
        "role-1", [ROLE_PERMISSION_JSON]
    )
    assert replaced[0].all_objects is True

    objects = await client.list_management_permission_objects(
        "role-1", content_type="folder-items"
    )
    assert objects[0].object_key == "folder-1"

    added = await client.add_management_permission_object(
        "role-1", PERMISSION_OBJECT_JSON
    )
    assert added.object_key == "folder-1"

    await client.delete_management_permission_object("role-1", PERMISSION_OBJECT_JSON)
    await client.aclose()


@pytest.mark.asyncio
async def test_async_flux_role_permissions_workflow():
    recorded: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded.append((request.method, request.url.path))
        if request.method == "GET" and request.url.path.endswith(
            "/permissions/objects/"
        ):
            return httpx.Response(200, json=[FLUX_PERMISSION_OBJECT_JSON])
        if request.method == "GET" and request.url.path.endswith("/permissions/"):
            return httpx.Response(200, json=[FLUX_ROLE_PERMISSION_JSON])
        if request.method == "POST" and request.url.path.endswith(
            "/permissions/objects/"
        ):
            body = json.loads(request.content.decode())
            return httpx.Response(201, json=FLUX_PERMISSION_OBJECT_JSON | body)
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

    added = await client.add_flux_permission_object(
        "flux-role-1", FLUX_PERMISSION_OBJECT_JSON
    )
    assert added.object_key == "api-1"

    await client.delete_flux_permission_object(
        "flux-role-1", FLUX_PERMISSION_OBJECT_JSON
    )
    await client.aclose()


@pytest.mark.asyncio
async def test_async_create_resource_with_component():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(201, json=RESOURCE_JSON)

    client = build_async_management_client(handler)
    result = await client.create_resource(
        "folder-1", {"data": {"title": "Hello"}}, component="comp-1"
    )
    assert result.key == "resource-1"
    assert "component=comp-1" in captured["url"]
    assert captured["body"]["data"]["title"] == "Hello"
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
