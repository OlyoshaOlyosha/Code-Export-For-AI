import os
import tkinter as tk
from tkinter import filedialog
import argparse
import time
from collections import defaultdict

# ===== CONFIGURATION =====

def load_config():
    """Load configuration from config.py or use defaults."""
    defaults = {
        'blacklist_extensions': {'txt', 'md', 'png', 'jpg'},
        'blacklist_dirs': {'__pycache__', '.git'},
        'default_output': "output.txt",
        'max_size': 1024 * 1024,
        'output_format': 'txt',
        'create_file': True,
        'copy_to_buffer': False,
        'blacklist_filenames': set(),
        'filename_filter_mode': 'exact'
    }

    try:
        import config
        return {
            'blacklist_extensions': config.BLACKLIST_EXTENSIONS,
            'blacklist_dirs': config.BLACKLIST_DIRS,
            'default_output': config.OUTPUT_FILENAME,
            'output_format': config.OUTPUT_FORMAT,
            'max_size': config.MAX_FILE_SIZE_MB * 1024 * 1024,
            'create_file': config.CREATE_FILE,
            'copy_to_buffer': config.COPY_TO_CLIPBOARD,
            'blacklist_filenames': config.BLACKLIST_FILENAMES,
            'filename_filter_mode': config.FILENAME_FILTER_MODE,
            'use_pygments': getattr(config, 'USE_PYGMENTS', True),
            'extension_language_map': getattr(config, 'EXTENSION_LANGUAGE_MAP', {})
        }
    except ImportError:
        print("config.py not found, using default settings")
        return defaults

# ===== UTILITIES =====

def select_directory():
    """Open a directory selection dialog."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    folder_path = filedialog.askdirectory(title="Select project folder")
    root.destroy()
    return folder_path


def get_next_filename(base_name):
    """Generate a unique filename (append a number if it already exists)."""
    if not os.path.exists(base_name):
        return base_name

    name, ext = os.path.splitext(base_name)
    counter = 1
    while os.path.exists(f"{name}_{counter}{ext}"):
        counter += 1
    return f"{name}_{counter}{ext}"


def copy_to_clipboard(text):
    """Copy text to clipboard in a cross-platform way.

    Tries (in order): pyperclip (if installed), platform native tools:
    - Windows: clip
    - macOS: pbcopy
    - Linux: xclip or xsel
    Returns True on success, False otherwise.
    """
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        pass

    try:
        import subprocess
        import sys
        import shutil

        if sys.platform == 'win32':
            subprocess.run(['clip'], input=text, text=True, check=True)
            return True
        if sys.platform == 'darwin':
            p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, text=True)
            p.communicate(text)
            return p.returncode == 0
        # Linux / other unix
        if shutil.which('xclip'):
            p = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE, text=True)
            p.communicate(text)
            return p.returncode == 0
        if shutil.which('xsel'):
            p = subprocess.Popen(['xsel', '--clipboard', '--input'], stdin=subprocess.PIPE, text=True)
            p.communicate(text)
            return p.returncode == 0
    except Exception as e:
        print(f"Clipboard copy error: {e}")

    return False

# ===== FILE PROCESSING =====

def is_code_file(file_path, blacklist_extensions, blacklist_dirs, blacklist_filenames, filename_filter_mode, max_size=None):
    """Decide whether the file should be included for processing."""
    filename = os.path.basename(file_path)

    # Hidden files
    if filename.startswith('.'):
        return False

    # Filename filtering
    if filename_filter_mode == 'exact' and filename in blacklist_filenames:
        return False
    elif filename_filter_mode == 'contains' and any(pattern in filename for pattern in blacklist_filenames):
        return False

    # Check parent directory
    parent_dir = os.path.basename(os.path.dirname(file_path))
    if parent_dir in blacklist_dirs:
        return False

    # Files without extension
    _, ext = os.path.splitext(filename)
    if not ext:
        return False

    # Blacklisted extensions
    if ext.lower()[1:] in blacklist_extensions:
        return False

    # File size (do this check last because it's relatively slow)
    if max_size and os.path.getsize(file_path) > max_size:
        return False

    return True


def read_file_content(file_path):
    """Read a file, trying common encodings until one succeeds."""
    encodings = ['utf-8', 'cp1251', 'latin-1']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None

    print(f"Failed to read file: {file_path}")
    return None


# ===== LANGUAGE DETECTION =====
def detect_language(file_path, content, config):
    """Detect a language tag for fenced code blocks using settings from config.

    config is the dict returned by load_config(); expects keys:
      - 'use_pygments' (bool)
      - 'extension_language_map' (dict)
    """
    use_pygments = config.get('use_pygments', True)
    extension_map = config.get('extension_language_map', {})

    # Try pygments if enabled
    if use_pygments:
        try:
            from pygments.lexers import guess_lexer_for_filename
            lexer = guess_lexer_for_filename(file_path, content)
            aliases = getattr(lexer, 'aliases', None)
            if aliases:
                return aliases[0]
        except Exception:
            # silently ignore and fall back to extension map
            pass

    # Fallback: extension map from config
    _, ext = os.path.splitext(file_path)
    if ext:
        key = ext.lower().lstrip('.')
        return extension_map.get(key, '')

    return ''

# ===== MAIN LOGIC =====

def process_directory(input_dir, output_file, config, create_file=True, copy_to_buffer=False):
    """Scan a directory and build the combined code output."""
    files_by_dir = defaultdict(list)
    all_content = []

    for root, dirs, files in os.walk(input_dir):
        # Filter directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in config['blacklist_dirs']]

        for file in files:
            file_path = os.path.join(root, file)

            # Check file
            if not is_code_file(file_path, config['blacklist_extensions'], config['blacklist_dirs'],
                              config['blacklist_filenames'], config['filename_filter_mode'], config['max_size']):
                continue

            # Read content
            content = read_file_content(file_path)
            if content is None:
                continue

            # Build output chunk
            rel_path = os.path.relpath(file_path, input_dir)
            rel_dir = os.path.dirname(rel_path) or "."
            files_by_dir[rel_dir].append(os.path.basename(file))

            # detect language for fenced code block
            language = detect_language(file_path, content, config)
            lang_tag = language if language else ''
            file_content = f"{rel_path}:\n```{lang_tag}\n{content}\n```\n\n"
            all_content.append(file_content)

    # Save result
    total_chars = sum(len(chunk) for chunk in all_content)

    if create_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(''.join(all_content))

    if copy_to_buffer:
        if copy_to_clipboard(''.join(all_content)):
            print("Content copied to clipboard")

    return files_by_dir, total_chars


def print_statistics(files_by_dir, total_chars, elapsed_time, output_file, create_file, copy_to_buffer):
    """Print processing statistics."""
    print("\n=== STATISTICS ===")
    print(f"Elapsed time: {elapsed_time:.2f} sec")
    print(f"Characters: {total_chars:,} ({total_chars / 1024:.1f} KB)")

    print("\nFiles by directory:")
    for dir_path in sorted(files_by_dir.keys()):
        files = files_by_dir[dir_path]
        print(f"  {dir_path}: {len(files)} - {', '.join(files)}")

    # Result summary
    result_parts = []
    if create_file:
        result_parts.append(f"saved to {output_file}")
    if copy_to_buffer:
        result_parts.append("copied to clipboard")

    print(f"\nDone! Result: {' and '.join(result_parts)}")

def main():
    start_time = time.time()

    __version__ = "1.0.0"
    __app_name__ = "Code Export For AI"

    print(f"{__app_name__} v{__version__}")

    # Load configuration
    config = load_config()
    create_file = config['create_file']
    copy_to_buffer = config['copy_to_buffer']

    # Ensure at least one output is enabled
    if not create_file and not copy_to_buffer:
        create_file = True
        print("File output enabled (both outputs were disabled)")

    # Parse arguments
    parser = argparse.ArgumentParser(description='Export code to a text format for AI')
    parser.add_argument('-o', '--output', help='Output file name')
    parser.add_argument('-d', '--directory', help='Path to the project directory')
    args = parser.parse_args()
    
    # Select folder
    if args.directory:
        if not os.path.isdir(args.directory):
            print("The specified directory does not exist!")
            return
        input_dir = args.directory
    else:
        print("Select the project folder...")
        input_dir = select_directory()
        if not input_dir:
            print("No folder selected!")
            return
    
    # Determine output file
    output_file = args.output or get_next_filename(config['default_output'])
    
    print(f"Directory: {input_dir}")
    print(f"Output file: {output_file}")
    
    # Process
    files_by_dir, total_chars = process_directory(input_dir, output_file, config, create_file, copy_to_buffer)
    
    # Statistics
    elapsed_time = time.time() - start_time
    print_statistics(files_by_dir, total_chars, elapsed_time, output_file, create_file, copy_to_buffer)
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()