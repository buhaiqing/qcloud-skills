"""P1.4 — Trace metadata builders.

Provides:
  - build_runtime_info(): captures python/tccli/sdk/git/deployment versions
  - build_skill_info(skill_version): maps SkillVersion (P1.2) to SkillInfo (P1.3)

All detection is best-effort and never raises; missing fields fall back to None.
"""
from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from typing import Optional

from copilot.trace_records import RuntimeInfo, SkillInfo
from copilot.skill_version import SkillVersion


def _detect_tccli_version() -> Optional[str]:
    """Run `tccli --version` and return stdout; None when tccli not installed."""
    try:
        r = subprocess.run(
            ["tccli", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        out = (r.stdout or r.stderr or "").strip()
        if out:
            # Strip leading noise like "Tccli v3.0.1.0\n" → "3.0.1.0"
            parts = out.split()
            for tok in reversed(parts):
                if any(ch.isdigit() for ch in tok) and "." in tok:
                    return tok.strip(",").strip()
            return out.splitlines()[0].strip()
    except Exception:
        return None
    return None


def _detect_sdk_version() -> tuple[Optional[str], Optional[str]]:
    """Probe tencentcloud-sdk-python; return (sdk_name, sdk_version) or (None, None)."""
    try:
        import importlib.metadata as md
    except Exception:
        return (None, None)
    try:
        for candidate in ("tencentcloud-sdk-python", "tencentcloud-sdk-python-sts"):
            try:
                v = md.version(candidate)
                return (candidate, v)
            except Exception:
                continue
    except Exception:
        return (None, None)
    return (None, None)


def _detect_git_commit(start: Optional[Path] = None) -> Optional[str]:
    """Return short HEAD commit hash for the repo containing `start` or cwd()."""
    try:
        cwd = str(start or Path.cwd())
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=cwd,
        )
        if r.returncode == 0:
            return r.stdout.strip() or None
    except Exception:
        return None
    return None


def build_runtime_info() -> RuntimeInfo:
    """Capture runtime environment versions; missing fields are None."""
    py_version = platform.python_version()
    tccli = _detect_tccli_version()
    sdk_name, sdk_version = _detect_sdk_version()
    git_commit = _detect_git_commit()
    deployment_version = os.environ.get("QCLOUD_COPILOT_RELEASE") or os.environ.get("RELEASE_VERSION")

    return RuntimeInfo(
        python_version=py_version,
        tccli_version=tccli,
        sdk_name=sdk_name,
        sdk_version=sdk_version,
        git_commit=git_commit,
        deployment_version=deployment_version,
    )


def build_skill_info(
    skill_version: Optional[SkillVersion],
    *,
    references: Optional[dict] = None,
    prompt_version: Optional[str] = None,
    rubric_version: Optional[str] = None,
    source: Optional[str] = None,
) -> SkillInfo:
    """Map SkillVersion (P1.2) → SkillInfo (P1.3)."""
    if skill_version is None:
        return SkillInfo(
            references=references,
            prompt_version=prompt_version,
            rubric_version=rubric_version,
            source=source,
        )
    sha = f"sha256:{skill_version.sha}" if skill_version.sha else None
    return SkillInfo(
        name=skill_version.skill_name,
        version=skill_version.version,
        source=source,
        skill_file_sha256=sha,
        skill_commit=None,
        references=references,
        prompt_version=prompt_version,
        rubric_version=rubric_version,
    )
