# CDN API & SDK Usage

## Operation Mapping

| Operation | API Method | Required Params | Response Key |
|-----------|-----------|-----------------|-------------|
| Add domain | `AddCdnDomain` | Domain, ServiceType, OriginType, Origin | Domain |
| Delete domain | `DeleteCdnDomain` | Domain | RequestId |
| Update config | `UpdateDomainConfig` | Domain, Config JSON | RequestId |
| Describe domains | `DescribeDomainsConfig` | Domain (optional), Offset, Limit | Domains, TotalCount |
| Start domain | `StartCdnDomain` | Domain | RequestId |
| Stop domain | `StopCdnDomain` | Domain | RequestId |
| Purge URLs | `PurgeUrlsCache` | Urls (array) | FlushId |
| Purge path | `PurgePathCache` | Paths (array) | FlushId |
| Push URLs (pre-warm) | `PushUrlsCache` | Urls (array) | FlushId |
| Traffic data | `DescribeCdnData` | StartTime, EndTime, MetricType | ChinaData, OverseaData |
| Top data | `ListTopData` | StartTime, EndTime, MetricType, DetailField | TopDataList |
| Domain logs | `DescribeCdnDomainLogs` | Domain, StartTime, EndTime | CdnDomainLogs |
| Domain detail | `DescribeCdnDomainDetailData` | Domain, StartTime, EndTime | DetailData |

## Python SDK Example

```python
from tencentcloud.common import credential
from tencentcloud.cdn.v20180606 import cdn_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = cdn_client.CdnClient(cred, "")

# Add domain
req = models.AddCdnDomainRequest()
req.Domain = "cdn.example.com"
req.ServiceType = "web"
req.OriginType = "cos"
req.Origin = ["your-bucket.cos.ap-guangzhou.myqcloud.com"]
resp = client.AddCdnDomain(req)

# Purge URLs
req = models.PurgeUrlsCacheRequest()
req.Urls = ["https://cdn.example.com/index.html"]
resp = client.PurgeUrlsCache(req)
print(f"FlushId: {resp.FlushId}")
```
