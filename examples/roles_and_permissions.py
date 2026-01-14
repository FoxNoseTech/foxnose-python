"""Working with roles and permissions.

This example demonstrates how to:
- Create and manage Management API roles
- Create and manage Flux API roles
- Assign permissions to roles
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
        # ======================
        # Management API Roles
        # ======================

        # Create a Management API role for content editors
        mgmt_role = client.create_management_role(
            {
                "name": "Content Editor",
                "description": "Can manage content but not settings",
                "full_access": False,
            }
        )
        print(f"Created Management role: {mgmt_role.key}")

        # Add permissions to the role
        # Allow read/write access to documents
        client.upsert_management_role_permission(
            mgmt_role.key,
            {
                "content_type": "document",
                "can_read": True,
                "can_create": True,
                "can_update": True,
                "can_delete": False,  # Cannot delete
            },
        )
        print("  Added document permissions")

        # Allow read-only access to folders
        client.upsert_management_role_permission(
            mgmt_role.key,
            {
                "content_type": "folder",
                "can_read": True,
                "can_create": False,
                "can_update": False,
                "can_delete": False,
            },
        )
        print("  Added folder permissions (read-only)")

        # List all permissions for the role
        permissions = client.list_management_role_permissions(mgmt_role.key)
        print(f"\nRole has {len(permissions)} permission(s)")

        # ======================
        # Flux API Roles
        # ======================

        # Create a Flux API role for frontend access
        flux_role = client.create_flux_role(
            {
                "name": "Frontend Reader",
                "description": "Read-only access for frontend applications",
            }
        )
        print(f"\nCreated Flux role: {flux_role.key}")

        # Add permissions - Flux roles typically have read-only access
        client.upsert_flux_role_permission(
            flux_role.key,
            {
                "content_type": "document",
                "can_read": True,
                "can_create": False,
                "can_update": False,
                "can_delete": False,
            },
        )
        print("  Added document read permission")

        # ======================
        # API Keys
        # ======================

        # Create a Management API key with the role
        mgmt_key = client.create_management_api_key(
            {
                "name": "Editor API Key",
                "roles": [mgmt_role.key],
            }
        )
        print(f"\nCreated Management API key: {mgmt_key.key}")
        # Note: The actual secret is only shown once upon creation

        # Create a Flux API key for frontend
        flux_key = client.create_flux_api_key(
            {
                "name": "Frontend API Key",
                "roles": [flux_role.key],
            }
        )
        print(f"Created Flux API key: {flux_key.key}")

        # ======================
        # Cleanup
        # ======================

        # List all Management roles
        all_roles = client.list_management_roles()
        print(f"\nTotal Management roles: {len(all_roles.results)}")

        # List all Flux roles
        all_flux_roles = client.list_flux_roles()
        print(f"Total Flux roles: {len(all_flux_roles.results)}")

    except FoxnoseAPIError as e:
        print(f"API Error: {e.message}")
        if e.details:
            print(f"Details: {e.details}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
