"""Using the Flux Client for content delivery.

The Flux API is optimized for content delivery with:
- Read-only access to published content
- Fast response times
- Search capabilities

This example demonstrates how to:
- Initialize the FluxClient
- Fetch published resources
- Search for content
"""

from foxnose_sdk.auth import SimpleKeyAuth
from foxnose_sdk.errors import FoxnoseAPIError
from foxnose_sdk.flux import FluxClient


def main():
    # Flux API uses key-based authentication
    auth = SimpleKeyAuth("YOUR_PUBLIC_KEY", "YOUR_SECRET_KEY")

    client = FluxClient(
        base_url="https://your-env-key.fxns.io",  # Replace with your env key
        api_prefix="v1",
        auth=auth,
    )

    folder_path = "blog-posts"

    try:
        # List published resources in a folder
        resources = client.list_resources(
            folder_path,
            params={
                "limit": 10,
                "offset": 0,
            },
        )
        print(f"Found {resources.get('count', 0)} published resources")

        for resource in resources.get("results", []):
            print(f"  - {resource['key']}")

        # Get a specific resource by key
        results = resources.get("results", [])
        if results:
            resource_key = results[0]["key"]
            resource = client.get_resource(folder_path, resource_key)
            print(f"\nResource data: {resource}")

        # Search for content
        search_results = client.search(
            folder_path,
            body={
                "query": "python",
                "limit": 5,
            },
        )
        print(f"\nSearch results: {len(search_results.get('hits', []))} hits")

    except FoxnoseAPIError as e:
        if e.status_code == 404:
            print("Resource not found or not published")
        else:
            print(f"API Error: {e.message}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
