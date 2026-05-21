# TencentDB for Redis Integration Guide

## SDK Setup

### Installation

```bash
# Full Redis SDK
pip install tencentcloud-sdk-python-redis

# Or install full SDK
pip install tencentcloud-sdk-python
```

### Python SDK Usage

```python
from tencentcloud.common import credential
from tencentcloud.redis import redis_client, models
import os

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = redis_client.RedisClient(
    cred,
    os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou")
)

# Example: List instances
req = models.DescribeInstanceListRequest()
req.Offset = 0
req.Limit = 100
resp = client.DescribeInstanceList(req)
for inst in resp.InstanceSet:
    print(f"Redis: {inst.Name} [{inst.InstanceId}] - {inst.Size}MB - Status {inst.Status}")
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TENCENTCLOUD_SECRET_ID` | API Secret ID | Yes |
| `TENCENTCLOUD_SECRET_KEY` | API Secret Key | Yes |
| `TENCENTCLOUD_REGION` | Default region code | Yes |

## Cross-Skill Delegation Matrix

| Redis Needs | From Skill | What to Delegate |
|-------------|------------|------------------|
| VPC/Subnet creation | `qcloud-vpc-ops` | Create VPC and subnet before CreateInstance |
| Security group management | `qcloud-vpc-ops` | Create/configure security groups for Redis |
| Metrics and alerting | `qcloud-monitor-ops` | Monitor data, alert rules, dashboards |
| CAM permissions | `qcloud-cam-ops` | IAM policies for Redis operations |

## CI/CD Integration

### Redis in CI/CD Pipeline

```yaml
# Provision Redis for environment
steps:
  - name: Create Redis instance
    run: |
      tccli redis CreateInstance \
        --Memory 2048 \
        --Period 1 \
        --Zone "${ZONE}" \
        --VpcId "${VPC_ID}" \
        --SubnetId "${SUBNET_ID}" \
        --InstanceName "app-${ENV}-redis" \
        --Password "${REDIS_PASSWORD}"

  - name: Wait for Redis ready
    run: |
      for i in $(seq 1 60); do
        STATUS=$(tccli redis DescribeInstances --InstanceId "$INST_ID" | jq -r '.Response.InstanceSet[0].Status')
        [ "$STATUS" = "2" ] && break
        sleep 10
      done

  - name: Set Redis connection string
    run: |
      IP=$(tccli redis DescribeInstances --InstanceId "$INST_ID" | jq -r '.Response.InstanceSet[0].Ip')
      PORT=$(tccli redis DescribeInstances --InstanceId "$INST_ID" | jq -r '.Response.InstanceSet[0].Port')
      echo "REDIS_URL=redis://:$REDIS_PASSWORD@$IP:$PORT/0" >> .env
```

## Automation: Redis Health Check

```bash
#!/bin/bash
# Daily Redis instance health check
for INST_ID in $(tccli redis DescribeInstanceList --Region ap-guangzhou --Limit 100 | jq -r '.Response.InstanceSet[].InstanceId'); do
  echo "=== Redis: $INST_ID ==="
  tccli redis DescribeInstances --InstanceId "$INST_ID" | jq '.Response.InstanceSet[0] | {
    name: .Name,
    status: .Status,
    memory_mb: .Size,
    connections: .Conn,
    cpu_percent: .Cpu,
    mem_percent: .Mem
  }'
done
```

## Redis CLI Integration

```bash
# Connect from CVM in same VPC
redis-cli -h <internal_ip> -p 6379 -a <password>

# Test connectivity
redis-cli -h <internal_ip> -p 6379 -a <password> ping
# Expected: PONG
```