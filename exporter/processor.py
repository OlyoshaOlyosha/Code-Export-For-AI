import os
from collections import defaultdict
from typing import Dict, List, Tuple

from exporter.clipboard import copy_to_clipboard
from exporter.scanner import is_code_file


# Default mapping from file extension to language tag for code fences
# Used as fallback when Pygments is not available or fails
EXTENSION_LANGUAGE_MAP = {
    'py': 'python', 'pyw': 'python',
    'js': 'javascript', 'mjs': 'javascript', 'cjs': 'javascript',
    'ts': 'typescript',
    'jsx': 'jsx', 'tsx': 'tsx',
    'java': 'java',
    'c': 'c', 'h': 'c',
    'cpp': 'cpp', 'cc': 'cpp', 'cxx': 'cpp', 'hpp': 'cpp',
    'cs': 'csharp',
    'go': 'go',
    'rs': 'rust',
    'rb': 'ruby',
    'php': 'php',
    'sh': 'bash', 'bash': 'bash',
    'ps1': 'powershell', 'psm1': 'powershell', 'psd1': 'powershell',
    'html': 'html', 'htm': 'html',
    'css': 'css',
    'json': 'json',
    'yml': 'yaml', 'yaml': 'yaml',
    'xml': 'xml',
    'sql': 'sql',
    'md': 'markdown', 'markdown': 'markdown',
    'dockerfile': 'dockerfile',
    'makefile': 'makefile',
    'txt': '',
    'ini': 'ini',
    'toml': 'toml',
    'gradle': 'groovy', 'groovy': 'groovy',
    'dart': 'dart',
    'kt': 'kotlin', 'kts': 'kotlin',
    'scala': 'scala',
    'jl': 'julia',
    'r': 'r',
    'swift': 'swift',
    'erl': 'erlang',
    'hs': 'haskell',
}


def read_file_content(file_path: str) -> str | None:
    """Read file content with fallback encodings."""
    encodings = ["utf-8", "cp1251", "latin-1"]

    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None

    print(f"Failed to read file (all encodings failed): {file_path}")
    return None

def generate_project_structure(input_dir: str, processed_paths: set) -> str:
    """
    Generate clean ASCII tree of the project structure
    based on actually processed relative paths.
    """
    # Build tree from relative paths
    root = {}
    for rel_path in sorted(processed_paths):
        parts = rel_path.replace("\\", "/").split("/")  # normalize slashes
        current = root
        for part in parts[:-1]:  # directories
            if part not in current:
                current[part] = {}
            current = current[part]
        # leaf is file
        filename = parts[-1]
        if "__files__" not in current:
            current["__files__"] = []
        current["__files__"].append(filename)

    def render_node(node: dict, prefix: str = "") -> List[str]:
        lines = []
        # Get directories and files
        dirs = [k for k in node.keys() if k != "__files__"]
        files = sorted(node.get("__files__", []))

        pointers = ["├── "] * (len(dirs) + len(files) - 1) + (["└── "] if dirs + files else [])

        for i, name in enumerate(sorted(dirs) + files):
            pointer = pointers[i]
            is_dir = name in dirs
            line = f"{prefix}{pointer}{name}/" if is_dir else f"{prefix}{pointer}{name}"
            lines.append(line)

            if is_dir:
                extension = "    " if pointer == "└── " else "│   "
                lines.extend(render_node(node[name], prefix + extension))

        return lines

    lines = ["# Project Directory Structure:", ".", ""]
    lines.extend(render_node(root))
    lines.append("")  # empty line after tree
    return "\n".join(lines)

def detect_language(file_path: str, content: str, config: Dict) -> str:
    """Detect language tag for syntax highlighting."""
    use_pygments = config.get("use_pygments", True)

    if use_pygments:
        try:
            from pygments.lexers import guess_lexer_for_filename
            lexer = guess_lexer_for_filename(file_path, content)
            if aliases := getattr(lexer, "aliases", None):
                return aliases[0]
        except Exception:
            pass  # Fall through to fallback map

    # Fallback to hardcoded extension map
    _, ext = os.path.splitext(file_path)
    if ext:
        key = ext.lower().lstrip(".")
        return EXTENSION_LANGUAGE_MAP.get(key, "")

    return ""


def export_project(
    input_dir: str,
    output_file: str,
    config: Dict,
    create_file: bool = True,
    copy_to_buffer: bool = False,
) -> Tuple[dict, int]:
    """
    Main export function: scan, filter, read, format and output project files.
    Returns (files_by_dir dict, total_chars).
    """
    files_by_dir = defaultdict(list)
    all_content: List[str] = []
    processed_paths = set()

    for root, dirs, files in os.walk(input_dir):
        # In-place filter directories
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in config["blacklist_dirs"]]

        for file in files:
            file_path = os.path.join(root, file)

            if not is_code_file(
                file_path,
                config["blacklist_extensions"],
                config["blacklist_dirs"],
                config["blacklist_filenames"],
                config["filename_filter_mode"],
                config["max_size"],
            ):
                continue

            content = read_file_content(file_path)
            if content is None:
                continue

            rel_path = os.path.relpath(file_path, input_dir)
            rel_dir = os.path.dirname(rel_path) or "."
            files_by_dir[rel_dir].append(os.path.basename(file))
            processed_paths.add(rel_path)

            language = detect_language(file_path, content, config)
            lang_tag = language if language else ""

            chunk = f"{rel_path}:\n```{lang_tag}\n{content}\n```\n\n"
            all_content.append(chunk)

    total_chars = sum(len(chunk) for chunk in all_content)
    structure = generate_project_structure(input_dir, processed_paths)
    full_output = structure + "\n# BEGIN FILE CONTENTS\n\n" + "".join(all_content)

    if create_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(full_output)

    if copy_to_buffer and copy_to_clipboard(full_output):
        print("Content copied to clipboard")

    return files_by_dir, total_chars