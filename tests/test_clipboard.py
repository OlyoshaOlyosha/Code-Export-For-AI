"""Behavioral tests for exporter/clipboard.py — public API only."""

from unittest.mock import patch

from exporter.clipboard import copy_to_clipboard


class TestCopyToClipboard:
    def test_pyperclip_succeeds_no_native(self) -> None:
        """Happy path: pyperclip available and succeeds → True, native never called."""
        with (
            patch("exporter.clipboard.HAS_PYPERCLIP", True),
            patch("exporter.clipboard.pyperclip.copy") as mock_copy,
            patch("exporter.clipboard._copy_with_native") as mock_native,
        ):
            assert copy_to_clipboard("test") is True
            mock_copy.assert_called_once()
            mock_native.assert_not_called()

    def test_both_fail(self) -> None:
        """Edge: pyperclip unavailable and native fails → False, no crash."""
        with (
            patch("exporter.clipboard.HAS_PYPERCLIP", False),
            patch("exporter.clipboard._copy_with_native", return_value=False),
        ):
            assert copy_to_clipboard("test") is False
