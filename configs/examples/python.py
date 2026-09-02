"""Example profile: Python projects.

Examples teach the "only differences" pattern: any setting you omit falls
back to the built-in defaults (see README -> Configuration). Copy this file,
rename it, and change only what your project needs.
"""

CONFIG_DESCRIPTION = "Python projects: code in, artifacts/caches out, .gitignore respected"

# Defaults are empty on purpose - a profile declares what it filters.
BLACKLIST_EXTENSIONS = {
    "pyc", "pyo", "pyd", "pyi",  # bytecode caches / type stubs
    "log", "cfg", "ini", "env",  # local machine state
    "png", "jpg", "jpeg", "gif", "svg", "ico",  # images
    "pdf", "docx", "xlsx",
    "zip", "tar", "gz", "7z",
    "lock",  # dependency lock files (huge, rarely useful in a prompt)
}

# Respect the project's .gitignore on top of these filters
USE_GITIGNORE = True

# Extensionless text files worth exporting
ALLOWED_EXTENSIONLESS_FILES = {"Dockerfile", "Makefile"}
