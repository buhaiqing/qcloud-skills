# FinOps Quality-Gate Rubric (GCL)

> Runtime rubric for **Generator-Critic-Loop (GCL)** of `qcloud-finops-ops`.
> **Read-only / advisory skill** — no destructive operations. Safety dimension is scored
> but **not** set to ABORT (no destructive ops to ABORT from).
> See [`qcloud-clb-ops/references/rubric.md`](../clb-ops/references/rubric.md) for the backbone.

---

## 4. FinOps-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | Bill download / cost report generation (any) | **Warn that the report contains sensitive billing data — do NOT output the raw report contents in the trace (only summary stats); mask any account IDs, invoice URLs, or personal billing contact info** | FinOps reports contain account-level spend data, invoice numbers, and potentially personal contact info. Leaking these into the trace is a data-privacy issue |
| 2 | Cost anomaly detection / budget alert configuration | **For any cost anomaly that triggers a budget alert: warn that the system will NOT auto-execute any billing changes (per skill constraint); suggest manual resource cleanup via the relevant product skill; confirm the user's intent to share the anomaly finding** | FinOps is reports-only. The most common mis-expectation: "The FinOps skill found an idle instance — I expected it to terminate it" |
| 3 | Tag-based cost allocation modification | **Warn that changing cost allocation tags changes how costs are attributed in future reports; existing report data is NOT retroactively re-attributed; require confirmation for tag changes** | Tag changes affect future cost allocation, which can confuse stakeholders if not communicated. The most common pattern: "I changed the team tag from 'team-a' to 'team-b' but last month's report still shows 'team-a' — the manager thinks team-b has zero costs" |
| 4 | COS idle detection output | **For idle detection: warn that the storage cost calculation is approximate (per CLS query accuracy); surface the query's time range; do NOT present the output as exact billing data; require the user to verify via the COS console before taking action** | Idle detection runs on CLS log queries which have inherent latency and sampling. The most common pattern: "The skill told me a 1TB bucket is idle and I should delete it — but the bucket had critical logs from yesterday that hadn't been queried yet" |
| 5 | Resource type report cross-skill delegation | **For resource-type recommendations (e.g., "consider terminating idle CVM"): delegate to the specific product skill (qcloud-cvm-ops); do NOT auto-execute; surface the recommendation and the delegation path; confirm that the user understands this is a recommendation, not an execution plan** | The FinOps skill must not cross the boundary into execution. The most common pattern: "The FinOps skill said 'use idle detection' and then terminated the instance" |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 FinOps rollout: rubric (5 rules: billing data privacy, no-auto-execute constraint, tag attribution timing, idle detection accuracy boundary, cross-skill delegation no-execution) |