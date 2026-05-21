# CDN Core Concepts

## Architecture

```
Client → CDN Edge Node → Origin Server (CVM/COS/CLB)
    ↓           ↓              ↓
  DNS CNAME  Cache hit/miss   Pull/Push
```

### Key Components

| Component | Description |
|-----------|-------------|
| Edge Node | CDN cache server closest to user |
| Origin Server | Source of content (COS bucket, CVM, CLB) |
| CNAME | DNS record pointing to CDN edge domain |
| Cache Layer | Stores copies of content at edge nodes |

## Cache Refresh vs Purge vs Pre-warm

| Operation | Effect | Latency | Use Case |
|-----------|--------|---------|----------|
| `PurgeUrlsCache` | Delete specific cached URLs | Immediate | Update specific assets (JS/CSS/images) |
| `PurgePathCache` | Delete all cached files under path | Immediate | Update entire directory |
| `PushUrlsCache` | Pre-warm cache from origin | 1-5 min | Proactive cache warming before traffic spike |

## Domain Lifecycle

```
Add Domain → DNS Verification → CNAME Config → Deploy → Online → (Start/Stop) → Delete
```

| Status | Description |
|--------|-------------|
| Deploying | Configuration being applied to edge nodes |
| Online | CDN is serving traffic |
| Offline | CDN stopped serving traffic (can be restarted) |
| Auditing | Domain under review (compliance check) |

## HTTPS Configuration

| Feature | Description |
|---------|-------------|
| HTTPS Switch | Enable/disable HTTPS on CDN edge |
| HTTP/2 | Enable HTTP/2 protocol for better performance |
| HSTS | Force browsers to always use HTTPS |
| ForceRedirect | Redirect HTTP requests to HTTPS |
| Certificate | Upload to CAM, reference by CertId |

## Origin Types

| Type | Configuration | Use Case |
|------|--------------|----------|
| COS Bucket | `bucket.cos.region.myqcloud.com` | Static assets, large files |
| CVM IP/Domain | CVM private IP or domain | Dynamic content, API |
| CLB Address | CLB VIP | High-availability origin |
| Third-party | External hostname | Multi-origin scenarios |

## Access Control Methods

| Method | Purpose | Configuration |
|--------|---------|--------------|
| Referer allowlist/blocklist | Prevent hotlinking | Domain-based filtering |
| IP blacklist/whitelist | Block/allow specific IPs | CIDR-based filtering |
| URL signing | Time-limited access | Token with expiry |
| Timestamp anti-leech | Prevent URL sharing | URL with timestamp parameter |
| Bandwidth limit | Cap traffic per domain | QPS/bandwidth caps |
