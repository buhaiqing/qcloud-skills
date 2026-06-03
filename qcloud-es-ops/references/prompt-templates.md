# ES GCL Prompt Templates

> Prompt skeletons for G/C/O of `qcloud-es-ops`.
> See [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) for the full backbone.

---

## 1. Generator — ES delta

```text
You are the Generator for the qcloud-es-ops skill (Tencent Cloud Elasticsearch).
- PRIMARY: tccli es <subcommand> ...  (verify with `tccli es help`)
- FALLBACK: Python SDK tencentcloud-sdk-python-es; namespace:
  from tencentcloud.es.v20180416 import es_client, models
```

---

## 4. Per-operation variants

| Operation | Pre-flight augmentation |
|---|---|
| `DeleteInstance` / `DeleteCluster` | rule 1: Cluster ID + Name + version + index count echo; warn irreversible; confirm |
| `DeleteIndex` / `DeleteDataStream` | rule 2: Index name + docs count + health echo; warn ILM policy awareness; no batch-drop |
| `UpdateInstanceSettings` / `ModifyClusterConfig` | rule 3: Config diff (BEFORE vs AFTER); warn stability-impacting settings; confirm each |
| `ResetPassword` / `ModifyAccountPassword` | rule 4: Account echo; warn immediate effect; no-recovery for `elastic`; confirm |
| `UpgradeElasticsearchVersion` | rule 5: Show current → target version; warn one-directional; list plugins + check compat; confirm |

---

## 5. ES-specific anti-patterns

- ❌ **DeleteInstance without index count** — user may not know how many indices exist
- ❌ **DeleteIndex on ILM-managed index** — breaks rollover policy
- ❌ **UpdateInstanceSettings without stability check** — OOM / indexing rejection
- ❌ **UpgradeElasticsearchVersion without plugin compat check** — incompatible plugins disabled
- ❌ **ResetPassword without ingestion pipeline warning** — Beats/Logstash connection loss

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 ES rollout: templates (5 rules, ILM-aware index deletion, config-change stability, version-upgrade plugin compat) |