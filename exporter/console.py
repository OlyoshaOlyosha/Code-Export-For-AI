"""Colored console output utilities using Colorama."""

from colorama import Fore, Style, init

# Initialize Colorama once (autoreset=True so each print resets after newline)
init(autoreset=True)


def info(msg: str) -> None:
    """Print informational message (normal/default color)."""
    print(msg)


def warning(msg: str) -> None:
    """Print warning message in yellow."""
    print(Fore.YELLOW + msg)


def error(msg: str) -> None:
    """Print error message in red."""
    print(Fore.RED + msg)


def success(msg: str) -> None:
    """Print success message in green."""
    print(Fore.GREEN + msg)


def header(msg: str) -> None:
    """Print header message in cyan + bold."""
    print(Style.BRIGHT + Fore.CYAN + msg)


def prompt(msg: str) -> str:
    """Print a prompt in light blue and return user input."""
    return input(Fore.LIGHTBLUE_EX + msg + Style.RESET_ALL)
