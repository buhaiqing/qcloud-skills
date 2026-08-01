"""Finding fingerprint — stable hash signature for deduplication.

A fingerprint is a deterministic, sortable string derived from:
- metric name
- resource identifier
- anomaly direction (upper/lower)
- time window bucket

Two findings with identical fingerprints are considered the same root cause
and de-duplicated in cruise-diff reports.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


@dataclass
class FindingFingerprint:
    """Immutable fingerprint of a diagnostic finding.

    Fields:
        metric: Short metric key, e.g. "cpu_util".
        resource_id: Cloud resource identifier, e.g. "ins-123456".
        direction: "upper" or "lower".
        window_minutes: Duration bucket (e.g. 60).
        agg_fn: Aggregation used ("avg", "max", "p99"...).
    """

    metric: str
    resource_id: str
    direction: str
    window_minutes: int = 60
    agg_fn: str = "avg"

    def __post_init__(self) -> None:
        self.direction = self.direction.lower()
        if self.direction not in ("upper", "lower"):
            raise ValueError(f"direction must be 'upper' or 'lower', got {self.direction}")

    @property
    def key(self) -> str:
        """Stable, sortable primary key for grouping/deduplication.

        Format: metric|resource_id|direction|window|agg
        """
        return f"{self.metric}|{self.resource_id}|{self.direction}|{self.window_minutes}|{self.agg_fn}"

    @property
    def hash(self) -> str:
        """Short hex digest for compact representation."""
        return hashlib.sha1(self.key.encode()).hexdigest()[:12]

    def matches(self, other: FindingFingerprint) -> bool:
        """Return True if two fingerprints refer to the same finding."""
        return self.key == other.key

    def to_dict(self) -> dict[str, str | int]:
        return {
            "metric": self.metric,
            "resource_id": self.resource_id,
            "direction": self.direction,
            "window_minutes": self.window_minutes,
            "agg_fn": self.agg_fn,
            "key": self.key,
            "hash": self.hash,
        }


@dataclass
class FingerprintRegistry:
    """Deduplication registry for a cruise run.

    Maintains a map of fingerprint → {finding_summary, count, first_seen_ts}.
    """

    fingerprints: dict[str, dict[str, object]] = field(default_factory=dict)

    def register(self, fp: FindingFingerprint, summary: str, severity: str = "warning") -> bool:
        """Register a finding fingerprint.

        Returns:
            True if this is a NEW fingerprint (first time seen).
            False if it was already registered (duplicate).
        """
        if fp.key in self.fingerprints:
            self.fingerprints[fp.key]["count"] += 1
            return False

        self.fingerprints[fp.key] = {
            "fp": fp,
            "summary": summary,
            "severity": severity,
            "count": 1,
        }
        return True

    def merge(self, other: FingerprintRegistry) -> FingerprintRegistry:
        """Merge another registry into this one (for multi-cruise aggregation)."""
        for key, entry in other.fingerprints.items():
            if key in self.fingerprints:
                self.fingerprints[key]["count"] += entry["count"]
            else:
                self.fingerprints[key] = entry
        return self

    def to_dict(self) -> dict[str, dict[str, object]]:
        return self.fingerprints

    def summary(self) -> dict[str, int]:
        """Return deduplication statistics."""
        return {
            "total_findings": sum(e["count"] for e in self.fingerprints.values()),
            "unique_findings": len(self.fingerprints),
        }

    def export_json(self) -> str:
        """Export full registry as JSON string."""
        data = {
            key: {
                "fp": entry["fp"].to_dict(),
                "summary": entry["summary"],
                "severity": entry["severity"],
                "count": entry["count"],
            }
            for key, entry in self.fingerprints.items()
        }
        return json.dumps(data, indent=2, ensure_ascii=False)
