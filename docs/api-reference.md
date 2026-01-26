# API Reference

Complete API reference for the FoxNose Python SDK.

## Management Client

::: foxnose_sdk.management.ManagementClient
    options:
      show_source: false
      heading_level: 3
      members_order: source

## Async Management Client

::: foxnose_sdk.management.AsyncManagementClient
    options:
      show_source: false
      heading_level: 3
      members_order: source

## Flux Client

::: foxnose_sdk.flux.FluxClient
    options:
      show_source: false
      heading_level: 3
      members_order: source

## Async Flux Client

::: foxnose_sdk.flux.AsyncFluxClient
    options:
      show_source: false
      heading_level: 3
      members_order: source

## Authentication

### JWTAuth

::: foxnose_sdk.auth.JWTAuth
    options:
      show_source: false
      heading_level: 4

### SimpleKeyAuth

::: foxnose_sdk.auth.SimpleKeyAuth
    options:
      show_source: false
      heading_level: 4

### SecureKeyAuth

::: foxnose_sdk.auth.SecureKeyAuth
    options:
      show_source: false
      heading_level: 4

### AuthStrategy

::: foxnose_sdk.auth.AuthStrategy
    options:
      show_source: false
      heading_level: 4

## Reference Type Aliases

The following type aliases are used in method signatures and can be imported for your own type annotations. Each accepts either a string key or the corresponding model object.

| Type alias | Definition |
|------------|------------|
| `FolderRef` | `Union[str, FolderSummary]` |
| `ResourceRef` | `Union[str, ResourceSummary]` |
| `RevisionRef` | `Union[str, RevisionSummary]` |
| `ComponentRef` | `Union[str, ComponentSummary]` |
| `SchemaVersionRef` | `Union[str, SchemaVersionSummary]` |
| `OrgRef` | `Union[str, OrganizationSummary]` |
| `ProjectRef` | `Union[str, ProjectSummary]` |
| `EnvironmentRef` | `Union[str, EnvironmentSummary]` |
| `ManagementRoleRef` | `Union[str, ManagementRoleSummary]` |
| `FluxRoleRef` | `Union[str, FluxRoleSummary]` |
| `ManagementAPIKeyRef` | `Union[str, ManagementAPIKeySummary]` |
| `FluxAPIKeyRef` | `Union[str, FluxAPIKeySummary]` |
| `APIRef` | `Union[str, APIInfo]` |

```python
from foxnose_sdk import FolderRef, ResourceRef, RevisionRef
```

## Errors

::: foxnose_sdk.errors.FoxnoseAPIError
    options:
      show_source: false
      heading_level: 3

## Models

### Pagination

::: foxnose_sdk.management.models.PaginatedResponse
    options:
      show_source: false
      heading_level: 4
      members: false

### Folder Models

::: foxnose_sdk.management.models.FolderSummary
    options:
      show_source: false
      heading_level: 4
      members: false

### Resource Models

::: foxnose_sdk.management.models.ResourceSummary
    options:
      show_source: false
      heading_level: 4
      members: false

### Revision Models

::: foxnose_sdk.management.models.RevisionSummary
    options:
      show_source: false
      heading_level: 4
      members: false

### Component Models

::: foxnose_sdk.management.models.ComponentSummary
    options:
      show_source: false
      heading_level: 4
      members: false

### Schema Models

::: foxnose_sdk.management.models.SchemaVersionSummary
    options:
      show_source: false
      heading_level: 4
      members: false

::: foxnose_sdk.management.models.FieldSummary
    options:
      show_source: false
      heading_level: 4
      members: false

### Organization Models

::: foxnose_sdk.management.models.OrganizationSummary
    options:
      show_source: false
      heading_level: 4
      members: false

::: foxnose_sdk.management.models.OrganizationUsage
    options:
      show_source: false
      heading_level: 4
      members: false

### Project Models

::: foxnose_sdk.management.models.ProjectSummary
    options:
      show_source: false
      heading_level: 4
      members: false

### Environment Models

::: foxnose_sdk.management.models.EnvironmentSummary
    options:
      show_source: false
      heading_level: 4
      members: false

::: foxnose_sdk.management.models.LocaleSummary
    options:
      show_source: false
      heading_level: 4
      members: false

### Role Models

::: foxnose_sdk.management.models.ManagementRoleSummary
    options:
      show_source: false
      heading_level: 4
      members: false

::: foxnose_sdk.management.models.FluxRoleSummary
    options:
      show_source: false
      heading_level: 4
      members: false

::: foxnose_sdk.management.models.RolePermission
    options:
      show_source: false
      heading_level: 4
      members: false

### API Key Models

::: foxnose_sdk.management.models.ManagementAPIKeySummary
    options:
      show_source: false
      heading_level: 4
      members: false

::: foxnose_sdk.management.models.FluxAPIKeySummary
    options:
      show_source: false
      heading_level: 4
      members: false

### API Models

::: foxnose_sdk.management.models.APIInfo
    options:
      show_source: false
      heading_level: 4
      members: false

::: foxnose_sdk.management.models.APIFolderSummary
    options:
      show_source: false
      heading_level: 4
      members: false
