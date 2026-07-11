"""LC-1 contract artifacts — prompt templates and SKILL cross-links."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

PROMPT_PATHS = [
    REPO_ROOT / "qcloud-copilot/references/agent-inspection-prompt.md",
    REPO_ROOT / "qcloud-proactive-inspection/references/agent-inspection-prompt.md",
]

SKILL_MARKERS = [
    (REPO_ROOT / "qcloud-copilot/SKILL.md", "Agent-Driven Inspection Flow"),
    (REPO_ROOT / "qcloud-proactive-inspection/SKILL.md", "Agent-Driven Inspection Flow"),
]


@pytest.mark.parametrize("path", PROMPT_PATHS, ids=lambda p: p.parent.parent.name)
def test_agent_inspection_prompt_contract(path: Path) -> None:
    assert path.is_file(), f"missing {path}"
    text = path.read_text(encoding="utf-8")
    assert "strategy_schema" in text
    assert "agent_session_v1" in text
    assert "朔州天源" in text
    assert "redis" in text and "topology_count=0" in text
    assert "TODO" not in text
    assert "FIXME" not in text


@pytest.mark.parametrize("skill_path,section", SKILL_MARKERS)
def test_skill_agent_driven_flow_section(skill_path: Path, section: str) -> None:
    text = skill_path.read_text(encoding="utf-8")
    assert section in text
    assert "agent-inspection-prompt.md" in text
