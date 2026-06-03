# Monitor Quality-Gate Rubric (GCL)

> Runtime rubric for **Generator-Critic-Loop (GCL)** of `qcloud-monitor-ops`.
> See [`qcloud-clb-ops/references/rubric.md`](../clb-ops/references/rubric.md) for the backbone.

---

## 4. Monitor-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DeleteAlarmPolicy` (any) | **Policy ID + Name + bound resource count echo (via `DescribeBindingAlarmPolicy` or equivalent); list the resource types and IDs; warn that deletion stops ALL alerts for the bound resources — no one will be notified if the resource fails; require literal "CONFIRM DELETE ALARM <name>"** | Alarms are the "canary in the coal mine" for production. Deleting an alarm policy is a silent incident: the resource continues running but nobody gets paged when it fails. The most common incident: "I reorganized alarm policies and deleted the old one, but forgot that the production CVM was still only bound to that old policy — the disk ran out of space and nobody noticed" |
| 2 | `UnbindAlarmRuleResource` / `UnBindingPolicyObject` | **Policy ID + Name + resource ID + resource type echoed; warn that unbinding the resource stops alerts for that specific resource; surface remaining bound resources; require confirmation with resource ID** | Unbinding a specific resource from a policy is often done thinking "I'll add it to a new policy later" — but the new policy may not be created. The most common pattern: "I unbound the DB instance from the staging policy but forgot to bind it to the production policy — the DB was unmonitored for 3 days" |
| 3 | `ModifyAlarmPolicy` / `ModifyAlarmPolicyCondition` (change conditions: metric threshold, evaluation period, consecutive periods) | **Show BEFORE/AFTER condition diff (metric, comparison operator, threshold value, evaluation window); warn that increasing the threshold reduces sensitivity — critical issues may be missed; warn that decreasing the evaluation period increases false positives; require confirmation for each changed condition** | Alarm condition changes are applied immediately. The most common incident: "I changed the CPU threshold from 80% to 95% to silence a noisy alert, but a real CPU spike went unnoticed and the autoscaler didn't trigger" |
| 4 | `DeleteAlarmNotices` (delete notice template) | **Notice template ID + Name + notice type (Email/SMS/WeChat/Webhook) + channel count; list alarm policies that use this notice template (via `DescribeAlarmPolicies` with notice template filter); warn that deleting an in-use notice template will stop ALL notifications for those policies; require confirmation** | Delete a notice template that's in use = all alarm notifications silently stop. The most common incident: "I cleaned up old notice templates and deleted the 'Production' template because I thought a newer one had replaced it — but the production alarm policy was still referencing the deleted template, so all notifications failed silently" |
| 5 | `SetDefaultAlarmPolicy` / `ModifyAlarmPolicyTasks` (default policy or auto-remediation tasks) | **Surface that the default alarm policy applies to all newly created resources; warn that changing the default changes alerting behavior for ALL future resources; for auto-remediation (AS reactions): warn that enabling auto-remediation may trigger automatic scaling actions without human approval; require confirmation** | The default alarm policy is far-reaching. Changing it can have unintended consequences for resources that inherit it. Auto-remediation tasks (like replacing an unhealthy CVM) can cause unexpected production changes |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 Monitor rollout: rubric (5 rules: alarm-policy deletion silent incident, resource unbinding lost coverage, condition change threshold drift, notice template notification silence, default policy far-reaching change) |