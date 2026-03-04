import os


def is_code_file(
    file_path: str,
    blacklist_extensions: set[str],
    blacklist_dirs: set[str],
    blacklist_filenames: set[str],
    filename_filter_mode: str,
    max_size: int | None = None,
) -> bool:
    """Determine if a file should be included in the export based on filters.

    Args:
        file_path: Path to the file to check.
        blacklist_extensions: Set of file extensions to exclude.
        blacklist_dirs: Set of directory names to exclude.
        blacklist_filenames: Set of filenames to exclude.
        filename_filter_mode: Mode for filename filtering ('exact' or 'contains').
        max_size: Maximum file size in bytes, or None for no limit.

    Returns:
        True if the file should be included, False otherwise.

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
