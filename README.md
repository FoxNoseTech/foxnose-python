# FoxNose Python SDK

[![PyPI version](https://img.shields.io/pypi/v/foxnose-sdk.svg)](https://pypi.org/project/foxnose-sdk/)
[![Python versions](https://img.shields.io/pypi/pyversions/foxnose-sdk.svg)](https://pypi.org/project/foxnose-sdk/)
[![CI](https://github.com/FoxNoseTech/foxnose-python/actions/workflows/ci.yml/badge.svg)](https://github.com/FoxNoseTech/foxnose-python/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/FoxNoseTech/foxnose-python/graph/badge.svg)](https://codecov.io/gh/FoxNoseTech/foxnose-python)
[![Docs](https://img.shields.io/badge/docs-foxnose--python.readthedocs.io-blue)](https://foxnose-python.readthedocs.io/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

[FoxNose](https://foxnose.net?utm_source=github&utm_medium=repository&utm_campaign=foxnose-python) is a managed knowledge layer for RAG and AI agents — auto-embeddings, hybrid search, and zero ETL pipelines to maintain.

This is the official Python SDK for FoxNose Management and Flux APIs.

## Features

- **Type-safe clients** - Full type hints and Pydantic models
- **Sync and async** - Both synchronous and asynchronous clients
- **Automatic retries** - Configurable retry with exponential backoff
- **JWT authentication** - Built-in token refresh support
- **Flux introspection** - Discover routes and live schema via `/_router` and `/_schema`

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

# List collections
collections = client.list_collections()
for collection in collections.results:
    print(f"{collection.name} ({collection.key})")

client.close()
```

> **Note (0.6.0):** Folder-named methods (`list_folders`, `create_folder`, `add_api_folder`,
> `list_folder_versions`, `list_folder_fields`, etc.) remain as deprecated aliases that
> emit a one-shot `DeprecationWarning` on first use per process. They keep their
> original wire behaviour (hitting the legacy `/folders/...` URL alias on the server)
> and will be removed in **1.0**. Prefer the `*_collection*` names in new code.

### Async Client

```python
from foxnose_sdk.management import AsyncManagementClient

async def main():
    client = AsyncManagementClient(
        base_url="https://api.foxnose.net",
        environment_key="your-environment-key",
        auth=JWTAuth.from_static_token("YOUR_ACCESS_TOKEN"),
    )

    collections = await client.list_collections()
    await client.aclose()
```

### Components on Collections

Collections can embed Components as nested fields with explicit pin
semantics (`component`, `component_version`, `auto_update`). The
`NestedFieldMeta` helper builds the `meta` block for you, and
`sync_collection_component` advances pinned fields to a target Component
version on demand.

```python
from foxnose_sdk import (
    ManagementClient,
    FoxnoseConfig,
    NestedFieldMeta,
)
from foxnose_sdk.auth import JWTAuth

client = ManagementClient(
    FoxnoseConfig(base_url="https://api.foxnose.com"),
    environment_key="prod",
    auth=JWTAuth("ACCESS_TOKEN"),
)

# Embed a Component as a pinned nested field on a Collection draft.
client.create_collection_field(
    "articles",
    "v2-draft",
    {
        "key": "seo",
        "name": "SEO",
        "type": "nested",
        "required": True,
        "meta": NestedFieldMeta(
            component="cmp-seo-metadata",
            component_version="ver-abc12345",
            auto_update=False,  # default — pin until explicit sync
        ).to_meta(),
    },
)

# Later, advance every pinned nested field to its Component's current
# version (empty body = sync all pinned).
result = client.sync_collection_component("articles")
print(result.synced_paths, result.schema_version)

# Advance specific paths to a chosen Component version.
result = client.sync_collection_component(
    "articles",
    field_paths=["seo"],
    to_versions={"seo": "ver-def67890"},
)
```

`sync_collection_component` returns a `SyncComponentResponse` with
`synced_paths`, `skipped` (per-path reasons), and `schema_version` (UID
of the newly published Collection schema version, or `None` if no field
needed advancing). On compatibility conflict the server returns 409
`component_sync_conflict`; quota exhaustion returns 422
`too_many_versions`. Both surface as `FoxnoseAPIError`.

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
