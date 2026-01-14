# Error Handling

The SDK provides structured error handling to help you manage API failures gracefully.

## Exception Types

### FoxnoseAPIError

The base exception for all API-related errors:

```python
from foxnose_sdk.errors import FoxnoseAPIError

try:
    resource = client.get_resource("folder-key", "resource-key")
except FoxnoseAPIError as e:
    print(f"Status: {e.status_code}")
    print(f"Message: {e.message}")
    print(f"Details: {e.details}")
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `status_code` | `int` | HTTP status code |
| `message` | `str` | Error message from the API |
| `details` | `dict \| None` | Additional error details (if provided) |

## Common Error Codes

### 400 Bad Request

Invalid request data or parameters:

```python
try:
    folder = client.create_folder({
        "name": "",  # Invalid: empty name
    })
except FoxnoseAPIError as e:
    if e.status_code == 400:
        print("Validation error:", e.message)
```

### 401 Unauthorized

Authentication failed or token expired:

```python
try:
    folders = client.list_folders()
except FoxnoseAPIError as e:
    if e.status_code == 401:
        print("Authentication failed - check your token")
```

### 403 Forbidden

Insufficient permissions:

```python
try:
    client.delete_folder("protected-folder")
except FoxnoseAPIError as e:
    if e.status_code == 403:
        print("Permission denied - you don't have access")
```

### 404 Not Found

Resource doesn't exist:

```python
try:
    folder = client.get_folder("non-existent")
except FoxnoseAPIError as e:
    if e.status_code == 404:
        print("Folder not found")
```

### 409 Conflict

Resource already exists or conflict with current state:

```python
try:
    folder = client.create_folder({
        "name": "Blog",
        "alias": "blog",  # Already exists
    })
except FoxnoseAPIError as e:
    if e.status_code == 409:
        print("A folder with this alias already exists")
```

### 422 Unprocessable Entity

Validation errors:

```python
try:
    revision = client.publish_revision(
        "folder-key",
        "resource-key",
        "revision-key",
    )
except FoxnoseAPIError as e:
    if e.status_code == 422:
        print("Validation failed:", e.details)
```

### 429 Too Many Requests

Rate limit exceeded:

```python
import time

try:
    for i in range(1000):
        client.list_folders()
except FoxnoseAPIError as e:
    if e.status_code == 429:
        retry_after = e.details.get("retry_after", 60)
        print(f"Rate limited. Retry after {retry_after} seconds")
        time.sleep(retry_after)
```

### 500+ Server Errors

Server-side errors:

```python
try:
    folders = client.list_folders()
except FoxnoseAPIError as e:
    if e.status_code >= 500:
        print("Server error - try again later")
```

## Error Handling Patterns

### Comprehensive Handler

```python
from foxnose_sdk.errors import FoxnoseAPIError

def handle_api_call(func, *args, **kwargs):
    """Wrapper with comprehensive error handling."""
    try:
        return func(*args, **kwargs)
    except FoxnoseAPIError as e:
        if e.status_code == 401:
            raise AuthenticationError("Token expired or invalid")
        elif e.status_code == 403:
            raise PermissionError(f"Access denied: {e.message}")
        elif e.status_code == 404:
            return None  # Resource not found
        elif e.status_code == 429:
            raise RateLimitError("Too many requests")
        elif e.status_code >= 500:
            raise ServiceUnavailableError("API is temporarily unavailable")
        else:
            raise

# Usage
folder = handle_api_call(client.get_folder, "my-folder")
if folder is None:
    print("Folder not found")
```

### Retry Pattern

```python
import time
from foxnose_sdk.errors import FoxnoseAPIError

def with_retry(func, max_retries=3, backoff=1.0):
    """Execute function with exponential backoff retry."""
    last_error = None

    for attempt in range(max_retries):
        try:
            return func()
        except FoxnoseAPIError as e:
            last_error = e

            # Don't retry client errors (except rate limiting)
            if 400 <= e.status_code < 500 and e.status_code != 429:
                raise

            # Calculate delay with exponential backoff
            delay = backoff * (2 ** attempt)
            print(f"Attempt {attempt + 1} failed, retrying in {delay}s...")
            time.sleep(delay)

    raise last_error

# Usage
folders = with_retry(client.list_folders)
```

### Async Error Handling

```python
from foxnose_sdk.errors import FoxnoseAPIError

async def fetch_resources_safely(client, folder_key):
    """Fetch resources with error handling."""
    try:
        return await client.list_resources(folder_key)
    except FoxnoseAPIError as e:
        if e.status_code == 404:
            print(f"Folder {folder_key} not found")
            return None
        raise
```

## Validation Errors

When creating or updating resources, validation errors include field-level details:

```python
try:
    resource = client.create_resource("folder-key", {
        "title": "",  # Required field is empty
        "email": "invalid-email",  # Invalid format
    })
except FoxnoseAPIError as e:
    if e.status_code in (400, 422):
        if e.details and "errors" in e.details:
            for field, messages in e.details["errors"].items():
                print(f"  {field}: {', '.join(messages)}")
```

## Network Errors

Network-level errors (timeouts, connection failures) raise standard Python exceptions:

```python
import httpx
from foxnose_sdk.errors import FoxnoseAPIError

try:
    folders = client.list_folders()
except httpx.TimeoutException:
    print("Request timed out")
except httpx.ConnectError:
    print("Could not connect to the API")
except FoxnoseAPIError as e:
    print(f"API error: {e.message}")
```

## Best Practices

1. **Be specific** - Catch specific error codes rather than catching all errors
2. **Log errors** - Always log error details for debugging
3. **Graceful degradation** - Handle 404s gracefully in user-facing applications
4. **Retry wisely** - Only retry on server errors and rate limits
5. **Show user-friendly messages** - Don't expose raw API errors to end users
