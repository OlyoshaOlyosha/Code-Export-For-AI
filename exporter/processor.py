"""Project file processing and export module.

Contains core logic: reading files, language detection for syntax highlighting,
project structure generation, and final output formatting.
"""

import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from exporter.clipboard import copy_to_clipboard
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
            print(f"Error reading {file_path}: {e}")
            return None

    print(f"Failed to read file (all encodings failed): {file_path}")
    return None


def generate_project_structure(input_dir: str, processed_paths: set[str]) -> str:
    """Generate clean ASCII tree of the project structure based on processed relative paths.

    Args:
        input_dir: Path to the input directory.
        processed_paths: Set of relative paths that were processed.

    Returns:
        A string representation of the project structure as an ASCII tree.

    """
    # Build tree from relative paths
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


def export_project(
    input_dir: str,
    output_file: str,
    config: dict[str, Any],
    *,
    create_file: bool = True,
    copy_to_buffer: bool = False,
) -> tuple[dict[str, list[str]], int]:
    """Export project: scan, filter, read, format and output project files.

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
    processed_paths = set()

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

            rel_path = os.path.relpath(file_path, input_dir)
            rel_dir = str(Path(rel_path).parent) or "."
            files_by_dir[rel_dir].append(Path(filename).name)
            processed_paths.add(rel_path)

            language = detect_language(file_path)
            lang_tag = language or ""

            chunk = f"{rel_path}:\n```{lang_tag}\n{content}\n```\n\n"
            all_content.append(chunk)

    total_chars = sum(len(chunk) for chunk in all_content)

    full_output_parts = []

    if config.get("export_structure", True):
        structure = generate_project_structure(input_dir, processed_paths)
        full_output_parts.append(structure)

    if config.get("export_content", True):
        if full_output_parts:  # Add separator if structure is present
            full_output_parts.append("\n")
        full_output_parts.append("# BEGIN FILE CONTENTS\n\n")
        full_output_parts.append("".join(all_content))

    full_output = "".join(full_output_parts)

    if create_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(full_output, encoding="utf-8")

    if copy_to_buffer and copy_to_clipboard(full_output):
        print("Content copied to clipboard")

    return files_by_dir, total_chars
