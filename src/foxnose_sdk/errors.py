from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class FoxnoseError(Exception):
    """Base class for all SDK errors."""


@dataclass
class FoxnoseAPIError(FoxnoseError):
    """Raised when the API responds with an error status."""

    message: str
    status_code: int
    error_code: str | None = None
    detail: Any | None = None
    response_headers: Mapping[str, str] | None = None
    response_body: Any | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        code = f", error_code={self.error_code}" if self.error_code else ""
        return f"{self.message} (status={self.status_code}{code})"


class SpendCapExceeded(FoxnoseAPIError):
    """Raised on HTTP 402 ``spend_cap_reached`` — the account spend cap was hit."""

    def __init__(
        self,
        *,
        cap_usd: float | None = None,
        cycle_resets_at: str | None = None,
        raise_cap_url: str | None = None,
        **base_kwargs: Any,
    ) -> None:
        super().__init__(**base_kwargs)
        self.cap_usd = cap_usd
        self.cycle_resets_at = cycle_resets_at
        self.raise_cap_url = raise_cap_url


class PlanExhausted(FoxnoseAPIError):
    """Raised on HTTP 402 ``plan_exhausted`` — a metered plan allowance ran out."""

    def __init__(
        self,
        *,
        axis: str | None = None,
        window_resets_at: str | None = None,
        upgrade_url: str | None = None,
        **base_kwargs: Any,
    ) -> None:
        super().__init__(**base_kwargs)
        self.axis = axis
        self.window_resets_at = window_resets_at
        self.upgrade_url = upgrade_url


class PlanLimitExceeded(FoxnoseAPIError):
    """Raised on HTTP 403 ``plan_limit_exceeded`` — a plan entity ceiling was hit."""

    def __init__(
        self,
        *,
        entity: str | None = None,
        limit: int | None = None,
        current: int | None = None,
        upgrade_url: str | None = None,
        **base_kwargs: Any,
    ) -> None:
        super().__init__(**base_kwargs)
        self.entity = entity
        self.limit = limit
        self.current = current
        self.upgrade_url = upgrade_url


class RateLimitExceeded(FoxnoseAPIError):
    """Raised on HTTP 429 ``rate_limited`` — too many requests."""

    def __init__(
        self,
        *,
        retry_after: float | None = None,
        **base_kwargs: Any,
    ) -> None:
        super().__init__(**base_kwargs)
        self.retry_after = retry_after


class CollectionNotWritable(FoxnoseAPIError):
    """Raised on HTTP 403 ``collection_not_writable`` — the target collection does
    not accept writes (or the key in use lacks write access)."""


class ExternalIdConflict(FoxnoseAPIError):
    """Raised on HTTP 409 ``external_id_conflict`` — the supplied ``key`` already
    identifies an existing resource in the collection."""


class ContentValidationFailed(FoxnoseAPIError):
    """Raised on HTTP 422 ``content_validation_failed`` — the submitted ``data``
    failed the collection's schema.

    ``errors`` is the list of individual validation problems, each a mapping that
    includes a ``json_path`` locating the offending field. ``errors_truncated`` is
    True when the server capped a very large error list.
    """

    def __init__(
        self,
        *,
        errors: list | None = None,
        errors_truncated: bool = False,
        **base_kwargs: Any,
    ) -> None:
        super().__init__(**base_kwargs)
        self.errors = errors or []
        self.errors_truncated = errors_truncated


class UpstreamError(FoxnoseAPIError):
    """Raised on HTTP 502 ``upstream_error`` — a write could not be confirmed.

    The write may or may not have been applied. Do not blindly retry; re-read the
    resource with a GET to determine the actual state first.
    """


class FoxnoseAuthError(FoxnoseError):
    """Raised when authentication headers cannot be generated."""


class FoxnoseTransportError(FoxnoseError):
    """Raised when the HTTP layer fails before receiving a response."""


def _validation_errors_from_detail(detail: Any) -> tuple[list, bool]:
    """Normalize a validation ``detail`` payload into (errors, truncated).

    The detail is either a single problem mapping (carrying ``json_path``) or a
    wrapper mapping carrying an ``errors`` list.
    """
    if isinstance(detail, dict):
        if isinstance(detail.get("errors"), list):
            return detail["errors"], bool(detail.get("errors_truncated", False))
        if "json_path" in detail:
            return [detail], bool(detail.get("errors_truncated", False))
    return [], False


def _header_lookup(headers: Mapping[str, str] | None, name: str) -> str | None:
    """Case-insensitively read a header value (httpx lowercases header names)."""
    if not headers:
        return None
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return value
    return None


def build_api_error(
    *,
    message: str,
    status_code: int,
    error_code: str | None,
    detail: Any | None,
    response_headers: Mapping[str, str] | None,
    response_body: Any | None,
) -> FoxnoseAPIError:
    """Build the most specific ``FoxnoseAPIError`` subclass for a response.

    Mapping is exact on ``(status_code, error_code)``; anything else — including
    a malformed body on a mapped status — falls through to the base class. This
    never raises while parsing.
    """
    base_kwargs: dict[str, Any] = {
        "message": message,
        "status_code": status_code,
        "error_code": error_code,
        "detail": detail,
        "response_headers": response_headers,
        "response_body": response_body,
    }
    body = response_body if isinstance(response_body, dict) else None

    if status_code == 402 and error_code == "spend_cap_reached" and body is not None:
        if "message" not in body:
            base_kwargs["message"] = "Spend cap reached"
        return SpendCapExceeded(
            cap_usd=body.get("cap_usd"),
            cycle_resets_at=body.get("cycle_resets_at"),
            raise_cap_url=body.get("raise_cap_url"),
            **base_kwargs,
        )

    if status_code == 402 and error_code == "plan_exhausted" and body is not None:
        if "message" not in body:
            base_kwargs["message"] = "Plan allowance exhausted"
        return PlanExhausted(
            axis=body.get("axis"),
            window_resets_at=body.get("window_resets_at"),
            upgrade_url=body.get("upgrade_url"),
            **base_kwargs,
        )

    if status_code == 403 and error_code == "plan_limit_exceeded":
        detail_obj = detail if isinstance(detail, dict) else {}
        return PlanLimitExceeded(
            entity=detail_obj.get("entity"),
            limit=detail_obj.get("limit"),
            current=detail_obj.get("current"),
            upgrade_url=detail_obj.get("upgrade_url"),
            **base_kwargs,
        )

    if status_code == 429 and error_code == "rate_limited":
        retry_after: float | None = None
        raw_retry_after = _header_lookup(response_headers, "Retry-After")
        if raw_retry_after is not None:
            try:
                retry_after = float(raw_retry_after)
            except ValueError:
                retry_after = None
        return RateLimitExceeded(retry_after=retry_after, **base_kwargs)

    if status_code == 403 and error_code == "collection_not_writable":
        if not message:
            base_kwargs["message"] = "Collection is not writable"
        return CollectionNotWritable(**base_kwargs)

    if status_code == 409 and error_code == "external_id_conflict":
        if not message:
            base_kwargs["message"] = "Resource key already exists"
        return ExternalIdConflict(**base_kwargs)

    if status_code == 422 and error_code == "content_validation_failed":
        errors, truncated = _validation_errors_from_detail(detail)
        if not message:
            base_kwargs["message"] = "Content validation failed"
        return ContentValidationFailed(
            errors=errors, errors_truncated=truncated, **base_kwargs
        )

    if status_code == 502 and error_code == "upstream_error":
        if not message:
            base_kwargs["message"] = "Upstream write failed"
        return UpstreamError(**base_kwargs)

    return FoxnoseAPIError(**base_kwargs)
