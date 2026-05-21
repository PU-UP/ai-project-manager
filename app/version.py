"""Application version helpers."""

from functools import lru_cache
from pathlib import Path
import tomllib


ROOT_DIR = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def get_app_version() -> str:
    """Return the project version from pyproject.toml."""
    try:
        data = tomllib.loads((ROOT_DIR / "pyproject.toml").read_text(encoding="utf-8"))
        return str(data.get("project", {}).get("version") or "0.0.0")
    except OSError:
        return "0.0.0"
