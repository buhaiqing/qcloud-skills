# CLI Usage — CDN

## Command Reference

| Operation | tccli Command | Notes |
|-----------|--------------|-------|
| Add domain | `tccli cdn AddCdnDomain --Domain <name> --ServiceType web --OriginType cos --Origin '["<cos-endpoint>"]'` | ServiceType: web/download/media |
| Delete domain | `tccli cdn DeleteCdnDomain --Domain <name>` | Verify no traffic first |
| Update config | `tccli cdn UpdateDomainConfig --Domain <name> --Https '<json>'` | Partial config update |
| Describe domains | `tccli cdn DescribeDomainsConfig --Offset 0 --Limit 20` | Paginated |
| Start domain | `tccli cdn StartCdnDomain --Domain <name>` | Activates CDN serving |
| Stop domain | `tccli cdn StopCdnDomain --Domain <name>` | Stops CDN serving |
| Purge URLs | `tccli cdn PurgeUrlsCache --Urls '["https://domain/path"]'` | Max 100 URLs/call |
| Purge path | `tccli cdn PurgePathCache --Paths '["https://domain/path/"]'` | Directory-level purge |
| Push URLs | `tccli cdn PushUrlsCache --Urls '["https://domain/path"]'` | Pre-warm cache |
| Traffic data | `tccli cdn DescribeCdnData --StartTime "2026-05-21 00:00:00" --EndTime "2026-05-21 23:59:59" --MetricType flux` | Returns traffic/bandwidth |
| Top data | `tccli cdn ListTopData --StartTime "..." --EndTime "..." --MetricType flux --DetailField domain` | Top domains by traffic |
| Domain logs | `tccli cdn DescribeCdnDomainLogs --Domain <name> --StartTime "..." --EndTime "..."` | Returns log download URLs |

## Coverage Gap Table

| Operation | CLI Support | SDK Needed? |
|-----------|-------------|-------------|
| Domain lifecycle | Full support | No |
| Cache purge/pre-warm | Full support | No |
| Traffic monitoring | Full support | No |
| Log download | Returns URLs | No |
| Complex config update | Partial | Yes (for nested config JSON) |
| Batch domains | Manual loop | Yes (for automation) |
| HTTPS certificate upload | Via CAM | Yes (CAM integration) |
