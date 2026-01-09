import argparse
import os
import time
from typing import Dict, Any

from exporter.processor import export_project
from exporter.utils import get_next_filename, print_statistics, select_directory


def load_config() -> Dict[str, Any]:
    """Load configuration from config.py."""
    try:
        import config

        print("Configuration loaded from config.py")

        return {
            'blacklist_extensions': getattr(config, 'BLACKLIST_EXTENSIONS', set()),
            'blacklist_dirs': getattr(config, 'BLACKLIST_DIRS', set()),
            'blacklist_filenames': getattr(config, 'BLACKLIST_FILENAMES', set()),
            'filename_filter_mode': getattr(config, 'FILENAME_FILTER_MODE', 'exact'),

            'default_output': getattr(config, 'OUTPUT_FILENAME', 'output.txt'),
            'output_format': getattr(config, 'OUTPUT_FORMAT', 'txt'),
            'max_size': getattr(config, 'MAX_FILE_SIZE_MB', 1) * 1024 * 1024,
            'create_file': getattr(config, 'CREATE_FILE', True),
            'copy_to_buffer': getattr(config, 'COPY_TO_CLIPBOARD', True),

            'use_pygments': getattr(config, 'USE_PYGMENTS', True),
            'show_progress': getattr(config, 'SHOW_PROGRESS', True),
            'include_empty_files': getattr(config, 'INCLUDE_EMPTY_FILES', False),
            'export_structure': getattr(config, 'EXPORT_STRUCTURE', True),
            'export_content': getattr(config, 'EXPORT_CONTENT', True),
        }

    except ImportError:
        print("ERROR: config.py not found!")
        print("Please copy config.py from the repository: https://github.com/OlyoshaOlyosha/Code-Export-For-AI")
        print("The tool requires proper configuration to filter out binaries, vendor folders, etc.")
        print("Running with empty filters — this may include unwanted files and make output huge.")

        return {
            'blacklist_extensions': set(),
            'blacklist_dirs': set(),
            'blacklist_filenames': set(),
            'filename_filter_mode': 'exact',
            'default_output': 'output.txt',
            'output_format': 'txt',
            'max_size': 1 * 1024 * 1024,
            'create_file': True,
            'copy_to_buffer': True,
            'use_pygments': True,
            'show_progress': True,
            'include_empty_files': False,
            'export_structure': getattr(config, 'EXPORT_STRUCTURE', True),
            'export_content': getattr(config, 'EXPORT_CONTENT', True),
        }
    except AttributeError as e:
        print(f"WARNING: Missing setting in config.py: {e}")
        print("Using safe fallback values.")

        return load_config()


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

    # Check export options
    if not config.get('export_structure', True) and not config.get('export_content', True):
        print("WARNING: Both EXPORT_STRUCTURE and EXPORT_CONTENT are disabled in config.py.")
        print("Nothing will be exported!")
        print("Do you want to enable code export (EXPORT_CONTENT=True) for this run?")
        print("Press Enter for Yes, or type n and Enter to exit: ", end="")
        
        response = input().strip().lower()
        
        if response == '' or response.startswith('y'):
            try:
                with open('config.py', 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                with open('config.py', 'w', encoding='utf-8') as f:
                    for line in lines:
                        if line.strip().startswith('EXPORT_CONTENT'):
                            f.write('EXPORT_CONTENT = True    # Include file contents (code) in output\n')
                        else:
                            f.write(line)

                print("Updated config.py: EXPORT_CONTENT set to True permanently.")
                config['export_content'] = True
                print("Continuing with code export enabled...\n")
            except Exception as e:
                print(f"Failed to update config.py: {e}")
                print("Enabled only for this run.")
                config['export_content'] = True
        else:
            print("Exiting — no content to export.")
            return

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