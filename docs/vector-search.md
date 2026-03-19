# Vector Search

The FoxNose Flux API supports vector search for semantic content discovery. This guide covers all search modes and their configuration.

## Overview

Vector search enables finding content by meaning rather than exact keywords. The SDK provides:

- **Typed models** for building search requests with validation
- **Convenience methods** on `FluxClient` / `AsyncFluxClient` for common patterns
- **Backward-compatible** raw `search()` method for full control

## Search Modes

| Mode | Description |
|------|-------------|
| `text` | Traditional keyword/phrase search (default) |
| `vector` | Pure semantic search using embeddings |
| `vector_boosted` | Keyword search with results boosted by vector similarity |
| `hybrid` | Blended text + vector search with configurable weights |

## Vector Field Type

Store pre-computed embeddings using the `vector` field type via the **Management client**:

```python
# Using ManagementClient (not FluxClient — schema changes are admin operations)
management_client.create_folder_field(
    "my-folder",
    "latest",
    {
        "key": "speaker_embedding",
        "name": "Speaker Embedding",
        "type": "vector",
        "meta": {"dimensions": 256},
        "required": False,
    },
)
```

Supported dimensions: 256, 384, 768, 1024, 1536.

## Semantic Search (Auto-generated Embeddings)

Search using natural language — the platform generates embeddings automatically:

```python
from foxnose_sdk.flux import FluxClient

results = client.vector_search(
    "blog-posts",
    query="articles about machine learning in healthcare",
    top_k=10,
    similarity_threshold=0.7,
)

for item in results["results"]:
    print(item["data"]["title"])
```

## Custom Embedding Search

Search with your own pre-computed embedding vectors:

```python
results = client.vector_field_search(
    "speakers",
    field="speaker_embedding",
    query_vector=[0.012, -0.034, 0.056, ...],  # Your embedding
    top_k=20,
    similarity_threshold=0.6,
)
```

!!! warning "Dimension Mismatch"
    If `query_vector` dimensions don't match the field's configured dimensions, the API returns a `422` error.

## Hybrid Search

Combine keyword matching with semantic similarity:

```python
results = client.hybrid_search(
    "blog-posts",
    query="machine learning applications",
    find_text={"query": "ML healthcare"},
    vector_weight=0.7,
    text_weight=0.3,
    rerank_results=True,
)
```

`vector_weight` and `text_weight` must sum to 1.0.

!!! note
    Hybrid mode only supports auto-generated embeddings (`vector_search`), not custom embeddings.

## Boosted Search

Start with keyword results and boost rankings using vector similarity:

```python
results = client.boosted_search(
    "blog-posts",
    find_text={"query": "python tutorial"},
    query="beginner programming guide",
    boost_factor=1.5,
    max_boost_results=20,
)
```

Boosted search supports both auto-generated and custom embeddings:

```python
# With custom embeddings
results = client.boosted_search(
    "blog-posts",
    find_text={"query": "python tutorial"},
    field="content_embedding",
    query_vector=[0.1, 0.2, ...],
    boost_factor=2.0,
)
```

## Using SearchRequest Directly

For full control, build a `SearchRequest` model and pass it to `search()`:

```python
from foxnose_sdk.flux.models import (
    SearchMode,
    SearchRequest,
    VectorSearch,
    HybridConfig,
)

req = SearchRequest(
    search_mode=SearchMode.HYBRID,
    find_text={"query": "python"},
    vector_search=VectorSearch(query="programming tutorials", top_k=10),
    hybrid_config=HybridConfig(vector_weight=0.6, text_weight=0.4),
    limit=20,
)

results = client.search("blog-posts", body=req.model_dump(exclude_none=True))
```

Extra fields (e.g., `where`, `sort`) are forwarded to the API:

```python
req = SearchRequest(
    search_mode=SearchMode.VECTOR,
    vector_search=VectorSearch(query="hello"),
    where={"category": "news"},
    sort="-published_at",
)
```

## Passing Extra Parameters

All convenience methods accept `**extra_body` for additional API parameters:

```python
results = client.vector_search(
    "articles",
    query="climate change",
    limit=10,
    where={"category": "science"},
    sort="-published_at",
)
```

## Async Usage

All methods are available on `AsyncFluxClient`:

```python
from foxnose_sdk.flux import AsyncFluxClient

async def search():
    client = AsyncFluxClient(
        base_url="https://env.fxns.io",
        api_prefix="v1",
        auth=auth,
    )

    results = await client.vector_search(
        "blog-posts",
        query="machine learning",
    )
    await client.aclose()
```

## Configuration Reference

### VectorSearch

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | required | Natural language search query |
| `fields` | `list[str]` | `None` | Fields to search (all vectorizable if omitted) |
| `top_k` | `int` | `10` | Max candidates for vector matching |
| `similarity_threshold` | `float` | `None` | Min cosine similarity (0.0-1.0) |

### VectorFieldSearch

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `field` | `str` | required | Vector field key to search |
| `query_vector` | `list[float]` | required | Pre-computed embedding vector |
| `top_k` | `int` | `10` | Max candidates for vector matching |
| `similarity_threshold` | `float` | `None` | Min cosine similarity (0.0-1.0) |

### VectorBoostConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `boost_factor` | `float` | `1.5` | Boost multiplier for vector-similar results |
| `similarity_threshold` | `float` | `None` | Min similarity to apply boost (0.0-1.0) |
| `max_boost_results` | `int` | `20` | Max results to apply boost to |

### HybridConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `vector_weight` | `float` | `0.6` | Weight for vector score (0.0-1.0) |
| `text_weight` | `float` | `0.4` | Weight for text score (0.0-1.0) |
| `rerank_results` | `bool` | `True` | Re-rank blended results |

## Error Handling

```python
from foxnose_sdk.errors import FoxnoseAPIError

try:
    results = client.vector_field_search(
        "speakers",
        field="embedding",
        query_vector=[0.1, 0.2],  # Wrong dimensions
    )
except FoxnoseAPIError as e:
    if e.status_code == 422:
        print("Dimension mismatch — check your vector dimensions")
    else:
        print(f"Error: {e.message}")
```
