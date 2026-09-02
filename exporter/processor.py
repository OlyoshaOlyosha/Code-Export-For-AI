"""Project file processing and export module.

Contains the public orchestrator function that coordinates file collection,
output building, and clipboard copying.
"""

from pathlib import Path
from typing import Any

from pathspec import PathSpec

from exporter.builder import _build_output, handle_clipboard_copy
from exporter.collector import _collect_files, _load_gitignore_spec
from exporter.console import error, warning
from exporter.utils import ExportStats


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
