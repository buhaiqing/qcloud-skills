"""Load project .env into os.environ (shell env wins via setdefault)."""

from __future__ import annotations

import os
from pathlib import Path

from copilot.blackboard import find_repo_root

_COPILOT_PACKAGE = Path(__file__).resolve().parent
_LOADED = False
_ENV_PREFIXES = ("COPILOT_", "TENCENTCLOUD_")


def _find_dotenv(start: Path | None = None) -> Path | None:
    explicit = os.environ.get("TENCENTCLOUD_DOTENV_PATH") or os.environ.get("COPILOT_DOTENV_PATH")
    if explicit:
        path = Path(explicit)
        return path if path.is_file() else None

    for base in (start or Path.cwd(), find_repo_root(), _COPILOT_PACKAGE):
        cur = base.resolve()
        visited: set[Path] = set()
        while cur not in visited:
            visited.add(cur)
            candidate = cur / ".env"
            if candidate.is_file():
                return candidate
            if cur.parent == cur or (cur / ".git").exists():
                break
            cur = cur.parent
    return None


def _parse_dotenv(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key.startswith(_ENV_PREFIXES):
            continue
        result[key] = value.strip().strip("\"'")
    return result


def load_project_dotenv(*, env_path: str | Path | None = None, force: bool = False) -> Path | None:
    """Inject COPILOT_* / TENCENTCLOUD_* from .env. Idempotent; does not override shell env."""
    global _LOADED
    if _LOADED and not force:
        return _find_dotenv()

    path = Path(env_path) if env_path else _find_dotenv()
    if path is None or not path.is_file():
        _LOADED = True
        return None

    for key, value in _parse_dotenv(path).items():
        os.environ.setdefault(key, value)

    _LOADED = True
    return path


def ensure_runtime_env() -> None:
    """Entry-point hook for CLI / engine before CI or tccli operations."""
    load_project_dotenv()
