"""
Code Export for AI - Main module.

This module provides the entry point for exporting code projects to a single file for AI review.
"""

import argparse
import time
from pathlib import Path
from typing import Any

from exporter.console import error, header, info, prompt, success, warning
from exporter.processor import export_project
from exporter.utils import OutputInfo, get_next_filename, print_statistics, select_directory

try:
    import config
except ImportError:
    config = None


def load_config() -> dict[str, Any]:
    """Load configuration from config.py.

    Returns:
        Dict[str, Any]: Configuration dictionary.

    Raises:
        SystemExit: If config.py is missing or incomplete.

    """
    if config is None:
        error("ERROR: config.py not found!")
        info("Please copy config.py from the repository: https://github.com/OlyoshaOlyosha/Code-Export-For-AI")
        info("The tool requires proper configuration to filter out binaries, vendor folders, etc.")
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
    }

    config_dict = {}
    for attr, expected_type in required_attrs.items():
        if not hasattr(config, attr):
            error(f"ERROR: config.py is missing required setting: {attr}")
            info("Please ensure your config.py contains all settings from the template.")
            input("\nPress Enter to exit...")
            raise SystemExit(1)
        value = getattr(config, attr)
        if not isinstance(value, expected_type):
            error(f"ERROR: config.py setting {attr} has wrong type (expected {expected_type})")
            input("\nPress Enter to exit...")
            raise SystemExit(1)
        config_dict[attr.lower()] = value

    # Special handling for max_size
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
    config_dict["blacklist_extensions"] = config_dict.pop("blacklist_extensions")
    config_dict["blacklist_dirs"] = config_dict.pop("blacklist_dirs")
    config_dict["blacklist_filenames"] = config_dict.pop("blacklist_filenames")
    config_dict["filename_filter_mode"] = config_dict.pop("filename_filter_mode")

    info("Configuration loaded from config.py")
    return config_dict


def check_export_options(config: dict[str, Any]) -> dict[str, Any]:
    """Check and adjust export options if necessary.

    - If both file and clipboard outputs are disabled, enables file output.
    - If both structure and content exports are disabled, prompts the user
      to enable content export. If the user agrees, the config file is updated.

    Args:
        config: Configuration dictionary.

    Returns:
        The modified configuration dictionary, or an empty dict
        if the user chooses to exit.

    """
    create_file = config["create_file"]
    copy_to_buffer = config["copy_to_buffer"]

    if not create_file and not copy_to_buffer:
        create_file = True
        info("File output enabled (both outputs were disabled)")

    if not config.get("export_structure", True) and not config.get("export_content", True):
        warning("WARNING: Both EXPORT_STRUCTURE and EXPORT_CONTENT are disabled in config.py.")
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
                config_path = Path("config.py")
                lines = config_path.read_text(encoding="utf-8").splitlines(keepends=True)
                new_lines = []
                for line in lines:
                    if line.strip().startswith("EXPORT_CONTENT"):
                        new_lines.append("EXPORT_CONTENT = True    # Include file contents (code) in output\n")
                    else:
                        new_lines.append(line)
                config_path.write_text("".join(new_lines), encoding="utf-8")

                success("Updated config.py: EXPORT_CONTENT set to True permanently.")
                config["export_content"] = True
                info("Continuing with code export enabled...\n")
            except OSError as e:
                error(f"Failed to update config.py: {e}")
                warning("Enabled only for this run.")
                config["export_content"] = True
        else:
            warning("Exiting — no content to export.")
            return {}
    config["create_file"] = create_file
    config["copy_to_buffer"] = copy_to_buffer
    return config


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments once."""
    parser = argparse.ArgumentParser(description="Export code project to a single file for AI review")
    parser.add_argument("-o", "--output", help="Output file name")
    parser.add_argument("-d", "--directory", help="Path to the project directory")
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
    __version__ = "1.1.0"
    __app_name__ = "Code Export For AI"

    header(f"{__app_name__} v{__version__}")

    args = parse_arguments()  # Parse command line arguments once
    first_run = True

    while True:
        # Reload config on each iteration to pick up external changes
        config_dict = load_config()
        config_dict = check_export_options(config_dict)
        if not config_dict:
            return

        create_file = config_dict["create_file"]
        copy_to_buffer = config_dict["copy_to_buffer"]

        # Get input directory (use command line arg only on first run)
        input_dir = get_input_directory(args, use_args=first_run)
        if not input_dir:
            return

        # Get output filename based on command line arguments and config
        output_file = get_output_filename(args, config_dict)

        perform_export(input_dir, output_file, config_dict, create_file=create_file, copy_to_buffer=copy_to_buffer)

        # After first run, subsequent iterations will ignore command line arguments
        first_run = False

        # Ask user whether to exit or start a new export
        info("\n" + "=" * 50)
        choice = prompt("Press Enter to exit, or type 'r' to restart: ").strip().lower()
        if choice != "r":
            break
        print()  # empty line for better readability


if __name__ == "__main__":
    main()
