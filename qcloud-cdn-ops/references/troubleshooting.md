# CDN Troubleshooting

## Error Code Diagnostics

| Error Code | Meaning | Diagnostic Steps | Recovery |
|---|---|---|---|
| `ResourceNotFound.CdnDomain` | Domain not found in CDN | 1. `DescribeDomainsConfig --Domain <name>`<br>2. Check domain spelling | Domain not added — use `AddCdnDomain` |
| `InvalidParameter.DomainExists` | Domain already configured | 1. `DescribeDomainsConfig --Domain <name>`<br>2. Review current config | Use `UpdateDomainConfig` instead of `AddCdnDomain` |
| `OperationDenied.DomainStatus` | Domain not in correct status | 1. Check domain status (deploying/online/offline)<br>2. Domain must be online for config changes | Start domain via `StartCdnDomain` if offline |
| `LimitExceeded.PurgeUrlsRateLimit` | Purge rate limit exceeded | 1. Check current purge count<br>2. Default: 100 URLs/minute | Wait and retry, or use path-level purge |
| `FailedOperation.OriginConnectFailed` | Origin connection failed | 1. Test origin reachability<br>2. Check origin IP/firewall<br>3. Verify origin port | Fix origin server network, update origin config |
| `AuthFailure.Unauthorized` | Caller lacks CDN permissions | 1. Check attached policies<br>2. Verify `QcloudCDNFullAccess` | Attach CDN permissions via CAM |
| `LimitExceeded.CdnDomainQuota` | Max CDN domains reached | 1. Count current domains<br>2. Default: 50 per account | Request quota increase via ticket |
| `InvalidParameter.UrlFormat` | Invalid URL in purge/pre-warm | 1. Verify URL scheme (https://)<br>2. Check URL encoding | Fix URL format, use full URL with scheme |
| `FailedOperation.CertVerifyFailed` | Certificate verification failed | 1. Check cert domain matches CDN domain<br>2. Verify cert not expired | Upload correct certificate for domain |
| `OperationDenied.DomainInDeploy` | Domain being deployed | 1. Check deployment status<br>2. Wait for completion | Wait 1-5 minutes, then retry |
| `FailedOperation.DomainBandWidthLimit` | Bandwidth limit exceeded | 1. Check current bandwidth usage<br>2. Compare to configured limit | Increase bandwidth limit or optimize traffic |
| `ResourceNotFound.CertInfo` | Certificate not found | 1. `DescribeCertDetails --CertId <id>`<br>2. Check if cert expired | Upload new certificate or use valid CertId |

## Common Diagnostic Patterns

### Cache Not Refreshing
1. Verify purge task status via FlushId
2. Check if origin Cache-Control headers override CDN cache
3. Verify CDN cache rules configured correctly
4. Test with `curl -I https://<domain>/<path>` — check X-Cache-Lookup header

### Origin Connection Failures
1. Ping origin from edge node perspective
2. Check origin server security group (allow CDN edge IPs)
3. Verify origin port matches CDN config
4. Test origin health: `curl -I http://<origin>`

### HTTPS Not Working
1. Verify certificate domain matches CDN domain (SAN/wildcard)
2. Check certificate expiry date
3. Verify ForceRedirect configuration
4. Test: `curl -vkI https://<domain>`
