# CloudBase CLI Usage (tccli tcb)

## Overview

`tccli tcb` provides the primary execution path for CloudBase operations. CLI output is JSON by default.

## CLI Conventions

```bash
# Format: tccli tcb <ActionName> --Param1 value1 --Param2 value2
tccli tcb DescribeEnvInfo --Region ap-guangzhou --EnvIds '["env-xxxxx"]'

# Credentials from env vars: TENCENTCLOUD_SECRET_ID, TENCENTCLOUD_SECRET_KEY
# Region specified via --Region (not --RegionId)
# JSON output by default
```

## Verified CLI Operations

| Action | Command Pattern | Notes |
|--------|---------------|-------|
| CheckTcbService | `tccli tcb CheckTcbService --Region {{region}}` | Returns ServiceAvailable |
| CreateEnv | `tccli tcb CreateEnv --Region {{region}} --EnvName "{{name}}"` | Returns EnvId |
| DescribeEnvInfo | `tccli tcb DescribeEnvInfo --Region {{region}}` | Lists all envs |
| ModifyEnv | `tccli tcb ModifyEnv --Region {{region}} --EnvId "{{env_id}}"` | Update env |
| DeleteEnv | `tccli tcb DeleteEnv --Region {{region}} --EnvId "{{env_id}}"` | **Destructive** |
| DescribeDatabaseACL | `tccli tcb DescribeDatabaseACL --Region {{region}} --EnvId "{{env_id}}"` | Get ACL |
| CreateDatabaseACL | `tccli tcb CreateDatabaseACL --Region {{region}} --EnvId "{{env_id}}"` | Set ACL |
| DescribeAuthDomains | `tccli tcb DescribeAuthDomains --Region {{region}} --EnvId "{{env_id}}"` | List domains |
| CreateAuthDomain | `tccli tcb CreateAuthDomain --Region {{region}} --EnvId "{{env_id}}"` | Add domain |
| DeleteAuthDomain | `tccli tcb DeleteAuthDomain --Region {{region}} --EnvId "{{env_id}}"` | Remove domain |
| DescribeApiKeyLists | `tccli tcb DescribeApiKeyLists --Region {{region}}` | List keys (masked) |
| CreateApiKey | `tccli tcb CreateApiKey --Region {{region}}` | Returns SecretKey once |
| DeleteApiKey | `tccli tcb DeleteApiKey --Region {{region}} --ApiKeyId "{{key_id}}"` | Revoke key |
| DescribeBillingInfo | `tccli tcb DescribeBillingInfo --Region {{region}} --EnvId "{{env_id}}"` | Billing info |
| DescribeCurveData | `tccli tcb DescribeCurveData --Region {{region}} --EnvId "{{env_id}}"` | Usage metrics |
| CreateHostingDomain | `tccli tcb CreateHostingDomain --Region {{region}} --EnvId "{{env_id}}"` | Custom domain |
| DescribeCloudBaseBuildService | `tccli tcb DescribeCloudBaseBuildService --Region {{region}} --EnvId "{{env_id}}"` | Build status |

## CLI Installation

```bash
pip install tccli
tccli configure  # Interactive setup
```

## CLI Help

```bash
# Top-level help
tccli tcb help

# Detailed help for an action
tccli tcb CreateEnv --help
```

## JSON Output Parsing

```bash
# Extract EnvId from CreateEnv response
ENV_ID=$(tccli tcb CreateEnv --Region ap-guangzhou --EnvName "my-env" \
  | jq -r '.Response.EnvId')

# Extract all environment IDs
tccli tcb DescribeEnvInfo --Region ap-guangzhou \
  | jq -r '.Response.EnvList[].EnvId'

# Extract environment status
tccli tcb DescribeEnvInfo --Region ap-guangzhou \
  --EnvIds '["env-xxxxx"]' \
  | jq -r '.Response.EnvList[0].Status'

# Extract billing info
tccli tcb DescribeBillingInfo --Region ap-guangzhou --EnvId "env-xxxxx" \
  | jq -r '.Response.BillingInfo'

# Extract curve data
tccli tcb DescribeCurveData --Region ap-guangzhou --EnvId "env-xxxxx" \
  --MetricName "FunctionCallCount" --StartTime "2026-07-01" --EndTime "2026-07-20" \
  | jq -r '.Response.CurveData'
```

## Coverage Gap Table

The following CloudBase operations are **SDK-only** (not exposed by `tccli tcb`):

| Operation | Reason | SDK Method |
|-----------|--------|------------|
| (none identified — CLI covers all major operations) | CLI coverage is comprehensive | — |

## Credential Verification

```bash
# Verify credentials work
tccli tcb CheckTcbService --Region {{env.TENCENTCLOUD_REGION}} \
  | jq -r '.Response.ServiceAvailable'

# Verify env exists
tccli tcb DescribeEnvInfo --Region {{env.TENCENTCLOUD_REGION}} \
  --EnvIds '["{{user.env_id}}"]' \
  | jq -r '.Response.EnvList[0].Status'
```

## Region Support

CloudBase is available in all Tencent Cloud regions. Query available regions dynamically:

```bash
tccli cvm DescribeRegions --Region ap-guangzhou | jq -r '.Response.RegionSet[].RegionName'
```
