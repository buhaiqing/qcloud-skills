# ES Quality-Gate Rubric (GCL)

> Runtime rubric for **Generator-Critic-Loop (GCL)** of `qcloud-es-ops`.
> See [`qcloud-clb-ops/references/rubric.md`](../clb-ops/references/rubric.md) for the backbone.

---

## 4. ES-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DeleteInstance` / `DeleteCluster` (any) | **Cluster ID + Name + version + index count echo; warn that ALL indices, data, snapshots, and Kibana configuration are permanently removed; list active indices count (via `DescribeInstanceLogs` or ES `_cat/indices`); require explicit confirmation with cluster name** | ES cluster deletion is irreversible. Unlike CDB's recycle bin, there is no temporary grace period. The most common incident: "I deleted the dev cluster but the production monitoring was still indexing to it" |
| 2 | `DeleteIndex` / `DeleteDataStream` (data-plane or API) | **Index name + shard count + document count + index health status echoed; warn that index deletion permanently removes all documents; for time-series indices (log-*): warn that the index may be part of a data stream or ILM policy; require explicit confirmation with index name; do NOT batch-drop** | Index deletion in ES is immediate and irreversible. If the index is part of an ILM policy, deleting it can break the policy's rollover cycle. The most common pattern: user deletes an "old" index but it was the rollover alias for the ILM policy |
| 3 | `UpdateInstanceSettings` / `ModifyClusterConfig` (cluster settings: `YML`, `ESConfig`, or dynamic settings) | **Echo the config change diff (BEFORE vs AFTER); for settings that affect stability (`indices.fielddata.cache.size`, `indices.breaker.total.limit`, `thread_pool.*`): warn that incorrect values can cause cluster instability or OOM; require explicit confirmation for each changed setting** | ES cluster config changes are the #1 cause of unplanned cluster restarts. A single wrong `indices.breaker.total.limit` value can cause the cluster to reject all indexing |
| 4 | `ResetPassword` / `ModifyAccountPassword` (Kibana / ES built-in user) | **Account name echoed; warn that the password change takes immediate effect; for the `elastic` / Kibana admin: warn that there is no Tencent Cloud admin recovery path — if the password is lost, the cluster may need to be rebuilt; require confirmation with account name** | ES `elastic` superuser password has no Tencent Cloud recovery path. The most common incident: "I rotated the elastic password via the API but forgot to update the Beats/Logstash configuration — data ingestion stopped for 12 hours" |
| 5 | `UpgradeElasticsearchVersion` (ES version upgrade) | **Show current version → target version; warn that ES upgrades are one-directional (downgrade requires a full snapshot restore to a new cluster); list installed plugins and check compatibility with target version; warn that any incompatible plugin will be disabled; require explicit confirmation** | ES version upgrades cannot be rolled back. Plugin incompatibility is the most common blocker. The most common incident: "I upgraded from 7.10 to 7.14 but the old IK plugin was incompatible and all Chinese-text search broke" |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 ES rollout: rubric (5 rules: cluster-delete irreversible, index-delete ILM awareness, config-change stability risk, password no-recovery, version-upgrade plugin compat) |