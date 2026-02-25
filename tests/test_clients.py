from __future__ import annotations

import json
from typing import Any, Callable

import httpx

import pytest

from foxnose_sdk.auth import SimpleKeyAuth
from foxnose_sdk.config import FoxnoseConfig
from foxnose_sdk.flux.client import FluxClient
from foxnose_sdk.http import HttpTransport
from foxnose_sdk.management.client import ManagementClient, _resolve_key
from foxnose_sdk.errors import FoxnoseAPIError
from foxnose_sdk.management.models import (
    BatchItemError,
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

USER_JSON = {
    "key": "user-1",
    "email": "owner@example.com",
    "first_name": "Jane",
    "last_name": "Doe",
    "full_name": "Jane Doe",
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
    "external_id": None,
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

ROLE_PERMISSION_JSON = {
    "content_type": "resources",
    "actions": ["read", "update"],
    "all_objects": True,
}

PERMISSION_OBJECT_JSON = {
    "content_type": "folder-items",
    "object_key": "folder-1",
}

FLUX_ROLE_JSON = {
    "key": "flux-role-1",
    "name": "Flux Readers",
    "description": "Read blog APIs",
    "environment": ENV_KEY,
    "created_at": "2024-01-10T00:00:00Z",
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

LOCALE_JSON = {
    "name": "Français",
    "code": "fr",
    "environment": ENV_KEY,
    "created_at": "2024-01-10T00:00:00Z",
    "is_default": False,
}

PROTECTED_ENVIRONMENT_JSON = ENVIRONMENT_JSON | {
    "protection_level": "org_owner",
    "protection_level_display": "Organization Owner Protected",
    "protected_by_user": USER_JSON,
    "protected_at": "2024-03-01T10:00:00Z",
    "protection_reason": "Maintenance",
}


def build_management_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> ManagementClient:
    client = ManagementClient(
        base_url="https://api.example.com",
        environment_key="env123",
        auth=SimpleKeyAuth("pub", "secret"),
    )
    client._transport = HttpTransport(  # type: ignore[attr-defined]
        config=FoxnoseConfig(base_url="https://api.example.com"),
        auth=SimpleKeyAuth("pub", "secret"),
        sync_client=httpx.Client(
            base_url="https://api.example.com", transport=httpx.MockTransport(handler)
        ),
    )
    return client


def test_list_folders_returns_model():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        payload = {"count": 1, "next": None, "previous": None, "results": [FOLDER_JSON]}
        return httpx.Response(200, json=payload)

    client = build_management_client(handler)
    folders = client.list_folders()
    assert folders.count == 1
    assert folders.results[0].alias == "folder"
    assert captured["path"] == "/v1/env123/folders/tree/"


def test_get_folder_by_path_adds_query_param():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=FOLDER_JSON)

    client = build_management_client(handler)
    folder = client.get_folder_by_path("/nested/path")
    assert folder.key == "folder-1"
    assert "path=%2Fnested%2Fpath" in captured["url"]


def test_list_folder_tree_children_mode():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        payload = {"count": 1, "next": None, "previous": None, "results": [FOLDER_JSON]}
        return httpx.Response(200, json=payload)

    client = build_management_client(handler)
    folders = client.list_folder_tree(key="folder-1", mode="children")
    assert folders.results[0].key == "folder-1"
    assert "key=folder-1" in captured["url"]
    assert "mode=children" in captured["url"]


def test_create_folder_posts_payload():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(201, json=FOLDER_JSON)

    client = build_management_client(handler)
    folder = client.create_folder({"name": "Folder", "alias": "folder"})
    assert folder.key == "folder-1"
    assert captured["body"]["alias"] == "folder"


def test_list_projects_and_update():
    captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(str(request.url))
        if request.method == "GET" and request.url.path.endswith("/projects/"):
            return httpx.Response(
                200,
                json={
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [PROJECT_JSON],
                },
            )
        return httpx.Response(200, json=PROJECT_JSON | {"name": "Updated"})

    client = build_management_client(handler)
    projects = client.list_projects(ORG_KEY)
    assert projects.results[0].key == PROJECT_KEY
    updated = client.update_project(ORG_KEY, PROJECT_KEY, {"name": "Updated"})
    assert updated.name == "Updated"
    assert captured[0].endswith(f"/organizations/{ORG_KEY}/projects/")
    assert captured[1].endswith(f"/organizations/{ORG_KEY}/projects/{PROJECT_KEY}/")


def test_create_environment_and_toggle():
    captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append((request.method, str(request.url)))
        if request.method == "POST" and request.url.path.endswith("/environments/"):
            return httpx.Response(201, json=ENVIRONMENT_JSON)
        return httpx.Response(200, json=ENVIRONMENT_JSON | {"name": "Updated Env"})

    client = build_management_client(handler)
    env = client.create_environment(ORG_KEY, PROJECT_KEY, {"name": "Prod"})
    assert env.key == ENV_KEY
    client.toggle_environment(ORG_KEY, PROJECT_KEY, ENV_KEY, is_enabled=False)
    assert captured[0][0] == "POST"
    assert captured[0][1].endswith(
        f"/organizations/{ORG_KEY}/projects/{PROJECT_KEY}/environments/"
    )
    assert captured[1][1].endswith(
        f"/organizations/{ORG_KEY}/projects/{PROJECT_KEY}/environments/{ENV_KEY}/toggle/"
    )


def test_update_environment_protection_and_clear():
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

    client = build_management_client(handler)
    env = client.update_environment_protection(
        ORG_KEY,
        PROJECT_KEY,
        ENV_KEY,
        protection_level="org_owner",
        protection_reason="Maintenance",
    )
    assert env.protection_level == "org_owner"
    assert captured["body"]["protection_reason"] == "Maintenance"
    assert captured["path"].endswith(
        f"/organizations/{ORG_KEY}/projects/{PROJECT_KEY}/environments/{ENV_KEY}/protection/"
    )

    cleared = client.clear_environment_protection(ORG_KEY, PROJECT_KEY, ENV_KEY)
    assert cleared.protection_level == "none"


def test_list_organizations_and_update():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(str(request.url))
        if request.method == "GET":
            return httpx.Response(200, json=[ORGANIZATION_JSON])
        body = json.loads(request.content.decode())
        return httpx.Response(200, json=ORGANIZATION_JSON | body)

    client = build_management_client(handler)
    orgs = client.list_organizations()
    assert orgs[0].owner.email == "owner@example.com"

    updated = client.update_organization(ORG_KEY, {"name": "Updated"})
    assert updated.name == "Updated"
    assert captured[0].endswith("/organizations/")
    assert captured[1].endswith(f"/organizations/{ORG_KEY}/")


def test_list_regions_returns_models():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(200, json=[REGION_JSON])

    client = build_management_client(handler)
    regions = client.list_regions()
    assert regions[0].code == "eu-central-1"
    assert captured["path"] == "/regions/"


def test_organization_plan_operations():
    captured: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append((request.method, str(request.url)))
        return httpx.Response(200, json=PLAN_STATUS_JSON)

    client = build_management_client(handler)
    plan = client.get_organization_plan(ORG_KEY)
    assert plan.active_plan.code == "standard"
    assert plan.active_plan.limits.projects == 10

    updated = client.set_organization_plan(ORG_KEY, "integration_tests")
    assert updated.next_plan.code == "pro"

    catalog = client.get_available_plans()
    assert catalog.active_plan.limits.roles_max_count == 5

    assert captured[0][1].endswith(f"/organizations/{ORG_KEY}/plan/")
    assert captured[1][1].endswith(f"/organizations/{ORG_KEY}/plan/integration_tests/")
    assert captured[2][1].endswith("/plans/")


def test_get_organization_usage_returns_model():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(200, json=USAGE_JSON)

    client = build_management_client(handler)
    usage = client.get_organization_usage(ORG_KEY)
    assert usage.storage.data_storage == 123.4
    assert usage.usage.projects.current == 2
    assert usage.current_usage.embedding_tokens["total"] == 1000
    assert captured["path"].endswith(f"/organizations/{ORG_KEY}/usage/")


def test_management_api_key_lifecycle():
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
            captured["bodies"].append(json.loads(request.content.decode()))
            return httpx.Response(
                200, json=MANAGEMENT_API_KEY_JSON | {"description": "Updated"}
            )
        if request.method == "DELETE":
            return httpx.Response(204)
        raise AssertionError(f"Unhandled request {request.method} {request.url}")

    client = build_management_client(handler)
    keys = client.list_management_api_keys()
    assert keys.results[0].public_key == "manage_pub_abc"

    created = client.create_management_api_key({"description": "Ops key"})
    assert created.secret_key == "manage_sec_xyz"

    detail = client.get_management_api_key("api-key-1")
    assert detail.key == "api-key-1"

    updated = client.update_management_api_key("api-key-1", {"description": "Updated"})
    assert updated.description == "Updated"

    client.delete_management_api_key("api-key-1")
    assert captured["paths"][0][1].endswith("/permissions/management-api/api-keys/")
    assert captured["paths"][-1][0] == "DELETE"


def test_flux_api_key_lifecycle():
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
            captured["bodies"].append(json.loads(request.content.decode()))
            return httpx.Response(
                200, json=FLUX_API_KEY_JSON | {"description": "Updated Flux Key"}
            )
        if request.method == "DELETE":
            return httpx.Response(204)
        raise AssertionError("Unexpected call")

    client = build_management_client(handler)
    keys = client.list_flux_api_keys()
    assert keys.results[0].public_key == "flux_pub_abc"

    created = client.create_flux_api_key({"description": "Flux key"})
    assert created.secret_key == "flux_sec_xyz"

    detail = client.get_flux_api_key("flux-key-1")
    assert detail.key == "flux-key-1"

    updated = client.update_flux_api_key(
        "flux-key-1", {"description": "Updated Flux Key"}
    )
    assert updated.description == "Updated Flux Key"

    client.delete_flux_api_key("flux-key-1")
    assert captured["paths"][0][1].endswith("/permissions/flux-api/api-keys/")
    assert captured["paths"][-1][0] == "DELETE"


def test_management_role_crud():
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

    client = build_management_client(handler)
    roles = client.list_management_roles()
    assert roles.results[0].name == "Editors"

    created = client.create_management_role({"name": "Editors"})
    assert created.key == "role-1"

    detail = client.get_management_role("role-1")
    assert detail.full_access is False

    updated = client.update_management_role("role-1", {"description": "Updated"})
    assert updated.description == "Updated"

    client.delete_management_role("role-1")
    assert captured[0].endswith("/permissions/management-api/roles/")
    assert captured[-1].endswith("/permissions/management-api/roles/role-1/")


def test_management_role_permissions_workflow():
    recorded: list[tuple[str, str]] = []
    bodies: list[dict[str, Any]] = []

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
            bodies.append(body)
            return httpx.Response(201, json=PERMISSION_OBJECT_JSON | body)
        if request.method == "POST" and request.url.path.endswith(
            "/permissions/batch/"
        ):
            body = json.loads(request.content.decode())
            bodies.append(body)
            return httpx.Response(200, json=body)
        if request.method == "POST":
            body = json.loads(request.content.decode())
            bodies.append(body)
            return httpx.Response(201, json=ROLE_PERMISSION_JSON | body)
        if request.method == "DELETE" and request.url.path.endswith("/permissions/"):
            return httpx.Response(204)
        if request.method == "DELETE" and request.url.path.endswith(
            "/permissions/objects/"
        ):
            bodies.append(json.loads(request.content.decode()))
            return httpx.Response(204)
        raise AssertionError("Unexpected request")

    client = build_management_client(handler)
    permissions = client.list_management_role_permissions("role-1")
    assert permissions[0].content_type == "resources"

    created = client.upsert_management_role_permission("role-1", ROLE_PERMISSION_JSON)
    assert created.actions == ["read", "update"]

    client.delete_management_role_permission("role-1", "resources")

    replaced = client.replace_management_role_permissions(
        "role-1", [ROLE_PERMISSION_JSON]
    )
    assert replaced[0].all_objects is True

    objects = client.list_management_permission_objects(
        "role-1", content_type="folder-items"
    )
    assert objects[0].object_key == "folder-1"

    added = client.add_management_permission_object("role-1", PERMISSION_OBJECT_JSON)
    assert added.object_key == "folder-1"

    client.delete_management_permission_object("role-1", PERMISSION_OBJECT_JSON)

    assert any("/permissions/batch/" in path for _, path in recorded)
    assert any(
        body.get("content_type") == "folder-items"
        for body in bodies
        if isinstance(body, dict)
    )


def test_flux_role_crud_and_permissions():
    captured: list[str] = []
    bodies: list[Any] = []

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
        if request.method == "POST" and request.url.path.endswith(
            "/permissions/objects/"
        ):
            body = json.loads(request.content.decode())
            bodies.append(body)
            return httpx.Response(201, json=FLUX_PERMISSION_OBJECT_JSON | body)
        if request.method == "POST" and request.url.path.endswith(
            "/permissions/batch/"
        ):
            body = json.loads(request.content.decode())
            bodies.append(body)
            return httpx.Response(200, json=body)
        if request.method == "POST" and request.url.path.endswith("/permissions/"):
            body = json.loads(request.content.decode())
            bodies.append(body)
            return httpx.Response(201, json=FLUX_ROLE_PERMISSION_JSON | body)
        if request.method == "POST":
            return httpx.Response(201, json=FLUX_ROLE_JSON)
        if request.method == "GET" and request.url.path.endswith(
            "/permissions/objects/"
        ):
            return httpx.Response(200, json=[FLUX_PERMISSION_OBJECT_JSON])
        if request.method == "GET" and request.url.path.endswith("/permissions/"):
            return httpx.Response(200, json=[FLUX_ROLE_PERMISSION_JSON])
        if request.method == "GET":
            return httpx.Response(200, json=FLUX_ROLE_JSON)
        if request.method == "PUT":
            patch = json.loads(request.content.decode())
            return httpx.Response(200, json=FLUX_ROLE_JSON | patch)
        if request.method == "DELETE" and request.url.path.endswith(
            "/permissions/objects/"
        ):
            bodies.append(json.loads(request.content.decode()))
            return httpx.Response(204)
        if request.method == "DELETE":
            return httpx.Response(204)
        raise AssertionError("Unexpected request")

    client = build_management_client(handler)
    roles = client.list_flux_roles()
    assert roles.results[0].key == "flux-role-1"

    created = client.create_flux_role({"name": "Flux Readers"})
    assert created.name == "Flux Readers"

    detail = client.get_flux_role("flux-role-1")
    assert detail.description == "Read blog APIs"

    updated = client.update_flux_role("flux-role-1", {"description": "Updated Flux"})
    assert updated.description == "Updated Flux"

    perms = client.list_flux_role_permissions("flux-role-1")
    assert perms[0].content_type == "flux-apis"

    upserted = client.upsert_flux_role_permission(
        "flux-role-1", FLUX_ROLE_PERMISSION_JSON
    )
    assert upserted.actions == FLUX_ROLE_PERMISSION_JSON["actions"]

    client.delete_flux_role_permission("flux-role-1", "flux-apis")

    replaced = client.replace_flux_role_permissions(
        "flux-role-1", [FLUX_ROLE_PERMISSION_JSON]
    )
    assert replaced[0].all_objects is False

    objects = client.list_flux_permission_objects(
        "flux-role-1", content_type="flux-apis"
    )
    assert objects[0].object_key == "api-1"

    added = client.add_flux_permission_object(
        "flux-role-1", FLUX_PERMISSION_OBJECT_JSON
    )
    assert added.object_key == "api-1"

    client.delete_flux_permission_object("flux-role-1", FLUX_PERMISSION_OBJECT_JSON)

    client.delete_flux_role("flux-role-1")
    assert captured[0].endswith("/permissions/flux-api/roles/")
    assert captured[-1].endswith("/permissions/flux-api/roles/flux-role-1/")


def test_list_environments_handles_array():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[ENVIRONMENT_JSON])

    client = build_management_client(handler)
    envs = client.list_environments(ORG_KEY, PROJECT_KEY)
    assert envs[0].host == "prod.fxns.io"


def test_locale_crud_flow():
    captured: list[tuple[str, str]] = []
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append((request.method, request.url.path))
        if request.method == "GET" and request.url.path.endswith("/locales/"):
            return httpx.Response(200, json=[LOCALE_JSON])
        if request.method == "POST":
            bodies.append(json.loads(request.content.decode()))
            return httpx.Response(201, json=LOCALE_JSON)
        if request.method == "GET":
            return httpx.Response(200, json=LOCALE_JSON)
        if request.method == "PUT":
            update = json.loads(request.content.decode())
            bodies.append(update)
            return httpx.Response(200, json=LOCALE_JSON | update)
        if request.method == "DELETE":
            return httpx.Response(204)
        raise AssertionError("Unexpected locale request")

    client = build_management_client(handler)
    locales = client.list_locales()
    assert locales[0].code == "fr"

    created = client.create_locale(
        {"name": "Spanish", "code": "es", "is_default": False}
    )
    assert created.name == "Français"

    detail = client.get_locale("fr")
    assert detail.is_default is False

    updated = client.update_locale("fr", {"name": "French", "is_default": True})
    assert updated.name == "French"
    assert updated.is_default is True

    client.delete_locale("fr")
    assert captured[0][1].endswith("/locales/")
    assert captured[-1][0] == "DELETE"
    assert bodies[0]["code"] == "es"


def test_list_resources_returns_model():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        payload = {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [RESOURCE_JSON],
        }
        return httpx.Response(200, json=payload)

    client = build_management_client(handler)
    response = client.list_resources("folder-1")
    assert response.count == 1
    assert response.results[0].key == "resource-1"
    assert captured["path"] == "/v1/env123/folders/folder-1/resources/"


def test_create_resource_supports_component_param():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(201, json=RESOURCE_JSON)

    client = build_management_client(handler)
    result = client.create_resource(
        "folder-1", {"data": {"title": "Hello"}}, component="comp-1"
    )
    assert result.key == "resource-1"
    assert "component=comp-1" in captured["url"]
    assert captured["body"]["data"]["title"] == "Hello"


def test_create_resource_with_external_id():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode())
        resource_json = {**RESOURCE_JSON, "external_id": "ext-1"}
        return httpx.Response(201, json=resource_json)

    client = build_management_client(handler)
    result = client.create_resource(
        "folder-1", {"data": {"title": "Hello"}}, external_id="ext-1"
    )
    assert result.key == "resource-1"
    assert result.external_id == "ext-1"
    assert captured["body"]["external_id"] == "ext-1"
    assert captured["body"]["data"]["title"] == "Hello"
    # external_id goes in the body, not in query params
    assert "external_id=" not in captured["url"]


def test_create_resource_with_component_and_external_id():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode())
        resource_json = {**RESOURCE_JSON, "external_id": "ext-1", "component": "comp-1"}
        return httpx.Response(201, json=resource_json)

    client = build_management_client(handler)
    result = client.create_resource(
        "folder-1",
        {"data": {"title": "Hello"}},
        component="comp-1",
        external_id="ext-1",
    )
    assert result.key == "resource-1"
    assert "component=comp-1" in captured["url"]
    assert captured["body"]["external_id"] == "ext-1"


def test_upsert_resource_sends_put_with_external_id():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode())
        resource_json = {**RESOURCE_JSON, "external_id": "my-ext-id"}
        return httpx.Response(200, json=resource_json)

    client = build_management_client(handler)
    result = client.upsert_resource(
        "folder-1",
        {"data": {"title": "Upserted"}},
        external_id="my-ext-id",
    )
    assert captured["method"] == "PUT"
    assert captured["url"].endswith("/resources/?external_id=my-ext-id")
    assert captured["body"]["data"]["title"] == "Upserted"
    assert result.key == "resource-1"
    assert result.external_id == "my-ext-id"


def test_upsert_resource_with_component():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        resource_json = {**RESOURCE_JSON, "external_id": "ext-2", "component": "comp-1"}
        return httpx.Response(201, json=resource_json)

    client = build_management_client(handler)
    result = client.upsert_resource(
        "folder-1",
        {"data": {"title": "New"}},
        external_id="ext-2",
        component="comp-1",
    )
    assert captured["method"] == "PUT"
    assert "external_id=ext-2" in captured["url"]
    assert "component=comp-1" in captured["url"]
    assert result.external_id == "ext-2"
    assert result.component == "comp-1"


def test_create_resource_without_external_id_omits_field_from_body():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(201, json=RESOURCE_JSON)

    client = build_management_client(handler)
    client.create_resource("folder-1", {"data": {"title": "Hello"}})
    assert "external_id" not in captured["body"]


def test_create_resource_does_not_mutate_original_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json=RESOURCE_JSON)

    client = build_management_client(handler)
    original = {"data": {"title": "Hello"}}
    client.create_resource("folder-1", original, external_id="ext-1")
    # original dict must not be modified
    assert "external_id" not in original


def test_create_resource_kwarg_overrides_payload_external_id():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        resource_json = {**RESOURCE_JSON, "external_id": "from-kwarg"}
        return httpx.Response(201, json=resource_json)

    client = build_management_client(handler)
    result = client.create_resource(
        "folder-1",
        {"data": {"title": "Hello"}, "external_id": "from-body"},
        external_id="from-kwarg",
    )
    assert captured["body"]["external_id"] == "from-kwarg"
    assert result.external_id == "from-kwarg"


def test_upsert_resource_does_not_put_external_id_in_body():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        captured["url"] = str(request.url)
        resource_json = {**RESOURCE_JSON, "external_id": "ext-1"}
        return httpx.Response(200, json=resource_json)

    client = build_management_client(handler)
    client.upsert_resource(
        "folder-1",
        {"data": {"title": "Hello"}},
        external_id="ext-1",
    )
    # upsert sends external_id as query param, not in body
    assert "external_id" not in captured["body"]
    assert "external_id=ext-1" in captured["url"]


def test_upsert_resource_accepts_folder_object():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        resource_json = {**RESOURCE_JSON, "external_id": "ext-1"}
        return httpx.Response(200, json=resource_json)

    client = build_management_client(handler)
    folder = FolderSummary.model_validate(FOLDER_JSON)
    result = client.upsert_resource(
        folder,
        {"data": {"title": "Via object"}},
        external_id="ext-1",
    )
    assert "folder-1" in captured["url"]
    assert result.external_id == "ext-1"


def test_resource_summary_parses_external_id():
    resource_with_ext = {**RESOURCE_JSON, "external_id": "my-ext"}
    summary = ResourceSummary.model_validate(resource_with_ext)
    assert summary.external_id == "my-ext"

    summary_without = ResourceSummary.model_validate(RESOURCE_JSON)
    assert summary_without.external_id is None


def test_resource_summary_parses_without_external_id_field():
    """Backward compatibility: API responses without external_id field parse OK."""
    raw = {k: v for k, v in RESOURCE_JSON.items() if k != "external_id"}
    summary = ResourceSummary.model_validate(raw)
    assert summary.external_id is None


# ---------------------------------------------------------------------------
# batch_upsert_resources
# ---------------------------------------------------------------------------


def test_batch_upsert_resources_success():
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        ext_id = str(request.url).split("external_id=")[1].split("&")[0]
        resource_json = {**RESOURCE_JSON, "external_id": ext_id}
        call_count += 1
        return httpx.Response(200, json=resource_json)

    client = build_management_client(handler)
    items = [
        BatchUpsertItem(external_id=f"ext-{i}", payload={"title": f"Item {i}"})
        for i in range(3)
    ]
    result = client.batch_upsert_resources("folder-1", items)

    assert isinstance(result, BatchUpsertResult)
    assert result.success_count == 3
    assert result.failure_count == 0
    assert result.has_failures is False
    assert result.total == 3
    assert call_count == 3
    returned_ext_ids = {r.external_id for r in result.succeeded}
    assert returned_ext_ids == {"ext-0", "ext-1", "ext-2"}


def test_batch_upsert_resources_empty_list():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("handler should not be called")

    client = build_management_client(handler)
    result = client.batch_upsert_resources("folder-1", [])

    assert result.success_count == 0
    assert result.failure_count == 0
    assert result.total == 0
    assert result.has_failures is False


def test_batch_upsert_resources_partial_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        ext_id = str(request.url).split("external_id=")[1].split("&")[0]
        # Fail requests where external_id ends with "1" (index 1)
        if ext_id == "ext-1":
            return httpx.Response(
                400, json={"message": "Bad request", "error_code": "validation_error"}
            )
        resource_json = {**RESOURCE_JSON, "external_id": ext_id}
        return httpx.Response(200, json=resource_json)

    client = build_management_client(handler)
    items = [
        BatchUpsertItem(external_id=f"ext-{i}", payload={"title": f"Item {i}"})
        for i in range(3)
    ]
    result = client.batch_upsert_resources("folder-1", items)

    assert result.success_count == 2
    assert result.failure_count == 1
    assert result.has_failures is True
    assert len(result.failed) == 1
    error = result.failed[0]
    assert isinstance(error, BatchItemError)
    assert error.external_id == "ext-1"
    assert isinstance(error.exception, FoxnoseAPIError)
    assert error.exception.status_code == 400


def test_batch_upsert_resources_fail_fast():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400, json={"message": "Bad request", "error_code": "validation_error"}
        )

    client = build_management_client(handler)
    items = [
        BatchUpsertItem(external_id=f"ext-{i}", payload={"title": f"Item {i}"})
        for i in range(5)
    ]
    with pytest.raises(FoxnoseAPIError) as exc_info:
        client.batch_upsert_resources("folder-1", items, fail_fast=True)
    assert exc_info.value.status_code == 400


def test_batch_upsert_resources_max_concurrency():
    import threading

    peak = 0
    current = 0
    lock = threading.Lock()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal peak, current
        with lock:
            current += 1
            if current > peak:
                peak = current
        import time

        time.sleep(0.05)
        with lock:
            current -= 1
        ext_id = str(request.url).split("external_id=")[1].split("&")[0]
        return httpx.Response(200, json={**RESOURCE_JSON, "external_id": ext_id})

    client = build_management_client(handler)
    items = [
        BatchUpsertItem(external_id=f"ext-{i}", payload={"title": f"Item {i}"})
        for i in range(6)
    ]
    result = client.batch_upsert_resources("folder-1", items, max_concurrency=2)
    assert result.success_count == 6
    assert peak <= 2


def test_batch_upsert_resources_progress_callback():
    def handler(request: httpx.Request) -> httpx.Response:
        ext_id = str(request.url).split("external_id=")[1].split("&")[0]
        return httpx.Response(200, json={**RESOURCE_JSON, "external_id": ext_id})

    progress_calls: list[tuple[int, int]] = []

    client = build_management_client(handler)
    items = [
        BatchUpsertItem(external_id=f"ext-{i}", payload={"title": f"Item {i}"})
        for i in range(3)
    ]
    result = client.batch_upsert_resources(
        "folder-1",
        items,
        on_progress=lambda done, total: progress_calls.append((done, total)),
    )
    assert result.success_count == 3
    assert len(progress_calls) == 3
    # All calls should have total=3
    assert all(total == 3 for _, total in progress_calls)
    # Completed counts should cover 1, 2, 3
    completed_values = sorted(done for done, _ in progress_calls)
    assert completed_values == [1, 2, 3]


def test_batch_upsert_resources_with_component():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(str(request.url))
        ext_id = str(request.url).split("external_id=")[1].split("&")[0]
        return httpx.Response(200, json={**RESOURCE_JSON, "external_id": ext_id})

    client = build_management_client(handler)
    items = [
        BatchUpsertItem(
            external_id="ext-1", payload={"title": "Item"}, component="comp-1"
        )
    ]
    result = client.batch_upsert_resources("folder-1", items)
    assert result.success_count == 1
    assert "component=comp-1" in captured[0]
    assert "external_id=ext-1" in captured[0]


def test_batch_upsert_resources_rejects_zero_concurrency():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=RESOURCE_JSON)

    client = build_management_client(handler)
    items = [BatchUpsertItem(external_id="ext-1", payload={"title": "Item"})]
    with pytest.raises(ValueError, match="max_concurrency must be at least 1"):
        client.batch_upsert_resources("folder-1", items, max_concurrency=0)


def test_publish_revision_uses_nested_path():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(200, json=REVISION_JSON)

    client = build_management_client(handler)
    revision = client.publish_revision("folder-1", "resource-1", "rev-1")
    assert revision.key == "rev-1"
    assert (
        captured["path"]
        == "/v1/env123/folders/folder-1/resources/resource-1/revisions/rev-1/publish/"
    )


def test_get_revision_data_returns_dict():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"title": "Sample"})

    client = build_management_client(handler)
    data = client.get_revision_data("folder-1", "resource-1", "rev-2")
    assert data["title"] == "Sample"


def test_list_components_and_versions():
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

    client = build_management_client(handler)
    components = client.list_components()
    assert components.results[0].key == "component-1"
    versions = client.list_component_versions("component-1")
    assert versions.results[0].key == "ver-1"
    assert recorded[0].endswith("/components/")
    assert recorded[1].endswith("/components/component-1/model/versions/")


def test_create_component_version_with_copy():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(201, json=VERSION_JSON)

    client = build_management_client(handler)
    version = client.create_component_version(
        "component-1", {"name": "Draft"}, copy_from="ver-0"
    )
    assert version.key == "ver-1"
    assert "copy_from=ver-0" in captured["url"]
    assert captured["body"]["name"] == "Draft"


def test_publish_component_version_and_fields():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.setdefault("paths", []).append(str(request.url))
        if request.url.path.endswith("/publish/"):
            return httpx.Response(
                200, json=VERSION_JSON | {"published_at": "2024-01-11T00:00:00Z"}
            )
        return httpx.Response(
            200,
            json={"count": 1, "next": None, "previous": None, "results": [FIELD_JSON]},
        )

    client = build_management_client(handler)
    published = client.publish_component_version("component-1", "ver-1")
    assert published.published_at is not None
    fields = client.list_component_fields(
        "component-1", "ver-1", params={"path": "title"}
    )
    assert fields.results[0].path == "title"
    assert captured["paths"][0].endswith(
        "/components/component-1/model/versions/ver-1/publish/"
    )
    assert "path=title" in captured["paths"][1]


def test_update_component_field_uses_field_endpoint():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json=FIELD_JSON | {"name": "Updated"})

    client = build_management_client(handler)
    field = client.update_component_field(
        "component-1", "ver-1", "title", {"name": "Updated"}
    )
    assert field.name == "Updated"
    assert (
        "/components/component-1/model/versions/ver-1/schema/tree/field/"
        in captured["url"]
    )
    assert "path=title" in captured["url"]


def test_folder_version_and_field_management():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(str(request.url))
        if request.method == "GET" and request.url.path.endswith("/schema/tree/"):
            return httpx.Response(
                200,
                json={
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [FIELD_JSON],
                },
            )
        if request.method == "POST" and request.url.path.endswith("/schema/tree/"):
            body = json.loads(request.content.decode())
            return httpx.Response(201, json=FIELD_JSON | {"name": body["name"]})
        if request.method == "POST" and request.url.path.endswith(
            "/schema/tree/field/"
        ):
            body = json.loads(request.content.decode())
            return httpx.Response(200, json=FIELD_JSON | {"name": body["name"]})
        return httpx.Response(200, json=VERSION_JSON)

    client = build_management_client(handler)
    version = client.create_folder_version("folder-1", {"name": "Draft"})
    assert version.key == "ver-1"

    fields = client.list_folder_fields("folder-1", "ver-1")
    assert fields.results[0].key == "title"

    created = client.create_folder_field(
        "folder-1", "ver-1", {"name": "Title", "key": "title"}
    )
    assert created.name == "Title"
    assert captured[0].endswith("/folders/folder-1/model/versions/")
    assert "/folders/folder-1/model/versions/ver-1/schema/tree/" in captured[1]


def test_add_api_folder_supports_route_descriptions():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["method"] = request.method
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(
            201,
            json=API_FOLDER_JSON | captured["body"],
        )

    client = build_management_client(handler)
    added = client.add_api_folder(
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


def test_update_api_folder_supports_route_descriptions():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["method"] = request.method
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json=API_FOLDER_JSON | captured["body"],
        )

    client = build_management_client(handler)
    updated = client.update_api_folder(
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


def test_flux_client_builds_paths_correctly():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.setdefault("paths", []).append(request.url.path)
        if request.url.path.endswith("/_router"):
            return httpx.Response(200, json={"api": "blog", "routes": []})
        if request.url.path.endswith("/_schema"):
            return httpx.Response(
                200,
                json={
                    "json_schema": {"type": "object"},
                    "searchable_fields": ["title"],
                    "non_searchable_fields": [],
                    "path": "/blog/articles",
                    "actions": ["get_many", "get_one"],
                },
            )
        return httpx.Response(200, json={"results": []})

    flux = FluxClient(
        base_url="https://env.fxns.io",
        api_prefix="blog",
        auth=SimpleKeyAuth("pub", "secret"),
    )
    flux._transport = HttpTransport(  # type: ignore[attr-defined]
        config=FoxnoseConfig(base_url="https://env.fxns.io"),
        auth=SimpleKeyAuth("pub", "secret"),
        sync_client=httpx.Client(
            base_url="https://env.fxns.io", transport=httpx.MockTransport(handler)
        ),
    )
    flux.list_resources("articles")
    flux.search("articles", body={"where": {"$": {"all_of": []}}})
    router = flux.get_router()
    schema = flux.get_schema("articles")
    assert router["api"] == "blog"
    assert schema["path"] == "/blog/articles"
    assert captured["paths"] == [
        "/blog/articles",
        "/blog/articles/_search",
        "/blog/_router",
        "/blog/articles/_schema",
    ]


# ---------------------------------------------------------------------------
# _resolve_key unit tests
# ---------------------------------------------------------------------------


def test_resolve_key_with_string():
    assert _resolve_key("some-key") == "some-key"


def test_resolve_key_with_model_object():
    folder = FolderSummary.model_validate(FOLDER_JSON)
    assert _resolve_key(folder) == "folder-1"


def test_resolve_key_raises_for_object_without_key():
    class NoKey:
        pass

    with pytest.raises(TypeError, match="object with a 'key' attribute"):
        _resolve_key(NoKey())  # type: ignore[arg-type]


def test_resolve_key_raises_for_non_string_key():
    class BadKey:
        key = 42

    with pytest.raises(TypeError, match="'key' to be a string"):
        _resolve_key(BadKey())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Model objects as identifiers (sync client)
# ---------------------------------------------------------------------------


def test_list_resources_accepts_folder_object():
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

    client = build_management_client(handler)
    folder = FolderSummary.model_validate(FOLDER_JSON)
    response = client.list_resources(folder)
    assert response.count == 1
    assert captured["path"] == "/v1/env123/folders/folder-1/resources/"


def test_get_revision_accepts_model_objects():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(200, json=REVISION_JSON)

    client = build_management_client(handler)
    folder = FolderSummary.model_validate(FOLDER_JSON)
    resource = ResourceSummary.model_validate(RESOURCE_JSON)
    revision = RevisionSummary.model_validate(REVISION_JSON)
    result = client.get_revision(folder, resource, revision)
    assert result.key == "rev-1"
    assert (
        captured["path"]
        == "/v1/env123/folders/folder-1/resources/resource-1/revisions/rev-1/"
    )


def test_create_resource_accepts_folder_object():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(201, json=RESOURCE_JSON)

    client = build_management_client(handler)
    folder = FolderSummary.model_validate(FOLDER_JSON)
    result = client.create_resource(folder, {"data": {"title": "Hello"}})
    assert result.key == "resource-1"
    assert "/folders/folder-1/resources/" in captured["url"]
