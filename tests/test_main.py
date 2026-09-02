"""Unit tests for main.py module."""

import argparse
import io
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Mark all tests in this module to use the main.py module
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


# ---------------------------------------------------------------------------
# perform_export
# ---------------------------------------------------------------------------
class TestPerformExport:
    def test_calls_export_and_statistics(
        self,
        sample_config_dict: dict[str, Any],
        mock_console: dict[str, MagicMock],
        mock_clipboard: MagicMock,
    ) -> None:
        """perform_export should call export_project and print_statistics."""
        from main import perform_export

        with (
            patch("main.export_project") as mock_export,
            patch("main.print_statistics") as mock_stats,
            patch("main.time.time", side_effect=[100.0, 101.5]),
        ):
            mock_stats_obj = MagicMock()  # dummy ExportStats
            mock_export.return_value = ({"src": ["main.py"]}, 42, "full output", mock_stats_obj)
            perform_export(
                input_dir="/project",
                output_file="/out.txt",
                config=sample_config_dict,
                create_file=True,
                copy_to_buffer=False,
                delta_since=None,
            )
            mock_export.assert_called_once_with(
                "/project",
                "/out.txt",
                sample_config_dict,
                create_file=True,
                copy_to_buffer=False,
                delta_since=None,
            )
            mock_stats.assert_called_once()
            # Check output_info passed
            output_info_arg = mock_stats.call_args[0][3]
            assert output_info_arg.output_file == "/out.txt"
            assert output_info_arg.create_file is True
            assert output_info_arg.copy_to_buffer is False


# ---------------------------------------------------------------------------
# get_input_directory
# ---------------------------------------------------------------------------
class TestGetInputDirectory:
    def test_directory_arg_exists(self, tmp_path: Path) -> None:
        """-d argument points to existing directory -> return it."""
        d = tmp_path / "project"
        d.mkdir()
        args = argparse.Namespace(directory=str(d))
        from main import get_input_directory

        result = get_input_directory(args, "")
        assert result == str(d), f"Expected {d}, got {result}"


# ---------------------------------------------------------------------------
# get_output_filename
# ---------------------------------------------------------------------------
class TestGetOutputFilename:
    def test_absolute_output_arg(self, sample_config_dict: dict[str, Any]) -> None:
        """Absolute -o returns as string."""
        expected = str(Path("/absolute/path/out.txt"))
        args = argparse.Namespace(output="/absolute/path/out.txt")

        from main import get_output_filename

        result = get_output_filename(args, sample_config_dict, create_file=True)
        assert result == expected, f"Unexpected {result}"


# ---------------------------------------------------------------------------
# check_export_options
# ---------------------------------------------------------------------------
class TestCheckExportOptions:
    def test_no_changes_when_ok(self, sample_config_dict: dict[str, Any]) -> None:
        """Nothing to change -> returns same config."""
        cfg = sample_config_dict.copy()
        from main import check_export_options

        result = check_export_options(cfg)
        assert result == cfg, "Config should be unchanged"


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------
class TestLoadConfig:
    @pytest.fixture
    def valid_config_content(self) -> str:
        """Content of a valid configuration file."""
        return """
BLACKLIST_EXTENSIONS = {"txt", "md"}
BLACKLIST_DIRS = {"__pycache__"}
BLACKLIST_FILENAMES = {"setup.py"}
FILENAME_FILTER_MODE = "exact"
OUTPUT_DIR = "outputs"
OUTPUT_FILENAME = "export.txt"
MAX_FILE_SIZE_MB = 5
CREATE_FILE = True
COPY_TO_CLIPBOARD = False
INCLUDE_EMPTY_FILES = True
EXPORT_STRUCTURE = True
EXPORT_CONTENT = True
SHOW_EMPTY_DIRS = False
MAX_CLIPBOARD_CHARS = 5000
MAX_DEPTH = -1
USE_GITIGNORE = False
ALLOWED_EXTENSIONLESS_FILES = {"Dockerfile"}
"""

    def test_loads_valid_config_and_transforms_keys(self, tmp_path: Path, valid_config_content: str) -> None:
        """Valid config -> returns dict with transformed keys."""
        config_file = tmp_path / "config.py"
        config_file.write_text(valid_config_content)

        from main import load_config

        result = load_config(config_file)
        assert isinstance(result, dict), "Result should be a dict"
        assert result["output_dir"] == "outputs", "output_dir mismatch"
        assert result["default_output"] == "export.txt", "default_output mismatch"
        assert result["max_size"] == 5 * 1024 * 1024, "max_size should be 5 MB"
        assert result["create_file"] is True
        assert result["copy_to_buffer"] is False
        assert result["blacklist_extensions"] == {"txt", "md"}

    def test_minimal_config_gets_defaults(self, tmp_path: Path) -> None:
        """Config with only BLACKLIST_EXTENSIONS loads; missing settings use defaults."""
        config_file = tmp_path / "config.py"
        config_file.write_text('BLACKLIST_EXTENSIONS = {"txt"}\n')

        from main import load_config

        result = load_config(config_file)
        assert result["blacklist_extensions"] == {"txt"}
        assert result["blacklist_dirs"] == set()
        assert result["blacklist_filenames"] == set()
        assert result["filename_filter_mode"] == "exact"
        assert result["output_dir"] == "outputs"
        assert result["default_output"] == "output.txt"
        assert result["max_size"] == 5 * 1024 * 1024
        assert result["create_file"] is True
        assert result["copy_to_buffer"] is False
        assert result["include_empty_files"] is True
        assert result["export_structure"] is True
        assert result["export_content"] is True
        assert result["show_empty_dirs"] is False
        assert result["max_clipboard_chars"] == 500000
        assert result["max_depth"] == -1
        assert result["use_gitignore"] is False
        assert result["allowed_extensionless_files"] == set()
        assert result["allowed_dirs"] == set()
        assert result["input_dir"] == ""
        assert result["priority_patterns"] == []
        assert result["low_priority_patterns"] == []

    def test_wrong_typed_setting_still_exits(self, tmp_path: Path, mock_input: MagicMock) -> None:
        """Explicit wrong-typed values still print the type error and SystemExit(1)."""
        config_file = tmp_path / "config.py"
        config_file.write_text('BLACKLIST_EXTENSIONS = {"txt"}\nOUTPUT_DIR = 123\n')

        from main import load_config

        with pytest.raises(SystemExit) as exc_info:
            load_config(config_file)
        assert exc_info.value.code == 1

    def test_error_path_skips_pause_without_tty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-TTY stdin (pytest/CI/pipes): wrong-typed setting exits(1) at once, without pausing (issue #5)."""
        config_file = tmp_path / "config.py"
        config_file.write_text('BLACKLIST_EXTENSIONS = {"txt"}\nOUTPUT_DIR = 123\n')

        from main import load_config

        monkeypatch.setattr(sys, "stdin", io.StringIO())  # isatty() -> False
        with (
            patch("builtins.input") as mock_in,
            patch("main.error") as mock_error,
            pytest.raises(SystemExit) as exc_info,
        ):
            load_config(config_file)

        assert exc_info.value.code == 1
        mock_in.assert_not_called()
        assert mock_error.call_count == 1
        assert "OUTPUT_DIR has wrong type" in mock_error.call_args[0][0]


# ---------------------------------------------------------------------------
# load_app_config
# ---------------------------------------------------------------------------
class TestLoadAppConfig:
    def test_config_exists_returns_true(self, tmp_path: Path) -> None:
        config_file = tmp_path / "app_config.py"
        config_file.write_text("CHECK_FOR_UPDATES = True\n")
        with patch("main.Path", return_value=config_file):
            from main import load_app_config

            result = load_app_config()
        assert result == {"check_for_updates": True}


# ---------------------------------------------------------------------------
# _get_config_description
# ---------------------------------------------------------------------------
class TestGetConfigDescription:
    def test_simple_description(self, tmp_path: Path) -> None:
        cfg = tmp_path / "cfg.py"
        cfg.write_text('CONFIG_DESCRIPTION = "A short description"\n')
        from main import _get_config_description

        assert _get_config_description(cfg) == "A short description"


# ---------------------------------------------------------------------------
# _resolve_config_path
# ---------------------------------------------------------------------------
class TestResolveConfigPath:
    def test_inside_configs_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        configs = tmp_path / "configs"
        configs.mkdir()
        cfg = configs / "dev.py"
        cfg.touch()
        monkeypatch.chdir(tmp_path)
        from main import _resolve_config_path

        result = _resolve_config_path("dev.py")
        assert result is not None
        assert result.resolve() == cfg.resolve()


# ---------------------------------------------------------------------------
# Additional get_input_directory scenarios
# ---------------------------------------------------------------------------
class TestGetInputDirectoryAdditional:
    def test_config_input_dir_valid_used(self, tmp_path: Path) -> None:
        preset = tmp_path / "preset"
        preset.mkdir()
        args = argparse.Namespace(directory=None)
        from main import get_input_directory

        assert get_input_directory(args, str(preset)) == str(preset)


# ---------------------------------------------------------------------------
# _display_config_tree
# ---------------------------------------------------------------------------
class TestDisplayConfigTree:
    def test_empty_list_produces_no_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        from main import _display_config_tree

        _display_config_tree([])
        assert capsys.readouterr().out == ""

    def test_single_file_with_description(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        cfg = configs_dir / "test.py"
        cfg.write_text('CONFIG_DESCRIPTION = "My config"\n')
        with patch("main.Path", wraps=Path) as mock_path:
            mock_path.side_effect = lambda p: configs_dir if p == "configs" else Path(p)
            from main import _display_config_tree

            _display_config_tree([cfg])
        captured = capsys.readouterr().out
        assert "1. test" in captured
        assert "My config" in captured


# ---------------------------------------------------------------------------
# Additional perform_export checks
# ---------------------------------------------------------------------------
class TestPerformExportAdditional:
    def test_logs_directory_and_output_paths(
        self,
        sample_config_dict: dict[str, Any],
    ) -> None:
        from main import perform_export

        with (
            patch("main.info") as mock_info,
            patch("main.export_project", return_value=({}, 0, "", MagicMock())),
            patch("main.print_statistics"),
            patch("main.time.time", side_effect=[1.0, 2.0]),
        ):
            perform_export(
                input_dir="/my/project",
                output_file="/out.txt",
                config=sample_config_dict,
                create_file=False,
                copy_to_buffer=False,
            )
        info_calls = [c[0][0] for c in mock_info.call_args_list]
        assert any("Directory: /my/project" in msg for msg in info_calls)
        assert any("Output file: /out.txt" in msg for msg in info_calls)


# ---------------------------------------------------------------------------
# Minimal main() integration test
# ---------------------------------------------------------------------------
class TestMainIntegration:
    def test_single_run_exports_and_quits(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_input: MagicMock,
    ) -> None:
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        cfg = configs_dir / "test.py"
        cfg.write_text(
            "BLACKLIST_EXTENSIONS = set()\n"
            "BLACKLIST_DIRS = set()\n"
            "BLACKLIST_FILENAMES = set()\n"
            "FILENAME_FILTER_MODE = 'exact'\n"
            "OUTPUT_DIR = 'out'\n"
            "OUTPUT_FILENAME = 'out.txt'\n"
            "MAX_FILE_SIZE_MB = 5\n"
            "CREATE_FILE = True\n"
            "COPY_TO_CLIPBOARD = False\n"
            "INCLUDE_EMPTY_FILES = True\n"
            "EXPORT_STRUCTURE = True\n"
            "EXPORT_CONTENT = True\n"
            "SHOW_EMPTY_DIRS = False\n"
            "MAX_CLIPBOARD_CHARS = 5000\n"
            "MAX_DEPTH = -1\n"
            "USE_GITIGNORE = False\n"
            "ALLOWED_EXTENSIONLESS_FILES = set()\n"
        )
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("print(1)")
        monkeypatch.chdir(tmp_path)
        mock_input.side_effect = ["n"]

        with (
            patch("sys.argv", ["main.py"]),
            patch("main.check_for_updates"),
            patch("main.select_directory", return_value=str(project_dir)),
            # Patch the loop's prompt directly: main binds `prompt` at import
            # time, so a MagicMock bound by an earlier test's mock_console
            # would otherwise answer "" ("repeat export") forever.
            patch("main.prompt", return_value="n"),
            patch(
                "main.export_project",
                return_value=({".": ["main.py"]}, 100, "fake output", MagicMock()),
            ) as mock_export,
            patch("main.print_statistics"),
            patch("main.check_export_options", side_effect=lambda cfg: cfg),
        ):
            from main import main

            main()
            mock_export.assert_called_once()


# ---------------------------------------------------------------------------
# Additional main.py helper tests (argument parsing / config / input dir)
# ---------------------------------------------------------------------------
class TestMainArgHelpers:
    def test_parse_arguments_config_and_output(self) -> None:
        """--config and --output are parsed into the namespace."""
        argv = ["main.py", "--config", "foo.py", "--output", "out.txt"]
        with patch.object(sys, "argv", argv):
            from main import parse_arguments

            args = parse_arguments()
        assert args.config == "foo.py"
        assert args.output == "out.txt"

    def test_select_config_file_valid_choice(self) -> None:
        """Multiple configs + a valid numeric choice selects the matching path."""
        from main import select_config_file

        files = [Path("configs/a.py"), Path("configs/b.py")]
        with (
            patch("main.find_config_files", return_value=files),
            patch("main.prompt", return_value="2"),
            patch("main.info"),
        ):
            result = select_config_file(None)
        assert result == files[1]
