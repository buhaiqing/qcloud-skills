# CKafka Quality-Gate Rubric (GCL)

> Runtime scoring rubric for the **Generator-Critic-Loop (GCL)** of `qcloud-ckafka-ops`.
> Sibling rubrics: see [`qcloud-clb-ops/references/rubric.md`](../clb-ops/references/rubric.md) for the 5-dimension backbone.

---

## 1. Scope and applicability

| Applies to | Does NOT apply to |
|---|---|
| CKafka mutation: `DeleteInstance`, `DeleteTopic`, `ModifyInstanceAttributes`, `ModifyTopic`, `CreatePartition`, `CreateAcl`, `DeleteAcl`, `CreateConsumerGroup`, `DeleteConsumerGroup` | Read operations (`DescribeInstances`, `DescribeTopic`, `DescribeConsumerGroup`, `DescribeACL`) — optional |

---

## 4. CKafka-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DeleteInstance` (any) | **Instance ID + Name echo; warn that ALL topics, messages, consumer offsets, and ACL configurations are permanently removed; list all topics (via `DescribeTopic`) and consumer groups (via `DescribeConsumerGroup`) before commit; require literal "CONFIRM DELETE <instance_id>" confirmation** | CKafka instance deletion is irreversible. Unlike CDB's `IsolateDBInstance` (recycle bin), there is no grace period. The most common CKafka incident: user deletes a "dev" instance but it is referenced by production consumers that now get `UnknownTopicOrPartition` |
| 2 | `DeleteTopic` (any) | **Topic Name + Partition count + any active consumer groups subscribed (via `DescribeTopicSubscribeGroup`) echoed; warn that all messages (by retention) and consumer offsets are lost; require explicit confirmation with topic name** | Topic deletion is cascading: all consumer groups lose their offsets for this topic, and replay is impossible unless messages were exported. This is the #1 CKafka data-loss pattern |
| 3 | `ModifyTopic` (partition count change) | **Show current partition count → target; warn that partition increase is one-directional (Kafka cannot shrink partitions); surface rebalancing impact on consumers (all consumer groups for this topic will rebalance — potentially dropping messages); require confirmation when the increase > 2× current** | Partition rebalancing during active consumption can cause message duplication or ordering violations. A > 2× increase is rarely needed and nearly always a mistake (user meant to create a new topic) |
| 4 | `ModifyInstanceAttributes` (broker config: `MaxTopicNum`, `MessageRetention`, `CleanUpPolicy`, `LogRetentionTime`, etc.) | **Echo current → new value for each modified attribute; for `MessageRetention` reduction: warn that messages older than the new retention will be deleted at the next retention cycle; for `CleanUpPolicy` change (delete→compact or vice versa): warn that log cleanup behavior changes irreversibly for existing segments; require confirmation for each change** | The most common CKafka config footgun: user reduces `MessageRetention` to "save costs" not realizing that messages will be deleted within minutes — not at the next rotation. `CleanUpPolicy` toggle is particularly dangerous: switching from `delete` to `compact` on a topic with active producers can cause compaction to fail silently |
| 5 | `CreateAcl` / `DeleteAcl` (access control) | **For `CreateAcl`: surface the ACL rule being added (principal, host, operation, permission type); warn if `PermissionType=ALLOW` + `Operation=ALL` + `Host=*` (open access); require explicit confirmation for permissive ACLs. For `DeleteAcl`: surface the ACL rule being removed; warn if the rule is the only allow rule for an operation — a consumer group may be locked out** | ACL mistakes are the #2 CKafka pain point (after partition rebalancing). A single `Host=*` ACL opens the cluster to any network that can reach the CKafka endpoint. Deleting the last allow rule for `READ` on a consumer group locks out all consumers until a new ACL is created — and the user may not realize until the consumer health check fails |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 CKafka rollout: rubric (5 rules: instance-delete cascade, topic-delete offset loss, partition rebalancing, broker-config retention drop, ACL open-access guard) |

## 8. See also

- [AGENTS.md §3](../../AGENTS.md#3-rubric-mandatory-per-skill), [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud)
- [`prompt-templates.md`](prompt-templates.md)
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates)
- Sibling rubrics: [`cvm`](../cvm-ops/references/rubric.md), [`cdb`](../cdb-ops/references/rubric.md), [`cos`](../cos-ops/references/rubric.md), [`clb`](../clb-ops/references/rubric.md), [`tke`](../tke-ops/references/rubric.md), [`cbs`](../cbs-ops/references/rubric.md)