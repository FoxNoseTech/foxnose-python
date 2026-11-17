import foxnose_sdk.management as management


def test_every_exported_name_exists():
    missing = [name for name in management.__all__ if not hasattr(management, name)]
    assert missing == []
