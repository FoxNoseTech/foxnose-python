"""Working with resources and revisions.

This example demonstrates how to:
- Create resources in a folder
- Create and publish revisions
- Fetch resource data
"""

from foxnose_sdk.auth import JWTAuth
from foxnose_sdk.errors import FoxnoseAPIError
from foxnose_sdk.management import ManagementClient


def main():
    auth = JWTAuth.from_static_token("YOUR_ACCESS_TOKEN")

    client = ManagementClient(
        base_url="https://api.foxnose.net",
        environment_key="your-environment-key",
        auth=auth,
    )

    folder_key = "your-folder-key"

    try:
        # Create a new resource
        # The payload structure depends on your folder's schema
        resource = client.create_resource(
            folder_key,
            {
                "title": "My New Article",
                "slug": "my-new-article",
                "content": {
                    "body": "This is the article content.",
                    "author": "John Doe",
                },
            },
        )
        print(f"Created resource: {resource.key}")

        # List all revisions for the resource
        revisions = client.list_revisions(folder_key, resource.key)
        print(f"Resource has {len(revisions.results)} revision(s)")

        # Get the latest revision
        if revisions.results:
            latest = revisions.results[0]
            print(f"Latest revision: {latest.key} (status: {latest.status})")

            # Validate before publishing
            validation = client.validate_revision(folder_key, resource.key, latest.key)
            if not validation.get("errors"):
                # Publish the revision
                published = client.publish_revision(
                    folder_key,
                    resource.key,
                    latest.key,
                )
                print(f"Published revision: {published.key}")

                # Fetch the published data
                data = client.get_resource_data(folder_key, resource.key)
                print(f"Published data: {data}")
            else:
                print(f"Validation errors: {validation['errors']}")

        # Create a new revision with updated content
        new_revision = client.create_revision(
            folder_key,
            resource.key,
            {
                "title": "My New Article (Updated)",
                "slug": "my-new-article",
                "content": {
                    "body": "This is the updated article content.",
                    "author": "John Doe",
                },
            },
        )
        print(f"Created new revision: {new_revision.key}")

    except FoxnoseAPIError as e:
        print(f"API Error: {e.message}")
        if e.details:
            print(f"Details: {e.details}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
