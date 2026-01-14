# Examples

This page provides links to complete code examples demonstrating common use cases.

## Available Examples

All examples are located in the [`examples/`](https://github.com/foxnose/python-sdk/tree/main/examples) directory.

### Basic Usage

**File:** `examples/basic_usage.py`

Demonstrates fundamental SDK operations:

- Client initialization with JWT authentication
- Listing folders and resources
- Creating and updating folders
- Proper client cleanup

```python
from foxnose_sdk.management import ManagementClient
from foxnose_sdk.auth import JWTAuth

client = ManagementClient(
    base_url="https://api.foxnose.net",
    environment_key="your-environment-key",
    auth=JWTAuth.from_static_token("YOUR_ACCESS_TOKEN"),
)

# List all folders
folders = client.list_folders()
for folder in folders.results:
    print(f"{folder.name} ({folder.key})")

client.close()
```

### Async Client

**File:** `examples/async_client.py`

Shows how to use the async client for concurrent operations:

- AsyncManagementClient setup
- Concurrent API calls with `asyncio.gather()`
- Proper async context management

```python
import asyncio
from foxnose_sdk.management import AsyncManagementClient

async def main():
    client = AsyncManagementClient(...)

    # Fetch multiple resources concurrently
    results = await asyncio.gather(
        client.get_folder("folder-1"),
        client.get_folder("folder-2"),
        client.list_resources("folder-3"),
    )

    await client.close()

asyncio.run(main())
```

### Resources and Revisions

**File:** `examples/resources_and_revisions.py`

Complete resource lifecycle management:

- Creating resources
- Managing revisions
- Publishing content
- Updating and deleting resources

```python
# Create a resource
resource = client.create_resource("blog-posts", {
    "title": "My First Post",
    "content": "Hello, world!",
})

# Create a new revision
revision = client.create_revision(
    "blog-posts",
    resource.key,
    {"title": "Updated Title", "content": "Updated content"},
)

# Publish the revision
client.publish_revision("blog-posts", resource.key, revision.key)
```

### Folder Schema

**File:** `examples/folder_schema.py`

Schema and field management:

- Creating schema versions
- Adding and configuring fields
- Publishing schema versions
- Field type options

```python
# Create a new schema version
version = client.create_folder_version("blog-posts", {"name": "v2.0"})

# Add fields
client.create_folder_field("blog-posts", version.key, {
    "name": "author",
    "alias": "author",
    "field_type": "text",
    "required": True,
})

# Publish the version
client.publish_folder_version("blog-posts", version.key)
```

### Roles and Permissions

**File:** `examples/roles_and_permissions.py`

Access control configuration:

- Creating management roles
- Creating Flux roles
- Setting permissions
- Generating API keys

```python
# Create a role
role = client.create_management_role({
    "name": "Content Editor",
    "description": "Can edit content but not delete",
})

# Add permissions
client.upsert_management_role_permission(role.key, {
    "content_type": "document",
    "can_read": True,
    "can_create": True,
    "can_update": True,
    "can_delete": False,
})

# Create an API key with this role
api_key = client.create_management_api_key({
    "name": "Editor Key",
    "roles": [role.key],
})
```

### Flux Client

**File:** `examples/flux_client.py`

Content delivery:

- FluxClient initialization
- Fetching published content
- Search capabilities
- Pagination and filtering

```python
from foxnose_sdk.flux import FluxClient
from foxnose_sdk.auth import SimpleKeyAuth

client = FluxClient(
    base_url="https://<env_key>.fxns.io",
    api_prefix="v1",
    auth=SimpleKeyAuth("YOUR_PUBLIC_KEY", "YOUR_SECRET_KEY"),
)

# Get published content
resource = client.get_resource("blog-posts", "my-article")
print(resource["title"])

# Search for content
results = client.search("blog-posts", body={"query": "python"})
```

## Running Examples

1. Clone the repository:

```bash
git clone https://github.com/foxnose/python-sdk.git
cd python-sdk
```

2. Install dependencies:

```bash
pip install -e .
```

3. Set environment variables:

```bash
export FOXNOSE_API_URL="https://api.foxnose.net"
export FOXNOSE_ENVIRONMENT_KEY="your-environment-key"
export FOXNOSE_ACCESS_TOKEN="your-access-token"
```

4. Run an example:

```bash
python examples/basic_usage.py
```

## Real-World Patterns

### Environment-Based Configuration

```python
import os
from foxnose_sdk.management import ManagementClient
from foxnose_sdk.auth import JWTAuth

def get_client():
    return ManagementClient(
        base_url=os.environ.get("FOXNOSE_API_URL", "https://api.foxnose.net"),
        environment_key=os.environ["FOXNOSE_ENVIRONMENT_KEY"],
        auth=JWTAuth.from_static_token(os.environ["FOXNOSE_ACCESS_TOKEN"]),
    )
```

### Context Manager Pattern

```python
from contextlib import contextmanager

@contextmanager
def foxnose_client():
    client = ManagementClient(...)
    try:
        yield client
    finally:
        client.close()

# Usage
with foxnose_client() as client:
    folders = client.list_folders()
```

### Pagination Helper

```python
def iter_all_resources(client, folder_key, page_size=50):
    """Iterate through all resources with automatic pagination."""
    offset = 0
    while True:
        page = client.list_resources(
            folder_key,
            params={"limit": page_size, "offset": offset},
        )
        yield from page.results

        if len(page.results) < page_size:
            break
        offset += page_size

# Usage
for resource in iter_all_resources(client, "blog-posts"):
    print(resource.title)
```
