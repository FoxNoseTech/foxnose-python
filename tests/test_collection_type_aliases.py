"""Verify Collection* type aliases point at the original Folder* types.

Aliases are re-exported from both the ``foxnose_sdk.management`` subpackage
and the top-level ``foxnose_sdk`` package — the test covers both surfaces so
the next person who adds a new alias notices if they only wire half the path.
"""

import foxnose_sdk
from foxnose_sdk.management import (
    APICollectionList,
    APICollectionSummary,
    CollectionList,
    CollectionRef,
    CollectionSummary,
    FolderRef,
)
from foxnose_sdk.management.models import (
    APIFolderList,
    APIFolderSummary,
    FolderList,
    FolderSummary,
)


def test_collection_summary_is_folder_summary():
    assert CollectionSummary is FolderSummary


def test_collection_list_is_folder_list():
    assert CollectionList is FolderList


def test_api_collection_summary_alias():
    assert APICollectionSummary is APIFolderSummary


def test_api_collection_list_alias():
    assert APICollectionList is APIFolderList


def test_collection_ref_alias():
    assert CollectionRef is FolderRef


def test_top_level_package_reexports_collection_types():
    """Aliases must also be importable from the top-level ``foxnose_sdk``."""
    assert foxnose_sdk.CollectionSummary is FolderSummary
    assert foxnose_sdk.CollectionList is FolderList
    assert foxnose_sdk.APICollectionSummary is APIFolderSummary
    assert foxnose_sdk.APICollectionList is APIFolderList
    assert foxnose_sdk.CollectionRef is FolderRef


def test_version_string_matches_pyproject():
    """Drift check between pyproject.toml and __version__."""
    assert foxnose_sdk.__version__ == "0.6.0"
