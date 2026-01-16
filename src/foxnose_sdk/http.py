from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Callable, Mapping

import httpx

from .auth.base import AnonymousAuth, AuthStrategy, RequestData
from .config import FoxnoseConfig, RetryConfig
from .errors import FoxnoseAPIError, FoxnoseTransportError

JSONDecoder = Callable[[httpx.Response], Any]


class HttpTransport:
    """Shared HTTP transport with retry logic and dual sync/async support."""

    def __init__(
        self,
        *,
        config: FoxnoseConfig,
        auth: AuthStrategy | None = None,
        retry_config: RetryConfig | None = None,
        sync_client: httpx.Client | None = None,
        async_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._auth = auth or AnonymousAuth()
        self._retry = retry_config or RetryConfig()
        self._client = sync_client or httpx.Client(
            base_url=self._config.base_url,
            timeout=self._config.timeout,
        )
        self._async_client = async_client or httpx.AsyncClient(
            base_url=self._config.base_url,
            timeout=self._config.timeout,
        )
        self._owns_client = sync_client is None
        self._owns_async_client = async_client is None

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Any | None = None,
        content: bytes | bytearray | memoryview | None = None,
        headers: Mapping[str, str] | None = None,
        parse_json: bool = True,
    ) -> Any:
        response = self._send_with_retries(
            client=self._client,
            builder=lambda: self._build_request(
                self._client,
                method,
                path,
                params=params,
                json_body=json_body,
                content=content,
                headers=headers,
            ),
            is_async=False,
        )
        return self._maybe_decode_response(response, parse_json=parse_json)

    async def arequest(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Any | None = None,
        content: bytes | bytearray | memoryview | None = None,
        headers: Mapping[str, str] | None = None,
        parse_json: bool = True,
    ) -> Any:
        response = await self._send_with_retries(
            client=self._async_client,
            builder=lambda: self._build_request(
                self._async_client,
                method,
                path,
                params=params,
                json_body=json_body,
                content=content,
                headers=headers,
            ),
            is_async=True,
        )
        return self._maybe_decode_response(response, parse_json=parse_json)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    async def aclose(self) -> None:
        if self._owns_async_client:
            await self._async_client.aclose()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _build_request(
        self,
        client: httpx.Client | httpx.AsyncClient,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None,
        json_body: Any | None,
        content: bytes | bytearray | memoryview | None,
        headers: Mapping[str, str] | None,
    ) -> httpx.Request:
        final_headers: dict[str, str] = {}
        if self._config.default_headers:
            final_headers.update(self._config.default_headers)
        final_headers.setdefault("User-Agent", self._config.user_agent)
        if headers:
            final_headers.update(headers)

        request = client.build_request(
            method=method,
            url=path,
            params=params,
            json=json_body,
            content=content,
            headers=final_headers,
        )
        request_data = RequestData(
            method=request.method,
            url=str(request.url),
            path=request.url.raw_path.decode("utf-8"),
            body=request.content,
        )
        auth_headers = self._auth.build_headers(request_data)
        if auth_headers:
            request.headers.update(auth_headers)
        return request

    def _should_retry(self, method: str, status_code: int) -> bool:
        if method.upper() not in self._retry.methods:
            return False
        return status_code in self._retry.status_codes

    def _compute_delay(self, attempt: int, retry_after: str | None) -> float:
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                return 0.0
        return self._retry.backoff_factor * (2 ** max(attempt - 1, 0))

    def _maybe_decode_response(
        self, response: httpx.Response, *, parse_json: bool
    ) -> Any:
        if not parse_json:
            return response
        if not response.content:
            return None
        try:
            return response.json()
        except json.JSONDecodeError:
            return response.text

    def _send_with_retries(
        self,
        *,
        client: httpx.Client | httpx.AsyncClient,
        builder: Callable[[], httpx.Request],
        is_async: bool,
    ) -> httpx.Response | asyncio.Future[httpx.Response]:
        async def async_loop() -> httpx.Response:
            for attempt in range(1, self._retry.attempts + 1):
                request = builder()
                try:
                    response = await client.send(request)
                except httpx.RequestError as exc:
                    delay = self._handle_transport_error(exc, attempt)
                    if delay > 0:
                        await asyncio.sleep(delay)
                    continue
                if response.status_code >= 400:
                    if (
                        self._should_retry(request.method, response.status_code)
                        and attempt < self._retry.attempts
                    ):
                        delay = self._compute_delay(
                            attempt, response.headers.get("Retry-After")
                        )
                        if delay:
                            await asyncio.sleep(delay)
                        continue
                    self._raise_api_error(response)
                return response
            raise AssertionError("unreachable")  # pragma: no cover

        def sync_loop() -> httpx.Response:
            for attempt in range(1, self._retry.attempts + 1):
                request = builder()
                try:
                    response = client.send(request)  # type: ignore[arg-type]
                except httpx.RequestError as exc:
                    delay = self._handle_transport_error(exc, attempt)
                    if delay > 0:
                        time.sleep(delay)
                    continue
                if response.status_code >= 400:
                    if (
                        self._should_retry(request.method, response.status_code)
                        and attempt < self._retry.attempts
                    ):
                        delay = self._compute_delay(
                            attempt, response.headers.get("Retry-After")
                        )
                        if delay:
                            time.sleep(delay)
                        continue
                    self._raise_api_error(response)
                return response
            raise AssertionError("unreachable")  # pragma: no cover

        return async_loop() if is_async else sync_loop()

    def _handle_transport_error(self, exc: httpx.RequestError, attempt: int) -> float:
        if attempt >= self._retry.attempts:
            raise FoxnoseTransportError(str(exc)) from exc
        return self._compute_delay(attempt, retry_after=None)

    @staticmethod
    def _raise_api_error(response: httpx.Response) -> None:
        message = response.text
        error_code = None
        detail = None
        body: Any | None = None
        if response.content:
            try:
                payload = response.json()
                message = payload.get("message", message)
                error_code = payload.get("error_code")
                detail = payload.get("detail")
                body = payload
            except json.JSONDecodeError:
                body = response.text
        raise FoxnoseAPIError(
            message=message or "API request failed",
            status_code=response.status_code,
            error_code=error_code,
            detail=detail,
            response_headers=dict(response.headers),
            response_body=body,
        )
