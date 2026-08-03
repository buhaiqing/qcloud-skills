# Output Schema Index (TE-4)

Central JSON path registry for all AIOps bundles. Full examples live in linked references — do not duplicate schemas here.

## Bundle Router

| Output type | When | Persist path | Canonical schema |
|-------------|------|--------------|-------------------|
| **Event Bundle** | TKE alarm storm / aggregation | — (inline) | [`alarm-handling.md`](alarm-handling.md) §5 |
| **RCA Bundle** | Multi-source / product / network RCA | — (inline) | [`multi-source-rca.md`](multi-source-rca.md) §4 |
| **Cruise Bundle** | Active inspection run | `./audit-results/cruise-*.json` | [`cruise-report-format.md`](cruise-report-format.md) |
| **Anomaly Bundle** | Baseline-only scan | `./audit-results/anomaly-bundle-*.json` | [`anomaly-detection.md`](anomaly-detection.md) |
| **GCL trace ref** | Post-GCL diagnosis embed | `./audit-results/gcl-trace-*.json` | [`SKILL.md`](../SKILL.md) Quality Gate §Phase 3 |
| **Incident KB record** | Post-incident feedback | `./audit-results/incident-kb-*.json` | [`incident-knowledge.md`](incident-knowledge.md) §3 |

## Shared Sub-Objects (→ §Shared Sub-Objects below)

| Path | Bundles | Reference |
|------|---------|-----------|
| `data_quality.*` | Event, RCA, Anomaly, Cross-Skill | §Shared Sub-Objects |
| `recommendations[].action` + `delegate_to` | Event, RCA, Cross-Skill | §Shared Sub-Objects |
| `incident_timeline_ref` | RCA, Anomaly | §Shared Sub-Objects |

## Top-Level JSON Paths (TE-4 consolidated)

### Event Bundle

| Path | Type | Required |
|------|------|----------|
| `bundle_id` | string | yes |
| `cluster_id` | string | yes |
| `incident_class` | string | yes |
| `severity` | P0–P3 | yes |
| `confidence` | HIGH/MEDIUM/LOW | yes |
| `root_alarm` | object | yes |
| `correlated_alarms[]` | array | yes |
| `recommendations[]` + `delegate_to` | array + string | yes |
| `data_quality.*` | object | yes |
| `incident_timeline_ref` | string | no |

### RCA Bundle

| Path | Type | Required |
|------|------|----------|
| `rca_id` | string | yes |
| `diagnosis_window` | string | yes |
| `trigger_signals[]` | array | yes |
| `top_cause.hypothesis_id` | string | yes |
| `top_cause.confidence` | HIGH/MEDIUM/LOW | yes |
| `top_cause.score` | number | yes |
| `hypotheses[]` | array | yes |
| `evidence_by_layer.*` | object per layer | yes |
| `topology_links[]` | array | when cross-layer |
| `time_alignment.overall_window` | string | yes |
| `verification_steps[]` | array | yes |
| `change_timeline[]` | array | when Rule F |
| `likely_change_trigger` | object | optional |
| `anomaly_findings[]` | array | when baseline run |
| `product_rca` / `network_rca` | object | when Rules H–P / G |
| `impact` / `similar_incidents[]` | object/array | when Workflow 10 |
| `cross_skill_ref` | object | when orchestrated |
| `recommendations[]` + `delegate_to` | array + string | yes |
| `data_quality.*` | object | yes |
| `incident_timeline_ref` | string | when incident-timeline ran |

### Anomaly Bundle

| Path | Type | Required |
|------|------|----------|
| `anomaly_bundle_id` | string | yes |
| `resource_type` / `resource_id` | string | yes |
| `detection_mode` | baseline_primary\|static_only | yes |
| `findings[]` | array | yes |
| `summary.highest_severity` | string | yes |
| `data_quality.baseline_coverage` | object | yes |
| `data_quality.*` | object | yes |
| `incident_timeline_ref` | string | no |

### Cross-Skill Bundle

| Path | Type | Required |
|------|------|----------|
| `orchestration_id` | string | yes |
| `mode` | F1\|F2\|P1\|A1\|A2 | yes |
| `participating_skills[]` | array | yes |
| `joint_hypothesis.confidence` | string | yes |
| `artifacts.rca_id` | string | when RCA ran |
| `recommendations[]` + `delegate_to` | array + string | yes |
| `data_quality.*` | object | yes |

## Shared Sub-Objects

### `data_quality.*` (all bundles)

| Path | Type | Note |
|------|------|------|
| `data_quality.status` | `complete\|partial\|stale` | — |
| `data_quality.degraded` | bool | — |
| `data_quality.missing_sources` | array | list unavailable sources |
| `data_quality.baseline_coverage` | object | Anomaly Bundle only |

See [`rubric.md`](rubric.md) Rule 4 (Data Recency).

### `recommendations[]` (Event / RCA / Cross-Skill bundles)

```json
"recommendations": [
  {
    "action": "RECOMMENDATION (not execution): Adjust memory limits to 2x current usage",
    "delegate_to": "qcloud-tke-ops",
    "priority": "P1"
  }
]
```

Must prefix `action` with `RECOMMENDATION (not execution)`. `delegate_to` must name a product skill.

### `incident_timeline_ref` (RCA / Anomaly bundles)

Reference to [`incident-timeline.md`](incident-timeline.md) §5 output. Use when `change_timeline[]` or `anomaly_findings[]` present.

## FinOps Thresholds

See [`capacity-forecast.md`](capacity-forecast.md) §Default FinOps Thresholds. Do not duplicate inline.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-13 | Initial TE-4 central path index |
| 1.2.0 | 2026-06-13 | Rules O/P SCF/CDN product_rca layers |
| 1.3.0 | 2026-08-03 | Consolidated bundle tables — shared fields now reference §Shared Sub-Objects (TE-4/TE-6); MTTR fields moved to [`mttr-tracking.md`](mttr-tracking.md) |
