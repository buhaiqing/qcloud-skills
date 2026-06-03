# SCF Quality-Gate Rubric (GCL)

> Runtime rubric for **Generator-Critic-Loop (GCL)** of `qcloud-scf-ops`.
> See [`qcloud-clb-ops/references/rubric.md`](../clb-ops/references/rubric.md) for the backbone.

---

## 4. SCF-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DeleteFunction` (any version/alias) | **Function name + namespace + version count + active trigger count echo; warn that deletion removes ALL versions, aliases, provisioned concurrency configs; list active triggers (via `ListTriggers`); require explicit confirmation with function name** | SCF function deletion is final. If the function has any triggers (API GW, COS, CKafka, timer), those integrations silently break. The most common incident: "I deleted the test function but the timer trigger was still scheduled and caused an alert for 3 days" |
| 2 | `DeleteFunctionTriggers` (any) | **Trigger type + trigger name + trigger-escaped source ARN echo; warn that removing a trigger stops all event-driven invocations; for timer triggers: surface `CronExpression`; require confirmation** | Removing a trigger is a service disruption. Timer triggers are especially dangerous because the user may not know the cron schedule and the trigger is the only source of events for the function |
| 3 | `DeleteNamespace` / `DeleteLayerVersion` | **Namespace name / layer name + version echo; for `DeleteNamespace`: warn that ALL functions, layers, aliases in the namespace are destroyed; for `DeleteLayerVersion`: list functions using this layer version; warn that those functions will fail on next cold start; require confirmation** | Deleting a namespace cascades to all child functions. Deleting a layer version that is still referenced by functions will cause them to error on cold start — but only on cold start, making it hard to detect |
| 4 | `UpdateFunctionCode` / `UpdateFunctionConfiguration` (code or config change) | **Show BEFORE/AFTER diff (for code: `CosBucketName`, `CosObjectName`, `ZipFile`; for config: `MemorySize`, `Timeout`, `Environment`, `VpcConfig`); warn that the update triggers a new deployment with zero-downtime rollout (but the old version's provisioned concurrency is released); for `Environment` variable changes: warn that the old env vars are overwritten; require confirmation** | SCF updates are atomic but overwrite env vars entirely. The most common incident: "I updated the function code but the new env vars didn't have the old `DATABASE_URL` — the function broke" |
| 5 | `InvokeFunction` (with `InvocationType=RequestResponse` or `Event`) | **For `InvocationType=Event` (async): warn that the function may not execute immediately and errors are logged to SLS; for `InvocationType=RequestResponse` with a function that has side effects (DB writes, API calls): warn that the invocation is live — the function's side effects will execute; require explicit confirmation for functions with known side effects** | Invoking a function with `InvocationType=Event` is fire-and-forget: the caller gets a `RequestId` but no error unless configured. The most common incident: "I invoked the function to test it but the function writes to the production database and the test invocation created 1000 records" |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 SCF rollout: rubric (5 rules: function-delete cascade, trigger removal disruption, namespace/layer cascade, code update env var overwrite, function invocation side effects) |