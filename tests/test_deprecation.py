"""Tests for the one-shot DeprecationWarning helper."""

import warnings

import pytest

from foxnose_sdk import _deprecation
from foxnose_sdk._deprecation import warn_deprecated_method


@pytest.fixture(autouse=True)
def _reset_warned():
    _deprecation._warned.clear()
    yield
    _deprecation._warned.clear()


def test_warn_emits_once_per_old_name():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        warn_deprecated_method("list_folders", "list_collections")
        warn_deprecated_method("list_folders", "list_collections")
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(deprecations) == 1
    msg = str(deprecations[0].message)
    assert "list_folders" in msg
    assert "list_collections" in msg


def test_warn_emits_once_per_distinct_method():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        warn_deprecated_method("get_folder", "get_collection")
        warn_deprecated_method("create_folder", "create_collection")
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(deprecations) == 2


def test_warn_message_mentions_removal_version():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        warn_deprecated_method("foo", "bar", removal="2.0")
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(deprecations) == 1
    assert "2.0" in str(deprecations[0].message)
