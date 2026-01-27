# FoxNose Python SDK

[![PyPI version](https://img.shields.io/pypi/v/foxnose-sdk.svg)](https://pypi.org/project/foxnose-sdk/)
[![Python versions](https://img.shields.io/pypi/pyversions/foxnose-sdk.svg)](https://pypi.org/project/foxnose-sdk/)
[![CI](https://github.com/FoxNoseTech/foxnose-python/actions/workflows/ci.yml/badge.svg)](https://github.com/FoxNoseTech/foxnose-python/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/FoxNoseTech/foxnose-python/graph/badge.svg)](https://codecov.io/gh/FoxNoseTech/foxnose-python)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

[FoxNose](https://foxnose.net?utm_source=github&utm_medium=repository&utm_campaign=foxnose-python) is a managed knowledge layer for RAG and AI agents — auto-embeddings, hybrid search, and zero ETL pipelines to maintain.

This is the official Python SDK for FoxNose Management and Flux APIs.

## Features

- **Type-safe clients** - Full type hints and Pydantic models
- **Sync and async** - Both synchronous and asynchronous clients
- **Automatic retries** - Configurable retry with exponential backoff
- **JWT authentication** - Built-in token refresh support

## Documentation

**SDK Documentation:** [foxnose-python.readthedocs.io](https://foxnose-python.readthedocs.io)

**FoxNose Platform:**
- [Product Documentation](https://foxnose.net/docs?utm_source=github&utm_medium=repository&utm_campaign=foxnose-python)
- [Guides](https://foxnose.net/docs/guides?utm_source=github&utm_medium=repository&utm_campaign=foxnose-python)
- [Management API Reference](https://foxnose.net/docs/management-api/v1/get-started?utm_source=github&utm_medium=repository&utm_campaign=foxnose-python)
- [Flux API Reference](https://foxnose.net/docs/flux-api/v1/get-started?utm_source=github&utm_medium=repository&utm_campaign=foxnose-python)

## Installation

```bash
pip install foxnose-sdk
```

## Quick Start

To get started, you'll need a FoxNose account. [Create one here](https://app.foxnose.net).

```python
from foxnose_sdk.management import ManagementClient
from foxnose_sdk.auth import JWTAuth

client = ManagementClient(
    base_url="https://api.foxnose.net",
    environment_key="your-environment-key",
    auth=JWTAuth.from_static_token("YOUR_ACCESS_TOKEN"),
)

# List folders
folders = client.list_folders()
for folder in folders.results:
    print(f"{folder.name} ({folder.key})")

client.close()
```

### Async Client

```python
from foxnose_sdk.management import AsyncManagementClient

async def main():
    client = AsyncManagementClient(
        base_url="https://api.foxnose.net",
        environment_key="your-environment-key",
        auth=JWTAuth.from_static_token("YOUR_ACCESS_TOKEN"),
    )

    folders = await client.list_folders()
    await client.aclose()
```

### Flux Client

```python
from foxnose_sdk.flux import FluxClient
from foxnose_sdk.auth import SimpleKeyAuth

client = FluxClient(
    base_url="https://<env_key>.fxns.io",
    api_prefix="v1",
    auth=SimpleKeyAuth("PUBLIC_KEY", "SECRET_KEY"),
)

resources = client.list_resources("blog-posts")
client.close()
```

## Development

```bash
# Install with dev dependencies
pip install -e .[test,docs]

# Run tests
pytest

# Run tests with coverage
pytest --cov=foxnose_sdk --cov-report=term-missing

# Build docs
mkdocs serve
```

## License

Apache 2.0 - see [LICENSE](LICENSE) for details.
