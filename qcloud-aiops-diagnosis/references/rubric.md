# AIOps Diagnosis Quality-Gate Rubric (GCL)

> Runtime rubric for **Generator-Critic-Loop (GCL)** of `qcloud-aiops-diagnosis`.
> **Read-only / advisory** — max_iter=5, no Safety=0 ABORT.

---

## 4. AIOps Diagnosis-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | Diagnosis workflow (any step) | **Surface confidence level (HIGH / MEDIUM / LOW) for each finding; do NOT present correlation as causation; if confidence < HIGH, include a caveat "this is an automated suggestion, verify before action"** | AI-driven diagnosis can produce false correlations. Presenting a MEDIUM-confidence finding as a root cause can mislead ops decisions |
| 2 | Cross-skill data collection | **When reading resource data from product skills (CVM, CDB, etc.): use only read APIs; do NOT mutate any resource; confirm the delegation is read-only in the trace** | Diagnosis must not cross into execution. The most common pattern: "The diagnosis collected data from the CDB instance, but the read query affected the instance's performance" |
| 3 | Time-range bounded correlation | **Surface the diagnosis time range; warn if historical data > 30 days may have different retention/availability; do NOT correlate data from non-overlapping time windows** | Correlating a CPU spike from last hour with a slow query from 3 days ago produces meaningless results |
| 4 | Data recency disclosure | **For each data source, surface when it was last updated; warn if data is older than 5 minutes; for CLS log data, surface log ingestion delay (typically 1-3 minutes)** | Stale data leads to incorrect diagnosis. The most common pattern: "The diagnosis said the CPU is normal now — but the metric data was from 10 minutes ago, and the actual CPU was already spiking" |
| 5 | Recommendation boundary | **For any recommendation that involves a mutation (e.g., "restart the instance", "scale up the disk"): prefix with "RECOMMENDATION (not execution)"; do NOT auto-execute; delegate to the product skill** | Diagnosis must stop at recommendation. The most common pattern: "The diagnosis said 'restart the CVM' and the agent restarted the production instance" |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 AIOps Diagnosis rollout: rubric (5 rules: confidence disclosure, read-only cross-skill, time-range correlation, data recency, recommendation boundary) |