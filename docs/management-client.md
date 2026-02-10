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
# Raises FoxnoseAPIError on first failure
try:
    result = client.batch_upsert_resources("folder-key", items, fail_fast=True)
except FoxnoseAPIError as exc:
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
        "all_objects": True,
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
        "all_objects": True,
    },
)
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
