# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/foxnose/python-sdk/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/foxnose/python-sdk/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/foxnose/python-sdk/releases/tag/v0.1.0
