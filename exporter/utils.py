"""Utility functions for project export.

This module provides helper functions for directory selection, filename generation,
and statistics printing.
"""

from dataclasses import dataclass
from pathlib import Path

import tiktoken

from exporter.console import Fore, Style, error, info, success, warning


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


def _build_file_tree(files_by_dir: dict[str, list[str]], root_name: str) -> str:
    """Build an ASCII tree representation of files grouped by directory.

    Args:
        files_by_dir: Mapping from relative directory paths to lists of filenames.
        root_name: Name of the project root directory.

    Returns:
        A string containing the formatted tree.

    """
    # Build nested dictionary structure
    tree: dict = {}
    for rel_dir, filenames in files_by_dir.items():
        # Normalize path separators and handle root '.' case
        if rel_dir == ".":
            parts = []
        else:
            parts = rel_dir.replace("\\", "/").split("/")
        current = tree
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]
        current["__files__"] = sorted(filenames)

    def render_node(node: dict, prefix: str = "") -> list[str]:
        lines = []
        dirs = [k for k in node if k != "__files__"]
        files = node.get("__files__", [])
        items = sorted(dirs) + files
        if not items:
            return lines

        pointers = ["├── "] * (len(items) - 1) + (["└── "] if items else [])
        for i, name in enumerate(items):
            pointer = pointers[i]
            is_dir = name in dirs
            line = f"{prefix}{pointer}{name}{'/' if is_dir else ''}"
            lines.append(line)
            if is_dir:
                extension = "    " if pointer == "└── " else "│   "
                lines.extend(render_node(node[name], prefix + extension))
        return lines

    root_line = f"{root_name}/"
    lines = [root_line]
    lines.extend(render_node(tree))
    return "\n".join(lines)


def print_statistics(
    files_by_dir: dict[str, list[str]],
    total_chars: int,
    elapsed_time: float,
    output_info: OutputInfo,
    input_dir: str,
    full_output: str,
) -> None:
    """Print formatted statistics after export.

    Args:
        files_by_dir: Dictionary mapping directories to lists of files.
        total_chars: Total number of characters in the exported content.
        elapsed_time: Time taken for the export process.
        output_info: OutputInfo object containing output file and flags.
        input_dir: Path to the project root directory (used for tree label).
        full_output: The complete exported text (used for token counting).

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

    if elapsed_time < 1.0:
        time_color = Fore.GREEN
    elif elapsed_time < 5.0:
        time_color = Fore.YELLOW
    else:
        time_color = Fore.RED
    info(f"Elapsed time: {time_color}{elapsed_time:.2f} sec{Style.RESET_ALL}")

    info(f"Characters: {total_chars:,} ({size_str})")

    CONTEXT_LIMIT = 128_000  # tokens
    percentage = (token_count / CONTEXT_LIMIT) * 100
    if percentage < 50:
        token_color = Fore.GREEN
    elif percentage < 80:
        token_color = Fore.YELLOW
    elif percentage < 95:
        token_color = Fore.LIGHTYELLOW_EX
    else:
        token_color = Fore.RED
    info(f"Tokens: ~{token_color}{token_count:,}{Style.RESET_ALL} / {CONTEXT_LIMIT:,} ({percentage:.1f}%)")

    info(f"📁 Directories: {num_dirs}")
    info(f"📄 Files: {num_files}")

    info("\nFiles by directory:")

    tree_output = _build_file_tree(files_by_dir, root_name)
    for line in tree_output.splitlines():
        if line.rstrip().endswith("/"):
            last_slash_idx = line.rfind("/")
            if last_slash_idx != -1:
                name_start = 0
                for i, ch in enumerate(line):
                    if ch not in (" ", "├", "└", "│", "─"):
                        name_start = i
                        break
                prefix = line[:name_start]
                name_with_slash = line[name_start:]
                if name_with_slash.endswith("/"):
                    name_only = name_with_slash[:-1]
                    slash = "/"
                else:
                    name_only = name_with_slash
                    slash = ""
                print(f"{prefix}{Fore.BLUE}{name_only}{Style.RESET_ALL}{slash}")
            else:
                print(f"{Fore.BLUE}{line}{Style.RESET_ALL}")
        else:
            print(line)

    result_parts = []
    if output_info.create_file:
        result_parts.append(f"saved to {output_info.output_file}")
    if output_info.copy_to_buffer:
        result_parts.append("copied to clipboard")

    success(f"\nDone! Result: {' and '.join(result_parts)}")
