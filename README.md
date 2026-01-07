# Code Export For AI

![Python](https://img.shields.io/badge/Python-3.6%2B-blue.svg)
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
- Recursively scans a directory and collects source files
- Configurable ignore rules for directories, filenames and extensions (`config.py`)
- Save output to a file and/or copy to the clipboard
- Print simple statistics (file count, characters, runtime)
- Works with CLI or GUI folder picker (Tkinter)

## Installation / Requirements
- Requires Python 3.6+ (recommended)

- Optional clipboard support: install `pyperclip` (recommended for macOS/Linux or for a more reliable cross-platform clipboard).

Install optional dependency (one of the options below):

```powershell
# install only pyperclip
pip install pyperclip

# or install from project's requirements.txt
pip install -r requirements.txt
```

## Quickstart
1. Open a terminal in the `Code Export For AI` folder.
2. Run:

```powershell
python code_export_for_AI.py
```

Or provide a folder and output file directly:

```powershell
python code_export_for_AI.py -d "C:\path\to\project" -o export.txt
```

3. If you run without `-d`, a folder selection dialog opens. The script will create `output.txt` by default and may copy the content to the clipboard if enabled. Clipboard support is cross-platform: the tool uses `pyperclip` when available, otherwise falls back to native utilities (`clip`, `pbcopy`, `xclip`/`xsel`).

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

## Configuration
The script loads `config.py` from the same folder (if present). Defaults are used otherwise. Key options:

- `BLACKLIST_EXTENSIONS` — set of file extensions to ignore
- `BLACKLIST_DIRS` — directories to skip (e.g. `node_modules`, `.git`)
- `OUTPUT_FILENAME` — default output file name
- `MAX_FILE_SIZE_MB` — maximum file size to include
- `CREATE_FILE` — whether to write the output file
- `COPY_TO_CLIPBOARD` — whether to copy result to clipboard
- `BLACKLIST_FILENAMES` — filenames to ignore
- `FILENAME_FILTER_MODE` — `'exact'` or `'contains'`
- `FILENAME_FILTER_MODE` — `'exact'` or `'contains'`
- `USE_PYGMENTS` — (bool) enable `pygments`-based detection of fenced-code language tags (default: `True`).
- `EXTENSION_LANGUAGE_MAP` — dict mapping extensions (no dot) to language tags used in fenced code blocks. Used as a fallback and fully user-overridable.

When `USE_PYGMENTS` is enabled and `pygments` is installed the script will try to auto-detect language aliases from filename+content; otherwise it falls back to `EXTENSION_LANGUAGE_MAP`. If no language is found the code fence remains untagged. To customize, edit `config.py`.

## Tips
- For large repositories, increase `MAX_FILE_SIZE_MB` or run on a subset of folders.
- If you rely on clipboard copying on Linux, ensure `xclip` or `xsel` is installed or install `pyperclip`.

## Contributing
Improvements welcome — open an issue or submit a pull request.
