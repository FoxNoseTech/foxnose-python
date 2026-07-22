from __future__ import annotations

import httpx
from typing import Any, Mapping

from ..auth import AuthStrategy
from ..config import FoxnoseConfig, RetryConfig
from ..http import HttpTransport
from .models import (
    HybridConfig,
    SearchMode,
    SearchRequest,
    VectorBoostConfig,
    VectorFieldSearch,
    VectorSearch,
)

_SEARCH_REQUEST_FIELDS = frozenset(SearchRequest.model_fields.keys())


def _merge_extra(validated: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    """Merge extra_body into the validated payload, rejecting key conflicts."""
    conflicts = _SEARCH_REQUEST_FIELDS & extra.keys()
    if conflicts:
        raise ValueError(
            f"extra_body keys conflict with SearchRequest fields: "
            f"{', '.join(sorted(conflicts))}. "
            f"Use the explicit parameters instead."
        )
    return {**validated, **extra}


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

    def create_resource(
        self,
        folder_path: str,
        data: Mapping[str, Any],
        *,
        key: str | None = None,
    ) -> Any:
        """Create a resource in a collection and publish it immediately.

        Args:
            folder_path: Collection path, e.g. ``"articles"`` or a nested path
                such as ``"users/usr_1/memories"``.
            data: The resource document (a JSON object).
            key: Optional external identifier for deduplication. Reusing a key
                that already exists raises :class:`ExternalIdConflict`.

        Returns:
            The parsed response mapping with ``resource_key``, ``revision_key``,
            ``write_units`` and ``published``.

        Note:
            Writes require an authenticated key with write access: an anonymous
            caller gets 401, a key without the ``create`` grant gets a generic
            403 (``access_denied``), and a collection whose connection does not
            allow writes raises :class:`CollectionNotWritable`. A failed
            write is never retried automatically — its outcome is unknown, so
            re-read with a GET before retrying.
        """
        path = self._build_path(folder_path, suffix="/")
        body: dict[str, Any] = {"data": dict(data)}
        if key is not None:
            body["key"] = key
        return self._transport.request(
            "POST", path, json_body=body, allow_retries=False
        )

    def update_resource(
        self,
        folder_path: str,
        resource_key: str,
        data: Mapping[str, Any],
    ) -> Any:
        """Replace a resource's document and publish a new revision.

        This is a full-document replace, not a partial merge: fields absent from
        ``data`` are removed from the stored resource.

        Returns:
            The parsed response mapping with ``resource_key``, ``revision_key``,
            ``write_units`` and ``published``.

        Note:
            Writes require an authenticated key with write access: an anonymous
            caller gets 401, a key without the ``update`` grant gets a generic
            403 (``access_denied``), and a collection whose connection does not
            allow writes raises :class:`CollectionNotWritable`. A failed write is
            never retried automatically — its outcome is unknown, so re-read with
            a GET before retrying.
        """
        path = self._build_path(folder_path, suffix=f"/{resource_key}/")
        return self._transport.request(
            "PUT", path, json_body={"data": dict(data)}, allow_retries=False
        )

    def vector_search(
        self,
        folder_path: str,
        *,
        query: str,
        fields: list[str] | None = None,
        top_k: int = 10,
        similarity_threshold: float | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **extra_body: Any,
    ) -> Any:
        """Semantic search using auto-generated embeddings."""
        req = SearchRequest(
            search_mode=SearchMode.VECTOR,
            vector_search=VectorSearch(
                query=query,
                fields=fields,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            ),
            limit=limit,
            offset=offset,
        )
        body = _merge_extra(req.model_dump(exclude_none=True), extra_body)
        return self.search(folder_path, body=body)

    def vector_field_search(
        self,
        folder_path: str,
        *,
        field: str,
        query_vector: list[float],
        top_k: int = 10,
        similarity_threshold: float | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **extra_body: Any,
    ) -> Any:
        """Search using custom pre-computed embeddings."""
        req = SearchRequest(
            search_mode=SearchMode.VECTOR,
            vector_field_search=VectorFieldSearch(
                field=field,
                query_vector=query_vector,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            ),
            limit=limit,
            offset=offset,
        )
        body = _merge_extra(req.model_dump(exclude_none=True), extra_body)
        return self.search(folder_path, body=body)

    def hybrid_search(
        self,
        folder_path: str,
        *,
        query: str,
        find_text: dict[str, Any],
        fields: list[str] | None = None,
        top_k: int = 10,
        similarity_threshold: float | None = None,
        vector_weight: float = 0.6,
        text_weight: float = 0.4,
        rerank_results: bool = True,
        limit: int | None = None,
        offset: int | None = None,
        **extra_body: Any,
    ) -> Any:
        """Blended text + vector search with configurable weights."""
        req = SearchRequest(
            search_mode=SearchMode.HYBRID,
            find_text=find_text,
            vector_search=VectorSearch(
                query=query,
                fields=fields,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            ),
            hybrid_config=HybridConfig(
                vector_weight=vector_weight,
                text_weight=text_weight,
                rerank_results=rerank_results,
            ),
            limit=limit,
            offset=offset,
        )
        body = _merge_extra(req.model_dump(exclude_none=True), extra_body)
        return self.search(folder_path, body=body)

    def boosted_search(
        self,
        folder_path: str,
        *,
        find_text: dict[str, Any],
        query: str | None = None,
        field: str | None = None,
        query_vector: list[float] | None = None,
        top_k: int = 10,
        similarity_threshold: float | None = None,
        boost_factor: float = 1.5,
        boost_similarity_threshold: float | None = None,
        max_boost_results: int = 20,
        limit: int | None = None,
        offset: int | None = None,
        **extra_body: Any,
    ) -> Any:
        """Text search with results boosted by vector similarity."""
        has_auto = query is not None
        has_custom = field is not None or query_vector is not None
        if has_auto and has_custom:
            raise ValueError(
                "Provide either 'query' for auto-generated embeddings "
                "or 'field' + 'query_vector' for custom embeddings, not both"
            )
        vs: VectorSearch | None = None
        vfs: VectorFieldSearch | None = None
        if has_auto:
            vs = VectorSearch(
                query=query,  # type: ignore[arg-type]
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )
        elif field is not None and query_vector is not None:
            vfs = VectorFieldSearch(
                field=field,
                query_vector=query_vector,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )
        else:
            raise ValueError(
                "Provide either 'query' for auto-generated embeddings "
                "or 'field' + 'query_vector' for custom embeddings"
            )
        req = SearchRequest(
            search_mode=SearchMode.VECTOR_BOOSTED,
            find_text=find_text,
            vector_search=vs,
            vector_field_search=vfs,
            vector_boost_config=VectorBoostConfig(
                boost_factor=boost_factor,
                similarity_threshold=boost_similarity_threshold,
                max_boost_results=max_boost_results,
            ),
            limit=limit,
            offset=offset,
        )
        body = _merge_extra(req.model_dump(exclude_none=True), extra_body)
        return self.search(folder_path, body=body)

    def get_router(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """Return available routes and contracts under the configured API prefix."""
        path = f"/{self.api_prefix}/_router"
        return self._transport.request("GET", path, params=params)

    def get_schema(
        self, folder_path: str, *, params: Mapping[str, Any] | None = None
    ) -> Any:
        """Return live JSON Schema and metadata for the given folder path."""
        path = self._build_path(folder_path, suffix="/_schema")
        return self._transport.request("GET", path, params=params)

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

    async def create_resource(
        self,
        folder_path: str,
        data: Mapping[str, Any],
        *,
        key: str | None = None,
    ) -> Any:
        """Create a resource in a collection and publish it immediately.

        Args:
            folder_path: Collection path, e.g. ``"articles"`` or a nested path
                such as ``"users/usr_1/memories"``.
            data: The resource document (a JSON object).
            key: Optional external identifier for deduplication. Reusing a key
                that already exists raises :class:`ExternalIdConflict`.

        Returns:
            The parsed response mapping with ``resource_key``, ``revision_key``,
            ``write_units`` and ``published``.

        Note:
            Writes require an authenticated key with write access: an anonymous
            caller gets 401, a key without the ``create`` grant gets a generic
            403 (``access_denied``), and a collection whose connection does not
            allow writes raises :class:`CollectionNotWritable`. A failed
            write is never retried automatically — its outcome is unknown, so
            re-read with a GET before retrying.
        """
        path = self._build_path(folder_path, suffix="/")
        body: dict[str, Any] = {"data": dict(data)}
        if key is not None:
            body["key"] = key
        return await self._transport.arequest(
            "POST", path, json_body=body, allow_retries=False
        )

    async def update_resource(
        self,
        folder_path: str,
        resource_key: str,
        data: Mapping[str, Any],
    ) -> Any:
        """Replace a resource's document and publish a new revision.

        This is a full-document replace, not a partial merge: fields absent from
        ``data`` are removed from the stored resource.

        Returns:
            The parsed response mapping with ``resource_key``, ``revision_key``,
            ``write_units`` and ``published``.

        Note:
            Writes require an authenticated key with write access: an anonymous
            caller gets 401, a key without the ``update`` grant gets a generic
            403 (``access_denied``), and a collection whose connection does not
            allow writes raises :class:`CollectionNotWritable`. A failed write is
            never retried automatically — its outcome is unknown, so re-read with
            a GET before retrying.
        """
        path = self._build_path(folder_path, suffix=f"/{resource_key}/")
        return await self._transport.arequest(
            "PUT", path, json_body={"data": dict(data)}, allow_retries=False
        )

    async def vector_search(
        self,
        folder_path: str,
        *,
        query: str,
        fields: list[str] | None = None,
        top_k: int = 10,
        similarity_threshold: float | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **extra_body: Any,
    ) -> Any:
        """Semantic search using auto-generated embeddings."""
        req = SearchRequest(
            search_mode=SearchMode.VECTOR,
            vector_search=VectorSearch(
                query=query,
                fields=fields,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            ),
            limit=limit,
            offset=offset,
        )
        body = _merge_extra(req.model_dump(exclude_none=True), extra_body)
        return await self.search(folder_path, body=body)

    async def vector_field_search(
        self,
        folder_path: str,
        *,
        field: str,
        query_vector: list[float],
        top_k: int = 10,
        similarity_threshold: float | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **extra_body: Any,
    ) -> Any:
        """Search using custom pre-computed embeddings."""
        req = SearchRequest(
            search_mode=SearchMode.VECTOR,
            vector_field_search=VectorFieldSearch(
                field=field,
                query_vector=query_vector,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            ),
            limit=limit,
            offset=offset,
        )
        body = _merge_extra(req.model_dump(exclude_none=True), extra_body)
        return await self.search(folder_path, body=body)

    async def hybrid_search(
        self,
        folder_path: str,
        *,
        query: str,
        find_text: dict[str, Any],
        fields: list[str] | None = None,
        top_k: int = 10,
        similarity_threshold: float | None = None,
        vector_weight: float = 0.6,
        text_weight: float = 0.4,
        rerank_results: bool = True,
        limit: int | None = None,
        offset: int | None = None,
        **extra_body: Any,
    ) -> Any:
        """Blended text + vector search with configurable weights."""
        req = SearchRequest(
            search_mode=SearchMode.HYBRID,
            find_text=find_text,
            vector_search=VectorSearch(
                query=query,
                fields=fields,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            ),
            hybrid_config=HybridConfig(
                vector_weight=vector_weight,
                text_weight=text_weight,
                rerank_results=rerank_results,
            ),
            limit=limit,
            offset=offset,
        )
        body = _merge_extra(req.model_dump(exclude_none=True), extra_body)
        return await self.search(folder_path, body=body)

    async def boosted_search(
        self,
        folder_path: str,
        *,
        find_text: dict[str, Any],
        query: str | None = None,
        field: str | None = None,
        query_vector: list[float] | None = None,
        top_k: int = 10,
        similarity_threshold: float | None = None,
        boost_factor: float = 1.5,
        boost_similarity_threshold: float | None = None,
        max_boost_results: int = 20,
        limit: int | None = None,
        offset: int | None = None,
        **extra_body: Any,
    ) -> Any:
        """Text search with results boosted by vector similarity."""
        has_auto = query is not None
        has_custom = field is not None or query_vector is not None
        if has_auto and has_custom:
            raise ValueError(
                "Provide either 'query' for auto-generated embeddings "
                "or 'field' + 'query_vector' for custom embeddings, not both"
            )
        vs: VectorSearch | None = None
        vfs: VectorFieldSearch | None = None
        if has_auto:
            vs = VectorSearch(
                query=query,  # type: ignore[arg-type]
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )
        elif field is not None and query_vector is not None:
            vfs = VectorFieldSearch(
                field=field,
                query_vector=query_vector,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )
        else:
            raise ValueError(
                "Provide either 'query' for auto-generated embeddings "
                "or 'field' + 'query_vector' for custom embeddings"
            )
        req = SearchRequest(
            search_mode=SearchMode.VECTOR_BOOSTED,
            find_text=find_text,
            vector_search=vs,
            vector_field_search=vfs,
            vector_boost_config=VectorBoostConfig(
                boost_factor=boost_factor,
                similarity_threshold=boost_similarity_threshold,
                max_boost_results=max_boost_results,
            ),
            limit=limit,
            offset=offset,
        )
        body = _merge_extra(req.model_dump(exclude_none=True), extra_body)
        return await self.search(folder_path, body=body)

    async def get_router(self, *, params: Mapping[str, Any] | None = None) -> Any:
        """Return available routes and contracts under the configured API prefix."""
        path = f"/{self.api_prefix}/_router"
        return await self._transport.arequest("GET", path, params=params)

    async def get_schema(
        self, folder_path: str, *, params: Mapping[str, Any] | None = None
    ) -> Any:
        """Return live JSON Schema and metadata for the given folder path."""
        path = self._build_path(folder_path, suffix="/_schema")
        return await self._transport.arequest("GET", path, params=params)

    async def aclose(self) -> None:
        await self._transport.aclose()
