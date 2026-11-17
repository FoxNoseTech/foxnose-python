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
- **FoxNose Files** - Upload links, analysis, review, policy and short-lived downloads
- **Outbound webhooks** - Endpoints, signing secrets, the event log, redelivery and recovery

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

### Handling billing errors

Billing and quota responses raise typed subclasses of `FoxnoseAPIError`, so
existing `except FoxnoseAPIError` handlers keep working while new code can read
the typed attributes:

```python
from foxnose_sdk import (
    SpendCapExceeded,
    PlanExhausted,
    PlanLimitExceeded,
    RateLimitExceeded,
)

try:
    client.create_collection({"name": "Blog"})
except SpendCapExceeded as e:  # HTTP 402
    print(f"Spend cap {e.cap_usd}; resets at {e.cycle_resets_at}: {e.raise_cap_url}")
except PlanExhausted as e:  # HTTP 402
    print(f"Allowance for {e.axis} exhausted; resets at {e.window_resets_at}")
except PlanLimitExceeded as e:  # HTTP 403
    print(f"{e.entity}: {e.current}/{e.limit}. Upgrade: {e.upgrade_url}")
except RateLimitExceeded as e:  # HTTP 429
    print(f"Rate limited; retry after {e.retry_after}s")
```

All four subclass `FoxnoseAPIError`, so a single `except FoxnoseAPIError` still
catches them if you don't need the typed fields.

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

# Writes require a write-capable key. Create publishes immediately; `key` is an
# optional external id used to deduplicate. update_resource is a full replace.
created = client.create_resource("blog-posts", {"title": "Hello"}, key="my-id")
client.update_resource("blog-posts", created["resource_key"], {"title": "Hello (edited)"})

client.close()
```

### Webhooks

FoxNose sends a signed `POST` to your endpoint when a subscribed event happens. Endpoints and the event log run through the Management client, in sync and async alike.

```python
from datetime import datetime, timedelta, timezone

endpoint = client.create_webhook_endpoint(
    url="https://hooks.example.com/foxnose",
    event_types=["revision.published", "resource.deleted"],
    collection_keys=["mK8nP3tYvBcX"],  # omit for every collection
    payload_mode="content",            # or "references" (the default)
)
store_secret(endpoint.secret)  # also readable later with get_webhook_endpoint_secret

client.send_webhook_test_event(endpoint.id, "revision.published")

# After an outage: send the failed deliveries of the last day again.
since = datetime.now(timezone.utc) - timedelta(days=1)
while True:
    result = client.recover_webhook_deliveries(endpoint.id, since=since)
    if not result.more:
        break

# Or send one logged event to one endpoint again.
client.redeliver_webhook_event("evt_01JCX3Q9W2B5V7RZ0D4K6M8P1T", endpoint_id=endpoint.id)
```

| Call | What it does |
|---|---|
| `list_webhook_endpoints` / `create_webhook_endpoint` / `get_webhook_endpoint` / `update_webhook_endpoint` / `delete_webhook_endpoint` | Endpoints of the environment; a list carries `stats_24h` |
| `list_webhook_endpoint_deliveries` | An endpoint's deliveries, each with the event it carries |
| `get_webhook_endpoint_secret` / `rotate_webhook_endpoint_secret` | Read or replace the signing secret |
| `send_webhook_test_event` | A sample event to one endpoint |
| `recover_webhook_deliveries` | Send an endpoint's failed deliveries again |
| `list_webhook_events` / `get_webhook_event` / `list_webhook_event_attempts` | The 30-day event log |
| `redeliver_webhook_event` | Send a logged event again |
| `list_webhook_event_types` | The event-type catalogue with JSON Schemas |

Deliveries follow [Standard Webhooks](https://www.standardwebhooks.com/), so the SDK has no verifier of its own: use a Standard Webhooks library with the endpoint's secret.

```python
# pip install standardwebhooks
from standardwebhooks.webhooks import Webhook

event = Webhook(secret).verify(request_body, request_headers)  # raises on a bad signature
```

`secret` of an endpoint is a credential: `repr()` of the secret models leaves it out, and it should stay out of logs. See the [Management client guide](https://foxnose-python.readthedocs.io/en/latest/management-client/#webhooks).

### Files

FoxNose Files takes uploads from end users and processes them for agents. Upload links and review run through the Management client, in sync and async alike.

```python
# A hosted page for an end user. The collection must be strict, and `owner` is
# the parent record. Works with a user token or a Management API key.
link = client.create_upload_link(
    "attachments",
    owner="tk_8f2c91",
    title="Upload your documents",
    max_files=3,
)
send_to_user(link.upload_url)  # returned once; no later read reproduces it

# Read the link back through the Management API.
link = client.get_upload_link("attachments", link.upload_id)
keys = [f.record_key for s in link.sessions for f in s.files if f.state == "ready"]

# The record's verdict, checks and findings.
view = client.get_file_analysis("attachments", keys[0])

# A download is a short-lived link. It is returned, never streamed.
safe_copy = client.get_file_safe_copy("attachments", keys[0])
print(safe_copy.url, safe_copy.expires_at)
```

| Call | What it does |
|---|---|
| `list_upload_links` / `create_upload_link` / `get_upload_link` / `revoke_upload_link` | Upload links of a collection |
| `get_file_analysis` | A record's file, verdict, checks and findings; `text_evidence` reads a finding's text |
| `approve_file` / `reject_file` / `reanalyze_file` | Decide on a held file, or analyze a file again |
| `get_file_original` / `get_file_safe_copy` / `get_file_page` | A short-lived link to one copy |
| `get_file_page_detail` | One page: redacted image, withheld regions, tables and text |
| `list_file_tombstones` | Blocked and rejected files |
| `get_files_policy` / `update_files_policy` | The collection's policy |
| `list_file_review_queue` | Files held for a reviewer in the environment |
| `get_my_permissions` | What the caller may do in the environment |

On the Flux client, a key takes a grant for one upload and polls it:

```python
grant = flux.create_upload_signature("tickets/tk_8f2c91/attachments")
status = flux.get_upload_status("tickets/tk_8f2c91/attachments", grant.upload_id)
```

The grant is a credential: `repr()` leaves its tokens out, and it should stay out of logs. Flux status answers only the Flux key that started the upload, so a link made through the Management API is read with `get_upload_link`. See the [Management client](https://foxnose-python.readthedocs.io/en/latest/management-client/#files) and [Flux client](https://foxnose-python.readthedocs.io/en/latest/flux-client/#file-uploads) guides.

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
