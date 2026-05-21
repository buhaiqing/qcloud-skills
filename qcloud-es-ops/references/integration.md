# ES Integration Guide

SDK setup, environment configuration, Cloud Shell, and cross-skill delegation for Tencent Cloud Elasticsearch Service.

---

## 1. Execution Environments

ES skill supports three execution environments:

| Environment | Setup Required | Use Case |
|-------------|---------------|----------|
| **Local CLI** | Install tccli + credentials | Quick operations, automation scripts |
| **Local SDK** | Python 3.8+ + `tencentcloud-sdk-python-es` | Complex operations, batch processing, error handling |
| **Cloud Shell** | Zero setup (browser-based) | Quick diagnostics, troubleshooting |

---

## 2. Cloud Shell Integration

### What is Cloud Shell

Cloud Shell is a browser-based shell environment provided by Tencent Cloud:

- **Pre-installed**: `tccli`, `tencentcloud-sdk-python`, common tools
- **Pre-authenticated**: Uses console login credentials automatically
- **Persistent storage**: 10GB persistent disk for scripts
- **Multi-region**: Switch regions with `--Region` flag
- **Free**: No additional cost (within quota)

### Access Cloud Shell

1. Login to [Tencent Cloud Console](https://console.cloud.tencent.com)
2. Click **Cloud Shell** icon (top right toolbar)
3. Terminal opens in browser

### Cloud Shell Features

```
┌──────────────────────────────────────────────────────────────────┐
│                    Tencent Cloud Console                          │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Cloud Shell Terminal                                        │ │
│  │  ┌────────────────────────────────────────────────────────┐  │ │
│  │  │ $ tccli es DescribeInstances --Region ap-guangzhou     │  │ │
│  │  │ Response: {...}                                        │  │ │
│  │  │                                                         │  │ │
│  │  │ Features:                                               │  │ │
│  │  │ ✓ Pre-installed tccli (latest)                         │  │ │
│  │  │ ✓ Pre-installed Python SDK (tencentcloud-sdk-python-es)│  │ │
│  │  │ ✓ Auto-authenticated (console login)                   │  │ │
│  │  │ ✓ Persistent storage (/data/)                          │  │ │
│  │  │ ✓ Upload/download files                                │  │ │
│  │  │ ✓ Multiple sessions                                    │  │ │
│  │  └────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### Cloud Shell Commands

```bash
# Check tccli version
tccli version

# Check Python SDK
python3 -c "from tencentcloud.es.v20180416 import es_client, models; print('ES SDK OK')"

# List ES clusters
tccli es DescribeInstances --Region ap-guangzhou --Limit 10

# Save scripts
mkdir -p /data/scripts
cat > /data/scripts/es_health_check.py << 'EOF'
import os, json
from tencentcloud.common import credential
from tencentcloud.es.v20180416 import es_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = es_client.EsClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))
req = models.DescribeInstancesRequest()
resp = client.DescribeInstances(req)
for inst in resp.InstanceList:
    print(f"{inst.InstanceId}: {inst.InstanceName} — Health={inst.HealthStatus}, Status={inst.Status}")
EOF
python3 /data/scripts/es_health_check.py
```

---

## 3. Local CLI Setup

```bash
# Install tccli
pip install tccli

# Verify
tccli version
tccli es help

# Set credentials
export TENCENTCLOUD_SECRET_ID="AKIDxxxx"
export TENCENTCLOUD_SECRET_KEY="xxxxx"
export TENCENTCLOUD_REGION="ap-guangzhou"

# Quick test
tccli es DescribeInstances --Region ap-guangzhou --Limit 5
```

---

## 4. Local Python SDK Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install ES SDK
pip install tencentcloud-sdk-python-es
# Or full SDK suite
pip install tencentcloud-sdk-python
```

### SDK Verification Script

```python
#!/usr/bin/env python3
"""ES SDK connection test."""
import os
from tencentcloud.common import credential
from tencentcloud.es.v20180416 import es_client, models

def test_connection():
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = es_client.EsClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))
    req = models.DescribeInstancesRequest()
    req.Limit = 5
    resp = client.DescribeInstances(req)
    print(f"Connected. Found {resp.TotalCount} ES clusters.")
    return True

test_connection()
```

---

## 5. Cross-Skill Delegation Patterns

### ES + VPC (Network Verification Before CreateInstance)

```bash
# 1. Delegate to qcloud-vpc-ops: verify VPC/subnet exist
# Task: tccli vpc DescribeVpcs --VpcIds '["vpc-xxxxxx"]'

# 2. Create ES cluster in verified VPC
tccli es CreateInstance \
  --Region ap-guangzhou \
  --Zone ap-guangzhou-3 \
  --VpcId "vpc-xxxxxx" \
  --SubnetId "subnet-xxxxxx" \
  --NodeType "ES.S1.MEDIUM4" \
  --NodeNum 3 \
  --DiskSize 200 \
  --EsVersion "7.14.2" \
  --Password "YourPassword123"
```

### ES + COS (Snapshot Backup)

```bash
# 1. Delegate to qcloud-cos-ops: verify COS bucket exists
# Task: tccli cos HeadBucket --Bucket "my-es-snapshots-1250000000"

# 2. Create ES snapshot (stored to COS automatically)
tccli es CreateClusterSnapshot \
  --InstanceId "es-xxxxxx" \
  --SnapshotName "weekly-backup-20260521"
```

### ES + Monitor (Dashboard and Alarms)

```bash
# Delegate to qcloud-monitor-ops: set up dashboards and alarms
# Task: Create alarm for ClusterStatus >= 2 (red) with 1-minute evaluation
# Task: Create dashboard for JVM heap, search latency, disk usage
```

### ES + CVM (Application Integration)

```bash
# CVM running application connecting to ES cluster endpoint
# ES endpoint retrieved from DescribeInstances: InstanceList[0].EsDomain
# Delegate to qcloud-cvm-ops if application has network/connectivity issues
```

---

## 6. CI/CD Integration

### GitHub Actions Example

```yaml
name: ES Cluster Health Check

on:
  schedule:
    - cron: '0 8 * * 1'  # Every Monday at 8:00

jobs:
  es-health-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check ES Cluster Health
        run: |
          pip install tccli
          export TENCENTCLOUD_SECRET_ID=${{ secrets.TENCENTCLOUD_SECRET_ID }}
          export TENCENTCLOUD_SECRET_KEY=${{ secrets.TENCENTCLOUD_SECRET_KEY }}
          tccli es DescribeInstances \
            --Region ap-guangzhou \
            --InstanceIds '["es-xxxxxx"]' | python3 -c "
import sys,json
d=json.load(sys.stdin)
i=d['Response']['InstanceList'][0]
health = i['HealthStatus']
print(f'Cluster: {i[\"InstanceName\"]}')
print(f'Health: {\"GREEN\" if health==0 else \"YELLOW\" if health==1 else \"RED\"} ')
exit(0 if health in [0,1] else 1)
"
```

### Terraform Integration

```hcl
# Example: Reference ES cluster endpoint in Terraform
data "tencentcloud_elasticsearch_instances" "es" {
  instance_id = "es-xxxxxx"
}

output "es_domain" {
  value = data.tencentcloud_elasticsearch_instances.es.instance_list[0].es_domain
}
```

---

## 7. Environment Variables Summary

| Variable | Required | Description |
|----------|----------|-------------|
| `TENCENTCLOUD_SECRET_ID` | Yes | API secret ID |
| `TENCENTCLOUD_SECRET_KEY` | Yes | API secret key |
| `TENCENTCLOUD_REGION` | Yes | Default region (e.g., ap-guangzhou) |
| `ES_PASSWORD` | For create | Initial Kibana/ES password |
| `https_proxy` | Optional | HTTP proxy if needed |

---

## 8. Common Script Templates

### Bulk Index Health Check

```python
#!/usr/bin/env python3
"""Check all ES clusters across regions."""
import os, json
from tencentcloud.common import credential
from tencentcloud.es.v20180416 import es_client, models

REGIONS = ["ap-guangzhou", "ap-shanghai", "ap-beijing", "ap-chengdu", "ap-singapore"]

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)

print(f"{'Region':<20} {'Cluster':<30} {'Health':<10} {'Nodes':<8}")
print("="*70)
for region in REGIONS:
    try:
        client = es_client.EsClient(cred, region)
        req = models.DescribeInstancesRequest()
        resp = client.DescribeInstances(req)
        for inst in resp.InstanceList:
            health = {0:"GREEN", 1:"YELLOW", 2:"RED", -1:"UNKN"}.get(inst.HealthStatus, "?")
            print(f"{region:<20} {inst.InstanceName:<30} {health:<10} {inst.NodeNum:<8}")
    except Exception as e:
        print(f"{region:<20} {'ERROR':<30} {str(e)[:30]:<10}")
```

### Snapshot Retention Management

```bash
#!/bin/bash
# Delete snapshots older than 30 days
INSTANCE_ID="${1:-es-xxxxxx}"
CUTOFF=$(date -v-30d +%Y%m%d)

tccli es DescribeClusterSnapshot --InstanceId "$INSTANCE_ID" | python3 -c "
import sys,json,subprocess
d=json.load(sys.stdin)
cutoff = $CUTOFF
deleted = 0
for snap in d['Response'].get('ClusterSnapshotSet', []):
    snap_date = snap['SnapshotName'].split('-')[-1][:8]
    if snap_date.isdigit() and int(snap_date) < cutoff:
        sid = snap['SnapshotId']
        print(f'Deleting old snapshot: {snap[\"SnapshotName\"]} ({sid})')
        subprocess.run(['tccli','es','DeleteClusterSnapshot',
            '--InstanceId', '$INSTANCE_ID', '--SnapshotId', sid])
        deleted += 1
print(f'Deleted {deleted} old snapshots')
" 2>&1 | grep -v '^{'
```
