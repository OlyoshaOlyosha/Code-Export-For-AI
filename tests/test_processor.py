"""Unit tests for exporter/processor.py."""

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from exporter.processor import (
    _build_output,
    _generate_structure_with_empty_dirs,
    build_full_output,
    detect_language,
    export_project,
    handle_clipboard_copy,
    read_file_content,
)


# ---------------------------------------------------------------------------
# export_project
# ---------------------------------------------------------------------------
class TestExportProject:
    def test_oserror_during_file_write_logs_error(self, sample_config_dict: dict[str, Any], tmp_path: Path) -> None:
        """If write_output raises OSError, error is logged but does not raise."""
        config = sample_config_dict.copy()
        config["use_gitignore"] = False
        input_dir = str(tmp_path / "in")
        os.makedirs(input_dir, exist_ok=True)
        output_file = str(tmp_path / "out.txt")

        files_by_dir = {".": ["main.py"]}
        all_content: list[str] = []
        processed_paths = {"main.py"}
        extra_dirs: set[str] = set()
        full_output = "content"
        mock_stats = MagicMock()
        with (
            patch(
                "exporter.processor._collect_files",
                return_value=(files_by_dir, all_content, processed_paths, extra_dirs, mock_stats),
            ),
            patch("exporter.processor._build_output", return_value=full_output),
            patch("pathlib.Path.mkdir"),
            patch.object(Path, "write_text", side_effect=OSError("disk full")),
            patch("exporter.processor.error") as mock_error,
            patch("exporter.processor.warning") as mock_warning,
            patch("exporter.processor.handle_clipboard_copy"),
        ):
            export_project(input_dir, output_file, config, create_file=True, copy_to_buffer=False)
            mock_error.assert_called_once()
            assert "disk full" in mock_error.call_args[0][0]
            mock_warning.assert_called_once()

    def test_gitignore_warning_when_not_found(self, sample_config_dict: dict[str, Any], tmp_path: Path) -> None:
        """USE_GITIGNORE=True but no .gitignore -> warning."""
        config = sample_config_dict.copy()
        config["use_gitignore"] = True
        root = tmp_path / "proj"
        root.mkdir()
        with (
            patch("exporter.processor.warning") as mock_warn,
            patch("exporter.processor._collect_files", return_value=({}, [], set(), set(), MagicMock())),
            patch("exporter.processor._build_output", return_value=""),
            patch("exporter.processor.handle_clipboard_copy"),
        ):
            export_project(str(root), "out.txt", config, create_file=False, copy_to_buffer=False)
            mock_warn.assert_called_once()
            assert "USE_GITIGNORE is True" in mock_warn.call_args[0][0]

    def test_full_flow_with_real_gitignore(self, sample_config_dict: dict[str, Any], tmp_path: Path) -> None:
        """Integration test: project with .gitignore excludes matching files."""
        config = sample_config_dict.copy()
        config["use_gitignore"] = True
        config["export_structure"] = True
        config["export_content"] = True
        config["create_file"] = False
        config["copy_to_buffer"] = False
        config["blacklist_dirs"] = set()
        config["blacklist_extensions"] = set()
        config["blacklist_filenames"] = set()
        root = tmp_path / "repo"
        root.mkdir()
        (root / ".gitignore").write_text("*.log\ndist/\n")
        (root / "main.py").write_text("print(1)")
        (root / "debug.log").write_text("log data")
        (root / "dist").mkdir()
        (root / "dist" / "bundle.js").write_text("js")
        output_file = str(tmp_path / "out.txt")
        result = export_project(str(root), output_file, config, create_file=False, copy_to_buffer=False)
        files_by_dir, total_chars, full_output, stats = result
        # main.py should be present, .log and dist/ excluded
        assert "main.py" in str(files_by_dir), "main.py should be collected"
        assert not any("debug.log" in p for d in files_by_dir for p in files_by_dir[d])
        assert not any("dist" in p for d in files_by_dir for p in files_by_dir[d])
        # full_output should not contain .log content
        assert "log data" not in full_output
        # stats should be valid
        assert stats is not None

    def test_limited_depth_export_content_false(self) -> None:
        """max_depth=0, export_content=False -> structure only, no BEGIN FILE CONTENTS."""
        config: dict[str, Any] = {
            "max_depth": 0,
            "export_structure": True,
            "export_content": False,
        }
        extra = set()
        with patch("exporter.processor._generate_structure_with_depth", return_value="tree\n") as mock_gen:
            result = _build_output("/in", {"a.py"}, [], extra, config)
            assert "tree" in result
            assert "# BEGIN FILE CONTENTS" not in result
            mock_gen.assert_called_once_with("/in", {"a.py"}, extra)


# ---------------------------------------------------------------------------
# read_file_content edge cases
# ---------------------------------------------------------------------------
class TestReadFileContentEdge:
    def test_latin1_fallback(self, tmp_path: Path) -> None:
        """File unreadable as utf-8/cp1251 but valid latin-1 -> content returned."""
        f = tmp_path / "latin1.txt"
        # 0x98 is undefined in cp1251 but decodes under latin-1, forcing the fallback.
        f.write_bytes(b"caf\x98")
        result = read_file_content(str(f))
        assert result is not None
        assert "caf\x98" == result


# ---------------------------------------------------------------------------
# detect_language edge cases
# ---------------------------------------------------------------------------
class TestDetectLanguageEdge:
    def test_unknown_extension(self) -> None:
        assert detect_language("data.xyz") == ""


# ---------------------------------------------------------------------------
# handle_clipboard_copy edge cases (over limit)
# ---------------------------------------------------------------------------
class TestClipboardCopyEdge:
    def test_over_limit_skips_copy(self) -> None:
        """Over limit + copy requested -> False, copy_to_clipboard never called."""
        with (
            patch("exporter.processor.copy_to_clipboard") as mock_copy,
            patch("exporter.processor.warning") as mock_warn,
        ):
            result = handle_clipboard_copy("x" * 100, 100, copy_to_buffer=True, config={"max_clipboard_chars": 50})
            assert result is False
            mock_warn.assert_called_once()
            mock_copy.assert_not_called()


# ---------------------------------------------------------------------------
# build_full_output edge cases
# ---------------------------------------------------------------------------
class TestBuildFullOutput:
    def test_only_structure(self) -> None:
        config = {"export_structure": True, "export_content": False}
        out = build_full_output("/p", {"a.py"}, [], config)
        assert "# Project Directory Structure:" in out
        assert "# BEGIN FILE CONTENTS" not in out


# ---------------------------------------------------------------------------
# ALLOWED_DIRS whitelist
# ---------------------------------------------------------------------------
class TestStructureWithAllowedDirs:
    def test_allowed_hidden_dir_shown_in_tree(self, tmp_path: Path) -> None:
        """An allowed (but normally hidden) dir appears in the structure tree.

        ALLOWED_DIRS is a force-include list, not a whitelist: the allowed hidden dir
        is force-included, while other (non-blacklisted) dirs like src/ are shown too.
        """
        root = tmp_path / "proj"
        root.mkdir()
        (root / ".secret").mkdir()
        (root / ".secret" / "main.py").write_text("x")
        (root / "src").mkdir()
        (root / "src" / "app.py").write_text("y")
        config = {"blacklist_dirs": set(), "allowed_dirs": {".secret"}}
        result = _generate_structure_with_empty_dirs(str(root), {".secret/main.py", "src/app.py"}, config)
        assert ".secret/" in result, f".secret should be in tree:\n{result}"
        assert "src/" in result, f"non-allowed src should still appear (normal filtering):\n{result}"
