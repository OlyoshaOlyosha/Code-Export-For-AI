"""Guard tests: every shipped config profile must load cleanly (issue #10)."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Built once at collection time. The is_file() filter keeps the suite green in
# exotic checkouts where configs/examples/ or configs/config.py is absent
# (empty list -> parametrize skips instead of failing).
_PROFILE_PATHS = [
    p
    for p in sorted((REPO_ROOT / "configs" / "examples").glob("*.py")) + [REPO_ROOT / "configs" / "config.py"]
    if p.is_file()
]


@pytest.mark.parametrize("config_path", _PROFILE_PATHS, ids=lambda p: p.name)
def test_shipped_profile_loads_with_required_keys(config_path: Path) -> None:
    """Each shipped profile must load via load_config and expose core keys."""
    from main import load_config

    config = load_config(config_path)
    assert isinstance(config, dict)
    for key in ("blacklist_extensions", "output_dir", "max_depth"):
        assert key in config, f"Missing key {key!r} in {config_path.name}"
