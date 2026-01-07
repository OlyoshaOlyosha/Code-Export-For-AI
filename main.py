import argparse
import os
import time
from typing import Dict

from exporter.processor import export_project
from exporter.utils import get_next_filename, print_statistics, select_directory


def load_config() -> Dict[str, any]:
    """Load configuration from config.py or return defaults."""
    defaults = {
        'blacklist_extensions': {'txt', 'md', 'png', 'jpg'},
        'blacklist_dirs': {'__pycache__', '.git'},
        'default_output': "output.txt",
        'max_size': 1024 * 1024,
        'output_format': 'txt',
        'create_file': True,
        'copy_to_buffer': False,
        'blacklist_filenames': set(),
        'filename_filter_mode': 'exact',
        'use_pygments': True,
        'extension_language_map': {}
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
            'extension_language_map': getattr(config, 'EXTENSION_LANGUAGE_MAP', {}),
        }
    except ImportError:
        print("config.py not found, using default settings")
        return defaults


def main() -> None:
    __version__ = "1.0.0"
    __app_name__ = "Code Export For AI"

    print(f"{__app_name__} v{__version__}")

    config = load_config()
    create_file = config['create_file']
    copy_to_buffer = config['copy_to_buffer']

    if not create_file and not copy_to_buffer:
        create_file = True
        print("File output enabled (both outputs were disabled)")

    parser = argparse.ArgumentParser(description="Export code project to a single file for AI review")
    parser.add_argument('-o', '--output', help='Output file name')
    parser.add_argument('-d', '--directory', help='Path to the project directory')
    args = parser.parse_args()

    # Select input directory
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

    start_time = time.time()

    files_by_dir, total_chars = export_project(
        input_dir, output_file, config, create_file, copy_to_buffer
    )

    elapsed_time = time.time() - start_time
    print_statistics(files_by_dir, total_chars, elapsed_time, output_file, create_file, copy_to_buffer)

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()