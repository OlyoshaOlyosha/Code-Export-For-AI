# Contributing to Project2Prompt

Thank you for considering a contribution! This guide covers the basics: reporting problems, setting up a development environment, and submitting changes.

## Reporting a bug

Open an issue with the **Bug report** template. Include:

- Steps to reproduce
- Expected and actual behaviour
- OS, Python version, and how you run the tool

## Suggesting a feature

Open an issue with the **Feature request** template. Describe the problem you are trying to solve first — the best solution may differ from the first idea.

## Development setup

Python 3.10+ is required.

```bash
git clone https://github.com/OlyoshaOlyosha/Project2Prompt.git
cd Project2Prompt
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux / macOS
pip install -r requirements.txt
pip install ruff            # dev-only linter, not in requirements.txt
```

## Running the checks

```bash
python -m pytest -q          # tests
ruff check .                 # lint
ruff format --check .        # formatting
```

CI runs the same commands on every push and pull request (Python 3.10–3.13, Ubuntu + Windows).

## Submitting a pull request

1. Fork the repository and create a branch (`feat/my-feature`, `fix/my-bug`).
2. Make the smallest change that solves the problem.
3. Run the checks above.
4. Open a pull request:
   - reference the issue it solves (`Closes #N`); for anything non-trivial, open an issue first;
   - describe **what** changed and **why**;
   - keep PRs small and focused — one purpose per PR.
5. Make sure CI is green.

## Commit style

Conventional Commits: `type(scope): short imperative summary`, e.g. `fix(scanner): ignore extensionless files in blacklist`. Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `ci`, `chore`.

## Code style

- Line length 120, double quotes (enforced by ruff).
- Type hints where they reduce misuse — not everywhere.
- `pathlib` over `os.path`; no bare `except:`.
- English identifiers, comments, and log messages.
