"""Vector search examples for the Flux Client.

Demonstrates all four search modes:
- Semantic search (auto-generated embeddings)
- Custom embedding search
- Hybrid text + vector search
- Boosted search with vector similarity

See the Vector Search guide for full documentation:
https://foxnose-python.readthedocs.io/en/latest/vector-search/
"""

from foxnose_sdk.auth import SimpleKeyAuth
from foxnose_sdk.errors import FoxnoseAPIError
from foxnose_sdk.flux import FluxClient


def main():
    auth = SimpleKeyAuth("YOUR_PUBLIC_KEY", "YOUR_SECRET_KEY")

    client = FluxClient(
        base_url="https://your-env-key.fxns.io",
        api_prefix="v1",
        auth=auth,
    )

    folder_path = "blog-posts"

    try:
        # 1. Semantic search — platform generates embeddings automatically
        print("=== Semantic Search ===")
        results = client.vector_search(
            folder_path,
            query="articles about machine learning in healthcare",
            top_k=10,
            similarity_threshold=0.7,
        )
        for item in results.get("results", []):
            print(f"  - {item['data']['title']}")

        # 2. Custom embedding search — bring your own vectors
        print("\n=== Custom Embedding Search ===")
        # Replace with your actual embedding vector
        embedding = [0.012, -0.034, 0.056] * 85 + [0.01]  # 256-dim example
        results = client.vector_field_search(
            folder_path,
            field="content_embedding",
            query_vector=embedding,
            top_k=5,
        )
        print(f"  Found {results.get('count', 0)} results")

        # 3. Hybrid search — blend text and vector scores
        print("\n=== Hybrid Search ===")
        results = client.hybrid_search(
            folder_path,
            query="machine learning applications",
            find_text={"query": "ML healthcare"},
            vector_weight=0.7,
            text_weight=0.3,
            rerank_results=True,
            limit=10,
        )
        for item in results.get("results", []):
            print(f"  - {item['data']['title']}")

        # 4. Boosted search — keyword results boosted by semantic similarity
        print("\n=== Boosted Search ===")
        results = client.boosted_search(
            folder_path,
            find_text={"query": "python tutorial"},
            query="beginner programming guide",
            boost_factor=1.5,
            max_boost_results=20,
        )
        for item in results.get("results", []):
            print(f"  - {item['data']['title']}")

        # 5. Extra parameters — use where/sort with any vector search method
        print("\n=== Vector Search with Filtering ===")
        results = client.vector_search(
            folder_path,
            query="climate change",
            limit=5,
            where={"category": "science"},
            sort="-published_at",
        )
        print(f"  Found {results.get('count', 0)} results")

    except FoxnoseAPIError as e:
        if e.status_code == 422:
            print(f"Validation error (check vector dimensions): {e.message}")
        else:
            print(f"API Error: {e.message}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
