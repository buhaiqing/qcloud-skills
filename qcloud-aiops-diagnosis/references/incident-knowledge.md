# Incident Knowledge Base — Impact, Similar Cases, Feedback Loop

> **Read-only learning layer.** Persists incident fingerprints to `./audit-results/`, matches historical cases, and estimates business impact from cloud evidence. Does not auto-execute fixes; `similar_incidents` are **advisory references** only.

## 1. Impact Assessment Model

Populate `impact` on Event Bundle and RCA Bundle after evidence collection, before final recommendations.

```json
{
  "severity": "P0|P1|P2|P3",
  "business_criticality": "P0|P1|P2|P3|unknown",
  "affected_scope": {
    "cluster_id": "cls-xxx",
    "namespaces": ["prod"],
    "workloads": ["api-deploy"],
    "load_balancer_ids": ["lb-xxx"]
  },
  "affected_resources": {
    "nodes": 1,
    "pods": 4,
    "clb_backends_unhealthy": 2,
    "clb_backends_total": 6
  },
  "estimated_traffic_pct": 33,
  "alarm_summary": {
    "p0_count": 1,
    "p1_count": 3,
    "suppressed_symptom_count": 5
  },
  "slo": {
    "configured": false,
    "latency_slo_violated": null,
    "error_budget_burn": null,
    "notes": "Supply {{user.slo_name}} or Monitor policy linkage for SLO fields"
  },
  "confidence": "HIGH|MEDIUM|LOW",
  "data_gaps": []
}
```

### Impact collection (read-only)

| Signal | Source | Field |
|---|---|---|
| Unhealthy CLB backends | `tccli clb DescribeTargetHealth` | `affected_resources.clb_backends_unhealthy` / `clb_backends_total` |
| Backend count & weight | `tccli clb DescribeTargets` | `estimated_traffic_pct` (unhealthy_weight / total_weight × 100, best effort) |
| Pod/workload scope | Event Bundle `correlated_alarms`, alarm labels | `affected_scope.workloads` |
| Node scope | TKE `DescribeClusterInstances` + alarms | `affected_resources.nodes` |
| Alarm severity mix | Event Bundle / `DescribeAlarmHistories` | `alarm_summary.p0_count`, `p1_count` |
| Business tag | `{{user.business_criticality}}` | `business_criticality` |
| SLO | `{{user.slo_name}}` + Monitor policy read (optional) | `slo.*` |

### Impact severity rules

| `impact.severity` | Criteria (first match) |
|---|---|
| **P0** | `p0_count` ≥ 1 OR `clb_backends_unhealthy/clb_backends_total` ≥ 0.5 OR `business_criticality=P0` |
| **P1** | `p1_count` ≥ 2 OR unhealthy ratio 0.2–0.5 OR multiple workloads affected |
| **P2** | Single workload / single node; partial degradation |
| **P3** | Informational; no user-facing symptom confirmed |

Set `confidence=LOW` when CLB/TKE inventory skipped; list gaps in `data_gaps`.

### Recommendation ordering

Sort `recommendations[]` by **impact severity first**, then existing technical priority (P0 root fix before P1 verification).

## 2. Incident KB Record

Written after Event Bundle / RCA Bundle / Timeline assembly completes.

```json
{
  "kb_id": "ikb-20260609-001",
  "recorded_at": "2026-06-09T10:30:00+08:00",
  "region": "ap-guangzhou",
  "fingerprint": {
    "trigger_signals": ["NodeNotReady", "CLB_5xx", "CrashLoopBackOff"],
    "incident_class": "Node Pressure",
    "hypothesis_id": "H1",
    "root_entity_type": "cvm_instance",
    "rule_ids": ["D", "A"]
  },
  "refs": {
    "rca_id": "rca-20260609-001",
    "bundle_id": "tke-evt-20260609-001",
    "timeline_id": "tl-20260609-001"
  },
  "summary": {
    "narrative": "CVM disk pressure → NodeNotReady → CLB 5xx",
    "top_cause_description": "CVM disk pressure",
    "confidence": "HIGH"
  },
  "impact_snapshot": {
    "severity": "P1",
    "estimated_traffic_pct": 33
  },
  "resolution": {
    "recommended_actions": ["drain node", "expand disk"],
    "delegate_skills": ["qcloud-cvm-ops", "qcloud-tke-ops"],
    "verified_root_cause": null,
    "was_accurate": null,
    "resolved_at": null,
    "notes": null
  }
}
```

**Persist path:** `./audit-results/incident-kb-YYYYMMDD-HHMMSS.json`

**Index (optional):** append entry to `./audit-results/incident-kb-index.json` — array of `{kb_id, fingerprint, recorded_at, path}` for faster matching without scanning all files.

## 3. Similar Case Matching

Run **before** finalizing RCA/Event Bundle when `incident_knowledge.similar_case_lookup=true` (default).

### Pipeline

```
Build current fingerprint from trigger_signals + top_cause + incident_class
  → Load candidates from incident-kb-index.json OR glob incident-kb-*.json
  → Score each candidate (§3.1)
  → Return top N (default 3) as similar_incidents[]
  → If best match ≥ threshold and verified resolution exists, add advisory note to recommendations
```

### Scoring (0–100)

| Factor | Max pts | Formula |
|---|---|---|
| Signal overlap | 40 | Jaccard(`trigger_signals`) × 40 |
| Same incident_class | 20 | +20 if equal |
| Same hypothesis_id / rule | 20 | +20 if `hypothesis_id` or primary `rule_ids` overlap |
| Same root_entity_type | 10 | +10 if equal |
| Verified past resolution | 10 | +10 if `was_accurate=true` |

| Match tier | Score | Label |
|---|---|---|
| Strong | ≥ 70 | `similarity=HIGH` |
| Moderate | 40–69 | `similarity=MEDIUM` |
| Weak | < 40 | Omit from `similar_incidents` |

**Cold start:** No KB files → `similar_incidents=[]`, `data_quality.warnings=["incident_kb_empty"]`; still write new KB record.

### similar_incidents output shape

```json
"similar_incidents": [
  {
    "kb_id": "ikb-20260601-003",
    "similarity_score": 78,
    "similarity": "HIGH",
    "recorded_at": "2026-06-01T14:20:00+08:00",
    "narrative": "CVM disk full → NodeNotReady → CLB 5xx (same pattern)",
    "historical_top_cause": "CVM disk pressure",
    "historical_resolution": {
      "was_accurate": true,
      "verified_root_cause": "DiskUsage 98%, log partition unrotated",
      "actions_taken": "RECOMMENDATION (not execution): expand disk via qcloud-cvm-ops",
      "notes": "Resolved in 25m"
    },
    "advisory": "REFERENCE ONLY — past incident ikb-20260601-003 resolved via disk expansion; verify current disk metrics before acting"
  }
]
```

> Never auto-execute historical actions. Prefix advisory with `REFERENCE ONLY`.

## 4. Feedback Loop

### On diagnosis complete (automatic)

1. Write `incident-kb-*.json` from bundle summary.
2. Set `feedback_loop.kb_id` on RCA/Event Bundle.
3. Set `feedback_loop.status=pending_review`.

### On user post-incident input (manual)

When user confirms outcome (`{{user.feedback_was_accurate}}`, `{{user.feedback_actual_root_cause}}`):

1. Update matching KB record `resolution.was_accurate`, `verified_root_cause`, `notes`, `resolved_at`.
2. Update RCA Bundle `feedback_loop` fields.
3. Re-append index entry or patch index record so future similarity scoring gets +10 verified bonus.

```json
"feedback_loop": {
  "kb_id": "ikb-20260609-001",
  "status": "pending_review|confirmed|corrected",
  "was_accurate": true,
  "actual_root_cause": "DiskUsage 97% — log rotation missing",
  "notes": "Diagnosis matched; added logrotate",
  "submitted_at": "2026-06-09T12:00:00+08:00"
}
```

| status | Meaning |
|---|---|
| `pending_review` | KB written; no user feedback yet |
| `confirmed` | User confirmed `was_accurate=true` |
| `corrected` | User provided different `actual_root_cause` |

## 5. Bundle Integration

| Bundle | New fields |
|---|---|
| RCA Bundle | `impact`, `similar_incidents[]`, expanded `feedback_loop` |
| Event Bundle | `impact`, `similar_incidents[]` (optional), `feedback_loop.kb_id` |
| Incident Timeline | `impact_snapshot` optional embed |

### RCA Bundle excerpt

```json
"impact": { "...": "§1" },
"similar_incidents": [],
"feedback_loop": {
  "kb_id": "ikb-20260609-001",
  "status": "pending_review",
  "was_accurate": null,
  "actual_root_cause": null,
  "notes": null
}
```

## 6. Privacy & retention

- Do not store credentials, secret values, or full CLS log bodies in KB records.
- Truncate narratives to ≤ 500 chars; mask instance IDs in shared exports if `{{user.mask_resource_ids}}=true`.
- Retention: prune KB files older than `incident_knowledge.retention_days` (default 90) only when user requests cleanup — this skill does not auto-delete.

## 7. Cross-Skill KB Notes

When orchestration mode F1/F2/P1 runs, include in KB `fingerprint.rule_ids`: add `XSKILL` and `mode` (`F1`/`F2`/etc.) for similar-case matching across FinOps+inspection incidents. Link `refs.orchestration_id` from Cross-Skill Bundle when present.

## 8. Changelog

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-06-09 | Impact model, KB record, similar case scoring, feedback loop, bundle integration |
| 1.1.0 | 2026-06-09 | Cross-skill orchestration KB fingerprint (`XSKILL`, mode) |
