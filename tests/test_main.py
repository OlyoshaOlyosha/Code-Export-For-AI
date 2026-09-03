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

    def test_first_auto_export_gets_01_prefix(self, tmp_path: Path, sample_config_dict: dict[str, Any]) -> None:
        """Missing output directory -> counter starts at 1 (01_output.txt)."""
        sample_config_dict["output_dir"] = str(tmp_path / "outputs")
        args = argparse.Namespace(output=None)

        from main import get_output_filename

        result = get_output_filename(args, sample_config_dict, create_file=True)
        assert result == str(tmp_path / "outputs" / "01_output.txt")

    def test_auto_counter_increments(self, tmp_path: Path, sample_config_dict: dict[str, Any]) -> None:
        """Existing 01_/02_ files -> next export is 03_output.txt."""
        out_dir = tmp_path / "outputs"
        out_dir.mkdir()
        (out_dir / "01_output.txt").write_text("")
        (out_dir / "02_output.txt").write_text("")
        sample_config_dict["output_dir"] = str(out_dir)
        args = argparse.Namespace(output=None)

        from main import get_output_filename

        result = get_output_filename(args, sample_config_dict, create_file=True)
        assert result == str(out_dir / "03_output.txt")

    def test_auto_counter_per_directory_independent(self, tmp_path: Path, sample_config_dict: dict[str, Any]) -> None:
        """Each target directory has its own counter."""
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        (dir_a / "01_output.txt").write_text("")
        args = argparse.Namespace(output=None)

        from main import get_output_filename

        first = get_output_filename(args, {**sample_config_dict, "output_dir": str(dir_a)}, create_file=True)
        second = get_output_filename(args, {**sample_config_dict, "output_dir": str(dir_b)}, create_file=True)
        assert first == str(dir_a / "02_output.txt")
        assert second == str(dir_b / "01_output.txt")

    def test_auto_counter_ignores_old_suffix_files(self, tmp_path: Path, sample_config_dict: dict[str, Any]) -> None:
        """Old-scheme output_1.txt and unrelated files do not affect the prefix counter."""
        out_dir = tmp_path / "outputs"
        out_dir.mkdir()
        (out_dir / "output_1.txt").write_text("")
        (out_dir / "notes.txt").write_text("")
        sample_config_dict["output_dir"] = str(out_dir)
        args = argparse.Namespace(output=None)

        from main import get_output_filename

        result = get_output_filename(args, sample_config_dict, create_file=True)
        assert result == str(out_dir / "01_output.txt")

    def test_auto_counter_escapes_regex_special_stem(self, tmp_path: Path, sample_config_dict: dict[str, Any]) -> None:
        """Stem with regex-special chars is matched literally."""
        out_dir = tmp_path / "outputs"
        out_dir.mkdir()
        (out_dir / "01_report[1].txt").write_text("")
        cfg = {**sample_config_dict, "output_dir": str(out_dir), "default_output": "report[1].txt"}
        args = argparse.Namespace(output=None)

        from main import get_output_filename

        result = get_output_filename(args, cfg, create_file=True)
        assert result == str(out_dir / "02_report[1].txt")

    def test_create_file_false_keeps_plain_name(self, tmp_path: Path, sample_config_dict: dict[str, Any]) -> None:
        """create_file=False -> plain default name without prefix."""
        sample_config_dict["output_dir"] = str(tmp_path / "outputs")
        args = argparse.Namespace(output=None)

        from main import get_output_filename

        result = get_output_filename(args, sample_config_dict, create_file=False)
        assert result == str(tmp_path / "outputs" / "output.txt")

    def test_output_arg_relative_keeps_exact_name(self, tmp_path: Path, sample_config_dict: dict[str, Any]) -> None:
        """Relative -o name kept verbatim when the target does not exist."""
        sample_config_dict["output_dir"] = str(tmp_path / "outputs")
        args = argparse.Namespace(output="myreport.txt")

        from main import get_output_filename

        result = get_output_filename(args, sample_config_dict, create_file=True)
        assert result == str(tmp_path / "outputs" / "myreport.txt")

    def test_output_arg_collision_falls_back_to_suffix(
        self, tmp_path: Path, sample_config_dict: dict[str, Any]
    ) -> None:
        """Existing -o target -> _1 fallback instead of overwrite."""
        out_dir = tmp_path / "outputs"
        out_dir.mkdir()
        (out_dir / "myreport.txt").write_text("")
        sample_config_dict["output_dir"] = str(out_dir)
        args = argparse.Namespace(output="myreport.txt")

        from main import get_output_filename

        result = get_output_filename(args, sample_config_dict, create_file=True)
        assert result == str(out_dir / "myreport_1.txt")

    def test_output_arg_with_directory_collision(self, tmp_path: Path, sample_config_dict: dict[str, Any]) -> None:
        """-o with subdirectories: collision resolved inside that parent."""
        sub = tmp_path / "outputs" / "sub"
        sub.mkdir(parents=True)
        (sub / "rep.txt").write_text("")
        sample_config_dict["output_dir"] = str(tmp_path / "outputs")
        args = argparse.Namespace(output="sub/rep.txt")

        from main import get_output_filename

        result = get_output_filename(args, sample_config_dict, create_file=True)
        assert result == str(sub / "rep_1.txt")


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
# get_input_directory — non-interactive stdin guard (issue #8)
# ---------------------------------------------------------------------------
class TestGetInputDirectoryNonInteractive:
    def test_no_preset_returns_empty_without_picker(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-TTY stdin, no -d and no INPUT_DIR -> "" via error, no Tkinter (issue #8)."""
        args = argparse.Namespace(directory=None)
        from main import get_input_directory

        monkeypatch.setattr(sys, "stdin", io.StringIO())  # isatty() -> False
        with (
            patch("tkinter.Tk") as mock_tk,  # must never be constructed in headless runs
            patch("main.select_directory") as mock_select,
            patch("main.error") as mock_error,
        ):
            result = get_input_directory(args, "")

        assert result == ""
        mock_select.assert_not_called()
        mock_tk.assert_not_called()
        assert mock_error.call_count == 1
        assert "No input directory could be resolved" in mock_error.call_args[0][0]

    def test_missing_preset_returns_empty_without_picker(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-TTY stdin + INPUT_DIR pointing to a missing path -> "" without picker (issue #8)."""
        args = argparse.Namespace(directory=None)
        from main import get_input_directory

        monkeypatch.setattr(sys, "stdin", io.StringIO())
        with (
            patch("tkinter.Tk") as mock_tk,
            patch("main.select_directory") as mock_select,
            patch("main.error") as mock_error,
        ):
            result = get_input_directory(args, str(tmp_path / "missing"))

        assert result == ""
        mock_select.assert_not_called()
        mock_tk.assert_not_called()
        assert mock_error.call_count == 1

    def test_interactive_stdin_still_uses_picker(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Interactive stdin -> picker behaviour unchanged, its value is returned."""
        args = argparse.Namespace(directory=None)
        from main import get_input_directory

        interactive_stdin = MagicMock()
        interactive_stdin.isatty.return_value = True
        monkeypatch.setattr(sys, "stdin", interactive_stdin)
        with patch("main.select_directory", return_value="/picked/dir") as mock_select:
            result = get_input_directory(args, "")

        mock_select.assert_called_once_with()
        assert result == "/picked/dir"


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
        # Issue #8: the folder picker now requires an interactive stdin, which
        # pytest does not provide — simulate a TTY for this integration run.
        interactive_stdin = MagicMock()
        interactive_stdin.isatty.return_value = True
        monkeypatch.setattr(sys, "stdin", interactive_stdin)

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
# --version / --dry-run flags (issue #9)
# ---------------------------------------------------------------------------
class TestParseArgumentsFlags:
    def test_version_constants_are_module_level(self) -> None:
        """Version constants live at module level, not inside main()."""
        import main

        assert main.__app_name__ == "Project2Prompt"
        assert main.__version__ == "1.4.0"

    def test_version_flag_prints_and_exits_zero(self, capsys: pytest.CaptureFixture[str]) -> None:
        """--version prints the version string and exits via SystemExit(0)."""
        from main import parse_arguments

        with (
            patch.object(sys, "argv", ["main.py", "--version"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            parse_arguments()

        assert exc_info.value.code == 0
        assert "Project2Prompt v1.4.0" in capsys.readouterr().out

    def test_dry_run_flag_parses_true(self) -> None:
        """--dry-run is exposed as args.dry_run."""
        from main import parse_arguments

        with patch.object(sys, "argv", ["main.py", "--dry-run"]):
            args = parse_arguments()

        assert args.dry_run is True

    def test_dry_run_flag_defaults_to_false(self) -> None:
        """Without --dry-run, args.dry_run is False."""
        from main import parse_arguments

        with patch.object(sys, "argv", ["main.py"]):
            args = parse_arguments()

        assert args.dry_run is False


class TestMainDryRunIntegration:
    def test_dry_run_scans_without_writing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_input: MagicMock,
    ) -> None:
        """--dry-run exports with create_file=False/copy_to_buffer=False despite CREATE_FILE=True (issue #9)."""
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
        # Simulate a TTY for this integration run (same pattern as TestMainIntegration).
        interactive_stdin = MagicMock()
        interactive_stdin.isatty.return_value = True
        monkeypatch.setattr(sys, "stdin", interactive_stdin)

        with (
            patch("sys.argv", ["main.py", "--dry-run", "-d", str(project_dir)]),
            patch("main.check_for_updates"),
            patch("main.prompt", return_value="n"),
            patch(
                "main.export_project",
                return_value=({".": ["main.py"]}, 100, "fake output", MagicMock()),
            ) as mock_export,
            patch("main.print_statistics"),
        ):
            from main import main

            main()

        mock_export.assert_called_once()
        assert mock_export.call_args.kwargs["create_file"] is False
        assert mock_export.call_args.kwargs["copy_to_buffer"] is False
        # create_file=False skips the two-digit counter prefix.
        assert mock_export.call_args.args[1] == str(Path("out") / "test" / "out.txt")
        # Nothing was written anywhere under the temp workspace.
        assert list(tmp_path.rglob("*.txt")) == []


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
