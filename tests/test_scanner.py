"""Unit tests for exporter/scanner.py."""

import pytest

from exporter.scanner import is_code_file, is_in_allowed_dirs


# ---------------------------------------------------------------------------
# helper to quickly build a config dict for scanner tests
# ---------------------------------------------------------------------------
def _make_config(**overrides):
    """Return a minimal valid scanner config with optional overrides."""
    base = {
        "blacklist_extensions": {"txt", "log"},
        "blacklist_dirs": {"__pycache__", "node_modules"},
        "blacklist_filenames": {"setup.py", "requirements.txt"},
        "filename_filter_mode": "exact",
        "allowed_extensionless_files": {"Dockerfile", "Makefile"},
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestIsCodeFile:
    def test_allowed_extension_accepted(self) -> None:
        """Not in blacklist, no size limit -> True."""
        cfg = _make_config()
        assert is_code_file("main.py", cfg) is True

    @pytest.mark.parametrize("ext", ["txt", "log"])
    def test_blacklisted_extension_rejected(self, ext: str) -> None:
        """Blacklisted extension -> False."""
        cfg = _make_config()
        filename = f"readme.{ext}"
        assert is_code_file(filename, cfg) is False, f"{ext} should be blacklisted"


class TestIsInAllowedDirs:
    def test_empty_allowed_dirs_is_unrestricted(self) -> None:
        """Empty whitelist never restricts."""
        assert is_in_allowed_dirs(".", set()) is True
        assert is_in_allowed_dirs("src", set()) is True
        assert is_in_allowed_dirs("src/deep", set()) is True

    def test_nested_whitelist_includes_deep_files(self) -> None:
        """A nested whitelist entry includes deep descendants only."""
        assert is_in_allowed_dirs("tests/unit", {"tests/unit"}) is True
        assert is_in_allowed_dirs("tests/unit/deep", {"tests/unit"}) is True
        assert is_in_allowed_dirs("tests/other", {"tests/unit"}) is False
        assert is_in_allowed_dirs("tests", {"tests/unit"}) is False
