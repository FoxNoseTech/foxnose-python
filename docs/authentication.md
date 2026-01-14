# Authentication

The FoxNose SDK supports multiple authentication methods depending on your use case.

## JWT Authentication

JWT (JSON Web Token) authentication is used for the Management API. It provides secure access with support for token refresh.

### Static Token

For simple scripts or testing, use a static access token:

```python
from foxnose_sdk.auth import JWTAuth

auth = JWTAuth.from_static_token("YOUR_ACCESS_TOKEN")
```

!!! warning "Token Expiration"
    Static tokens will expire. For long-running applications, use refresh token support.

### With Refresh Token

For applications that run for extended periods:

```python
from foxnose_sdk.auth import JWTAuth

auth = JWTAuth(
    access_token="YOUR_ACCESS_TOKEN",
    refresh_token="YOUR_REFRESH_TOKEN",
)
```

The SDK will automatically refresh the access token when it expires.

### Custom Token Provider

For advanced scenarios, implement a custom token provider:

```python
from foxnose_sdk.auth import AuthStrategy

class CustomAuth(AuthStrategy):
    def get_headers(self) -> dict[str, str]:
        token = self._fetch_token_from_vault()
        return {"Authorization": f"Bearer {token}"}

    async def aget_headers(self) -> dict[str, str]:
        token = await self._async_fetch_token()
        return {"Authorization": f"Bearer {token}"}
```

## API Key Authentication

API key authentication is used for the Flux API. It's suitable for public-facing applications.

### Simple Key (Development)

For development and testing:

```python
from foxnose_sdk.auth import SimpleKeyAuth

auth = SimpleKeyAuth(
    public_key="YOUR_PUBLIC_KEY",
    secret_key="YOUR_SECRET_KEY",
)
```

### Secure Key (Production)

For production use with cryptographic signatures:

```python
from foxnose_sdk.auth import SecureKeyAuth

auth = SecureKeyAuth(
    public_key="YOUR_PUBLIC_KEY",
    private_key="YOUR_PRIVATE_KEY",
)
```

API keys are typically prefixed and can be safely exposed in frontend applications (with appropriate CORS configuration).

### Creating API Keys

You can create API keys programmatically:

```python
from foxnose_sdk.management import ManagementClient
from foxnose_sdk.auth import JWTAuth

client = ManagementClient(
    base_url="https://api.foxnose.net",
    environment_key="your-environment-key",
    auth=JWTAuth.from_static_token("YOUR_ACCESS_TOKEN"),
)

# Create a Flux API key
flux_key = client.create_flux_api_key({
    "name": "Frontend Key",
    "roles": ["reader-role-key"],
})

print(f"Key created: {flux_key.key}")
# The actual secret is only shown once upon creation
```

## Using with Clients

Pass the auth strategy when creating a client:

=== "Management Client"

    ```python
    from foxnose_sdk.management import ManagementClient
    from foxnose_sdk.auth import JWTAuth

    client = ManagementClient(
        base_url="https://api.foxnose.net",
        environment_key="your-environment-key",
        auth=JWTAuth.from_static_token("YOUR_TOKEN"),
    )
    ```

=== "Flux Client"

    ```python
    from foxnose_sdk.flux import FluxClient
    from foxnose_sdk.auth import SimpleKeyAuth

    client = FluxClient(
        base_url="https://<env_key>.fxns.io",
        api_prefix="v1",
        auth=SimpleKeyAuth("YOUR_PUBLIC_KEY", "YOUR_SECRET_KEY"),
    )
    ```

## Environment Variables

For security, store credentials in environment variables:

```python
import os
from foxnose_sdk.auth import JWTAuth

auth = JWTAuth.from_static_token(os.environ["FOXNOSE_ACCESS_TOKEN"])
```

Or use a `.env` file with `python-dotenv`:

```python
from dotenv import load_dotenv
import os

load_dotenv()

auth = JWTAuth.from_static_token(os.environ["FOXNOSE_ACCESS_TOKEN"])
```

## Security Best Practices

1. **Never commit tokens** - Use environment variables or secret management
2. **Rotate tokens regularly** - Especially for production environments
3. **Use least privilege** - Assign only necessary permissions to API keys
4. **Monitor usage** - Check API key usage in the FoxNose dashboard
