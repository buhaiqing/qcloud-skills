# CKafka GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-ckafka-ops` |
| CLI | `tccli ckafka help` |
| max_iterations | 2 |


Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (CKafka).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **2**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (CKafka — 5 rules). Do not duplicate gate text here.

| Role | Action |
|---|---|
| Generator | Load rubric §4; map op → rule 1–5; run gates; append to trace `preflight` |
| Critic | Score rubric §3 + mark §4 rules VIOLATED / SATISFIED / NOT-APPLICABLE |
| Orchestrator | Safety=0 on §4 violation (destructive) → ABORT; advisory/read-only: rubric §2 |

API flows: [SKILL.md](../SKILL.md) (Pre-flight → Execute → Verify → Recover).

---

## 5. Anti-patterns (banned)


> Generic GCL anti-patterns: [../../qcloud-skill-generator/references/gcl-prompt-backbone.md](../../qcloud-skill-generator/references/gcl-prompt-backbone.md) §4.
> Below: **product-only** bans.


- ❌ **Logging secret content** — `TENCENTCLOUD_SECRET_KEY` MUST NOT appear in
  command line, raw response, or trace beyond `<masked>` / `***`.

CKafka-specific (the canonical CKafka data-loss patterns):

- ❌ **DeleteTopic without consumer-group enumeration** — the #1 CKafka incident
  pattern. The Generator must call `DescribeTopicSubscribeGroup` + `DescribeConsumerGroup`
  BEFORE the destructive call and surface every (group, ConsumeLag) pair in the
  user-facing prompt. A trace that captures the enumeration but a prompt that does
  not surface it is still a violation — rubric §4 rule 2, traced by Critic in §2.
- ❌ **DeleteInstance without (topics × groups × lag) matrix** — same family as above
  but at instance scope. Rubric §4 rule 1. A user deleting a "dev" instance can
  accidentally take out production consumers that subscribed to topics on the instance;
  the cascade is invisible until the next on-call page.
- ❌ **ModifyTopic partition reduction without quorum check** — Kafka cannot shrink
  partitions, so any "reduce" call is silently ignored or accepted with the larger
  count. Worse: increasing partitions with `ReplicaNum > broker count` produces
  under-replicated partitions that the API accepts but the broker cannot serve with
  quorum. Rubric §4 rule 3.
- ❌ **ModifyInstanceAttributes reducing `MsgRetentionTime` without units guard** —
  `MsgRetentionTime` is MINUTES, not milliseconds. A user saying "set retention to 7
  days" with the agent passing `7` thinking milliseconds produces a 7-minute retention
  window — messages are deleted within minutes, not days. The most common silent
  data-loss pattern in CKafka broker config changes.
- ❌ **`CleanUpPolicy` flip without keyed-message confirmation** — switching from
  `delete` to `compact` on a topic with unkeyed messages produces a topic that grows
  unboundedly because nothing is eligible for compaction (compaction expects keyed
  messages). Switching from `compact` to `delete` loses all compaction history.
  Rubric §4 rule 4.
- ❌ **CreateAcl `Host=*` + `Operation=ALL` + `PermissionType=Allow`** — the
  open-cluster-access pattern. Any principal from any host can perform any operation
  on the resource. Rubric §4 rule 5.
- ❌ **DeleteAcl removing the last allow rule** — silent consumer lockout. The user
  may not realize until consumer health checks fail hours later. Rubric §4 rule 5.
- ❌ **In-flight consumer eviction via `DeleteConsumerGroup`** — deleting a consumer
  group with `Members > 0` evicts in-flight consumers mid-commit; their next start
  loses the offset commit in flight. Rubric §3.3 idempotency row 4.
- ❌ **CLI `tccli ckafka` parameter shape confusion** — CKafka params accept JSON
  arrays for `InstanceIds`, `TopicList`, `GroupList`. Passing comma-separated strings
  (e.g. `--InstanceIds "ckafka-aaa,ckafka-bbb"`) is silently rejected with a generic
  `InvalidParameter`; the correct shape is `--InstanceIds '["ckafka-aaa","ckafka-bbb"]'`.
  Rubric §3.4 traceability row 6 + AGENTS.md §14 Reflexion pattern.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 CKafka rollout: Generator + Critic + Orchestrator templates (5 rules, instance-delete cascade, topic-delete offset loss, partition rebalancing, broker-config retention drop, ACL open-access guard, last-allow lockout) |
| 1.1.0 | 2026-06-19 | Tier-A conformance flesh-out: expanded to 7 sections (§1 Generator with full pre-flight emphasizing `DescribeConsumerGroup` enumeration + ConsumeLag display, §2 Critic with CKafka-cascade-enforcement block + credential hygiene, §3 Orchestrator with Reflexion pre-flight + failure_pattern extraction, §4 per-operation variants augmented with unit-mismatch guard + post-call `DescribeACL` verification + async polling variant, §5 anti-patterns extended with CLI parameter shape + CleanUpPolicy flip + in-flight consumer eviction, §6 changelog, §7 see also). Source-of-truth: `qcloud-cos-ops/references/prompt-templates.md` v1.0.0 + `qcloud-clb-ops/references/prompt-templates.md` v1.0.0; only the §4 per-operation table and §5 CKafka-specific anti-patterns are product-specific |
| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |
| 1.2.0 | 2026-06-19 | TE-6: G/C/O → gcl-prompt-backbone |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [AGENTS.md §14 Reflexion Integration](../../AGENTS.md#14-reflexion-integration-lightweight-reflexion) — cross-session failure pattern memory
- [rubric.md](rubric.md) — the rubric instance these templates score against (5 dimensions, 5 CKafka-specific safety rules)
- [SKILL.md](../SKILL.md) — the build-time safety gates and pre-flight tables (Instance Deletion, Topic Deletion, Quality Gate (GCL))
- [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) — sibling templates (Tier A canonical)
- [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) — sibling templates (CLB pilot)
- [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md), [`qcloud-cdb-ops/references/prompt-templates.md`](../cdb-ops/references/prompt-templates.md) — sibling templates (compute and database pilots)
- [`docs/failure-patterns.md`](../../docs/failure-patterns.md) — Reflexion memory; CKafka-specific patterns land here as GCL `failure_pattern` extractions accumulate
