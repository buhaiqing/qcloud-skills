"""Skill version parser — reads SKILL.md frontmatter and computes content hash.

Per SPEC: extract metadata.version, last_updated; compute SHA of skill file +
references + prompt + rubric for reproducible version identification.
"""
from __future__ import annotations

from dataclasses import dataclass

import hashlib
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None  # yaml is optional; version returns None without it


SKILL_FILE = "SKILL.md"
# Files included in the version hash (order-sensitive)
VERSIONED_FILES = [
    "SKILL.md",
    "references/cli-usage.md",
    "references/api-sdk-usage.md",
    "references/troubleshooting.md",
    "references/rubric.md",
    "references/prompt-templates.md",
    "references/user-experience-spec.md",
]


def _sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:12]


@dataclass
class SkillVersion:
    """Immutable skill version descriptor (SPEC P1.2)."""

    skill_name: str
    version: Optional[str] = None
    last_updated: Optional[str] = None
    sha: Optional[str] = None  # 12-char hex of skill directory content
    cli_applicability: Optional[str] = None

    def is_complete(self) -> bool:
        return bool(self.version and self.sha)


# ---------------------------------------------------------------------------
# Core parser
# ---------------------------------------------------------------------------


def parse_skill_version(skill_dir: Path) -> SkillVersion:
    """Parse SKILL.md frontmatter from a skill directory.

    Computes sha over tracked files for reproducible identification.
    Returns SkillVersion; incomplete fields are None (not empty strings).
    """
    skill_name = skill_dir.name
    skill_md = skill_dir / SKILL_FILE

    if not skill_md.exists():
        return SkillVersion(skill_name=skill_name)

    frontmatter = _parse_yaml_frontmatter(skill_md)
    version = _get_nested(frontmatter, "metadata", "version")
    last_updated = _get_nested(frontmatter, "metadata", "last_updated")
    cli_applicability = _get_nested(frontmatter, "metadata", "cli_applicability")

    sha = _compute_skill_sha(skill_dir)

    return SkillVersion(
        skill_name=skill_name,
        version=version,
        last_updated=last_updated,
        sha=sha,
        cli_applicability=cli_applicability,
    )


def _parse_yaml_frontmatter(skill_md: Path) -> dict:
    """Extract YAML frontmatter (between leading --- and next ---)."""
    if yaml is None:
        return {}
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.index("\n---\n", 3)
    yaml_text = text[3:end].strip()
    try:
        return yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError:
        return {}


def _get_nested(data: dict, *keys: str) -> Optional[str]:
    """Safely extract a string value from nested dict; None if missing."""
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
        if data is None:
            return None
    if isinstance(data, str):
        return data
    return None


def _compute_skill_sha(skill_dir: Path) -> Optional[str]:
    """Compute a combined SHA over versioned files in deterministic order."""
    if yaml is None:
        return None
    hasher = hashlib.sha256()
    for rel_path in VERSIONED_FILES:
        file_path = skill_dir / rel_path
        if not file_path.is_file():
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError:
            continue
        hasher.update(rel_path.encode("utf-8"))
        hasher.update(b"\x00")
        hasher.update(content.encode("utf-8"))
        hasher.update(b"\n")
    digest = hasher.digest()
    if digest == hashlib.sha256().digest():  # empty
        return None
    return digest.hex()[:12]


# ---------------------------------------------------------------------------
# Copilot-level version
# ---------------------------------------------------------------------------

COPILOT_ROOT = Path(__file__).resolve().parents[1]


def copilot_version() -> SkillVersion:
    return parse_skill_version(COPILOT_ROOT)
