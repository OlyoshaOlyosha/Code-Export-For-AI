"""
User-configurable settings for Code Export For AI.
Edit this file to customize behavior without touching the code.
"""

# File extensions to ignore (without dot)
BLACKLIST_EXTENSIONS = {
    'txt', 'md', 'markdown', 'log', 'pdf', 'doc', 'docx', 'xls', 'xlsx',
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'ico', 'svg', 'webp',
    'mp3', 'mp4', 'avi', 'mov', 'wav',
    'zip', 'rar', '7z', 'tar', 'gz',
    'exe', 'dll', 'so', 'bin', 'o', 'obj',
    'pyc', 'pyo', 'pyd', 'class',
    'db', 'sqlite', 'mdb',
    'ini', 'cfg', 'conf', 'config', 'env'
}

# Directories to ignore
BLACKLIST_DIRS = {
    '__pycache__', '.git', '.vscode', '.vs', '.idea', 'node_modules',
    'obj', 'bin', 'venv', 'env', 'virtualenv', 'dist', 'build', 'target', 'packages'
}

# Output settings
OUTPUT_FORMAT = 'txt'          # 'txt' or 'md'
OUTPUT_FILENAME = "output.txt"

# Limits and behavior
MAX_FILE_SIZE_MB = 1
CREATE_FILE = True
COPY_TO_CLIPBOARD = True

# File filtering
BLACKLIST_FILENAMES = {'__init__.py', 'setup.py', 'requirements.txt'}
FILENAME_FILTER_MODE = 'exact'  # 'exact' or 'contains'
INCLUDE_EMPTY_FILES = False
SHOW_PROGRESS = True

# Language detection
USE_PYGMENTS = True

EXTENSION_LANGUAGE_MAP = {
    'py': 'python', 'pyw': 'python',
    'js': 'javascript', 'mjs': 'javascript', 'cjs': 'javascript',
    'ts': 'typescript', 'jsx': 'jsx', 'tsx': 'tsx',
    'java': 'java',
    'c': 'c', 'h': 'c',
    'cpp': 'cpp', 'cc': 'cpp', 'cxx': 'cpp', 'hpp': 'cpp',
    'cs': 'csharp',
    'go': 'go', 'rs': 'rust', 'rb': 'ruby', 'php': 'php',
    'sh': 'bash', 'bash': 'bash',
    'ps1': 'powershell', 'psm1': 'powershell', 'psd1': 'powershell',
    'html': 'html', 'htm': 'html', 'css': 'css',
    'json': 'json', 'yml': 'yaml', 'yaml': 'yaml', 'xml': 'xml',
    'sql': 'sql', 'md': 'markdown', 'markdown': 'markdown',
    'dockerfile': 'dockerfile', 'makefile': 'makefile',
    'txt': '', 'ini': 'ini', 'toml': 'toml',
    'gradle': 'groovy', 'groovy': 'groovy',
    'dart': 'dart', 'kt': 'kotlin', 'kts': 'kotlin',
    'scala': 'scala', 'jl': 'julia', 'r': 'r',
    'swift': 'swift', 'erl': 'erlang', 'hs': 'haskell',
}