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
- Configurable ignore rules for directories, filenames and extensions (`config.py`).
- Filename filtering with exact or partial matching (`FILENAME_FILTER_MODE`).
- Export project directory structure (ASCII tree) and file contents separately.
- Option to show empty directories in the structure (`SHOW_EMPTY_DIRS`) and include empty files (only in structure, no code block, `INCLUDE_EMPTY_FILES`).
- Save output to a file and/or copy to the clipboard.
- Automatic unique filename generation when output file already exists.
- Clipboard safety limit to avoid pasting huge amounts of text accidentally.
- Print simple statistics (file count, characters, runtime).
- Works with CLI or GUI folder picker (Tkinter).
- Interactive mode – restart export without retyping paths.
- If both structure and content export are disabled, the tool asks whether to enable content export and updates `config.py` automatically.

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

Or provide a folder and output file directly:

```powershell
python main.py -d "C:\path\to\project" -o export.txt
```

3. If you run without `-d`, a folder selection dialog opens. The script will create `output.txt` inside the `outputs/` folder by default and may copy the content to the clipboard if enabled. Clipboard support is cross-platform: the tool uses `pyperclip` when available, otherwise falls back to native utilities (`clip`, `pbcopy`, `xclip`/`xsel`).

After export, the tool asks whether to restart (type `r`) or exit (press Enter). This lets you quickly process another folder without re‑entering the path.

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
The script **requires** a valid `config.py` file in the same folder. It will not run without it. Copy the example `config.py` from the repository and adjust it as needed. Key options:

| Setting | Default | Description |
|---------|---------|-------------|
| `BLACKLIST_EXTENSIONS` | Set of extensions (e.g., `"png"`, `"jpg"`, `"txt"`, `"md"`, `"log"`, `"pyc"`) | File extensions to ignore. |
| `BLACKLIST_DIRS` | Set of directory names | Directories to skip (e.g., `node_modules`, `.git`, `__pycache__`). |
| `BLACKLIST_FILENAMES` | Set of filenames | Specific filenames to ignore. |
| `FILENAME_FILTER_MODE` | `"exact"` | Matching mode for `BLACKLIST_FILENAMES`: `"exact"` or `"contains"`. |
| `OUTPUT_DIR` | `"outputs"` | Default directory where output files are saved. |
| `OUTPUT_FILENAME` | `"output.txt"` | Base name for output file (placed inside `OUTPUT_DIR`). |
| `MAX_FILE_SIZE_MB` | `5` | Maximum file size to include (in MB). |
| `CREATE_FILE` | `True` | Whether to write the output file. |
| `COPY_TO_CLIPBOARD` | `True` | Whether to copy result to clipboard. |
| `EXPORT_STRUCTURE` | `True` | Include project directory structure (ASCII tree) in output. |
| `EXPORT_CONTENT` | `True` | Include file contents (code) in output. |
| `SHOW_EMPTY_DIRS` | `True` | When `EXPORT_STRUCTURE` is `True`, show empty directories in the tree. |
| `INCLUDE_EMPTY_FILES` | `True` | When `EXPORT_CONTENT` is `True`, include empty files (only in structure, no code block). |
| `MAX_CLIPBOARD_CHARS` | `500000` | Maximum characters to copy to clipboard; set to `0` to disable the limit. |

> **Note:** If both `EXPORT_STRUCTURE` and `EXPORT_CONTENT` are set to `False`, the script will ask whether to enable `EXPORT_CONTENT` for this run and automatically update `config.py` for future runs.

Language detection for code fences is based on file extension using a built-in mapping (e.g., `.py` → `python`, `.js` → `javascript`). The mapping can be extended by editing the `EXTENSION_LANGUAGE_MAP` dictionary in `exporter/processor.py` if needed.

## Tips
- For large repositories, increase `MAX_FILE_SIZE_MB` or run on a subset of folders.
- If you rely on clipboard copying on Linux, ensure `xclip` or `xsel` is installed or install `pyperclip`.
- To export only the project structure (without file contents), set `EXPORT_CONTENT = False` in `config.py`.
- If the output is too large for the clipboard, increase `MAX_CLIPBOARD_CHARS` or set it to `0`.
- The tool automatically generates a unique filename (e.g., `output_1.txt`) if the default file already exists.

## Contributing
Improvements welcome — open an issue or submit a pull request.
