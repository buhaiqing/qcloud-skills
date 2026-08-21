"""Tests for the EVO-1 self-evolution Generator (memory / decision / guard / hooks)."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta

from copilot.evolution import EvolutionPolicy, EvolutionStore
from copilot.evolution.guard import DriftGuard
from copilot.integration.skills import SkillDispatcher
from copilot.models import PlanStep

# --------------------------------------------------------------------------- #
# fixtures / helpers
# --------------------------------------------------------------------------- #


def _write_failure(path, rows):
    path.write_text(
        "## 1. CLI Parameter Errors\n\n"
        "| Skill | Command | Error Pattern | Root Cause | Fix | Count | LastSeen | Severity |\n"
        "|-------|---------|--------------|------------|-----|-------|----------|----------|\n"
        + "\n".join(rows)
        + "\n",
        encoding="utf-8",
    )


def _write_success(path):
    path.write_text(
        "## 1. 高频成功操作（可转化为 allowlist）\n\n"
        "| Skill | Operation | Pattern | success_rate | last_verified |\n"
        "|-------|-----------|---------|--------------|---------------|\n"
        "| `qcloud-cvm-ops` | `describe-special-thing` | works | 0.97 | 2026-06 |\n",
        encoding="utf-8",
    )


def _recent(days_ago: int = 0) -> str:
    """Return a recent LastSeen date so recency-decay tests don't rot over time."""
    return (datetime.now(UTC) - timedelta(days=days_ago)).strftime("%Y-%m-%d")


class FakeQuery:
    def __init__(self, rates):
        self._rates = rates

    def skill_success_rate(self, skill, days=7):
        return self._rates.get(skill, 0.0)


# --------------------------------------------------------------------------- #
# Phase 0 — Memory layer (store)
# --------------------------------------------------------------------------- #


def test_store_parses_failure_patterns(tmp_path):
    fp = tmp_path / "failure-patterns.md"
    _write_failure(
        fp,
        [
            f"| `qcloud-cvm-ops` | `DescribeInstances` | `InvalidParameter` | bad | fix | 12 | {_recent(0)} | critical |",
        ],
    )
    store = EvolutionStore(failure_path=fp)
    pats = store.load()
    assert len(pats) == 1
    p = pats[0]
    assert p.skill == "qcloud-cvm-ops"
    assert p.command == "DescribeInstances"
    assert p.category == "cli_parameter"
    assert p.count == 12
    assert p.kind == "failure"
    assert p.confidence >= 0.7
    assert len(store.high_confidence("failure", 0.7)) == 1


def test_store_skips_non_skill_rows(tmp_path):
    fp = tmp_path / "failure-patterns.md"
    _write_failure(
        fp,
        [
            "| `qcloud-cvm-ops` | `DescribeInstances` | `InvalidParameter` | bad | fix | 5 | 2026-07-10 | major |",
            # placeholder / non-skill row must be ignored
            "| — | `AuthFailure` | `SecretIdNotFound` | creds | check | 3 | — | minor |",
        ],
    )
    store = EvolutionStore(failure_path=fp)
    pats = store.load()
    assert [p.skill for p in pats] == ["qcloud-cvm-ops"]


def test_store_loads_real_failure_patterns():
    store = EvolutionStore()
    if not (store._failure_path.exists()):
        return
    pats = store.load()
    assert len(pats) > 0
    assert all(p.skill.startswith("qcloud-") for p in pats)


def test_store_success_op_allowlist(tmp_path):
    sp = tmp_path / "success-patterns.md"
    _write_success(sp)
    store = EvolutionStore(success_path=sp)
    pol = EvolutionPolicy(store, None)
    allow = pol.op_allowlist("qcloud-cvm-ops")
    assert "describe-special-thing" in allow
    assert "—" not in allow


def test_op_allowlist_filters_low_confidence_success(tmp_path):
    sp = tmp_path / "success-patterns.md"
    sp.write_text(
        "## 1. 高频成功操作（可转化为 allowlist）\n\n"
        "| Skill | Operation | Pattern | success_rate | last_verified |\n"
        "|-------|-----------|---------|--------------|---------------|\n"
        "| `qcloud-cvm-ops` | `describe-special-thing` | works | 0.5 | 2026-06 |\n",
        encoding="utf-8",
    )
    pol = EvolutionPolicy(EvolutionStore(success_path=sp), None)
    assert pol.op_allowlist("qcloud-cvm-ops") == set()


def test_op_allowlist_normalizes_camelcase_to_kebab(tmp_path):
    sp = tmp_path / "success-patterns.md"
    sp.write_text(
        "## 1. 高频成功操作（可转化为 allowlist）\n\n"
        "| Skill | Operation | Pattern | success_rate | last_verified |\n"
        "|-------|-----------|---------|--------------|---------------|\n"
        "| `qcloud-cvm-ops` | `DescribeInstances` | works | 0.97 | 2026-06 |\n",
        encoding="utf-8",
    )
    pol = EvolutionPolicy(EvolutionStore(success_path=sp), None)
    allow = pol.op_allowlist("qcloud-cvm-ops")
    assert "describe-instances" in allow


def test_op_allowlist_uses_count_for_mining_shape(tmp_path):
    # scripts/success_pattern_mine.py emits Count/LastHit, no success_rate/Severity.
    sp = tmp_path / "success-patterns.md"
    sp.write_text(
        "## 1. Winning CLI Operation Patterns\n\n"
        "| Skill | Operation | CommandSignature | FullCommand | Iter | Count | FirstHit | LastHit | Scores | AvgIter |\n"
        "|-------|-----------|------------------|-------------|------|-------|----------|---------|--------|---------|\n"
        "| `qcloud-cvm-ops` | `DescribeInstances` | tccli cvm DescribeInstances | — | 1 | 3 | 2026-08-01 | 2026-08-20 | {} | 1.0 |\n"
        "| `qcloud-cvm-ops` | `TerminateInstances` | tccli cvm TerminateInstances | — | 1 | 1 | 2026-08-20 | 2026-08-20 | {} | 1.0 |\n",
        encoding="utf-8",
    )
    pol = EvolutionPolicy(EvolutionStore(success_path=sp), None)
    allow = pol.op_allowlist("qcloud-cvm-ops")
    # count>=2 -> existence-proven; count==1 -> below floor (fluke)
    assert "describe-instances" in allow
    assert "terminate-instances" not in allow


def test_normalize_op_preserves_digits():
    from copilot.evolution.policy import normalize_op

    assert normalize_op("DescribeInstances") == "describe-instances"
    assert normalize_op("DescribeInstances2") == "describe-instances-2"
    assert normalize_op("GetObjectV1") == "get-object-v-1"
    assert normalize_op("GetObjectV2") == "get-object-v-2"
    assert normalize_op("describe-special-thing") == "describe-special-thing"


# --------------------------------------------------------------------------- #
# Phase 1 — Decision layer (policy)
# --------------------------------------------------------------------------- #


def test_policy_route_hint_flags_high_failure(tmp_path):
    fp = tmp_path / "failure-patterns.md"
    _write_failure(
        fp,
        [
            f"| `qcloud-cvm-ops` | `DescribeInstances` | `InvalidParameter` | bad | fix | 12 | {_recent(0)} | critical |",
            f"| `qcloud-cvm-ops` | `StopInstances` | `MissingParameter` | bad | fix | 11 | {_recent(1)} | critical |",
            f"| `qcloud-cvm-ops` | `TerminateInstances` | `AuthFailure` | bad | fix | 10 | {_recent(2)} | critical |",
        ],
    )
    pol = EvolutionPolicy(EvolutionStore(failure_path=fp), None)
    hint = pol.route_hint("qcloud-cvm-ops")
    assert hint is not None and "qcloud-cvm-ops" in hint
    # skill with no high-confidence failures -> no hint
    assert pol.route_hint("qcloud-redis-ops") is None


def test_policy_route_hint_accepts_intent_object(tmp_path):
    fp = tmp_path / "failure-patterns.md"
    _write_failure(
        fp,
        [
            f"| `qcloud-cvm-ops` | `DescribeInstances` | `InvalidParameter` | bad | fix | 12 | {_recent(0)} | critical |",
            f"| `qcloud-cvm-ops` | `StopInstances` | `MissingParameter` | bad | fix | 11 | {_recent(1)} | critical |",
            f"| `qcloud-cvm-ops` | `TerminateInstances` | `AuthFailure` | bad | fix | 10 | {_recent(2)} | critical |",
        ],
    )

    class _Intent:
        primary = "qcloud-cvm-ops"

    pol = EvolutionPolicy(EvolutionStore(failure_path=fp), None)
    assert pol.route_hint(_Intent()) is not None


def test_policy_recommend_threshold(tmp_path):
    fp = tmp_path / "failure-patterns.md"
    _write_failure(
        fp,
        [
            "| `qcloud-cvm-ops` | `DescribeInstances` | `InvalidParameter` | bad | fix | 12 | 2026-07-10 | critical |",
        ],
    )
    # low success rate + failures -> raises the recommended threshold
    pol = EvolutionPolicy(EvolutionStore(failure_path=fp), FakeQuery({"qcloud-cvm-ops": 0.5}))
    rec = pol.recommend_threshold("qcloud-cvm-ops", "safety")
    assert rec is not None and rec > 0.7

    # no signal at all -> None
    pol2 = EvolutionPolicy(EvolutionStore(failure_path=fp), FakeQuery({}))
    assert pol2.recommend_threshold("qcloud-redis-ops", "safety") is None


# --------------------------------------------------------------------------- #
# Phase 2 — Guard layer
# --------------------------------------------------------------------------- #


def test_guard_clamp():
    g = DriftGuard()
    assert g.clamp(1.5) == 1.0
    assert g.clamp(-0.3) == 0.0
    assert g.clamp(0.4, floor=0.2, ceil=0.9) == 0.4


def test_guard_shadow_deterministic_and_ratio():
    g = DriftGuard()
    assert g.should_use_evolution("run-1") == g.should_use_evolution("run-1")
    assert g.should_use_evolution("") is False
    n = 20000
    frac = sum(1 for i in range(n) if g.should_use_evolution(f"run-{i}")) / n
    assert 0.03 < frac < 0.07


def test_guard_evaluate():
    g = DriftGuard()
    assert g.evaluate(0.9, 0.85) is True  # within tolerance
    assert g.evaluate(0.9, 0.5) is False  # significant drop -> revert
    assert g.evaluate(0.0, 0.0) is True  # no baseline


# --------------------------------------------------------------------------- #
# Phase 3 — Hook points
# --------------------------------------------------------------------------- #


def test_check_h_merges_op_allowlist(tmp_path, monkeypatch):
    import copilot.quality.hallucination as h

    sp = tmp_path / "success-patterns.md"
    _write_success(sp)
    pol = EvolutionPolicy(EvolutionStore(success_path=sp), None)
    monkeypatch.setattr(h, "_get_evolution_policy", lambda: pol)

    # op proven by success patterns must NOT be flagged as unknown
    ok = PlanStep(
        id="s1",
        type="skill_call",
        skill="qcloud-cvm-ops",
        params={"operation": "describe-special-thing"},
    )
    assert h.check_h(ok, use_evolution=True)["passed"] is True

    # a genuinely unknown op is still flagged
    bad = PlanStep(
        id="s2",
        type="skill_call",
        skill="qcloud-cvm-ops",
        params={"operation": "nuke-everything"},
    )
    assert h.check_h(bad, use_evolution=True)["passed"] is False


def test_dispatcher_injects_evolution_warning(tmp_path, monkeypatch):
    class _FakeProc:
        stdout = '{"Response": {"InstanceSet": []}}'
        stderr = ""
        returncode = 0

    def _fake_run(cmd, *a, **k):
        return _FakeProc()

    monkeypatch.setattr(subprocess, "run", _fake_run)

    class _FakePolicy:
        def route_hint(self, skill):
            return "WARN: risky skill"

    disp = SkillDispatcher(evolution_policy=_FakePolicy())
    step = PlanStep(
        id="s1", type="skill_call", skill="qcloud-cvm-ops", params={"operation": "describe"}
    )
    result = disp.execute(step, {})
    assert result.status == "success"
    assert result.output.get("evolution_warning") == "WARN: risky skill"


def test_dispatcher_without_policy_has_no_warning():
    disp = SkillDispatcher()  # default: no evolution policy
    # route_advice must be None-safe when no policy is injected
    assert disp.route_advice("qcloud-cvm-ops") is None


# --------------------------------------------------------------------------- #
# Phase 4 — Feedback signal (engine)
# --------------------------------------------------------------------------- #


def test_engine_record_feedback_emits_adopt(tmp_path, monkeypatch):
    import copilot.engine as engine_mod
    from copilot.observ import ObservableSink as RealSink

    metrics = tmp_path / ".runtime" / "metrics" / "metrics.jsonl"
    sink = RealSink(runtime_root=tmp_path / ".runtime")
    monkeypatch.setattr(engine_mod, "ObservableSink", lambda: sink)

    engine = engine_mod.CopilotEngine()
    engine.record_feedback("sess-1", adopted=True, overridden=False)
    assert metrics.exists()
    text = metrics.read_text()
    assert "copilot_user_adopt" in text
    assert "sess-1" in text
