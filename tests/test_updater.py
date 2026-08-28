"""Unit tests for exporter/updater.py."""

import json
from unittest.mock import MagicMock, patch

import pytest
from exporter.updater import _parse_version, check_for_updates


# ---------------------------------------------------------------------------
# _parse_version
# ---------------------------------------------------------------------------
class TestParseVersion:
    def test_normal_version(self) -> None:
        assert _parse_version("1.4.0") == (1, 4, 0)

    def test_non_numeric_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_version("1.x.0")


# ---------------------------------------------------------------------------
# check_for_updates
# ---------------------------------------------------------------------------
def _make_urlopen(json_str: str) -> MagicMock:
    """Build a mock urllib.request.urlopen returning the given JSON body."""
    mock_urlopen = MagicMock()
    context = MagicMock()
    response = MagicMock()
    response.read.return_value.decode.return_value = json_str
    context.__enter__.return_value = response
    mock_urlopen.return_value = context
    return mock_urlopen


class TestCheckForUpdates:
    def test_newer_version_warns(self) -> None:
        """A newer GitHub release triggers a 'new version' warning."""
        mock_urlopen = _make_urlopen(json.dumps({"tag_name": "v1.5.0"}))
        with (
            patch("exporter.updater.urllib.request.urlopen", mock_urlopen),
            patch("exporter.updater.warning") as mock_warn,
        ):
            check_for_updates("1.4.0")
        mock_warn.assert_called_once()
        assert "1.5.0" in mock_warn.call_args[0][0]

    def test_same_or_older_version_no_warning(self) -> None:
        """Equal or older latest version does not warn about a new version."""
        mock_urlopen = _make_urlopen(json.dumps({"tag_name": "v1.4.0"}))
        with (
            patch("exporter.updater.urllib.request.urlopen", mock_urlopen),
            patch("exporter.updater.warning") as mock_warn,
        ):
            check_for_updates("1.4.0")
        mock_warn.assert_not_called()

    def test_missing_tag_name_warns(self) -> None:
        """Response without tag_name -> warning about missing tag."""
        mock_urlopen = _make_urlopen(json.dumps({}))
        with (
            patch("exporter.updater.urllib.request.urlopen", mock_urlopen),
            patch("exporter.updater.warning") as mock_warn,
        ):
            check_for_updates("1.4.0")
        mock_warn.assert_called_once()
        assert "missing tag" in mock_warn.call_args[0][0]

    def test_url_error_warns_without_raising(self) -> None:
        """Network URLError/HTTPError is reported, not raised."""
        import urllib.error

        mock_urlopen = MagicMock(side_effect=urllib.error.URLError("boom"))
        with (
            patch("exporter.updater.urllib.request.urlopen", mock_urlopen),
            patch("exporter.updater.warning") as mock_warn,
        ):
            check_for_updates("1.4.0")
        mock_warn.assert_called_once()

    def test_json_decode_error_warns_without_raising(self) -> None:
        """Malformed JSON response is reported, not raised."""
        mock_urlopen = _make_urlopen("not valid json")
        with (
            patch("exporter.updater.urllib.request.urlopen", mock_urlopen),
            patch("exporter.updater.warning") as mock_warn,
        ):
            check_for_updates("1.4.0")
        mock_warn.assert_called_once()

    def test_version_parse_error_warns_without_raising(self) -> None:
        """A non-numeric tag version is reported, not raised."""
        mock_urlopen = _make_urlopen(json.dumps({"tag_name": "v1.x.0"}))
        with (
            patch("exporter.updater.urllib.request.urlopen", mock_urlopen),
            patch("exporter.updater.warning") as mock_warn,
        ):
            check_for_updates("1.4.0")
        mock_warn.assert_called_once()
