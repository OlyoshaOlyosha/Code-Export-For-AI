"""Project file processing and export module.

Contains core logic: reading files, language detection for syntax highlighting,
project structure generation, and final output formatting.
"""

import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from exporter.clipboard import copy_to_clipboard
from exporter.console import error, success, warning
from exporter.scanner import is_code_file

# Default mapping from file extension to language tag for code fences
# Used as fallback when Pygments is not available or fails
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    "py": "python",
    "pyw": "python",
    "js": "javascript",
    "mjs": "javascript",
    "cjs": "javascript",
    "ts": "typescript",
    "jsx": "jsx",
    "tsx": "tsx",
    "java": "java",
    "c": "c",
    "h": "c",
    "cpp": "cpp",
    "cc": "cpp",
    "cxx": "cpp",
    "hpp": "cpp",
    "cs": "csharp",
    "go": "go",
    "rs": "rust",
    "rb": "ruby",
    "php": "php",
    "sh": "bash",
    "bash": "bash",
    "ps1": "powershell",
    "psm1": "powershell",
    "psd1": "powershell",
    "html": "html",
    "htm": "html",
    "css": "css",
    "json": "json",
    "yml": "yaml",
    "yaml": "yaml",
    "xml": "xml",
    "sql": "sql",
    "md": "markdown",
    "markdown": "markdown",
    "dockerfile": "dockerfile",
    "makefile": "makefile",
    "txt": "",
    "ini": "ini",
    "toml": "toml",
    "gradle": "groovy",
    "groovy": "groovy",
    "dart": "dart",
    "kt": "kotlin",
    "kts": "kotlin",
    "scala": "scala",
    "jl": "julia",
    "r": "r",
    "swift": "swift",
    "erl": "erlang",
    "hs": "haskell",
}


def read_file_content(file_path: str) -> str | None:
    """Read file content with fallback encodings.

    Args:
        file_path: Path to the file to read.

    Returns:
        The file content as a string, or None if reading failed.

    """
    path = Path(file_path)
    encodings = ["utf-8", "cp1251", "latin-1"]

    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        except OSError as e:
            error(f"Error reading {file_path}: {e}")
            return None

    error(f"Failed to read file (all encodings failed): {file_path}")
    return None


def _generate_structure_with_empty_dirs(input_dir: str, processed_paths: set[str], config: dict[str, Any]) -> str:
    """Generate project tree including all directories (even empty) from actual filesystem.

    Directories are filtered according to blacklist_dirs and hidden directories (starting with '.').
    Only exported files (from processed_paths) are shown as leaves.

    Args:
        input_dir: Path to the input directory.
        processed_paths: Set of relative paths of exported files.
        config: Configuration dictionary with 'blacklist_dirs'.

    Returns:
        ASCII tree string.

    """
    root_path = Path(input_dir)
    blacklist_dirs = config["blacklist_dirs"]

    # Build directory tree by walking filesystem with filtering
    dir_tree = {}  # root node representing contents of input_dir

    for root, dirs, _ in os.walk(input_dir):
        # Filter dirs in-place: skip hidden and blacklisted
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in blacklist_dirs]

        rel_root = os.path.relpath(root, input_dir)
        if rel_root == ".":
            continue  # root directory itself is represented by dir_tree

        # Ensure all parent directories exist in the tree
        parts = Path(rel_root).parts
        current = dir_tree
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]

    # Add files from processed_paths
    for rel_path in processed_paths:
        # Normalize separators to '/'
        norm_parts = rel_path.replace("\\", "/").split("/")
        filename = norm_parts[-1]
        dir_parts = norm_parts[:-1]

        current = dir_tree
        for part in dir_parts:
            # Directory should exist from walk, but if not (e.g., due to edge cases), create it
            if part not in current:
                current[part] = {}
            current = current[part]

        if "__files__" not in current:
            current["__files__"] = []
        current["__files__"].append(filename)

    def render_node(node: dict, prefix: str = "") -> list[str]:
        lines = []
        dirs = [k for k in node if k != "__files__"]
        files = sorted(node.get("__files__", []))

        pointers = ["├── "] * (len(dirs) + len(files) - 1) + (["└── "] if dirs + files else [])

        for i, name in enumerate(sorted(dirs) + files):
            pointer = pointers[i]
            is_dir = name in dirs
            line = f"{prefix}{pointer}{name}/" if is_dir else f"{prefix}{pointer}{name}"
            lines.append(line)

            if is_dir:
                extension = "    " if pointer == "└── " else "│   "
                lines.extend(render_node(node[name], prefix + extension))

        return lines

    root_name = root_path.name + "/"
    lines = ["# Project Directory Structure:", root_name]
    lines.extend(render_node(dir_tree))
    return "\n".join(lines)


def generate_project_structure(input_dir: str, processed_paths: set[str], config: dict[str, Any]) -> str:
    """Generate clean ASCII tree of the project structure based on processed relative paths.

    Args:
        input_dir: Path to the input directory.
        processed_paths: Set of relative paths that were processed.

    Returns:
        A string representation of the project structure as an ASCII tree.

    """
    if config.get("show_empty_dirs", False):
        return _generate_structure_with_empty_dirs(input_dir, processed_paths, config)

    # Original method (without empty dirs)
    root = {}
    for rel_path in sorted(processed_paths):
        parts = rel_path.replace("\\", "/").split("/")  # normalize slashes
        current = root
        for part in parts[:-1]:  # directories
            if part not in current:
                current[part] = {}
            current = current[part]
        # leaf is file
        filename = parts[-1]
        if "__files__" not in current:
            current["__files__"] = []
        current["__files__"].append(filename)

    def render_node(node: dict, prefix: str = "") -> list[str]:
        lines = []
        # Get directories and files
        dirs = [k for k in node if k != "__files__"]
        files = sorted(node.get("__files__", []))

        pointers = ["├── "] * (len(dirs) + len(files) - 1) + (["└── "] if dirs + files else [])

        for i, name in enumerate(sorted(dirs) + files):
            pointer = pointers[i]
            is_dir = name in dirs
            line = f"{prefix}{pointer}{name}/" if is_dir else f"{prefix}{pointer}{name}"
            lines.append(line)

            if is_dir:
                extension = "    " if pointer == "└── " else "│   "
                lines.extend(render_node(node[name], prefix + extension))

        return lines

    root_name = Path(input_dir).name + "/"
    lines = ["# Project Directory Structure:", root_name]
    lines.extend(render_node(root))
    return "\n".join(lines)


def detect_language(file_path: str) -> str:
    """Detect language tag for syntax highlighting based on file extension."""
    ext = Path(file_path).suffix.lower().lstrip(".")
    return EXTENSION_LANGUAGE_MAP.get(ext, "")


def build_full_output(
    input_dir: str,
    processed_paths: set[str],
    all_content: list[str],
    config: dict[str, Any],
) -> str:
    """Build the complete output: project structure (if enabled) and file contents.

    Args:
        input_dir: Path to the project root directory.
        processed_paths: Set of relative paths of processed files.
        all_content: List of strings with file contents (formatted with syntax highlighting).
        config: Configuration dictionary.

    Returns:
        The complete output string to be written or copied.

    """
    parts: list[str] = []

    if config.get("export_structure", True):
        structure = generate_project_structure(input_dir, processed_paths, config)
        parts.append(structure)

    if config.get("export_content", True):
        if parts:  # Add a separator if structure is present
            parts.append("\n")
        parts.append("# BEGIN FILE CONTENTS\n\n")
        parts.append("".join(all_content))

    return "".join(parts)


def handle_clipboard_copy(
    full_output: str,
    total_chars: int,
    *,
    copy_to_buffer: bool,
    config: dict[str, Any],
) -> bool:
    """Handle clipboard copying with character limit enforcement.

    Args:
        full_output: Text to be copied.
        total_chars: Number of characters in the text.
        copy_to_buffer: Flag indicating whether copying is requested.
        config: Configuration dictionary.

    Returns:
        True if copying was performed (or not needed), False if skipped due to limit or failure.

    """
    if not copy_to_buffer:
        return False

    max_chars = config.get("max_clipboard_chars", 0)
    if max_chars > 0 and total_chars > max_chars:
        warning(
            f"WARNING: Clipboard copy skipped — output size ({total_chars} chars) exceeds "
            f"MAX_CLIPBOARD_CHARS={max_chars}.\n"
            "To disable this limit, set MAX_CLIPBOARD_CHARS = 0 in config.py"
        )
        return False

    if copy_to_clipboard(full_output):
        success("Content copied to clipboard")
        return True
    return False


def export_project(
    input_dir: str,
    output_file: str,
    config: dict[str, Any],
    *,
    create_file: bool = True,
    copy_to_buffer: bool = False,
) -> tuple[dict[str, list[str]], int]:
    """Export project: scan, filter, read, and produce output.

    Args:
        input_dir: Path to the input directory.
        output_file: Path to the output file.
        config: Configuration dictionary.
        create_file: Whether to create the output file.
        copy_to_buffer: Whether to copy the output to clipboard.

    Returns:
        A tuple containing a dictionary of files by directory and total character count.

    """
    files_by_dir = defaultdict(list)
    all_content: list[str] = []
    processed_paths: set[str] = set()

    for root, dirs, files in os.walk(input_dir):
        # In-place filter directories
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in config["blacklist_dirs"]]

        for filename in files:
            file_path = str(Path(root) / filename)

            if not is_code_file(file_path, config):
                continue

            content = read_file_content(file_path)
            if content is None:
                continue

            if not config.get("include_empty_files", True) and content == "":
                continue

            rel_path = os.path.relpath(file_path, input_dir)
            rel_dir = str(Path(rel_path).parent) or "."
            files_by_dir[rel_dir].append(Path(filename).name)
            processed_paths.add(rel_path)

            if content != "":
                language = detect_language(file_path)
                lang_tag = language or ""
                chunk = f"{rel_path}:\n```{lang_tag}\n{content}\n```\n\n"
                all_content.append(chunk)

    total_chars = sum(len(chunk) for chunk in all_content)
    full_output = build_full_output(input_dir, processed_paths, all_content, config)

    if create_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(full_output, encoding="utf-8")

    handle_clipboard_copy(full_output, total_chars, copy_to_buffer=copy_to_buffer, config=config)
    return files_by_dir, total_chars
