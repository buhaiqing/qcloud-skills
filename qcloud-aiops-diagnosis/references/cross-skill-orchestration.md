# Cross-Skill Orchestration — FinOps · Proactive Inspection · AIOps

> **Orchestration hub for `qcloud-aiops-diagnosis`.** Defines bidirectional handoffs with `qcloud-finops-ops` and `qcloud-proactive-inspection`. This skill remains **read-only**; FinOps/inspection skills remain authoritative for billing and scheduled audits.

## 1. Orchestration Modes

| Mode | Entry skill | Flow | Output |
|---|---|---|---|
| **F1** | `qcloud-finops-ops` | FinOps anomaly (HIGH) → proactive inspection → AIOps RCA | Cross-Skill Bundle |
| **F2** | `qcloud-finops-ops` | FinOps anomaly + top product delta → AIOps joint diagnosis (skip full inspection) | Cross-Skill Bundle + RCA Bundle |
| **P1** | `qcloud-proactive-inspection` | Inspection CRITICAL finding → AIOps validate / deepen | RCA or Anomaly Bundle |
| **A1** | `qcloud-aiops-diagnosis` | Post-incident → generate proactive inspection follow-up items | `prevention_items[]` + delegate inspection |
| **A2** | `qcloud-aiops-diagnosis` | RCA capacity/saturation signal → FinOps cost advisory | `finops_advisory` block |

### Mode selection

```
IF {{user.handoff_source}} == finops AND confidence == HIGH AND auto_dispatch_inspection == true
  → F1
ELIF {{user.handoff_source}} == finops AND top_product_delta known
  → F2
ELIF {{user.handoff_source}} == proactive_inspection AND finding_severity >= CRITICAL
  → P1
ELIF incident resolved AND user wants prevention
  → A1
ELIF RCA shows sustained capacity pressure OR week-over-week metric drift
  → A2 (append to bundle; delegate finops for savings estimate)
ELSE
  → standard AIOps workflow only
```

## 2. Handoff Payloads

### 2.1 FinOps → AIOps (`finops_handoff`)

Produced by `qcloud-finops-ops` anomaly pipeline; consumed at AIOps pre-flight. Validate: `assets/finops-handoff.schema.json`.

```json
{
  "handoff_id": "finops-ho-20260609-001",
  "source_skill": "qcloud-finops-ops",
  "anomaly": {
    "month": "2026-05",
    "confidence": "HIGH|MEDIUM",
    "ii_ratio": 0.35,
    "iii_ratio": 0.92,
    "ii_violated": true,
    "iii_violated": true,
    "total_delta_cny": 12500.0
  },
  "top_products": [
    {"product": "cvm", "delta_cny": 8000, "delta_pct": 0.42, "top_resource_ids": ["ins-aaa", "ins-bbb"]},
    {"product": "cdb", "delta_cny": 3000, "delta_pct": 0.28, "top_resource_ids": ["cdb-xxx"]}
  ],
  "dispatch_inspection": true,
  "time_window": {"start": "2026-05-01", "end": "2026-05-31"},
  "owner": "finops-team"
}
```

**AIOps actions on receive:**
1. Map `top_products[].product` → `resource_type` + run Workflow 8 (baseline) on `top_resource_ids`.
2. Run product RCA (H/I/J) or TKE/CLB RCA when IDs imply infra chain.
3. Correlate bill delta timing with metric anomalies and change events (Rule F).
4. Never duplicate FinOps billing API calls unless verifying a specific resource attribution.

### 2.2 Proactive Inspection → AIOps (`inspection_handoff`)

Validate: `assets/inspection-handoff.schema.json`.

```json
{
  "handoff_id": "insp-ho-20260609-002",
  "source_skill": "qcloud-proactive-inspection",
  "inspection_id": "insp-20260609-weekly",
  "findings": [
    {
      "resource_type": "cvm",
      "resource_id": "ins-aaa",
      "severity": "CRITICAL",
      "rule": "cpu_sustained_high",
      "metric": "CpuUsage",
      "value": "96%",
      "detected_at": "2026-06-09T08:00:00+08:00"
    }
  ],
  "report_path": "./audit-results/inspection-report-20260609.md"
}
```

**AIOps actions:** Treat each CRITICAL/HIGH finding as incident symptom; run baseline anomaly + RCA; compare with inspection snapshot timestamps (`data_quality` must note inspection age).

### 2.3 AIOps → Proactive Inspection (`prevention_handoff`) — Mode A1

After RCA/Event Bundle, emit items for **next** inspection cycle:

```json
"prevention_items": [
  {
    "item_id": "prev-001",
    "source_rca_id": "rca-20260609-001",
    "check_type": "disk_usage_trend",
    "resource_type": "cvm",
    "resource_id": "ins-xxx",
    "rationale": "Root cause was disk pressure; add weekly disk rotation check",
    "delegate_to": "qcloud-proactive-inspection",
    "priority": "P1"
  }
]
```

Prefix actions: `RECOMMENDATION (not execution): schedule inspection item ...`

### 2.4 AIOps → FinOps (`finops_advisory`) — Mode A2

```json
"finops_advisory": {
  "trigger": "capacity_saturation|metric_drift|incident_scale_out_risk",
  "confidence": "MEDIUM",
  "affected_products": ["cvm", "cdb"],
  "resource_ids": ["ins-xxx", "cdb-yyy"],
  "signals": [
    {"type": "baseline_anomaly", "metric": "CpuUsage", "anomaly_score": 68},
    {"type": "rca_hypothesis", "hypothesis_id": "E", "description": "CVM saturation"}
  ],
  "recommended_finops_actions": [
    "RECOMMENDATION (not execution): run right-sizing analysis via qcloud-finops-ops",
    "RECOMMENDATION (not execution): compare on-demand vs reserved for ins-xxx"
  ],
  "delegate_to": "qcloud-finops-ops"
}
```

Do not run `DescribeBill*` from this skill unless user explicitly requests joint bill+RCA in same session.

## 3. Mode F1 — FinOps HIGH → Inspection → AIOps

```
FinOps anomaly detected (confidence HIGH)
  ↓
[Delegate] qcloud-proactive-inspection
  Input: {{user.products}} from top_products; focus resources from finops_handoff
  Output: inspection_report + CRITICAL/HIGH findings
  ↓
[AIOps] For each escalated finding + finops top resources:
  Baseline anomaly (Workflow 8) → RCA (Workflow 6/9) → Impact (Workflow 10)
  ↓
Merge into Cross-Skill Bundle (§4)
  ↓
Notify: finops owner + inspection assignee (recommendation only)
```

**Skip inspection** when `finops_handoff.dispatch_inspection=false` or confidence MEDIUM → use **F2** only.

## 4. Mode F2 — FinOps + AIOps Joint Diagnosis

Joint hypothesis categories:

| Bill pattern | Metric pattern | Joint hypothesis | Rules |
|---|---|---|---|
| CVM cost ↑ | CpuUsage/NetworkIn anomaly | Traffic burst / scale-out | E + anomaly |
| CDB cost ↑ | SlowQueries + CpuUseRate | Query regression / missing index | H |
| COS cost ↑ | Request count ↑ | Log lifecycle / traffic | delegate cos-ops |
| Multi-product ↑ | TKE + CLB symptoms | Incident drove autoscale | A + F |
| Cost ↑ | Metrics normal | Config/billing change, new resources | FinOps attribution; CloudAudit |

Score joint confidence:

| Factor | Points |
|---|---|
| FinOps HIGH + metric anomaly same product | +3 |
| Time overlap (bill window ∩ metric window) | +2 |
| Change event in window (Rule F) | +2 |
| Inspection finding matches | +2 |
| Metrics normal despite bill spike | -2 (billing/config suspect) |

## 5. Cross-Skill Orchestration Bundle

Persist: `./audit-results/cross-skill-bundle-YYYYMMDD-HHMMSS.json`

```json
{
  "orchestration_id": "xskill-20260609-001",
  "mode": "F1|F2|P1|A1|A2",
  "participating_skills": ["qcloud-finops-ops", "qcloud-proactive-inspection", "qcloud-aiops-diagnosis"],
  "handoffs": {
    "finops": {},
    "inspection": {},
    "aiops": {}
  },
  "joint_hypothesis": {
    "summary": "CVM traffic burst caused May bill +42% and CLB 5xx",
    "confidence": "HIGH",
    "score": 7
  },
  "artifacts": {
    "rca_id": "rca-20260609-001",
    "inspection_report": "./audit-results/inspection-report-20260609.md",
    "finops_anomaly_ref": "finops-ho-20260609-001",
    "incident_kb_id": "ikb-20260609-001"
  },
  "prevention_items": [],
  "finops_advisory": null,
  "recommendations": [
    {
      "action": "RECOMMENDATION (not execution): right-size CVM ins-aaa after traffic review",
      "delegate_to": "qcloud-finops-ops",
      "priority": "P1"
    }
  ],
  "data_quality": {
    "status": "complete|partial",
    "warnings": []
  }
}
```

Embed summary on RCA Bundle:

```json
"cross_skill_ref": {
  "orchestration_id": "xskill-20260609-001",
  "mode": "F2",
  "joint_hypothesis_summary": "CVM traffic burst ↔ May bill delta"
}
```

## 6. Boundaries

| Skill | Owns | Must NOT |
|---|---|---|
| `qcloud-finops-ops` | Billing, budget, cost attribution, anomaly ii/iii | Execute RCA metric collection as substitute for AIOps |
| `qcloud-proactive-inspection` | Scheduled discovery, threshold detection, inspection report | Active incident response |
| `qcloud-aiops-diagnosis` | RCA, bundles, KB, cross-skill merge | Bill API as primary path; CRUD |

## 7. Variables

| Variable | Source | Use |
|---|---|---|
| `{{user.handoff_source}}` | User/caller | `finops` \| `proactive_inspection` \| `none` |
| `{{user.finops_handoff}}` | FinOps JSON | Mode F1/F2 input |
| `{{user.inspection_handoff}}` | Inspection JSON | Mode P1 input |
| `{{user.orchestration_mode}}` | User | Force `F1`/`F2`/`P1`/`A1`/`A2` or `auto` |
| `{{user.auto_dispatch_inspection}}` | Config | F1 gate (default true when finops HIGH) |

## 8. Changelog

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-06-09 | Modes F1/F2/P1/A1/A2, handoff schemas, Cross-Skill Bundle, joint hypothesis scoring |
