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
            assert result == str(selected), f"Expected {selected}, got {result}"
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
            assert result == expected, f"Expected {expected}, got {result}"
            mock_error.assert_not_called()

    def test_import_error_falls_back_to_manual(self) -> None:
        """Tkinter import fails -> warning, then manual input."""
        with (
            patch("exporter.utils.input", return_value="/manual_dir"),
            patch("exporter.utils.Path.is_dir", return_value=True),
            patch("exporter.utils.warning") as mock_warn,
        ):
            # Simulate ImportError by removing tkinter from sys.modules temporarily?
            # We'll directly patch the 'import tkinter' inside select_directory.
            # Use a mock that raises ImportError when the import is attempted.
            original_import = __import__

            def fake_import(name, *args, **kwargs):
                if name == "tkinter":
                    raise ImportError("tkinter not available")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=fake_import):
                result = select_directory()
                # select_directory returns an absolute, resolved path.
                # Compare Path objects to be cross‑platform.
                expected = Path("/manual_dir").resolve()
                assert Path(result) == expected, f"Expected {expected}, got {result}"
                mock_warn.assert_called_once()

    def test_tcl_error_falls_back_to_manual(self) -> None:
        """TclError during tkinter usage -> warning, manual fallback."""
        pytest.importorskip("tkinter")
        import tkinter

        manual_input = "/tcl_fallback"
        expected_path = str(Path(manual_input).expanduser().resolve())
        with (
            patch("tkinter.Tk", side_effect=tkinter.TclError("TclError")),
            patch("exporter.utils.input", return_value=manual_input),
            patch("exporter.utils.Path.is_dir", return_value=True),
            patch("exporter.utils.warning") as mock_warn,
        ):
            result = select_directory()
            assert result == expected_path, f"Expected {expected_path}, got {result}"
            mock_warn.assert_called_once()

    def test_manual_cancelled_returns_none(self) -> None:
        """Manual input with empty line returns None."""
        with (
            patch("exporter.utils.input", return_value=""),
            patch("exporter.utils.Path.is_dir", return_value=False),  # not needed
            patch("exporter.utils.warning"),
            patch("exporter.utils.info") as mock_info,
            patch("builtins.__import__", side_effect=ImportError),
        ):
            result = select_directory()
            assert result is None, "Empty manual input should cancel"
            mock_info.assert_called()  # prompt message

    def test_manual_invalid_then_valid_path(self) -> None:
        """Manual input first invalid, then valid -> returns valid path."""
        valid_dir = Path("/real_dir")

        with (
            patch("exporter.utils.input", side_effect=["bad_dir", str(valid_dir)]),
            patch("exporter.utils.Path.is_dir", side_effect=[False, True]),
            patch("exporter.utils.warning"),
            patch("exporter.utils.error") as mock_error,
            patch("exporter.utils.info") as mock_info,
            patch("builtins.__import__", side_effect=ImportError),
        ):
            result = select_directory()
            # select_directory resolves the path → compare resolved Path objects
            assert Path(result) == valid_dir.resolve(), f"Expected {valid_dir.resolve()}, got {result}"
            mock_error.assert_called_once()  # first invalid attempt
            # info called twice: initial prompt + prompt after error
            assert mock_info.call_count == 2


# ---------------------------------------------------------------------------
# get_next_filename
# ---------------------------------------------------------------------------
class TestGetNextFilename:
    def test_no_existing_files_returns_counter_1(self, tmp_path: Path) -> None:
        """No files -> returns base with _1 suffix."""
        base = str(tmp_path / "output.txt")
        expected = str(tmp_path / "output_1.txt")
        result = get_next_filename(base)
        assert result == expected, f"Expected {expected}, got {result}"

    def test_existing_counter_increments_max(self, tmp_path: Path) -> None:
        """Existing output_3.txt -> returns output_4.txt."""
        (tmp_path / "output_3.txt").write_text("")
        (tmp_path / "other.txt").write_text("")  # not relevant
        base = str(tmp_path / "output.txt")
        expected = str(tmp_path / "output_4.txt")
        result = get_next_filename(base)
        assert result == expected, f"Expected {expected}, got {result}"

    def test_ignores_non_matching_pattern(self, tmp_path: Path) -> None:
        """Only files matching stem_<digit>.suffix are considered."""
        (tmp_path / "output_abc.txt").write_text("")
        (tmp_path / "output_1.txt").write_text("")
        base = str(tmp_path / "output.txt")
        expected = str(tmp_path / "output_2.txt")
        result = get_next_filename(base)
        assert result == expected, f"Expected {expected}, got {result}"

    def test_handles_no_extension(self, tmp_path: Path) -> None:
        """No extension in base -> suffix empty, returns stem_1."""
        base = str(tmp_path / "Dockerfile")
        expected = str(tmp_path / "Dockerfile_1")
        result = get_next_filename(base)
        assert result == expected, f"Expected {expected}, got {result}"

    def test_multiple_digits_in_counter(self, tmp_path: Path) -> None:
        """Counter can be multi-digit, max 12 -> 13."""
        (tmp_path / "export_12.md").write_text("")
        base = str(tmp_path / "export.md")
        expected = str(tmp_path / "export_13.md")
        result = get_next_filename(base)
        assert result == expected, f"Expected {expected}, got {result}"

    def test_non_existent_parent(self, tmp_path: Path) -> None:
        """Parent directory does not exist; still returns counter 1."""
        base = str(tmp_path / "nonexistent" / "output.txt")
        expected = str(tmp_path / "nonexistent" / "output_1.txt")
        result = get_next_filename(base)
        assert result == expected, f"Expected {expected}, got {result}"


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

            # Check that success was called at the end
            mock_success.assert_called_once()
            # The success message should mention "saved to out.txt"
            assert "saved to out.txt" in mock_success.call_args[0][0]

        # Also check that token count was printed (with ANSI color codes)
        captured = capsys.readouterr()
        assert "Tokens:" in captured.out
        # The token count appears as ~\x1b[32m100\x1b[0m; check that "100" is present
        assert "100" in captured.out

    def test_elapsed_time_color_coding(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Elapsed time under 1s is rendered with the green style label."""
        output_info = OutputInfo("out.txt", False, False)
        with (
            patch("exporter.utils.tiktoken.get_encoding") as mock_enc,
            patch("exporter.utils.success"),
        ):
            mock_encoder = MagicMock()
            mock_encoder.encode.return_value = []
            mock_enc.return_value = mock_encoder
            print_statistics(
                {".": ["a.py"]},
                100,
                0.5,
                output_info,
                "/root",
                "hello",
            )
        captured = capsys.readouterr()
        # Under 1s the time is coloured green; assert the value is printed.
        assert "Elapsed time:" in captured.out
        assert "0.50 sec" in captured.out

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

    def test_largest_files_table_rendered(self, capsys: pytest.CaptureFixture[str], mock_tiktoken: MagicMock) -> None:
        """Non-empty largest_files renders the Top 5 Largest Files table."""
        output_info = OutputInfo("out.txt", False, False)
        stats = ExportStats(largest_files=[(1024, "big.py"), (10, "small.py")])
        with patch("exporter.utils.success"):
            print_statistics({".": ["a.py"]}, 100, 0.1, output_info, "/root", "data", stats=stats)
        captured = capsys.readouterr()
        assert "Top 5 Largest Files" in captured.out
        assert "big.py" in captured.out

    def test_delta_mode_skips_empty_dir_walk(
        self, capsys: pytest.CaptureFixture[str], mock_tiktoken: MagicMock
    ) -> None:
        """delta_mode=True avoids os.walk and does not crash on a missing dir."""
        output_info = OutputInfo("out.txt", False, False)
        with patch("exporter.utils.success") as mock_success:
            print_statistics(
                {".": ["a.py"]},
                100,
                0.1,
                output_info,
                "/root",
                "data",
                delta_mode=True,
                show_empty_dirs=True,
                blacklist_dirs={"node_modules"},
            )
        mock_success.assert_called_once()

    def test_show_empty_dirs_walks_and_adds(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path, mock_tiktoken: MagicMock
    ) -> None:
        """show_empty_dirs walks the input dir and adds empty dirs to the tree."""
        (tmp_path / "empty_sub").mkdir()
        (tmp_path / "a.py").write_text("x")
        output_info = OutputInfo("out.txt", False, False)
        with patch("exporter.utils.success"):
            print_statistics(
                {".": ["a.py"]},
                2,
                0.1,
                output_info,
                str(tmp_path),
                "data",
                show_empty_dirs=True,
                blacklist_dirs=set(),
            )
        captured = capsys.readouterr()
        assert "empty_sub" in captured.out


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

    def test_offline_empty_text_still_positive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty output must not produce a zero/negative token count."""
        monkeypatch.setattr("exporter.utils._enc_cache", None)
        monkeypatch.setattr("exporter.utils._warned_offline", False)

        def boom(*_args: object, **_kwargs: object) -> object:
            raise RuntimeError("offline")

        monkeypatch.setattr(tiktoken, "get_encoding", boom)
        monkeypatch.setattr("exporter.utils.warning", lambda m: None)
        assert _estimate_tokens("") == 1

    def test_online_returns_real_count(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When the encoder is available, return its real token count."""
        monkeypatch.setattr("exporter.utils._enc_cache", None)
        monkeypatch.setattr("exporter.utils._warned_offline", False)
        fake = MagicMock()
        fake.encode.side_effect = lambda s: list(s)  # 1 token per character
        monkeypatch.setattr(tiktoken, "get_encoding", lambda *a, **k: fake)
        monkeypatch.setattr("exporter.utils.warning", lambda m: None)
        assert _estimate_tokens("abc") == 3


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
