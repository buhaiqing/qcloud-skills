# AIOps Diagnosis GCL Prompt Templates

> See [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) for backbone.
> **Read-only** — no destructive ops. No Safety=0 ABORT.

---

## 4. Per-operation variants

| Operation | Pre-flight augmentation |
|---|---|
| Diagnosis workflow | rule 1: Surface confidence level; do NOT present correlation as causation |
| Cross-skill data read | rule 2: Confirm read-only; no mutation; log delegation |
| Time-range correlation | rule 3: Surface diagnosis window; warn non-overlapping windows |
| Data source use | rule 4: Surface data recency; warn ingestion delay |
| Recommendation output | rule 5: Prefix "RECOMMENDATION (not execution)"; delegate to product skill |

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 AIOps Diagnosis rollout: templates (5 rules, read-only cross-skill, confidence disclosure, recommendation boundary) |