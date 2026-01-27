# Flux Client

The `FluxClient` provides access to the FoxNose Flux API for content delivery.

## Overview

The Flux API is designed for:

- **Read-only access** to published content
- **Fast response times** optimized for high performance
- **Public access** with API key authentication
- **Search** capabilities for content discovery

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

```python
# First page
page1 = client.list_resources("posts", params={"limit": 10})

# Next page (use the cursor from the previous response)
if page1["next"]:
    page2 = client.list_resources("posts", params={"limit": 10, "next": "<cursor>"})

print(f"Got {len(page1['results'])} items")
```

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
