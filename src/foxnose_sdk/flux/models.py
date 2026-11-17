"""Pydantic models for Flux vector search requests."""

from __future__ import annotations

import math
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SearchMode(str, Enum):
    """Search mode for the Flux search endpoint."""

    TEXT = "text"
    VECTOR = "vector"
    VECTOR_BOOSTED = "vector_boosted"
    HYBRID = "hybrid"


def _check_finite(v: float, field_name: str) -> float:
    if not math.isfinite(v):
        raise ValueError(f"{field_name} must be a finite number")
    return v


def _check_threshold(v: float | None, field_name: str) -> float | None:
    if v is not None:
        _check_finite(v, field_name)
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"{field_name} must be between 0.0 and 1.0")
    return v


class VectorSearch(BaseModel):
    """Configuration for auto-generated embedding search."""

    query: str
    fields: list[str] | None = None
    top_k: int = 10
    similarity_threshold: float | None = None

    @field_validator("top_k")
    @classmethod
    def _top_k_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("top_k must be >= 1")
        return v

    @field_validator("similarity_threshold")
    @classmethod
    def _threshold_range(cls, v: float | None) -> float | None:
        return _check_threshold(v, "similarity_threshold")


class VectorFieldSearch(BaseModel):
    """Configuration for custom pre-computed embedding search."""

    field: str
    query_vector: list[float]
    top_k: int = 10
    similarity_threshold: float | None = None

    @field_validator("query_vector")
    @classmethod
    def _vector_not_empty(cls, v: list[float]) -> list[float]:
        if not v:
            raise ValueError("query_vector must not be empty")
        for i, val in enumerate(v):
            if not math.isfinite(val):
                raise ValueError(
                    f"query_vector[{i}] must be a finite number, got {val}"
                )
        return v

    @field_validator("top_k")
    @classmethod
    def _top_k_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("top_k must be >= 1")
        return v

    @field_validator("similarity_threshold")
    @classmethod
    def _threshold_range(cls, v: float | None) -> float | None:
        return _check_threshold(v, "similarity_threshold")


class VectorBoostConfig(BaseModel):
    """Configuration for vector-boosted search mode."""

    boost_factor: float = 1.5
    similarity_threshold: float | None = None
    max_boost_results: int = 20

    @field_validator("boost_factor")
    @classmethod
    def _boost_positive(cls, v: float) -> float:
        _check_finite(v, "boost_factor")
        if v <= 0:
            raise ValueError("boost_factor must be > 0")
        return v

    @field_validator("similarity_threshold")
    @classmethod
    def _threshold_range(cls, v: float | None) -> float | None:
        return _check_threshold(v, "similarity_threshold")

    @field_validator("max_boost_results")
    @classmethod
    def _max_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_boost_results must be >= 1")
        return v


class HybridConfig(BaseModel):
    """Configuration for hybrid (text + vector) search mode."""

    vector_weight: float = 0.6
    text_weight: float = 0.4
    rerank_results: bool = True

    @field_validator("vector_weight", "text_weight")
    @classmethod
    def _weight_range(cls, v: float) -> float:
        _check_finite(v, "weight")
        if not 0.0 <= v <= 1.0:
            raise ValueError("weight must be between 0.0 and 1.0")
        return v

    @model_validator(mode="after")
    def _weights_sum(self) -> HybridConfig:
        total = self.vector_weight + self.text_weight
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"vector_weight + text_weight must equal 1.0, got {total}")
        return self


class SearchRequest(BaseModel):
    """Full search request payload for the Flux search endpoint.

    Supports all search modes: text, vector, vector_boosted, and hybrid.
    Extra fields (e.g. ``where``, ``sort``) are forwarded to the API.
    """

    model_config = ConfigDict(extra="allow")

    search_mode: SearchMode = SearchMode.TEXT
    find_text: dict[str, Any] | None = None
    find_phrase: dict[str, Any] | None = None
    vector_search: VectorSearch | None = None
    vector_field_search: VectorFieldSearch | None = None
    vector_boost_config: VectorBoostConfig | None = None
    hybrid_config: HybridConfig | None = None
    limit: int | None = None
    offset: int | None = None

    @model_validator(mode="after")
    def _validate_mode_constraints(self) -> SearchRequest:
        mode = self.search_mode
        vs = self.vector_search
        vfs = self.vector_field_search
        boost = self.vector_boost_config
        hybrid = self.hybrid_config
        has_text = self.find_text is not None or self.find_phrase is not None

        # Mutual exclusion: vector_search and vector_field_search
        if vs is not None and vfs is not None:
            raise ValueError(
                "vector_search and vector_field_search are mutually exclusive"
            )

        if mode == SearchMode.TEXT:
            if vs is not None:
                raise ValueError("vector_search is not allowed in text search mode")
            if vfs is not None:
                raise ValueError(
                    "vector_field_search is not allowed in text search mode"
                )
            if boost is not None:
                raise ValueError(
                    "vector_boost_config is not allowed in text search mode"
                )
            if hybrid is not None:
                raise ValueError("hybrid_config is not allowed in text search mode")

        elif mode == SearchMode.VECTOR:
            if vs is None and vfs is None:
                raise ValueError(
                    "vector search mode requires vector_search or vector_field_search"
                )
            if boost is not None:
                raise ValueError(
                    "vector_boost_config is not allowed in vector search mode"
                )
            if hybrid is not None:
                raise ValueError("hybrid_config is not allowed in vector search mode")

        elif mode == SearchMode.VECTOR_BOOSTED:
            if vs is None and vfs is None:
                raise ValueError(
                    "vector_boosted mode requires vector_search or vector_field_search"
                )
            if not has_text:
                raise ValueError(
                    "vector_boosted mode requires find_text or find_phrase"
                )
            if hybrid is not None:
                raise ValueError("hybrid_config is not allowed in vector_boosted mode")

        elif mode == SearchMode.HYBRID:
            if vfs is not None:
                raise ValueError("vector_field_search is not allowed in hybrid mode")
            if vs is None:
                raise ValueError("hybrid mode requires vector_search")
            if not has_text:
                raise ValueError("hybrid mode requires find_text or find_phrase")
            if boost is not None:
                raise ValueError("vector_boost_config is not allowed in hybrid mode")

        return self


class UploadSignature(BaseModel):
    """A grant for one upload to a files collection.

    The grant is a credential. ``repr()`` and ``str()`` show only ``upload_id`` and
    ``token_expire``, and a response that fails to parse does not quote it, so an
    accidental log line stays clean. Keep it that way: read ``auth_token`` and
    ``status_token`` only to pass them on.

    Attribute names are snake_case; ``model_dump(by_alias=True)`` gives the wire
    field names, for handing the grant to a browser.
    """

    model_config = ConfigDict(
        extra="allow", populate_by_name=True, hide_input_in_errors=True
    )

    public_key: str = Field(alias="publicKey")
    upload_base_url: str = Field(alias="uploadBaseUrl")
    auth_token: str = Field(alias="authToken", repr=False)
    token_expire: int = Field(alias="tokenExpire")
    store: str
    metadata: dict[str, Any]
    upload_id: str
    status_token: str = Field(repr=False)
    rotation: int

    def __repr_args__(self) -> list[tuple[str, Any]]:
        # An allow-list: a field the server adds later must not reach a log line.
        return [("upload_id", self.upload_id), ("token_expire", self.token_expire)]


class UploadFileStatus(BaseModel):
    """The status of one file of an upload.

    A key sees ``state`` as ``processing``, ``ready`` (with ``record_key``),
    ``pending_review`` or ``rejected`` (with ``public_reason``). A status token
    sees ``processing``, ``accepted`` or ``rejected``, with ``user_status``,
    ``reason`` and ``slot``.
    """

    model_config = ConfigDict(extra="allow")

    state: str
    record_key: str | None = None
    public_reason: str | None = None
    user_status: str | None = None
    reason: str | None = None
    slot: int | None = None


class UploadStatus(UploadFileStatus):
    """The status of an upload.

    For an upload of one file these are that file's fields. For a link of several
    files, ``state`` is ``processing`` or ``done`` and ``files`` and ``remaining``
    are set; a status token also gets ``slots_uploading``.
    """

    files: list[UploadFileStatus] | None = None
    remaining: int | None = None
    slots_uploading: list[dict[str, Any]] | None = None
