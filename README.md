# Code Export For AI

![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Version](https://img.shields.io/github/v/release/OlyoshaOlyosha/Code-Export-For-AI?label=Version&color=orange)
![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)

Tool to export any project folder or repository into a single, neatly formatted file — ideal for quick AI-assisted code review, debugging and refactoring. The script collects source files recursively, wraps each file in fenced code blocks with relative paths, filters common noise (e.g. `node_modules`, `.git`, images), and produces a paste-ready output or copies it to the clipboard.

## Why use Code Export For AI
- Prepare full project context for AI quickly: paste the entire codebase into ChatGPT/Claude without manual copying.
- Fast code review and debugging: get a consolidated snapshot to ask focused questions about structure, bugs or refactoring.
- Share reproducible context: include relative paths and file order so AI or reviewers can follow the codebase layout.
- Filter and reduce noise: automatically ignore large binaries, images and common vendor folders to keep the export relevant.

## Typical use cases
- Code review and refactoring requests to AI assistants (send whole project context in one paste).
- Pair-programming / debugging sessions where you need to show multiple files at once.
- Student help and tutoring: submit a full assignment for constructive feedback.
- Quick repository snapshots for onboarding, audits or issue reproduction.

## Features
- Recursively scans a directory and collects source files.
- **Multiple configuration profiles** – place `.py` config files in the `configs/` folder and select one at startup.
- Configurable ignore rules for directories, filenames and extensions (per configuration).
- Filename filtering with exact or partial matching (`FILENAME_FILTER_MODE`).
- **.gitignore integration** – automatically respect `.gitignore` rules when `USE_GITIGNORE = True` (reads the `.gitignore` located in the project root).
- **Depth limit** – restrict recursion depth with `MAX_DEPTH` (useful for large monorepos).
- Whitelist for extensionless files (e.g., `Dockerfile`, `Makefile`).
- Export project directory structure (ASCII tree) and file contents separately.
- Option to show empty directories in the structure (`SHOW_EMPTY_DIRS`) and include empty files (only in structure, no code block, `INCLUDE_EMPTY_FILES`).
- Save output to a file and/or copy to the clipboard.
- Clipboard safety limit to avoid pasting huge amounts of text accidentally.
- Print simple statistics (file count, characters, runtime).
- Works with CLI or GUI folder picker (Tkinter).

## Installation / Requirements
- Python 3.10 or higher (recommended).
- Required: `colorama` for colored console output.
- Optional: `pyperclip` for more reliable cross-platform clipboard support (if not installed, the tool falls back to native utilities: `clip`, `pbcopy`, `xclip`/`xsel`).

Install dependencies:

```powershell
# install from project's requirements.txt
pip install -r requirements.txt
```

Or install manually:

```powershell
pip install colorama
# optional, for better clipboard support
pip install pyperclip
```

## Quickstart
1. Open a terminal in the `Code Export For AI` folder.
2. Run:

```powershell
python main.py
```

Or provide a folder, output file, and configuration directly:

```powershell
python main.py -d "C:\path\to\project" -o export.txt -c python
```

- `-d, --directory` – path to project folder (if omitted, a GUI folder picker opens).
- `-o, --output` – output filename (relative to `OUTPUT_DIR/config_name/`).
- `-c, --config` – name of a configuration file from the `configs/` folder (e.g., `python` for `configs/python.py`). If omitted, the tool will:
  - automatically use the only config if exactly one `.py` file exists in `configs/`,
  - show a numbered selection menu if multiple configs are present,
  - fall back to `config.py` in the project root if `configs/` is empty.

Clipboard support is cross-platform: the tool uses `pyperclip` when available, otherwise falls back to native utilities (`clip`, `pbcopy`, `xclip`/`xsel`).

## Sample output
Each file is exported with a relative path header followed by a fenced code block. Example:

````
src/main.py:
```python
def hello():
    print("Hello World")
```
````

````
components/button.js:
```javascript
function Button() {
    return <button>Click me</button>
}
```
````

If `EXPORT_STRUCTURE` is enabled (default), the output begins with a project directory tree, followed by the file contents:

````
```
# Project Directory Structure:
myproject/
├── src/
│   ├── main.py
│   └── utils/
│       └── helpers.py
└── README.md

# BEGIN FILE CONTENTS

src/main.py:
```python
def main():
    print("Hello")
```
````

When `INCLUDE_EMPTY_FILES` is enabled (default), empty files are shown in the structure but have no code block. When `SHOW_EMPTY_DIRS` is enabled, empty directories are also shown.

## Configuration
The script expects configuration files inside the `configs/` folder (or a legacy `config.py` in the project root). Copy the example `config.py` from the repository into `configs/` and adjust it as needed. You can maintain multiple profiles (e.g., `python.py`, `frontend.py`) and switch between them using the `-c` flag.

**Note on output location:** The final output is saved in a subdirectory named after the configuration file (without `.py`) inside `OUTPUT_DIR`. For example, if `OUTPUT_DIR = "outputs"` and you use `python.py`, the file will be placed in `outputs/python/`.

Key options (inside a `.py` config file):

| Setting | Default | Description |
|---------|---------|-------------|
| `BLACKLIST_EXTENSIONS` | Set of extensions (e.g., `"png"`, `"jpg"`, `"txt"`, `"md"`, `"log"`, `"pyc"`) | File extensions to ignore. |
| `ALLOWED_EXTENSIONLESS_FILES` | `{"Dockerfile", "Makefile", "README", "LICENSE"}` | Filenames without extension that should be included. |
| `BLACKLIST_DIRS` | Set of directory names | Directories to skip (e.g., `node_modules`, `.git`, `__pycache__`). |
| `BLACKLIST_FILENAMES` | Set of filenames | Specific filenames to ignore. |
| `FILENAME_FILTER_MODE` | `"exact"` | Matching mode for `BLACKLIST_FILENAMES`: `"exact"` or `"contains"`. |
| `USE_GITIGNORE` | `True` | If `True`, also respect `.gitignore` rules in addition to blacklists. The `.gitignore` file must be in the root of the exported project. |
| `MAX_DEPTH` | `-1` | Maximum recursion depth: `-1` = unlimited, `0` = only selected directory, positive integer = max depth. |
| `OUTPUT_DIR` | `"outputs"` | Base directory where output files are saved. A subfolder with the configuration name will be created automatically. |
| `OUTPUT_FILENAME` | `"output.txt"` | Base name for output file (placed inside `OUTPUT_DIR/config_name/`). |
| `MAX_FILE_SIZE_MB` | `5` | Maximum file size to include (in MB). |
| `CREATE_FILE` | `True` | Whether to write the output file. |
| `COPY_TO_CLIPBOARD` | `True` | Whether to copy result to clipboard. |
| `EXPORT_STRUCTURE` | `True` | Include project directory structure (ASCII tree) in output. |
| `EXPORT_CONTENT` | `True` | Include file contents (code) in output. |
| `SHOW_EMPTY_DIRS` | `True` | When `EXPORT_STRUCTURE` is `True`, show empty directories in the tree. |
| `INCLUDE_EMPTY_FILES` | `True` | When `EXPORT_CONTENT` is `True`, include empty files (only in structure, no code block). |
| `MAX_CLIPBOARD_CHARS` | `500000` | Maximum characters to copy to clipboard; set to `0` to disable the limit. |

> **Note:** If both `EXPORT_STRUCTURE` and `EXPORT_CONTENT` are set to `False`, the script will ask whether to enable `EXPORT_CONTENT` for this run and automatically update the configuration file for future runs.

Language detection for code fences is based on file extension using a built-in mapping (e.g., `.py` → `python`, `.js` → `javascript`). The mapping can be extended by editing the `EXTENSION_LANGUAGE_MAP` dictionary in `exporter/processor.py` if needed.

## Tips
- For large repositories, increase `MAX_FILE_SIZE_MB` or use `MAX_DEPTH` to limit traversal.
- If you rely on clipboard copying on Linux, ensure `xclip` or `xsel` is installed or install `pyperclip`.
- To export only the project structure (without file contents), set `EXPORT_CONTENT = False` in your configuration.
- If the output is too large for the clipboard, increase `MAX_CLIPBOARD_CHARS` or set it to `0`.
- Create multiple configuration files in `configs/` for different project types (e.g., Python-only, frontend-only) and switch with `-c`.

## Contributing
Improvements welcome — open an issue or submit a pull request.