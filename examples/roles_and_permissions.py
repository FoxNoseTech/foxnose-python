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

        # Create a Management API role with read-only access
        mgmt_role = client.create_management_role(
            {
                "name": "Collection Reader",
                "description": "Read-only access to collection structure and items",
                "full_access": False,
            }
        )
        print(f"Created Management role: {mgmt_role.key}")

        # Grant read-only access to the collection structure
        client.upsert_management_role_permission(
            mgmt_role.key,
            {
                "content_type": "collection-structure",
                "actions": ["read"],
            },
        )
        print("  Added collection-structure permission (read-only)")

        # Grant read-only access to items across all collections
        client.upsert_management_role_permission(
            mgmt_role.key,
            {
                "content_type": "collection-items",
                "actions": ["read"],
                "all_objects": True,
            },
        )
        print("  Added collection-items permission (read-only, all collections)")

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

        # Add permissions - Flux roles have read-only access.
        # all_objects=True grants read access to every Flux API in the environment.
        client.upsert_flux_role_permission(
            flux_role.key,
            {
                "content_type": "flux-apis",
                "actions": ["read"],
                "all_objects": True,
            },
        )
        print("  Added flux-apis read permission (all APIs)")

        # ======================
        # API Keys
        # ======================

        # Create a Management API key with the role
        mgmt_key = client.create_management_api_key(
            {
                "description": "Reader API key",
                "role": mgmt_role.key,
            }
        )
        print(f"\nCreated Management API key: {mgmt_key.public_key}")
        # Note: the secret key (mgmt_key.secret_key) is only returned once here

        # Create a Flux API key for frontend
        flux_key = client.create_flux_api_key(
            {
                "description": "Frontend API key",
                "role": flux_role.key,
            }
        )
        print(f"Created Flux API key: {flux_key.public_key}")

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
        if e.detail:
            print(f"Details: {e.detail}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
