from __future__ import annotations

import httpx
from typing import Any, Mapping
from urllib.parse import quote

from ..auth import AuthStrategy
from ..config import FoxnoseConfig, RetryConfig
from ..http import HttpTransport
from .models import (
    HybridConfig,
    SearchMode,
    SearchRequest,
    UploadSignature,
    UploadStatus,
    VectorBoostConfig,
    VectorFieldSearch,
    VectorSearch,
)

_SEARCH_REQUEST_FIELDS = frozenset(SearchRequest.model_fields.keys())


def _merge_extra(validated: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    """Merge extra_body into the validated payload, rejecting key conflicts."""
    if "truncate_text" in extra:
        raise ValueError(
            "'truncate_text' is a query parameter, not a body field. "
            "Pass it via 'query_params={\"truncate_text\": ...}' instead."
        )
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


def _upload_status_suffix(upload_id: str) -> str:
    return f"/_uploads/{quote(upload_id, safe='')}"


def _upload_signature_body(session_key: str | None) -> dict[str, str] | None:
    return None if session_key is None else {"session_key": session_key}


def _upload_status_headers(status_token: str | None) -> dict[str, str] | None:
    return None if status_token is None else {"X-Upload-Status-Token": status_token}


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
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        """Search a collection.

        Args:
            folder_path: Collection path to search.
            body: The search request body (see :class:`SearchRequest`).
            params: Optional query parameters, e.g. ``{"truncate_text": 200}``
                to cap every ``text``-typed field in the response. Values
                are not validated client-side; an invalid ``truncate_text``
                (non-integer or < 1) surfaces as a server ``422``.
        """
        path = self._build_path(folder_path, suffix="/_search")
        return self._transport.request("POST", path, json_body=body, params=params)

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

    def create_upload_signature(
        self,
        folder_path: str,
        *,
        session_key: str | None = None,
    ) -> UploadSignature:
        """Get a grant for one upload to a files collection.

        The grant is a credential: pass it on, do not log it.

        Args:
            folder_path: Path of the files collection. For a strict collection it
                names the owner, e.g. ``"support/tickets/tk_1/attachments"``.
            session_key: Optional idempotency key of 43 URL-safe characters. A
                repeat with the same key, collection and owner reaches the same
                upload session.

        Returns:
            The :class:`UploadSignature`, with the ``upload_id`` to poll and the
            end user's ``status_token``.

        Note:
            Needs a key with create access to the collection. A failed request is
            never retried automatically; to retry one safely, send a
            ``session_key``.
        """
        path = self._build_path(folder_path, suffix="/_upload-signature")
        data = self._transport.request(
            "POST",
            path,
            json_body=_upload_signature_body(session_key),
            allow_retries=False,
        )
        return UploadSignature.model_validate(data)

    def get_upload_status(
        self,
        folder_path: str,
        upload_id: str,
        *,
        status_token: str | None = None,
    ) -> UploadStatus:
        """Read the status of an upload.

        A key reads the uploads that key started, and the path must name the same
        collection and owner. Any other combination is ``404 not_found``, which
        includes a link made through the Management API: read that one with
        ``ManagementClient.get_upload_link``.

        Args:
            folder_path: Path of the files collection.
            upload_id: The upload's id.
            status_token: The end user's token from the grant, for a client that
                holds no key (use ``AnonymousAuth``). It answers the end user's
                view, which never carries a record key. A request authenticated
                by a key ignores it.
        """
        path = self._build_path(folder_path, suffix=_upload_status_suffix(upload_id))
        data = self._transport.request(
            "GET", path, headers=_upload_status_headers(status_token)
        )
        return UploadStatus.model_validate(data)

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
        query_params: Mapping[str, Any] | None = None,
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
        return self.search(folder_path, body=body, params=query_params)

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
        query_params: Mapping[str, Any] | None = None,
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
        return self.search(folder_path, body=body, params=query_params)

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
        query_params: Mapping[str, Any] | None = None,
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
        return self.search(folder_path, body=body, params=query_params)

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
        query_params: Mapping[str, Any] | None = None,
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
        return self.search(folder_path, body=body, params=query_params)

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
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        """Search a collection.

        Args:
            folder_path: Collection path to search.
            body: The search request body (see :class:`SearchRequest`).
            params: Optional query parameters, e.g. ``{"truncate_text": 200}``
                to cap every ``text``-typed field in the response. Values
                are not validated client-side; an invalid ``truncate_text``
                (non-integer or < 1) surfaces as a server ``422``.
        """
        path = self._build_path(folder_path, suffix="/_search")
        return await self._transport.arequest(
            "POST", path, json_body=body, params=params
        )

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

    async def create_upload_signature(
        self,
        folder_path: str,
        *,
        session_key: str | None = None,
    ) -> UploadSignature:
        """Get a grant for one upload to a files collection.

        The grant is a credential: pass it on, do not log it.

        Args:
            folder_path: Path of the files collection. For a strict collection it
                names the owner, e.g. ``"support/tickets/tk_1/attachments"``.
            session_key: Optional idempotency key of 43 URL-safe characters. A
                repeat with the same key, collection and owner reaches the same
                upload session.

        Returns:
            The :class:`UploadSignature`, with the ``upload_id`` to poll and the
            end user's ``status_token``.

        Note:
            Needs a key with create access to the collection. A failed request is
            never retried automatically; to retry one safely, send a
            ``session_key``.
        """
        path = self._build_path(folder_path, suffix="/_upload-signature")
        data = await self._transport.arequest(
            "POST",
            path,
            json_body=_upload_signature_body(session_key),
            allow_retries=False,
        )
        return UploadSignature.model_validate(data)

    async def get_upload_status(
        self,
        folder_path: str,
        upload_id: str,
        *,
        status_token: str | None = None,
    ) -> UploadStatus:
        """Read the status of an upload.

        A key reads the uploads that key started, and the path must name the same
        collection and owner. Any other combination is ``404 not_found``, which
        includes a link made through the Management API: read that one with
        ``AsyncManagementClient.get_upload_link``.

        Args:
            folder_path: Path of the files collection.
            upload_id: The upload's id.
            status_token: The end user's token from the grant, for a client that
                holds no key (use ``AnonymousAuth``). It answers the end user's
                view, which never carries a record key. A request authenticated
                by a key ignores it.
        """
        path = self._build_path(folder_path, suffix=_upload_status_suffix(upload_id))
        data = await self._transport.arequest(
            "GET", path, headers=_upload_status_headers(status_token)
        )
        return UploadStatus.model_validate(data)

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
        query_params: Mapping[str, Any] | None = None,
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
        return await self.search(folder_path, body=body, params=query_params)

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
        query_params: Mapping[str, Any] | None = None,
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
        return await self.search(folder_path, body=body, params=query_params)

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
        query_params: Mapping[str, Any] | None = None,
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
        return await self.search(folder_path, body=body, params=query_params)

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
        query_params: Mapping[str, Any] | None = None,
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
        return await self.search(folder_path, body=body, params=query_params)

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
