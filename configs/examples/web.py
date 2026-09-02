"""Example profile: JS/TS frontends (React, Vue, plain Node).

Also demonstrates PRIORITY_PATTERNS / LOW_PRIORITY_PATTERNS: the AI reads
the export top-down, so entry points come first and test files come last.
"""

CONFIG_DESCRIPTION = "JS/TS frontends: sources in, node_modules/build out, entry points first"

BLACKLIST_EXTENSIONS = {
    "log", "env",
    "png", "jpg", "jpeg", "gif", "svg", "ico", "webp",
    "woff", "woff2", "ttf", "eot",  # fonts
    "mp4", "webm",
    "zip", "gz",
}

BLACKLIST_DIRS = {"node_modules", "dist", "build", "coverage", ".next", ".nuxt", ".cache"}

USE_GITIGNORE = True

# Exported first: the AI sees entry points before the implementation
PRIORITY_PATTERNS = ["package.json", "README.md", "index.*", "main.*"]

# Exported last: tests and generated stories
LOW_PRIORITY_PATTERNS = ["*.test.*", "*.spec.*", "*.stories.*"]
