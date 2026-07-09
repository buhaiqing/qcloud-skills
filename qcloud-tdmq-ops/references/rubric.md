# TDMQ GCL Rubric

> Runtime scoring rubric for the **Generator-Critic-Loop (GCL)** of `qcloud-tdmq-ops`.
> Source-of-truth: [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) and §8 Per-Skill Defaults (`qcloud-tdmq-ops` → **required**, `max_iterations = 2`).

---

## 1. Scope and applicability

| Applies to | Does NOT apply to |
|---|---|
| Every TDMQ mutation operation invoked by this skill: `CreateRocketMQCluster`, `CreateRocketMQNamespace`, `CreateRocketMQTopic`, `CreateRocketMQGroup`, `DeleteRocketMQTopic`, `DeleteRocketMQCluster`, `ResetRocketMQConsumerOffSet`, `RewindCmqQueue` | Pure read operations (`DescribeRocketMQClusters`, `DescribeRocketMQTopics`, `ReceiveMessage`) — scored at the Orchestrator's discretion; recommend max_iter=1, no hard abort |
| Dual-path execution (tccli primary, SDK fallback) | — |
| Data loss risk operations (`DeleteRocketMQTopic`, `DeleteRocketMQCluster`) | — |

---

## 2. Five rubric dimensions (mandatory)

Each dimension is scored `0`, `0.5`, or `1`. Thresholds are taken from
[AGENTS.md §3](../../AGENTS.md#3-rubric-mandatory-per-skill). Correctness = 1.0 is **required**
for destructive operations (DeleteRocketMQCluster, DeleteRocketMQTopic).

| # | Dimension | Threshold | Why this threshold for TDMQ |
|---|---|---|---|
| 1 | **Correctness** | ≥ 0.5 (1.0 required for destructive ops) | Half-correct delete may leave orphaned topics/consumers |
| 2 | **Safety** | **= 1** (strict) | Deletes destroy messages; offset reset alters consumption state |
| 3 | **Idempotency** | ≥ 0.5 | TDMQ resources have async status; retry carefully |
| 4 | **Traceability** | ≥ 0.5 | Every call has `RequestId`; resource IDs are audit anchors |
| 5 | **Spec Compliance** | ≥ 0.5 | Refers to `references/cli-usage.md` / `references/core-concepts.md` |

**Safety = 0 → ABORT immediately**, regardless of total score.

---

## 3. Per-dimension scoring checklist

### 3.1 Correctness (weight: high)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Returned `{{output.cluster_id}}` / `{{output.topic_id}}` parses; describe confirms exists | ✓ | ID parses but state not yet confirmed | ID missing, wrong shape |
| For `DeleteRocketMQTopic`: post-state confirmed via `DescribeRocketMQTopics` absent | ✓ | — | topic "deleted" but still listed |
| For `DeleteRocketMQCluster`: all child resources verified absent | ✓ | partial | cluster still present |
| For `ResetRocketMQConsumerOffSet`: offset confirmed changed via `DescribeRocketMQConsumerConnections` | ✓ | partial | offset unchanged |

### 3.2 Safety (weight: highest; threshold = 1)

| Check | Score 1 | Score 0 |
|---|---|---|
| Destructive op has **explicit user confirmation** captured (cluster/topic ID + name echoed) | ✓ | missing or implicit |
| For `DeleteRocketMQCluster` — warning that ALL child resources destroyed; verify cluster empty | ✓ | not surfaced |
| For `DeleteRocketMQTopic` — warning about message loss; verify no active consumers | ✓ | not surfaced |
| For `ResetRocketMQConsumerOffSet` / `RewindCmqQueue` — target offset/timestamp confirmed with user | ✓ | not confirmed |
| Credentials masked in trace | ✓ | credential leaked |

### 3.3 Idempotency (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| For `DeleteRocketMQTopic` retries: same topic ID; already-deleted recognized as no-op | ✓ | retry fresh ID | second delete on deleted topic |
| `CreateRocketMQTopic` retry after `InvalidParameter.TopicExists`: reuse existing | ✓ | — | duplicate created |
| `ResetRocketMQConsumerOffSet` retry: idempotent target offset | ✓ | — | offset drifted |

### 3.4 Traceability (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Full CLI/SDK call captured (masking credentials) | ✓ | only params | reconstructed |
| Raw response JSON captured (RequestId, resource ID) | ✓ | only IDs | reconstructed |
| Polling tail captured for state-transition ops | ✓ | only initial | empty |
| Exit code captured | ✓ | — | missing |

### 3.5 Spec Compliance (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Cluster/namespace/topic names valid per TDMQ spec | ✓ | — | invalid submitted |
| Region valid and supports TDMQ | ✓ | — | invalid region |
| Message body within size limits | ✓ | — | oversized body |

---

## 4. TDMQ-specific safety rules

These rules are the **must-cover** subset. Each is enforced by the Safety dimension; missing any → Safety = 0 → ABORT.

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DeleteRocketMQCluster` | **Cluster ID + Name echoed + explicit confirmation + verify empty (no topics/groups) + total destruction warning** | Deletes all namespaces, topics, groups, and messages irreversibly |
| 2 | `DeleteRocketMQTopic` | **Topic + cluster + namespace echoed + explicit confirmation + active-consumer check + message loss warning** | Destroys all messages and subscription state |
| 3 | `ResetRocketMQConsumerOffSet` / `RewindCmqQueue` | **Target offset/timestamp echoed + explicit confirmation + downstream-impact warning** | Reprocesses or skips messages; affects all consumers in group |

---

## 5. Output schema (returned by Critic)

Strict JSON, same shape as [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill):

```json
{
  "scores": {
    "correctness": 0|0.5|1,
    "safety": 0|1,
    "idempotency": 0|0.5|1,
    "traceability": 0|0.5|1,
    "spec_compliance": 0|0.5|1
  },
  "suggestions": ["≤ 3 concrete, executable improvements"],
  "blocking": true|false,
  "rule_violations": [
    {"rule": 1, "operation": "DeleteRocketMQCluster", "rationale": "No empty-cluster verification"}
  ],
  "thresholds": {
    "correctness": 1.0,
    "safety": 1.0,
    "idempotency": 0.5,
    "traceability": 0.5,
    "spec_compliance": 0.5
  }
}
```

---

## 6. Worked examples

### Example A — PASS on `DeleteRocketMQTopic`

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | Topic deleted; `DescribeRocketMQTopics` confirms absent |
| Safety | 1 | Topic + cluster + namespace echoed; user confirmed; no active consumers; message loss warned |
| Idempotency | 1 | Retry on deleted topic returns no-op |
| Traceability | 1 | Full CLI call + RequestId captured |
| Spec Compliance | 1 | Region valid |

`blocking: false`. `final: PASS, iter: 1`.

### Example B — SAFETY_FAIL on `DeleteRocketMQCluster`

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | Cluster deleted |
| **Safety** | **0** | Rule 1 violated: no empty-cluster verification; child topics still existed |
| Idempotency | 1 | — |
| Traceability | 1 | Everything logged |
| Spec Compliance | 1 | — |

`blocking: true`. `rule_violations: [{rule: 1, operation: "DeleteRocketMQCluster", rationale: "No empty-cluster verification; child topics destroyed silently"}]`. **ABORT** — recovery: verify cluster empty (delete all topics/groups/namespaces) before retry.

### Example C — RETRY on `CreateRocketMQTopic` (namespace missing)

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 0.5 | Topic creation failed — namespace not found |
| Safety | 1 | Pre-flight validation performed |
| Idempotency | 1 | — |
| Traceability | 1 | Everything logged |
| **Spec Compliance** | **0** | Rule 3 violated: namespace not validated before submission |

`blocking: true`. `suggestions: ["Create namespace first or verify existing namespace"]`. After G creates namespace and retries, all dimensions score 1.

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-09 | Initial TDMQ rubric: 3 rules (cluster delete guard, topic delete guard, offset/rewind confirmation). Dual-path execution. Covers RocketMQ lifecycle + CMQ rewind. |

## 8. See also

- [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill)
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-tdmq-ops` is `required`, `max_iter=2`
- [`prompt-templates.md`](prompt-templates.md)
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations)
