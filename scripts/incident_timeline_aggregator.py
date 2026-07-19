#!/usr/bin/env python3
"""incident_timeline_aggregator.py — Build unified incident timeline from diagnostic bundles.

Reads RCA Bundle and Event Bundle JSON files from audit-results/ and assembles
a time-ordered incident timeline with cross-product topology linking.

Pipeline (per incident-timeline.md §2):
  Collect bundle inputs (Event/RCA Bundles)
    → Normalize each item into Timeline Event
    → Sort by timestamp ascending
    → Assign roles (trigger / root_candidate / symptom / change / etc.)
    → Attach cross-links (topology_links)
    → Output unified Incident Timeline JSON

Usage:
  python3 scripts/incident_timeline_aggregator.py aggregate --pattern "audit-results/rca-*.json"
  python3 scripts/incident_timeline_aggregator.py aggregate --pattern "audit-results/*evt*.json"
  python3 scripts/incident_timeline_aggregator.py self-verify
"""

from __future__ import annotations

import argparse
import re
import glob
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "audit-results"

# ---------------------------------------------------------------------------
# Role constants (incident-timeline.md §3)
# ---------------------------------------------------------------------------

ROLE_CHANGE        = "change"
ROLE_TRIGGER       = "trigger"
ROLE_ROOT_CAND     = "root_candidate"
ROLE_SYMPTOM       = "symptom"
ROLE_CORRELATED    = "correlated"
ROLE_METRIC_SPIKE  = "metric_spike"
ROLE_METRIC_ANOMALY = "metric_anomaly"
ROLE_LOG_PATTERN  = "log_pattern"

# ---------------------------------------------------------------------------
# Field normalizers
# ---------------------------------------------------------------------------

def _norm_ts(value: Any) -> str:
    """Return ISO8601 string, or empty string on failure."""
    if not value:
        return ""
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return str(value)
    s = str(value).strip()
    if not s:
        return ""
    # Already ISO?
    if "T" in s or "Z" in s or "+" in s:
        return s[:19] + "Z" if "Z" not in s and "+" not in s else s[:26]
    return s


def _norm_str(value: Any) -> str:
    if not value:
        return ""
    s = str(value).strip()
    return s[:200]  # guard against huge strings


def _extract_str(data: Any, *keys, default="") -> str:
    for k in keys:
        if isinstance(data, dict):
            data = data.get(k, default)
        else:
            return default
    return _norm_str(data) if data else default


# ---------------------------------------------------------------------------
# Bundle loading
# ---------------------------------------------------------------------------

def load_bundles(pattern: str) -> list[dict[str, Any]]:
    """Load all JSON files matching glob pattern."""
    files = sorted(glob.glob(pattern))
    bundles = []
    for fp in files:
        try:
            data = json.loads(Path(fp).read_text(encoding="utf-8"))
            bundles.append(data)
        except Exception as e:
            print(f"WARNING: skipped {fp}: {e}", file=sys.stderr)
    return bundles


def _load_audit_bundles(prefix: str = "rca") -> list[dict[str, Any]]:
    """Load bundles from audit-results matching prefix."""
    pattern = str(AUDIT_DIR / f"{prefix}-*.json")
    return load_bundles(pattern)


# ---------------------------------------------------------------------------
# Event extraction
# ---------------------------------------------------------------------------

def _extract_events_from_rca(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract timeline events from an RCA Bundle JSON."""
    events = []
    bundle_id = _extract_str(bundle, "rca_id", "bundle_id", "timeline_id", default="unknown")
    ts_base = _norm_ts(bundle.get("timestamp", ""))

    # Change timeline events
    for idx, change in enumerate(bundle.get("change_timeline", [])):
        events.append({
            "seq": None,
            "timestamp": _norm_ts(change.get("timestamp", ts_base)),
            "role": ROLE_CHANGE,
            "source": _extract_str(change, "source", default="cloudaudit"),
            "summary": _norm_str(change.get("change_action", change.get("summary", ""))),
            "entity_type": _extract_str(change, "entity_type", default="change"),
            "entity_id": _extract_str(change, "entity_id", default=""),
            "severity": _extract_str(change, "severity", default="INFO"),
            "confidence": "HIGH",
            "ref_ids": {"change_id": change.get("change_id", f"{bundle_id}-change-{idx}")},
            "linkage": _extract_str(change, "details", "linkage", "cluster_id", default=""),
            "_bundle": bundle_id,
        })

    # Top cause event
    top_cause = bundle.get("top_cause", {})
    if top_cause:
        events.append({
            "seq": None,
            "timestamp": ts_base,
            "role": ROLE_ROOT_CAND,
            "source": "aiops-diagnosis",
            "summary": _norm_str(top_cause.get("description", top_cause.get("category", ""))),
            "entity_type": _extract_str(top_cause, "entity_type", default="unknown"),
            "entity_id": _extract_str(top_cause, "entity_id", default=""),
            "severity": _extract_str(top_cause, "severity", default="P1"),
            "confidence": _extract_str(bundle.get("top_cause", {}), "confidence", default="MEDIUM"),
            "ref_ids": {"hypothesis_id": bundle.get("top_cause", {}).get("hypothesis_id", "")},
            "linkage": {},
            "_bundle": bundle_id,
        })

    # Alarm events
    for alarm in bundle.get("correlated_alarms", bundle.get("alarms", [])):
        alarm_ts = _norm_ts(alarm.get("alarm_time", alarm.get("trigger_time", ts_base)))
        suppressed = alarm.get("suppressed", False)
        events.append({
            "seq": None,
            "timestamp": alarm_ts,
            "role": ROLE_SYMPTOM if suppressed else ROLE_TRIGGER,
            "source": "monitor",
            "summary": _norm_str(alarm.get("alarm_name", alarm.get("message", ""))),
            "entity_type": _extract_str(alarm, "entity_type", "resource_type", default="alarm"),
            "entity_id": _extract_str(alarm, "alarm_id", "entity_id", default=""),
            "severity": _extract_str(alarm, "severity", default="P2"),
            "confidence": "HIGH",
            "ref_ids": {"alarm_id": alarm.get("alarm_id", "")},
            "linkage": {
                "cluster_id": _extract_str(alarm, "cluster_id", default=""),
                "namespace": _extract_str(alarm, "namespace", default=""),
            },
            "_bundle": bundle_id,
        })

    # Anomaly findings → metric_anomaly role
    for finding in bundle.get("anomaly_findings", []):
        if isinstance(finding, dict):
            score = finding.get("anomaly_score", 0)
            role = ROLE_METRIC_ANOMALY if score >= 30 else ROLE_METRIC_SPIKE
            events.append({
                "seq": None,
                "timestamp": ts_base,
                "role": role,
                "source": "monitor",
                "summary": f"{_extract_str(finding, 'metric', 'metric_name')} anomaly score={score}",
                "entity_type": _extract_str(finding, "entity_type", default="metric"),
                "entity_id": _extract_str(finding, "entity_id", default=""),
                "severity": "P2" if score < 60 else "P1",
                "confidence": "MEDIUM",
                "ref_ids": {},
                "linkage": {},
                "_bundle": bundle_id,
            })

    return events


def _extract_events_from_evt(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract timeline events from an Event Bundle JSON."""
    events = []
    bundle_id = _extract_str(bundle, "event_bundle_id", "bundle_id", default="unknown")
    ts_base = _norm_ts(bundle.get("timestamp", ""))

    # Root alarm
    root = bundle.get("root_alarm", {})
    if root:
        events.append({
            "seq": None,
            "timestamp": _norm_ts(root.get("alarm_time", ts_base)),
            "role": ROLE_TRIGGER,
            "source": "monitor",
            "summary": _norm_str(root.get("alarm_name", root.get("message", ""))),
            "entity_type": _extract_str(root, "entity_type", default="alarm"),
            "entity_id": _extract_str(root, "alarm_id", default=""),
            "severity": _extract_str(root, "severity", default="P1"),
            "confidence": "HIGH",
            "ref_ids": {"alarm_id": root.get("alarm_id", "")},
            "linkage": {},
            "_bundle": bundle_id,
        })

    # Correlated alarms
    for alarm in bundle.get("correlated_alarms", []):
        suppressed = alarm.get("suppressed", False)
        events.append({
            "seq": None,
            "timestamp": _norm_ts(alarm.get("alarm_time", alarm.get("trigger_time", ts_base))),
            "role": ROLE_SYMPTOM if suppressed else ROLE_CORRELATED,
            "source": "monitor",
            "summary": _norm_str(alarm.get("alarm_name", alarm.get("message", ""))),
            "entity_type": _extract_str(alarm, "entity_type", default="alarm"),
            "entity_id": _extract_str(alarm, "alarm_id", default=""),
            "severity": _extract_str(alarm, "severity", default="P2"),
            "confidence": "MEDIUM",
            "ref_ids": {"alarm_id": alarm.get("alarm_id", "")},
            "linkage": {},
            "_bundle": bundle_id,
        })

    # Evidence items → metric_spike / log_pattern
    for ev in bundle.get("evidence", []):
        ev_type = _extract_str(ev, "evidence_type", "type", default="unknown")
        if ev_type in ("log", "log_pattern", "cls"):
            role = ROLE_LOG_PATTERN
        else:
            role = ROLE_METRIC_SPIKE
        events.append({
            "seq": None,
            "timestamp": _norm_ts(ev.get("timestamp", ts_base)),
            "role": role,
            "source": _extract_str(ev, "source", default="cls"),
            "summary": _norm_str(ev.get("pattern", ev.get("summary", ""))),
            "entity_type": _extract_str(ev, "entity_type", default=ev_type),
            "entity_id": _extract_str(ev, "entity_id", default=""),
            "severity": "P2",
            "confidence": "MEDIUM",
            "ref_ids": {},
            "linkage": {},
            "_bundle": bundle_id,
        })

    return events


def extract_events(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract and normalize events from heterogeneous bundle list."""
    events = []
    for bundle in bundles:
        btype = _extract_str(bundle, "bundle_type", "type", default="").lower()
        if "rca" in btype or "rca_id" in bundle or "top_cause" in bundle:
            events.extend(_extract_events_from_rca(bundle))
        elif "evt" in btype or "event_bundle" in btype or "event_bundle_id" in bundle:
            events.extend(_extract_events_from_evt(bundle))
        else:
            # Try both
            events.extend(_extract_events_from_rca(bundle))
            events.extend(_extract_events_from_evt(bundle))
    return events


# ---------------------------------------------------------------------------
# Topology linking
# ---------------------------------------------------------------------------

ID_PATTERNS = (
    ("instance_id", re.compile(r"ins-[a-z0-9]+", re.I)),
    ("vpc_id",      re.compile(r"vpc-[a-z0-9]+", re.I)),
    ("cluster_id",  re.compile(r"cls-[a-z0-9]+", re.I)),
    ("pod_id",       re.compile(r"pod-[a-z0-9]+", re.I)),
    ("alarm_id",     re.compile(r"alarm-[a-z0-9]+", re.I)),
    ("lb_id",        re.compile(r"lb-[a-z0-9]+", re.I)),
)


def _extract_entity_ids(text: str) -> dict[str, str]:
    """Find all entity IDs in a string."""
    found = {}
    for name, pattern in ID_PATTERNS:
        m = pattern.search(text)
        if m:
            found[name] = m.group(0)
    return found


def topology_link(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add topology linkage between events that share entity IDs."""
    # Build entity_id → event indices map
    entity_map: dict[tuple[str, str], list[int]] = {}
    for i, ev in enumerate(events):
        combined = json.dumps([ev.get("entity_id", ""), ev.get("summary", ""), ev.get("linkage", "")])
        for name, pattern in ID_PATTERNS:
            m = pattern.search(combined)
            if m:
                key = (name, m.group(0).lower())
                entity_map.setdefault(key, []).append(i)

    # Annotate events with linked events
    for key, indices in entity_map.items():
        if len(indices) < 2:
            continue
        for i in indices:
            others = [events[j]["entity_id"] or events[j].get("summary", "")[:30]
                  for j in indices if j != i]
            events[i].setdefault("_topology_links", []).extend(others)

    return events


# ---------------------------------------------------------------------------
# Timeline assembly
# ---------------------------------------------------------------------------

def align_timeline(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort events by timestamp ascending; assign seq numbers."""
    # Filter events with valid timestamps
    sortable = []
    for ev in events:
        ts = ev.get("timestamp", "")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            sortable.append((dt, ev))
        except Exception:
            # Try parsing as unix timestamp
            try:
                dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
                sortable.append((dt, ev))
            except Exception:
                pass

    sortable.sort(key=lambda x: x[0])
    for seq, (_, ev) in enumerate(sortable, 1):
        ev["seq"] = seq

    return [ev for _, ev in sortable]


def build_incident_timeline(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    """Main entry point: aggregate bundles → unified timeline."""
    events = extract_events(bundles)
    events = topology_link(events)
    events = align_timeline(events)

    if not events:
        return {"error": "No events with valid timestamps found", "events": []}

    # Detect likely change trigger: earliest change event that precedes symptoms
    change_events = [e for e in events if e.get("role") == ROLE_CHANGE]
    trigger_events = [e for e in events if e.get("role") == ROLE_TRIGGER]
    root_cand = next((e for e in events if e.get("role") == ROLE_ROOT_CAND), None)

    likely_change = {}
    if change_events and trigger_events:
        first_change_ts = change_events[0].get("timestamp", "")
        first_trigger_ts = trigger_events[0].get("timestamp", "")
        try:
            cdt = datetime.fromisoformat(first_change_ts.replace("Z", "+00:00"))
            tdt = datetime.fromisoformat(first_trigger_ts.replace("Z", "+00:00"))
            if cdt < tdt:
                likely_change = change_events[0]
        except Exception:
            pass

    # Build causal chain (consecutive events)
    causal_chain = []
    for i in range(len(events) - 1):
        e1, e2 = events[i], events[i + 1]
        r1, r2 = e1.get("role", ""), e2.get("role", "")
        if r1 == ROLE_CHANGE and r2 in (ROLE_TRIGGER, ROLE_SYMPTOM):
            rel = "change→symptom" if r2 == ROLE_SYMPTOM else "change→trigger"
        elif r1 in (ROLE_TRIGGER, ROLE_SYMPTOM) and r2 == ROLE_SYMPTOM:
            rel = "symptom→symptom"
        elif r1 == ROLE_ROOT_CAND:
            rel = "root→symptom"
        else:
            rel = "sequential"
        causal_chain.append({"from_seq": e1["seq"], "to_seq": e2["seq"], "relation": rel})

    # Diagnosis window
    all_ts = [e["timestamp"] for e in events if e.get("timestamp")]
    diag_window = {}
    if all_ts:
        diag_window = {"start": min(all_ts), "end": max(all_ts)}

    # Narrative summary
    narrative_parts = []
    if change_events:
        narrative_parts.append(f"Change {change_events[0].get('summary','')[:40]}@{change_events[0]['timestamp'][11:16]}")
    if trigger_events:
        narrative_parts.append(f"→ Alarm @{trigger_events[0]['timestamp'][11:16]}")
    if root_cand:
        narrative_parts.append(f"→ Root: {root_cand.get('summary','')[:40]}")
    narrative_summary = "; ".join(narrative_parts)[:280] if narrative_parts else "No clear causal chain"

    bundle_ids = list({e.get("_bundle", "unknown") for e in events})

    return {
        "timeline_id": f"tl-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        "incident_ref": {"bundle_ids": bundle_ids},
        "diagnosis_window": diag_window,
        "narrative_summary": narrative_summary,
        "events": events,
        "causal_chain": causal_chain,
        "top_cause_ref": {
            "description": root_cand.get("summary", "") if root_cand else "",
            "confidence": root_cand.get("confidence", "") if root_cand else "",
        } if root_cand else {},
        "likely_change_trigger": likely_change if likely_change else {},
        "data_quality": {
            "status": "complete" if len(events) >= 3 else "partial",
            "total_events": len(events),
            "missing_layers": [],
            "warnings": [],
        },
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_aggregate(args: argparse.Namespace) -> int:
    bundles = load_bundles(args.pattern)
    if not bundles:
        print(f"WARNING: No bundles matched pattern '{args.pattern}'", file=sys.stderr)
    print(f"Loaded {len(bundles)} bundle(s)", file=sys.stderr)

    timeline = build_incident_timeline(bundles)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(timeline, indent=2, ensure_ascii=False))
        print(f"Timeline written to {out_path}", file=sys.stderr)

    if args.json:
        print(json.dumps(timeline, indent=2, ensure_ascii=False))
    else:
        print(f"Timeline: {timeline.get('timeline_id', 'unknown')}")
        print(f"  Events: {len(timeline.get('events', []))}")
        print(f"  Narrative: {timeline.get('narrative_summary', '')[:120]}")
        print(f"  Window: {timeline.get('diagnosis_window', {})}")
        if timeline.get("causal_chain"):
            print(f"  Causal chain ({len(timeline['causal_chain'])} links):")
            for link in timeline["causal_chain"][:5]:
                print(f"    seq {link['from_seq']} → {link['to_seq']}: {link['relation']}")

    return 0


# ---------------------------------------------------------------------------
# Self-verification
# ---------------------------------------------------------------------------


def self_verify() -> bool:
    # Synthetic RCA bundle
    synthetic = [{
        "bundle_id": "rca-test-001",
        "timestamp": "2026-07-19T10:00:00Z",
        "change_timeline": [
            {"timestamp": "2026-07-19T10:00:00Z", "change_action": "Deploy api-deploy rev42",
             "entity_type": "deployment", "entity_id": "api-deploy"},
        ],
        "correlated_alarms": [
            {"alarm_time": "2026-07-19T10:02:00Z", "alarm_name": "Pod CrashLoop",
             "severity": "P1", "suppressed": False},
            {"alarm_time": "2026-07-19T10:03:00Z", "alarm_name": "CLB 5xx",
             "severity": "P1", "suppressed": True},
        ],
        "top_cause": {
            "description": "Post-change app regression",
            "entity_type": "deployment", "entity_id": "api-deploy",
            "severity": "P1", "confidence": "HIGH",
        },
        "anomaly_findings": [
            {"metric": "CpuUsage", "anomaly_score": 65, "entity_id": "ins-xxx"},
        ],
    }]

    events = extract_events(synthetic)
    assert len(events) == 5, f"Expected 5 events, got {len(events)}"

    # Verify role assignment
    roles = {e["role"] for e in events}
    assert ROLE_CHANGE in roles, f"Missing change role in {roles}"
    assert ROLE_TRIGGER in roles, f"Missing trigger role in {roles}"

    # Verify timeline ordering
    timeline = build_incident_timeline(synthetic)
    evs = timeline["events"]
    assert len(evs) == 5, f"Expected 5 ordered events, got {len(evs)}"
    assert evs[0]["role"] == ROLE_CHANGE, f"First event should be change, got {evs[0]['role']}"

    # Verify causal chain
    assert len(timeline["causal_chain"]) == 4

    # Verify narrative
    assert "Deploy" in timeline["narrative_summary"]

    print("  [PASS] extract_events: 5 events from synthetic RCA bundle")
    print("  [PASS] role assignment: change + trigger present")
    print("  [PASS] timeline ordering: change first")
    print("  [PASS] causal_chain: 4 links generated")
    print("  [PASS] narrative_summary: generated")
    return True


# ---------------------------------------------------------------------------
# CLI builder
# ---------------------------------------------------------------------------

def _cmd_self_verify(_):
    return 0 if self_verify() else 1
    
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    agg = sub.add_parser("aggregate", help="Aggregate bundles into unified timeline")
    agg.add_argument("--pattern", required=True, help="Glob pattern for bundle JSONs")
    agg.add_argument("--output", default=None, help="Write timeline JSON to file")
    agg.add_argument("--json", action="store_true")
    agg.set_defaults(func=cmd_aggregate)
    sv = sub.add_parser("self-verify")
    sv.set_defaults(func=_cmd_self_verify)
    return p


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())