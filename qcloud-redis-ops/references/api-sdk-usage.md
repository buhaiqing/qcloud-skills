# TencentDB for Redis API & SDK Usage

## API Reference

**Base URL:** `https://redis.tencentcloudapi.com`
**API Version:** 2018-04-12
**API Product:** Redis
**Documentation:** https://cloud.tencent.com/document/api/239

## Operation Map

### Instance Lifecycle

| API Method | Description | CLI Command | Required Params |
|------------|-------------|-------------|-----------------|
| CreateInstance | Create a Redis instance | `tccli redis CreateInstance` | Memory, Period, GoodsNum, Zone, Password |
| DescribeInstances | Query instance details | `tccli redis DescribeInstances` | Optional: InstanceId |
| DescribeInstanceList | Paginated instance list | `tccli redis DescribeInstanceList` | Offset, Limit |
| IsolateInstance | Soft-delete instance | `tccli redis IsolateInstance` | InstanceId |
| OnlineIsolateInstance | Online isolate instance | `tccli redis OnlineIsolateInstance` | InstanceId |
| OfflineIsolateInstance | Offline isolate instance | `tccli redis OfflineIsolateInstance` | InstanceId |
| CleanInstance | Hard-delete isolated instance | `tccli redis CleanInstance` | InstanceId |
| UnIsolateInstance | Restore isolated instance | `tccli redis UnIsolateInstance` | InstanceId |

### Instance Management

| API Method | Description | CLI Command | Required Params |
|------------|-------------|-------------|-----------------|
| UpgradeInstance | Upgrade memory/spec/type | `tccli redis UpgradeInstance` | InstanceId, Memory |
| AutoRenewInstance | Enable auto-renew for prepaid | `tccli redis AutoRenewInstance` | InstanceId |
| ManualRenewInstance | Manual renewal | `tccli redis ManualRenewInstance` | InstanceId, Period |
| ModifyInstanceName | Rename instance | `tccli redis ModifyInstanceName` | InstanceId, InstanceName |
| ModifyInstancePassword | Change password | `tccli redis ModifyInstancePassword` | InstanceId, Password |
| ModifyInstanceParams | Change runtime params | `tccli redis ModifyInstanceParams` | InstanceId, Params |
| DescribeParamTemplateInfo | Query param templates | `tccli redis DescribeParamTemplateInfo` | TemplateId |

### Backup Management

| API Method | Description | CLI Command | Required Params |
|------------|-------------|-------------|-----------------|
| DescribeInstanceBackupRecords | List backup records | `tccli redis DescribeInstanceBackupRecords` | InstanceId, BeginTime, EndTime |
| DescribeAutoBackupConfig | Get auto backup config | `tccli redis DescribeAutoBackupConfig` | InstanceId |
| ModifyAutoBackupConfig | Set auto backup config | `tccli redis ModifyAutoBackupConfig` | InstanceId, WeekDays, TimePeriod |

### Product Information

| API Method | Description | CLI Command | Required Params |
|------------|-------------|-------------|-----------------|
| DescribeProductInfo | Query instance specs | `tccli redis DescribeProductInfo` | None |
| DescribeInstanceDealDetail | Query trade/order details | `tccli redis DescribeInstanceDealDetail` | DealId |

### Instance Security

| API Method | Description | CLI Command | Required Params |
|------------|-------------|-------------|-----------------|
| DescribeInstanceSecurityGroups | Get security groups | `tccli redis DescribeInstanceSecurityGroups` | InstanceId |
| AssociateSecurityGroups | Associate security groups | `tccli redis AssociateSecurityGroups` | InstanceId, SecurityGroupIds |
| DisassociateSecurityGroups | Dissociate security groups | `tccli redis DisassociateSecurityGroups` | InstanceId, SecurityGroupIds |

### Monitoring

| API Method | Description | CLI Command | Required Params |
|------------|-------------|-------------|-----------------|
| DescribeInstanceMonitorToCloudMonitor | Monitor data | `tccli redis DescribeInstanceMonitorToCloudMonitor` | InstanceId |
| DescribeInstanceMonitorBigKey | Check big keys | `tccli redis DescribeInstanceMonitorBigKey` | InstanceId |

## SDK Usage Examples

### Initialization

```python
from tencentcloud.common import credential
from tencentcloud.redis import redis_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = redis_client.RedisClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
```

### CreateInstance Request

```python
req = models.CreateInstanceRequest()
req.Memory = 1024                        # Required: memory in MB
req.Period = 1                           # Required: billing period (months)
req.GoodsNum = 1                         # Required: quantity
req.Zone = "100001"                      # Required: zone ID
req.ProjectId = 0                        # Optional: project
req.Password = os.environ.get("REDIS_PASSWORD")
req.VpcId = os.environ.get("VPC_ID")
req.SubnetId = os.environ.get("SUBNET_ID")
req.InstanceName = os.environ.get("INSTANCE_NAME")
req.AutoRenewFlag = 0                    # Optional: auto-renew
req.NoAuth = False                       # Optional: disable authentication
resp = client.CreateInstance(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

### DescribeInstances Response

```json
{
  "Response": {
    "InstanceSet": [
      {
        "InstanceId": "crs-xxxxxxxx",
        "Name": "my-redis",
        "Status": 2,
        "Size": 1024,
        "VpcId": "vpc-xxxxx",
        "SubnetId": "subnet-xxxxx",
        "Ip": "10.0.1.100",
        "Port": 6379,
        "WanAddress": "",
        "ProjectId": 0,
        "AutoRenewFlag": 0,
        "NetType": 0,
        "Type": 2
      }
    ],
    "TotalCount": 1,
    "RequestId": "abc-123-def"
  }
}
```

## Pagination Pattern

```bash
OFFSET=0
LIMIT=100
while true; do
  DATA=$(tccli redis DescribeInstanceList --Offset $OFFSET --Limit $LIMIT --Region {{env.TENCENTCLOUD_REGION}})
  COUNT=$(echo "$DATA" | jq '.Response.InstanceSet | length')
  echo "$DATA" | jq '.Response.InstanceSet[]'
  [ "$COUNT" -lt "$LIMIT" ] && break
  OFFSET=$((OFFSET + LIMIT))
done
```

## Async Operation Pattern

Instance creation/upgrade is async. Poll DescribeInstances until Status = 2:

```bash
poll_redis_status() {
  INST_ID=$1
  TARGET_STATUS=${2:-2}
  MAX_WAIT=${3:-600}
  INTERVAL=${4:-10}

  for i in $(seq 1 $((MAX_WAIT / INTERVAL))); do
    STATUS=$(tccli redis DescribeInstances --InstanceId "$INST_ID" | jq -r '.Response.InstanceSet[0].Status')
    if [ "$STATUS" = "$TARGET_STATUS" ]; then
      echo "Redis instance reached status $TARGET_STATUS"
      return 0
    fi
    sleep $INTERVAL
  done
  echo "Timeout waiting for status $TARGET_STATUS (current: $STATUS)"
  return 1
}
```