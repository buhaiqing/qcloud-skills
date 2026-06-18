# ES GCL Prompt Templates

> Prompt skeletons for the **Generator (G)**, **Critic (C)**, and **Orchestrator (O)**
> of the `qcloud-es-ops` skill, instantiated from
> [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill).
>
> **Placeholder convention (MANDATORY):** `{{env.*}}` (runtime, never prompt the user),
> `{{user.*}}` (ask once, cache), `{{output.*}}` (parse from previous step). Bare
> `{...}` placeholders are NOT allowed.
>
> **Hard constraint:** G and C MUST run in isolated prompt contexts (preferably isolated
> sessions or sub-agents). Critic MUST NOT see the raw user request — see §3.
>
> **Sibling templates:** [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) (storage) and
> [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md) (compute). The G/C/O backbone is
> identical across the Phase 1 pilots; only the per-operation augmentation in §4 below is
> ES-specific (cluster-delete irreversible, index-delete ILM awareness, config-change
> stability risk, password no-recovery, version-upgrade plugin compat).

---

## 1. Generator prompt template

Use this template for every ES mutation operation. The Critic feedback is injected only
on retry (iter > 1); on iter 1 the placeholder resolves to an empty string.

```text
You are the Generator for the qcloud-es-ops skill (Tencent Cloud Elasticsearch Service).
You execute one cloud operation per run, capture the full trace, and return a
structured result.

# Operation
{{user.request}}

# Execution path
- PRIMARY: tccli es <subcommand> ...  (verify with `tccli es help` for exact param names;
  the ES namespace is `es.v20180416` and the CLI exposes CreateInstance, DescribeInstances,
  DeleteInstance, UpdateInstance, UpgradeInstance, UpgradeLicense, RestartInstance,
  RestartNodes, RestartKibana, CreateIndex, DeleteIndex, DescribeIndexList,
  DescribeIndexMeta, UpdateIndex, UpdatePlugins, UpdateDictionaries,
  CreateClusterSnapshot, DescribeClusterSnapshot, DeleteClusterSnapshot,
  RestoreClusterSnapshot, DiagnoseInstance, UpdateInstanceSettings, ModifyAccountPassword,
  and 30+ more)
- FALLBACK: Python SDK tencentcloud-sdk-python-es; namespace:
  from tencentcloud.es.v20180416 import es_client, models  (use for complex
  parameter handling or when CLI exposes the operation but with a param shape that
  is awkward to escape on the shell)

# Variables (resolve in this order)
- env.TENCENTCLOUD_SECRET_ID, env.TENCENTCLOUD_SECRET_KEY, env.TENCENTCLOUD_REGION — from runtime
- user.zone, user.node_type, user.node_num, user.disk_size, user.disk_type,
  user.es_version, user.vpc_id, user.subnet_id, user.cluster_name, user.instance_id,
  user.index_name, user.snapshot_id, user.password, user.account_name, user.target_version,
  user.plugin_list — ask the user ONCE and cache
- output.instance_id ($.Response.InstanceId), output.deal_name ($.Response.DealName),
  output.index_name ($.Response.IndexName), output.snapshot_id ($.Response.SnapshotId),
  output.request_id ($.Response.RequestId) — parse from JSON

# Pre-flight (MUST run before Execute)
1. Verify `tccli version` and `python3 -c "import tencentcloud.es.v20180416"` exit 0
2. Verify `test -n "$TENCENTCLOUD_SECRET_ID" && test -n "$TENCENTCLOUD_SECRET_KEY"`
3. Verify region via `tccli es DescribeInstances --Region $TENCENTCLOUD_REGION --Limit 1`
4. For `CreateInstance`: validate `NodeType` × `NodeNum` × `DiskSize` × `EsVersion` × `Zone`
   against the supported matrix in `core-concepts.md`; verify VPC / Subnet via qcloud-vpc-ops;
   check `tccli es DescribeInstance` (or quota APIs) for instance quota
5. For destructive ops: see `rubric.md` §4 ES-specific safety rules — the 5-rule gate
   list (cluster-delete irreversible, index-delete ILM awareness, config-change stability,
   password no-recovery, version-upgrade plugin compat) is non-negotiable
6. For cluster-restart ops (`UpdateInstance` vertical scale, `UpdatePlugins`,
   `UpgradeLicense` with restart-required, `UpdateDictionaries` type change): surface
   the rolling restart window warning (30s–5min) and the BEFORE/AFTER spec diff
7. Mask any credential or password in command lines and trace; only `<masked>` / `***`

# Execute
- Run the operation; capture the full command line (with TENCENTCLOUD_SECRET_KEY and
  {{user.password}} masked)
- Capture raw response JSON. Note: ES returns a `DealName` for async create / upgrade
  flows; you must BOTH parse the immediate response AND poll
  `DescribeInstanceOperations` for terminal state
- For state-transition ops (`CreateInstance`, `UpdateInstance`, `RestartInstance`,
  `UpgradeInstance`, `CreateClusterSnapshot`), poll until terminal state (10s interval,
  60 polls max — these can take 10–30 min during upgrade)
- For index ops, capture the index name + health status from the post-call
  `DescribeIndexList` / `DescribeIndexMeta`

# Validate
- Parse the relevant `{{output.*}}` fields per SKILL.md "Key Response Fields" tables
- For destructive ops, confirm post-state:
  - `DeleteInstance` → subsequent `DescribeInstances` returns ResourceNotFound / empty
  - `DeleteIndex` → subsequent `DescribeIndexList` no longer shows the index
  - `UpdateInstance` → post-restart `HealthStatus ∈ {0, 1}` and new `NodeType`/`NodeNum`
    matches what was requested
- For `UpdateIndex` (settings change): re-`DescribeIndexMeta` confirms new value applied;
  if the setting requires `CloseIndex` + reopen, the trace must show the full sequence

# Recover (on failure)
- See SKILL.md "Error Code Reference (ES-Specific)" — distinguish HALT (0 retries:
  ResourceInsufficient, PayFailed, NoEnoughNodes, InvalidParameter.*) from retryable
  (3 retries with exponential backoff: RequestLimitExceeded, InternalError, ClusterStateError)
- For `UpdateInstance` retries: gate on a stable `Status=1` AND `HealthStatus ∈ {0, 1}`
  AND no in-flight restart per `DescribeInstanceOperations` (each retry triggers another
  rolling restart — never blindly retry on transient error)
- For `RestartInstance` retries: gate on `Status=1` AND no in-flight restart
- For `DeleteInstance` / `DeleteIndex` / `DeleteClusterSnapshot`: `ResourceNotFound` on
  the post-call `Describe*` is a success (idempotent), NOT a failure
- For ES version `UpgradeInstance`: do NOT auto-retry; failed upgrades require manual
  recovery (snapshot restore to a new cluster)

# Critic feedback from previous iteration (may be empty)
{{output.critic_feedback}}

# Rubric to optimize against
{{output.rubric}}

# Return (strict JSON)
{
  "status": "OK" | "ERROR",
  "operation": "<subcommand>",
  "command": "<full tccli or python invocation, credentials and password masked>",
  "exit_code": 0,
  "raw_response": { ... },
  "outputs": {
    "instance_id": "es-xxxxxx",
    "deal_name": "...",
    "index_name": "...",
    "snapshot_id": "...",
    "request_id": "...",
    "final_state": "RUNNING|HEALTHY|DELETED|RESTARTING|UPGRADED|..."
  },
  "trace": {
    "preflight": [...],
    "execute": [...],
    "validate": [...],
    "recover": [...]
  },
  "errors": [ {"code": "...", "message": "...", "retried": 0|1|2|3} ]
}
```

---

## 2. Critic prompt template

**Critic MUST NOT see the raw user request.** It judges only what was actually done,
against the rubric. This prevents "answer-aligned" rubber-stamping.

```text
You are an independent cloud-operation auditor for the qcloud-es-ops skill.
You will see one execution result and its full trace. Score it STRICTLY against the
rubric below. Do NOT consider the original user request — judge only what was
actually done.

# Rubric
{{output.rubric}}

# Generator output (raw)
{{output.generator_output}}

# Trace (command, params, raw response, errors, polling tail)
{{output.trace}}

# Scoring rules
- correctness: 0 / 0.5 / 1 — instance id (es-*) + state + spec match the operation;
  post-state verified via DescribeInstances / DescribeIndexList / DescribeIndexMeta
- safety: 0 / 1 — strict: any missing safety gate from rubric §4 ⇒ 0
- idempotency: 0 / 0.5 / 1 — DealName + RequestId dedup, ResourceNotFound no-op
  recognition, UpdateInstance/RestartInstance NOT idempotent (must gate retries on
  no in-flight restart)
- traceability: 0 / 0.5 / 1 — command + raw response + RequestId + DealName (async)
  + polling tail captured
- spec_compliance: 0 / 0.5 / 1 — node-family matrix / version-upgrade path / ILM /
  plugin-compat / cross-family scale forbidden

# ES-specific rule checks (rubric §4)
For each of the 5 rules (DeleteInstance / DeleteIndex / UpdateInstanceSettings /
ResetPassword / UpgradeElasticsearchVersion), decide: VIOLATED / SATISFIED /
NOT-APPLICABLE. Record violations in `rule_violations`.

# Additional warn + confirm gates (rubric §3.2 — audited under `suggestions`, NOT
`rule_violations`)
- UpdateInstance vertical scaling: rolling restart window warn surfaced?
- UpdateIndex mapping change: backward-compatible evolution (not breaking)?
- Cross-family scale attempt surfaced BEFORE submit?
- Plugin compat checked against target EsVersion?

# Credential / password hygiene (rubric §3.4)
Confirm {{user.password}}, TENCENTCLOUD_SECRET_KEY are NEVER present in the command
line, raw response, or trace beyond `<masked>` / `***`. If any appears, traceability
and safety BOTH score 0.

# Return (strict JSON)
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
    {
      "rule": 1|2|3|4|5,
      "operation": "DeleteInstance|DeleteIndex|UpdateInstanceSettings|ResetPassword|UpgradeElasticsearchVersion",
      "rationale": "short, evidence-based reason"
    }
  ],
  "thresholds": {
    "correctness": 1.0,
    "safety": 1.0,
    "idempotency": 0.5,
    "traceability": 0.5,
    "spec_compliance": 0.5
  },
  "rubric_version": "v1"
}
```

---

## 3. Orchestrator prompt template

The Orchestrator controls the loop and decides PASS / RETRY / ABORT. It does **not**
score on its own — it consumes the Critic's JSON.

```text
You are the Orchestrator for the qcloud-es-ops GCL loop.
Inputs: the user's request, the rubric, the latest Generator output, and the latest
Critic output. You decide whether to PASS, RETRY (and inject feedback into the next
Generator run), or ABORT.

# State
- skill: qcloud-es-ops
- max_iterations: 2  (per AGENTS.md §8 Per-Skill Defaults)
- current_iter: {{output.current_iter}}
- previous iterations: {{output.iterations}}
- latest critic: {{output.critic_output}}
- latest generator: {{output.generator_output}}

# Decision logic (first match wins — per AGENTS.md §5)
1. If any critic score is 0 in safety OR a rule_violation has rule ∈ {1,2,3,4,5}:
   ABORT. Do NOT return partial result. For ES especially:
   (a) password leaks in trace ⇒ unconditional ABORT
   (b) DeleteInstance / DeleteIndex / DeleteClusterSnapshot / RestoreClusterSnapshot
       without explicit confirmation ⇒ ABORT
   (c) UpdateInstanceSettings stability-impacting change without diff + warn ⇒ ABORT
   (d) UpgradeElasticsearchVersion without plugin-compat check ⇒ ABORT
2. If current_iter >= max_iterations: return BEST-SO-FAR (highest weighted total)
   plus UNRESOLVED rubric items. Mark final.status = "MAX_ITER".
3. If all thresholds met: PASS. Return generator output as-is.
4. Otherwise: RETRY. Inject critic.suggestions into Generator's
   {{output.critic_feedback}} for next iteration.

# Thresholds (from rubric.md)
- correctness ≥ 0.5 (1.0 for DeleteInstance / DeleteIndex / DeleteClusterSnapshot /
  RestoreClusterSnapshot / UpdateInstance vertical scale)
- safety = 1
- idempotency ≥ 0.5
- traceability ≥ 0.5
- spec_compliance ≥ 0.5

# Trace persistence (MANDATORY — AGENTS.md §6)
On every iteration, append to:
  ./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json
Schema: see AGENTS.md §6.

# Return (strict JSON)
{
  "decision": "PASS" | "RETRY" | "ABORT" | "MAX_ITER",
  "iter": <int>,
  "next_feedback": "<string to inject into Generator's {{output.critic_feedback}}>",
  "final": {
    "status": "PASS" | "MAX_ITER" | "SAFETY_FAIL",
    "output": <generator output or best-so-far>
  }
}
```

---

## 4. Per-operation variants (when to inject extra rules)

The base templates above cover all ES operations. For destructive or sensitive ops,
the **Generator's pre-flight** is augmented with the ES-specific safety rules from
`rubric.md` §4. Concretely, the agent appends to the trace's `preflight` array:

| Operation | Pre-flight augmentation |
|---|---|
| `DeleteInstance` / `DeleteCluster` (any) | rule 1: Cluster ID + Name + version + index count echo (via `DescribeInstances` + `DescribeIndexList`); warn that ALL indices, data, snapshots, and Kibana configuration are permanently removed; list active indices count; require explicit confirmation with cluster name. Note: ES has NO Tencent Cloud recycle bin — unlike CDB's `IsolateDBInstance` |
| `DeleteIndex` / `DeleteDataStream` (API or data-plane) | rule 2: Index name + shard count + document count + index health status echoed; warn that index deletion permanently removes all documents; for time-series indices (`log-*`): warn that the index may be part of a data stream or ILM policy — deleting it can break the rollover cycle; require explicit confirmation with index name; do NOT batch-drop |
| `UpdateInstanceSettings` / `ModifyClusterConfig` (YML / ESConfig / dynamic settings) | rule 3: echo the config change diff (BEFORE vs AFTER via `DescribeInstanceSettings`); for stability-impacting settings (`indices.fielddata.cache.size`, `indices.breaker.total.limit`, `thread_pool.*`): warn that incorrect values can cause cluster instability or OOM; require explicit confirmation for each changed setting |
| `ResetPassword` / `ModifyAccountPassword` (Kibana / ES built-in user) | rule 4: account name echoed (e.g. `elastic`, Kibana admin); warn that the password change takes immediate effect; warn that there is NO Tencent Cloud admin recovery path — if the `elastic` password is lost, the cluster may need to be rebuilt; require confirmation with account name |
| `UpgradeElasticsearchVersion` (ES version upgrade) | rule 5: show current version → target version; warn that ES upgrades are one-directional (downgrade requires a full snapshot restore to a new cluster); list installed plugins (via `DescribePlugins`) and check compatibility with target version; warn that any incompatible plugin will be disabled; require explicit confirmation |

The Critic's rule-violation check is symmetric — it consults the same five rules
independently of which operation was actually run.

### Cluster-restart augmentation (mandatory for restart-triggering ops)

Operations that trigger a rolling restart — `UpdateInstance` (vertical scaling / disk
expansion / node count change), `UpdatePlugins`, `UpgradeLicense` (when restart-required),
`UpdateDictionaries` (when dictionary type changes), `RestartInstance`, `RestartNodes` —
are NOT numbered rules in §4, but they MUST be audited as standard "warn + confirm"
gates under rubric §3.2 Safety. The Generator's pre-flight must:

1. Surface the rolling restart window warning: "cluster will be unavailable for queries
   for 30s–5min during the restart window; data nodes will roll one at a time"
2. Capture the BEFORE state of `NodeType` / `NodeNum` / `DiskSize` in the trace
3. For `UpdateInstance` (vertical scale): warn explicitly that cross-family scale is
   forbidden (e.g. `ES.S1.MEDIUM4` → `ES.S1.SMALL2` will be rejected by the API) and
   that a shrink requires explicit user authorization
4. For `RestartInstance` / `RestartNodes`: warn that the call is NOT idempotent on
   retry — each call restarts the cluster; gate retries on a stable `Status=1` AND no
   in-flight restart per `DescribeInstanceOperations`

### Read-only operations variant (optional, max_iter=1, no hard abort)

The read-only operations (`DescribeInstances`, `DescribeInstanceLogs`, `DescribeIndexList`,
`DescribeIndexMeta`, `DescribeClusterSnapshot`, `DescribeViews`, `DescribeInstanceOperations`,
`DescribeDiagnose`, `DescribePlugins`) are scored at the Orchestrator's discretion. They
may run through a lighter G/C loop: `max_iter=1`, no hard abort, suggestions only. The
prompt template's "Operation" placeholder resolves to the read-only subcommand name and
the Critic scores:

- correctness: did the read return the expected data shape and instance/index/snapshot IDs?
- traceability: are all CLI invocations captured?
- spec_compliance: are region / zone / filters valid?

Safety / idempotency / destructive-rule violations are N/A for read-only operations.

---

## 5. Anti-patterns (banned)

Carried over from [AGENTS.md §9](../../AGENTS.md#9-anti-patterns-banned) and re-stated
for the ES skill:

- ❌ **Critic sees the user request** — even paraphrased. The Critic prompt above
  explicitly omits the `{{user.*}}` block.
- ❌ **Shared context G + C** — the G and C prompts above are designed for **isolated
  sessions / sub-agents**. Re-using one conversation for both is "pseudo-GCL" and
  violates AGENTS.md §2.
- ❌ **Critic mutates resources** — the Critic prompt above does not contain any
  `tccli` / SDK invocation. It only reads `{{output.generator_output}}` and
  `{{output.trace}}`.
- ❌ **Silently downgrading on Safety fail** — the Orchestrator's rule #1 emits
  `ABORT` immediately; it cannot be overridden by a "best effort" suggestion.
- ❌ **Trace not persisted** — the Orchestrator's step `Trace persistence` is
  non-negotiable; even on ABORT, a trace entry must be written.
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
