"""
Code Export for AI - Main module.

This module provides the entry point for exporting code projects to a single file for AI review.
"""

import argparse
import importlib.util
import time
from pathlib import Path
from typing import Any

from exporter.console import error, header, info, prompt, success, warning
from exporter.processor import export_project
from exporter.utils import OutputInfo, get_next_filename, print_statistics, select_directory


def find_config_files() -> list[Path]:
    """Return a sorted list of .py config files from the 'configs/' directory.

    Excludes __init__.py and hidden files.

    Returns:
        List of Path objects, sorted alphabetically.

    """
    configs_dir = Path("configs")
    if not configs_dir.is_dir():
        return []

    config_files = [
        p for p in configs_dir.iterdir() if p.suffix == ".py" and p.name != "__init__.py" and not p.name.startswith(".")
    ]
    return sorted(config_files)


def select_config_file(requested_config: str | None) -> Path | None:
    """Determine which configuration file to use.

    Priority:
        1. If --config is provided, use that file from 'configs/' (or as absolute path).
        2. Otherwise, look inside 'configs/':
            - If exactly one .py file, use it automatically.
            - If multiple, display a numbered list and prompt the user.
        3. Fall back to root 'config.py' if 'configs/' is empty or missing.

    Args:
        requested_config: Value of the --config command-line argument.

    Returns:
        Path to the selected configuration file, or None if not found (should exit).

    """
    # 1. Explicit --config argument
    if requested_config:
        candidate = Path(requested_config)
        if candidate.is_absolute():
            if candidate.exists():
                return candidate
            error(f"Configuration file not found: {candidate}")
            return None
        # Relative: look inside configs/ first
        candidate = Path("configs") / requested_config
        if candidate.exists():
            return candidate
        # Also try as relative path from current directory
        candidate = Path(requested_config)
        if candidate.exists():
            return candidate
        error(f"Configuration file not found: {requested_config}")
        return None

    # 2. Automatic selection from configs/
    config_files = find_config_files()
    if config_files:
        if len(config_files) == 1:
            info(f"Using configuration: {config_files[0].name}")
            return config_files[0]

        # Multiple configs – prompt user
        print("\nAvailable configurations:")
        for idx, path in enumerate(config_files, start=1):
            print(f"  {idx}. {path.name}")
        while True:
            choice = prompt("Select configuration number: ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(config_files):
                    return config_files[idx]
            except ValueError:
                pass
            error("Invalid selection. Please enter a number from the list.")

    # 3. Fallback to root config.py
    root_config = Path("config.py")
    if root_config.exists():
        warning("No configurations found in 'configs/'. Falling back to root 'config.py'.")
        return root_config

    error(
        "No configuration file found. Please create 'configs/' folder with at least one .py file or 'config.py' in root."
    )
    return None


def load_config(config_path: Path) -> dict[str, Any]:
    """Dynamically load a configuration module from the given path.

    Args:
        config_path: Path to the .py configuration file.

    Returns:
        Dictionary containing the configuration values.

    Raises:
        SystemExit: If the file is missing, cannot be imported, or is incomplete.

    """
    if not config_path.exists():
        error(f"ERROR: Configuration file not found: {config_path}")
        info("Please ensure the configuration file exists.")
        input("\nPress Enter to exit...")
        raise SystemExit(1)

    # Dynamically import the module
    spec = importlib.util.spec_from_file_location("user_config", config_path)
    if spec is None or spec.loader is None:
        error(f"ERROR: Could not load configuration from {config_path}")
        input("\nPress Enter to exit...")
        raise SystemExit(1)

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        error(f"ERROR: Failed to execute configuration file: {e}")
        input("\nPress Enter to exit...")
        raise SystemExit(1)

    required_attrs = {
        "BLACKLIST_EXTENSIONS": set,
        "BLACKLIST_DIRS": set,
        "BLACKLIST_FILENAMES": set,
        "FILENAME_FILTER_MODE": str,
        "OUTPUT_DIR": str,
        "OUTPUT_FILENAME": str,
        "MAX_FILE_SIZE_MB": (int, float),
        "CREATE_FILE": bool,
        "COPY_TO_CLIPBOARD": bool,
        "INCLUDE_EMPTY_FILES": bool,
        "EXPORT_STRUCTURE": bool,
        "EXPORT_CONTENT": bool,
        "SHOW_EMPTY_DIRS": bool,
        "MAX_CLIPBOARD_CHARS": int,
        "MAX_DEPTH": int,
    }

    config_dict = {}
    for attr, expected_type in required_attrs.items():
        if not hasattr(module, attr):
            error(f"ERROR: Configuration file is missing required setting: {attr}")
            info("Please ensure the configuration contains all settings from the template.")
            input("\nPress Enter to exit...")
            raise SystemExit(1)
        value = getattr(module, attr)
        if not isinstance(value, expected_type):
            error(f"ERROR: Configuration setting {attr} has wrong type (expected {expected_type})")
            input("\nPress Enter to exit...")
            raise SystemExit(1)
        config_dict[attr.lower()] = value

    # Transform keys and values to the internal format
    config_dict["max_size"] = config_dict.pop("max_file_size_mb") * 1024 * 1024
    config_dict["output_dir"] = config_dict.pop("output_dir")
    config_dict["default_output"] = config_dict.pop("output_filename")
    config_dict["create_file"] = config_dict.pop("create_file")
    config_dict["copy_to_buffer"] = config_dict.pop("copy_to_clipboard")
    config_dict["include_empty_files"] = config_dict.pop("include_empty_files")
    config_dict["export_structure"] = config_dict.pop("export_structure")
    config_dict["export_content"] = config_dict.pop("export_content")
    config_dict["show_empty_dirs"] = config_dict.pop("show_empty_dirs")
    config_dict["max_clipboard_chars"] = config_dict.pop("max_clipboard_chars")
    config_dict["max_depth"] = config_dict.pop("max_depth")
    config_dict["blacklist_extensions"] = config_dict.pop("blacklist_extensions")
    config_dict["blacklist_dirs"] = config_dict.pop("blacklist_dirs")
    config_dict["blacklist_filenames"] = config_dict.pop("blacklist_filenames")
    config_dict["filename_filter_mode"] = config_dict.pop("filename_filter_mode")

    info(f"Configuration loaded from {config_path}")
    return config_dict


def check_export_options(config_dict: dict[str, Any], config_path: Path) -> dict[str, Any]:
    """Check and adjust export options if necessary.

    - If both file and clipboard outputs are disabled, enables file output.
    - If both structure and content exports are disabled, prompts the user
      to enable content export. If the user agrees, the configuration file is updated.

    Args:
        config_dict: Configuration dictionary.
        config_path: Path to the configuration file (needed for updating).

    Returns:
        The modified configuration dictionary, or an empty dict
        if the user chooses to exit.

    """
    create_file = config_dict["create_file"]
    copy_to_buffer = config_dict["copy_to_buffer"]

    if not create_file and not copy_to_buffer:
        create_file = True
        info("File output enabled (both outputs were disabled)")

    if not config_dict.get("export_structure", True) and not config_dict.get("export_content", True):
        warning("WARNING: Both EXPORT_STRUCTURE and EXPORT_CONTENT are disabled in configuration.")
        warning("Nothing will be exported!")
        response = (
            prompt(
                "Do you want to enable code export (EXPORT_CONTENT=True) for this run? (Press Enter for Yes, or type n and Enter to exit): "
            )
            .strip()
            .lower()
        )

        if response == "" or response.startswith("y"):
            try:
                lines = config_path.read_text(encoding="utf-8").splitlines(keepends=True)
                new_lines = []
                for line in lines:
                    if line.strip().startswith("EXPORT_CONTENT"):
                        new_lines.append("EXPORT_CONTENT = True    # Include file contents (code) in output\n")
                    else:
                        new_lines.append(line)
                config_path.write_text("".join(new_lines), encoding="utf-8")

                success(f"Updated {config_path.name}: EXPORT_CONTENT set to True permanently.")
                config_dict["export_content"] = True
                info("Continuing with code export enabled...\n")
            except OSError as e:
                error(f"Failed to update {config_path.name}: {e}")
                warning("Enabled only for this run.")
                config_dict["export_content"] = True
        else:
            warning("Exiting — no content to export.")
            return {}
    config_dict["create_file"] = create_file
    config_dict["copy_to_buffer"] = copy_to_buffer
    return config_dict


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments once."""
    parser = argparse.ArgumentParser(description="Export code project to a single file for AI review")
    parser.add_argument("-o", "--output", help="Output file name")
    parser.add_argument("-d", "--directory", help="Path to the project directory")
    parser.add_argument(
        "-c", "--config", help="Name of the configuration file (e.g., 'python.py') from the 'configs/' folder"
    )
    return parser.parse_args()


def get_input_directory(args: argparse.Namespace, *, use_args: bool = True) -> str | None:
    """
    Determine input directory based on command line arguments or user interaction.

    Args:
        args: Parsed command line arguments.
        use_args: If True and args.directory is provided, use it; otherwise ask user.

    Returns:
        Selected directory path or None if cancelled/invalid.

    """
    if use_args and args.directory:
        if Path(args.directory).is_dir():
            return args.directory
        error("The specified directory does not exist!")
        return None

    info("Select the project folder...")
    dir_path = select_directory()
    if not dir_path:
        error("No folder selected!")
    return dir_path


def get_output_filename(
    args: argparse.Namespace,
    config: dict[str, Any],
) -> str:
    """
    Determine output filename based on command line arguments and config.

    Args:
        args: Parsed command line arguments.
        config: Configuration dictionary.

    Returns:
        Output file path as string.

    """
    if args.output:
        # Use provided path, possibly prepend output_dir if relative
        path = Path(args.output)
        if not path.is_absolute():
            # Relative path: prepend output_dir from config
            base_dir = Path(config["output_dir"])
            path = base_dir / path
        return str(path)

    # No command line output specified: use OUTPUT_DIR / default_output
    base_dir = Path(config["output_dir"])
    candidate = base_dir / config["default_output"]
    # Ensure uniqueness
    return get_next_filename(str(candidate))


def perform_export(
    input_dir: str,
    output_file: str,
    config: dict[str, Any],
    *,
    create_file: bool,
    copy_to_buffer: bool,
) -> None:
    """Perform the export and print statistics."""
    info(f"Directory: {input_dir}")
    info(f"Output file: {output_file}")

    start_time = time.time()

    files_by_dir, total_chars = export_project(
        input_dir, output_file, config, create_file=create_file, copy_to_buffer=copy_to_buffer
    )

    elapsed_time = time.time() - start_time
    output_info = OutputInfo(output_file, create_file, copy_to_buffer)
    print_statistics(files_by_dir, total_chars, elapsed_time, output_info)


def main() -> None:
    __version__ = "1.2.0"
    __app_name__ = "Code Export For AI"

    header(f"{__app_name__} v{__version__}")

    args = parse_arguments()
    first_run = True

    while True:
        # 1. Choose configuration file (once per loop, may change if user restarts)
        config_path = select_config_file(args.config if first_run else None)
        if config_path is None:
            return

        # 2. Load and validate configuration
        config_dict = load_config(config_path)
        config_dict = check_export_options(config_dict, config_path)
        if not config_dict:
            return

        create_file = config_dict["create_file"]
        copy_to_buffer = config_dict["copy_to_buffer"]

        # 3. Get input directory (use command line arg only on first run)
        input_dir = get_input_directory(args, use_args=first_run)
        if not input_dir:
            return

        # 4. Determine output filename
        output_file = get_output_filename(args, config_dict)

        # 5. Perform the export
        perform_export(input_dir, output_file, config_dict, create_file=create_file, copy_to_buffer=copy_to_buffer)

        first_run = False

        # 6. Ask for restart or exit
        info("\n" + "=" * 50)
        choice = prompt("Press Enter to exit, or type 'r' to restart: ").strip().lower()
        if choice != "r":
            break
        print()


if __name__ == "__main__":
    main()
