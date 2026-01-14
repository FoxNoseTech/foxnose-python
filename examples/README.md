# FoxNose SDK Examples

This directory contains example scripts demonstrating how to use the FoxNose Python SDK.

## Examples

| File | Description |
|------|-------------|
| [basic_usage.py](basic_usage.py) | Getting started with the ManagementClient |
| [async_client.py](async_client.py) | Using AsyncManagementClient for concurrent operations |
| [resources_and_revisions.py](resources_and_revisions.py) | Creating and managing content resources |
| [folder_schema.py](folder_schema.py) | Defining folder schemas and fields |
| [roles_and_permissions.py](roles_and_permissions.py) | Managing RBAC roles and API keys |
| [flux_client.py](flux_client.py) | Using FluxClient for content delivery |

## Running the Examples

1. Install the SDK:

```bash
pip install foxnose-sdk
```

2. Set up your credentials. You can either:
   - Replace the placeholder values in the example files
   - Use environment variables:

```bash
export FOXNOSE_ACCESS_TOKEN="your-access-token"
export FOXNOSE_ENVIRONMENT_KEY="your-environment-key"
```

3. Run an example:

```bash
python basic_usage.py
```

## Authentication

The SDK supports multiple authentication methods:

### JWT Authentication (Management API)

```python
from foxnose_sdk.auth import JWTAuth

# From a static token
auth = JWTAuth.from_static_token("ACCESS_TOKEN")

# With refresh token support
auth = JWTAuth(
    access_token="ACCESS_TOKEN",
    refresh_token="REFRESH_TOKEN",
)
```

### API Key Authentication (Flux API)

```python
from foxnose_sdk.auth import APIKeyAuth

auth = APIKeyAuth("YOUR_API_KEY")
```

## Error Handling

All API errors raise `FoxNoseAPIError`:

```python
from foxnose_sdk.errors import FoxNoseAPIError

try:
    resource = client.get_resource(folder_key, resource_key)
except FoxNoseAPIError as e:
    print(f"Status: {e.status_code}")
    print(f"Message: {e.message}")
    print(f"Details: {e.details}")
```

## Need Help?

- [Documentation](https://docs.foxnose.net)
- [API Reference](https://docs.foxnose.net/api)
- [GitHub Issues](https://github.com/FoxNoseTech/foxnose-python/issues)
