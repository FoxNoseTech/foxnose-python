"""Basic usage example for the FoxNose Python SDK.

This example demonstrates how to:
- Initialize the ManagementClient with authentication
- List and retrieve folders
- Handle errors
"""

from foxnose_sdk.auth import JWTAuth
from foxnose_sdk.errors import FoxnoseAPIError
from foxnose_sdk.management import ManagementClient


def main():
    # Initialize the client with JWT authentication
    # You can obtain tokens from the FoxNose dashboard or via OAuth flow
    auth = JWTAuth.from_static_token("YOUR_ACCESS_TOKEN")

    client = ManagementClient(
        base_url="https://api.foxnose.net",
        environment_key="your-environment-key",
        auth=auth,
    )

    try:
        # List all folders in the environment
        folders = client.list_folders()
        print(f"Found {len(folders.results)} folders:")

        for folder in folders.results:
            print(f"  - {folder.name} (key: {folder.key}, type: {folder.folder_type})")

        # Get a specific folder by key
        if folders.results:
            folder_key = folders.results[0].key
            folder = client.get_folder(folder_key)
            print(f"\nFolder details: {folder.name}")
            print(f"  Alias: {folder.alias}")
            print(f"  Content type: {folder.content_type}")

    except FoxnoseAPIError as e:
        print(f"API Error: {e.message}")
        print(f"Status code: {e.status_code}")
    finally:
        # Always close the client to release resources
        client.close()


if __name__ == "__main__":
    main()
