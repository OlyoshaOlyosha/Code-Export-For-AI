"""Unit tests for exporter/utils.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import tiktoken

from exporter.utils import (
    ExportStats,
    OutputInfo,
    _estimate_tokens,
    get_next_filename,
    print_statistics,
    select_directory,
)


# ---------------------------------------------------------------------------
# select_directory
# ---------------------------------------------------------------------------
class TestSelectDirectory:
    def test_gui_returns_selected_folder(self, tmp_path: Path) -> None:
        """Tkinter dialog returns a path -> returned as string."""
        selected = tmp_path / "selected_folder"
        selected.mkdir()

        with (
            patch("tkinter.Tk") as mock_tk,
            patch("tkinter.filedialog.askdirectory", return_value=str(selected)),
        ):
            result = select_directory()
            assert result == str(selected)
            mock_tk.return_value.withdraw.assert_called()
            mock_tk.return_value.destroy.assert_called()

    def test_gui_returns_empty_string_cancels(self) -> None:
        """Tkinter returns empty string -> falls back to manual input."""
        manual_input = "/valid_dir"
        expected = str(Path(manual_input).expanduser().resolve())
        with (
            patch("tkinter.Tk"),
            patch("tkinter.filedialog.askdirectory", return_value=""),
            patch("exporter.utils.input", side_effect=[manual_input]),
            patch("exporter.utils.Path.is_dir", return_value=True),
            patch("exporter.utils.warning"),
            patch("exporter.utils.error") as mock_error,
        ):
            result = select_directory()
            assert result == expected
            mock_error.assert_not_called()


# ---------------------------------------------------------------------------
# get_next_filename
# ---------------------------------------------------------------------------
class TestGetNextFilename:
    def test_no_existing_files_returns_counter_1(self, tmp_path: Path) -> None:
        """No files -> returns base with _1 suffix."""
        base = str(tmp_path / "output.txt")
        expected = str(tmp_path / "output_1.txt")
        result = get_next_filename(base)
        assert result == expected

    def test_existing_counter_increments_max(self, tmp_path: Path) -> None:
        """Existing output_3.txt -> returns output_4.txt."""
        (tmp_path / "output_3.txt").write_text("")
        (tmp_path / "other.txt").write_text("")  # not relevant
        base = str(tmp_path / "output.txt")
        expected = str(tmp_path / "output_4.txt")
        result = get_next_filename(base)
        assert result == expected


# ---------------------------------------------------------------------------
# print_statistics
# ---------------------------------------------------------------------------
class TestPrintStatistics:
    def test_outputs_all_sections(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Full statistics printed with mocked tiktoken and console."""
        files_by_dir = {"src": ["main.py"], "tests": ["test_main.py"]}
        total_chars = 5000
        elapsed_time = 1.2
        output_info = OutputInfo(output_file="out.txt", create_file=True, copy_to_buffer=False)
        input_dir = "/project"
        full_output = "some content"

        with (
            patch("exporter.utils.tiktoken.get_encoding") as mock_enc,
            patch("exporter.utils.success") as mock_success,
        ):
            mock_encoder = MagicMock()
            mock_encoder.encode.return_value = [0] * 100  # 100 tokens
            mock_enc.return_value = mock_encoder

            print_statistics(
                files_by_dir,
                total_chars,
                elapsed_time,
                output_info,
                input_dir,
                full_output,
            )

            mock_success.assert_called_once()
            assert "saved to out.txt" in mock_success.call_args[0][0]

        captured = capsys.readouterr()
        assert "Tokens:" in captured.out
        assert "100" in captured.out

    def test_file_size_mb_when_large(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Characters >= 1 MB displayed in MB."""
        output_info = OutputInfo("big.txt", False, False)
        total_chars = 2 * 1024 * 1024  # 2 MB
        with (
            patch("exporter.utils.tiktoken.get_encoding") as mock_enc,
            patch("exporter.utils.success"),
        ):
            mock_encoder = MagicMock()
            mock_encoder.encode.return_value = []
            mock_enc.return_value = mock_encoder
            print_statistics(
                {".": ["large.bin"]},
                total_chars,
                0.1,
                output_info,
                "/root",
                "data",
            )
        captured = capsys.readouterr()
        assert "2.00 MB" in captured.out


# ---------------------------------------------------------------------------
# print_statistics — extended coverage
# ---------------------------------------------------------------------------
class TestPrintStatisticsExtended:
    def test_skip_counters_printed_when_nonzero(
        self, capsys: pytest.CaptureFixture[str], mock_tiktoken: MagicMock
    ) -> None:
        """Non-zero skip counters each produce a printed line."""
        output_info = OutputInfo("out.txt", False, False)
        stats = ExportStats(skipped_binary=2, skipped_size=3, skipped_rules=1)
        with patch("exporter.utils.success"):
            print_statistics({".": ["a.py"]}, 100, 0.1, output_info, "/root", "data", stats=stats)
        captured = capsys.readouterr()
        assert "Binary / unreadable: 2" in captured.out
        assert "Exceeded size limit: 3" in captured.out
        assert "Excluded by rules: 1" in captured.out

    def test_extension_counts_table_rendered(
        self, capsys: pytest.CaptureFixture[str], mock_tiktoken: MagicMock
    ) -> None:
        """Non-empty extension_counts renders the Top Extensions table."""
        output_info = OutputInfo("out.txt", False, False)
        stats = ExportStats(extension_counts={"py": 4, "js": 1})
        with patch("exporter.utils.success"):
            print_statistics({".": ["a.py"]}, 100, 0.1, output_info, "/root", "data", stats=stats)
        captured = capsys.readouterr()
        assert "Top Extensions" in captured.out
        assert "py" in captured.out


# ---------------------------------------------------------------------------
# _estimate_tokens — offline resilience
# ---------------------------------------------------------------------------
class TestEstimateTokens:
    def test_offline_returns_positive_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When get_encoding raises, fall back to ~4 chars/token (>=1)."""
        monkeypatch.setattr("exporter.utils._enc_cache", None)
        monkeypatch.setattr("exporter.utils._warned_offline", False)

        def boom(*_args: object, **_kwargs: object) -> object:
            raise RuntimeError("offline")

        monkeypatch.setattr(tiktoken, "get_encoding", boom)
        warnings: list[str] = []
        monkeypatch.setattr("exporter.utils.warning", lambda m: warnings.append(m))

        assert _estimate_tokens("hello world this is a test") >= 1
        assert warnings, "offline should warn exactly once"
        # Second call must not warn again and must stay positive.
        assert _estimate_tokens("x") >= 1
        assert len(warnings) == 1


# ---------------------------------------------------------------------------
# print_statistics — token logic offline/online
# ---------------------------------------------------------------------------
class TestPrintStatisticsTokens:
    def test_offline_does_not_crash_and_warns(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Offline: print_statistics runs, prints a token line, warns once."""
        monkeypatch.setattr("exporter.utils._enc_cache", None)
        monkeypatch.setattr("exporter.utils._warned_offline", False)

        def boom(*_args: object, **_kwargs: object) -> object:
            raise RuntimeError("offline")

        monkeypatch.setattr(tiktoken, "get_encoding", boom)
        warnings: list[str] = []
        monkeypatch.setattr("exporter.utils.warning", lambda m: warnings.append(m))

        output_info = OutputInfo("out.txt", False, False)
        print_statistics({".": ["a.py"]}, 100, 0.1, output_info, "/root", "hello world this is content")

        captured = capsys.readouterr()
        assert "Tokens:" in captured.out
        assert warnings, "offline path should warn once"

    def test_online_uses_real_count(self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
        """Online: token count comes from the encoder (3 chars -> 3 tokens)."""
        monkeypatch.setattr("exporter.utils._enc_cache", None)
        monkeypatch.setattr("exporter.utils._warned_offline", False)
        fake = MagicMock()
        fake.encode.side_effect = lambda s: list(s)
        monkeypatch.setattr(tiktoken, "get_encoding", lambda *a, **k: fake)
        monkeypatch.setattr("exporter.utils.warning", lambda m: None)

        output_info = OutputInfo("out.txt", False, False)
        print_statistics({".": ["a.py"]}, 100, 0.1, output_info, "/root", "abc")

        captured = capsys.readouterr()
        assert "3" in captured.out
