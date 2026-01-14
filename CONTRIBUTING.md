# Contributing to FoxNose Python SDK

Thank you for your interest in contributing to the FoxNose Python SDK! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributors of all backgrounds and experience levels.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git

### Development Setup

1. Clone the repository:

```bash
git clone https://github.com/FoxNoseTech/foxnose-python.git
cd foxnose-python
```

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package with development dependencies:

```bash
pip install -e ".[test]"
```

4. Install linting tools:

```bash
pip install ruff
```

## Development Workflow

### Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting. Before submitting a pull request, ensure your code passes all checks:

```bash
# Check for linting issues
ruff check .

# Format code
ruff format .
```

### Type Hints

All public APIs should include type hints. We use Python's built-in `typing` module and Pydantic for model definitions.

### Docstrings

All public methods and classes should have docstrings following Google style:

```python
def get_resource(self, folder_key: str, resource_key: str) -> ResourceSummary:
    """Retrieve metadata for a specific resource.

    Args:
        folder_key: Unique identifier of the folder.
        resource_key: Unique identifier of the resource.

    Returns:
        Resource metadata including key, name, and timestamps.

    Raises:
        FoxNoseAPIError: If the resource is not found or access is denied.
    """
```

### Running Tests

Run the test suite to ensure your changes don't break existing functionality:

```bash
pytest
```

For verbose output:

```bash
pytest -v
```

To run a specific test file:

```bash
pytest tests/management/test_folders.py
```

## Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/add-webhook-support`
- `fix/retry-on-timeout`
- `docs/update-readme`

### Commit Messages

Write clear, concise commit messages:

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters
- Reference issues and pull requests when relevant

Example:
```
Add retry logic for transient network errors

- Implement exponential backoff with jitter
- Add configurable retry count and delay
- Handle connection timeout and 5xx errors

Fixes #123
```

### Pull Requests

1. Create a new branch from `main`
2. Make your changes
3. Run tests and linting
4. Push your branch and create a pull request
5. Fill out the PR template with:
   - Description of changes
   - Related issues
   - Testing performed

## Project Structure

```
foxnose-python/
├── src/
│   └── foxnose_sdk/
│       ├── __init__.py
│       ├── auth.py           # Authentication strategies
│       ├── config.py         # Configuration classes
│       ├── errors.py         # Exception definitions
│       ├── http.py           # HTTP transport layer
│       ├── management/       # Management API client
│       │   ├── __init__.py
│       │   ├── client.py     # ManagementClient, AsyncManagementClient
│       │   └── models.py     # Pydantic models
│       └── flux/             # Flux API client
│           ├── __init__.py
│           ├── client.py     # FluxClient, AsyncFluxClient
│           └── models.py     # Pydantic models
├── tests/                    # Test suite
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

## Adding New Features

When adding new API methods:

1. Add the method to the sync client (`ManagementClient` or `FluxClient`)
2. Add the corresponding async method to the async client
3. Add appropriate Pydantic models if needed
4. Write tests covering the new functionality
5. Add docstrings with Args, Returns, and Raises sections
6. Update documentation if applicable

## Reporting Issues

When reporting bugs, please include:

- Python version
- SDK version
- Operating system
- Minimal code example to reproduce
- Full error traceback

## Questions?

If you have questions about contributing, feel free to open an issue with the "question" label.

## License

By contributing to this project, you agree that your contributions will be licensed under the Apache License 2.0.
