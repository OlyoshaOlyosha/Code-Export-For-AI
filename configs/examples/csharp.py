"""Example profile: C# / .NET projects (WinForms, WPF, console apps).

The same "declare your filters" pattern as the other examples; the value
here is bin/obj build output staying out of the export.
"""

CONFIG_DESCRIPTION = "C#/.NET projects: sources in, bin/obj build output out"

BLACKLIST_EXTENSIONS = {
    "log", "txt",
    "png", "jpg", "ico",
    "dll", "exe", "pdb",
    "cache",
}

BLACKLIST_DIRS = {"bin", "obj", "packages", ".vs", "TestResults"}

USE_GITIGNORE = True
ALLOWED_EXTENSIONLESS_FILES = {"Dockerfile", "Makefile"}
