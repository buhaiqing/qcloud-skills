# CKafka GCL Prompt Templates

> Prompt skeletons for G/C/O of `qcloud-ckafka-ops`.
> See [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) for the full backbone.

---

## 1. Generator — CKafka delta

```text
You are the Generator for the qcloud-ckafka-ops skill (Tencent Cloud CKafka).
- PRIMARY: tccli ckafka <subcommand> ...  (verify with `tccli ckafka help`)
- FALLBACK: Python SDK tencentcloud-sdk-python-ckafka; namespace:
  from tencentcloud.ckafka.v20190819 import ckafka_client, models
```

Variables: `user.instance_id`, `user.topic_name`, `user.partition_count`, `user.acl_rule`;
outputs: `$.Response.InstanceId`, `$.Response.TopicId`, `$.Response.Result`.

Pre-flight for `DeleteInstance`: list topics + consumer groups; echo counts.
Pre-flight for `CreateAcl`: check `Host=*` + `Operation=ALL` + `PermissionType=ALLOW` combo.

---

## 4. Per-operation variants

| Operation | Pre-flight augmentation |
|---|---|
| `DeleteInstance` | rule 1: ID + Name echo; list topics/consumer groups; warn irreversible; literal confirm |
| `DeleteTopic` | rule 2: Topic + partition count + active consumer groups; confirm with topic name |
| `ModifyTopic` (partition change) | rule 3: Show current → target; warn one-directional; surface rebalancing impact; confirm if >2× |
| `ModifyInstanceAttributes` (retention/config) | rule 4: Echo current → new; warn retention reduction timing; warn CleanUpPolicy irreversibility |
| `CreateAcl` / `DeleteAcl` | rule 5: Surface ACL rule; warn `Host=*` + `ALL` + `ALLOW` open access; warn last-rule lockout |

---

## 5. CKafka-specific anti-patterns

- ❌ **DeleteInstance without topic/consumer group enumeration** — data loss cascade
- ❌ **ModifyTopic partition increase >2× without rebalancing warning** — consumer disruption
- ❌ **CreateAcl `Host=*` with `ALL` operation** — open access to cluster
- ❌ **DeleteAcl — last allow rule removed** — consumer group lockout
- ❌ **MessageRetention reduction without timing clarification** — "saving costs" = immediate message loss

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 CKafka rollout: templates (5 rules, instance-delete cascade, partition rebalancing, ACL open-access guard) |