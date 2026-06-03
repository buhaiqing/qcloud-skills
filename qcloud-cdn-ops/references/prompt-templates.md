# CDN GCL Prompt Templates

> Prompt skeletons for G/C/O of `qcloud-cdn-ops`.
> See [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) for the backbone.

---

## 1. Generator — CDN delta

```text
You are the Generator for the qcloud-cdn-ops skill (Tencent Cloud CDN).
- PRIMARY: tccli cdn <subcommand> ...  (verify with `tccli cdn help`)
- FALLBACK: Python SDK tencentcloud-sdk-python-cdn; namespace:
  from tencentcloud.cdn.v20180606 import cdn_client, models
```

---

## 4. Per-operation variants

| Operation | Pre-flight augmentation |
|---|---|
| `DeleteCdnDomain` | rule 1: Domain + CNAME echo; warn CDN stop; list origin config; literal confirm |
| `PurgeUrlsCache` with `/*` | rule 2: Warn `/*` clears ALL cached content; surface cache hit ratio; recurse-confirm |
| `PurgePathCache` | rule 3: Path echo; warn broad impact; require confirmation; root path → recurse-confirm |
| `UpdateDomainConfig` | rule 4: BEFORE/AFTER diff; warn origin/SSL mismatch risk; confirm per field |
| `PushUrlsCache` (preload) | rule 5: URL list + preload size echo; warn large preload origin cost; confirm |

---

## 5. CDN-specific anti-patterns

- ❌ **DeleteCdnDomain without DNS CNAME check** — site inaccessible via CDN
- ❌ **PurgeUrlsCache `/*` without cache-hit-ratio context** — users don't realize the impact
- ❌ **UpdateDomainConfig origin without content parity** — 404 surge
- ❌ **PushUrlsCache large preload without cost warning** — origin bill shock

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 CDN rollout: templates (5 rules, domain-delete CNAME break, wildcard purge, origin config change, preload origin cost) |