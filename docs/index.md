# FoxNose Python SDK

Official Python client for FoxNose Management and Flux APIs.

## Features

- **Type-safe clients** - Full type hints and Pydantic models for all API responses
- **Sync and async support** - Both synchronous and asynchronous clients available
- **Automatic retries** - Configurable retry logic with exponential backoff
- **JWT authentication** - Built-in support for JWT tokens with automatic refresh
- **Comprehensive coverage** - Access to all Management and Flux API endpoints

## Installation

```bash
pip install foxnose-sdk
```

## Quick Start

```python
from foxnose_sdk.management import ManagementClient
from foxnose_sdk.auth import JWTAuth

# Initialize the client
client = ManagementClient(
    base_url="https://api.foxnose.net",
    environment_key="your-environment-key",
    auth=JWTAuth.from_static_token("YOUR_ACCESS_TOKEN"),
)

# List folders
folders = client.list_folders()
for folder in folders.results:
    print(f"{folder.name} ({folder.key})")

# Don't forget to close
client.close()
```

## Clients

The SDK provides two main clients:

### ManagementClient

For administrative operations:

- Managing folders, components, and schemas
- Creating and managing resources and revisions
- Configuring roles, permissions, and API keys
- Managing organizations, projects, and environments

### FluxClient

For content delivery:

- Fetching published resources
- Accessing localized content
- Search capabilities

## Next Steps

- [Getting Started](getting-started.md) - Installation and basic setup
- [Authentication](authentication.md) - Configure authentication methods
- [Examples](examples.md) - Code examples for common use cases
