"""Project file processing and export module.

Contains core logic: reading files, language detection for code‑fence tags,
project structure generation, and final output formatting.
"""

import os
import re
from collections import defaultdict
from fnmatch import translate as fnmatch_translate
from pathlib import Path
from typing import Any

from exporter.clipboard import copy_to_clipboard
from exporter.console import error, success, warning
from exporter.scanner import is_code_file

# Default mapping from file extension to language tag for code fences
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    # ==================== Python ====================
    "py": "python",
    "pyw": "python",
    # ==================== JavaScript / TypeScript ====================
    "js": "javascript",
    "mjs": "javascript",
    "cjs": "javascript",
    "ts": "typescript",
    "jsx": "jsx",
    "tsx": "tsx",
    # ==================== Java / C / C++ / C# ====================
    "java": "java",
    "c": "c",
    "h": "c",
    "cpp": "cpp",
    "cc": "cpp",
    "cxx": "cpp",
    "hpp": "cpp",
    "cs": "csharp",
    # ==================== Rust / Go / Ruby / PHP ====================
    "rs": "rust",
    "rb": "ruby",
    "php": "php",
    # ==================== Shell & Scripting ====================
    "sh": "bash",
    "bash": "bash",
    "ps1": "powershell",
    "psm1": "powershell",
    "psd1": "powershell",
    "pl": "perl",
    "pm": "perl",
    "t": "perl",
    "cgi": "perl",
    "awk": "awk",
    "sed": "sed",
    "bat": "batch",
    "cmd": "batch",
    "ahk": "autohotkey",
    # ==================== Web (HTML / CSS) ====================
    "html": "html",
    "htm": "html",
    "css": "css",
    "scss": "scss",
    "sass": "sass",
    "less": "less",
    "styl": "stylus",
    # ==================== Markup & Documentation ====================
    "md": "markdown",
    "mdx": "mdx",
    "rst": "rst",
    "asciidoc": "asciidoc",
    "adoc": "asciidoc",
    "latex": "latex",
    "tex": "latex",
    "bib": "bibtex",
    # ==================== Data & Configuration ====================
    "yml": "yaml",
    "yaml": "yaml",
    "json": "json",
    "xml": "xml",
    "toml": "toml",
    "ini": "ini",
    "conf": "ini",
    "cfg": "ini",
    "config": "ini",
    "properties": "properties",
    "csv": "csv",
    "tsv": "tsv",
    "log": "log",
    "env": "env",
    "txt": "text",
    # ==================== Infrastructure & Build ====================
    "dockerfile": "dockerfile",
    "makefile": "makefile",
    "tf": "hcl",
    "tfvars": "hcl",
    "hcl": "hcl",
    "nix": "nix",
    "cmake": "cmake",
    "gradle": "groovy",
    "groovy": "groovy",
    # ==================== Database & Query Languages ====================
    "sql": "sql",
    "graphql": "graphql",
    "gql": "graphql",
    "proto": "protobuf",
    "thrift": "thrift",
    # ==================== Functional & Other Languages ====================
    "ex": "elixir",
    "exs": "elixir",
    "eex": "elixir",
    "heex": "elixir",
    "clj": "clojure",
    "cljs": "clojure",
    "cljc": "clojure",
    "erl": "erlang",
    "hs": "haskell",
    "fs": "fsharp",
    "fsi": "fsharp",
    "fsx": "fsharp",
    "jl": "julia",
    "nim": "nim",
    "zig": "zig",
    "crystal": "crystal",
    "elm": "elm",
    "purs": "purescript",
    "d": "d",
    # ==================== Frontend Frameworks ====================
    "svelte": "svelte",
    "vue": "vue",
    "astro": "astro",
    # ==================== Assembly & Low-level ====================
    "asm": "asm",
    "s": "asm",
    # ==================== .NET & Visual Basic ====================
    "vb": "vbnet",
    "vbs": "vbnet",
    # ==================== Ignore Files ====================
    "dockerignore": "dockerignore",
    "gitignore": "gitignore",
    "editorconfig": "editorconfig",
    # ==================== Other ====================
    "jinja": "jinja",
    "j2": "jinja",
    "prisma": "prisma",
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
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in blacklist_dirs]

        rel_root = Path(root).relative_to(input_dir).as_posix()
        if rel_root == ".":
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


def generate_project_structure(input_dir: str, processed_paths: set[str], config: dict[str, Any]) -> str:
    """Generate clean ASCII tree of the project structure based on processed relative paths.

    Args:
        input_dir: Path to the input directory.
        processed_paths: Set of relative paths that were processed.
        config: Configuration dictionary (used for show_empty_dirs flag).

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
    """Detect language tag for code fences based on file extension."""
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


class GitignoreParser:
    """Parse .gitignore rules and test paths against them."""

    def __init__(self, gitignore_path: Path, root_dir: Path) -> None:
        """Read and compile patterns from a .gitignore file.

        Args:
            gitignore_path: Path to the .gitignore file.
            root_dir: Root directory of the project (for relative path calculation).

        """
        self.root_dir = root_dir.resolve()
        self.patterns: list[tuple[re.Pattern, bool]] = []  # (regex, is_negation)

        if not gitignore_path.is_file():
            return

        try:
            lines = gitignore_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return

        for raw_line in lines:
            line = raw_line.rstrip("\r\n")
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            is_negation = False
            if line.startswith("!"):
                is_negation = True
                line = line[1:]

            # Remove trailing spaces (not allowed in patterns)
            line = line.rstrip()

            # Handle directory indicator (trailing slash)
            # For matching we treat it as "this pattern only applies to directories"
            # but our simple implementation treats paths uniformly.
            line = line.removesuffix("/")

            # Convert gitignore pattern to regex
            regex = self._pattern_to_regex(line)
            self.patterns.append((re.compile(regex), is_negation))

    @staticmethod
    def _pattern_to_regex(pattern: str) -> str:
        """Convert a gitignore pattern to a regular expression."""
        # If pattern contains '/', it's anchored to the directory containing .gitignore
        # Otherwise it matches anywhere in the path.
        if "/" in pattern and not pattern.startswith("**/"):
            # Anchored relative to gitignore location
            anchored = True
        else:
            anchored = False

        # Handle leading "**/"
        if pattern.startswith("**/"):
            pattern = pattern[3:]
            anchored = False  # "**/" means any number of directories

        # Convert glob pattern to regex using fnmatch, then adjust
        # fnmatch.translate uses '(?s:...)\Z' – we strip the end anchor and add our own.
        parts = pattern.split("/")
        regex_parts = []
        for part in parts:
            if part == "**":
                regex_parts.append(r"(?:.*/)?")
            else:
                # Escape then translate glob
                part_regex = fnmatch_translate(part)
                # fnmatch_translate returns '(?s:pattern)\Z'
                # Strip the '(?s:' prefix and ')\Z' suffix
                if part_regex.startswith("(?s:") and part_regex.endswith(")\\Z"):
                    part_regex = part_regex[4:-3]
                else:
                    # Fallback: just escape special regex chars except *
                    part_regex = re.escape(part).replace(r"\*", ".*")
                regex_parts.append(part_regex)

        joined = "/".join(regex_parts)

        if anchored:
            # Must match from the start of the relative path
            return f"^{joined}(/.*)?$"
        # Can match anywhere in the relative path
        return f"(?:^|.*/){joined}(/.*)?$"

    def is_ignored(self, rel_path: str, is_dir: bool = False) -> bool:
        """Return True if the path should be ignored according to parsed rules.

        Args:
            rel_path: Relative path from project root (using POSIX separators).
            is_dir: Whether the path represents a directory.

        Returns:
            True if the path should be excluded.

        """
        ignored = False
        for regex, is_negation in self.patterns:
            if regex.search(rel_path):
                ignored = not is_negation
        return ignored


def _load_gitignore_parser(root_dir: Path) -> GitignoreParser | None:
    """Create a GitignoreParser for the given root directory if .gitignore exists.

    Args:
        root_dir: Project root directory.

    Returns:
        GitignoreParser instance or None if .gitignore is missing/unreadable.

    """
    gitignore_path = root_dir / ".gitignore"
    if gitignore_path.is_file():
        return GitignoreParser(gitignore_path, root_dir)
    return None


def _collect_files(
    input_dir: str,
    config: dict[str, Any],
) -> tuple[defaultdict[str, list[str]], list[str], set[str], set[str]]:
    """Collect files during directory traversal respecting depth limit.

    Args:
        input_dir: Path to the project root.
        config: Configuration dictionary containing 'max_depth', 'blacklist_dirs',
            'include_empty_files', etc.

    Returns:
        Tuple of:
            - files_by_dir: Mapping from directory to list of file names.
            - all_content: List of formatted file content chunks.
            - processed_paths: Set of relative paths of included files.
            - extra_dirs: Set of directories that are truncated at depth limit.

    """
    files_by_dir: defaultdict[str, list[str]] = defaultdict(list)
    all_content: list[str] = []
    processed_paths: set[str] = set()
    extra_dirs: set[str] = set()

    max_depth = config.get("max_depth", -1)  # -1 = unlimited, 0 = only root, >0 = limited
    input_path = Path(input_dir)

    # Load .gitignore parser if enabled
    gitignore_parser = None
    if config.get("use_gitignore", False):
        gitignore_parser = _load_gitignore_parser(input_path)
        if gitignore_parser is None:
            warning("USE_GITIGNORE is True but .gitignore not found in project root. Continuing without it.")

    for root, dirs, files in os.walk(input_dir):
        rel_root = Path(root).relative_to(input_dir).as_posix()
        depth = 0 if rel_root == "." else len(Path(rel_root).parts)

        # Filter out blacklisted and hidden directories
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in config["blacklist_dirs"]]

        # Apply .gitignore filtering to directories
        if gitignore_parser is not None:
            filtered_dirs = []
            for d in dirs:
                dir_rel_path = (Path(root) / d).relative_to(input_path).as_posix()
                if not gitignore_parser.is_ignored(dir_rel_path, is_dir=True):
                    filtered_dirs.append(d)
            dirs[:] = filtered_dirs

        # Apply depth limit (-1 means unlimited)
        if max_depth != -1:
            if depth > max_depth:
                dirs.clear()
                continue
            if depth == max_depth:
                if rel_root != ".":  # don't mark root as "extra"
                    extra_dirs.add(rel_root)
                dirs.clear()  # do not go deeper

        for filename in files:
            file_path = Path(root) / filename
            rel_path = file_path.relative_to(input_path).as_posix()

            # Apply .gitignore filtering to files
            if gitignore_parser is not None and gitignore_parser.is_ignored(rel_path, is_dir=False):
                continue

            if not is_code_file(str(file_path), config):
                continue

            export_content = config.get("export_content", True)
            include_empty = config.get("include_empty_files", True)

            # When content export is disabled we avoid reading the whole file.
            if export_content:
                content = read_file_content(str(file_path))
                if content is None:
                    continue
                if not include_empty and content == "":
                    continue
            else:
                # Determine emptiness via file size – fast and avoids I/O.
                try:
                    is_empty = file_path.stat().st_size == 0
                except OSError:
                    # Inaccessible file – skip it.
                    continue
                if not include_empty and is_empty:
                    continue
                content = ""  # not used, but keeps variable defined

            rel_dir = Path(rel_path).parent.as_posix()
            files_by_dir[rel_dir].append(filename)
            processed_paths.add(rel_path)

            # Build content chunk only if content export is enabled.
            if export_content and content:
                language = detect_language(str(file_path))
                lang_tag = language or Path(file_path).suffix.lower().lstrip(".")
                chunk = f"{rel_path}:\n```{lang_tag}\n{content}\n```\n\n"
                all_content.append(chunk)

    return files_by_dir, all_content, processed_paths, extra_dirs


def _build_output(
    input_dir: str,
    processed_paths: set[str],
    all_content: list[str],
    extra_dirs: set[str],
    config: dict[str, Any],
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

    Returns:
        Complete output string (structure + contents).

    """
    max_depth = config.get("max_depth", -1)
    if max_depth == -1:
        # Unlimited depth: use the full output (respects SHOW_EMPTY_DIRS)
        return build_full_output(input_dir, processed_paths, all_content, config)

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


def export_project(
    input_dir: str,
    output_file: str,
    config: dict[str, Any],
    *,
    create_file: bool = True,
    copy_to_buffer: bool = False,
) -> tuple[dict[str, list[str]], int, str]:
    """Export project: collect files, build output, write to file and/or copy to clipboard.

    Args:
        input_dir: Path to the project root directory.
        output_file: Path where the output file will be saved.
        config: Configuration dictionary with export settings.
        create_file: Whether to write the output to a file.
        copy_to_buffer: Whether to copy the output to the clipboard.

    Returns:
        Tuple containing:
            - files_by_dir: Dictionary mapping directories to lists of file names.
            - total_chars: Total number of characters in the exported content.
            - full_output: The complete exported text (used for statistics/token count).

    """
    files_by_dir, all_content, processed_paths, extra_dirs = _collect_files(input_dir, config)

    full_output = _build_output(input_dir, processed_paths, all_content, extra_dirs, config)
    total_chars = len(full_output)

    if create_file:
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(full_output, encoding="utf-8")
        except OSError as e:
            error(f"Failed to write output file '{output_file}': {e}")
            warning("Output file was not created. Continuing with other operations...")

    handle_clipboard_copy(full_output, total_chars, copy_to_buffer=copy_to_buffer, config=config)
    return files_by_dir, total_chars, full_output
