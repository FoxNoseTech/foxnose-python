from __future__ import annotations

import json
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


class _FilesModel(BaseModel):
    """Base of the Files response models: a field the server adds is kept."""

    model_config = ConfigDict(extra="allow")


class UploadFileProgress(_FilesModel):
    """Where a file stands in the processing steps."""

    step: int
    of: int
    step_name: str | None = None


class FileSummary(_FilesModel):
    """The file attached to a record or a revision."""

    uuid: str | None = None
    mime: str | None = None
    width: int | None = None
    height: int | None = None
    cdn_url_base: str | None = None
    filename: str | None = None
    size: int | None = None
    page_count: int | None = None


class FileRecordOwner(_FilesModel):
    """The parent record of a file record. ``title`` is ``None`` when the caller may
    not read the owner, and ``deleted`` is true for a parent that was deleted."""

    key: str
    title: str | None = None
    deleted: bool = False


class FileInfo(_FilesModel):
    """A file record's newest file, published or not."""

    filename: str | None = None
    mime: str | None = None
    size: int | None = None
    page_count: int | None = None


class ResourceSummary(BaseModel):
    """Metadata describing a Management API resource entry.

    ``owner``, ``status``, ``progress``, ``analysis_state``, ``thumbnail_url``,
    ``file_info``, ``verdict`` and ``verdict_reasons`` are set on a record of a files
    collection only. ``thumbnail_url`` is short-lived and left out of ``repr()``.
    ``guardrails`` is the record's trust summary where the API computes one.
    """

    key: str
    folder: str
    content_type: str
    created_at: datetime
    vectors_size: int
    name: str | None = None
    name_is_auto: bool = False
    resource_owner: str | None = None
    current_revision: str | None = None
    external_id: str | None = None
    file: FileSummary | None = None
    owner: FileRecordOwner | None = None
    status: str | None = None
    progress: UploadFileProgress | None = None
    analysis_state: str | None = None
    thumbnail_url: str | None = Field(default=None, repr=False)
    file_info: FileInfo | None = None
    verdict: str | None = None
    verdict_reasons: list[Any] = []
    guardrails: dict[str, Any] | None = None


class RevisionSummary(BaseModel):
    """Metadata describing a revision associated with a resource.

    ``schema_version`` is ``None`` when the schema version is gone.
    ``schema_version_number`` is ``None`` then too, and for a draft version.
    """

    key: str
    resource: str
    schema_version: str | None
    schema_version_number: int | None = None
    file: FileSummary | None = None
    guardrails: dict[str, Any] | None = None
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
    content_type: str
    strict_reference: bool
    created_at: datetime
    parent: str | None = None
    mode: str | None = None
    path: str | None = None


FolderList = PaginatedResponse[FolderSummary]

# Collection-named aliases — same model, preferred name in new code.
CollectionSummary = FolderSummary
CollectionList = FolderList


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


class NestedFieldMeta(BaseModel):
    """Helper for building the ``meta`` block of a Collection ``nested`` field.

    A ``nested`` field on a Collection schema embeds a Component schema at
    a specific published version. The pin is required: even in auto-update
    mode, ``component_version`` stores the most recently resolved version
    and acts as a fallback if a future Component publish fails compatibility.

    Use ``.to_meta()`` (or just unpack via ``model_dump()``) when building
    the ``meta`` payload for :meth:`ManagementClient.create_collection_field`
    or :meth:`ManagementClient.update_collection_field`.

    Example
    -------
    >>> meta = NestedFieldMeta(
    ...     component="cmp-seo-metadata",
    ...     component_version="ver-abc12345",
    ...     auto_update=True,
    ... )
    >>> client.create_collection_field(
    ...     "articles",
    ...     "v1-draft",
    ...     {"key": "seo", "name": "SEO", "type": "nested",
    ...      "required": True, "meta": meta.to_meta()},
    ... )
    """

    model_config = ConfigDict(extra="allow")

    component: str = Field(min_length=6, max_length=36)
    component_version: str = Field(min_length=6, max_length=36)
    auto_update: bool = False

    def to_meta(self) -> dict[str, Any]:
        """Return the dict shape expected by the schema-tree endpoint."""
        return self.model_dump()


class SyncComponentSkippedItem(BaseModel):
    """One entry in the ``skipped`` list of a sync_component response.

    Attributes
    ----------
    path:
        The nested field path that was skipped.
    reason:
        Why the field was skipped. One of: ``"not_requested"``,
        ``"auto_update_mode"``, ``"already_at_target"``,
        ``"component_not_found"``, ``"component_unpublished"``.
    """

    model_config = ConfigDict(extra="allow")

    path: str
    reason: str


class SyncComponentResponse(BaseModel):
    """Response payload from ``POST /collections/{key}/sync_component/``.

    Attributes
    ----------
    synced_paths:
        Field paths whose ``meta.component_version`` was advanced. Empty
        when every requested path was skipped (no new schema version was
        created in that case and ``schema_version`` is ``None``).
    skipped:
        Per-path skip records explaining why each was left alone.
    schema_version:
        UID of the newly published Collection schema version that the
        sync materialized. ``None`` when no advance was needed.
    """

    model_config = ConfigDict(extra="allow")

    synced_paths: list[str] = Field(default_factory=list)
    skipped: list[SyncComponentSkippedItem] = Field(default_factory=list)
    schema_version: str | None = None


class ComponentSyncConflictDetail(BaseModel):
    """One structured conflict entry inside a 409 ``component_sync_conflict``
    error detail (e.g. ``{"field_path": "...", "blocking_reason": "..."}``).

    ``blocking_reason`` is one of: ``"required_field_added_no_default"``,
    ``"type_narrowed"``, ``"field_removed"``.
    """

    model_config = ConfigDict(extra="allow")

    field_path: str
    blocking_reason: str


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
    #: First 12 characters of the key's bearer token (e.g. ``fxk_A7fQ2mXe``), or
    #: None when none is issued. Enough to recognise a token in a config file or
    #: a log; never enough to use one — the token itself is returned only by
    #: :meth:`ManagementClient.issue_flux_api_key_bearer_token`, once.
    #: Optional so the model still validates against a server predating the
    #: feature.
    bearer_token_prefix: str | None = None
    #: When the current bearer token was issued, or None.
    bearer_token_issued_at: datetime | None = None


FluxAPIKeyList = PaginatedResponse[FluxAPIKeySummary]


class FluxAPIKeyBearerToken(BaseModel):
    """The one-time response from issuing or re-issuing a bearer token.

    A bearer token is an opaque credential bound to a Flux API key, for hosted
    MCP connectors that accept only a token value and send it as
    ``Authorization: Bearer <token>``. It identifies the key and nothing more:
    role, grants and per-collection permissions are the key's own.
    """

    #: The credential, e.g. ``fxk_A7fQ2mXe...``. RETURNED ONLY HERE, ONLY ONCE —
    #: the service stores a hash, so a lost token is re-issued, not recovered.
    bearer_token: str
    #: First 12 characters, also present on every subsequent key read.
    bearer_token_prefix: str
    bearer_token_issued_at: datetime


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
    all_objects: bool | None = None
    objects: list[str] | None = None


class RolePermissionObject(BaseModel):
    """Object-level scope entry for an object-based permission."""

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
    #: Whether the MCP endpoint (``/{prefix}/_mcp``) is exposed. Defaults to True.
    mcp_enabled: bool = True
    #: Whether router introspection (``/{prefix}/_router``) is exposed. Defaults to True.
    router_introspection_enabled: bool = True
    #: Allowed browser origins for cross-origin reads. Empty (the default) means
    #: CORS is off; ``["*"]`` allows any origin. Server-validated and normalized.
    #: Covers public read traffic only — writes still require a key.
    cors_origins: list[str] = Field(default_factory=list)
    created_at: datetime
    path: str | None = None


APIList = PaginatedResponse[APIInfo]


class FlatRoute(BaseModel):
    """One cross-parent (flat) read address for a strict-reference collection.

    Fully-flat (``level == 0``) drops every ancestor key from the path;
    partially-flat (``level >= 1``) retains the root-most ancestor keys.
    """

    model_config = ConfigDict(extra="allow")

    level: int
    path: str
    omitted_ancestors: list[str]
    retained_ancestors: list[str]
    enabled: bool
    read_methods: list[str]
    available: bool
    unavailable_reason: str | None
    published_generation: int
    router_generation: int


class FlatRouteSummary(BaseModel):
    """The connection's currently-active flat route, singular.

    Undocumented: present on connection responses but not covered by the API
    docs. It appears to mirror whichever entry of ``flat_routes`` is enabled,
    minus ``level`` and ``retained_ancestors``. No behavior is built on it;
    it is typed here only so it is not silently dropped.
    """

    model_config = ConfigDict(extra="allow")

    path: str
    omitted_ancestors: list[str]
    enabled: bool
    read_methods: list[str]
    available: bool
    unavailable_reason: str | None
    published_generation: int
    router_generation: int


class APIFolderSummary(BaseModel):
    """Association between an API and a folder."""

    model_config = ConfigDict(extra="allow")

    folder: str
    api: str | None = None
    path: str | None = None
    allowed_methods: list[str] | None = None
    description_get_one: str | None = None
    description_get_many: str | None = None
    description_search: str | None = None
    description_schema: str | None = None
    created_at: datetime | None = None

    # Cross-parent (flat) addressing. `unscoped_levels`/`unscoped_ancestors`
    # and `expose_owner` were present on every connection inspected
    # (including ones with no flat routes, as `[]`, `[]`, `False`) — not
    # nullable, but defaulted so an omitted key degrades to an empty value
    # instead of a parse error. `flat_route`/`flat_routes` were observed
    # `null` on a connection with no key-bearing ancestor, so both are
    # optional *and* nullable.
    unscoped_levels: list[int] = Field(default_factory=list)
    unscoped_ancestors: list[str] = Field(default_factory=list)
    expose_owner: bool = False
    flat_route: FlatRouteSummary | None = None
    flat_routes: list[FlatRoute] | None = None


APIFolderList = PaginatedResponse[APIFolderSummary]

# Collection-named aliases.
APICollectionSummary = APIFolderSummary
APICollectionList = APIFolderList


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
    is_verified: bool = False
    verification_method: str | None = None


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
    """Breakdown of quota-based resource usage (organization-scoped entities)."""

    projects: UsageMetric
    resources: UsageMetric
    users: UsageMetric


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


# ---------------------------------------------------------------------------
# Batch upsert helpers
# ---------------------------------------------------------------------------


class BatchUpsertItem(BaseModel):
    """A single item to upsert in a batch operation."""

    model_config = ConfigDict(extra="forbid")

    external_id: str
    payload: dict[str, Any]


class BatchItemError(BaseModel):
    """Error information for a single failed upsert in a batch."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    index: int
    external_id: str
    exception: Exception


class BatchUpsertResult(BaseModel):
    """Aggregate result of a batch upsert operation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    succeeded: list[ResourceSummary] = []
    failed: list[BatchItemError] = []

    @property
    def total(self) -> int:
        """Total number of processed items."""
        return len(self.succeeded) + len(self.failed)

    @property
    def success_count(self) -> int:
        """Number of items that succeeded."""
        return len(self.succeeded)

    @property
    def failure_count(self) -> int:
        """Number of items that failed."""
        return len(self.failed)

    @property
    def has_failures(self) -> bool:
        """Whether any items failed."""
        return len(self.failed) > 0


# --------------------------------------------------------------------------- #
# Files
# --------------------------------------------------------------------------- #


class UploadLinkCreator(_FilesModel):
    """Who created an upload link."""

    kind: str  # "user" or "api_key"
    label: str | None = None
    user: str | None = None
    key: str | None = None


class UploadLinkFile(_FilesModel):
    """One file uploaded through a link, as the link's owner sees it."""

    state: str  # processing, ready, pending_review or rejected
    record_key: str | None = None
    public_reason: str | None = None
    file_name: str | None = None
    progress: UploadFileProgress | None = None


class UploadLinkSession(_FilesModel):
    """One visit to a link's hosted page and the files it uploaded."""

    created_at: datetime | None = None
    expires_at: datetime | None = None
    files: list[UploadLinkFile] = []


class UploadLink(_FilesModel):
    """An upload link with its sessions and the status of each file."""

    upload_id: str
    created_by: UploadLinkCreator | None = None
    owner_key: str | None = None
    title: str | None = None
    instructions: str | None = None
    max_files: int
    allowed_kinds: list[str] = []
    consumed_count: int = 0
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    state: str  # active, consumed, expired or revoked
    sessions: list[UploadLinkSession] = []


UploadLinkList = PaginatedResponse[UploadLink]


class UploadLinkCreated(_FilesModel):
    """The answer to creating an upload link.

    ``upload_url`` carries the link's token and is returned only here: no later
    read reproduces it. It is left out of ``repr()``, and a response that fails
    to parse does not quote it.
    """

    model_config = ConfigDict(extra="allow", hide_input_in_errors=True)

    upload_id: str
    title: str | None = None
    instructions: str | None = None
    upload_url: str = Field(repr=False)
    expires_at: datetime
    max_files: int
    allowed_kinds: list[str] = []


class FileAnalysis(_FilesModel):
    """The active analysis of a file."""

    generation: int
    state: str
    verdict: str | None = None
    verdict_reasons: list[Any] = []
    public_reason: str | None = None
    error_code: str | None = None
    in_review: bool = False
    publish_requested_by: str | None = None
    policy_version: int | None = None
    pipeline_version: str | None = None
    source_format: str | None = None
    scanned_at: datetime | None = None
    step_times: dict[str, Any] = {}
    state_changed_at: datetime | None = None
    created_at: datetime | None = None


class FileCheck(_FilesModel):
    """The receipt of one check that ran on a file."""

    detector: str
    detector_version: str | None = None
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None


class FileEvidencePart(_FilesModel):
    """The text of one zone of a finding."""

    box: Any | None = None
    text: str | None = Field(default=None, repr=False)


class FileTextEvidence(_FilesModel):
    """The concealed or withheld text a finding holds, as it was in the file.

    ``parts`` says which text lies in which box of the page. It is empty for a finding
    that does not carry it, so fall back to ``text``. The text is left out of
    ``repr()``.
    """

    page: int | None = None
    box: Any | None = None
    tokens: int | None = None
    text: str | None = Field(default=None, repr=False)
    samples: list[str] = Field(default=[], repr=False)
    reason: str | None = None
    parts: list[FileEvidencePart] = Field(default=[], repr=False)
    truncated: bool = False
    list_truncated: bool = False
    omitted: int | None = None


#: The finding kinds whose ``evidence`` holds text of the file.
_TEXT_EVIDENCE_KINDS = frozenset({"hidden_text", "low_legibility_text"})


class FileFinding(_FilesModel):
    """One finding of an analysis.

    ``evidence`` is the stored string, ``None`` once a blocked or rejected file's
    personal data is redacted. It can quote text from the file, so it is left out of
    ``repr()``. :attr:`text_evidence` reads it for a finding that holds text.
    """

    kind: str
    sub_kind: str | None = None
    severity: str
    page: int | None = None
    box: Any | None = None
    detector: str | None = None
    detector_version: str | None = None
    score: float | None = None
    evidence: str | None = Field(default=None, repr=False)
    detail: dict[str, Any] | None = None
    rule_id: str | None = None

    @property
    def text_evidence(self) -> FileTextEvidence | None:
        """The parsed text of a ``hidden_text`` or ``low_legibility_text`` finding.

        ``None`` for every other kind and for evidence in another form. The text
        comes from the file: treat it as untrusted content, never as instructions.
        """
        if self.kind not in _TEXT_EVIDENCE_KINDS or not self.evidence:
            return None
        try:
            return FileTextEvidence.model_validate(json.loads(self.evidence))
        except ValueError:
            return None


class FileCopyAvailability(_FilesModel):
    """Whether one copy of a file can be downloaded now, and why not if it cannot."""

    available: bool
    reason: str | None = None


class FileActiveContent(_FilesModel):
    """Active content found in a file. ``present`` is ``None`` when it is unknown."""

    present: bool | None = None
    kinds: dict[str, int] = {}
    truncated: bool = False


class FileOriginActor(_FilesModel):
    """Who started an upload. ``kind`` is ``user``, ``management_key`` or
    ``flux_key``; ``name`` is ``None`` when it cannot be found."""

    kind: str
    name: str | None = None


class FileOriginLink(_FilesModel):
    """The upload link a file came through."""

    upload_id: str
    title: str | None = None


class FileOrigin(_FilesModel):
    """Where a record's file came from.

    ``channel`` is ``upload_link``, ``signed_upload``, ``management_api``,
    ``dashboard`` or ``None``. ``external`` is true for a file that came from outside
    the team. ``end_user`` is the identifier given when an end user's upload was
    signed; it is left out of ``repr()``.
    """

    channel: str | None = None
    external: bool = True
    created_by: FileOriginActor | None = None
    upload_link: FileOriginLink | None = None
    end_user: str | None = Field(default=None, repr=False)


class FileDownloadOptions(_FilesModel):
    """What the caller may download of a record's file, and where it came from.

    ``origin`` is set on ``get_file_analysis`` for a file bound to the record, and
    ``None`` for a record uploaded without an intent.
    """

    original: FileCopyAvailability
    safe_copy: FileCopyAvailability
    active_content: FileActiveContent = FileActiveContent()
    original_access: str | None = None
    origin: FileOrigin | None = None


class FileTrust(_FilesModel):
    """How agent surfaces mark the file's content."""

    processing: str | None = None
    content_tainted: bool = False
    tainted_paths: list[str] = []


class FileRecordView(_FilesModel):
    """A record's file, its active analysis, check receipts and findings.

    ``outcome`` and ``reason`` are set on the answer to an approval only.
    """

    resource_key: str
    file_uuid: str | None = None
    page_count: int | None = None
    asset_state: str | None = None
    tombstone: bool = False
    trust: FileTrust | None = None
    analysis: FileAnalysis | None = None
    checks: list[FileCheck] = []
    findings: list[FileFinding] = []
    file: FileDownloadOptions | None = None
    outcome: str | None = None
    reason: str | None = None


class FileDownload(_FilesModel):
    """A short-lived link to one copy of a file.

    ``url`` works for whoever holds it until it expires, so it is left out of
    ``repr()``, and a response that fails to parse does not quote it.
    """

    model_config = ConfigDict(extra="allow", hide_input_in_errors=True)

    url: str = Field(repr=False)
    expires_in: int | None = None
    expires_at: datetime | None = None
    kind: str  # original, safe_copy or page
    filename: str | None = None
    content_type: str | None = None
    generation: int | None = None
    state: str | None = None
    active_content: FileActiveContent | None = None
    warnings: list[dict[str, Any]] = []


class FilePageRedaction(_FilesModel):
    """A region withheld from a page image."""

    reason: str
    box: list[float]
    label: str | None = None


class FilePageTable(_FilesModel):
    """A table found on a page."""

    box: Any


class FilePagePii(_FilesModel):
    """Where personal data stands on a page. ``unreliable`` marks data found only in
    text read with low confidence. The matched text is never included."""

    type: str
    label: str | None = None
    box: list[float]
    unreliable: bool = False


class FileFindingGroup(_FilesModel):
    """The findings of a file that share a kind, severity and source."""

    code: str
    sub_kind: str | None = None
    severity: str
    source: str | None = None
    pages: list[int] = []
    removed_from_agents: bool = False
    label: str | None = None
    rule_id: str | None = None


class FilePageFinding(_FilesModel):
    """A finding of one page. ``box`` is ``None`` when it has no place on the page."""

    code: str
    sub_kind: str | None = None
    severity: str
    source: str | None = None
    box: list[float] | None = None
    removed_from_agents: bool = False
    label: str | None = None
    rule_id: str | None = None


class FilePageDetail(_FilesModel):
    """One page of a file: its redacted image, what was withheld, its tables and the
    text an agent receives.

    ``image_url`` is short-lived and ``text`` is the file's own text: both are left
    out of ``repr()``. ``redactions``,
    ``tables``, ``text``, ``content_flags``, ``pii`` and ``pii_truncated`` are ``None``
    for a page without extracted text. With ``pii_truncated`` true, an empty ``pii``
    means locations were discarded, not that none were found.

    ``findings`` covers the whole file and ``page_findings`` this page. Neither carries
    evidence. ``removed_passages`` counts the file's findings whose text is withheld
    from agents.
    """

    model_config = ConfigDict(extra="allow", hide_input_in_errors=True)

    page: int
    of: int | None = None
    image_url: str = Field(repr=False)
    image_width: int | None = None
    image_height: int | None = None
    expires_in: int | None = None
    redactions: list[FilePageRedaction] | None = None
    tables: list[FilePageTable] | None = None
    text: str | None = Field(default=None, repr=False)
    content_flags: list[dict[str, Any]] | None = None
    pii: list[FilePagePii] | None = None
    pii_truncated: bool | None = None
    findings: list[FileFindingGroup] = []
    page_findings: list[FilePageFinding] = []
    removed_passages: int = 0
    trust: FileTrust | None = None
    verdict: str | None = None
    reasons: list[Any] = []
    generation: int | None = None
    state: str | None = None


class FileTombstone(_FilesModel):
    """A blocked or rejected file.

    ``original_filename``, ``raw_payload``, ``uploaded_by``, ``owner_key`` and each
    finding's ``evidence`` are ``None`` once ``redacted`` is true. The first three,
    the personal data, are left out of ``repr()``.
    """

    resource_key: str | None = None
    file_uuid: str | None = None
    reason: str
    public_reason: str | None = None
    error_code: str | None = None
    verdict_reasons: list[Any] = []
    generation: int | None = None
    asset_state: str | None = None
    blocked_at: datetime | None = None
    purge_completed_at: datetime | None = None
    redacts_at: datetime | None = None
    redacted: bool = False
    original_filename: str | None = Field(default=None, repr=False)
    raw_payload: Any | None = Field(default=None, repr=False)
    uploaded_by: str | None = Field(default=None, repr=False)
    owner_key: str | None = None
    findings: list[FileFinding] = []


FileTombstoneList = PaginatedResponse[FileTombstone]


class FileFindingsSummary(_FilesModel):
    """Counts of a file's findings."""

    total: int = 0
    by_kind: dict[str, int] = {}
    by_severity: dict[str, int] = {}


class FileReviewItem(_FilesModel):
    """A file held for a reviewer.

    ``owner`` is ``None`` outside a strict collection. ``thumbnail_url`` is short-lived
    and left out of ``repr()``; it is ``None`` for a caller who is not the record's
    reviewer, for a file held by moderation and over the project's view budget.
    """

    resource_key: str
    file_uuid: str | None = None
    collection: str
    file_name: str | None = None
    generation: int | None = None
    state: str | None = None
    verdict: str | None = None
    verdict_reasons: list[Any] = []
    public_reason: str | None = None
    findings: FileFindingsSummary = FileFindingsSummary()
    owner: dict[str, Any] | None = None
    held_at: datetime | None = None
    thumbnail_url: str | None = Field(default=None, repr=False)


FileReviewQueue = PaginatedResponse[FileReviewItem]


class FilesPolicyBody(_FilesModel):
    """The settings of a collection's files policy.

    As a request body it is a full replacement: a field left out takes its default.
    """

    suspicious_action: str | None = None  # deliver or quarantine
    overrides: dict[str, str] | None = None
    allowed_kinds: list[str] | None = None
    tables: str | None = None  # auto, never or always
    moderation_rules: list[dict[str, Any]] | None = None
    acknowledge_explicit_delivery: bool | None = None
    original_access: str | None = None  # allowed, when_clean or disabled


class FilesPolicy(_FilesModel):
    """A collection's live files policy.

    ``version`` is ``None`` while the collection runs on the default policy.
    """

    version: int | None = None
    enforce_from: datetime | None = None
    body: FilesPolicyBody
    config_hash: str | None = None
    created_at: datetime | None = None


class EnvironmentAccess(BaseModel):
    """The state of the environment, for combining with what a caller may do."""

    model_config = ConfigDict(extra="allow")

    protection_level: str | None = None
    is_enabled: bool = True


class ContentTypeAccess(BaseModel):
    """What a caller may do with one content type.

    ``objects`` lists the keys the caller is restricted to; ``None`` means every
    object.
    """

    model_config = ConfigDict(extra="allow")

    actions: list[str] = []
    objects: list[str] | None = None


class MyPermissions(BaseModel):
    """What the authenticated caller may do in the environment.

    This says what the caller is allowed, not whether an action is available now:
    billing and usage blocks, a blocked organization, environment protection and a
    disabled environment can still refuse it.
    """

    model_config = ConfigDict(extra="allow")

    subject: str  # "user" or "api_key"
    organization_owner: bool = False
    organization_admin: bool = False
    project_admin: bool = False
    environment_full_access: bool = False
    environment: EnvironmentAccess
    content_types: dict[str, ContentTypeAccess] = {}


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
    "BatchUpsertItem",
    "BatchItemError",
    "BatchUpsertResult",
    "FlatRoute",
    "FlatRouteSummary",
    "UploadLinkCreator",
    "UploadFileProgress",
    "UploadLinkFile",
    "UploadLinkSession",
    "UploadLink",
    "UploadLinkList",
    "UploadLinkCreated",
    "FileAnalysis",
    "FileCheck",
    "FileFinding",
    "FileCopyAvailability",
    "FileActiveContent",
    "FileDownloadOptions",
    "FileRecordView",
    "FileDownload",
    "FilePageRedaction",
    "FilePageTable",
    "FilePageDetail",
    "FileTombstone",
    "FileTombstoneList",
    "FileFindingsSummary",
    "FileReviewItem",
    "FileReviewQueue",
    "FilesPolicyBody",
    "FilesPolicy",
    "FileOrigin",
    "FileOriginActor",
    "FileOriginLink",
    "FileSummary",
    "FileRecordOwner",
    "FileInfo",
    "FileEvidencePart",
    "FileTextEvidence",
    "FileTrust",
    "FilePagePii",
    "FileFindingGroup",
    "FilePageFinding",
    "EnvironmentAccess",
    "ContentTypeAccess",
    "MyPermissions",
]
