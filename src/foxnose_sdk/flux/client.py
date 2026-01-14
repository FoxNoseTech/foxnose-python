from __future__ import annotations

import httpx
from typing import Any, Mapping

from ..auth import AuthStrategy
from ..config import FoxnoseConfig, RetryConfig
from ..http import HttpTransport


def _clean_prefix(prefix: str) -> str:
    value = prefix.strip("/")
    if not value:
        raise ValueError("api_prefix cannot be empty")
    return value


def _normalize_folder_path(folder_path: str) -> str:
    return folder_path.strip("/")


class FluxClient:
    """Synchronous client for Flux delivery APIs."""

    def __init__(
        self,
        *,
        base_url: str,
        api_prefix: str,
        auth: AuthStrategy,
        timeout: float = 15.0,
        retry_config: RetryConfig | None = None,
        default_headers: Mapping[str, str] | None = None,
        verify_ssl: bool = True,
    ) -> None:
        self.api_prefix = _clean_prefix(api_prefix)
        config = FoxnoseConfig(
            base_url=base_url,
            timeout=timeout,
            default_headers=default_headers,
        )
        client = httpx.Client(base_url=base_url, timeout=timeout, verify=verify_ssl)
        self._transport = HttpTransport(
            config=config,
            auth=auth,
            retry_config=retry_config,
            sync_client=client,
        )

    def _build_path(self, folder_path: str, *, suffix: str = "") -> str:
        folder = _normalize_folder_path(folder_path)
        base = f"/{self.api_prefix}/{folder}"
        if suffix:
            return f"{base}{suffix}"
        return base

    def list_resources(
        self,
        folder_path: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        path = self._build_path(folder_path)
        return self._transport.request("GET", path, params=params)

    def get_resource(
        self,
        folder_path: str,
        resource_key: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        """Get a single resource by key."""
        path = self._build_path(folder_path, suffix=f"/{resource_key}")
        return self._transport.request("GET", path, params=params)

    def search(
        self,
        folder_path: str,
        *,
        body: Mapping[str, Any],
    ) -> Any:
        path = self._build_path(folder_path, suffix="/_search")
        return self._transport.request("POST", path, json_body=body)

    def close(self) -> None:
        self._transport.close()


class AsyncFluxClient:
    """Async variant of :class:`FluxClient`."""

    def __init__(
        self,
        *,
        base_url: str,
        api_prefix: str,
        auth: AuthStrategy,
        timeout: float = 15.0,
        retry_config: RetryConfig | None = None,
        default_headers: Mapping[str, str] | None = None,
        verify_ssl: bool = True,
    ) -> None:
        self.api_prefix = _clean_prefix(api_prefix)
        config = FoxnoseConfig(
            base_url=base_url,
            timeout=timeout,
            default_headers=default_headers,
        )
        async_client = httpx.AsyncClient(
            base_url=base_url, timeout=timeout, verify=verify_ssl
        )
        self._transport = HttpTransport(
            config=config,
            auth=auth,
            retry_config=retry_config,
            async_client=async_client,
        )

    def _build_path(self, folder_path: str, *, suffix: str = "") -> str:
        folder = _normalize_folder_path(folder_path)
        base = f"/{self.api_prefix}/{folder}"
        if suffix:
            return f"{base}{suffix}"
        return base

    async def list_resources(
        self,
        folder_path: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        path = self._build_path(folder_path)
        return await self._transport.arequest("GET", path, params=params)

    async def get_resource(
        self,
        folder_path: str,
        resource_key: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        """Get a single resource by key."""
        path = self._build_path(folder_path, suffix=f"/{resource_key}")
        return await self._transport.arequest("GET", path, params=params)

    async def search(
        self,
        folder_path: str,
        *,
        body: Mapping[str, Any],
    ) -> Any:
        path = self._build_path(folder_path, suffix="/_search")
        return await self._transport.arequest("POST", path, json_body=body)

    async def aclose(self) -> None:
        await self._transport.aclose()
