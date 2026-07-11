"""Blackboard concurrent write tests (P3-T2)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from copilot.blackboard import BlackboardClient


def _board_dir(tmp_path):
    repo_schema = Path(__file__).resolve().parents[2] / ".runtime" / "blackboard" / "schema.json"
    target_dir = tmp_path / "blackboard"
    target_dir.mkdir()
    target_dir.joinpath("schema.json").write_text(
        repo_schema.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return target_dir


def _contrib(skill: str, hint: str, finding_id: str) -> dict:
    return {
        "version": "1.0.0",
        "verdict": "PASS",
        "findings": [{"id": finding_id, "severity": "INFO", "summary": f"{skill} ok"}],
        "topology_hints": [hint],
        "metadata": {"skill": skill},
    }


def test_ten_threads_ten_skills(tmp_path):
    board_dir = _board_dir(tmp_path)
    client = BlackboardClient(board_dir=board_dir)
    session_id = "ses-concurrent-10"
    client.create(session_id, "10 skills")

    def write(skill_idx: int) -> str:
        skill = f"qcloud-skill-{skill_idx}"
        client.write_contribution(
            session_id, skill, _contrib(skill, f"r-{skill_idx}", f"f-{skill_idx}")
        )
        return skill

    with ThreadPoolExecutor(max_workers=10) as pool:
        skills = list(pool.map(write, range(10)))

    board = client.load(session_id)
    contributions = board["shared_context"]["contributions"]
    assert len(contributions) == 10
    for skill in skills:
        assert skill in contributions


def test_same_skill_merge_preserves_findings(tmp_path):
    board_dir = _board_dir(tmp_path)
    client = BlackboardClient(board_dir=board_dir)
    session_id = "ses-concurrent-merge"
    client.create(session_id, "merge")

    skill = "qcloud-monitor-ops"

    def write_a():
        client.write_contribution(
            session_id,
            skill,
            {
                "version": "1.0.0",
                "verdict": "WARNING",
                "findings": [{"id": "a", "severity": "P1", "summary": "first"}],
                "topology_hints": ["i-a"],
                "metadata": {"source": "a"},
            },
        )

    def write_b():
        client.write_contribution(
            session_id,
            skill,
            {
                "version": "1.0.0",
                "verdict": "WARNING",
                "findings": [{"id": "b", "severity": "P1", "summary": "second"}],
                "topology_hints": ["i-b"],
                "metadata": {"source": "b"},
            },
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(write_a), pool.submit(write_b)]
        for f in as_completed(futures):
            f.result()

    merged = client.read_contributions(session_id)[skill]
    finding_ids = {f["id"] for f in merged["findings"]}
    assert finding_ids == {"a", "b"}
    assert set(merged["topology_hints"]) == {"i-a", "i-b"}
    assert merged["metadata"]["source"] in ("a", "b")
