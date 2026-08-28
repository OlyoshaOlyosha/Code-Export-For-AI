"""Module for scanning and filtering code files based on blacklist rules."""

from pathlib import Path
from typing import Any


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
