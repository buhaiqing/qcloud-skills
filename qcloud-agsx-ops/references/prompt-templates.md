# AGSX GCL Prompt Templates

> Prompt skeletons for G/C/O of `qcloud-agsx-ops`. **SDK-only** — no tccli support.
> See [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) for the backbone.

---

## 1. Generator — AGSX delta

```text
You are the Generator for the qcloud-agsx-ops skill (Tencent Cloud AGSX agent service).
- PRIMARY: **SDK only** — `tccli ags help` returns "Invalid product"
- FALLBACK: Python SDK tencentcloud-sdk-python (v20190312):
  from tencentcloud.ags.v20190312 import ags_client, models
```

---

## 4. Per-operation variants

| Operation | Pre-flight augmentation |
|---|---|
| `DeleteAgentPool` / `TerminateAgentPool` | rule 1: Pool ID + Name + agent count echo; warn cascade; confirm |
| `DeleteAgent` (active) | rule 2: Agent ID + name + status echo; check pending executions; confirm |
| `TerminateAgentExecution` | rule 3: Execution ID + agent ID + start time echo; warn no-rollback; confirm |
| `UpdateAgentPoolConfig` | rule 4: BEFORE/AFTER diff; warn capacity/timeout changes kill in-flight agents; confirm per field |
| `CreateAgentPool` / `CreateAgent` | rule 5: Surface cost + quota; warn compute-heavy agent billing; confirm |

---

## 5. AGSX-specific anti-patterns

- ❌ **TerminateAgentExecution without rollback warning** — partial state changes persist
- ❌ **UpdateAgentPoolConfig MaxConcurrency reduction** — in-flight agents terminated
- ❌ **CreateAgentPool without cost estimation** — bill shock
- ❌ **DeleteAgentPool without agent count enumeration** — silent cascade

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 AGSX rollout: templates (5 rules, SDK-only, agent-pool cascade, force-termination no-rollback, pool config disruption, provisioning cost) |