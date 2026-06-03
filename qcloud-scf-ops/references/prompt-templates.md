# SCF GCL Prompt Templates

> Prompt skeletons for G/C/O of `qcloud-scf-ops`.
> See [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) for the full backbone.

---

## 1. Generator — SCF delta

```text
You are the Generator for the qcloud-scf-ops skill (Tencent Cloud SCF serverless).
- PRIMARY: tccli scf <subcommand> ...  (verify with `tccli scf help`)
- FALLBACK: Python SDK tencentcloud-sdk-python-scf; namespace:
  from tencentcloud.scf.v20180416 import scf_client, models
```

---

## 4. Per-operation variants

| Operation | Pre-flight augmentation |
|---|---|
| `DeleteFunction` | rule 1: Function name + namespace + version count + trigger count echo; warn cascade; confirm |
| `DeleteFunctionTriggers` | rule 2: Trigger type + name + source ARN echo; warn disruption; for timer: surface cron; confirm |
| `DeleteNamespace` / `DeleteLayerVersion` | rule 3: Namespace/layer + version echo; list dependents; warn cascade; confirm |
| `UpdateFunctionCode` / `UpdateFunctionConfiguration` | rule 4: BEFORE/AFTER diff; warn env var overwrite; confirm |
| `InvokeFunction` (side effects) | rule 5: Surface side effects; confirm for Event type; warn live execution |

---

## 5. SCF-specific anti-patterns

- ❌ **DeleteFunction without trigger enumeration** — silent integration breakage
- ❌ **DeleteLayerVersion still referenced** — cold start failures
- ❌ **UpdateFunctionCode without env var preservation** — overwrite kills config
- ❌ **InvokeFunction with side effects** — unintended DB writes / API calls

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 SCF rollout: templates (5 rules, function-delete cascade, trigger disruption, env var overwrite, invocation side effects) |