"""Using the Flux Client for content delivery.

The Flux API is optimized for content delivery with:
- Fast reads of published content
- Search capabilities
- Writes (create / replace resources) with a write-capable key

This example demonstrates how to:
- Initialize the FluxClient
- Fetch published resources
- Search for content
- Create and update resources
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
                "find_text": {"query": "python"},
                "limit": 5,
            },
        )
        print(f"\nSearch results: {len(search_results.get('results', []))} results")

        # Create a resource (requires a write-capable key). `key` is an optional
        # external identifier used to deduplicate — reusing it raises a conflict.
        created = client.create_resource(
            folder_path,
            {"title": "Hello from the SDK", "body": "..."},
            key="example-external-id",
        )
        print(f"\nCreated resource: {created['resource_key']}")

        # Replace the resource's document (full replace, not a merge).
        client.update_resource(
            folder_path,
            created["resource_key"],
            {"title": "Hello (edited)", "body": "..."},
        )

    except FoxnoseAPIError as e:
        if e.status_code == 404:
            print("Resource not found or not published")
        else:
            print(f"API Error: {e.message}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
