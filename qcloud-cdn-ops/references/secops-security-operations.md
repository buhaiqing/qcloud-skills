# CDN SecOps - Security Operations

## Anti-Hotlinking

| Method | Configuration | Effectiveness |
|--------|--------------|--------------|
| Referer allowlist | Domain whitelist | Blocks direct linking from unauthorized sites |
| Referer blocklist | Domain blacklist | Blocks specific hotlinking sites |
| URL signing | Token + expiry | Time-limited access, prevents URL sharing |
| Timestamp anti-leech | URL + timestamp parameter | Prevents stale URL reuse |

## Access Control

| Control | Configuration | Use Case |
|---------|--------------|----------|
| IP blacklist | Block specific CIDRs | Block known attackers |
| IP whitelist | Allow only specific CIDRs | Internal CDN access only |
| Bandwidth limit | Cap per domain | Prevent abuse/DDoS cost |
| QPS limit | Cap requests per second | Prevent request flooding |

## Origin Protection

| Risk | Mitigation |
|------|-----------|
| Origin IP exposed | Use CLB/COS as origin, not direct CVM IP |
| Origin DDoS | Enable CDN anti-DDoS, rate limiting |
| Origin data leak | Restrict origin access to CDN edge IPs only |
| Content tampering | Enable URL signing for sensitive content |

## HTTPS Security

| Check | Configuration |
|-------|--------------|
| TLS version | TLS 1.2 minimum, TLS 1.3 preferred |
| Cipher suites | Strong ciphers only (no RC4, DES, MD5) |
| Certificate chain | Complete chain including intermediate |
| HSTS | max-age ≥ 31536000, includeSubDomains |

## WAF Integration

| Integration | Purpose |
|-------------|---------|
| CDN + WAF | WAF inspects traffic before CDN edge |
| WAF rules | SQL injection, XSS, bot detection |
| Rate limiting | Per-IP request rate caps |
| Bot management | Block malicious bots, allow search engines |
