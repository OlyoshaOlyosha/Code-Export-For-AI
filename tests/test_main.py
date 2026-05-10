"""Unit tests for main.py module."""

import argparse
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Mark all tests in this module to use the main.py module
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


# ---------------------------------------------------------------------------
# find_config_files
# ---------------------------------------------------------------------------
class TestFindConfigFiles:
    def test_returns_empty_list_when_configs_dir_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Configs directory does not exist -> returns empty list."""
        monkeypatch.setattr(Path, "is_dir", lambda self: (self.name == "xyz" and self.name == "configs") or False)
        # More straightforward: patch specific Path("configs").is_dir()
        with patch("main.Path") as mock_path:
            mock_path.return_value.is_dir.return_value = False
            from main import find_config_files

            result = find_config_files()
            assert result == [], "Expected empty list when configs/ is missing"

    def test_returns_sorted_py_files_excluding_init_and_hidden(self, tmp_path: Path) -> None:
        """Only .py files, not __init__.py or hidden, sorted alphabetically."""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        (configs_dir / "b.py").touch()
        (configs_dir / "a.py").touch()
        (configs_dir / "__init__.py").touch()
        (configs_dir / ".hidden.py").touch()
        (configs_dir / "readme.md").touch()  # ignored

        with patch("main.Path", wraps=Path) as mock_path:
            mock_path.return_value = configs_dir
            from main import find_config_files

            result = find_config_files()
            expected = [configs_dir / "a.py", configs_dir / "b.py"]
            assert result == expected, f"Expected {expected}, got {result}"

    def test_handles_oserror_and_returns_empty(self) -> None:
        """When iterdir raises OSError, return [] and warn."""
        with (
            patch("main.Path") as mock_path,
            patch("main.warning") as mock_warning,
        ):
            mock_path.return_value.is_dir.return_value = True
            mock_path.return_value.iterdir.side_effect = OSError("Permission denied")
            from main import find_config_files

            result = find_config_files()
            assert result == [], "Expected empty list on OSError"
            mock_warning.assert_called_once()
            assert "Cannot read 'configs/'" in mock_warning.call_args[0][0]


# ---------------------------------------------------------------------------
# select_config_file
# ---------------------------------------------------------------------------
class TestSelectConfigFile:
    def test_explicit_absolute_path_exists(self, tmp_path: Path) -> None:
        """When --config is an absolute path that exists, return it."""
        config = tmp_path / "my_config.py"
        config.touch()
        from main import select_config_file

        result = select_config_file(str(config))
        assert result == config, f"Expected {config}, got {result}"

    def test_explicit_absolute_path_not_found(self) -> None:
        """Absolute path given but missing -> error, return None."""
        abs_path = "/nonexistent/config.py"
        with patch("main.error") as mock_error:
            from main import select_config_file

            result = select_config_file(abs_path)
            assert result is None, "Expected None for missing absolute path"
            mock_error.assert_called_once()
            assert f"Configuration file not found: {abs_path}" in mock_error.call_args[0][0]

    def test_explicit_relative_exists_in_configs(self, tmp_path: Path) -> None:
        """Relative path that exists inside configs/ -> return it."""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        config_file = configs_dir / "dev.py"
        config_file.touch()

        with patch("main.Path", wraps=Path) as mock_path:
            # Ensure Path("configs") returns tmp_path/configs
            mock_path.side_effect = lambda p, *args: Path(p) if p != "configs" else configs_dir
            from main import select_config_file

            result = select_config_file("dev.py")
            assert result == config_file, f"Expected {config_file}, got {result}"

    def test_explicit_relative_fallback_to_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Relative path not in configs but exists relative to CWD."""
        cwd_config = tmp_path / "local.py"
        cwd_config.touch()
        monkeypatch.chdir(tmp_path)

        # Ensure configs/ directory does not exist so the fallback is taken
        assert not Path("configs").exists(), "configs/ should not be present"

        from main import select_config_file

        result = select_config_file("local.py")
        assert result.resolve() == cwd_config.resolve(), f"Expected {cwd_config}, got {result}"

    def test_explicit_relative_not_found_anywhere(self) -> None:
        """Relative path not found -> error, return None."""
        with patch("main.error") as mock_error:
            from main import select_config_file

            result = select_config_file("missing.py")
            assert result is None, "Expected None for missing relative config"
            mock_error.assert_called_once()
            assert "Configuration file not found: missing.py" in mock_error.call_args[0][0]

    def test_no_explicit_config_single_config_auto_select(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Only one config -> automatically selected and info printed."""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        config_file = configs_dir / "only.py"
        config_file.touch()
        monkeypatch.chdir(tmp_path)

        with patch("main.info") as mock_info:
            from main import select_config_file

            result = select_config_file(None)
            assert result.resolve() == config_file.resolve(), f"Expected {config_file}, got {result}"
            mock_info.assert_called_once()
            assert "only.py" in mock_info.call_args[0][0]

    def test_multiple_configs_prompt_valid_choice(
        self, mock_input: MagicMock, mock_console: dict[str, MagicMock], tmp_path: Path
    ) -> None:
        """Multiple configs: user picks a valid number."""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        files = [configs_dir / "a.py", configs_dir / "b.py", configs_dir / "c.py"]
        for f in files:
            f.touch()

        mock_input.side_effect = ["2"]  # Choose b.py

        with patch("main.Path", wraps=Path) as mock_path:
            mock_path.side_effect = lambda p: configs_dir if p == "configs" else Path(p)
            from main import select_config_file

            result = select_config_file(None)
            assert result == files[1], f"Expected {files[1]}, got {result}"

    def test_multiple_configs_invalid_then_valid_choice(
        self, mock_input: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """User enters invalid choice, then valid."""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        files = [configs_dir / "x.py", configs_dir / "y.py"]
        for f in files:
            f.touch()
        monkeypatch.chdir(tmp_path)

        mock_input.side_effect = ["x", "-1", "0", "1"]

        with patch("main.error") as mock_error:
            from main import select_config_file

            result = select_config_file(None)
            assert result.resolve() == files[0].resolve(), f"Expected {files[0]}, got {result}"
            assert mock_error.call_count == 3

    def test_no_configs_fallback_to_root_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """No configs/ dir, root config.py exists -> use it."""
        root_config = tmp_path / "config.py"
        root_config.touch()
        monkeypatch.chdir(tmp_path)

        with patch("main.warning") as mock_warning:
            from main import select_config_file

            result = select_config_file(None)
            assert result.resolve() == root_config.resolve(), f"Expected {root_config}, got {result}"
            mock_warning.assert_called_once()

    def test_no_configs_no_root_config_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """No configs anywhere -> error, return None."""
        monkeypatch.chdir(tmp_path)  # tmp_path has no config.py

        with patch("main.error") as mock_error:
            from main import select_config_file

            result = select_config_file(None)
            assert result is None, "Expected None when no config found"
            mock_error.assert_called_once()


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

    def test_missing_required_attribute_causes_system_exit(self, tmp_path: Path, mock_input: MagicMock) -> None:
        """Config file missing a required attr -> SystemExit."""
        config_file = tmp_path / "bad_config.py"
        config_file.write_text("BLACKLIST_EXTENSIONS = set()\n")

        with patch("main.error") as mock_error:
            from main import load_config

            with pytest.raises(SystemExit, match="1"):
                load_config(config_file)
            mock_error.assert_called()
            mock_input.assert_called()

    def test_wrong_type_causes_system_exit(
        self, tmp_path: Path, valid_config_content: str, mock_input: MagicMock
    ) -> None:
        """Attribute with wrong type -> SystemExit."""
        # Change MAX_DEPTH to a string
        bad_content = valid_config_content.replace("MAX_DEPTH = -1", 'MAX_DEPTH = "unlimited"')
        config_file = tmp_path / "config.py"
        config_file.write_text(bad_content)

        from main import load_config

        with pytest.raises(SystemExit, match="1"):
            load_config(config_file)
        mock_input.assert_called()

    def test_max_depth_below_minus_one_exits(self, tmp_path: Path, valid_config_content: str) -> None:
        """MAX_DEPTH < -1 -> SystemExit (no input prompt)."""
        bad_content = valid_config_content.replace("MAX_DEPTH = -1", "MAX_DEPTH = -5")
        config_file = tmp_path / "config.py"
        config_file.write_text(bad_content)

        from main import load_config

        with pytest.raises(SystemExit, match="1"):
            load_config(config_file)

    def test_file_not_found_causes_system_exit(self, mock_input: MagicMock) -> None:
        """Non-existent config path -> SystemExit."""
        with patch("main.error") as mock_error:
            from main import load_config

            with pytest.raises(SystemExit, match="1"):
                load_config(Path("ghost.py"))
            mock_error.assert_called()
            mock_input.assert_called()

    def test_import_failure_spec_is_none(
        self, tmp_path: Path, valid_config_content: str, mock_input: MagicMock
    ) -> None:
        """spec_from_file_location returns None -> SystemExit."""
        config_file = tmp_path / "config.py"
        config_file.write_text(valid_config_content)
        with patch("importlib.util.spec_from_file_location", return_value=None):
            from main import load_config

            with pytest.raises(SystemExit, match="1"):
                load_config(config_file)
        mock_input.assert_called()

    def test_import_failure_exec_module_raises(
        self, tmp_path: Path, valid_config_content: str, mock_input: MagicMock
    ) -> None:
        """exec_module raises exception -> SystemExit."""
        config_file = tmp_path / "config.py"
        config_file.write_text(valid_config_content)
        with patch("importlib.util.spec_from_file_location") as mock_spec:
            mock_spec.return_value.loader = MagicMock()
            mock_spec.return_value.loader.exec_module.side_effect = ImportError("boom")
            from main import load_config

            with pytest.raises(SystemExit, match="1"):
                load_config(config_file)
        mock_input.assert_called()

    def test_defaults_for_optional_attrs(self, tmp_path: Path, mock_input: MagicMock) -> None:
        """USE_GITIGNORE and ALLOWED_EXTENSIONLESS_FILES are optional."""
        # Content without those two
        content = """
BLACKLIST_EXTENSIONS = set()
BLACKLIST_DIRS = set()
BLACKLIST_FILENAMES = set()
FILENAME_FILTER_MODE = "exact"
OUTPUT_DIR = "out"
OUTPUT_FILENAME = "out.txt"
MAX_FILE_SIZE_MB = 1
CREATE_FILE = False
COPY_TO_CLIPBOARD = False
INCLUDE_EMPTY_FILES = False
EXPORT_STRUCTURE = False
EXPORT_CONTENT = False
SHOW_EMPTY_DIRS = False
MAX_CLIPBOARD_CHARS = 0
MAX_DEPTH = 0
"""
        config_file = tmp_path / "config.py"
        config_file.write_text(content)
        from main import load_config

        result = load_config(config_file)
        assert result.get("use_gitignore") is False, "default use_gitignore should be False"
        assert result.get("allowed_extensionless_files") == set(), (
            "default allowed_extensionless_files should be empty set"
        )


# ---------------------------------------------------------------------------
# check_export_options
# ---------------------------------------------------------------------------
class TestCheckExportOptions:
    def test_both_outputs_disabled_enables_file(self, sample_config_dict: dict[str, Any]) -> None:
        """Both create_file and copy_to_buffer False -> info, set create_file True."""
        cfg = sample_config_dict.copy()
        cfg["create_file"] = False
        cfg["copy_to_buffer"] = False

        with patch("main.info") as mock_info:
            from main import check_export_options

            result = check_export_options(cfg)
            assert result["create_file"] is True, "Expected create_file to be enabled"
            mock_info.assert_called()
            assert "File output enabled" in mock_info.call_args[0][0]

    def test_both_export_flags_disabled_user_confirms(self, sample_config_dict: dict[str, Any]) -> None:
        """Both export flags False; user confirms -> export_content True."""
        cfg = sample_config_dict.copy()
        cfg["export_structure"] = False
        cfg["export_content"] = False

        with (
            patch("main.prompt", return_value="y"),
            patch("main.warning") as mock_warning,
        ):
            from main import check_export_options

            result = check_export_options(cfg)
            assert result["export_content"] is True, "Expected export_content to be enabled"
            mock_warning.assert_called()

    def test_both_export_flags_disabled_user_rejects(self, sample_config_dict: dict[str, Any]) -> None:
        """User rejects enabling content -> returns empty dict."""
        cfg = sample_config_dict.copy()
        cfg["export_structure"] = False
        cfg["export_content"] = False

        with (
            patch("main.prompt", return_value="n"),
            patch("main.warning") as mock_warning,
        ):
            from main import check_export_options

            result = check_export_options(cfg)
            assert result == {}, "Expected empty dict when user rejects"
            mock_warning.assert_called()

    def test_no_changes_when_ok(self, sample_config_dict: dict[str, Any]) -> None:
        """Nothing to change -> returns same config."""
        cfg = sample_config_dict.copy()
        from main import check_export_options

        result = check_export_options(cfg)
        assert result == cfg, "Config should be unchanged"


# ---------------------------------------------------------------------------
# parse_arguments
# ---------------------------------------------------------------------------
class TestParseArguments:
    def test_defaults(self) -> None:
        """No arguments -> output and directory and config are None."""
        with patch.object(sys, "argv", ["main.py"]):
            from main import parse_arguments

            args = parse_arguments()
            assert args.output is None
            assert args.directory is None
            assert args.config is None

    def test_all_args_short(self) -> None:
        """Short flags provided."""
        argv = ["main.py", "-o", "out.txt", "-d", "/tmp/project", "-c", "dev"]
        with patch.object(sys, "argv", argv):
            from main import parse_arguments

            args = parse_arguments()
            assert args.output == "out.txt", f"Expected 'out.txt', got {args.output}"
            assert args.directory == "/tmp/project"
            assert args.config == "dev"

    def test_all_args_long(self) -> None:
        """Long flags provided."""
        argv = ["main.py", "--output", "export.py", "--directory", "src", "--config", "prod"]
        with patch.object(sys, "argv", argv):
            from main import parse_arguments

            args = parse_arguments()
            assert args.output == "export.py"
            assert args.directory == "src"
            assert args.config == "prod"


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

        result = get_input_directory(args)
        assert result == str(d), f"Expected {d}, got {result}"

    def test_directory_arg_not_a_directory(self, tmp_path: Path) -> None:
        """-d argument is not a directory -> error, return None."""
        f = tmp_path / "file.txt"
        f.touch()
        args = argparse.Namespace(directory=str(f))

        with patch("main.error") as mock_error:
            from main import get_input_directory

            result = get_input_directory(args)
            assert result is None, "Expected None for non-directory"
            mock_error.assert_called()

    def test_no_directory_arg_select_success(self, tmp_path: Path) -> None:
        """No -d, select_directory returns a path."""
        args = argparse.Namespace(directory=None)
        selected = tmp_path / "chosen"
        selected.mkdir()

        with (
            patch("main.select_directory", return_value=str(selected)),
            patch("main.info") as mock_info,
        ):
            from main import get_input_directory

            result = get_input_directory(args)
            assert result == str(selected), f"Expected {selected}, got {result}"
            mock_info.assert_called()

    def test_no_directory_arg_select_cancelled(self) -> None:
        """No -d, select_directory returns None."""
        args = argparse.Namespace(directory=None)

        with (
            patch("main.select_directory", return_value=None),
            patch("main.error") as mock_error,
        ):
            from main import get_input_directory

            result = get_input_directory(args)
            assert result is None, "Expected None when selection cancelled"
            mock_error.assert_called()


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

    def test_relative_output_arg_prepends_output_dir(self, sample_config_dict: dict[str, Any]) -> None:
        """Relative -o is placed inside output_dir."""
        cfg = sample_config_dict.copy()
        cfg["output_dir"] = "outputs/prod"
        args = argparse.Namespace(output="result.txt")
        from main import get_output_filename

        result = get_output_filename(args, cfg, create_file=False)
        expected = str(Path("outputs/prod/result.txt"))
        assert result == expected, f"Expected {expected}, got {result}"

    def test_no_output_arg_uses_default_and_unique(
        self, sample_config_dict: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No -o, create_file=True -> calls get_next_filename."""
        cfg = sample_config_dict.copy()
        cfg["output_dir"] = "out"
        cfg["default_output"] = "export.txt"
        args = argparse.Namespace(output=None)

        with patch("main.get_next_filename") as mock_next:
            mock_next.return_value = "out/export_5.txt"
            from main import get_output_filename

            result = get_output_filename(args, cfg, create_file=True)
            mock_next.assert_called_once_with(str(Path("out/export.txt")))
            assert result == "out/export_5.txt"

    def test_no_output_arg_create_file_false(self, sample_config_dict: dict[str, Any]) -> None:
        """No -o, create_file=False -> returns candidate without uniqueness."""
        cfg = sample_config_dict.copy()
        cfg["output_dir"] = "out"
        cfg["default_output"] = "export.txt"
        args = argparse.Namespace(output=None)

        from main import get_output_filename

        result = get_output_filename(args, cfg, create_file=False)
        expected = str(Path("out/export.txt"))
        assert result == expected, f"Expected {expected}, got {result}"


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
            )
            mock_export.assert_called_once_with(
                "/project",
                "/out.txt",
                sample_config_dict,
                create_file=True,
                copy_to_buffer=False,
            )
            mock_stats.assert_called_once()
            # Check output_info passed
            output_info_arg = mock_stats.call_args[0][3]
            assert output_info_arg.output_file == "/out.txt"
            assert output_info_arg.create_file is True
            assert output_info_arg.copy_to_buffer is False
