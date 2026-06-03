# CDN Quality-Gate Rubric (GCL)

> Runtime rubric for **Generator-Critic-Loop (GCL)** of `qcloud-cdn-ops`.
> See [`qcloud-clb-ops/references/rubric.md`](../clb-ops/references/rubric.md) for the backbone.

---

## 4. CDN-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DeleteCdnDomain` (any) | **Domain name + CNAME + traffic/bandwidth estimate echo; warn that deletion deactivates the domain's CDN service — DNS pointing to the CNAME will break; list active origin configurations; require literal "CONFIRM DELETE DOMAIN <name>"** | CDN domain deletion stops service immediately. If DNS still points to the CDN CNAME, all HTTP/S requests fail. The most common incident: "I deleted the staging domain but the production DNS was still using the same CNAME for failover — the entire site was down" |
| 2 | `PurgeUrlsCache` with `/*` wildcard (purge all) | **Domain name + URL pattern echoed; warn that `/*` clears ALL cached content for the domain — every subsequent request will miss the cache and hit the origin; surface current cache hit ratio (from `DescribeCdnData` or `DescribeDomainsConfig`); require recurse-confirm "yes, purge ALL cached content for <domain>"** | A `/*` purge is the most common CDN incident. The user means "purge this file" but types `/*` instead of `/specific-file.js`. The result: all cached data is flushed, origin traffic spikes, and costs increase |
| 3 | `PurgePathCache` (directory-level) | **Domain name + path prefix echoed; warn that purging a directory invalidates ALL files under that path; require confirmation with path; for `/` (root path): require recurse-confirm same as `/*`** | Path cache purge is still broad. Purging `/static/` invalidates all files under static. The most common pattern: "I purged /images/ to update a logo but it also invalidated the thousands of product images under /images/products/" |
| 4 | `UpdateDomainConfig` (any configuration change: origin, SSL cert, cache rules, access control) | **Show BEFORE/AFTER config diff; for origin change: warn that new origin must serve the same content or users will see errors; for SSL cert change: warn that the new cert must match the domain name; for cache rule change (TTL): warn that reducing TTL increases origin load; require confirmation for each changed field** | Config changes are applied asynchronously and can cause transient errors. The most common incident: "I changed the origin from `origin-a.com` to `origin-b.com` but forgot that `origin-b.com` had a different directory structure — users saw 404s for 30 minutes until the cache expired" |
| 5 | `PushUrlsCache` (prefetch / URL preload) | **URL list + estimated preload size echoed; warn that prefetching large files (>1GB total) may incur significant origin bandwidth costs (prefetch bypasses CDN cache — all requests hit the origin); require confirmation for large preloads** | URL prefetching is often more expensive than expected because it bypasses the CDN cache. The most common pattern: "I prefetched the new product images to warm up the cache, but the origin bill was $2000 because the images were all dynamically generated" |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 CDN rollout: rubric (5 rules: domain-deletion CNAME break, wildcard `/*` purge mass flush, path purge broad impact, origin/SSL config change, preload origin cost) |