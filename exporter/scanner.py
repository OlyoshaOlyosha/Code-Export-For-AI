import os
from typing import Optional, Set


def is_code_file(
    file_path: str,
    blacklist_extensions: Set[str],
    blacklist_dirs: Set[str],
    blacklist_filenames: Set[str],
    filename_filter_mode: str,
    max_size: Optional[int] = None,
) -> bool:
    """
    Determine if a file should be included in the export based on filters.
    """
    filename = os.path.basename(file_path)

    # Skip hidden files
    if filename.startswith("."):
        return False

    # Filename blacklist
    if filename_filter_mode == "exact" and filename in blacklist_filenames:
        return False
    if filename_filter_mode == "contains" and any(p in filename for p in blacklist_filenames):
        return False

    # Skip if parent directory is blacklisted
    parent_dir = os.path.basename(os.path.dirname(file_path))
    if parent_dir in blacklist_dirs:
        return False

    # Skip files without extension
    _, ext = os.path.splitext(filename)
    if not ext:
        return False

    # Blacklisted extension
    if ext.lower()[1:] in blacklist_extensions:
        return False

    # File size limit
    if max_size and os.path.getsize(file_path) > max_size:
        return False

    return True