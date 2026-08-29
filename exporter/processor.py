"""Project file processing and export module.

Contains core logic: reading files, language detection for code‑fence tags,
project structure generation, and final output formatting.
"""

import fnmatch
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from pathspec import PathSpec
from rich.progress import BarColumn, Progress, TextColumn

from exporter.clipboard import copy_to_clipboard
from exporter.console import error, success, warning
from exporter.scanner import is_code_file, is_in_allowed_dirs
from exporter.utils import ExportStats

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


def _load_gitignore_spec(root_dir: Path) -> PathSpec | None:
    """Load .gitignore patterns into a PathSpec object.

    Args:
        root_dir: Project root directory.

    Returns:
        PathSpec instance if .gitignore exists and is readable, else None.

    """
    gitignore_path = root_dir / ".gitignore"
    if not gitignore_path.is_file():
        return None
    try:
        lines = gitignore_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    spec = PathSpec.from_lines("gitwildmatch", lines)
    return spec


def _dir_allowed(cand_rel: str, allowed_dirs: set[str]) -> bool:
    """Check whether a candidate relative directory is within the allowed whitelist.

    Args:
        cand_rel: Relative directory path (forward slashes, e.g. "tests/unit").
        allowed_dirs: Set of allowed relative directory paths. An empty set means
            no restriction (always returns True).

    Returns:
        True if the candidate equals an allowed dir, is a descendant of one, or is
        an ancestor of one (so a partially-typed ancestor still reveals branches).

    """
    if not allowed_dirs:
        return True
    for a in allowed_dirs:
        a_norm = a.rstrip("/")
        if cand_rel == a_norm or cand_rel.startswith(a_norm + "/") or a_norm.startswith(cand_rel + "/"):
            return True
    return False


def _prune_dirs(
    dirs: list[str],
    root: str,
    *,
    input_dir: Path | str,
    blacklist_dirs: set[str],
    allowed_dirs: set[str],
    gitignore_spec: PathSpec | None,
) -> list[str]:
    """Filter directory names by blacklist/gitignore rules with force-include exceptions.

    Hidden directories (those starting with ``.``) are not auto-skipped here; their
    exclusion is governed solely by ``blacklist_dirs`` and ``.gitignore``. When a dir is
    listed in ``allowed_dirs`` it is force-included, bypassing both the blacklist and
    gitignore pruning. All other dirs are still filtered normally — they are NOT
    restricted to the allowed set. With an empty ``allowed_dirs`` behavior is unchanged.

    Args:
        dirs: Directory names in the current ``os.walk`` step.
        root: Absolute/relative root path of the current ``os.walk`` step.
        input_dir: Project root path (used to compute relative paths for gitignore).
        blacklist_dirs: Set of blacklisted directory names.
        allowed_dirs: Set of allowed relative directory paths.
        gitignore_spec: Compiled .gitignore patterns, or None to skip.

    Returns:
        The filtered list of directory names.

    """
    base = Path(input_dir)
    rel_root = Path(root).relative_to(base).as_posix()
    pruned: list[str] = []
    for d in dirs:
        cand = f"{rel_root}/{d}" if rel_root != "." else d
        # Force-include allowed dirs: bypass blacklist/gitignore pruning. The
        # empty-set guard is required because _dir_allowed returns True on an
        # empty set, which would otherwise let everything slip past the filters.
        if allowed_dirs and _dir_allowed(cand, allowed_dirs):
            pruned.append(d)
            continue
        if d in blacklist_dirs:
            continue
        if gitignore_spec is not None and gitignore_spec.match_file(
            f"{(Path(root) / d).relative_to(base).as_posix()}/"
        ):
            continue
        pruned.append(d)
    return pruned


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


def detect_language(file_path: str) -> str:
    """Detect language tag for code fences based on file extension."""
    ext = Path(file_path).suffix.lower().lstrip(".")
    return EXTENSION_LANGUAGE_MAP.get(ext, "")


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


def _collect_files(
    input_dir: str,
    config: dict[str, Any],
    gitignore_spec: PathSpec | None = None,
    delta_since: float | None = None,
) -> tuple[defaultdict[str, list[str]], list[str], set[str], set[str], ExportStats]:
    """Collect files during directory traversal respecting depth limit.

    Args:
        input_dir: Path to the project root.
        config: Configuration dictionary containing 'max_depth', 'blacklist_dirs',
            'include_empty_files', etc.
        gitignore_spec: Compiled .gitignore patterns (PathSpec from pathspec), or None.

    Returns:
        Tuple of:
            - files_by_dir: Mapping from directory to list of file names.
            - all_content: List of formatted file content chunks.
            - processed_paths: Set of relative paths of included files.
            - extra_dirs: Set of directories that are truncated at depth limit.
            - stats: Extended statistics (skips, extensions, largest files).

    """
    files_by_dir: defaultdict[str, list[str]] = defaultdict(list)
    chunks: dict[str, str] = {}
    processed_paths: set[str] = set()
    extra_dirs: set[str] = set()
    stats = ExportStats()

    max_depth = config.get("max_depth", -1)  # -1 = unlimited, 0 = only root, >0 = limited
    input_path = Path(input_dir)
    max_size = config.get("max_size")  # may be 0 meaning "no limit"
    allowed_dirs = config.get("allowed_dirs", set())

    # ── Progress bar while collecting files ────────────────────────────
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed} files"),
        transient=True,
    ) as progress:
        task = progress.add_task("Scanning...", total=None)
        processed_count = 0
        last_update_time = time.time()

        for root, dirs, files in os.walk(input_dir):
            rel_root = Path(root).relative_to(input_dir).as_posix()
            depth = 0 if rel_root == "." else len(Path(rel_root).parts)

            # Filter directories by blacklist/gitignore rules with allowed-dirs
            # force-include exceptions (allowed dirs bypass blacklist/gitignore).
            dirs[:] = _prune_dirs(
                dirs,
                root,
                input_dir=input_path,
                blacklist_dirs=config["blacklist_dirs"],
                allowed_dirs=allowed_dirs,
                gitignore_spec=gitignore_spec,
            )

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

                # Force-include files inside allowed dirs (bypass .gitignore). The
                # bool(allowed_dirs) guard matters: is_in_allowed_dirs returns True on
                # an empty set, which would otherwise force-include everything.
                rel_dir = Path(rel_path).parent.as_posix()
                in_allowed = bool(allowed_dirs) and is_in_allowed_dirs(rel_dir, allowed_dirs)

                # Apply .gitignore filtering to files (unless force-included)
                if gitignore_spec is not None and gitignore_spec.match_file(rel_path) and not in_allowed:
                    continue

                if not is_code_file(str(file_path), config, allowed_dirs=allowed_dirs, root_dir=str(input_path)):
                    stats.skipped_rules += 1
                    continue

                # File passed code‑file filters – collect size and mtime
                try:
                    st = file_path.stat()
                    file_size = st.st_size
                    file_mtime = st.st_mtime
                except OSError:
                    # Inaccessible file – skip it.
                    continue

                # Size limit check
                if max_size and file_size > max_size:
                    stats.skipped_size += 1
                    continue

                # Delta filter – skip files not modified after delta_since
                if delta_since is not None and file_mtime <= delta_since:
                    continue

                export_content = config.get("export_content", True)
                include_empty = config.get("include_empty_files", True)

                # When content export is disabled we avoid reading the whole file.
                if export_content:
                    content = read_file_content(str(file_path))
                    if content is None:
                        stats.skipped_binary += 1
                        continue
                    if not include_empty and content == "":
                        continue
                else:
                    # Determine emptiness via file size – fast and avoids I/O.
                    is_empty = file_size == 0
                    if not include_empty and is_empty:
                        continue
                    content = ""  # placeholder

                # File is included → update extension counter
                ext = file_path.suffix.lower().lstrip(".")
                ext_key = ext or "<no extension>"
                stats.extension_counts[ext_key] = stats.extension_counts.get(ext_key, 0) + 1

                # Record file size only after all filters passed (for accurate Top‑5 table)
                stats.largest_files.append((file_size, rel_path))

                rel_dir = Path(rel_path).parent.as_posix()
                files_by_dir[rel_dir].append(filename)
                processed_paths.add(rel_path)

                # Update progress bar (throttled to ~20 fps)
                processed_count += 1
                now = time.time()
                if now - last_update_time >= 0.05:
                    progress.update(
                        task,
                        completed=processed_count,
                        description=f"Scanning... ({processed_count} files)",
                    )
                    last_update_time = now

                # Build content chunk only if content export is enabled.
                if export_content and content:
                    language = detect_language(str(file_path))
                    lang_tag = language or file_path.suffix.lower().lstrip(".")
                    chunk = f"{rel_path}:\n```{lang_tag}\n{content}\n```\n\n"
                    chunks[rel_path] = chunk

        # Final unconditional update — always show the correct count before disappearing.
        progress.update(
            task,
            completed=processed_count,
            description=f"Scanning... ({processed_count} files)",
        )

    # Apply priority-based ordering if patterns are defined
    priority_patterns = config.get("priority_patterns", [])
    if priority_patterns:
        low_priority_patterns = config.get("low_priority_patterns", [])
        sorted_paths = sorted(processed_paths)

        def _compute_priority(rel_path: str) -> int:
            """Return priority tier: 0..N high, N neutral, N+1 low."""
            for idx, pattern in enumerate(priority_patterns):
                if fnmatch.fnmatch(rel_path, pattern):
                    return idx
            if low_priority_patterns:
                for pattern in low_priority_patterns:
                    if fnmatch.fnmatch(rel_path, pattern):
                        return len(priority_patterns) + 1
            return len(priority_patterns)

        sorted_paths.sort(key=lambda p: (_compute_priority(p), p.count("/") + 1, p))
        all_content = [chunks[p] for p in sorted_paths if p in chunks]
    else:
        all_content = list(chunks.values())

    return files_by_dir, all_content, processed_paths, extra_dirs, stats


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


def export_project(
    input_dir: str,
    output_file: str,
    config: dict[str, Any],
    *,
    create_file: bool = True,
    copy_to_buffer: bool = False,
    delta_since: float | None = None,
) -> tuple[dict[str, list[str]], int, str, ExportStats]:
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
            - stats: Extended statistics (skips, extensions, largest files).

    """
    input_path = Path(input_dir).resolve()

    # Load .gitignore spec if enabled
    gitignore_spec: PathSpec | None = None
    if config.get("use_gitignore", False):
        gitignore_spec = _load_gitignore_spec(input_path)
        if gitignore_spec is None:
            warning("USE_GITIGNORE is True but .gitignore not found in project root. Continuing without it.")

    files_by_dir, all_content, processed_paths, extra_dirs, stats = _collect_files(
        input_dir,
        config,
        gitignore_spec=gitignore_spec,
        delta_since=delta_since,
    )

    full_output = _build_output(
        input_dir,
        processed_paths,
        all_content,
        extra_dirs,
        config,
        gitignore_spec=gitignore_spec,
        delta_since=delta_since,
    )
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
    return files_by_dir, total_chars, full_output, stats
