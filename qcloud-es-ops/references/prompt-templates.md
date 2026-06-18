# ES GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-es-ops` |
| CLI | `tccli es help` |
| max_iterations | 2 |


Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (ES).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **2**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (ES — 5 rules). Do not duplicate gate text here.

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


- ❌ **Logging the ES `elastic` / Kibana admin password** — extending the AGENTS.md list
  with the ES-specific ban on letting `{{user.password}}` appear unmasked anywhere in
  command, response, or trace. The `elastic` superuser password has no Tencent Cloud
  recovery path; a leaked password that is then rotated without updating the
  Beats / Logstash configuration can silently halt data ingestion for hours.
- ❌ **`DeleteInstance` without snapshot** — ES-specific: unlike CDB's recycle bin,
  ES cluster deletion is **immediate and irreversible**. The single most common ES
  incident is "I deleted the dev cluster but production monitoring was still indexing
  to it". The Generator must surface index count + active data streams BEFORE delete.
- ❌ **`DeleteIndex` on an ILM-managed index** — ES-specific: deleting an index that
  is the rollover alias target of an ILM policy breaks the policy's rollover cycle.
  The Generator must check ILM / data-stream membership via `DescribeIndexMeta`
  (or warn that the data-plane check is required) BEFORE delete.
- ❌ **`UpdateInstance` spec downgrade without cross-family check** — ES-specific:
  the API rejects cross-family scale (`ES.S1.MEDIUM4` → `ES.S1.SMALL2`) but the
  Generator must surface the cross-family restriction BEFORE submit, not after a
  failed `InvalidParameter` response. A silent acceptance on a cross-family scale
  (which the API does NOT do) would leave the cluster in a restart loop.
- ❌ **`UpgradeElasticsearchVersion` without plugin-compat check** — ES-specific:
  incompatible plugins are silently disabled on upgrade. The Generator must list
  installed plugins via `DescribePlugins` and check the compat matrix against the
  target version BEFORE submit.
- ❌ **`UpdateInstanceSettings` stability-impacting change without diff** — ES-specific:
  cluster config changes are the #1 cause of unplanned cluster restarts. A single wrong
  `indices.breaker.total.limit` value can cause the cluster to reject all indexing. The
  Generator must surface the BEFORE/AFTER diff and warn per setting.
- ❌ **`ResetPassword` without ingestion-pipeline warning** — ES-specific: rotating
  the `elastic` password via the API does not update Beats / Logstash / Kibana
  saved-credentials. The Generator must surface the affected pipelines (Logstash output
  blocks, Beats credentials, Kibana data-source credentials) BEFORE submit.
- ❌ **Treating data-plane DELETE as API DELETE** — ES-specific: the user may ask
  "delete the index `log-2024.01`" and the agent may route to a data-plane curl
  (`DELETE /log-2024.01` via the ES HTTP API) instead of `tccli es DeleteIndex`. The
  GCL pilot covers the Tencent Cloud ES API surface; data-plane calls are a separate
  skill boundary. If the user requests a data-plane mutation, the agent should HALT
  and explain the boundary.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 ES rollout: minimal templates (5 rules, ILM-aware index deletion, config-change stability, version-upgrade plugin compat). Backbone was a thin ES delta referencing `qcloud-clb-ops/references/prompt-templates.md` |
| 1.1.0 | 2026-06-19 | Tier A conformance flesh-out: §1 Generator prompt with full ES pre-flight (NodeType × DiskSize × EsVersion matrix, cluster-restart augmentations, async DealName polling, no-recycle-bin DeleteInstance), §2 Critic prompt with explicit "Critic MUST NOT see the raw user request" + 5-dimension scoring + ES rule_violations, §3 Orchestrator prompt with decision flow + trace persistence, §4 Per-operation variants with cluster-restart augmentation section + read-only variant, §5 Anti-patterns (10 ES-specific banned patterns: DeleteInstance without snapshot, DeleteIndex on ILM-managed index, UpdateInstance cross-family scale, UpgradeInstance without plugin-compat, UpdateInstanceSettings stability-impacting change, ResetPassword ingestion-pipeline, data-plane boundary), §7 See also. Cross-references `rubric.md` §4 (5 rules) and `AGENTS.md` §7/§8/§9 |
| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |
| 1.2.0 | 2026-06-19 | TE-6: G/C/O → gcl-prompt-backbone |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [AGENTS.md §9](../../AGENTS.md#9-anti-patterns-banned) — anti-patterns the §5 list extends
- [rubric.md](rubric.md) — the rubric instance these templates score against (5 dimensions, 5 ES-specific safety rules)
- [SKILL.md](../SKILL.md) — the build-time safety gates and pre-flight tables
- [SKILL.md §Quality Gate (GCL)](../SKILL.md#quality-gate-gcl) — SKILL.md's Quality Gate chapter that references these templates
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations) — destructive-op gates the rubric §4 mirrors
- [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) — sibling templates (storage pilot)
- [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md) — sibling templates (compute pilot)
- [`qcloud-cdb-ops/references/rubric.md`](../cdb-ops/references/rubric.md) — sibling rubric (database pilot) for cross-skill pattern reference
