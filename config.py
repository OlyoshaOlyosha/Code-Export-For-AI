"""
User configuration for Code Export For AI.

Edit this file to customize filtering and behavior.
"""

# File extensions to ignore (without dot)
BLACKLIST_EXTENSIONS = {
    "txt", "md", "markdown", "log", "pdf", "doc", "docx", "xls", "xlsx",
    "png", "jpg", "jpeg", "gif", "bmp", "ico", "svg", "webp",
    "mp3", "mp4", "avi", "mov", "wav",
    "zip", "rar", "7z", "tar", "gz",
    "exe", "dll", "so", "bin", "o", "obj",
    "pyc", "pyo", "pyd", "class",
    "db", "sqlite", "mdb",
    "ini", "cfg", "conf", "config", "env",
    # Build artifacts and generated files
    "pyi",            # Type stub files
    "lock",           # Dependency lock files (poetry.lock, package-lock.json)
    "map",            # Source maps
    "min.js", "min.css",  # Minified assets
    "bundle.js", "chunk.js",  # Bundled JS
}

# Directories to completely skip
BLACKLIST_DIRS = {
    "__pycache__",
    ".git",
    ".vscode",
    ".vs",
    ".idea",
    "node_modules",
    "obj",
    "bin",
    "venv",
    "env",
    "virtualenv",
    "dist",
    "build",
    "target",
    "packages",
    # Caches and test outputs
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    "coverage",
    # Temporary directories
    "tmp",
    "temp",
    "logs",
}

# Filenames to ignore
BLACKLIST_FILENAMES = {"setup.py", "requirements.txt"}

# Filename matching mode: 'exact' or 'contains'
FILENAME_FILTER_MODE = "exact"

# Output settings
OUTPUT_DIR = "outputs"  # Default directory for output files
OUTPUT_FILENAME = "output.txt"  # Base name for output file (will be placed in OUTPUT_DIR)
OUTPUT_FORMAT = "txt"  # future: 'md'
MAX_FILE_SIZE_MB = 5  # Max file size to include (in MB)
CREATE_FILE = True  # Write output to file
COPY_TO_CLIPBOARD = True  # Copy output to clipboard

# Features
USE_PYGMENTS = True  # Enable syntax highlighting
SHOW_PROGRESS = True  # Show progress during export

# Export options
EXPORT_STRUCTURE = True  # Include project directory tree in output
EXPORT_CONTENT = True  # Include file contents (code) in output

SHOW_EMPTY_DIRS = True  # Include empty directories in the structure tree
INCLUDE_EMPTY_FILES = True  # Include empty files in output (structure only, no empty code blocks)

# Clipboard safety
MAX_CLIPBOARD_CHARS = 500000  # Maximum characters to copy to clipboard (0 to disable)
