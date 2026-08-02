"""P0-3 IncidentStateMachine unit tests — TDD red→green.

Covers SPEC §8 Self-check / DoD:
  - 7 states + cancel/reopen replayable
  - happy-path full chain detected→…→reviewed (state + timestamps set)
  - invalid transition → InvalidTransitionError
  - concurrency (expected_state mismatch) → StaleStateError
  - cancel from mid state → CANCELLED
  - reopen: RESOLVED + REOPEN → DETECTED
  - SLA escalation (beyond sla_minutes) → sla_escalated + escalation_path
  - replay() idempotent (replay twice → identical final record)
  - dwell_stats exact mttd/mtta/mttr values
  - no credentials in JSONL records

Run: python3 -m pytest scripts/test_incident_state.py -q
     (or) python3 -m unittest scripts.test_incident_state
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys_path = str(ROOT / "qcloud-copilot")
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from copilot.incident_state import (
    IncidentEvent,
    IncidentRecord,
    IncidentState,
    IncidentStateMachine,
    InvalidTransitionError,
    StaleStateError,
    dwell_stats,
    replay,
)

_T = "2026-01-01T00:00:00+00:00"


def _base(state: IncidentState = IncidentState.DETECTED) -> IncidentRecord:
    return IncidentRecord(
        incident_id="INC-1",
        state=state,
        severity="P1",
        detected_at=_T,
    )


class TransitionTableTests(unittest.TestCase):
    def test_valid_transitions_known_pairs(self) -> None:
        sm = IncidentStateMachine()
        pairs = dict(sm.valid_transitions(IncidentState.DETECTED))
        self.assertEqual(pairs[IncidentEvent.CORRELATE], IncidentState.CORRELATED)

        pairs = dict(sm.valid_transitions(IncidentState.RESOLVED))
        self.assertEqual(pairs[IncidentEvent.REVIEW], IncidentState.REVIEWED)
        self.assertEqual(pairs[IncidentEvent.REOPEN], IncidentState.DETECTED)

    def test_escalate_is_terminal_same_state_all_nonterminal(self) -> None:
        sm = IncidentStateMachine()
        for st in (IncidentState.DETECTED, IncidentState.CORRELATED, IncidentState.DIAGNOSED,
                   IncidentState.MITIGATING, IncidentState.VERIFYING):
            to = dict(sm.valid_transitions(st)).get(IncidentEvent.ESCALATE)
            self.assertEqual(to, st, f"escalate from {st} should stay in {st}")

    def test_reviewed_is_terminal(self) -> None:
        sm = IncidentStateMachine()
        # no forward transitions out of terminal states
        for st in (IncidentState.REVIEWED, IncidentState.CANCELLED):
            self.assertEqual(sm.valid_transitions(st), [])


class HappyPathTests(unittest.TestCase):
    def test_full_chain_to_reviewed(self) -> None:
        sm = IncidentStateMachine()
        r = _base()
        steps = [
            (IncidentEvent.CORRELATE, IncidentState.CORRELATED, "correlated_at"),
            (IncidentEvent.DIAGNOSE, IncidentState.DIAGNOSED, "diagnosed_at"),
            (IncidentEvent.MITIGATE, IncidentState.MITIGATING, "mitigating_at"),
            (IncidentEvent.VERIFY, IncidentState.VERIFYING, "verifying_at"),
            (IncidentEvent.RESOLVE, IncidentState.RESOLVED, "resolved_at"),
            (IncidentEvent.REVIEW, IncidentState.REVIEWED, "reviewed_at"),
        ]
        for event, expected_state, ts_field in steps:
            r = sm.transition(r, event, actor="ops")
            self.assertEqual(r.state, expected_state)
            self.assertIsNotNone(getattr(r, ts_field), f"{ts_field} should be set")

    def test_transition_returns_new_record_not_mutated(self) -> None:
        sm = IncidentStateMachine()
        r = _base()
        r2 = sm.transition(r, IncidentEvent.CORRELATE, actor="ops")
        self.assertIsNot(r, r2, "transition must return a NEW record")
        self.assertEqual(r.state, IncidentState.DETECTED, "input record must not be mutated")
        self.assertEqual(r2.state, IncidentState.CORRELATED)

    def test_action_log_appended(self) -> None:
        sm = IncidentStateMachine()
        r = sm.transition(_base(), IncidentEvent.CORRELATE, actor="ops", note="linked alarm")
        self.assertEqual(len(r.action_log), 1)
        entry = r.action_log[0]
        self.assertEqual(entry["event"], "correlate")
        self.assertEqual(entry["state"], "correlated")
        self.assertEqual(entry["actor"], "ops")
        self.assertEqual(entry["note"], "linked alarm")
        self.assertIn("at", entry)


class InvalidTransitionTests(unittest.TestCase):
    def test_detected_resolve_is_invalid(self) -> None:
        sm = IncidentStateMachine()
        with self.assertRaises(InvalidTransitionError):
            sm.transition(_base(), IncidentEvent.RESOLVE)

    def test_reviewed_has_no_transitions(self) -> None:
        sm = IncidentStateMachine()
        r = _base(IncidentState.REVIEWED)
        for ev in IncidentEvent:
            with self.assertRaises(InvalidTransitionError):
                sm.transition(r, ev)

    def test_cancelled_is_terminal(self) -> None:
        sm = IncidentStateMachine()
        r = _base(IncidentState.CANCELLED)
        with self.assertRaises(InvalidTransitionError):
            sm.transition(r, IncidentEvent.CORRELATE)


class ConcurrencyTests(unittest.TestCase):
    def test_stale_state_error(self) -> None:
        sm = IncidentStateMachine()
        r = _base(IncidentState.DIAGNOSED)  # actual state
        with self.assertRaises(StaleStateError):
            sm.transition(r, IncidentEvent.MITIGATE, expected_state=IncidentState.DETECTED)

    def test_expected_state_match_succeeds(self) -> None:
        sm = IncidentStateMachine()
        r = _base()
        r2 = sm.transition(r, IncidentEvent.CORRELATE, expected_state=IncidentState.DETECTED)
        self.assertEqual(r2.state, IncidentState.CORRELATED)


class CancelReopenTests(unittest.TestCase):
    def test_cancel_from_mid_state(self) -> None:
        sm = IncidentStateMachine()
        r = _base()
        r = sm.transition(r, IncidentEvent.CORRELATE)
        r = sm.transition(r, IncidentEvent.DIAGNOSE)
        r = sm.transition(r, IncidentEvent.CANCEL, actor="ops")
        self.assertEqual(r.state, IncidentState.CANCELLED)
        self.assertIsNotNone(r.cancelled_at)

    def test_reopen_resolved(self) -> None:
        sm = IncidentStateMachine()
        r = _base()
        for ev in (IncidentEvent.CORRELATE, IncidentEvent.DIAGNOSE, IncidentEvent.MITIGATE,
                   IncidentEvent.VERIFY, IncidentEvent.RESOLVE):
            r = sm.transition(r, ev)
        self.assertEqual(r.state, IncidentState.RESOLVED)
        r2 = sm.transition(r, IncidentEvent.REOPEN)
        self.assertEqual(r2.state, IncidentState.DETECTED)
        # reopen from a non-resolved state is invalid
        with self.assertRaises(InvalidTransitionError):
            sm.transition(_base(IncidentState.DIAGNOSED), IncidentEvent.REOPEN)


class EscalationTests(unittest.TestCase):
    def test_escalate_sets_flag_and_path(self) -> None:
        sm = IncidentStateMachine(sla_minutes={"diagnosed": 30})
        r = _base()
        for ev in (IncidentEvent.CORRELATE, IncidentEvent.DIAGNOSE):
            r = sm.transition(r, ev)
        # diagnosed at 10min < 30min sla → not escalated on this path
        r = sm.transition(r, IncidentEvent.ESCALATE, actor="sre-1")
        self.assertEqual(r.state, IncidentState.DIAGNOSED, "escalate keeps same state")
        self.assertTrue(r.sla_escalated)
        self.assertIn({"actor": "sre-1"}, r.escalation_path)

    def test_escalate_appends_multiple(self) -> None:
        sm = IncidentStateMachine(sla_minutes={"diagnosed": 30})
        r = _base()
        for ev in (IncidentEvent.CORRELATE, IncidentEvent.DIAGNOSE):
            r = sm.transition(r, ev)
        r = sm.transition(r, IncidentEvent.ESCALATE, actor="sre-1")
        r = sm.transition(r, IncidentEvent.ESCALATE, actor="manager")
        self.assertEqual(len(r.escalation_path), 2)
        self.assertEqual(r.escalation_path[-1]["actor"], "manager")

    def test_sla_breached_detects_over_limit(self) -> None:
        sm = IncidentStateMachine(sla_minutes={"diagnosed": 30})
        r = IncidentRecord(
            incident_id="INC-1", state=IncidentState.DIAGNOSED, severity="P1",
            diagnosed_at="2026-01-01T00:10:00+00:00",
        )
        # now=00:50 → 40min dwell > 30min sla → breached
        self.assertTrue(sm.sla_breached(r, now="2026-01-01T00:50:00+00:00"))

    def test_sla_breached_false_within_limit(self) -> None:
        sm = IncidentStateMachine(sla_minutes={"diagnosed": 30})
        r = IncidentRecord(
            incident_id="INC-1", state=IncidentState.DIAGNOSED, severity="P1",
            diagnosed_at="2026-01-01T00:10:00+00:00",
        )
        # now=00:20 → 10min dwell < 30min sla → not breached
        self.assertFalse(sm.sla_breached(r, now="2026-01-01T00:20:00+00:00"))

    def test_sla_breached_no_config_returns_false(self) -> None:
        sm = IncidentStateMachine()  # 无 sla_minutes 配置
        r = IncidentRecord(
            incident_id="INC-1", state=IncidentState.CORRELATED, severity="P1",
            correlated_at="2026-01-01T00:00:00+00:00",
        )
        self.assertFalse(sm.sla_breached(r, now="2026-01-01T01:00:00+00:00"))


class ReplayTests(unittest.TestCase):
    def test_replay_reconstructs_state(self) -> None:
        log = [
            {"event": "correlate", "state": "correlated", "at": "2026-01-01T00:05:00+00:00", "actor": "ops", "note": ""},
            {"event": "diagnose", "state": "diagnosed", "at": "2026-01-01T00:10:00+00:00", "actor": "ops", "note": ""},
            {"event": "mitigate", "state": "mitigating", "at": "2026-01-01T00:20:00+00:00", "actor": "ops", "note": ""},
            {"event": "verify", "state": "verifying", "at": "2026-01-01T00:25:00+00:00", "actor": "ops", "note": ""},
            {"event": "resolve", "state": "resolved", "at": "2026-01-01T00:35:00+00:00", "actor": "ops", "note": ""},
            {"event": "review", "state": "reviewed", "at": "2026-01-01T00:40:00+00:00", "actor": "ops", "note": ""},
        ]
        r = replay(log)
        self.assertEqual(r.state, IncidentState.REVIEWED)
        self.assertEqual(r.resolved_at, "2026-01-01T00:35:00+00:00")

    def test_replay_idempotent(self) -> None:
        log = [
            {"event": "correlate", "state": "correlated", "at": "2026-01-01T00:05:00+00:00", "actor": "ops", "note": ""},
            {"event": "diagnose", "state": "diagnosed", "at": "2026-01-01T00:10:00+00:00", "actor": "ops", "note": ""},
        ]
        r1 = replay(log)
        r2 = replay(log)
        self.assertEqual(r1.state, r2.state)
        self.assertEqual(r1.diagnosed_at, r2.diagnosed_at)
        self.assertEqual([e["event"] for e in r1.action_log], [e["event"] for e in r2.action_log])

    def test_replay_cancel_chain(self) -> None:
        log = [
            {"event": "correlate", "state": "correlated", "at": "2026-01-01T00:05:00+00:00", "actor": "ops", "note": ""},
            {"event": "cancel", "state": "cancelled", "at": "2026-01-01T00:06:00+00:00", "actor": "ops", "note": ""},
        ]
        r = replay(log)
        self.assertEqual(r.state, IncidentState.CANCELLED)
        self.assertIsNotNone(r.cancelled_at)


class DwellTests(unittest.TestCase):
    def test_dwell_stats_exact(self) -> None:
        rec = IncidentRecord(
            incident_id="INC-1",
            state=IncidentState.REVIEWED,
            severity="P1",
            detected_at="2026-01-01T00:00:00+00:00",
            correlated_at="2026-01-01T00:05:00+00:00",
            diagnosed_at="2026-01-01T00:10:00+00:00",
            mitigating_at="2026-01-01T00:20:00+00:00",
            verifying_at="2026-01-01T00:25:00+00:00",
            resolved_at="2026-01-01T00:35:00+00:00",
            reviewed_at="2026-01-01T00:40:00+00:00",
        )
        stats = dwell_stats(rec)
        self.assertEqual(stats["mttd_min"], 5.0)
        self.assertEqual(stats["mtta_min"], 10.0)
        self.assertEqual(stats["mttr_min"], 35.0)
        self.assertEqual(stats["detected"], 5.0)
        self.assertEqual(stats["correlated"], 5.0)
        self.assertEqual(stats["diagnosed"], 10.0)
        self.assertEqual(stats["mitigating"], 5.0)
        self.assertEqual(stats["verifying"], 10.0)
        self.assertEqual(stats["resolved"], 5.0)
        self.assertEqual(stats["reviewed"], 0.0)  # terminal, no next state

    def test_dwell_unset_uses_zero(self) -> None:
        stats = dwell_stats(_base())
        self.assertEqual(stats["mttd_min"], 0.0)
        self.assertEqual(stats["mtta_min"], 0.0)
        self.assertEqual(stats["mttr_min"], 0.0)

    def test_dwell_cancelled(self) -> None:
        rec = IncidentRecord(
            incident_id="INC-1",
            state=IncidentState.CANCELLED,
            severity="P1",
            detected_at="2026-01-01T00:00:00+00:00",
            correlated_at="2026-01-01T00:05:00+00:00",
            cancelled_at="2026-01-01T00:08:00+00:00",
        )
        stats = dwell_stats(rec)
        self.assertEqual(stats["detected"], 5.0)
        self.assertEqual(stats["correlated"], 3.0)  # cancelled_at - correlated_at


class CredentialsTests(unittest.TestCase):
    def test_replay_structure_has_no_credentials(self) -> None:
        # 状态机/回放产生的结构（action_log / escalation_path / 时间戳 / 状态字段）
        # 不引入任何凭据字段名或凭据值：合法 action_log 回放后序列化应不含凭据字面量。
        log = [
            {"event": "correlate", "state": "correlated", "at": _T, "actor": "ops", "note": "linked alarm"},
            {"event": "diagnose", "state": "diagnosed", "at": "2026-01-01T00:10:00+00:00", "actor": "ops", "note": "root cause found"},
        ]
        rec = replay(log)
        blob = json.dumps(
            {
                "incident_id": rec.incident_id,
                "state": rec.state.value,
                "action_log": rec.action_log,
                "escalation_path": rec.escalation_path,
                "detected_at": rec.detected_at,
            }
        )
        self.assertNotIn("AKID", blob)
        self.assertNotIn("SK-", blob)
        self.assertNotIn("secret", blob.lower())
        self.assertNotIn("SecretKey", blob)

    def test_escalation_path_does_not_carry_credentials(self) -> None:
        sm = IncidentStateMachine()
        rec = _base()
        rec = sm.transition(rec, IncidentEvent.ESCALATE, actor="sre-1")
        blob = json.dumps(rec.escalation_path)
        self.assertNotIn("AKID", blob)
        self.assertNotIn("secret", blob.lower())


class ReopenDwellRegressionTests(unittest.TestCase):
    def test_no_negative_dwell_or_mttr_after_reopen(self) -> None:
        # 回放完整链到 resolved，再 reopen；replay 会用 reopen 覆盖 detected_at，
        # 旧状态时间戳晚于新 detected_at → dwell/MTTR 不得为负。
        log = [
            {"event": "correlate", "at": "2026-01-01T00:05:00+00:00"},
            {"event": "diagnose", "at": "2026-01-01T00:10:00+00:00"},
            {"event": "mitigate", "at": "2026-01-01T00:20:00+00:00"},
            {"event": "verify", "at": "2026-01-01T00:25:00+00:00"},
            {"event": "resolve", "at": "2026-01-01T00:35:00+00:00"},
            {"event": "reopen", "at": "2026-01-01T01:00:00+00:00"},
        ]
        rec = replay(log)
        self.assertEqual(rec.state, IncidentState.DETECTED)
        stats = dwell_stats(rec)
        for k, v in stats.items():
            self.assertGreaterEqual(v, 0.0, f"{k} must not be negative, got {v}")
        self.assertGreaterEqual(stats["mttr_min"], 0.0)

    def test_replay_missing_event_raises_value_error(self) -> None:
        log = [{"at": "2026-01-01T00:05:00+00:00"}]  # 缺 'event' 键
        with self.assertRaises(ValueError):
            replay(log)


if __name__ == "__main__":
    unittest.main()
