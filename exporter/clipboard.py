import shutil
import subprocess
import sys


def copy_to_clipboard(text: str) -> bool:
    """
    Copy text to clipboard in a cross-platform way.

    Order of attempts:
    1. pyperclip (if installed)
    2. Native tools: clip (Windows), pbcopy (macOS), xclip/xsel (Linux)

    Returns True on success, False otherwise.
    """
    # Try pyperclip first
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        pass

    # Fallback to native tools
    try:
        if sys.platform == "win32":
            subprocess.run(["clip"], input=text, text=True, check=True)
            return True

        if sys.platform == "darwin":
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, text=True)
            p.communicate(text)
            return p.returncode == 0

        # Linux
        for cmd in ("xclip", "xsel"):
            if shutil.which(cmd):
                args = ["xclip", "-selection", "clipboard"] if cmd == "xclip" else ["xsel", "--clipboard", "--input"]
                p = subprocess.Popen(args, stdin=subprocess.PIPE, text=True)
                p.communicate(text)
                return p.returncode == 0

    except Exception as e:
        print(f"Clipboard copy error: {e}")

    return False