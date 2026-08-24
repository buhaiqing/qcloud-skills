#!/usr/bin/env python3
"""Phase 3.4 — Immutable audit logger for autonomous decisions."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ----------------------------------------------------------------------
# Dataclasses
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class AutonomousDecision:
    """A single autonomous decision record written to the audit log."""

    decision_id: str
    timestamp: str
    autonomy_level: int
    operation: str
    resource_ids: list[str]
    risk_level: str
    action_taken: str
    rationale: str
    result: str
    revocable_until: str
    skill: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "timestamp": self.timestamp,
            "autonomy_level": self.autonomy_level,
            "operation": self.operation,
            "resource_ids": self.resource_ids,
            "risk_level": self.risk_level,
            "action_taken": self.action_taken,
            "rationale": self.rationale,
            "result": self.result,
            "revocable_until": self.revocable_until,
            "skill": self.skill,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AutonomousDecision:
        return cls(
            decision_id=d["decision_id"],
            timestamp=d["timestamp"],
            autonomy_level=d["autonomy_level"],
            operation=d["operation"],
            resource_ids=d["resource_ids"],
            risk_level=d["risk_level"],
            action_taken=d["action_taken"],
            rationale=d["rationale"],
            result=d["result"],
            revocable_until=d["revocable_until"],
            skill=d["skill"],
        )


# ----------------------------------------------------------------------
# AuditLogger
# ----------------------------------------------------------------------


class AuditLogger:
    """Append-only audit log writer for autonomous decisions.

    Log file location: ``{runtime_root}/.runtime/audit/decisions.jsonl``
    (one JSON object per line).
    """

    def __init__(self, runtime_root: Path | None = None) -> None:
        root = runtime_root or Path.cwd()
        self._log_path = root / ".runtime" / "audit" / "decisions.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_decision(self, decision: AutonomousDecision) -> None:
        """Append a decision record to the append-only JSONL log."""
        with open(self._log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(decision.to_dict(), ensure_ascii=False) + "\n")

    def generate_report(self, since: str, level: int | None = None) -> str:
        """Generate a markdown-formatted report of decisions since an ISO-8601 timestamp.

        Parameters
        ----------
        since:
            ISO 8601 timestamp (inclusive). All decisions with
            ``timestamp >= since`` are included.
        level:
            If given, only include decisions made at this autonomy level.

        Returns
        -------
        str
            Markdown-formatted report.
        """
        decisions = self._read_decisions(since, level)

        if not decisions:
            return (
                f"## Autonomous Decisions Audit Report\n\n"
                f"No autonomous decisions found since {since}.\n"
            )

        total = len(decisions)
        by_action: dict[str, list[AutonomousDecision]] = {}
        by_skill: dict[str, list[AutonomousDecision]] = {}
        by_result: dict[str, int] = {}
        revoked = 0

        for d in decisions:
            by_action.setdefault(d.action_taken, []).append(d)
            by_result[d.result] = by_result.get(d.result, 0) + 1
            if d.skill:
                by_skill.setdefault(d.skill, []).append(d)
            if d.result == "rolled_back":
                revoked += 1

        lines = [
            "## Autonomous Decisions Audit Report",
            "",
            f"**Period:** since {since}",
            f"**Total decisions:** {total}",
            f"**Revoked:** {revoked}",
            "",
        ]

        lines.append("### By Action Taken")
        for action, items in sorted(by_action.items()):
            lines.append(f"- **{action}**: {len(items)} decision(s)")
            for item in items[:3]:
                lines.append(
                    f"  - `{item.decision_id}` `{item.operation}` "
                    f"risk={item.risk_level} → {item.action_taken} ({item.result})"
                )
            if len(items) > 3:
                lines.append(f"  - ... and {len(items) - 3} more")
        lines.append("")

        lines.append("### By Result")
        for result_name, count in sorted(by_result.items()):
            lines.append(f"- {result_name}: {count}")
        lines.append("")

        if by_skill:
            lines.append("### By Skill")
            for skill, items in sorted(by_skill.items()):
                lines.append(f"- **{skill}**: {len(items)} decision(s)")
            lines.append("")

        return "\n".join(lines)

    def revoke(self, decision_id: str) -> bool:
        """Mark a decision as ``rolled_back`` if it is still within the 5-minute window.

        Returns ``True`` if the revocation succeeded; ``False`` if the decision
        was not found, already revoked, or the window has expired.
        """
        now = datetime.now(UTC)

        if not self._log_path.exists():
            return False

        decisions: list[dict[str, Any]] = []
        with open(self._log_path, encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    decisions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        updated_lines: list[str] = []
        revoked = False

        for d in decisions:
            if d["decision_id"] == decision_id:
                if d["result"] == "rolled_back":
                    return False  # already revoked
                revocable_until = datetime.fromisoformat(d["revocable_until"])
                if now <= revocable_until:
                    d["result"] = "rolled_back"
                    revoked = True
            updated_lines.append(json.dumps(d, ensure_ascii=False))

        if revoked:
            with open(self._log_path, "w", encoding="utf-8") as fh:
                fh.writelines(l + "\n" for l in updated_lines)

        return revoked

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_decisions(
        self, since: str, level: int | None = None
    ) -> list[AutonomousDecision]:
        """Read all decision records from the log, optionally filtered."""
        if not self._log_path.exists():
            return []

        since_dt = datetime.fromisoformat(since)
        decisions: list[AutonomousDecision] = []

        with open(self._log_path, encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                record_dt = datetime.fromisoformat(d["timestamp"])
                if record_dt < since_dt:
                    continue
                if level is not None and d.get("autonomy_level") != level:
                    continue
                decisions.append(AutonomousDecision.from_dict(d))

        return decisions
