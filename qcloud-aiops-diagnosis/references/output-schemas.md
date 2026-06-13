# Output Schema Index (TE-4)

Central JSON path registry for all AIOps bundles. Full examples live in linked references — do not duplicate schemas here.

## Bundle Router

| Output type | When | Persist path | Canonical schema |
|-------------|------|--------------|-------------------|
| **Event Bundle** | TKE alarm storm / aggregation | — (inline) | [`alarm-handling.md`](alarm-handling.md) §5 |
| **RCA Bundle** | Multi-source / product / network RCA | — (inline) | [`multi-source-rca.md`](multi-source-rca.md) §4 |
| **Anomaly Bundle** | Baseline-only scan | `./audit-results/anomaly-bundle-*.json` | [`anomaly-detection.md`](anomaly-detection.md) §6 |
| **Incident Timeline** | Post RCA/Event assembly | `./audit-results/incident-timeline-*.json` | [`incident-timeline.md`](incident-timeline.md) §3 |
| **Cross-Skill Bundle** | F1/F2/P1/A1/A2 orchestration | `./audit-results/cross-skill-bundle-*.json` | [`cross-skill-orchestration.md`](cross-skill-orchestration.md) §5 |
| **GCL trace ref** | Post-GCL diagnosis embed | `./audit-results/gcl-trace-*.json` | [`SKILL.md`](../SKILL.md) Quality Gate §Phase 3 |
| **Incident KB record** | Post-incident feedback | `./audit-results/incident-kb-*.json` | [`incident-knowledge.md`](incident-knowledge.md) §3 |

## Top-Level JSON Paths

### Event Bundle

| Path | Type | Required |
|------|------|----------|
| `bundle_id` | string | yes |
| `cluster_id` | string | yes |
| `incident_class` | string | yes |
| `severity` | P0–P3 | yes |
| `confidence` | HIGH/MEDIUM/LOW | yes |
| `data_quality.status` | complete\|partial\|stale | yes |
| `data_quality.degraded` | bool | yes |
| `data_quality.missing_sources` | array | yes |
| `root_alarm` | object | yes |
| `correlated_alarms[]` | array | yes |
| `recommendations[].delegate_to` | string | yes |

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

### Anomaly Bundle

| Path | Type | Required |
|------|------|----------|
| `anomaly_bundle_id` | string | yes |
| `resource_type` / `resource_id` | string | yes |
| `detection_mode` | baseline_primary\|static_only | yes |
| `findings[]` | array | yes |
| `summary.highest_severity` | string | yes |
| `data_quality.baseline_coverage` | object | yes |

### Cross-Skill Bundle

| Path | Type | Required |
|------|------|----------|
| `orchestration_id` | string | yes |
| `mode` | F1\|F2\|P1\|A1\|A2 | yes |
| `participating_skills[]` | array | yes |
| `joint_hypothesis.confidence` | string | yes |
| `artifacts.rca_id` | string | when RCA ran |
| `prevention_items[]` | array | Mode A1 |
| `finops_advisory` | object | Mode A2 |

## Shared Sub-Objects

| Path | Used by | Reference |
|------|---------|-----------|
| `data_quality.*` | All bundles | [`rubric.md`](rubric.md) Rule 4 |
| `recommendations[].action` | All bundles | Must prefix `RECOMMENDATION (not execution)` |
| `incident_timeline_ref` | RCA, Event, Anomaly | [`incident-timeline.md`](incident-timeline.md) §5 |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-13 | Initial TE-4 central path index for 6 bundle types |
| 1.2.0 | 2026-06-13 | Rules O/P SCF/CDN product_rca layers |
