"""
Code Export for AI - Main module.

This module provides the entry point for exporting code projects to a single file for AI review.
"""

import argparse
import importlib.util
import time
from pathlib import Path
from typing import Any

from exporter.console import error, header, info, prompt, warning
from exporter.processor import export_project
from exporter.utils import OutputInfo, get_next_filename, print_statistics, select_directory


def find_config_files() -> list[Path]:
    """Return a sorted list of .py config files from the 'configs/' directory.

    Excludes __init__.py and hidden files.

    Returns:
        List of Path objects, sorted alphabetically. Returns empty list on error.

    """
    configs_dir = Path("configs")
    if not configs_dir.is_dir():
        return []

    try:
        config_files = [
            p
            for p in configs_dir.iterdir()
            if p.suffix == ".py" and p.name != "__init__.py" and not p.name.startswith(".")
        ]
    except OSError as e:
        warning(f"Cannot read 'configs/' directory: {e}")
        return []

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
        "USE_GITIGNORE": bool,
        "ALLOWED_EXTENSIONLESS_FILES": set,
    }

    config_dict = {}
    for attr, expected_type in required_attrs.items():
        if not hasattr(module, attr):
            # Provide defaults for optional settings (backward compatibility)
            if attr in ("USE_GITIGNORE", "ALLOWED_EXTENSIONLESS_FILES"):
                default = False if attr == "USE_GITIGNORE" else set()
                config_dict[attr.lower()] = default
                continue
            error(f"ERROR: Configuration file is missing required setting: {attr}")
            info("Please ensure the configuration contains all settings from the template.")
            input("\nPress Enter to exit...")
            raise SystemExit(1)
        value = getattr(module, attr)
        if not isinstance(value, expected_type):
            error(f"ERROR: Configuration setting {attr} has wrong type (expected {expected_type})")
            input("\nPress Enter to exit...")
            raise SystemExit(1)
        if attr == "MAX_DEPTH" and value < -1:
            error(
                f"ERROR: MAX_DEPTH is set to {value}. Valid range: -1 (unlimited), 0 (root only), or positive integer."
            )
            info("Please fix the value in your configuration file (MAX_DEPTH must be -1, 0, or a positive integer).")
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


def check_export_options(config_dict: dict[str, Any]) -> dict[str, Any]:
    """Check and adjust export options for the current run.

    - If both file and clipboard outputs are disabled, enables file output.
    - If both structure and content exports are disabled, prompts the user
      to enable content export for this session only (no file modification).

    Args:
        config_dict: Configuration dictionary.

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
            config_dict["export_content"] = True
            info("Content export enabled for this run.\n")
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


def get_input_directory(args: argparse.Namespace) -> str | None:
    """
    Determine input directory based on command line arguments or user interaction.

    Args:
        args: Parsed command line arguments.

    Returns:
        Selected directory path or None if cancelled/invalid.

    """
    if args.directory:
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
    *,
    create_file: bool,
) -> str:
    """
    Determine output filename based on command line arguments and config.

    Args:
        args: Parsed command line arguments.
        config: Configuration dictionary.
        create_file: Whether the file will actually be written (skips uniqueness check if False).

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

    # Only generate a unique filename if we actually intend to create the file
    if create_file:
        return get_next_filename(str(candidate))
    return str(candidate)


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

    files_by_dir, total_chars, full_output = export_project(
        input_dir, output_file, config, create_file=create_file, copy_to_buffer=copy_to_buffer
    )

    elapsed_time = time.time() - start_time
    output_info = OutputInfo(output_file, create_file, copy_to_buffer)
    print_statistics(files_by_dir, total_chars, elapsed_time, output_info, input_dir, full_output)


def main() -> None:
    __version__ = "1.3.0"
    __app_name__ = "Code Export For AI"

    try:
        header(f"{__app_name__} v{__version__}")

        args = parse_arguments()

        # 1. Choose configuration file
        config_path = select_config_file(args.config)
        if config_path is None:
            input("\nPress Enter to exit...")
            return

        # 2. Load and validate configuration
        config_dict = load_config(config_path)

        # Append configuration name (without .py) to output directory
        config_stem = config_path.stem
        base_output = Path(config_dict["output_dir"])
        config_dict["output_dir"] = str(base_output / config_stem)

        config_dict = check_export_options(config_dict)
        if not config_dict:
            input("\nPress Enter to exit...")
            return

        create_file = config_dict["create_file"]
        copy_to_buffer = config_dict["copy_to_buffer"]

        # 3. Get input directory (use command line arg if provided)
        input_dir = get_input_directory(args)
        if not input_dir:
            input("\nPress Enter to exit...")
            return

        # 4. Determine output filename
        output_file = get_output_filename(args, config_dict, create_file=create_file)

        # 5. Perform the export
        perform_export(input_dir, output_file, config_dict, create_file=create_file, copy_to_buffer=copy_to_buffer)

        input("\nPress Enter to exit...")
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        return


if __name__ == "__main__":
    main()
