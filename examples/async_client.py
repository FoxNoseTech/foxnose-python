"""Async client usage example for the FoxNose Python SDK.

This example demonstrates how to:
- Use the AsyncManagementClient for non-blocking operations
- Perform concurrent API calls
- Work with async context managers
"""

import asyncio

from foxnose_sdk.auth import JWTAuth
from foxnose_sdk.errors import FoxnoseAPIError
from foxnose_sdk.management import AsyncManagementClient


async def fetch_folder_details(client: AsyncManagementClient, folder_key: str):
    """Fetch folder details and its resources concurrently."""
    # Run both requests concurrently
    folder, resources = await asyncio.gather(
        client.get_folder(folder_key),
        client.list_resources(folder_key),
    )
    return folder, resources


async def main():
    auth = JWTAuth.from_static_token("YOUR_ACCESS_TOKEN")

    client = AsyncManagementClient(
        base_url="https://api.foxnose.net",
        environment_key="your-environment-key",
        auth=auth,
    )

    try:
        # List folders
        folders = await client.list_folders()
        print(f"Found {len(folders.results)} folders")

        # Fetch details for multiple folders concurrently
        if folders.results:
            tasks = [
                fetch_folder_details(client, folder.key)
                for folder in folders.results[:3]  # Limit to first 3
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for folder_data in results:
                if isinstance(folder_data, Exception):
                    print(f"Error: {folder_data}")
                else:
                    folder, resources = folder_data
                    print(f"\n{folder.name}: {len(resources.results)} resources")

    except FoxnoseAPIError as e:
        print(f"API Error: {e.message}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
