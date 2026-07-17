# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.0] - 2026-07-16

### Added

- **Typed billing exceptions** in `foxnose_sdk.errors`, all subclasses of `FoxnoseAPIError`:
  - `SpendCapExceeded` (HTTP 402 `spend_cap_reached`) — attrs `cap_usd`, `cycle_resets_at`, `raise_cap_url`
  - `PlanExhausted` (HTTP 402 `plan_exhausted`) — attrs `axis`, `window_resets_at`, `upgrade_url`
  - `PlanLimitExceeded` (HTTP 403 `plan_limit_exceeded`) — attrs `entity`, `limit`, `current`, `upgrade_url`
  - `RateLimitExceeded` (HTTP 429 `rate_limited`) — attr `retry_after` (from the `Retry-After` header)
- All four are exported from the package root and caught by `except FoxnoseAPIError`.
- **Components on Collections** — `NestedFieldMeta` helper for building nested-field `meta` (`component`, `component_version`, `auto_update`), and `sync_collection_component()` on `ManagementClient` / `AsyncManagementClient` to advance pinned nested fields to a target Component version. New models `SyncComponentResponse`, `SyncComponentSkippedItem`, and `ComponentSyncConflictDetail`.

### Changed

- **Renamed Folder → Collection across the Management API surface.** New `*_collection*` methods (`list_collections`, `create_collection`, `list_collection_versions`, `list_collection_fields`, etc.) and models (`CollectionSummary`, `CollectionList`, `APICollectionSummary`, `APICollectionList`) are the preferred names. The old `*_folder*` methods and `FolderSummary` / `FolderList` remain as deprecated aliases that emit a one-shot `DeprecationWarning` on first use and will be removed in 1.0.

### Removed

- Composite folder support.

### Fixed

- `RolePermission.all_objects` is now optional (`bool | None`), so permissions for non-object-based content types — which the API returns with `all_objects: null` — parse without error.
- Corrected the `roles_and_permissions` example and the docs to the real permission wire-shape (`content_type` + `actions` list, with `all_objects` only on object-based content types), the renamed content-type keys (`collection-structure` / `collection-items` in place of `folder-*`), and the real API-key create shape (`description` + a single `role`).

## [0.5.0] - 2026-03-19

### Added

- **Vector search models** in `foxnose_sdk.flux.models`:
  - `SearchMode` enum (`text`, `vector`, `vector_boosted`, `hybrid`)
  - `VectorSearch` — auto-generated embedding search configuration
  - `VectorFieldSearch` — custom pre-computed embedding search configuration
  - `VectorBoostConfig` — boost configuration for `vector_boosted` mode
  - `HybridConfig` — weight configuration for `hybrid` mode
  - `SearchRequest` — typed search payload with cross-field validation
- **Convenience methods** on `FluxClient` and `AsyncFluxClient`:
  - `vector_search()` — semantic search with auto-generated embeddings
  - `vector_field_search()` — search with custom embedding vectors
  - `hybrid_search()` — blended text + vector search
  - `boosted_search()` — keyword search boosted by vector similarity
- **Vector Search documentation** — dedicated guide covering all search modes
- All convenience methods support `offset` and `**extra_body` pass-through for additional API parameters (`where`, `sort`, etc.)

### Fixed

- `examples/flux_client.py` search example now uses correct API keys (`find_text` and `results`)

## [0.4.2] - 2026-03-10

### Fixed

- **Secure Management/Flux signing with query parameters**:
  - `SecureKeyAuth` now signs only the URL path (without query string)
  - aligns SDK signatures with server-side verification and Management auth docs
  - prevents `401 authentication_failed` / `Invalid signature` on requests with query params

## [0.4.1] - 2026-03-05

### Fixed

- **Flux role permission objects handling** in Management clients:
  - normalize permission object list responses consistently
  - keep compatibility with paginated/object payload variants
  - align role-scoped flux permission object behavior with production contract

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
- **`batch_upsert_resources()`** method on `ManagementClient` and `AsyncManagementClient` — upsert multiple resources concurrently with configurable `max_concurrency`, `fail_fast` error handling mode, and optional `on_progress` callback.
- **`BatchUpsertItem`**, **`BatchItemError`**, **`BatchUpsertResult`** models for batch upsert input/output.
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

[Unreleased]: https://github.com/FoxNoseTech/foxnose-python/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/FoxNoseTech/foxnose-python/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/FoxNoseTech/foxnose-python/compare/v0.4.2...v0.5.0
[0.4.2]: https://github.com/FoxNoseTech/foxnose-python/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/FoxNoseTech/foxnose-python/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/FoxNoseTech/foxnose-python/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/FoxNoseTech/foxnose-python/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/FoxNoseTech/foxnose-python/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/FoxNoseTech/foxnose-python/releases/tag/v0.1.0
