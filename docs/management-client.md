# Management Client

The `ManagementClient` provides access to the FoxNose Management API for administrative operations.

## Initialization

```python
from foxnose_sdk.management import ManagementClient
from foxnose_sdk.auth import JWTAuth

client = ManagementClient(
    base_url="https://api.foxnose.net",
    environment_key="your-environment-key",
    auth=JWTAuth.from_static_token("YOUR_ACCESS_TOKEN"),
    timeout=30.0,  # Optional: request timeout in seconds
)
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `base_url` | `str` | No | API base URL (default: `https://api.foxnose.net`) |
| `environment_key` | `str` | Yes | Your environment identifier |
| `auth` | `AuthStrategy` | Yes | Authentication strategy |
| `timeout` | `float` | No | Request timeout in seconds (default: 30.0) |
| `retry_config` | `RetryConfig` | No | Retry configuration |
| `default_headers` | `Mapping[str, str]` | No | Headers to include in all requests |

## Using Model Objects as Identifiers

All client methods that accept a `*_key` string parameter also accept the corresponding model object. The SDK automatically extracts the `.key` attribute from the object. This means you can pass objects returned by the API directly into subsequent calls without manually extracting keys.

```python
# Before: manually extracting keys
folder = client.get_folder("folder-key")
resources = client.list_resources(folder.key)
resource = client.get_resource(folder.key, resources.results[0].key)

# After: passing objects directly
folder = client.get_folder("folder-key")
resources = client.list_resources(folder)
resource = client.get_resource(folder, resources.results[0])
```

This works across all methods and supports chaining naturally:

```python
# Create a resource and publish a revision in one flow
folder = client.get_folder("blog-posts")
resource = client.create_resource(folder, {"data": {"title": "New Post"}})
revision = client.create_revision(folder, resource, {"data": {"title": "Draft"}})
client.publish_revision(folder, resource, revision)
```

String keys continue to work everywhere — this is fully backward compatible.

### Available Type Aliases

For type annotations in your own code, the SDK exports these reference types:

| Type alias | Accepts |
|------------|---------|
| `FolderRef` | `str` or `FolderSummary` |
| `ResourceRef` | `str` or `ResourceSummary` |
| `RevisionRef` | `str` or `RevisionSummary` |
| `ComponentRef` | `str` or `ComponentSummary` |
| `SchemaVersionRef` | `str` or `SchemaVersionSummary` |
| `OrgRef` | `str` or `OrganizationSummary` |
| `ProjectRef` | `str` or `ProjectSummary` |
| `EnvironmentRef` | `str` or `EnvironmentSummary` |
| `ManagementRoleRef` | `str` or `ManagementRoleSummary` |
| `FluxRoleRef` | `str` or `FluxRoleSummary` |
| `ManagementAPIKeyRef` | `str` or `ManagementAPIKeySummary` |
| `FluxAPIKeyRef` | `str` or `FluxAPIKeySummary` |
| `APIRef` | `str` or `APIInfo` |

```python
from foxnose_sdk import FolderRef, ResourceRef

def publish_all(client, folder: FolderRef):
    resources = client.list_resources(folder)
    for resource in resources.results:
        revisions = client.list_revisions(folder, resource)
        # ...
```

## APIs

```python
api = client.create_api(
    {
        "name": "Storefront",
        "prefix": "shop",
        "is_auth_required": False,
        "cors_origins": ["*"],  # browser CORS for public APIs (reads only)
    }
)
print(api.key, api.cors_origins)
```

`cors_origins` is a list of allowed browser origins (each including the scheme,
e.g. `https://app.example.com`) or `["*"]` for any origin; an empty list turns
CORS off. `mcp_enabled` and `router_introspection_enabled` (both default `True`)
control the `/{prefix}/_mcp` and `/{prefix}/_router` endpoints.

## API Folder Route Descriptions

When connecting a folder to a Flux API, you can configure per-route descriptions used by Flux `/_router` introspection.

```python
connection = client.add_api_folder(
    api_key="api-key",
    folder_key="folder-key",
    allowed_methods=["get_many", "get_one"],
    description_get_one="Get one article by key",
    description_get_many="List published articles",
    description_search="Search published articles",
    description_schema="Read article schema",
)

print(connection.description_schema)
```

To update descriptions later:

```python
updated = client.update_api_folder(
    "api-key",
    "folder-key",
    description_get_many="Public article feed",
    description_search="Search feed items",
)
```

### Cross-Parent (Flat) Read Addressing

For a strict-reference collection nested under one or more parents, pass
`unscoped_levels` and `unscoped_ancestors` to expose additional, read-only
addresses that drop some or all of the ancestor keys from the Flux path:

```python
connection = client.add_api_collection(
    api_key="api-key",
    collection_key="photos",
    unscoped_levels=[0],  # 0 = fully flat; 1+ retains that many root ancestors
    unscoped_ancestors=[
        "01debe0d-0325-42b1-9bfd-ef52046cd785",  # accounts connection (UUID)
        "432880c9-ae43-4462-b4f3-f16c18068ea5",  # listings connection (UUID)
    ],
)
```

The two must be sent together — the API rejects a level set with an empty
ancestor chain. This is not validated client-side; the server owns the rule
and may relax it.

`unscoped_ancestors` and the `omitted_ancestors` / `retained_ancestors`
entries below are connection UUIDs, **not** the short collection keys used
elsewhere (e.g. `folder`). Do not conflate the two.

The connection object returned by `add_api_collection`, `update_api_collection`,
`get_api_collection`, and `list_api_collections` carries these fields,
**read-only** — configure the addresses via `unscoped_levels` /
`unscoped_ancestors` above, not by constructing `flat_routes` yourself:

- `unscoped_levels: list[int]`, `unscoped_ancestors: list[str]` — echo what
  was configured.
- `expose_owner: bool` — present on the wire; semantics are unconfirmed, so
  the SDK does not expose a way to set it.
- `flat_routes: list[FlatRoute] | None` — one entry per configured level,
  each with `level`, `path`, `omitted_ancestors`, `retained_ancestors`,
  `enabled`, `read_methods`, `available`, `unavailable_reason`,
  `published_generation`, and `router_generation`. `None` when the
  connection has no key-bearing ancestor to flatten (not `[]`).
- `flat_route: FlatRouteSummary | None` — a single, undocumented field that
  appears to mirror whichever `flat_routes` entry is enabled. No behavior is
  built on it in the SDK.

Before relying on a flat address, check `enabled`, `available`, and
`read_methods` per entry — `read_methods` is typed exactly as the server
sends it, including two known discrepancies from the docs (raised with the
API team, not worked around here): Get Resource appears in `read_methods` at
level 0 even though the docs say it needs `level >= 1`, and `search` never
appears in `read_methods` at any level even though the docs list Search as
available on flat addresses.

## Folder Operations

### List Folders

```python
folders = client.list_folders()
for folder in folders.results:
    print(f"{folder.name} (key: {folder.key})")
```

### Get Folder

```python
folder = client.get_folder("folder-key")
print(f"Name: {folder.name}")
print(f"Type: {folder.folder_type}")
```

### Get Folder by Path

```python
folder = client.get_folder_by_path("parent/child")
```

### Create Folder

```python
folder = client.create_folder({
    "name": "Blog Posts",
    "alias": "blog-posts",
    "folder_type": "collection",
    "content_type": "document",
})
```

### Update Folder

```python
folder = client.update_folder("folder-key", {
    "name": "Updated Name",
})
```

### Delete Folder

```python
client.delete_folder("folder-key")
```

## Resource Operations

### List Resources

```python
resources = client.list_resources(
    "folder-key",
    params={"limit": 10, "offset": 0},
)
```

### Get Resource

```python
resource = client.get_resource("folder-key", "resource-key")
```

### Create Resource

```python
resource = client.create_resource(
    "folder-key",
    {
        "data": {
            "title": "My Article",
            "content": "Article content here...",
        },
    },
)
```

You can assign an `external_id` during creation to identify the resource by your own system's ID:

```python
resource = client.create_resource(
    "folder-key",
    {"title": "Imported Article", "content": "..."},
    external_id="cms-article-42",
)
```

### Upsert Resource

Create or update a resource in a single call using an `external_id`. If no resource with the given `external_id` exists in the folder, a new resource is created. If one already exists, a new revision is created for it.

```python
# First call: creates the resource
resource = client.upsert_resource(
    "folder-key",
    {"title": "My Article", "content": "First version"},
    external_id="cms-article-42",
)

# Second call with the same external_id: updates (creates a new revision)
resource = client.upsert_resource(
    "folder-key",
    {"title": "My Article", "content": "Updated version"},
    external_id="cms-article-42",
)
```

For component-based folders, pass the `component` parameter:

```python
resource = client.upsert_resource(
    "folder-key",
    {"title": "Product", "price": 29.99},
    external_id="product-100",
    component="product-component",
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `folder_key` | `FolderRef` | Yes | Target folder key or object |
| `payload` | `dict` | Yes | JSON payload matching the folder schema |
| `external_id` | `str` | Yes | External identifier for the resource |
| `component` | `ComponentRef` | No | Component key for composite folders |

### Batch Upsert Resources

Upsert many resources in parallel. The SDK fans out individual `upsert_resource()` calls using threads (sync client) or async tasks (async client), controlled by `max_concurrency`.

This is an SDK helper, not a separate Management API endpoint. Under the hood it executes concurrent `PUT /v1/:env/folders/:folder/resources/?external_id=<value>` calls.

```python
from foxnose_sdk import BatchUpsertItem

items = [
    BatchUpsertItem(external_id="ext-1", payload={"title": "Article 1"}),
    BatchUpsertItem(external_id="ext-2", payload={"title": "Article 2"}),
    BatchUpsertItem(external_id="ext-3", payload={"title": "Article 3"}),
]

result = client.batch_upsert_resources("folder-key", items, max_concurrency=10)

print(f"Succeeded: {result.success_count}, Failed: {result.failure_count}")
for error in result.failed:
    print(f"  [{error.index}] {error.external_id}: {error.exception}")
```

Async usage:

```python
result = await client.batch_upsert_resources("folder-key", items, max_concurrency=10)
```

**Error handling modes:**

- `fail_fast=False` (default) — process all items, collect successes and failures in the result.
- `fail_fast=True` — stop on the first error and raise it immediately.

```python
# Raises on first failed upsert call
try:
    result = client.batch_upsert_resources("folder-key", items, fail_fast=True)
except Exception as exc:
    print(f"Batch stopped: {exc}")
```

**Progress tracking:**

```python
result = client.batch_upsert_resources(
    "folder-key",
    items,
    on_progress=lambda done, total: print(f"{done}/{total}"),
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `folder_key` | `FolderRef` | Yes | Target folder key or object |
| `items` | `Sequence[BatchUpsertItem]` | Yes | Items to upsert |
| `max_concurrency` | `int` | No | Max parallel workers (default 5) |
| `fail_fast` | `bool` | No | Stop on first error (default `False`) |
| `on_progress` | `Callable[[int, int], None]` | No | Progress callback `(completed, total)` |

**`BatchUpsertItem` fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `external_id` | `str` | Yes | External identifier for the resource |
| `payload` | `dict` | Yes | JSON payload matching the folder schema |
| `component` | `str` | No | Component key for composite folders |

**`BatchUpsertResult` attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `succeeded` | `list[ResourceSummary]` | Successfully upserted resources |
| `failed` | `list[BatchItemError]` | Failed items with error details |
| `success_count` | `int` | Number of successes |
| `failure_count` | `int` | Number of failures |
| `total` | `int` | Total processed items |
| `has_failures` | `bool` | Whether any items failed |

### Update Resource

```python
resource = client.update_resource(
    "folder-key",
    "resource-key",
    {"name": "Updated Resource Name"},
)
```

### Delete Resource

```python
client.delete_resource("folder-key", "resource-key")
```

### Get Published Data

```python
data = client.get_resource_data("folder-key", "resource-key")
```

## Revision Operations

### List Revisions

```python
revisions = client.list_revisions("folder-key", "resource-key")
```

### Create Revision

```python
revision = client.create_revision(
    "folder-key",
    "resource-key",
    {
        "data": {
            "title": "New Title",
            "content": "New content...",
        },
    },
)
```

### Publish Revision

```python
revision = client.publish_revision(
    "folder-key",
    "resource-key",
    "revision-key",
)
```

### Validate Revision

```python
result = client.validate_revision(
    "folder-key",
    "resource-key",
    "revision-key",
)
if result.get("errors"):
    print("Validation errors:", result["errors"])
```

## Schema Operations

### Folder Versions

```python
# List versions
versions = client.list_folder_versions("folder-key")

# Create version
version = client.create_folder_version("folder-key", {"name": "v2.0"})

# Publish version
client.publish_folder_version("folder-key", "version-key")
```

### Schema Fields

```python
# List fields
fields = client.list_folder_fields("folder-key", "version-key")

# Create field
field = client.create_folder_field(
    "folder-key",
    "version-key",
    {
        "key": "title",
        "name": "Title",
        "type": "text",
        "required": True,
    },
)

# Update field
client.update_folder_field(
    "folder-key",
    "version-key",
    "title",
    {"description": "The article title"},
)

# Delete field
client.delete_folder_field("folder-key", "version-key", "title")
```

## Role and Permission Operations

### Management Roles

```python
# List roles
roles = client.list_management_roles()

# Create role
role = client.create_management_role({
    "name": "Editor",
    "description": "Content editor role",
    "full_access": False,
})

# Add permission
client.upsert_management_role_permission(
    "role-key",
    {
        "content_type": "resources",
        "actions": ["read", "create", "update"],
    },
)
```

### Flux Roles

```python
# Create Flux role
role = client.create_flux_role({
    "name": "Reader",
    "description": "Read-only access",
})

# Add permission
client.upsert_flux_role_permission(
    "role-key",
    {
        "content_type": "flux-apis",
        "actions": ["read"],
        "all_objects": False,
    },
)

# Scope access to specific Flux APIs
client.add_flux_permission_object(
    "role-key",
    {
        "content_type": "flux-apis",
        "object_key": "api-key-1",
    },
)

objects = client.list_flux_permission_objects(
    "role-key", content_type="flux-apis"
)
# objects is a list[RolePermissionObject]
```

### API Keys

```python
# Management API key
mgmt_key = client.create_management_api_key({
    "description": "CI/CD Key",
    "role": "role-key-1",
})

# Flux API key
flux_key = client.create_flux_api_key({
    "description": "Frontend Key",
    "role": "reader-role",
})
```

## Files

Calls for FoxNose Files collections. Each takes the collection key or a `CollectionSummary`, and a record call takes the record key or a `ResourceSummary`.

### Upload Links

An upload link opens a hosted page where an end user adds files. The collection must be strict, and `owner` is the parent record the files belong to. `title` is required. `expires_in` sets the link's lifetime, from 300 seconds to 86400 seconds; without it, the link lasts 30 minutes.

```python
link = client.create_upload_link(
    "attachments",
    owner="tk_8f2c91",
    title="Upload your documents",
    instructions="Add the signed contract.",
    max_files=3,
    allowed_kinds=["document", "image"],
    expires_in=3600,
)
send_to_user(link.upload_url)
```

`upload_url` carries the link's token. It is returned once, and `repr()` leaves it out.

```python
page = client.list_upload_links("attachments", params={"state": "active", "limit": 20})
link = client.get_upload_link("attachments", upload_id)
for session in link.sessions:
    for file in session.files:
        print(file.state, file.record_key, file.public_reason)

client.revoke_upload_link("attachments", upload_id)
```

A user token or a Management API key of the environment can create and revoke a link. `created_by.kind` is `user` or `api_key`. Read a link here, not through Flux: the Flux upload status answers only the Flux key that started an upload.

A link's `state` is `active`, `consumed`, `expired` or `revoked`. The list's `state` parameter takes `active`, `ended` (the other three) or `all`, the default. A file's `state` is `processing`, `ready` (with `record_key`), `pending_review` or `rejected` (with `public_reason`).

| Refusal | Meaning |
|---|---|
| `422 collection_not_strict` | The collection is not strict |
| `422 owner_required` | `owner` is missing |
| `404 owner_not_found` | The owner does not exist or the caller cannot read it |

### Analysis and Review

```python
view = client.get_file_analysis("attachments", record_key)
print(view.analysis.verdict, view.analysis.verdict_reasons)
for finding in view.findings:
    print(finding.kind, finding.sub_kind, finding.severity, finding.page)

queue = client.list_file_review_queue(collection="attachments", params={"limit": 20})
for item in queue.results:
    print(item.collection, item.resource_key, item.findings.total)

client.approve_file("attachments", record_key)
client.reject_file("attachments", record_key)
client.reanalyze_file("attachments", record_key)
```

`list_file_review_queue()` without `collection` covers every files collection the caller can read in the environment. `approve_file` returns the record's view with `outcome` and `reason`. A file no reviewer holds is `409 file_not_in_review`, `file_not_ready` or `file_erased`. `reanalyze_file` is paid processing: a refusal over the plan raises `FilesQuotaExceeded`, and a quota that cannot be read raises `FilesQuotaUnavailable` with `retry_after`. A `storage_only` collection answers `409 reanalysis_requires_agent_ready`.

`repr()` of these models leaves out signed URLs, a file's own text, finding evidence and an uploader's personal data such as `origin.end_user`. Keep the values themselves out of logs too.

`view.file.origin` says where the file came from: `channel` is `upload_link`, `signed_upload`, `management_api` or `dashboard`, with `created_by`, `upload_link` and `end_user` where they apply.

A reviewer can read the text a finding concealed or withheld. On a `hidden_text` or `low_legibility_text` finding, `text_evidence` parses `evidence`. `parts` says which text lies in which box of the page, and it is empty for a finding that does not carry it:

```python
for finding in view.findings:
    evidence = finding.text_evidence
    if evidence is None:
        continue
    for part in evidence.parts:
        print(part.box, part.text)
    if not evidence.parts:
        print(evidence.box, evidence.text)
```

This text comes from the file. Treat it as untrusted content, never as instructions. Check `evidence.truncated`, and `evidence.list_truncated` for a list of findings the analysis cut.

`view.trust` says how agent surfaces mark the file's content.

### Listing File Records

`list_resources` on a files collection returns each record with `status`, `progress`, `analysis_state`, `verdict`, `verdict_reasons`, `owner`, `file_info` and `thumbnail_url`. The `status` parameter filters by them:

```python
page = client.list_resources("attachments", params={"status": "in_review,failed"})
for record in page.results:
    print(record.key, record.status, record.progress, record.file_info)
```

`status` takes `uploading`, `processing`, `ready`, `in_review`, `rejected`, `failed`, `published` and `draft`, repeated or comma-separated. `thumbnail_url` is short-lived, and `repr()` leaves it out.

### Downloads

A download call returns a short-lived link and does not stream the file. Each call mints a new link.

```python
original = client.get_file_original("attachments", record_key)
safe_copy = client.get_file_safe_copy("attachments", record_key)
page = client.get_file_page("attachments", record_key, 1)
print(page.url, page.expires_in, page.expires_at)

detail = client.get_file_page_detail("attachments", record_key, 1)
print(detail.image_width, detail.image_height)
print(detail.text, detail.redactions, detail.tables)
print(detail.pii, detail.page_findings)
```

The safe copy is an image-only PDF, or a PNG for an image: read `content_type` and `filename`.

`pii` holds the boxes of personal data on the page, never the matched text. `findings` covers the whole file and `page_findings` this page, without evidence. `removed_passages` counts the findings whose text is withheld from agents.

`url` and `image_url` work for whoever holds them until they expire, and `repr()` leaves them out. Check `warnings` before opening an original.

A copy that cannot be downloaded now is a `409`. The reason is in the error:

```python
from foxnose_sdk import FoxnoseAPIError

try:
    original = client.get_file_original("attachments", record_key)
except FoxnoseAPIError as error:
    if error.status_code == 409:
        print(error.detail["reason"])
```

`get_file_analysis` shows the same answer ahead of time, in `view.file.original` and `view.file.safe_copy`.

### Policy and Tombstones

```python
policy = client.get_files_policy("attachments")

body = policy.body.model_copy(update={"suspicious_action": "quarantine"})
client.update_files_policy("attachments", body)

tombstones = client.list_file_tombstones("attachments", params={"limit": 20})
```

`update_files_policy` takes a `FilesPolicyBody` or a mapping and replaces the policy: an omitted field takes its default. `version` is `None` while the collection runs on the default policy.

## My Permissions

`get_my_permissions` says what the authenticated caller may do in the environment. It works for a user token and for a Management API key of this environment.

```python
mine = client.get_my_permissions()
print(mine.subject, mine.environment_full_access)

access = mine.content_types["resources"]
print(access.actions, access.objects)  # objects is None for every object
```

This reports what the caller is allowed. Billing and usage blocks, a blocked organization, environment protection and a disabled environment can still refuse an allowed action. `mine.environment` carries `protection_level` and `is_enabled` to combine with it. A caller with no grants is a `403`, and a key of another environment is a `404 environment_not_found`.

## Organization Operations

```python
# List organizations
orgs = client.list_organizations()

# Get organization
org = client.get_organization("org-key")

# Get usage
usage = client.get_organization_usage("org-key")
```

## Project Operations

```python
# List projects
projects = client.list_projects("org-key")

# Create project
project = client.create_project("org-key", {
    "name": "My Project",
})
```

## Environment Operations

```python
# List environments
envs = client.list_environments("org-key", "project-key")

# Create environment
env = client.create_environment("org-key", "project-key", {
    "name": "staging",
    "region": "eu-west-1",
})

# Toggle environment
client.toggle_environment("org-key", "project-key", "env-key", is_enabled=True)
```

## Async Client

The `AsyncManagementClient` provides the same methods with async/await support:

```python
from foxnose_sdk.management import AsyncManagementClient

async def main():
    client = AsyncManagementClient(
        base_url="https://api.foxnose.net",
        environment_key="your-environment-key",
        auth=JWTAuth.from_static_token("YOUR_TOKEN"),
    )

    folders = await client.list_folders()

    await client.close()
```

## Closing the Client

Always close the client to release resources:

```python
client.close()

# Or for async:
await client.close()
```
