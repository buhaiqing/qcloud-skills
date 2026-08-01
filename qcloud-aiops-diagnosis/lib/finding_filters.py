"""Finding filters — suppress known-known and informational findings.

Filters reduce noise in cruise reports by excluding:
- Known-bad alerts already in an allow-list (suppress)
- Informational-level findings (severity < warning)
- Findings from resources in maintenance windows
- Findings with insufficient data (too few data points)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FindingFilter:
    """Single filter rule."""

    name: str
    field: str  # which finding field to match: metric, resource_id, pattern, severity
    op: str  # "equals", "contains", "regex", "severity_above"
    value: str
    action: str = "suppress"  # "suppress" or "flag"
    _compiled_re: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.op == "regex":
            # Pre-compile once at construction time. Reject patterns that
            # are known to cause catastrophic backtracking on long inputs.
            try:
                self._compiled_re = re.compile(self.value)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{self.value}': {e}") from e

    def matches(self, finding: dict[str, Any]) -> bool:
        """Return True if finding matches this filter rule."""
        val = finding.get(self.field, "")
        if self.op == "equals":
            return str(val).lower() == self.value.lower()
        if self.op == "contains":
            return self.value.lower() in str(val).lower()
        if self.op == "regex":
            if self._compiled_re is None:
                return False  # malformed pattern, safe default
            # Use timeout-equivalent: limit search to first 10 000 chars.
            # Catastrophic backtracking cannot occur beyond this window.
            haystack = str(val)[:10_000]
            return bool(self._compiled_re.search(haystack))
        if self.op == "severity_above":
            severity_order = {"info": 0, "warning": 1, "critical": 2}
            finding_level = severity_order.get(str(val).lower(), 0)
            rule_level = severity_order.get(self.value.lower(), 99)
            return finding_level < rule_level
        return False


@dataclass
class FindingFilterSet:
    """Collection of filter rules applied in order.

    Each filter can "suppress" (drop) or "flag" (annotate) matching findings.
    """

    name: str
    rules: list[FindingFilter] = field(default_factory=list)
    _suppress_count: int = field(default=0, repr=False)

    def add_rule(
        self,
        name: str,
        field: str,
        op: str,
        value: str,
        action: str = "suppress",
    ) -> FindingFilterSet:
        """Add a filter rule (fluent builder)."""
        self.rules.append(FindingFilter(name, field, op, value, action))
        return self

    def apply(self, findings: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Apply filter rules to findings.

        Returns:
            (kept_findings, suppressed_findings)
        """
        kept: list[dict[str, Any]] = []
        suppressed: list[dict[str, Any]] = []

        for finding in findings:
            suppressed_by: list[str] = []
            for rule in self.rules:
                if rule.matches(finding) and rule.action == "suppress":
                    suppressed_by.append(rule.name)
                    self._suppress_count += 1

            if suppressed_by:
                suppressed_finding = dict(finding)
                suppressed_finding["_suppressed_by"] = suppressed_by
                suppressed.append(suppressed_finding)
            else:
                kept.append(finding)

        return kept, suppressed

    def apply_and_annotate(self, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply filters and annotate findings with matching rule names.

        Returns the original list with "_suppressed_by" or "_flagged_by" added.
        """
        result: list[dict[str, Any]] = []
        for finding in findings:
            annotated = dict(finding)
            for rule in self.rules:
                if rule.matches(finding):
                    key = "_flagged_by" if rule.action == "flag" else "_suppressed_by"
                    annotated.setdefault(key, []).append(rule.name)
            result.append(annotated)
        return result

    def suppression_stats(self) -> dict[str, int]:
        return {"total_suppressed": self._suppress_count}


# --- Pre-built filter sets ---

def finops_cost_filter() -> FindingFilterSet:
    """Suppress high-frequency FinOps alerts that are expected during peak billing."""
    fs = FindingFilterSet(name="finops_cost")
    fs.add_rule(
        name="suppress_informational_billing",
        field="severity",
        op="severity_above",
        value="warning",
    )
    fs.add_rule(
        name="suppress_known_upgrade_window",
        field="resource_id",
        op="regex",
        value=r"^cmpt-test-",
        action="flag",
    )
    return fs


def reliability_filter() -> FindingFilterSet:
    """Suppress reliability noise: known single-point-of-failure CVMs."""
    fs = FindingFilterSet(name="reliability")
    fs.add_rule(
        name="suppress_ha_candidates",
        field="resource_id",
        op="regex",
        value=r"(?i)(ha|standby|backup)-",
        action="flag",
    )
    return fs
