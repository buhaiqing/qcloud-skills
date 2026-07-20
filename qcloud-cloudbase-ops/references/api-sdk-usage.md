# CloudBase API & SDK Usage

## Module

```python
from tencentcloud.tcb.v20180608 import tcb_client, models
```

## Operation Map

### Environment Lifecycle

| Operation | SDK Method | CLI Command | Notes |
|-----------|-----------|-------------|-------|
| CreateEnv | `CreateEnv()` | `tccli tcb CreateEnv` | Returns EnvId; async — poll until Status=0 |
| DescribeEnvInfo | `DescribeEnvInfo()` | `tccli tcb DescribeEnvInfo` | Lists all envs or filter by EnvIds |
| ModifyEnv | `ModifyEnv()` | `tccli tcb ModifyEnv` | Update env name or config |
| DeleteEnv | `DeleteEnv()` | `tccli tcb DeleteEnv` | Deletes ALL resources; irreversible |
| CheckTcbService | `CheckTcbService()` | `tccli tcb CheckTcbService` | Verify service is enabled |

### Database ACL

| Operation | SDK Method | CLI Command | Notes |
|-----------|-----------|-------------|-------|
| DescribeDatabaseACL | `DescribeDatabaseACL()` | `tccli tcb DescribeDatabaseACL` | Get collection permissions |
| CreateDatabaseACL | `CreateDatabaseACL()` | `tccli tcb CreateDatabaseACL` | Set collection permissions |

### Auth Domains

| Operation | SDK Method | CLI Command | Notes |
|-----------|-----------|-------------|-------|
| DescribeAuthDomains | `DescribeAuthDomains()` | `tccli tcb DescribeAuthDomains` | List whitelisted domains |
| CreateAuthDomain | `CreateAuthDomain()` | `tccli tcb CreateAuthDomain` | Add domain to whitelist |
| DeleteAuthDomain | `DeleteAuthDomain()` | `tccli tcb DeleteAuthDomain` | Remove domain from whitelist |

### API Keys

| Operation | SDK Method | CLI Command | Notes |
|-----------|-----------|-------------|-------|
| DescribeApiKeyLists | `DescribeApiKeyLists()` | `tccli tcb DescribeApiKeyLists` | SecretKey is masked |
| CreateApiKey | `CreateApiKey()` | `tccli tcb CreateApiKey` | **SecretKey shown ONCE** |
| DeleteApiKey | `DeleteApiKey()` | `tccli tcb DeleteApiKey` | Revoke immediately |

### Billing & Metrics

| Operation | SDK Method | CLI Command | Notes |
|-----------|-----------|-------------|-------|
| DescribeBillingInfo | `DescribeBillingInfo()` | `tccli tcb DescribeBillingInfo` | Env billing + usage summary |
| DescribeCurveData | `DescribeCurveData()` | `tccli tcb DescribeCurveData` | Time-series metrics |
| DescribeDatabaseACL | `DescribeDatabaseACL()` | `tccli tcb DescribeDatabaseACL` | DB usage metrics |

### Static Hosting & Build

| Operation | SDK Method | CLI Command | Notes |
|-----------|-----------|-------------|-------|
| CreateHostingDomain | `CreateHostingDomain()` | `tccli tcb CreateHostingDomain` | Bind custom domain |
| DescribeCloudBaseBuildService | `DescribeCloudBaseBuildService()` | `tccli tcb DescribeCloudBaseBuildService` | Build job status |

### Other Operations

| Operation | SDK Method | CLI Command | Notes |
|-----------|-----------|-------------|-------|
| CreateMySQL | `CreateMySQL()` | `tccli tcb CreateMySQL` | Create MySQL database |
| CreateStaticStore | `CreateStaticStore()` | `tccli tcb CreateStaticStore` | Create static storage |
| CreateTable | `CreateTable()` | `tccli tcb CreateTable` | Create doc database table |
| DescribeBaasPackageList | `DescribeBaasPackageList()` | `tccli tcb DescribeBaasPackageList` | BaaS package info |
| DescribeCloudBaseRunServerVersion | `DescribeCloudBaseRunServerVersion()` | `tccli tcb DescribeCloudBaseRunServerVersion` | CloudBase Run version |

## Required Fields per Operation

### CreateEnv

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `EnvName` | Yes | string | Environment name (2-50 chars) |
| `Channel` | No | string | Source channel (default: `cloudbase`) |
| `BillingType` | No | integer | Billing type (0=体验版, 1=正式版) |
| `VpcInfo` | No | object | VPC configuration |
| `PackageType` | No | string | Package type (env-basic, env-pro, etc.) |

### DescribeEnvInfo

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `EnvIds` | No | array | Filter by EnvId list; omit for all |

### DescribeCurveData

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `EnvId` | Yes | string | Environment ID |
| `MetricName` | Yes | string | Metric name (see core-concepts.md) |
| `StartTime` | Yes | string | Start time (YYYY-MM-DD or ISO 8601) |
| `EndTime` | Yes | string | End time (YYYY-MM-DD or ISO 8601) |
| `Granularity` | No | integer | Aggregation interval in seconds (60, 300, 3600, 86400) |

### CreateDatabaseACL

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `EnvId` | Yes | string | Environment ID |
| `CollectionName` | Yes | string | Collection name |
| `Acl` | Yes | string (JSON) | ACL JSON string (e.g., `{"readOnly": false}`) |

### CreateAuthDomain

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `EnvId` | Yes | string | Environment ID |
| `Domain` | Yes | string | Domain name to whitelist |
| `Type` | Yes | string | Type: `web` or `qiniu` |

### DeleteApiKey

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `ApiKeyId` | Yes | string | API key ID to revoke |

## SDK Code Examples

### Create Environment (SDK)

```python
from tencentcloud.tcb.v20180608 import tcb_client, models

req = models.CreateEnvRequest()
req.EnvName = "my-app-env"
req.Channel = "cloudbase"
resp = client.CreateEnv(req)
env_id = resp.Response.EnvId  # env-xxxxx
```

### Describe Environment (SDK)

```python
req = models.DescribeEnvInfoRequest()
req.EnvIds = ["env-xxxxx"]
resp = client.DescribeEnvInfo(req)
for env in resp.Response.EnvList:
    print(f"{env.EnvName}: {env.Status}")
```

### DescribeCurveData (SDK)

```python
req = models.DescribeCurveDataRequest()
req.EnvId = "env-xxxxx"
req.MetricName = "FunctionCallCount"
req.StartTime = "2026-07-01"
req.EndTime = "2026-07-20"
req.Granularity = 86400
resp = client.DescribeCurveData(req)
for point in resp.Response.CurveData:
    print(point)
```

## Pagination

List operations return all results in one call (no pagination needed for most env-level queries). For very large result sets, use `Offset` and `Limit` parameters where supported.

## Error Handling

```python
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

try:
    resp = client.DescribeEnvInfo(req)
except TencentCloudSDKException as e:
    print(f"[ERROR] {e.code}: {e.message}")
    # Log RequestId from e for escalation
```
