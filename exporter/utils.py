import os
import tkinter as tk
from tkinter import filedialog
from typing import Dict, List


def select_directory() -> str | None:
    """Open a GUI dialog to select a project directory."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    folder_path = filedialog.askdirectory(title="Select project folder")
    root.destroy()
    return folder_path or None


def get_next_filename(base_name: str) -> str:
    """Generate unique filename by adding _1, _2 etc. if needed."""
    if not os.path.exists(base_name):
        return base_name

    name, ext = os.path.splitext(base_name)
    counter = 1
    while os.path.exists(f"{name}_{counter}{ext}"):
        counter += 1
    return f"{name}_{counter}{ext}"


def print_statistics(
    files_by_dir: Dict[str, List[str]],
    total_chars: int,
    elapsed_time: float,
    output_file: str,
    create_file: bool,
    copy_to_buffer: bool,
) -> None:
    """Print formatted statistics after export."""
    print("\n=== STATISTICS ===")
    print(f"Elapsed time: {elapsed_time:.2f} sec")
    print(f"Characters: {total_chars:,} ({total_chars / 1024:.1f} KB)")

    print("\nFiles by directory:")
    for dir_path in sorted(files_by_dir.keys()):
        files = files_by_dir[dir_path]
        print(f"  {dir_path}: {len(files)} - {', '.join(files)}")

    result_parts = []
    if create_file:
        result_parts.append(f"saved to {output_file}")
    if copy_to_buffer:
        result_parts.append("copied to clipboard")

    print(f"\nDone! Result: {' and '.join(result_parts)}")