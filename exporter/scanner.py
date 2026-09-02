"""Module for scanning and filtering code files based on blacklist rules."""

from pathlib import Path
from typing import Any

from pathspec import PathSpec


def is_code_file(
    file_path: str,
    config: dict[str, Any],
    allowed_dirs: set[str] | None = None,
    root_dir: str | None = None,
) -> bool:
    """Determine if a file should be included in the export based on filters.

    Args:
        file_path: Path to the file to check.
        config: Configuration dictionary containing the keys:
            'blacklist_extensions', 'blacklist_dirs', 'blacklist_filenames',
            'filename_filter_mode', and optionally 'max_size'.
        allowed_dirs: Optional whitelist of allowed relative directory paths. When a
            file lives inside an allowed (but blacklisted) directory, the directory
            blacklist is overridden so the file is still exported.
        root_dir: Project root, used to compute the file's relative directory for the
            allowed_dirs lookup. Required for the override to take effect.

    Returns:
        True if the file should be included, False otherwise.

    """
    path = Path(file_path)
    filename = path.name

    # Skip hidden files
    if filename.startswith("."):
        return False

    # Filename blacklist (combined exact/contains check)
    blacklist_filenames = config["blacklist_filenames"]
    mode = config["filename_filter_mode"]
    if (mode == "exact" and filename in blacklist_filenames) or (
        mode == "contains" and any(p in filename for p in blacklist_filenames)
    ):
        return False

    # Override: a file inside an explicitly allowed dir bypasses the dir blacklist.
    allowed = (
        bool(allowed_dirs)
        and root_dir is not None
        and is_in_allowed_dirs(Path(file_path).relative_to(Path(root_dir)).parent.as_posix(), allowed_dirs)
    )

    # Skip if parent directory is blacklisted (unless it is an allowed dir)
    if path.parent.name in config["blacklist_dirs"] and not allowed:
        return False

    # Skip files without extension or with blacklisted extension
    blacklist_extensions = config["blacklist_extensions"]
    ext = path.suffix.lower().lstrip(".")
    if not ext:
        # Extensionless file: include only if its name is in the whitelist
        allowed_extensionless = config.get("allowed_extensionless_files", set())
        if filename not in allowed_extensionless:
            return False
    elif ext in blacklist_extensions:
        return False

    # File size limit – return True only if size is within limit (or no limit)
    max_size = config.get("max_size")
    if max_size:
        try:
            if path.stat().st_size > max_size:
                return False
        except OSError as e:
            # File may be inaccessible or a broken symlink – skip it
            from exporter.console import warning

            warning(f"Skipping inaccessible file: {file_path} ({e})")
            return False
    return True


def is_in_allowed_dirs(rel_dir: str, allowed_dirs: set[str]) -> bool:
    """Check whether a relative directory path falls within the allowed whitelist.

    Args:
        rel_dir: Relative directory path (use "." for the project root, and use
            forward slashes as path separators, e.g. "tests/unit").
        allowed_dirs: Set of allowed relative directory paths. An empty set means
            no restriction (always returns True).

    Returns:
        True if the directory (or one of its ancestors) is in the whitelist,
        or if the whitelist is empty.

    """
    if not allowed_dirs:
        return True
    parts = [] if rel_dir in (".", "") else rel_dir.split("/")
    return any("/".join(parts[:i]) in allowed_dirs for i in range(1, len(parts) + 1))


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
