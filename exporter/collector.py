"""File collection and gitignore loading for project export."""

import fnmatch
import os
import time
from collections import defaultdict
from pathlib import Path

from pathspec import PathSpec
from rich.progress import BarColumn, Progress, TextColumn

from exporter.reader import detect_language, read_file_content
from exporter.scanner import _prune_dirs, is_code_file, is_in_allowed_dirs
from exporter.utils import ExportStats


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


def _collect_files(
    input_dir: str,
    config: dict,
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
