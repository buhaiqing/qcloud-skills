# CLS GCL Prompt Templates

> Prompt skeletons for G/C/O of `qcloud-cls-ops`.
> See [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) for the full backbone.

---

## 1. Generator — CLS delta

```text
You are the Generator for the qcloud-cls-ops skill (Tencent Cloud CLS log service).
- PRIMARY: tccli cls <subcommand> ...  (verify with `tccli cls help`)
- FALLBACK: Python SDK tencentcloud-sdk-python-cls; namespace:
  from tencentcloud.cls.v20201016 import cls_client, models
```

---

## 4. Per-operation variants

| Operation | Pre-flight augmentation |
|---|---|
| `DeleteLogset` | rule 1: Logset ID + Name + topic count echo; list topics; warn cascade; literal confirm |
| `DeleteTopic` | rule 2: Topic ID + Name + shard count + data size echo; warn data loss; check shipping tasks; confirm |
| `DeleteIndex` | rule 3: Index ID + Topic ID echo; warn data unsearchable; warn re-index time+cost; confirm |
| `DeleteMachineGroup` / `DeleteConfigAttachment` | rule 4: MachineGroup ID + config count + agent count echo; warn collection stop; confirm |
| `ModifyConfig` | rule 5: BEFORE/AFTER diff; warn ~60s apply delay; warn path/filter changes cause gaps; confirm per field |

---

## 5. CLS-specific anti-patterns

- ❌ **DeleteLogset without topic enumeration** — data loss cascade surprise
- ❌ **DeleteTopic without shipping task check** — COS/CKafka pipeline broken
- ❌ **DeleteIndex without re-index cost warning** — "but I need to search the old data"
- ❌ **DeleteMachineGroup without agent reassignment** — silent log gap
- ❌ **ModifyConfig path without old-path coverage** — log collection gap

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 CLS rollout: templates (5 rules, logset cascade, topic data loss, index unsearchable, machine group collection stop, config change gap) |