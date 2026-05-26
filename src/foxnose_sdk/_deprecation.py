"""One-shot DeprecationWarning helpers for renamed SDK methods.

Each (old_name) is warned at most once per process. Caller-side filtering
with ``warnings.filterwarnings("error", category=DeprecationWarning)`` is
respected because we emit a standard library ``DeprecationWarning``.
"""

import warnings

_warned: set[str] = set()


def warn_deprecated_method(old_name: str, new_name: str, *, removal: str = "1.0") -> None:
    """Emit a :class:`DeprecationWarning` at most once per process per ``old_name``.

    Args:
        old_name: The method name being deprecated (e.g. ``"list_folders"``).
        new_name: The replacement method name (e.g. ``"list_collections"``).
        removal: The SDK version where the old name will be removed.
    """
    if old_name in _warned:
        return
    _warned.add(old_name)
    warnings.warn(
        f"foxnose-sdk: {old_name}() is deprecated; use {new_name}() instead. "
        f"{old_name}() will be removed in foxnose-sdk {removal}.",
        DeprecationWarning,
        stacklevel=3,
    )
