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
resource = client.create_resource(folder, {"title": "New Post"})
revision = client.create_revision(folder, resource, {"title": "Draft"})
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
        "title": "My Article",
        "content": "Article content here...",
    },
)
```

### Update Resource

```python
resource = client.update_resource(
    "folder-key",
    "resource-key",
    {
        "title": "Updated Title",
        "content": "Updated content...",
    },
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
        "title": "New Title",
        "content": "New content...",
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
        "name": "title",
        "alias": "title",
        "field_type": "text",
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
        "content_type": "document",
        "can_read": True,
        "can_create": True,
        "can_update": True,
        "can_delete": False,
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
        "content_type": "document",
        "can_read": True,
    },
)
```

### API Keys

```python
# Management API key
mgmt_key = client.create_management_api_key({
    "name": "CI/CD Key",
    "roles": ["role-key-1", "role-key-2"],
})

# Flux API key
flux_key = client.create_flux_api_key({
    "name": "Frontend Key",
    "roles": ["reader-role"],
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
