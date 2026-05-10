"""Utility functions for project export.

This module provides helper functions for directory selection, filename generation,
and statistics printing.
"""

from dataclasses import dataclass
from pathlib import Path

import tiktoken
from rich.tree import Tree

from exporter.console import console, error, info, success, warning


def select_directory() -> str | None:
    """Prompt for a project directory via GUI or console fallback.

    First attempts a tkinter folder selection dialog. If tkinter is not available
    or fails, falls back to manual console input.

    Returns:
        The selected directory path or None if no selection was made.

    """
    # Attempt GUI selection
    folder_path = None
    try:
        import tkinter as tk  # noqa: PLC0415
        from tkinter import filedialog  # noqa: PLC0415
    except ImportError as e:
        warning(f"GUI folder selection unavailable: {e}")
    else:
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            folder_path = filedialog.askdirectory(title="Select project folder")
            root.destroy()
        except tk.TclError as e:
            warning(f"GUI folder selection unavailable: {e}")

    if folder_path:
        return folder_path

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

    Scans the parent directory once to find the highest existing numeric suffix,
    then returns the next number.

    Args:
        base_name: The base file path (e.g., "outputs/config/output.txt").

    Returns:
        A unique file path with a numeric suffix (e.g., "outputs/config/output_1.txt").

    """
    path = Path(base_name)
    parent = path.parent
    stem = path.stem
    suffix = path.suffix

    # Scan directory once to find the maximum existing counter
    max_counter = 0
    pattern = f"{stem}_"
    if parent.exists():
        for existing in parent.iterdir():
            name = existing.name
            if name.startswith(pattern) and name.endswith(suffix):
                # Extract the numeric part between pattern and suffix
                middle = name[len(pattern) : -len(suffix)]
                if middle.isdigit():
                    max_counter = max(max_counter, int(middle))

    counter = max_counter + 1
    return str(parent / f"{stem}_{counter}{suffix}")


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
    input_dir: str,
    full_output: str,
) -> None:
    """Print formatted statistics after export.

    Uses Rich to render a colour‑coded file tree and to decorate metrics.
    """
    num_dirs = len(files_by_dir)
    num_files = sum(len(files) for files in files_by_dir.values())
    root_name = Path(input_dir).name

    enc = tiktoken.get_encoding("o200k_base")
    token_count = len(enc.encode(full_output))

    if total_chars >= 1024 * 1024:
        size_str = f"{total_chars / (1024 * 1024):.2f} MB"
    else:
        size_str = f"{total_chars / 1024:.1f} KB"

    info("\n=== STATISTICS ===")

    # Elapsed time colour thresholds
    time_style = "green" if elapsed_time < 1.0 else ("yellow" if elapsed_time < 5.0 else "red")
    info(f"Elapsed time: [{time_style}]{elapsed_time:.2f} sec[/]")

    info(f"Characters: {total_chars:,} ({size_str})")

    # Token colour thresholds
    context_limit = 128_000
    percentage = (token_count / context_limit) * 100
    if percentage < 50:
        token_style = "green"
    elif percentage < 80:
        token_style = "yellow"
    elif percentage < 95:
        token_style = "bright_yellow"
    else:
        token_style = "red"
    info(f"Tokens: ~[{token_style}]{token_count:,}[/] / {context_limit:,} ({percentage:.1f}%)")

    info(f"📁 Directories: {num_dirs}")
    info(f"📄 Files: {num_files}")

    # Build a Rich Tree from the files_by_dir mapping
    info("\nFiles by directory:")

    tree = Tree(f"[blue]{root_name}/[/]", guide_style="bold bright_blue")
    # Keep track of already‑created directory nodes keyed by their relative path.
    dir_nodes: dict[str, Tree] = {".": tree}

    for rel_dir in sorted(files_by_dir):
        if rel_dir == ".":
            parent_node = tree
        else:
            parts = rel_dir.split("/")
            accumulated = ""
            parent_node = tree
            for part in parts:
                accumulated = f"{accumulated}/{part}" if accumulated else part
                if accumulated not in dir_nodes:
                    dir_node = parent_node.add(f"[blue]{part}/[/]")
                    dir_nodes[accumulated] = dir_node
                parent_node = dir_nodes[accumulated]
            # parent_node is now the node for rel_dir

        for filename in sorted(files_by_dir[rel_dir]):
            parent_node.add(filename)

    console.print(tree)

    # Final result line
    result_parts = []
    if output_info.create_file:
        result_parts.append(f"saved to {output_info.output_file}")
    if output_info.copy_to_buffer:
        result_parts.append("copied to clipboard")

    success(f"\nDone! Result: {' and '.join(result_parts)}")
