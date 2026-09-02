"""Example profile: full context - code AND documentation.

The shipped default excludes .md; when you review documentation together
with the code, you usually want it in. This profile differs from the
default exactly there: .md / .txt / .rst stay included.
"""

CONFIG_DESCRIPTION = "Code + Markdown/text docs in one export (default excludes .md)"

BLACKLIST_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "svg", "ico",
    "pdf", "doc", "docx", "xls", "xlsx", "pptx",
    "zip", "rar", "7z", "tar", "gz",
    "exe", "dll", "bin", "db", "sqlite",
    "pyc", "class", "o", "obj",
}

USE_GITIGNORE = True
INCLUDE_EMPTY_FILES = True
