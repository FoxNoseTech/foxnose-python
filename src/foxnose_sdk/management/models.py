from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic pagination envelope returned by Management API list endpoints."""

    count: int
    next: str | None
    previous: str | None
    results: list[T]


class ResourceSummary(BaseModel):
    """Metadata describing a Management API resource entry."""

    key: str
    folder: str
    content_type: str
    created_at: datetime
    vectors_size: int
    name: str | None = None
    component: str | None = None
    resource_owner: str | None = None
    current_revision: str | None = None


class RevisionSummary(BaseModel):
    """Metadata describing a revision associated with a resource."""

    key: str
    resource: str
    schema_version: str
    number: int
    size: int
    created_at: datetime
    status: str
    is_valid: bool | None
    published_at: datetime | None
    unpublished_at: datetime | None


ResourceList = PaginatedResponse[ResourceSummary]
RevisionList = PaginatedResponse[RevisionSummary]


class FolderSummary(BaseModel):
    """Metadata returned for folder definitions."""

    key: str
    name: str
    alias: str
    folder_type: str
    content_type: str
    strict_reference: bool
    created_at: datetime
    parent: str | None = None
    mode: str | None = None
    path: str | None = None


FolderList = PaginatedResponse[FolderSummary]


class ComponentSummary(BaseModel):
    """Metadata describing a reusable component schema."""

    key: str
    name: str
    description: str | None = None
    environment: str
    content_type: str
    created_at: datetime
    current_version: str | None = None


ComponentList = PaginatedResponse[ComponentSummary]


class SchemaVersionSummary(BaseModel):
    """Represents a schema/model version for folders or components."""

    key: str
    name: str
    description: str | None
    version_number: int | None
    created_at: datetime
    published_at: datetime | None
    archived_at: datetime | None
    json_schema: dict[str, Any] | None = None


class FieldSummary(BaseModel):
    """Schema field metadata for a version."""

    model_config = ConfigDict(extra="allow")

    key: str
    name: str
    description: str | None
    path: str
    parent: str | None
    type: str
    meta: dict[str, Any]
    json_schema: dict[str, Any] | None = None
    required: bool
    nullable: bool
    multiple: bool | None
    localizable: bool | None
    searchable: bool | None
    private: bool
    vectorizable: bool | None = None


SchemaVersionList = PaginatedResponse[SchemaVersionSummary]
FieldList = PaginatedResponse[FieldSummary]


class RegionInfo(BaseModel):
    """Represents a provisioned region for projects."""

    location: str
    name: str
    code: str


class ProjectSummary(BaseModel):
    """Represents a project within an organization."""

    key: str
    name: str
    organization: str

    region: RegionInfo | str
    environments: list[dict[str, Any]]
    gdpr: bool | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(extra="allow")

    @field_validator("region", mode="before")
    @classmethod
    def _normalize_region(
        cls, value: str | dict[str, Any] | RegionInfo | None
    ) -> str | RegionInfo | None:
        if isinstance(value, dict):
            return RegionInfo.model_validate(value)
        return value


ProjectList = PaginatedResponse[ProjectSummary]


class EnvironmentSummary(BaseModel):
    """Represents an environment under a project."""

    key: str
    name: str
    project: str
    host: str
    is_enabled: bool
    created_at: datetime
    protection_level: str | None = None
    protection_level_display: str | None = None
    protected_by_user: UserReference | None = None
    protected_at: datetime | None = None
    protection_reason: str | None = None


EnvironmentList = list[EnvironmentSummary]


class LocaleSummary(BaseModel):
    """Represents an environment locale."""

    name: str
    code: str
    environment: str
    is_default: bool
    created_at: datetime


LocaleList = list[LocaleSummary]


class ManagementAPIKeySummary(BaseModel):
    """Represents a Management API key under an environment."""

    key: str
    description: str | None = None
    public_key: str
    secret_key: str
    role: str | None = None
    environment: str
    created_at: datetime


ManagementAPIKeyList = PaginatedResponse[ManagementAPIKeySummary]


class FluxAPIKeySummary(BaseModel):
    """Represents a Flux API key under an environment."""

    key: str
    description: str | None = None
    public_key: str
    secret_key: str
    role: str | None = None
    environment: str
    created_at: datetime


FluxAPIKeyList = PaginatedResponse[FluxAPIKeySummary]


class ManagementRoleSummary(BaseModel):
    """Represents a management API role."""

    key: str
    name: str
    description: str | None = None
    full_access: bool
    environment: str
    created_at: datetime


ManagementRoleList = PaginatedResponse[ManagementRoleSummary]


class RolePermission(BaseModel):
    """Permission entry attached to a role."""

    content_type: str
    actions: list[str]
    all_objects: bool
    objects: list[str] | None = None


class RolePermissionObject(BaseModel):
    """Object-level scope entry for folder-items permissions."""

    content_type: str
    object_key: str


class UserReference(BaseModel):
    """Lightweight reference to a user."""

    key: str
    email: str
    first_name: str
    last_name: str
    full_name: str


class FluxRoleSummary(BaseModel):
    """Represents a Flux API role."""

    key: str
    name: str
    description: str | None = None
    environment: str
    created_at: datetime


FluxRoleList = PaginatedResponse[FluxRoleSummary]


class APIInfo(BaseModel):
    """Represents a public API definition for delivering content."""

    key: str
    name: str
    prefix: str
    description: str | None = None
    environment: str
    version: str | None = None
    is_auth_required: bool
    created_at: datetime
    path: str | None = None


APIList = PaginatedResponse[APIInfo]


class APIFolderSummary(BaseModel):
    """Association between an API and a folder."""

    folder: str
    api: str | None = None
    path: str | None = None
    allowed_methods: list[str] | None = None
    created_at: datetime | None = None


APIFolderList = PaginatedResponse[APIFolderSummary]


class OrganizationOwner(BaseModel):
    """Owner metadata embedded into organization responses."""

    key: str
    email: str
    first_name: str
    last_name: str
    full_name: str


class OrganizationSummary(BaseModel):
    """Represents an organization and its billing metadata."""

    key: str
    name: str
    owner: OrganizationOwner
    tax_num: str
    city: str
    province: str
    address: str
    country_iso: str | None
    zip_code: str
    legal_name: str
    created_at: datetime
    block_dt: datetime | None = None
    block_reason: str | None = None
    is_blocked: bool


OrganizationList = list[OrganizationSummary]


class PlanLimits(BaseModel):
    """Usage limits associated with a billing plan."""

    units_included: str | None = None
    projects: int | None = None
    environments: int | None = None
    folders: int | None = None
    resources: int | None = None
    users: int | None = None
    components: int | None = None
    allow_negative: bool | None = None
    negative_limit: int | float | None = None
    unit_cost: float | None = None
    api_keys_max_count: int | None = None
    roles_max_count: int | None = None
    locales_max_count: int | None = None
    schemas_max_count: int | None = None
    schemas_fields_max_count: int | None = None
    flux_api_max_count: int | None = None
    max_component_inheritance_depth: int | None = None


class PlanDetails(BaseModel):
    """Plan metadata returned by billing endpoints."""

    code: str
    name: str
    price: float
    from_: datetime | None = Field(default=None, alias="from")
    to: datetime | None = Field(default=None, alias="to")
    transferred: str | None = None
    limits: PlanLimits


class OrganizationPlanStatus(BaseModel):
    """Active and scheduled plan details for an organization."""

    active_plan: PlanDetails
    next_plan: PlanDetails


class UnitsUsage(BaseModel):
    """Unit balance information for an organization."""

    remained: str | int | float | None = None
    unit_cost: float | None = None
    allow_negative: bool
    negative_limit: str | None = None


class StorageUsage(BaseModel):
    """Storage usage statistics."""

    data_storage: float
    vector_storage: float


class UsageMetric(BaseModel):
    """Shared shape for usage counters."""

    max: int | None
    current: int


class UsageBreakdown(BaseModel):
    """Breakdown of quota-based resource usage."""

    projects: UsageMetric
    environments: UsageMetric
    folders: UsageMetric
    resources: UsageMetric
    users: UsageMetric
    components: UsageMetric


class CurrentUsage(BaseModel):
    """Current meter-based usage metrics."""

    api_requests: int
    embedding_tokens: dict[str, Any]


class OrganizationUsage(BaseModel):
    """Overall usage payload returned by the monitoring endpoint."""

    units: UnitsUsage
    storage: StorageUsage
    usage: UsageBreakdown
    current_usage: CurrentUsage


__all__ = [
    "PaginatedResponse",
    "ResourceSummary",
    "RevisionSummary",
    "ResourceList",
    "RevisionList",
    "FolderSummary",
    "FolderList",
    "ComponentSummary",
    "ComponentList",
    "SchemaVersionSummary",
    "SchemaVersionList",
    "FieldSummary",
    "FieldList",
    "ProjectSummary",
    "ProjectList",
    "EnvironmentSummary",
    "EnvironmentList",
    "LocaleSummary",
    "LocaleList",
    "ManagementAPIKeySummary",
    "ManagementAPIKeyList",
    "FluxAPIKeySummary",
    "FluxAPIKeyList",
    "ManagementRoleSummary",
    "ManagementRoleList",
    "RolePermission",
    "RolePermissionObject",
    "UserReference",
    "FluxRoleSummary",
    "FluxRoleList",
    "OrganizationSummary",
    "OrganizationList",
    "OrganizationOwner",
    "RegionInfo",
    "PlanLimits",
    "PlanDetails",
    "OrganizationPlanStatus",
    "OrganizationUsage",
]
