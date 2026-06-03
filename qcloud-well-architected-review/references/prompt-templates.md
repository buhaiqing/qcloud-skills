# Well-Architected Review GCL Prompt Templates

> See [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) for backbone.

---

## 4. Per-operation variants

| Operation | Pre-flight augmentation |
|---|---|
| Assessment (any pillar) | rule 1: Surface scope; mark skipped pillars as "NOT ASSESSED" |
| Cross-skill data read | rule 2: Confirm read-only; no alarm/SG modification; log delegation |
| Finding output | rule 3: Surface confidence (HIGH/MEDIUM/LOW); caveat for incomplete data |
| Cross-pillar analysis | rule 4: Surface conflicting recommendations; flag trade-offs |
| Delegation outside matrix | rule 5: Check Delegation Matrix; reject out-of-scope skills |

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 Well-Architected Review rollout: templates (5 rules, scope clarity, confidence disclosure, cross-pillar consistency, delegation matrix) |