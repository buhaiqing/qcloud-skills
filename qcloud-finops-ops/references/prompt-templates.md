# FinOps GCL Prompt Templates

> Prompt skeletons for G/C/O of `qcloud-finops-ops`.
> **Read-only / advisory** — no Safety=0 ABORT. `max_iter=3`, no destructive ops.
> See [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) for the backbone.

---

## 1. Generator — FinOps delta

```text
You are the Generator for the qcloud-finops-ops skill (Tencent Cloud FinOps).
- Reports and analysis only — NEVER auto-execute billing changes
- PRIMARY: tccli billing <subcommand> ... (verify with `tccli billing help`)
- FALLBACK: Python SDK tencentcloud-sdk-python; namespaces:
  from tencentcloud.billing.v20180709 import billing_client, models
  from tencentcloud.partners.v20180321 import partners_client, models
```

Key constraint: NEVER output raw billing data to trace. Summarize only.

---

## 4. Per-operation variants

| Operation | Pre-flight augmentation |
|---|---|
| Bill download / report | rule 1: Warn sensitive data; mask account IDs, invoice URLs, contacts; no raw output to trace |
| Anomaly detection / budget alert | rule 2: Clarify no-auto-execute; suggest delegation path; confirm user intent |
| Tag cost allocation change | rule 3: Warn future-only attribution; existing reports unchanged; confirm |
| COS idle detection | rule 4: Warn CLS query accuracy; surface time range; verify before action |
| Resource recommendation | rule 5: Delegate to product skill; do NOT auto-execute; confirm understanding |

---

## 5. FinOps-specific anti-patterns

- ❌ **Raw billing data in trace** — privacy violation
- ❌ **Auto-executing a recommendation** — violates skill boundary
- ❌ **Presenting idle detection as exact** — CLS query has latency/sampling
- ❌ **Changing tag allocation without attribution timing clarification** — stakeholder confusion
- ❌ **Outputting invoice URLs to trace** — sensitive financial data

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 FinOps rollout: templates (5 rules, billing data privacy, no-auto-execute, idle detection accuracy boundary, cross-skill delegation) |