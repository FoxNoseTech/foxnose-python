# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-02-25

### Added

- **Flux introspection methods** on sync and async clients:
  - `get_router()` calls `GET /{api_prefix}/_router`
  - `get_schema(folder_path)` calls `GET /{api_prefix}/{folder_path}/_schema`
- **API folder route description support** in Management clients:
  - `add_api_folder()` and `update_api_folder()` now accept:
    - `description_get_one`
    - `description_get_many`
    - `description_search`
    - `description_schema`
- **`APIFolderSummary` model fields** for route descriptions:
  - `description_get_one`
  - `description_get_many`
  - `description_search`
  - `description_schema`

## [0.3.0] - 2026-02-10

### Added

- **`upsert_resource()`** method on `ManagementClient` and `AsyncManagementClient` — create or update a resource by `external_id` in a single call. Uses `PUT /folders/:folder/resources/?external_id=<value>`.
- **`external_id`** optional parameter on `create_resource()` — assign an external identifier when creating a resource via `POST`.
- **`external_id`** field on `ResourceSummary` model — populated in API responses for resources that have an external identifier.

## [0.2.0] - 2026-01-26

### Added

- **Model objects as identifiers** — Management client methods now accept either string keys or corresponding model objects (e.g. `FolderSummary`, `ResourceSummary`) wherever a `*_key` parameter is used. This eliminates the need to manually extract `.key` from objects returned by the API.
- `_resolve_key()` helper function for extracting string keys from model objects.
- 13 type aliases for method parameters: `FolderRef`, `ResourceRef`, `RevisionRef`, `ComponentRef`, `SchemaVersionRef`, `OrgRef`, `ProjectRef`, `EnvironmentRef`, `ManagementRoleRef`, `FluxRoleRef`, `ManagementAPIKeyRef`, `FluxAPIKeyRef`, `APIRef`.

## [0.1.0] - 2026-01-14

### Added

- Initial release of the FoxNose Python SDK
- `ManagementClient` for administrative operations
- `AsyncManagementClient` for async administrative operations
- `FluxClient` for content delivery
- `AsyncFluxClient` for async content delivery
- JWT authentication with automatic token refresh
- API key authentication for Flux API
- Comprehensive type hints and Pydantic models
- Automatic retry with exponential backoff
- Full support for all Management API endpoints:
    - Organizations
    - Projects
    - Environments
    - Folders
    - Resources
    - Revisions
    - Schema versions and fields
    - Components
    - Locales
    - Management roles and permissions
    - Flux roles and permissions
    - Management API keys
    - Flux API keys

### Documentation

- Getting started guide
- Authentication guide
- Management Client reference
- Flux Client reference
- Error handling guide
- Code examples

[0.4.0]: https://github.com/foxnose/python-sdk/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/foxnose/python-sdk/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/foxnose/python-sdk/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/foxnose/python-sdk/releases/tag/v0.1.0
