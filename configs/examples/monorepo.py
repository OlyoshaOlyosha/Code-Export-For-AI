"""Example profile: large repositories / monorepos.

MAX_DEPTH limits how deep the scan goes (0 = root only, N = N levels,
-1 = unlimited). Depth limiting keeps exports fast and focused when the
repository is huge.
"""

CONFIG_DESCRIPTION = "Large repos: depth-limited scan, fast and focused"

BLACKLIST_EXTENSIONS = {
    "log", "env",
    "png", "jpg", "jpeg", "gif", "svg", "ico",
    "pdf", "zip", "gz", "mp4",
    "pyc", "class", "o", "obj", "dll", "exe",
}

MAX_DEPTH = 3
USE_GITIGNORE = True
