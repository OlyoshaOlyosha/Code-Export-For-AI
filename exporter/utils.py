"""Utility functions for project export.

This module provides helper functions for directory selection, filename generation,
and statistics printing.
"""

from dataclasses import dataclass
from pathlib import Path

from exporter.console import info, success


def select_directory() -> str | None:
    """Prompt for a project directory via GUI or console fallback.

    First attempts a tkinter folder selection dialog. If tkinter is not available
    or fails, falls back to manual console input.

    Returns:
        The selected directory path or None if no selection was made.

    """
    # Attempt GUI selection
    try:
        import tkinter as tk  # noqa: PLC0415
        from tkinter import filedialog  # noqa: PLC0415

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder_path = filedialog.askdirectory(title="Select project folder")
        root.destroy()
        if folder_path:
            return folder_path
    except (ImportError, tk.TclError) as e:
        # tkinter not installed or cannot connect to display
        warning(f"GUI folder selection unavailable: {e}")

    # Fallback to manual input
    info("Please enter the project directory path manually:")
    while True:
        user_input = input("Path: ").strip()
        if not user_input:
            return None
        path = Path(user_input).expanduser().resolve()
        if path.is_dir():
            return str(path)
        error(f"Directory does not exist or is not accessible: {path}")
        info("Press Enter to cancel or try again.")


def get_next_filename(base_name: str) -> str:
    """Generate a unique filename by always appending a sequential number.

    The first candidate is `{stem}_1{suffix}`. If it already exists,
    increments the number until an unused name is found.

    Args:
        base_name: The base file path (e.g., "outputs/config/output.txt").

    Returns:
        A unique file path with a numeric suffix (e.g., "outputs/config/output_1.txt").

    """
    path = Path(base_name)
    parent = path.parent
    stem = path.stem
    suffix = path.suffix

    counter = 1
    while True:
        new_name = parent / f"{stem}_{counter}{suffix}"
        if not new_name.exists():
            return str(new_name)
        counter += 1


@dataclass
class OutputInfo:
    """Information about output destination and actions."""

    output_file: str
    create_file: bool
    copy_to_buffer: bool


def print_statistics(
    files_by_dir: dict[str, list[str]],
    total_chars: int,
    elapsed_time: float,
    output_info: OutputInfo,
) -> None:
    """Print formatted statistics after export.

    Args:
        files_by_dir: Dictionary mapping directories to lists of files.
        total_chars: Total number of characters in the exported content.
        elapsed_time: Time taken for the export process.
        output_info: OutputInfo object containing output file and flags.

    """
    num_dirs = len(files_by_dir)
    num_files = sum(len(files) for files in files_by_dir.values())

    info("\n=== STATISTICS ===")
    info(f"Elapsed time: {elapsed_time:.2f} sec")
    info(f"Characters: {total_chars:,} ({total_chars / 1024:.1f} KB)")
    info(f"Directories: {num_dirs}")
    info(f"Files: {num_files}")

    info("\nFiles by directory:")
    for dir_path in sorted(files_by_dir.keys()):
        files = files_by_dir[dir_path]
        info(f"  {dir_path}: {len(files)} - {', '.join(files)}")

    result_parts = []
    if output_info.create_file:
        result_parts.append(f"saved to {output_info.output_file}")
    if output_info.copy_to_buffer:
        result_parts.append("copied to clipboard")

    success(f"\nDone! Result: {' and '.join(result_parts)}")
