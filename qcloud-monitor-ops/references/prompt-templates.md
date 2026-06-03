# Monitor GCL Prompt Templates

> Prompt skeletons for G/C/O of `qcloud-monitor-ops`.
> See [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) for the backbone.

---

## 1. Generator — Monitor delta

```text
You are the Generator for the qcloud-monitor-ops skill (Tencent Cloud Monitor).
- PRIMARY: tccli monitor <subcommand> ...  (verify with `tccli monitor help`)
- FALLBACK: Python SDK tencentcloud-sdk-python-monitor; namespace:
  from tencentcloud.monitor.v20180724 import monitor_client, models
```

---

## 4. Per-operation variants

| Operation | Pre-flight augmentation |
|---|---|
| `DeleteAlarmPolicy` | rule 1: Policy ID + Name + bound resource count echo; warn alert silence; literal confirm |
| `UnbindAlarmRuleResource` | rule 2: Policy + Resource ID echo; warn coverage loss; surface remaining resources; confirm |
| `ModifyAlarmPolicy` (condition) | rule 3: BEFORE/AFTER diff; warn threshold drift (higher misses issues, lower = false positives); confirm per field |
| `DeleteAlarmNotices` | rule 4: Notice template + type echo; list referencing policies; warn notification silence; confirm |
| `SetDefaultAlarmPolicy` / auto-remediation | rule 5: Warn default applies to ALL future resources; warn auto-remediation without human approval; confirm |

---

## 5. Monitor-specific anti-patterns

- ❌ **DeleteAlarmPolicy without bound-resource count** — silent alert blackout
- ❌ **UnbindAlarmRuleResource without new-policy reassignment** — unmonitored resource
- ❌ **ModifyAlarmPolicy increasing threshold without impact assessment** — critical miss
- ❌ **DeleteAlarmNotices in-use** — notifications silently stop
- ❌ **SetDefaultAlarmPolicy without scope understanding** — far-reaching consequences

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 Monitor rollout: templates (5 rules, alarm-policy deletion silent incident, unbinding coverage loss, threshold drift, notice template silence, default policy reach) |