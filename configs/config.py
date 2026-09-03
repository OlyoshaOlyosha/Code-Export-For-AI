"""
Default (balanced) profile for Project2Prompt.

This file lists every setting explicitly and works as the reference baseline.
Your own profiles don't have to: any setting you omit falls back to the
built-in defaults - write only the lines that differ (see configs/examples/).
"""

# ── Identity ─────────────────────────────────────────────────────────────
# Shown in the configuration selection menu (one line, ~80 chars max).
CONFIG_DESCRIPTION = "Balanced default: code and text in, binaries and noise out"

# ── 1. What to exclude ───────────────────────────────────────────────────

# File extensions to ignore (without the dot), grouped by category.
BLACKLIST_EXTENSIONS = {
    # Documents and text
    "txt",
    "md",
    "markdown",
    "log",
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    # Images
    "png",
    "jpg",
    "jpeg",
    "gif",
    "bmp",
    "ico",
    "svg",
    "webp",
    # Audio / video
    "mp3",
    "mp4",
    "avi",
    "mov",
    "wav",
    # Archives
    "zip",
    "rar",
    "7z",
    "tar",
    "gz",
    # Binaries and build artifacts
    "exe",
    "dll",
    "so",
    "bin",
    "o",
    "obj",
    "pyc",
    "pyo",
    "pyd",
    "class",
    # Databases
    "db",
    "sqlite",
    "mdb",
    # Local config and machine state ("env" here means .env files with secrets)
    "ini",
    "cfg",
    "conf",
    "config",
    "env",
    # Generated files
    "pyi",  # Type stub files
    "lock",  # Dependency lock files (poetry.lock, package-lock.json)
    "map",  # Source maps
}

# Directories to completely skip, grouped by category.
BLACKLIST_DIRS = {
    # IDE / editor / VCS internals
    ".git",
    ".vscode",
    ".vs",
    ".idea",
    # Build output and dependency folders
    "__pycache__",
    "node_modules",
    "obj",
    "bin",
    "dist",
    "build",
    "target",
    "packages",
    # Virtual environments ("env" here is the virtualenv folder, not the .env file)
    "venv",
    "env",
    "virtualenv",
    ".venv",
    "site-packages",
    # Caches and test outputs
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    "coverage",
    # Bundler / framework caches
    ".next",
    ".parcel-cache",
    ".svelte-kit",
    ".astro",
    ".gradle",
    ".turbo",
    ".nuxt",
    ".output",
    # Temporary directories
    "tmp",
    "temp",
    "logs",
    ".cache",
    ".tox",
}

# Force-include list of allowed directories (relative paths from project root).
# Listed dirs (and all ancestors/descendants) bypass BLACKLIST_DIRS and
# .gitignore, so their files are always exported. All other dirs keep normal
# filtering — they are NOT restricted. Example: use {"src", "tests/unit"} to
# force-include those two directories (and everything inside them) while every
# other directory is still filtered by BLACKLIST_DIRS / .gitignore as usual.
# Empty set = no restriction. Hidden dirs remain governed by BLACKLIST_DIRS /
# .gitignore unless explicitly listed here.
ALLOWED_DIRS = set()

# Individual files to exclude. Nothing is excluded by default; this is where
# minified/bundled files belong (e.g. app.min.js, vendor.bundle.js) together
# with FILENAME_FILTER_MODE = "contains".
# Example: BLACKLIST_FILENAMES = {"min.", "bundle.", "chunk."}
# Note: do NOT add these to BLACKLIST_EXTENSIONS -- that set works on the
# part after the LAST dot, so "min.js" would only match a file named literally "min.js".
BLACKLIST_FILENAMES = set()

# Filename matching mode for BLACKLIST_FILENAMES: 'exact' or 'contains'
FILENAME_FILTER_MODE = "exact"

# Extensionless files whitelist: files without an extension are normally
# excluded. Add names here to allow them.
ALLOWED_EXTENSIONLESS_FILES = {
    "Dockerfile",
    "Makefile",
    "README",
    "LICENSE",
}

# ── 2. Where to scan ─────────────────────────────────────────────────────

# Default project directory to export.
# Can be an absolute path, e.g.:
#   Windows:  "C:\\Users\\Name\\Projects\\MyApp"
#   Linux/macOS: "/home/name/Projects/MyApp"
# You can also use "~" to refer to the home directory, e.g. "~/Projects/MyApp".
# Leave empty ("") to always prompt for folder selection (GUI or console).
INPUT_DIR: str = ""

# Directory traversal depth: -1 = unlimited, 0 = only the selected directory,
# positive integer = at most N levels deep.
MAX_DEPTH = -1

# Respect the project's .gitignore on top of the blacklists above.
USE_GITIGNORE = True

# ── 3. Where to write ────────────────────────────────────────────────────

OUTPUT_DIR = "outputs"  # Root folder for output files (per-config subfolder is added)
OUTPUT_FILENAME = "output.txt"  # Base name; auto-numbered as 01_output.txt, 02_output.txt, ...
MAX_FILE_SIZE_MB = 5  # Max file size to include (in MB). Set to 0 to disable the limit.
CREATE_FILE = True  # Write output to file
COPY_TO_CLIPBOARD = False  # Copy output to clipboard (opt-in; set True to enable)
MAX_CLIPBOARD_CHARS = 500000  # Clipboard safety limit (0 disables it)

# ── 4. What goes into the output ─────────────────────────────────────────

EXPORT_STRUCTURE = True  # Include project directory tree
EXPORT_CONTENT = True  # Include file contents (code)
SHOW_EMPTY_DIRS = True  # Include empty directories in the structure tree
INCLUDE_EMPTY_FILES = True  # Include empty files (structure only, no empty code blocks)

# ── 5. File order inside the export ──────────────────────────────────────

# Priority-based file ordering (optional).
# Patterns use fnmatch syntax against the entire relative path.
# Within each priority tier files are sorted by directory depth then alphabetically.
# When both lists are empty the original insertion order is preserved.
#
# Example for a typical Python project:
# PRIORITY_PATTERNS: list[str] = [
#     "README*",
#     "*.yaml", "*.yml", "*.toml", "setup.cfg", "pyproject.toml",
#     "src/*.py", "src/*/*.py", "tests/*.py", "*.py",
# ]
# LOW_PRIORITY_PATTERNS: list[str] = [
#     "requirements*.txt", "Pipfile", "Pipfile.lock",
# ]
PRIORITY_PATTERNS: list[str] = []
LOW_PRIORITY_PATTERNS: list[str] = []
