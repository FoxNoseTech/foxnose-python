from __future__ import annotations

from typing import Any, Mapping

from ..auth import AuthStrategy
from ..config import FoxnoseConfig, RetryConfig
from ..http import HttpTransport
from .models import (
    APIFolderList,
    APIFolderSummary,
    APIInfo,
    APIList,
    ComponentList,
    ComponentSummary,
    EnvironmentList,
    EnvironmentSummary,
    FieldList,
    FieldSummary,
    FluxAPIKeyList,
    FluxAPIKeySummary,
    FluxRoleList,
    FluxRoleSummary,
    FolderList,
    FolderSummary,
    LocaleList,
    LocaleSummary,
    ManagementAPIKeyList,
    ManagementAPIKeySummary,
    ManagementRoleList,
    ManagementRoleSummary,
    OrganizationList,
    OrganizationPlanStatus,
    OrganizationSummary,
    OrganizationUsage,
    ProjectList,
    ProjectSummary,
    RegionInfo,
    ResourceList,
    ResourceSummary,
    RevisionList,
    RevisionSummary,
    RolePermission,
    RolePermissionObject,
    SchemaVersionList,
    SchemaVersionSummary,
)


class _ManagementPathsMixin:
    """Mixin providing URL path helpers for Management API clients."""

    environment_key: str

    # Organization paths
    def _org_root(self, org_key: str) -> str:
        return f"/organizations/{org_key}"

    def _projects_base(self, org_key: str) -> str:
        return f"{self._org_root(org_key)}/projects"

    def _project_root(self, org_key: str, project_key: str) -> str:
        return f"{self._projects_base(org_key)}/{project_key}"

    def _environments_base(self, org_key: str, project_key: str) -> str:
        return f"{self._project_root(org_key, project_key)}/environments"

    def _environment_root(
        self, org_key: str, project_key: str, environment_key: str
    ) -> str:
        return f"{self._environments_base(org_key, project_key)}/{environment_key}"

    # Folder paths
    def _folders_root(self) -> str:
        return f"/v1/{self.environment_key}/folders"

    def _folders_tree_root(self) -> str:
        return f"{self._folders_root()}/tree"

    def _folders_tree_item(self) -> str:
        return f"{self._folders_tree_root()}/folder"

    def _folder_root(self, folder_key: str) -> str:
        return f"{self._folders_root()}/{folder_key}"

    def _folder_versions_base(self, folder_key: str) -> str:
        return f"{self._folder_root(folder_key)}/model/versions"

    def _folder_schema_tree(self, folder_key: str, version_key: str) -> str:
        return f"{self._folder_versions_base(folder_key)}/{version_key}/schema/tree"

    # Component paths
    def _components_root(self) -> str:
        return f"/v1/{self.environment_key}/components"

    def _component_root(self, component_key: str) -> str:
        return f"{self._components_root()}/{component_key}"

    def _component_versions_base(self, component_key: str) -> str:
        return f"{self._component_root(component_key)}/model/versions"

    def _component_schema_tree(self, component_key: str, version_key: str) -> str:
        return (
            f"{self._component_versions_base(component_key)}/{version_key}/schema/tree"
        )

    # Resource paths
    def _resource_base(self, folder_key: str) -> str:
        return f"{self._folder_root(folder_key)}/resources"

    def _revision_base(self, folder_key: str, resource_key: str) -> str:
        return f"{self._resource_base(folder_key)}/{resource_key}/revisions"

    # Management API key paths
    def _management_api_keys_root(self) -> str:
        return f"/v1/{self.environment_key}/permissions/management-api/api-keys"

    def _management_api_key_root(self, api_key: str) -> str:
        return f"{self._management_api_keys_root()}/{api_key}"

    # Flux API key paths
    def _flux_api_keys_root(self) -> str:
        return f"/v1/{self.environment_key}/permissions/flux-api/api-keys"

    def _flux_api_key_root(self, api_key: str) -> str:
        return f"{self._flux_api_keys_root()}/{api_key}"

    # API management paths
    def _apis_root(self) -> str:
        return f"/v1/{self.environment_key}/api"

    def _api_root(self, api_key: str) -> str:
        return f"{self._apis_root()}/{api_key}"

    def _api_folders_root(self, api_key: str) -> str:
        return f"{self._api_root(api_key)}/folders"

    # Management role paths
    def _management_roles_root(self) -> str:
        return f"/v1/{self.environment_key}/permissions/management-api/roles"

    def _management_role_root(self, role_key: str) -> str:
        return f"{self._management_roles_root()}/{role_key}"

    def _role_permissions_root(self, role_key: str) -> str:
        return f"{self._management_role_root(role_key)}/permissions"

    def _role_permissions_batch(self, role_key: str) -> str:
        return f"{self._role_permissions_root(role_key)}/batch"

    def _role_permission_objects_root(self, role_key: str) -> str:
        return f"{self._management_role_root(role_key)}/permissions/objects"

    # Flux role paths
    def _flux_roles_root(self) -> str:
        return f"/v1/{self.environment_key}/permissions/flux-api/roles"

    def _flux_role_root(self, role_key: str) -> str:
        return f"{self._flux_roles_root()}/{role_key}"

    def _flux_role_permissions_root(self, role_key: str) -> str:
        return f"{self._flux_role_root(role_key)}/permissions"

    def _flux_role_permissions_batch(self, role_key: str) -> str:
        return f"{self._flux_role_permissions_root(role_key)}/batch"

    def _flux_role_permission_objects_root(self, role_key: str) -> str:
        return f"{self._flux_role_root(role_key)}/permissions/objects"

    # Locale paths
    def _locales_root(self) -> str:
        return f"/v1/{self.environment_key}/locales"

    def _locale_root(self, code: str) -> str:
        return f"{self._locales_root()}/{code}"

    @staticmethod
    def _coerce_environment_list(payload: Any) -> EnvironmentList:
        if isinstance(payload, dict):
            if "results" in payload and isinstance(payload["results"], list):
                items = payload["results"]
            else:
                items = [payload]
        elif isinstance(payload, list):
            items = payload
        else:
            items = [payload]
        return [EnvironmentSummary.model_validate(item) for item in items]


class ManagementClient(_ManagementPathsMixin):
    """Synchronous client for the Foxnose Management API."""

    def __init__(
        self,
        *,
        base_url: str = "https://api.foxnose.net",
        environment_key: str,
        auth: AuthStrategy,
        timeout: float = 30.0,
        retry_config: RetryConfig | None = None,
        default_headers: Mapping[str, str] | None = None,
    ) -> None:
        if not environment_key:
            raise ValueError("environment_key must be provided")
        self.environment_key = environment_key
        config = FoxnoseConfig(
            base_url=base_url,
            timeout=timeout,
            default_headers=default_headers,
        )
        self._transport = HttpTransport(
            config=config, auth=auth, retry_config=retry_config
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Any | None = None,
        headers: Mapping[str, str] | None = None,
        parse_json: bool = True,
    ) -> Any:
        """Low-level escape hatch for calling arbitrary endpoints."""
        return self._transport.request(
            method,
            path,
            params=params,
            json_body=json_body,
            headers=headers,
            parse_json=parse_json,
        )

    # ------------------------------------------------------------------ #
    # Organization operations
    # ------------------------------------------------------------------ #

    def list_organizations(self) -> OrganizationList:
        """List all organizations accessible to the authenticated user."""
        payload = self.request("GET", "/organizations/") or []
        if not isinstance(payload, list):
            payload = [payload]
        return [OrganizationSummary.model_validate(item) for item in payload]

    def get_organization(self, org_key: str) -> OrganizationSummary:
        """Retrieve details for a specific organization.

        Args:
            org_key: Unique identifier of the organization.
        """
        data = self.request("GET", f"{self._org_root(org_key)}/")
        return OrganizationSummary.model_validate(data)

    def update_organization(
        self, org_key: str, payload: Mapping[str, Any]
    ) -> OrganizationSummary:
        """Update an organization's settings.

        Args:
            org_key: Unique identifier of the organization.
            payload: Fields to update (e.g., name, settings).
        """
        data = self.request("PUT", f"{self._org_root(org_key)}/", json_body=payload)
        return OrganizationSummary.model_validate(data)

    def list_regions(self) -> list[RegionInfo]:
        """List all available deployment regions."""
        payload = self.request("GET", "/regions/") or []
        if not isinstance(payload, list):
            payload = [payload]
        return [RegionInfo.model_validate(item) for item in payload]

    def get_available_plans(self) -> OrganizationPlanStatus:
        """Retrieve the list of available subscription plans."""
        data = self.request("GET", "/plans/")
        return OrganizationPlanStatus.model_validate(data)

    def get_organization_plan(self, org_key: str) -> OrganizationPlanStatus:
        """Get the current subscription plan for an organization.

        Args:
            org_key: Unique identifier of the organization.
        """
        data = self.request("GET", f"{self._org_root(org_key)}/plan/")
        return OrganizationPlanStatus.model_validate(data)

    def set_organization_plan(
        self, org_key: str, plan_code: str
    ) -> OrganizationPlanStatus:
        """Change the subscription plan for an organization.

        Args:
            org_key: Unique identifier of the organization.
            plan_code: Code of the plan to activate.
        """
        data = self.request("POST", f"{self._org_root(org_key)}/plan/{plan_code}/")
        return OrganizationPlanStatus.model_validate(data)

    def get_organization_usage(self, org_key: str) -> OrganizationUsage:
        """Retrieve usage statistics for an organization.

        Args:
            org_key: Unique identifier of the organization.
        """
        data = self.request("GET", f"{self._org_root(org_key)}/usage/")
        return OrganizationUsage.model_validate(data)

    # ------------------------------------------------------------------ #
    # Management API key operations
    # ------------------------------------------------------------------ #

    def list_management_api_keys(
        self, *, params: Mapping[str, Any] | None = None
    ) -> ManagementAPIKeyList:
        """List all Management API keys in the environment.

        Args:
            params: Optional query parameters for filtering/pagination.
        """
        data = self.request(
            "GET", f"{self._management_api_keys_root()}/", params=params
        )
        return ManagementAPIKeyList.model_validate(data)

    def create_management_api_key(
        self, payload: Mapping[str, Any]
    ) -> ManagementAPIKeySummary:
        """Create a new Management API key.

        Args:
            payload: Key configuration including name and role assignments.
        """
        data = self.request(
            "POST", f"{self._management_api_keys_root()}/", json_body=payload
        )
        return ManagementAPIKeySummary.model_validate(data)

    def get_management_api_key(self, key: str) -> ManagementAPIKeySummary:
        """Retrieve details for a specific Management API key.

        Args:
            key: Unique identifier of the API key.
        """
        data = self.request("GET", f"{self._management_api_key_root(key)}/")
        return ManagementAPIKeySummary.model_validate(data)

    def update_management_api_key(
        self, key: str, payload: Mapping[str, Any]
    ) -> ManagementAPIKeySummary:
        """Update a Management API key.

        Args:
            key: Unique identifier of the API key.
            payload: Fields to update.
        """
        data = self.request(
            "PUT", f"{self._management_api_key_root(key)}/", json_body=payload
        )
        return ManagementAPIKeySummary.model_validate(data)

    def delete_management_api_key(self, key: str) -> None:
        """Delete a Management API key.

        Args:
            key: Unique identifier of the API key to delete.
        """
        self.request(
            "DELETE", f"{self._management_api_key_root(key)}/", parse_json=False
        )

    def list_flux_api_keys(
        self, *, params: Mapping[str, Any] | None = None
    ) -> FluxAPIKeyList:
        """List all Flux API keys in the environment.

        Args:
            params: Optional query parameters for filtering/pagination.
        """
        data = self.request("GET", f"{self._flux_api_keys_root()}/", params=params)
        return FluxAPIKeyList.model_validate(data)

    def create_flux_api_key(self, payload: Mapping[str, Any]) -> FluxAPIKeySummary:
        """Create a new Flux API key.

        Args:
            payload: Key configuration including name and role assignments.
        """
        data = self.request("POST", f"{self._flux_api_keys_root()}/", json_body=payload)
        return FluxAPIKeySummary.model_validate(data)

    def get_flux_api_key(self, key: str) -> FluxAPIKeySummary:
        """Retrieve details for a specific Flux API key.

        Args:
            key: Unique identifier of the API key.
        """
        data = self.request("GET", f"{self._flux_api_key_root(key)}/")
        return FluxAPIKeySummary.model_validate(data)

    def update_flux_api_key(
        self, key: str, payload: Mapping[str, Any]
    ) -> FluxAPIKeySummary:
        """Update a Flux API key.

        Args:
            key: Unique identifier of the API key.
            payload: Fields to update.
        """
        data = self.request(
            "PUT", f"{self._flux_api_key_root(key)}/", json_body=payload
        )
        return FluxAPIKeySummary.model_validate(data)

    def delete_flux_api_key(self, key: str) -> None:
        """Delete a Flux API key.

        Args:
            key: Unique identifier of the API key to delete.
        """
        self.request("DELETE", f"{self._flux_api_key_root(key)}/", parse_json=False)

    # ------------------------------------------------------------------ #
    # API management operations
    # ------------------------------------------------------------------ #

    def list_apis(self, *, params: Mapping[str, Any] | None = None) -> APIList:
        """List all APIs in the environment.

        Args:
            params: Optional query parameters for filtering/pagination.
        """
        data = self.request("GET", f"{self._apis_root()}/", params=params)
        return APIList.model_validate(data)

    def create_api(self, payload: Mapping[str, Any]) -> APIInfo:
        """Create a new API endpoint configuration.

        Args:
            payload: API configuration including name and settings.
        """
        data = self.request("POST", f"{self._apis_root()}/", json_body=payload)
        return APIInfo.model_validate(data)

    def get_api(self, api_key: str) -> APIInfo:
        """Retrieve details for a specific API.

        Args:
            api_key: Unique identifier of the API.
        """
        data = self.request("GET", f"{self._api_root(api_key)}/")
        return APIInfo.model_validate(data)

    def update_api(self, api_key: str, payload: Mapping[str, Any]) -> APIInfo:
        """Update an API configuration.

        Args:
            api_key: Unique identifier of the API.
            payload: Fields to update.
        """
        data = self.request("PUT", f"{self._api_root(api_key)}/", json_body=payload)
        return APIInfo.model_validate(data)

    def delete_api(self, api_key: str) -> None:
        """Delete an API.

        Args:
            api_key: Unique identifier of the API to delete.
        """
        self.request("DELETE", f"{self._api_root(api_key)}/", parse_json=False)

    def list_api_folders(
        self, api_key: str, *, params: Mapping[str, Any] | None = None
    ) -> APIFolderList:
        """List folders exposed through an API.

        Args:
            api_key: Unique identifier of the API.
            params: Optional query parameters for filtering/pagination.
        """
        data = self.request("GET", f"{self._api_folders_root(api_key)}/", params=params)
        return APIFolderList.model_validate(data)

    def add_api_folder(
        self,
        api_key: str,
        folder_key: str,
        *,
        allowed_methods: list[str] | None = None,
    ) -> APIFolderSummary:
        """Add a folder to an API.

        Args:
            api_key: Unique identifier of the API.
            folder_key: Unique identifier of the folder to add.
            allowed_methods: HTTP methods allowed for this folder (e.g., ["GET", "POST"]).
        """
        payload: dict[str, Any] = {"folder": folder_key}
        if allowed_methods:
            payload["allowed_methods"] = allowed_methods
        data = self.request(
            "POST", f"{self._api_folders_root(api_key)}/", json_body=payload
        )
        return APIFolderSummary.model_validate(data)

    def get_api_folder(self, api_key: str, folder_key: str) -> APIFolderSummary:
        """Retrieve details for a folder within an API.

        Args:
            api_key: Unique identifier of the API.
            folder_key: Unique identifier of the folder.
        """
        data = self.request("GET", f"{self._api_folders_root(api_key)}/{folder_key}/")
        return APIFolderSummary.model_validate(data)

    def update_api_folder(
        self,
        api_key: str,
        folder_key: str,
        *,
        allowed_methods: list[str] | None = None,
    ) -> APIFolderSummary:
        """Update a folder's configuration within an API.

        Args:
            api_key: Unique identifier of the API.
            folder_key: Unique identifier of the folder.
            allowed_methods: HTTP methods allowed for this folder.
        """
        payload: dict[str, Any] = {}
        if allowed_methods is not None:
            payload["allowed_methods"] = allowed_methods
        data = self.request(
            "PUT", f"{self._api_folders_root(api_key)}/{folder_key}/", json_body=payload
        )
        return APIFolderSummary.model_validate(data)

    def remove_api_folder(self, api_key: str, folder_key: str) -> None:
        """Remove a folder from an API.

        Args:
            api_key: Unique identifier of the API.
            folder_key: Unique identifier of the folder to remove.
        """
        self.request(
            "DELETE",
            f"{self._api_folders_root(api_key)}/{folder_key}/",
            parse_json=False,
        )

    # ------------------------------------------------------------------ #
    # Management role operations
    # ------------------------------------------------------------------ #

    def list_management_roles(
        self, *, params: Mapping[str, Any] | None = None
    ) -> ManagementRoleList:
        """List all Management API roles in the environment.

        Args:
            params: Optional query parameters for filtering/pagination.
        """
        data = self.request("GET", f"{self._management_roles_root()}/", params=params)
        return ManagementRoleList.model_validate(data)

    def create_management_role(
        self, payload: Mapping[str, Any]
    ) -> ManagementRoleSummary:
        """Create a new Management API role.

        Args:
            payload: Role configuration including name and permissions.
        """
        data = self.request(
            "POST", f"{self._management_roles_root()}/", json_body=payload
        )
        return ManagementRoleSummary.model_validate(data)

    def get_management_role(self, role_key: str) -> ManagementRoleSummary:
        """Retrieve details for a specific Management API role.

        Args:
            role_key: Unique identifier of the role.
        """
        data = self.request("GET", f"{self._management_role_root(role_key)}/")
        return ManagementRoleSummary.model_validate(data)

    def update_management_role(
        self, role_key: str, payload: Mapping[str, Any]
    ) -> ManagementRoleSummary:
        """Update a Management API role.

        Args:
            role_key: Unique identifier of the role.
            payload: Fields to update.
        """
        data = self.request(
            "PUT", f"{self._management_role_root(role_key)}/", json_body=payload
        )
        return ManagementRoleSummary.model_validate(data)

    def delete_management_role(self, role_key: str) -> None:
        """Delete a Management API role.

        Args:
            role_key: Unique identifier of the role to delete.
        """
        self.request(
            "DELETE", f"{self._management_role_root(role_key)}/", parse_json=False
        )

    def list_management_role_permissions(self, role_key: str) -> list[RolePermission]:
        """List all permissions assigned to a Management API role.

        Args:
            role_key: Unique identifier of the role.
        """
        payload = self.request("GET", f"{self._role_permissions_root(role_key)}/") or []
        return [RolePermission.model_validate(item) for item in payload]

    def upsert_management_role_permission(
        self,
        role_key: str,
        payload: Mapping[str, Any],
    ) -> RolePermission:
        """Create or update a permission for a Management API role.

        Args:
            role_key: Unique identifier of the role.
            payload: Permission configuration.
        """
        data = self.request(
            "POST", f"{self._role_permissions_root(role_key)}/", json_body=payload
        )
        return RolePermission.model_validate(data)

    def delete_management_role_permission(
        self, role_key: str, content_type: str
    ) -> None:
        """Delete a permission from a Management API role.

        Args:
            role_key: Unique identifier of the role.
            content_type: Content type of the permission to delete.
        """
        params = {"content_type": content_type}
        self.request(
            "DELETE",
            f"{self._role_permissions_root(role_key)}/",
            params=params,
            parse_json=False,
        )

    def replace_management_role_permissions(
        self,
        role_key: str,
        permissions: list[Mapping[str, Any]],
    ) -> list[RolePermission]:
        """Replace all permissions for a Management API role.

        Args:
            role_key: Unique identifier of the role.
            permissions: List of permission configurations to set.
        """
        data = (
            self.request(
                "POST",
                f"{self._role_permissions_batch(role_key)}/",
                json_body=permissions,
            )
            or []
        )
        return [RolePermission.model_validate(item) for item in data]

    def list_management_permission_objects(
        self, role_key: str, *, content_type: str
    ) -> list[RolePermissionObject]:
        """List permission objects for a Management API role.

        Args:
            role_key: Unique identifier of the role.
            content_type: Content type to filter by.
        """
        params = {"content_type": content_type}
        payload = (
            self.request(
                "GET", f"{self._role_permission_objects_root(role_key)}/", params=params
            )
            or []
        )
        return [RolePermissionObject.model_validate(item) for item in payload]

    def add_management_permission_object(
        self,
        role_key: str,
        payload: Mapping[str, Any],
    ) -> RolePermissionObject:
        """Add a permission object to a Management API role.

        Args:
            role_key: Unique identifier of the role.
            payload: Permission object configuration.
        """
        data = self.request(
            "POST",
            f"{self._role_permission_objects_root(role_key)}/",
            json_body=payload,
        )
        return RolePermissionObject.model_validate(data)

    def delete_management_permission_object(
        self,
        role_key: str,
        payload: Mapping[str, Any],
    ) -> None:
        """Delete a permission object from a Management API role.

        Args:
            role_key: Unique identifier of the role.
            payload: Permission object to delete.
        """
        self.request(
            "DELETE",
            f"{self._role_permission_objects_root(role_key)}/",
            json_body=payload,
            parse_json=False,
        )

    def list_flux_roles(
        self, *, params: Mapping[str, Any] | None = None
    ) -> FluxRoleList:
        """List all Flux API roles in the environment.

        Args:
            params: Optional query parameters for filtering/pagination.
        """
        data = self.request("GET", f"{self._flux_roles_root()}/", params=params)
        return FluxRoleList.model_validate(data)

    def create_flux_role(self, payload: Mapping[str, Any]) -> FluxRoleSummary:
        """Create a new Flux API role.

        Args:
            payload: Role configuration including name and permissions.
        """
        data = self.request("POST", f"{self._flux_roles_root()}/", json_body=payload)
        return FluxRoleSummary.model_validate(data)

    def get_flux_role(self, role_key: str) -> FluxRoleSummary:
        """Retrieve details for a specific Flux API role.

        Args:
            role_key: Unique identifier of the role.
        """
        data = self.request("GET", f"{self._flux_role_root(role_key)}/")
        return FluxRoleSummary.model_validate(data)

    def update_flux_role(
        self, role_key: str, payload: Mapping[str, Any]
    ) -> FluxRoleSummary:
        """Update a Flux API role.

        Args:
            role_key: Unique identifier of the role.
            payload: Fields to update.
        """
        data = self.request(
            "PUT", f"{self._flux_role_root(role_key)}/", json_body=payload
        )
        return FluxRoleSummary.model_validate(data)

    def delete_flux_role(self, role_key: str) -> None:
        """Delete a Flux API role.

        Args:
            role_key: Unique identifier of the role to delete.
        """
        self.request("DELETE", f"{self._flux_role_root(role_key)}/", parse_json=False)

    def list_flux_role_permissions(self, role_key: str) -> list[RolePermission]:
        """List all permissions assigned to a Flux API role.

        Args:
            role_key: Unique identifier of the role.
        """
        payload = (
            self.request("GET", f"{self._flux_role_permissions_root(role_key)}/") or []
        )
        return [RolePermission.model_validate(item) for item in payload]

    def upsert_flux_role_permission(
        self, role_key: str, payload: Mapping[str, Any]
    ) -> RolePermission:
        """Create or update a permission for a Flux API role.

        Args:
            role_key: Unique identifier of the role.
            payload: Permission configuration.
        """
        data = self.request(
            "POST", f"{self._flux_role_permissions_root(role_key)}/", json_body=payload
        )
        return RolePermission.model_validate(data)

    def delete_flux_role_permission(self, role_key: str, content_type: str) -> None:
        """Delete a permission from a Flux API role.

        Args:
            role_key: Unique identifier of the role.
            content_type: Content type of the permission to delete.
        """
        self.request(
            "DELETE",
            f"{self._flux_role_permissions_root(role_key)}/",
            params={"content_type": content_type},
            parse_json=False,
        )

    def replace_flux_role_permissions(
        self,
        role_key: str,
        permissions: list[Mapping[str, Any]],
    ) -> list[RolePermission]:
        """Replace all permissions for a Flux API role.

        Args:
            role_key: Unique identifier of the role.
            permissions: List of permission configurations to set.
        """
        payload = (
            self.request(
                "POST",
                f"{self._flux_role_permissions_batch(role_key)}/",
                json_body=permissions,
            )
            or []
        )
        return [RolePermission.model_validate(item) for item in payload]

    def list_flux_permission_objects(
        self, role_key: str, *, content_type: str
    ) -> list[RolePermissionObject]:
        """List permission objects for a Flux API role.

        Args:
            role_key: Unique identifier of the role.
            content_type: Content type to filter by.
        """
        payload = (
            self.request(
                "GET",
                f"{self._flux_role_permission_objects_root(role_key)}/",
                params={"content_type": content_type},
            )
            or []
        )
        return [RolePermissionObject.model_validate(item) for item in payload]

    def add_flux_permission_object(
        self, role_key: str, payload: Mapping[str, Any]
    ) -> RolePermissionObject:
        """Add a permission object to a Flux API role.

        Args:
            role_key: Unique identifier of the role.
            payload: Permission object configuration.
        """
        data = self.request(
            "POST",
            f"{self._flux_role_permission_objects_root(role_key)}/",
            json_body=payload,
        )
        return RolePermissionObject.model_validate(data)

    def delete_flux_permission_object(
        self, role_key: str, payload: Mapping[str, Any]
    ) -> None:
        """Delete a permission object from a Flux API role.

        Args:
            role_key: Unique identifier of the role.
            payload: Permission object to delete.
        """
        self.request(
            "DELETE",
            f"{self._flux_role_permission_objects_root(role_key)}/",
            json_body=payload,
            parse_json=False,
        )

    # ------------------------------------------------------------------ #
    # Folder operations
    # ------------------------------------------------------------------ #

    def list_folders(self, *, params: Mapping[str, Any] | None = None) -> FolderList:
        """List all folders in the environment.

        Args:
            params: Optional query parameters for filtering/pagination.
        """
        path = f"{self._folders_tree_root()}/"
        data = self.request("GET", path, params=params)
        return FolderList.model_validate(data)

    def get_folder(self, folder_key: str) -> FolderSummary:
        """Retrieve details for a specific folder by key.

        Args:
            folder_key: Unique identifier of the folder.
        """
        data = self.request(
            "GET", f"{self._folders_tree_item()}/", params={"key": folder_key}
        )
        return FolderSummary.model_validate(data)

    def get_folder_by_path(self, path: str) -> FolderSummary:
        """Retrieve details for a folder by its path.

        Args:
            path: Hierarchical path to the folder (e.g., "parent/child").
        """
        data = self.request(
            "GET",
            f"{self._folders_tree_item()}/",
            params={"path": path},
        )
        return FolderSummary.model_validate(data)

    def list_folder_tree(
        self,
        *,
        key: str | None = None,
        mode: str | None = None,
    ) -> FolderList:
        """List folders as a hierarchical tree.

        Args:
            key: Optional root folder key to start from.
            mode: Tree traversal mode.
        """
        params: dict[str, Any] = {}
        if key:
            params["key"] = key
        if mode:
            params["mode"] = mode
        path = f"{self._folders_tree_root()}/"
        data = self.request("GET", path, params=params or None)
        return FolderList.model_validate(data)

    def create_folder(self, payload: Mapping[str, Any]) -> FolderSummary:
        """Create a new folder.

        Args:
            payload: Folder configuration including name, alias, folder_type, and content_type.
        """
        data = self.request("POST", f"{self._folders_tree_root()}/", json_body=payload)
        return FolderSummary.model_validate(data)

    def update_folder(
        self, folder_key: str, payload: Mapping[str, Any]
    ) -> FolderSummary:
        """Update a folder's configuration.

        Args:
            folder_key: Unique identifier of the folder.
            payload: Fields to update.
        """
        data = self.request(
            "PUT",
            f"{self._folders_tree_item()}/",
            params={"key": folder_key},
            json_body=payload,
        )
        return FolderSummary.model_validate(data)

    def delete_folder(self, folder_key: str) -> None:
        """Delete a folder.

        Args:
            folder_key: Unique identifier of the folder to delete.
        """
        self.request(
            "DELETE",
            f"{self._folders_tree_item()}/",
            params={"key": folder_key},
            parse_json=False,
        )

    # ------------------------------------------------------------------ #
    # Project operations
    # ------------------------------------------------------------------ #

    def list_projects(
        self, org_key: str, *, params: Mapping[str, Any] | None = None
    ) -> ProjectList:
        """List all projects in an organization.

        Args:
            org_key: Unique identifier of the organization.
            params: Optional query parameters for filtering/pagination.
        """
        data = self.request("GET", f"{self._projects_base(org_key)}/", params=params)
        return ProjectList.model_validate(data)

    def get_project(self, org_key: str, project_key: str) -> ProjectSummary:
        """Retrieve details for a specific project.

        Args:
            org_key: Unique identifier of the organization.
            project_key: Unique identifier of the project.
        """
        data = self.request("GET", f"{self._project_root(org_key, project_key)}/")
        return ProjectSummary.model_validate(data)

    def create_project(
        self, org_key: str, payload: Mapping[str, Any]
    ) -> ProjectSummary:
        """Create a new project in an organization.

        Args:
            org_key: Unique identifier of the organization.
            payload: Project configuration including name and settings.
        """
        data = self.request(
            "POST", f"{self._projects_base(org_key)}/", json_body=payload
        )
        return ProjectSummary.model_validate(data)

    def update_project(
        self, org_key: str, project_key: str, payload: Mapping[str, Any]
    ) -> ProjectSummary:
        """Update a project's configuration.

        Args:
            org_key: Unique identifier of the organization.
            project_key: Unique identifier of the project.
            payload: Fields to update.
        """
        data = self.request(
            "PUT", f"{self._project_root(org_key, project_key)}/", json_body=payload
        )
        return ProjectSummary.model_validate(data)

    def delete_project(self, org_key: str, project_key: str) -> None:
        """Delete a project.

        Args:
            org_key: Unique identifier of the organization.
            project_key: Unique identifier of the project to delete.
        """
        self.request(
            "DELETE", f"{self._project_root(org_key, project_key)}/", parse_json=False
        )

    # ------------------------------------------------------------------ #
    # Environment operations
    # ------------------------------------------------------------------ #

    def list_environments(self, org_key: str, project_key: str) -> EnvironmentList:
        """List all environments in a project.

        Args:
            org_key: Unique identifier of the organization.
            project_key: Unique identifier of the project.
        """
        payload = self.request(
            "GET", f"{self._environments_base(org_key, project_key)}/"
        )
        return self._coerce_environment_list(payload)

    def get_environment(
        self, org_key: str, project_key: str, env_key: str
    ) -> EnvironmentSummary:
        """Retrieve details for a specific environment.

        Args:
            org_key: Unique identifier of the organization.
            project_key: Unique identifier of the project.
            env_key: Unique identifier of the environment.
        """
        data = self.request(
            "GET", f"{self._environment_root(org_key, project_key, env_key)}/"
        )
        return EnvironmentSummary.model_validate(data)

    def create_environment(
        self,
        org_key: str,
        project_key: str,
        payload: Mapping[str, Any],
    ) -> EnvironmentSummary:
        """Create a new environment in a project.

        Args:
            org_key: Unique identifier of the organization.
            project_key: Unique identifier of the project.
            payload: Environment configuration including name and region.
        """
        data = self.request(
            "POST",
            f"{self._environments_base(org_key, project_key)}/",
            json_body=payload,
        )
        return EnvironmentSummary.model_validate(data)

    def update_environment(
        self,
        org_key: str,
        project_key: str,
        env_key: str,
        payload: Mapping[str, Any],
    ) -> EnvironmentSummary:
        """Update an environment's configuration.

        Args:
            org_key: Unique identifier of the organization.
            project_key: Unique identifier of the project.
            env_key: Unique identifier of the environment.
            payload: Fields to update.
        """
        data = self.request(
            "PUT",
            f"{self._environment_root(org_key, project_key, env_key)}/",
            json_body=payload,
        )
        return EnvironmentSummary.model_validate(data)

    def delete_environment(self, org_key: str, project_key: str, env_key: str) -> None:
        """Delete an environment.

        Args:
            org_key: Unique identifier of the organization.
            project_key: Unique identifier of the project.
            env_key: Unique identifier of the environment to delete.
        """
        self.request(
            "DELETE",
            f"{self._environment_root(org_key, project_key, env_key)}/",
            parse_json=False,
        )

    def toggle_environment(
        self, org_key: str, project_key: str, env_key: str, *, is_enabled: bool
    ) -> None:
        """Enable or disable an environment.

        Args:
            org_key: Unique identifier of the organization.
            project_key: Unique identifier of the project.
            env_key: Unique identifier of the environment.
            is_enabled: Whether the environment should be enabled.
        """
        self.request(
            "POST",
            f"{self._environment_root(org_key, project_key, env_key)}/toggle/",
            json_body={"is_enabled": is_enabled},
            parse_json=False,
        )

    def update_environment_protection(
        self,
        org_key: str,
        project_key: str,
        env_key: str,
        *,
        protection_level: str,
        protection_reason: str | None = None,
    ) -> EnvironmentSummary:
        """Set protection level for an environment.

        Args:
            org_key: Unique identifier of the organization.
            project_key: Unique identifier of the project.
            env_key: Unique identifier of the environment.
            protection_level: Protection level (e.g., "none", "read_only", "locked").
            protection_reason: Optional reason for the protection.
        """
        payload: dict[str, Any] = {"protection_level": protection_level}
        if protection_reason is not None:
            payload["protection_reason"] = protection_reason
        data = self.request(
            "PATCH",
            f"{self._environment_root(org_key, project_key, env_key)}/protection/",
            json_body=payload,
        )
        return EnvironmentSummary.model_validate(data)

    def clear_environment_protection(
        self, org_key: str, project_key: str, env_key: str
    ) -> EnvironmentSummary:
        """Remove protection from an environment.

        Args:
            org_key: Unique identifier of the organization.
            project_key: Unique identifier of the project.
            env_key: Unique identifier of the environment.
        """
        return self.update_environment_protection(
            org_key,
            project_key,
            env_key,
            protection_level="none",
        )

    # ------------------------------------------------------------------ #
    # Locale operations
    # ------------------------------------------------------------------ #

    def list_locales(self) -> LocaleList:
        """List all locales configured in the environment."""
        payload = self.request("GET", f"{self._locales_root()}/") or []
        return [LocaleSummary.model_validate(item) for item in payload]

    def create_locale(self, payload: Mapping[str, Any]) -> LocaleSummary:
        """Create a new locale.

        Args:
            payload: Locale configuration including code and name.
        """
        data = self.request("POST", f"{self._locales_root()}/", json_body=payload)
        return LocaleSummary.model_validate(data)

    def get_locale(self, code: str) -> LocaleSummary:
        """Retrieve details for a specific locale.

        Args:
            code: Locale code (e.g., "en-US", "de-DE").
        """
        data = self.request("GET", f"{self._locale_root(code)}/")
        return LocaleSummary.model_validate(data)

    def update_locale(self, code: str, payload: Mapping[str, Any]) -> LocaleSummary:
        """Update a locale's configuration.

        Args:
            code: Locale code.
            payload: Fields to update.
        """
        data = self.request("PUT", f"{self._locale_root(code)}/", json_body=payload)
        return LocaleSummary.model_validate(data)

    def delete_locale(self, code: str) -> None:
        """Delete a locale.

        Args:
            code: Locale code to delete.
        """
        self.request("DELETE", f"{self._locale_root(code)}/", parse_json=False)

    # ------------------------------------------------------------------ #
    # Component operations
    # ------------------------------------------------------------------ #

    def list_components(
        self, *, params: Mapping[str, Any] | None = None
    ) -> ComponentList:
        """List all reusable components in the environment.

        Args:
            params: Optional query parameters for filtering/pagination.
        """
        data = self.request("GET", f"{self._components_root()}/", params=params)
        return ComponentList.model_validate(data)

    def get_component(self, component_key: str) -> ComponentSummary:
        """Retrieve details for a specific component.

        Args:
            component_key: Unique identifier of the component.
        """
        data = self.request("GET", f"{self._component_root(component_key)}/")
        return ComponentSummary.model_validate(data)

    def create_component(self, payload: Mapping[str, Any]) -> ComponentSummary:
        """Create a new reusable component.

        Args:
            payload: Component configuration including name and content_type.
        """
        data = self.request("POST", f"{self._components_root()}/", json_body=payload)
        return ComponentSummary.model_validate(data)

    def update_component(
        self, component_key: str, payload: Mapping[str, Any]
    ) -> ComponentSummary:
        """Update a component's configuration.

        Args:
            component_key: Unique identifier of the component.
            payload: Fields to update.
        """
        data = self.request(
            "PUT", f"{self._component_root(component_key)}/", json_body=payload
        )
        return ComponentSummary.model_validate(data)

    def delete_component(self, component_key: str) -> None:
        """Delete a component.

        Args:
            component_key: Unique identifier of the component to delete.
        """
        self.request(
            "DELETE", f"{self._component_root(component_key)}/", parse_json=False
        )

    def list_component_versions(
        self,
        component_key: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> SchemaVersionList:
        """List all schema versions for a component.

        Args:
            component_key: Unique identifier of the component.
            params: Optional query parameters for filtering/pagination.
        """
        data = self.request(
            "GET", f"{self._component_versions_base(component_key)}/", params=params
        )
        return SchemaVersionList.model_validate(data)

    def create_component_version(
        self,
        component_key: str,
        payload: Mapping[str, Any],
        *,
        copy_from: str | None = None,
    ) -> SchemaVersionSummary:
        """Create a new schema version for a component.

        Args:
            component_key: Unique identifier of the component.
            payload: Version configuration including name.
            copy_from: Optional version key to copy schema from.
        """
        params = {"copy_from": copy_from} if copy_from else None
        data = self.request(
            "POST",
            f"{self._component_versions_base(component_key)}/",
            params=params,
            json_body=payload,
        )
        return SchemaVersionSummary.model_validate(data)

    def get_component_version(
        self,
        component_key: str,
        version_key: str,
        *,
        include_schema: bool | None = None,
    ) -> SchemaVersionSummary:
        """Retrieve details for a specific component version.

        Args:
            component_key: Unique identifier of the component.
            version_key: Unique identifier of the version.
            include_schema: Whether to include the full schema definition.
        """
        params = (
            {"include_schema": str(include_schema).lower()}
            if include_schema is not None
            else None
        )
        data = self.request(
            "GET",
            f"{self._component_versions_base(component_key)}/{version_key}/",
            params=params,
        )
        return SchemaVersionSummary.model_validate(data)

    def publish_component_version(
        self,
        component_key: str,
        version_key: str,
    ) -> SchemaVersionSummary:
        """Publish a component version, making it available for use.

        Args:
            component_key: Unique identifier of the component.
            version_key: Unique identifier of the version to publish.
        """
        data = self.request(
            "POST",
            f"{self._component_versions_base(component_key)}/{version_key}/publish/",
            json_body=None,
        )
        return SchemaVersionSummary.model_validate(data)

    def update_component_version(
        self,
        component_key: str,
        version_key: str,
        payload: Mapping[str, Any],
    ) -> SchemaVersionSummary:
        """Update a component version's configuration.

        Args:
            component_key: Unique identifier of the component.
            version_key: Unique identifier of the version.
            payload: Fields to update.
        """
        data = self.request(
            "PUT",
            f"{self._component_versions_base(component_key)}/{version_key}/",
            json_body=payload,
        )
        return SchemaVersionSummary.model_validate(data)

    def delete_component_version(self, component_key: str, version_key: str) -> None:
        """Delete a component version.

        Args:
            component_key: Unique identifier of the component.
            version_key: Unique identifier of the version to delete.
        """
        self.request(
            "DELETE",
            f"{self._component_versions_base(component_key)}/{version_key}/",
            parse_json=False,
        )

    def list_component_fields(
        self,
        component_key: str,
        version_key: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> FieldList:
        """List all fields in a component version's schema.

        Args:
            component_key: Unique identifier of the component.
            version_key: Unique identifier of the version.
            params: Optional query parameters for filtering.
        """
        data = self.request(
            "GET",
            f"{self._component_schema_tree(component_key, version_key)}/",
            params=params,
        )
        return FieldList.model_validate(data)

    def create_component_field(
        self,
        component_key: str,
        version_key: str,
        payload: Mapping[str, Any],
    ) -> FieldSummary:
        """Add a new field to a component version's schema.

        Args:
            component_key: Unique identifier of the component.
            version_key: Unique identifier of the version.
            payload: Field configuration including name and type.
        """
        data = self.request(
            "POST",
            f"{self._component_schema_tree(component_key, version_key)}/",
            json_body=payload,
        )
        return FieldSummary.model_validate(data)

    def get_component_field(
        self,
        component_key: str,
        version_key: str,
        field_path: str,
    ) -> FieldSummary:
        """Retrieve details for a specific field in a component schema.

        Args:
            component_key: Unique identifier of the component.
            version_key: Unique identifier of the version.
            field_path: Path to the field (e.g., "title" or "metadata.author").
        """
        data = self.request(
            "GET",
            f"{self._component_schema_tree(component_key, version_key)}/field/",
            params={"path": field_path},
        )
        return FieldSummary.model_validate(data)

    def update_component_field(
        self,
        component_key: str,
        version_key: str,
        field_path: str,
        payload: Mapping[str, Any],
    ) -> FieldSummary:
        """Update a field in a component schema.

        Args:
            component_key: Unique identifier of the component.
            version_key: Unique identifier of the version.
            field_path: Path to the field.
            payload: Fields to update.
        """
        data = self.request(
            "PUT",
            f"{self._component_schema_tree(component_key, version_key)}/field/",
            params={"path": field_path},
            json_body=payload,
        )
        return FieldSummary.model_validate(data)

    def delete_component_field(
        self, component_key: str, version_key: str, field_path: str
    ) -> None:
        """Delete a field from a component schema.

        Args:
            component_key: Unique identifier of the component.
            version_key: Unique identifier of the version.
            field_path: Path to the field to delete.
        """
        self.request(
            "DELETE",
            f"{self._component_schema_tree(component_key, version_key)}/field/",
            params={"path": field_path},
            parse_json=False,
        )

    # ------------------------------------------------------------------ #
    # Collection folder schema operations
    # ------------------------------------------------------------------ #

    def list_folder_versions(
        self,
        folder_key: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> SchemaVersionList:
        """List all schema versions for a collection folder.

        Args:
            folder_key: Unique identifier of the folder.
            params: Optional query parameters for filtering/pagination.
        """
        data = self.request(
            "GET", f"{self._folder_versions_base(folder_key)}/", params=params
        )
        return SchemaVersionList.model_validate(data)

    def create_folder_version(
        self,
        folder_key: str,
        payload: Mapping[str, Any],
        *,
        copy_from: str | None = None,
    ) -> SchemaVersionSummary:
        """Create a new schema version for a collection folder.

        Args:
            folder_key: Unique identifier of the folder.
            payload: Version configuration including name.
            copy_from: Optional version key to copy schema from.
        """
        params = {"copy_from": copy_from} if copy_from else None
        data = self.request(
            "POST",
            f"{self._folder_versions_base(folder_key)}/",
            params=params,
            json_body=payload,
        )
        return SchemaVersionSummary.model_validate(data)

    def get_folder_version(
        self,
        folder_key: str,
        version_key: str,
        *,
        include_schema: bool | None = None,
    ) -> SchemaVersionSummary:
        """Retrieve details for a specific folder schema version.

        Args:
            folder_key: Unique identifier of the folder.
            version_key: Unique identifier of the version.
            include_schema: Whether to include the full schema definition.
        """
        params = (
            {"include_schema": str(include_schema).lower()}
            if include_schema is not None
            else None
        )
        data = self.request(
            "GET",
            f"{self._folder_versions_base(folder_key)}/{version_key}/",
            params=params,
        )
        return SchemaVersionSummary.model_validate(data)

    def update_folder_version(
        self,
        folder_key: str,
        version_key: str,
        payload: Mapping[str, Any],
    ) -> SchemaVersionSummary:
        """Update a folder schema version's configuration.

        Args:
            folder_key: Unique identifier of the folder.
            version_key: Unique identifier of the version.
            payload: Fields to update.
        """
        data = self.request(
            "PUT",
            f"{self._folder_versions_base(folder_key)}/{version_key}/",
            json_body=payload,
        )
        return SchemaVersionSummary.model_validate(data)

    def delete_folder_version(self, folder_key: str, version_key: str) -> None:
        """Delete a folder schema version.

        Args:
            folder_key: Unique identifier of the folder.
            version_key: Unique identifier of the version to delete.
        """
        self.request(
            "DELETE",
            f"{self._folder_versions_base(folder_key)}/{version_key}/",
            parse_json=False,
        )

    def publish_folder_version(
        self,
        folder_key: str,
        version_key: str,
    ) -> SchemaVersionSummary:
        """Publish a folder schema version, making it active for the folder.

        Args:
            folder_key: Unique identifier of the folder.
            version_key: Unique identifier of the version to publish.
        """
        data = self.request(
            "POST",
            f"{self._folder_versions_base(folder_key)}/{version_key}/publish/",
        )
        return SchemaVersionSummary.model_validate(data)

    def list_folder_fields(
        self,
        folder_key: str,
        version_key: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> FieldList:
        """List all fields in a folder schema version.

        Args:
            folder_key: Unique identifier of the folder.
            version_key: Unique identifier of the version.
            params: Optional query parameters for filtering.
        """
        data = self.request(
            "GET",
            f"{self._folder_schema_tree(folder_key, version_key)}/",
            params=params,
        )
        return FieldList.model_validate(data)

    def create_folder_field(
        self,
        folder_key: str,
        version_key: str,
        payload: Mapping[str, Any],
    ) -> FieldSummary:
        """Add a new field to a folder schema version.

        Args:
            folder_key: Unique identifier of the folder.
            version_key: Unique identifier of the version.
            payload: Field configuration including name and type.
        """
        data = self.request(
            "POST",
            f"{self._folder_schema_tree(folder_key, version_key)}/",
            json_body=payload,
        )
        return FieldSummary.model_validate(data)

    def get_folder_field(
        self,
        folder_key: str,
        version_key: str,
        field_path: str,
    ) -> FieldSummary:
        """Retrieve details for a specific field in a folder schema.

        Args:
            folder_key: Unique identifier of the folder.
            version_key: Unique identifier of the version.
            field_path: Path to the field (e.g., "title" or "metadata.author").
        """
        data = self.request(
            "GET",
            f"{self._folder_schema_tree(folder_key, version_key)}/field/",
            params={"path": field_path},
        )
        return FieldSummary.model_validate(data)

    def update_folder_field(
        self,
        folder_key: str,
        version_key: str,
        field_path: str,
        payload: Mapping[str, Any],
    ) -> FieldSummary:
        """Update a field in a folder schema.

        Args:
            folder_key: Unique identifier of the folder.
            version_key: Unique identifier of the version.
            field_path: Path to the field.
            payload: Fields to update.
        """
        data = self.request(
            "PUT",
            f"{self._folder_schema_tree(folder_key, version_key)}/field/",
            params={"path": field_path},
            json_body=payload,
        )
        return FieldSummary.model_validate(data)

    def delete_folder_field(
        self, folder_key: str, version_key: str, field_path: str
    ) -> None:
        """Delete a field from a folder schema.

        Args:
            folder_key: Unique identifier of the folder.
            version_key: Unique identifier of the version.
            field_path: Path to the field to delete.
        """
        self.request(
            "DELETE",
            f"{self._folder_schema_tree(folder_key, version_key)}/field/",
            params={"path": field_path},
            parse_json=False,
        )

    def list_resources(
        self,
        folder_key: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> ResourceList:
        """List resources inside a specific folder using limit/offset pagination."""
        path = f"{self._resource_base(folder_key)}/"
        data = self.request("GET", path, params=params)
        return ResourceList.model_validate(data)

    def get_resource(self, folder_key: str, resource_key: str) -> ResourceSummary:
        """Retrieve metadata for a specific resource."""
        path = f"{self._resource_base(folder_key)}/{resource_key}/"
        data = self.request("GET", path)
        return ResourceSummary.model_validate(data)

    def create_resource(
        self,
        folder_key: str,
        payload: Mapping[str, Any],
        *,
        component: str | None = None,
    ) -> ResourceSummary:
        """
        Create a new resource.

        Args:
            folder_key: Target folder key.
            payload: JSON payload that matches the folder/component schema.
            component: Optional component key for component-based folders.
        """

        params = {"component": component} if component else None
        data = self.request(
            "POST",
            f"{self._resource_base(folder_key)}/",
            params=params,
            json_body=payload,
        )
        return ResourceSummary.model_validate(data)

    def update_resource(
        self,
        folder_key: str,
        resource_key: str,
        payload: Mapping[str, Any],
    ) -> ResourceSummary:
        """Update a resource by creating a new revision payload."""
        path = f"{self._resource_base(folder_key)}/{resource_key}/"
        self.request("PUT", path, json_body=payload, parse_json=False)
        return self.get_resource(folder_key, resource_key)

    def delete_resource(self, folder_key: str, resource_key: str) -> None:
        """Delete a resource."""
        path = f"{self._resource_base(folder_key)}/{resource_key}/"
        self.request("DELETE", path, parse_json=False)

    def get_resource_data(
        self, folder_key: str, resource_key: str
    ) -> Mapping[str, Any]:
        """Fetch the published JSON data for a resource."""
        path = f"{self._resource_base(folder_key)}/{resource_key}/data/"
        return self.request("GET", path)

    def list_revisions(
        self,
        folder_key: str,
        resource_key: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> RevisionList:
        """List all revisions for a resource.

        Args:
            folder_key: Unique identifier of the folder.
            resource_key: Unique identifier of the resource.
            params: Optional query parameters for filtering/pagination.
        """
        path = f"{self._revision_base(folder_key, resource_key)}/"
        data = self.request("GET", path, params=params)
        return RevisionList.model_validate(data)

    def create_revision(
        self,
        folder_key: str,
        resource_key: str,
        payload: Mapping[str, Any],
    ) -> RevisionSummary:
        """Create a new revision for a resource.

        Args:
            folder_key: Unique identifier of the folder.
            resource_key: Unique identifier of the resource.
            payload: Revision data matching the folder schema.
        """
        path = f"{self._revision_base(folder_key, resource_key)}/"
        data = self.request("POST", path, json_body=payload)
        return RevisionSummary.model_validate(data)

    def get_revision(
        self,
        folder_key: str,
        resource_key: str,
        revision_key: str,
    ) -> RevisionSummary:
        """Retrieve details for a specific revision.

        Args:
            folder_key: Unique identifier of the folder.
            resource_key: Unique identifier of the resource.
            revision_key: Unique identifier of the revision.
        """
        path = f"{self._revision_base(folder_key, resource_key)}/{revision_key}/"
        data = self.request("GET", path)
        return RevisionSummary.model_validate(data)

    def update_revision(
        self,
        folder_key: str,
        resource_key: str,
        revision_key: str,
        payload: Mapping[str, Any],
    ) -> RevisionSummary:
        """Update a revision's data.

        Args:
            folder_key: Unique identifier of the folder.
            resource_key: Unique identifier of the resource.
            revision_key: Unique identifier of the revision.
            payload: Updated revision data.
        """
        path = f"{self._revision_base(folder_key, resource_key)}/{revision_key}/"
        data = self.request("PUT", path, json_body=payload)
        return RevisionSummary.model_validate(data)

    def delete_revision(
        self, folder_key: str, resource_key: str, revision_key: str
    ) -> None:
        """Delete a revision.

        Args:
            folder_key: Unique identifier of the folder.
            resource_key: Unique identifier of the resource.
            revision_key: Unique identifier of the revision to delete.
        """
        path = f"{self._revision_base(folder_key, resource_key)}/{revision_key}/"
        self.request("DELETE", path, parse_json=False)

    def publish_revision(
        self,
        folder_key: str,
        resource_key: str,
        revision_key: str,
        payload: Mapping[str, Any] | None = None,
    ) -> RevisionSummary:
        """Publish a revision, making it the active version of the resource.

        Args:
            folder_key: Unique identifier of the folder.
            resource_key: Unique identifier of the resource.
            revision_key: Unique identifier of the revision to publish.
            payload: Optional publish configuration.
        """
        path = (
            f"{self._revision_base(folder_key, resource_key)}/{revision_key}/publish/"
        )
        data = self.request("POST", path, json_body=payload)
        return RevisionSummary.model_validate(data)

    def validate_revision(
        self,
        folder_key: str,
        resource_key: str,
        revision_key: str,
    ) -> Mapping[str, Any]:
        """Validate a revision before publishing.

        Args:
            folder_key: Unique identifier of the folder.
            resource_key: Unique identifier of the resource.
            revision_key: Unique identifier of the revision.

        Returns:
            Validation result containing any errors found.
        """
        path = (
            f"{self._revision_base(folder_key, resource_key)}/{revision_key}/validate/"
        )
        return self.request("POST", path)

    def get_revision_data(
        self,
        folder_key: str,
        resource_key: str,
        revision_key: str,
    ) -> Mapping[str, Any]:
        """Fetch the JSON data for a specific revision.

        Args:
            folder_key: Unique identifier of the folder.
            resource_key: Unique identifier of the resource.
            revision_key: Unique identifier of the revision.
        """
        path = f"{self._revision_base(folder_key, resource_key)}/{revision_key}/data/"
        return self.request("GET", path)

    def close(self) -> None:
        """Close the HTTP transport and release resources."""
        self._transport.close()


class AsyncManagementClient(_ManagementPathsMixin):
    """Async variant of :class:`ManagementClient`."""

    def __init__(
        self,
        *,
        base_url: str = "https://api.foxnose.net",
        environment_key: str,
        auth: AuthStrategy,
        timeout: float = 30.0,
        retry_config: RetryConfig | None = None,
        default_headers: Mapping[str, str] | None = None,
    ) -> None:
        if not environment_key:
            raise ValueError("environment_key must be provided")
        self.environment_key = environment_key
        config = FoxnoseConfig(
            base_url=base_url,
            timeout=timeout,
            default_headers=default_headers,
        )
        self._transport = HttpTransport(
            config=config, auth=auth, retry_config=retry_config
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Any | None = None,
        headers: Mapping[str, str] | None = None,
        parse_json: bool = True,
    ) -> Any:
        return await self._transport.arequest(
            method,
            path,
            params=params,
            json_body=json_body,
            headers=headers,
            parse_json=parse_json,
        )

    # ------------------------------------------------------------------ #
    # Organization operations
    # ------------------------------------------------------------------ #

    async def list_organizations(self) -> OrganizationList:
        payload = await self.request("GET", "/organizations/") or []
        if not isinstance(payload, list):
            payload = [payload]
        return [OrganizationSummary.model_validate(item) for item in payload]

    async def get_organization(self, org_key: str) -> OrganizationSummary:
        data = await self.request("GET", f"{self._org_root(org_key)}/")
        return OrganizationSummary.model_validate(data)

    async def update_organization(
        self, org_key: str, payload: Mapping[str, Any]
    ) -> OrganizationSummary:
        data = await self.request(
            "PUT", f"{self._org_root(org_key)}/", json_body=payload
        )
        return OrganizationSummary.model_validate(data)

    async def list_regions(self) -> list[RegionInfo]:
        payload = await self.request("GET", "/regions/") or []
        if not isinstance(payload, list):
            payload = [payload]
        return [RegionInfo.model_validate(item) for item in payload]

    async def get_available_plans(self) -> OrganizationPlanStatus:
        data = await self.request("GET", "/plans/")
        return OrganizationPlanStatus.model_validate(data)

    async def get_organization_plan(self, org_key: str) -> OrganizationPlanStatus:
        data = await self.request("GET", f"{self._org_root(org_key)}/plan/")
        return OrganizationPlanStatus.model_validate(data)

    async def set_organization_plan(
        self, org_key: str, plan_code: str
    ) -> OrganizationPlanStatus:
        data = await self.request(
            "POST", f"{self._org_root(org_key)}/plan/{plan_code}/"
        )
        return OrganizationPlanStatus.model_validate(data)

    async def get_organization_usage(self, org_key: str) -> OrganizationUsage:
        data = await self.request("GET", f"{self._org_root(org_key)}/usage/")
        return OrganizationUsage.model_validate(data)

    # ------------------------------------------------------------------ #
    # Management API key operations
    # ------------------------------------------------------------------ #

    async def list_management_api_keys(
        self, *, params: Mapping[str, Any] | None = None
    ) -> ManagementAPIKeyList:
        data = await self.request(
            "GET", f"{self._management_api_keys_root()}/", params=params
        )
        return ManagementAPIKeyList.model_validate(data)

    async def create_management_api_key(
        self, payload: Mapping[str, Any]
    ) -> ManagementAPIKeySummary:
        data = await self.request(
            "POST", f"{self._management_api_keys_root()}/", json_body=payload
        )
        return ManagementAPIKeySummary.model_validate(data)

    async def get_management_api_key(self, key: str) -> ManagementAPIKeySummary:
        data = await self.request("GET", f"{self._management_api_key_root(key)}/")
        return ManagementAPIKeySummary.model_validate(data)

    async def update_management_api_key(
        self, key: str, payload: Mapping[str, Any]
    ) -> ManagementAPIKeySummary:
        data = await self.request(
            "PUT", f"{self._management_api_key_root(key)}/", json_body=payload
        )
        return ManagementAPIKeySummary.model_validate(data)

    async def delete_management_api_key(self, key: str) -> None:
        await self.request(
            "DELETE", f"{self._management_api_key_root(key)}/", parse_json=False
        )

    async def list_flux_api_keys(
        self, *, params: Mapping[str, Any] | None = None
    ) -> FluxAPIKeyList:
        data = await self.request(
            "GET", f"{self._flux_api_keys_root()}/", params=params
        )
        return FluxAPIKeyList.model_validate(data)

    async def create_flux_api_key(
        self, payload: Mapping[str, Any]
    ) -> FluxAPIKeySummary:
        data = await self.request(
            "POST", f"{self._flux_api_keys_root()}/", json_body=payload
        )
        return FluxAPIKeySummary.model_validate(data)

    async def get_flux_api_key(self, key: str) -> FluxAPIKeySummary:
        data = await self.request("GET", f"{self._flux_api_key_root(key)}/")
        return FluxAPIKeySummary.model_validate(data)

    async def update_flux_api_key(
        self, key: str, payload: Mapping[str, Any]
    ) -> FluxAPIKeySummary:
        data = await self.request(
            "PUT", f"{self._flux_api_key_root(key)}/", json_body=payload
        )
        return FluxAPIKeySummary.model_validate(data)

    async def delete_flux_api_key(self, key: str) -> None:
        await self.request(
            "DELETE", f"{self._flux_api_key_root(key)}/", parse_json=False
        )

    # ------------------------------------------------------------------ #
    # API management operations (async)
    # ------------------------------------------------------------------ #

    async def list_apis(self, *, params: Mapping[str, Any] | None = None) -> APIList:
        data = await self.request("GET", f"{self._apis_root()}/", params=params)
        return APIList.model_validate(data)

    async def create_api(self, payload: Mapping[str, Any]) -> APIInfo:
        data = await self.request("POST", f"{self._apis_root()}/", json_body=payload)
        return APIInfo.model_validate(data)

    async def get_api(self, api_key: str) -> APIInfo:
        data = await self.request("GET", f"{self._api_root(api_key)}/")
        return APIInfo.model_validate(data)

    async def update_api(self, api_key: str, payload: Mapping[str, Any]) -> APIInfo:
        data = await self.request(
            "PUT", f"{self._api_root(api_key)}/", json_body=payload
        )
        return APIInfo.model_validate(data)

    async def delete_api(self, api_key: str) -> None:
        await self.request("DELETE", f"{self._api_root(api_key)}/", parse_json=False)

    async def list_api_folders(
        self, api_key: str, *, params: Mapping[str, Any] | None = None
    ) -> APIFolderList:
        data = await self.request(
            "GET", f"{self._api_folders_root(api_key)}/", params=params
        )
        return APIFolderList.model_validate(data)

    async def add_api_folder(
        self,
        api_key: str,
        folder_key: str,
        *,
        allowed_methods: list[str] | None = None,
    ) -> APIFolderSummary:
        payload: dict[str, Any] = {"folder": folder_key}
        if allowed_methods:
            payload["allowed_methods"] = allowed_methods
        data = await self.request(
            "POST", f"{self._api_folders_root(api_key)}/", json_body=payload
        )
        return APIFolderSummary.model_validate(data)

    async def get_api_folder(self, api_key: str, folder_key: str) -> APIFolderSummary:
        data = await self.request(
            "GET", f"{self._api_folders_root(api_key)}/{folder_key}/"
        )
        return APIFolderSummary.model_validate(data)

    async def update_api_folder(
        self,
        api_key: str,
        folder_key: str,
        *,
        allowed_methods: list[str] | None = None,
    ) -> APIFolderSummary:
        payload: dict[str, Any] = {}
        if allowed_methods is not None:
            payload["allowed_methods"] = allowed_methods
        data = await self.request(
            "PUT", f"{self._api_folders_root(api_key)}/{folder_key}/", json_body=payload
        )
        return APIFolderSummary.model_validate(data)

    async def remove_api_folder(self, api_key: str, folder_key: str) -> None:
        await self.request(
            "DELETE",
            f"{self._api_folders_root(api_key)}/{folder_key}/",
            parse_json=False,
        )

    # ------------------------------------------------------------------ #
    # Management role operations
    # ------------------------------------------------------------------ #

    async def list_management_roles(
        self, *, params: Mapping[str, Any] | None = None
    ) -> ManagementRoleList:
        data = await self.request(
            "GET", f"{self._management_roles_root()}/", params=params
        )
        return ManagementRoleList.model_validate(data)

    async def create_management_role(
        self, payload: Mapping[str, Any]
    ) -> ManagementRoleSummary:
        data = await self.request(
            "POST", f"{self._management_roles_root()}/", json_body=payload
        )
        return ManagementRoleSummary.model_validate(data)

    async def get_management_role(self, role_key: str) -> ManagementRoleSummary:
        data = await self.request("GET", f"{self._management_role_root(role_key)}/")
        return ManagementRoleSummary.model_validate(data)

    async def update_management_role(
        self, role_key: str, payload: Mapping[str, Any]
    ) -> ManagementRoleSummary:
        data = await self.request(
            "PUT", f"{self._management_role_root(role_key)}/", json_body=payload
        )
        return ManagementRoleSummary.model_validate(data)

    async def delete_management_role(self, role_key: str) -> None:
        await self.request(
            "DELETE", f"{self._management_role_root(role_key)}/", parse_json=False
        )

    async def list_management_role_permissions(
        self, role_key: str
    ) -> list[RolePermission]:
        payload = (
            await self.request("GET", f"{self._role_permissions_root(role_key)}/") or []
        )
        return [RolePermission.model_validate(item) for item in payload]

    async def upsert_management_role_permission(
        self,
        role_key: str,
        payload: Mapping[str, Any],
    ) -> RolePermission:
        data = await self.request(
            "POST", f"{self._role_permissions_root(role_key)}/", json_body=payload
        )
        return RolePermission.model_validate(data)

    async def delete_management_role_permission(
        self, role_key: str, content_type: str
    ) -> None:
        await self.request(
            "DELETE",
            f"{self._role_permissions_root(role_key)}/",
            params={"content_type": content_type},
            parse_json=False,
        )

    async def replace_management_role_permissions(
        self,
        role_key: str,
        permissions: list[Mapping[str, Any]],
    ) -> list[RolePermission]:
        data = (
            await self.request(
                "POST",
                f"{self._role_permissions_batch(role_key)}/",
                json_body=permissions,
            )
            or []
        )
        return [RolePermission.model_validate(item) for item in data]

    async def list_management_permission_objects(
        self, role_key: str, *, content_type: str
    ) -> list[RolePermissionObject]:
        payload = await self.request(
            "GET",
            f"{self._role_permission_objects_root(role_key)}/",
            params={"content_type": content_type},
        )
        payload = payload or []
        return [RolePermissionObject.model_validate(item) for item in payload]

    async def add_management_permission_object(
        self,
        role_key: str,
        payload: Mapping[str, Any],
    ) -> RolePermissionObject:
        data = await self.request(
            "POST",
            f"{self._role_permission_objects_root(role_key)}/",
            json_body=payload,
        )
        return RolePermissionObject.model_validate(data)

    async def delete_management_permission_object(
        self,
        role_key: str,
        payload: Mapping[str, Any],
    ) -> None:
        await self.request(
            "DELETE",
            f"{self._role_permission_objects_root(role_key)}/",
            json_body=payload,
            parse_json=False,
        )

    async def list_flux_roles(
        self, *, params: Mapping[str, Any] | None = None
    ) -> FluxRoleList:
        data = await self.request("GET", f"{self._flux_roles_root()}/", params=params)
        return FluxRoleList.model_validate(data)

    async def create_flux_role(self, payload: Mapping[str, Any]) -> FluxRoleSummary:
        data = await self.request(
            "POST", f"{self._flux_roles_root()}/", json_body=payload
        )
        return FluxRoleSummary.model_validate(data)

    async def get_flux_role(self, role_key: str) -> FluxRoleSummary:
        data = await self.request("GET", f"{self._flux_role_root(role_key)}/")
        return FluxRoleSummary.model_validate(data)

    async def update_flux_role(
        self, role_key: str, payload: Mapping[str, Any]
    ) -> FluxRoleSummary:
        data = await self.request(
            "PUT", f"{self._flux_role_root(role_key)}/", json_body=payload
        )
        return FluxRoleSummary.model_validate(data)

    async def delete_flux_role(self, role_key: str) -> None:
        await self.request(
            "DELETE", f"{self._flux_role_root(role_key)}/", parse_json=False
        )

    async def list_flux_role_permissions(self, role_key: str) -> list[RolePermission]:
        payload = (
            await self.request("GET", f"{self._flux_role_permissions_root(role_key)}/")
            or []
        )
        return [RolePermission.model_validate(item) for item in payload]

    async def upsert_flux_role_permission(
        self, role_key: str, payload: Mapping[str, Any]
    ) -> RolePermission:
        data = await self.request(
            "POST", f"{self._flux_role_permissions_root(role_key)}/", json_body=payload
        )
        return RolePermission.model_validate(data)

    async def delete_flux_role_permission(
        self, role_key: str, content_type: str
    ) -> None:
        await self.request(
            "DELETE",
            f"{self._flux_role_permissions_root(role_key)}/",
            params={"content_type": content_type},
            parse_json=False,
        )

    async def replace_flux_role_permissions(
        self,
        role_key: str,
        permissions: list[Mapping[str, Any]],
    ) -> list[RolePermission]:
        payload = (
            await self.request(
                "POST",
                f"{self._flux_role_permissions_batch(role_key)}/",
                json_body=permissions,
            )
            or []
        )
        return [RolePermission.model_validate(item) for item in payload]

    async def list_flux_permission_objects(
        self, role_key: str, *, content_type: str
    ) -> list[RolePermissionObject]:
        payload = await self.request(
            "GET",
            f"{self._flux_role_permission_objects_root(role_key)}/",
            params={"content_type": content_type},
        )
        payload = payload or []
        return [RolePermissionObject.model_validate(item) for item in payload]

    async def add_flux_permission_object(
        self,
        role_key: str,
        payload: Mapping[str, Any],
    ) -> RolePermissionObject:
        data = await self.request(
            "POST",
            f"{self._flux_role_permission_objects_root(role_key)}/",
            json_body=payload,
        )
        return RolePermissionObject.model_validate(data)

    async def delete_flux_permission_object(
        self,
        role_key: str,
        payload: Mapping[str, Any],
    ) -> None:
        await self.request(
            "DELETE",
            f"{self._flux_role_permission_objects_root(role_key)}/",
            json_body=payload,
            parse_json=False,
        )

    # ------------------------------------------------------------------ #
    # Folder operations
    # ------------------------------------------------------------------ #

    async def list_folders(
        self, *, params: Mapping[str, Any] | None = None
    ) -> FolderList:
        data = await self.request("GET", f"{self._folders_tree_root()}/", params=params)
        return FolderList.model_validate(data)

    async def get_folder(self, folder_key: str) -> FolderSummary:
        data = await self.request(
            "GET", f"{self._folders_tree_item()}/", params={"key": folder_key}
        )
        return FolderSummary.model_validate(data)

    async def get_folder_by_path(self, path: str) -> FolderSummary:
        data = await self.request(
            "GET",
            f"{self._folders_tree_item()}/",
            params={"path": path},
        )
        return FolderSummary.model_validate(data)

    async def list_folder_tree(
        self,
        *,
        key: str | None = None,
        mode: str | None = None,
    ) -> FolderList:
        params: dict[str, Any] = {}
        if key:
            params["key"] = key
        if mode:
            params["mode"] = mode
        data = await self.request(
            "GET", f"{self._folders_tree_root()}/", params=params or None
        )
        return FolderList.model_validate(data)

    async def create_folder(self, payload: Mapping[str, Any]) -> FolderSummary:
        data = await self.request(
            "POST", f"{self._folders_tree_root()}/", json_body=payload
        )
        return FolderSummary.model_validate(data)

    async def update_folder(
        self, folder_key: str, payload: Mapping[str, Any]
    ) -> FolderSummary:
        data = await self.request(
            "PUT",
            f"{self._folders_tree_item()}/",
            params={"key": folder_key},
            json_body=payload,
        )
        return FolderSummary.model_validate(data)

    async def delete_folder(self, folder_key: str) -> None:
        await self.request(
            "DELETE",
            f"{self._folders_tree_item()}/",
            params={"key": folder_key},
            parse_json=False,
        )

    # ------------------------------------------------------------------ #
    # Component operations
    # ------------------------------------------------------------------ #

    async def list_components(
        self, *, params: Mapping[str, Any] | None = None
    ) -> ComponentList:
        data = await self.request("GET", f"{self._components_root()}/", params=params)
        return ComponentList.model_validate(data)

    async def get_component(self, component_key: str) -> ComponentSummary:
        data = await self.request("GET", f"{self._component_root(component_key)}/")
        return ComponentSummary.model_validate(data)

    async def create_component(self, payload: Mapping[str, Any]) -> ComponentSummary:
        data = await self.request(
            "POST", f"{self._components_root()}/", json_body=payload
        )
        return ComponentSummary.model_validate(data)

    async def update_component(
        self, component_key: str, payload: Mapping[str, Any]
    ) -> ComponentSummary:
        data = await self.request(
            "PUT",
            f"{self._component_root(component_key)}/",
            json_body=payload,
        )
        return ComponentSummary.model_validate(data)

    async def delete_component(self, component_key: str) -> None:
        await self.request(
            "DELETE", f"{self._component_root(component_key)}/", parse_json=False
        )

    async def list_component_versions(
        self,
        component_key: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> SchemaVersionList:
        data = await self.request(
            "GET", f"{self._component_versions_base(component_key)}/", params=params
        )
        return SchemaVersionList.model_validate(data)

    async def create_component_version(
        self,
        component_key: str,
        payload: Mapping[str, Any],
        *,
        copy_from: str | None = None,
    ) -> SchemaVersionSummary:
        params = {"copy_from": copy_from} if copy_from else None
        data = await self.request(
            "POST",
            f"{self._component_versions_base(component_key)}/",
            params=params,
            json_body=payload,
        )
        return SchemaVersionSummary.model_validate(data)

    async def get_component_version(
        self,
        component_key: str,
        version_key: str,
        *,
        include_schema: bool | None = None,
    ) -> SchemaVersionSummary:
        params = (
            {"include_schema": str(include_schema).lower()}
            if include_schema is not None
            else None
        )
        data = await self.request(
            "GET",
            f"{self._component_versions_base(component_key)}/{version_key}/",
            params=params,
        )
        return SchemaVersionSummary.model_validate(data)

    async def publish_component_version(
        self,
        component_key: str,
        version_key: str,
    ) -> SchemaVersionSummary:
        data = await self.request(
            "POST",
            f"{self._component_versions_base(component_key)}/{version_key}/publish/",
        )
        return SchemaVersionSummary.model_validate(data)

    async def update_component_version(
        self,
        component_key: str,
        version_key: str,
        payload: Mapping[str, Any],
    ) -> SchemaVersionSummary:
        data = await self.request(
            "PUT",
            f"{self._component_versions_base(component_key)}/{version_key}/",
            json_body=payload,
        )
        return SchemaVersionSummary.model_validate(data)

    async def delete_component_version(
        self, component_key: str, version_key: str
    ) -> None:
        await self.request(
            "DELETE",
            f"{self._component_versions_base(component_key)}/{version_key}/",
            parse_json=False,
        )

    async def list_component_fields(
        self,
        component_key: str,
        version_key: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> FieldList:
        data = await self.request(
            "GET",
            f"{self._component_schema_tree(component_key, version_key)}/",
            params=params,
        )
        return FieldList.model_validate(data)

    async def create_component_field(
        self,
        component_key: str,
        version_key: str,
        payload: Mapping[str, Any],
    ) -> FieldSummary:
        data = await self.request(
            "POST",
            f"{self._component_schema_tree(component_key, version_key)}/",
            json_body=payload,
        )
        return FieldSummary.model_validate(data)

    async def get_component_field(
        self,
        component_key: str,
        version_key: str,
        field_path: str,
    ) -> FieldSummary:
        data = await self.request(
            "GET",
            f"{self._component_schema_tree(component_key, version_key)}/field/",
            params={"path": field_path},
        )
        return FieldSummary.model_validate(data)

    async def update_component_field(
        self,
        component_key: str,
        version_key: str,
        field_path: str,
        payload: Mapping[str, Any],
    ) -> FieldSummary:
        data = await self.request(
            "PUT",
            f"{self._component_schema_tree(component_key, version_key)}/field/",
            params={"path": field_path},
            json_body=payload,
        )
        return FieldSummary.model_validate(data)

    async def delete_component_field(
        self, component_key: str, version_key: str, field_path: str
    ) -> None:
        await self.request(
            "DELETE",
            f"{self._component_schema_tree(component_key, version_key)}/field/",
            params={"path": field_path},
            parse_json=False,
        )

    async def list_folder_versions(
        self,
        folder_key: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> SchemaVersionList:
        data = await self.request(
            "GET", f"{self._folder_versions_base(folder_key)}/", params=params
        )
        return SchemaVersionList.model_validate(data)

    async def create_folder_version(
        self,
        folder_key: str,
        payload: Mapping[str, Any],
        *,
        copy_from: str | None = None,
    ) -> SchemaVersionSummary:
        params = {"copy_from": copy_from} if copy_from else None
        data = await self.request(
            "POST",
            f"{self._folder_versions_base(folder_key)}/",
            params=params,
            json_body=payload,
        )
        return SchemaVersionSummary.model_validate(data)

    async def get_folder_version(
        self,
        folder_key: str,
        version_key: str,
        *,
        include_schema: bool | None = None,
    ) -> SchemaVersionSummary:
        params = (
            {"include_schema": str(include_schema).lower()}
            if include_schema is not None
            else None
        )
        data = await self.request(
            "GET",
            f"{self._folder_versions_base(folder_key)}/{version_key}/",
            params=params,
        )
        return SchemaVersionSummary.model_validate(data)

    async def update_folder_version(
        self,
        folder_key: str,
        version_key: str,
        payload: Mapping[str, Any],
    ) -> SchemaVersionSummary:
        data = await self.request(
            "PUT",
            f"{self._folder_versions_base(folder_key)}/{version_key}/",
            json_body=payload,
        )
        return SchemaVersionSummary.model_validate(data)

    async def delete_folder_version(self, folder_key: str, version_key: str) -> None:
        await self.request(
            "DELETE",
            f"{self._folder_versions_base(folder_key)}/{version_key}/",
            parse_json=False,
        )

    async def publish_folder_version(
        self,
        folder_key: str,
        version_key: str,
    ) -> SchemaVersionSummary:
        data = await self.request(
            "POST",
            f"{self._folder_versions_base(folder_key)}/{version_key}/publish/",
        )
        return SchemaVersionSummary.model_validate(data)

    async def list_folder_fields(
        self,
        folder_key: str,
        version_key: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> FieldList:
        data = await self.request(
            "GET",
            f"{self._folder_schema_tree(folder_key, version_key)}/",
            params=params,
        )
        return FieldList.model_validate(data)

    async def create_folder_field(
        self,
        folder_key: str,
        version_key: str,
        payload: Mapping[str, Any],
    ) -> FieldSummary:
        data = await self.request(
            "POST",
            f"{self._folder_schema_tree(folder_key, version_key)}/",
            json_body=payload,
        )
        return FieldSummary.model_validate(data)

    async def get_folder_field(
        self,
        folder_key: str,
        version_key: str,
        field_path: str,
    ) -> FieldSummary:
        data = await self.request(
            "GET",
            f"{self._folder_schema_tree(folder_key, version_key)}/field/",
            params={"path": field_path},
        )
        return FieldSummary.model_validate(data)

    async def update_folder_field(
        self,
        folder_key: str,
        version_key: str,
        field_path: str,
        payload: Mapping[str, Any],
    ) -> FieldSummary:
        data = await self.request(
            "PUT",
            f"{self._folder_schema_tree(folder_key, version_key)}/field/",
            params={"path": field_path},
            json_body=payload,
        )
        return FieldSummary.model_validate(data)

    async def delete_folder_field(
        self, folder_key: str, version_key: str, field_path: str
    ) -> None:
        await self.request(
            "DELETE",
            f"{self._folder_schema_tree(folder_key, version_key)}/field/",
            params={"path": field_path},
            parse_json=False,
        )

    async def list_projects(
        self, org_key: str, *, params: Mapping[str, Any] | None = None
    ) -> ProjectList:
        data = await self.request(
            "GET", f"{self._projects_base(org_key)}/", params=params
        )
        return ProjectList.model_validate(data)

    async def get_project(self, org_key: str, project_key: str) -> ProjectSummary:
        data = await self.request("GET", f"{self._project_root(org_key, project_key)}/")
        return ProjectSummary.model_validate(data)

    async def create_project(
        self, org_key: str, payload: Mapping[str, Any]
    ) -> ProjectSummary:
        data = await self.request(
            "POST", f"{self._projects_base(org_key)}/", json_body=payload
        )
        return ProjectSummary.model_validate(data)

    async def update_project(
        self, org_key: str, project_key: str, payload: Mapping[str, Any]
    ) -> ProjectSummary:
        data = await self.request(
            "PUT", f"{self._project_root(org_key, project_key)}/", json_body=payload
        )
        return ProjectSummary.model_validate(data)

    async def delete_project(self, org_key: str, project_key: str) -> None:
        await self.request(
            "DELETE", f"{self._project_root(org_key, project_key)}/", parse_json=False
        )

    async def list_environments(
        self, org_key: str, project_key: str
    ) -> EnvironmentList:
        payload = await self.request(
            "GET", f"{self._environments_base(org_key, project_key)}/"
        )
        return ManagementClient._coerce_environment_list(payload)

    async def get_environment(
        self, org_key: str, project_key: str, env_key: str
    ) -> EnvironmentSummary:
        data = await self.request(
            "GET", f"{self._environment_root(org_key, project_key, env_key)}/"
        )
        return EnvironmentSummary.model_validate(data)

    async def create_environment(
        self,
        org_key: str,
        project_key: str,
        payload: Mapping[str, Any],
    ) -> EnvironmentSummary:
        data = await self.request(
            "POST",
            f"{self._environments_base(org_key, project_key)}/",
            json_body=payload,
        )
        return EnvironmentSummary.model_validate(data)

    async def update_environment(
        self,
        org_key: str,
        project_key: str,
        env_key: str,
        payload: Mapping[str, Any],
    ) -> EnvironmentSummary:
        data = await self.request(
            "PUT",
            f"{self._environment_root(org_key, project_key, env_key)}/",
            json_body=payload,
        )
        return EnvironmentSummary.model_validate(data)

    async def delete_environment(
        self, org_key: str, project_key: str, env_key: str
    ) -> None:
        await self.request(
            "DELETE",
            f"{self._environment_root(org_key, project_key, env_key)}/",
            parse_json=False,
        )

    async def toggle_environment(
        self, org_key: str, project_key: str, env_key: str, *, is_enabled: bool
    ) -> None:
        await self.request(
            "POST",
            f"{self._environment_root(org_key, project_key, env_key)}/toggle/",
            json_body={"is_enabled": is_enabled},
            parse_json=False,
        )

    async def update_environment_protection(
        self,
        org_key: str,
        project_key: str,
        env_key: str,
        *,
        protection_level: str,
        protection_reason: str | None = None,
    ) -> EnvironmentSummary:
        payload: dict[str, Any] = {"protection_level": protection_level}
        if protection_reason is not None:
            payload["protection_reason"] = protection_reason
        data = await self.request(
            "PATCH",
            f"{self._environment_root(org_key, project_key, env_key)}/protection/",
            json_body=payload,
        )
        return EnvironmentSummary.model_validate(data)

    async def clear_environment_protection(
        self, org_key: str, project_key: str, env_key: str
    ) -> EnvironmentSummary:
        return await self.update_environment_protection(
            org_key,
            project_key,
            env_key,
            protection_level="none",
        )

    # ------------------------------------------------------------------ #
    # Locale operations
    # ------------------------------------------------------------------ #

    async def list_locales(self) -> LocaleList:
        payload = await self.request("GET", f"{self._locales_root()}/") or []
        return [LocaleSummary.model_validate(item) for item in payload]

    async def create_locale(self, payload: Mapping[str, Any]) -> LocaleSummary:
        data = await self.request("POST", f"{self._locales_root()}/", json_body=payload)
        return LocaleSummary.model_validate(data)

    async def get_locale(self, code: str) -> LocaleSummary:
        data = await self.request("GET", f"{self._locale_root(code)}/")
        return LocaleSummary.model_validate(data)

    async def update_locale(
        self, code: str, payload: Mapping[str, Any]
    ) -> LocaleSummary:
        data = await self.request(
            "PUT", f"{self._locale_root(code)}/", json_body=payload
        )
        return LocaleSummary.model_validate(data)

    async def delete_locale(self, code: str) -> None:
        await self.request("DELETE", f"{self._locale_root(code)}/", parse_json=False)

    # ------------------------------------------------------------------ #
    # Resource operations
    # ------------------------------------------------------------------ #

    async def list_resources(
        self,
        folder_key: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> ResourceList:
        data = await self.request(
            "GET", f"{self._resource_base(folder_key)}/", params=params
        )
        return ResourceList.model_validate(data)

    async def get_resource(self, folder_key: str, resource_key: str) -> ResourceSummary:
        data = await self.request(
            "GET", f"{self._resource_base(folder_key)}/{resource_key}/"
        )
        return ResourceSummary.model_validate(data)

    async def create_resource(
        self,
        folder_key: str,
        payload: Mapping[str, Any],
        *,
        component: str | None = None,
    ) -> ResourceSummary:
        params = {"component": component} if component else None
        data = await self.request(
            "POST",
            f"{self._resource_base(folder_key)}/",
            params=params,
            json_body=payload,
        )
        return ResourceSummary.model_validate(data)

    async def update_resource(
        self,
        folder_key: str,
        resource_key: str,
        payload: Mapping[str, Any],
    ) -> ResourceSummary:
        await self.request(
            "PUT",
            f"{self._resource_base(folder_key)}/{resource_key}/",
            json_body=payload,
            parse_json=False,
        )
        return await self.get_resource(folder_key, resource_key)

    async def delete_resource(self, folder_key: str, resource_key: str) -> None:
        await self.request(
            "DELETE",
            f"{self._resource_base(folder_key)}/{resource_key}/",
            parse_json=False,
        )

    async def get_resource_data(
        self, folder_key: str, resource_key: str
    ) -> Mapping[str, Any]:
        return await self.request(
            "GET", f"{self._resource_base(folder_key)}/{resource_key}/data/"
        )

    async def list_revisions(
        self,
        folder_key: str,
        resource_key: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> RevisionList:
        data = await self.request(
            "GET", f"{self._revision_base(folder_key, resource_key)}/", params=params
        )
        return RevisionList.model_validate(data)

    async def create_revision(
        self,
        folder_key: str,
        resource_key: str,
        payload: Mapping[str, Any],
    ) -> RevisionSummary:
        data = await self.request(
            "POST",
            f"{self._revision_base(folder_key, resource_key)}/",
            json_body=payload,
        )
        return RevisionSummary.model_validate(data)

    async def get_revision(
        self,
        folder_key: str,
        resource_key: str,
        revision_key: str,
    ) -> RevisionSummary:
        data = await self.request(
            "GET",
            f"{self._revision_base(folder_key, resource_key)}/{revision_key}/",
        )
        return RevisionSummary.model_validate(data)

    async def update_revision(
        self,
        folder_key: str,
        resource_key: str,
        revision_key: str,
        payload: Mapping[str, Any],
    ) -> RevisionSummary:
        data = await self.request(
            "PUT",
            f"{self._revision_base(folder_key, resource_key)}/{revision_key}/",
            json_body=payload,
        )
        return RevisionSummary.model_validate(data)

    async def delete_revision(
        self, folder_key: str, resource_key: str, revision_key: str
    ) -> None:
        await self.request(
            "DELETE",
            f"{self._revision_base(folder_key, resource_key)}/{revision_key}/",
            parse_json=False,
        )

    async def publish_revision(
        self,
        folder_key: str,
        resource_key: str,
        revision_key: str,
        payload: Mapping[str, Any] | None = None,
    ) -> RevisionSummary:
        data = await self.request(
            "POST",
            f"{self._revision_base(folder_key, resource_key)}/{revision_key}/publish/",
            json_body=payload,
        )
        return RevisionSummary.model_validate(data)

    async def validate_revision(
        self,
        folder_key: str,
        resource_key: str,
        revision_key: str,
    ) -> Mapping[str, Any]:
        """Validate a revision before publishing. Returns validation errors if any."""
        path = (
            f"{self._revision_base(folder_key, resource_key)}/{revision_key}/validate/"
        )
        return await self.request("POST", path)

    async def get_revision_data(
        self,
        folder_key: str,
        resource_key: str,
        revision_key: str,
    ) -> Mapping[str, Any]:
        return await self.request(
            "GET",
            f"{self._revision_base(folder_key, resource_key)}/{revision_key}/data/",
        )

    async def aclose(self) -> None:
        await self._transport.aclose()
