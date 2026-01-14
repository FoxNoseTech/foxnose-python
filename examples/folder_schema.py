"""Working with folder schemas and fields.

This example demonstrates how to:
- Create folder schema versions
- Add and update fields
- Publish schema versions
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

    try:
        # Create a new collection folder
        folder = client.create_folder(
            {
                "name": "Blog Posts",
                "alias": "blog-posts",
                "folder_type": "collection",
                "content_type": "document",
            }
        )
        print(f"Created folder: {folder.key}")

        # Create a schema version for the folder
        version = client.create_folder_version(
            folder.key,
            {"name": "v1.0"},
        )
        print(f"Created schema version: {version.key}")

        # Add fields to the schema
        fields = [
            {
                "name": "title",
                "alias": "title",
                "field_type": "text",
                "required": True,
            },
            {
                "name": "slug",
                "alias": "slug",
                "field_type": "text",
                "required": True,
            },
            {
                "name": "content",
                "alias": "content",
                "field_type": "richtext",
                "required": False,
            },
            {
                "name": "published_at",
                "alias": "published_at",
                "field_type": "datetime",
                "required": False,
            },
        ]

        for field_data in fields:
            field = client.create_folder_field(folder.key, version.key, field_data)
            print(f"  Added field: {field.name} ({field.field_type})")

        # List all fields in the schema
        all_fields = client.list_folder_fields(folder.key, version.key)
        print(f"\nSchema has {len(all_fields.results)} fields")

        # Update a field
        client.update_folder_field(
            folder.key,
            version.key,
            "title",
            {
                "name": "title",
                "alias": "title",
                "field_type": "text",
                "required": True,
                "description": "The title of the blog post",
            },
        )
        print("Updated 'title' field with description")

        # Publish the schema version
        published = client.publish_folder_version(folder.key, version.key)
        print(f"\nPublished schema version: {published.key}")
        print(f"Status: {published.status}")

    except FoxnoseAPIError as e:
        print(f"API Error: {e.message}")
        if e.details:
            print(f"Details: {e.details}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
