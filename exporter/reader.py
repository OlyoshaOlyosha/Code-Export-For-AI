"""File reading and language detection for project export."""

from pathlib import Path

from exporter.console import error

# Default mapping from file extension to language tag for code fences
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    # ==================== Python ====================
    "py": "python",
    "pyw": "python",
    # ==================== JavaScript / TypeScript ====================
    "js": "javascript",
    "mjs": "javascript",
    "cjs": "javascript",
    "ts": "typescript",
    "jsx": "jsx",
    "tsx": "tsx",
    # ==================== Java / C / C++ / C# ====================
    "java": "java",
    "c": "c",
    "h": "c",
    "cpp": "cpp",
    "cc": "cpp",
    "cxx": "cpp",
    "hpp": "cpp",
    "cs": "csharp",
    # ==================== Rust / Go / Ruby / PHP ====================
    "rs": "rust",
    "rb": "ruby",
    "php": "php",
    # ==================== Shell & Scripting ====================
    "sh": "bash",
    "bash": "bash",
    "ps1": "powershell",
    "psm1": "powershell",
    "psd1": "powershell",
    "pl": "perl",
    "pm": "perl",
    "t": "perl",
    "cgi": "perl",
    "awk": "awk",
    "sed": "sed",
    "bat": "batch",
    "cmd": "batch",
    "ahk": "autohotkey",
    # ==================== Web (HTML / CSS) ====================
    "html": "html",
    "htm": "html",
    "css": "css",
    "scss": "scss",
    "sass": "sass",
    "less": "less",
    "styl": "stylus",
    # ==================== Markup & Documentation ====================
    "md": "markdown",
    "mdx": "mdx",
    "rst": "rst",
    "asciidoc": "asciidoc",
    "adoc": "asciidoc",
    "latex": "latex",
    "tex": "latex",
    "bib": "bibtex",
    # ==================== Data & Configuration ====================
    "yml": "yaml",
    "yaml": "yaml",
    "json": "json",
    "xml": "xml",
    "toml": "toml",
    "ini": "ini",
    "conf": "ini",
    "cfg": "ini",
    "config": "ini",
    "properties": "properties",
    "csv": "csv",
    "tsv": "tsv",
    "log": "log",
    "env": "env",
    "txt": "text",
    # ==================== Infrastructure & Build ====================
    "dockerfile": "dockerfile",
    "makefile": "makefile",
    "tf": "hcl",
    "tfvars": "hcl",
    "hcl": "hcl",
    "nix": "nix",
    "cmake": "cmake",
    "gradle": "groovy",
    "groovy": "groovy",
    # ==================== Database & Query Languages ====================
    "sql": "sql",
    "graphql": "graphql",
    "gql": "graphql",
    "proto": "protobuf",
    "thrift": "thrift",
    # ==================== Functional & Other Languages ====================
    "ex": "elixir",
    "exs": "elixir",
    "eex": "elixir",
    "heex": "elixir",
    "clj": "clojure",
    "cljs": "clojure",
    "cljc": "clojure",
    "erl": "erlang",
    "hs": "haskell",
    "fs": "fsharp",
    "fsi": "fsharp",
    "fsx": "fsharp",
    "jl": "julia",
    "nim": "nim",
    "zig": "zig",
    "crystal": "crystal",
    "elm": "elm",
    "purs": "purescript",
    "d": "d",
    # ==================== Frontend Frameworks ====================
    "svelte": "svelte",
    "vue": "vue",
    "astro": "astro",
    # ==================== Assembly & Low-level ====================
    "asm": "asm",
    "s": "asm",
    # ==================== .NET & Visual Basic ====================
    "vb": "vbnet",
    "vbs": "vbnet",
    # ==================== Ignore Files ====================
    "dockerignore": "dockerignore",
    "gitignore": "gitignore",
    "editorconfig": "editorconfig",
    # ==================== Other ====================
    "jinja": "jinja",
    "j2": "jinja",
    "prisma": "prisma",
}


def read_file_content(file_path: str) -> str | None:
    """Read file content with fallback encodings.

    Args:
        file_path: Path to the file to read.

    Returns:
        The file content as a string, or None if reading failed.

    """
    path = Path(file_path)
    encodings = ["utf-8", "cp1251", "latin-1"]

    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        except OSError as e:
            error(f"Error reading {file_path}: {e}")
            return None

    error(f"Failed to read file (all encodings failed): {file_path}")
    return None


def detect_language(file_path: str) -> str:
    """Detect language tag for code fences based on file extension."""
    ext = Path(file_path).suffix.lower().lstrip(".")
    return EXTENSION_LANGUAGE_MAP.get(ext, "")
