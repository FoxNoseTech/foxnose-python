# Getting Started

This guide will help you install and set up the FoxNose Python SDK.

## Requirements

- Python 3.9 or higher
- pip or another Python package manager

## Installation

Install the SDK using pip:

```bash
pip install foxnose-sdk
```

Or with poetry:

```bash
poetry add foxnose-sdk
```

## Configuration

### Environment Key

Every API request requires an environment key. You can find this in your FoxNose dashboard under Project Settings.

### Authentication

The SDK supports multiple authentication methods. The most common is JWT authentication:

```python
from foxnose_sdk.auth import JWTAuth

auth = JWTAuth.from_static_token("YOUR_ACCESS_TOKEN")
```

See [Authentication](authentication.md) for more details.

## Basic Usage

### Management Client

The `ManagementClient` is used for administrative operations:

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
print(f"Found {len(folders.results)} folders")

# Always close the client when done
client.close()
```

### Async Client

For async applications, use `AsyncManagementClient`:

```python
import asyncio
from foxnose_sdk.management import AsyncManagementClient
from foxnose_sdk.auth import JWTAuth

async def main():
    client = AsyncManagementClient(
        base_url="https://api.foxnose.net",
        environment_key="your-environment-key",
        auth=JWTAuth.from_static_token("YOUR_ACCESS_TOKEN"),
    )

    folders = await client.list_folders()
    print(f"Found {len(folders.results)} folders")

    await client.close()

asyncio.run(main())
```

### Flux Client

The `FluxClient` is optimized for content delivery:

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
print(resource)

client.close()
```

## Error Handling

All API errors raise `FoxnoseAPIError`:

```python
from foxnose_sdk.errors import FoxnoseAPIError

try:
    folder = client.get_folder("non-existent-key")
except FoxnoseAPIError as e:
    print(f"Error {e.status_code}: {e.message}")
```

See [Error Handling](error-handling.md) for more details.

## Next Steps

- [Authentication](authentication.md) - Learn about authentication options
- [Management Client](management-client.md) - Explore Management API operations
- [Examples](examples.md) - See complete code examples
