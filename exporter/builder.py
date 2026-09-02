"""Structure generation, output assembly, and clipboard handling for project export."""

import os
from pathlib import Path
from typing import Any

from pathspec import PathSpec

from exporter.clipboard import copy_to_clipboard
from exporter.console import success, warning
from exporter.scanner import _prune_dirs


def _generate_structure_with_empty_dirs(
    input_dir: str,
    processed_paths: set[str],
    config: dict[str, Any],
    gitignore_spec: PathSpec | None = None,
) -> str:
    """Generate project tree including all directories (even empty) from actual filesystem.

    Directories are filtered according to blacklist_dirs (hidden directories are no longer
    auto-skipped — their exclusion is governed by blacklist_dirs / .gitignore) and optionally
    .gitignore rules (via gitignore_spec).

    Only exported files (from processed_paths) are shown as leaves.

    Args:
        input_dir: Path to the input directory.
        processed_paths: Set of relative paths of exported files.
        config: Configuration dictionary with 'blacklist_dirs'.
        gitignore_spec: Compiled .gitignore patterns, or None to skip.

    Returns:
        ASCII tree string.

    """
    root_path = Path(input_dir)
    blacklist_dirs = config["blacklist_dirs"]
    allowed_dirs = config.get("allowed_dirs", set())

    # Build directory tree by walking filesystem with filtering
    dir_tree = {}  # root node representing contents of input_dir

    for root, dirs, _ in os.walk(input_dir):
        rel_root = Path(root).relative_to(input_dir).as_posix()

        # Filter directories by blacklist/gitignore rules and the allowed-dirs
        # whitelist (allowed dirs bypass the blacklist pruning).
        dirs[:] = _prune_dirs(
            dirs,
            root,
            input_dir=input_dir,
            blacklist_dirs=blacklist_dirs,
            allowed_dirs=allowed_dirs,
            gitignore_spec=gitignore_spec,
        )

        if rel_root == ".":
            # Insert first‑level directories into the tree so they show even when empty
            for d in dirs:
                if d not in dir_tree:
                    dir_tree[d] = {}
            continue

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


def _generate_structure_with_depth(
    input_dir: str,
    processed_paths: set[str],
    extra_dirs: set[str],
) -> str:
    """Generate project tree from processed files and truncated directories.

    Used when MAX_DEPTH > 0. Shows files and directories (including those
    truncated by depth limit), but not their children.

    Args:
        input_dir: Path to the project root.
        processed_paths: Relative paths of exported files.
        extra_dirs: Relative paths of directories to show (even if empty).

    Returns:
        ASCII tree string.

    """
    root = {}
    # Add files
    for rel_path in processed_paths:
        parts = rel_path.replace("\\", "/").split("/")
        current = root
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        filename = parts[-1]
        if "__files__" not in current:
            current["__files__"] = []
        current["__files__"].append(filename)

    # Add directories (placeholders)
    for rel_dir in extra_dirs:
        if not rel_dir or rel_dir == ".":
            continue
        parts = rel_dir.replace("\\", "/").split("/")
        current = root
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]
        # No files added – the directory node already exists

    # Render tree (same as original render_node)
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

    root_name = Path(input_dir).name + "/"
    lines = ["# Project Directory Structure:", root_name]
    lines.extend(render_node(root))
    return "\n".join(lines)


def generate_project_structure(
    input_dir: str,
    processed_paths: set[str],
    config: dict[str, Any],
    gitignore_spec: PathSpec | None = None,
    *,
    show_empty_dirs: bool | None = None,
) -> str:
    """Generate clean ASCII tree of the project structure based on processed relative paths.

    Args:
        input_dir: Path to the input directory.
        processed_paths: Set of relative paths that were processed.
        config: Configuration dictionary (used for show_empty_dirs flag).
        gitignore_spec: Compiled .gitignore patterns for empty-dirs mode, or None.
        show_empty_dirs: Explicit override for SHOW_EMPTY_DIRS; if None, falls back to config.

    Returns:
        A string representation of the project structure as an ASCII tree.

    """
    use_empty_dirs = show_empty_dirs if show_empty_dirs is not None else config.get("show_empty_dirs", False)

    if use_empty_dirs:
        return _generate_structure_with_empty_dirs(input_dir, processed_paths, config, gitignore_spec)

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


def build_full_output(
    input_dir: str,
    processed_paths: set[str],
    all_content: list[str],
    config: dict[str, Any],
    gitignore_spec: PathSpec | None = None,
    *,
    show_empty_dirs_override: bool | None = None,
) -> str:
    """Build the complete output: project structure (if enabled) and file contents.

    Args:
        input_dir: Path to the project root directory.
        processed_paths: Set of relative paths of processed files.
        all_content: List of strings with file contents (formatted with syntax highlighting).
        config: Configuration dictionary.
        gitignore_spec: Compiled .gitignore patterns for empty-dirs mode, or None.
        show_empty_dirs_override: If not None, overrides SHOW_EMPTY_DIRS from config.

    Returns:
        The complete output string to be written or copied.

    """
    parts: list[str] = []

    if config.get("export_structure", True):
        show_empty = (
            show_empty_dirs_override if show_empty_dirs_override is not None else config.get("show_empty_dirs", False)
        )
        structure = generate_project_structure(
            input_dir, processed_paths, config, gitignore_spec, show_empty_dirs=show_empty
        )
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


def _build_output(
    input_dir: str,
    processed_paths: set[str],
    all_content: list[str],
    extra_dirs: set[str],
    config: dict[str, Any],
    gitignore_spec: PathSpec | None = None,
    delta_since: float | None = None,
) -> str:
    """Build the final output string, respecting the configured depth limit.

    When max_depth == -1 (unlimited), the full output (with empty directories
    if configured) is generated. Otherwise (0 or positive) a depth‑aware
    structure that includes truncated directories is used.

    Args:
        input_dir: Project root path.
        processed_paths: Set of relative paths of included files.
        all_content: List of formatted file content chunks.
        extra_dirs: Directories that were truncated because of depth limit.
        config: Configuration dictionary.
        gitignore_spec: Compiled .gitignore patterns for empty-dirs mode, or None.
        delta_since: Timestamp for delta export; if set, empty directories are hidden.

    Returns:
        Complete output string (structure + contents).

    """
    max_depth = config.get("max_depth", -1)
    if max_depth == -1:
        # Unlimited depth: use the full output (respects SHOW_EMPTY_DIRS, but
        # force them off in delta mode to show only modified files)
        return build_full_output(
            input_dir,
            processed_paths,
            all_content,
            config,
            gitignore_spec=gitignore_spec,
            show_empty_dirs_override=False if delta_since is not None else None,
        )

    # Depth is limited (0 = only root, >0 = limited)
    structure = _generate_structure_with_depth(input_dir, processed_paths, extra_dirs)
    parts: list[str] = []
    if config.get("export_structure", True):
        parts.append(structure)
    if config.get("export_content", True):
        if parts:
            parts.append("\n")
        parts.append("# BEGIN FILE CONTENTS\n\n")
        parts.append("".join(all_content))
    return "".join(parts)
