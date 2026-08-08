# Flux Client

The `FluxClient` provides access to the FoxNose Flux API for content delivery.

## Overview

The Flux API is designed for:

- **Fast reads** of published content
- **API key authentication** (public reads; writes require a write-capable key)
- **Search** capabilities for content discovery
- **Writes** — create and replace resources

## Initialization

```python
from foxnose_sdk.flux import FluxClient
from foxnose_sdk.auth import SimpleKeyAuth

client = FluxClient(
    base_url="https://<env_key>.fxns.io",  # Your environment URL
    api_prefix="v1",  # Your API prefix
    auth=SimpleKeyAuth("YOUR_PUBLIC_KEY", "YOUR_SECRET_KEY"),
)
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `base_url` | `str` | Yes | Your Flux URL: `https://<env_key>.fxns.io` |
| `api_prefix` | `str` | Yes | API prefix for routing |
| `auth` | `AuthStrategy` | Yes | Authentication strategy |
| `timeout` | `float` | No | Request timeout in seconds (default: 15.0) |
| `retry_config` | `RetryConfig` | No | Retry configuration |
| `default_headers` | `Mapping[str, str]` | No | Headers to include in all requests |
| `verify_ssl` | `bool` | No | Verify SSL certificates (default: True) |

## Fetching Resources

### List Resources

Fetch a list of published resources from a folder:

```python
resources = client.list_resources(
    "blog-posts",  # folder path
    params={"limit": 10},
)

for resource in resources["results"]:
    print(f"{resource['_sys']['key']}: {resource['data']['title']}")
```

### Get Resource

Fetch a specific resource by key:

```python
resource = client.get_resource("blog-posts", "my-first-post")
print(resource["data"]["title"])
print(resource["data"]["content"])
```

### Get Resource with Params

```python
resource = client.get_resource(
    "blog-posts",
    "my-article",
    params={"return_locales": "de"},
)
```

## Search

Search for resources within a folder:

```python
results = client.search(
    "blog-posts",
    body={
        "find_text": {"query": "python tutorial"},
        "limit": 10,
    },
)

for item in results["results"]:
    print(item["data"]["title"])
```

`search()` also accepts a keyword-only `params` mapping, forwarded to the
query string (not the body) — e.g. `params={"truncate_text": 200}`. See
[Truncating Text Fields](#truncating-text-fields) below.

## Writing Resources

Writes require a write-capable key. Creating and updating publish immediately;
the response carries `resource_key`, `revision_key`, `write_units`, and
`published`.

```python
# Create a resource. `key` is an optional external identifier used to
# deduplicate — reusing an existing key raises ExternalIdConflict.
created = client.create_resource(
    "blog-posts",
    {"title": "Hello", "body": "..."},
    key="my-external-id",
)

# Replace the whole document (this is a full replace, not a partial merge).
client.update_resource("blog-posts", created["resource_key"], {"title": "Hello (edited)"})
```

Writes also work with nested collection paths, e.g.
`client.create_resource("users/usr_1/memories", {...})`.

Writes are never retried automatically: a failed write's outcome is unknown, so
on `UpstreamError` re-read the resource with a GET before deciding to retry.

## Vector Search

The Flux API supports multiple vector search modes. See the [Vector Search guide](vector-search.md) for full documentation.

### Quick Examples

```python
# Semantic search with auto-generated embeddings
results = client.vector_search(
    "blog-posts",
    query="machine learning in healthcare",
    top_k=10,
)

# Search with custom embeddings
results = client.vector_field_search(
    "speakers",
    field="speaker_embedding",
    query_vector=[0.012, -0.034, 0.056, ...],
)

# Hybrid text + vector search
results = client.hybrid_search(
    "blog-posts",
    query="ML applications",
    find_text={"query": "machine learning"},
    vector_weight=0.7,
    text_weight=0.3,
)

# Text search boosted by vector similarity
results = client.boosted_search(
    "blog-posts",
    find_text={"query": "python tutorial"},
    query="beginner programming guide",
    boost_factor=1.5,
)
```

All vector search methods support `offset`, `limit`, and `**extra_body` for additional parameters like `where` and `sort`.

The raw `search()` method continues to work with plain dicts for backward compatibility.

## Introspection Endpoints

Use Flux introspection to discover available routes and live schema metadata at runtime.

### Router Introspection

```python
router = client.get_router()
print(router["api"])
print(f"Discovered routes: {len(router['routes'])}")
```

### Schema Introspection

```python
schema = client.get_schema("blog-posts")
print(schema["path"])
print(schema["searchable_fields"])
print(schema["json_schema"]["type"])
```

Async usage:

```python
router = await client.get_router()
schema = await client.get_schema("blog-posts")
```

## Query Parameters

### Filtering

```python
resources = client.list_resources(
    "products",
    params={
        "where__category__eq": "electronics",
        "where__in_stock__eq": "true",
    },
)
```

### Sorting

```python
resources = client.list_resources(
    "blog-posts",
    params={
        "sort": "-published_at",  # Descending by publish date
    },
)
```

### Pagination

`next` in the response is a full absolute URL (e.g.
`https://<env>.fxns.io/<prefix>/posts?limit=10&next=Xk6KmhmHZuAU`), not a bare
cursor. The SDK does not follow it automatically — `list_resources` always
targets the configured `base_url`/`api_prefix`, so a server-returned absolute
URL can't be fed back in directly. Extract the `next` query parameter and
re-pass it (along with any other parameters you want to keep, such as
`truncate_text`) instead:

```python
from urllib.parse import urlparse, parse_qs

# First page
page1 = client.list_resources("posts", params={"limit": 10, "truncate_text": 200})

# Next page: pull the cursor out of the absolute `next` URL and re-pass it
# alongside the parameters you want to carry forward.
if page1["next"]:
    cursor = parse_qs(urlparse(page1["next"]).query)["next"][0]
    page2 = client.list_resources(
        "posts",
        params={"limit": 10, "truncate_text": 200, "next": cursor},
    )

print(f"Got {len(page1['results'])} items")
```

If you ever build a helper that follows `next` automatically, validate that
the URL is same-origin with your configured `base_url` *before* attaching any
auth header — blindly following a server-supplied absolute URL with
credentials attached is an SSRF and credential-leak vector.

### Truncating Text Fields

Pass `truncate_text` (an integer ≥ 1) on List Resources or Search to cap
every `text`-typed field in the response. It has no effect when `raw=true`.

```python
resources = client.list_resources("blog-posts", params={"truncate_text": 200})
results = client.search(
    "blog-posts",
    body={"find_text": {"query": "python"}},
    params={"truncate_text": 200},
)
```

Truncated fields are marked under `_sys.truncated`:

```json
{
  "_sys": {
    "key": "Cpa3KebZoqb3",
    "truncated": [{"field": "body", "locale": null, "original_length": 210}]
  }
}
```

`locale` is `null` for non-localized fields; fields within the limit get no
entry. The SDK does not validate `truncate_text` client-side — there is no
typed request model for query parameters to hang a validator on. An invalid
value (non-integer, or < 1) surfaces as a server `422 validation_error`.

The same parameter works with the typed search wrappers — `vector_search()`,
`vector_field_search()`, `hybrid_search()`, `boosted_search()` — via
`query_params`, e.g. `client.vector_search("blog-posts", query="ml",
query_params={"truncate_text": 200})`. Use `query_params`, not `params`: the
wrappers already collect unrecognized keyword arguments (like `where` and
`sort`) into the JSON body, and `params` is a plausible body field name.
Passing `truncate_text` as a body field raises a clear error naming
`query_params` as the fix.

## Cross-Parent Addressing

A strict-reference collection nested under one or more parents can also be
configured (via the Management API, see
[API Folder Route Descriptions](management-client.md#api-folder-route-descriptions))
to expose additional, read-only addresses that drop some or all of the
ancestor keys from the path:

```python
# Normal, fully-nested address:
client.list_resources("realty/accounts/acc_1/listings/lst_1/photos")

# Fully-flat (level 0): every ancestor key is dropped.
client.list_resources("realty/accounts/listings/photos")

# Partially-flat (level >= 1): the root-most ancestor key(s) are retained.
client.list_resources("realty/accounts/acc_1/listings/photos")
```

This works today for List Resources, Get Resource, and Schema — the folder
path is an opaque, slash-trimmed string with no segment parsing or ancestor
validation on the client side. **Writes cannot target a flat address**:
`FluxClient` has no method that would let you, and the server rejects writes
on flat paths regardless.

Not every configured level necessarily serves every read method. Before
relying on a flat address, check `enabled`, `available`, and `read_methods`
on the connection's `flat_routes` (see
[API Folder Route Descriptions](management-client.md#api-folder-route-descriptions))
rather than assuming every read method is available at every level — the
docs and the live API disagree on this in at least two ways that are still
open with the API team (Get Resource at level 0; Search never appears in
`read_methods` at any level).

## Error Handling

```python
from foxnose_sdk.errors import FoxnoseAPIError

try:
    resource = client.get_resource("posts", "non-existent")
except FoxnoseAPIError as e:
    if e.status_code == 404:
        print("Resource not found or not published")
    else:
        print(f"Error: {e.message}")
```

## Async Client

For async applications:

```python
from foxnose_sdk.flux import AsyncFluxClient
from foxnose_sdk.auth import SimpleKeyAuth

async def fetch_content():
    client = AsyncFluxClient(
        base_url="https://<env_key>.fxns.io",
        api_prefix="v1",
        auth=SimpleKeyAuth("YOUR_PUBLIC_KEY", "YOUR_SECRET_KEY"),
    )

    # Fetch multiple resources concurrently
    import asyncio

    results = await asyncio.gather(
        client.get_resource("posts", "article-1"),
        client.get_resource("posts", "article-2"),
        client.get_resource("posts", "article-3"),
    )

    await client.aclose()
    return results
```

## Best Practices

1. **Use folder paths** - Reference folders by their path for readability
2. **Handle 404s gracefully** - Resources may be unpublished
3. **Implement pagination** - Don't fetch all resources at once
4. **Use async for multiple requests** - Concurrent fetching improves performance

## Closing the Client

```python
client.close()

# Or for async:
await client.aclose()
```
