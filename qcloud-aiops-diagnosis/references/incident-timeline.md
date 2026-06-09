# Incident Timeline — Unified Causal Narrative

> Assembles alarms, metrics, logs, topology links, and **change events** into a single time-ordered narrative. Use alongside Event Bundle and RCA Bundle; does not replace them.

## 1. Purpose

Event Bundle and RCA Bundle answer **what happened** and **likely root cause**. Incident Timeline answers **in what order** — critical for on-call handoff, postmortems, and distinguishing change-induced regression from infrastructure failure.

## 2. Assembly Pipeline

```
Collect bundle inputs (Event Bundle and/or RCA Bundle + change_timeline)
  → Normalize each item into Timeline Event (§3)
  → Sort by timestamp ascending
  → Assign role (trigger | root_candidate | symptom | correlated | change)
  → Attach cross-links (topology_links, correlation_edges)
  → Output Incident Timeline (§4)
```

Run this pipeline **after** alarm aggregation (Workflow 5) or multi-source RCA (Workflow 6). See [`diagnostic-workflows.md`](diagnostic-workflows.md#workflow-7-incident-timeline-assembly).

## 3. Timeline Event Model

```json
{
  "seq": 1,
  "timestamp": "2026-06-09T10:02:00+08:00",
  "role": "change|trigger|root_candidate|symptom|correlated|metric_spike|metric_anomaly|log_pattern",
  "source": "cloudaudit|monitor|tke|clb|cvm|cls",
  "summary": "Deployment api-deploy RollingUpdate revision 42",
  "entity_type": "deployment|pod|node|clb|cvm|alarm",
  "entity_id": "api-deploy|pod-xxx|ins-xxx",
  "severity": "P0|P1|P2|P3|INFO",
  "confidence": "HIGH|MEDIUM|LOW",
  "ref_ids": {
    "alarm_id": "alarm-001",
    "change_id": "chg-20260609-001",
    "hypothesis_id": "F1"
  },
  "linkage": {
    "cluster_id": "cls-xxx",
    "namespace": "prod",
    "workload": "api-deploy"
  }
}
```

### Role Assignment Rules

| role | When to assign |
|---|---|
| `change` | Entry from `change_timeline` ([`change-correlation.md`](change-correlation.md)) |
| `trigger` | Earliest alarm or metric spike that started the incident window |
| `root_candidate` | Entity from `top_cause` or `likely_change_trigger` |
| `symptom` | Alarms marked `suppressed=true` or downstream in correlation rules |
| `correlated` | Evidence supporting a hypothesis but not root/symptom |
| `metric_spike` | Standalone metric threshold breach in evidence |
| `metric_anomaly` | Baseline anomaly finding from [`anomaly-detection.md`](anomaly-detection.md) (`anomaly_score` ≥ 30) |
| `log_pattern` | CLS pattern match (OOM, exception spike) |

If `likely_change_trigger` is non-null and precedes symptoms, list the change event first with `role=change`, then mark the first symptom with `role=trigger`.

## 4. Incident Timeline Output Schema

```json
{
  "timeline_id": "tl-20260609-001",
  "incident_ref": {
    "bundle_id": "tke-evt-20260609-001",
    "rca_id": "rca-20260609-001"
  },
  "diagnosis_window": {
    "start": "2026-06-09T09:45:00+08:00",
    "end": "2026-06-09T10:20:00+08:00"
  },
  "narrative_summary": "Deploy api-deploy@10:02 → pod CrashLoop@10:04 → CLB 5xx@10:05; node/CVM metrics remained normal — regression likely.",
  "events": [],
  "causal_chain": [
    {"from_seq": 1, "to_seq": 2, "relation": "change→symptom"},
    {"from_seq": 2, "to_seq": 3, "relation": "symptom→symptom"}
  ],
  "top_cause_ref": {
    "hypothesis_id": "F1",
    "description": "Post-change app regression",
    "confidence": "HIGH"
  },
  "likely_change_trigger": {},
  "data_quality": {
    "status": "complete|partial",
    "missing_layers": ["cls_events"],
    "warnings": []
  }
}
```

### narrative_summary Generation

Compose one sentence from ordered events:

1. List `change` and `trigger` events with timestamps (HH:MM).
2. State `top_cause_ref.description` or highest-scoring hypothesis.
3. Note disqualifying evidence (e.g., "node metrics normal — rules out node pressure").

Keep ≤ 280 characters when possible for chat/on-call tools.

## 5. Integration with Existing Bundles

| Source field | Maps to timeline |
|---|---|
| Event Bundle `root_alarm` | `role=root_candidate` or `trigger` |
| Event Bundle `correlated_alarms[]` | `role=symptom` if `suppressed=true`, else `correlated` |
| Event Bundle `evidence[]` | `metric_spike` or `log_pattern` |
| RCA Bundle `hypotheses[]` | `ref_ids.hypothesis_id` on related events |
| RCA Bundle `change_timeline[]` | `role=change` |
| RCA Bundle `likely_change_trigger` | First `change` event + `top_cause_ref` when F1–F4 wins |

Event Bundle may include optional embedded timeline:

```json
"incident_timeline_ref": {
  "timeline_id": "tl-20260609-001",
  "narrative_summary": "...",
  "event_count": 8
}
```

Full `events[]` live in the standalone Incident Timeline object or `./audit-results/incident-timeline-YYYYMMDD-HHMMSS.json`.

## 6. Persistence

| Artifact | Path |
|---|---|
| Full timeline JSON | `./audit-results/incident-timeline-YYYYMMDD-HHMMSS.json` |
| KB seed (optional) | `./audit-results/incident-kb-YYYYMMDD-HHMMSS.json` — `trigger_signals` + `top_cause` + `narrative_summary` for future similar-case matching |

## 7. Changelog

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-06-09 | Initial release — Timeline Event model, assembly pipeline, output schema, Event/RCA Bundle integration |
| 1.1.0 | 2026-06-09 | `metric_anomaly` timeline role for baseline findings |
