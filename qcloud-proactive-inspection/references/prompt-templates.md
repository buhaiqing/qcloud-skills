# Proactive Inspection GCL Prompt Templates

> See [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) for backbone.

---

## 4. Per-operation variants

| Operation | Pre-flight augmentation |
|---|---|
| Inspection run | rule 1: Check idempotency (same scope/time within 1h); warn duplicate; track inspection ID |
| Cross-skill data collection | rule 2: Confirm read-only; no alarm/notification triggers |
| Report generation | rule 3: Mask credentials/API keys in output; check report content |
| Result presentation | rule 4: Surface time range; warn snapshot-only; add "state as of <timestamp>" |
| File write | rule 5: Check output path security; no public upload without confirmation |

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 Proactive Inspection rollout: templates (5 rules, run idempotency, read-only collection, credential safety, report path security) |