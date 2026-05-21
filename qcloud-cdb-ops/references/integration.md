# CDB Integration Guide

SDK setup, environment configuration, Cloud Shell, and cross-skill delegation for Tencent Cloud TencentDB for MySQL.

---

## 1. Execution Environments

CDB skill supports three execution environments:

| Environment | Setup Required | Use Case |
|-------------|---------------|----------|
| **Local CLI** | Install tccli + credentials | Quick operations, automation scripts |
| **Local SDK** | Python 3.8+ + `tencentcloud-sdk-python-cdb` | Complex operations, batch processing, error handling |
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

### Cloud Shell Commands

```bash
# Check tccli version
tccli version

# Check Python SDK
python3 -c "from tencentcloud.cdb.v20170320 import cdb_client, models; print('CDB SDK OK')"

# List MySQL instances
tccli cdb DescribeDBInstances --Region ap-guangzhou --Limit 10

# Save scripts to persistent storage
mkdir -p /data/scripts
cat > /data/scripts/cdb_health_check.py << 'EOF'
import os, json
from tencentcloud.common import credential
from tencentcloud.cdb.v20170320 import cdb_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = cdb_client.CdbClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))
req = models.DescribeDBInstancesRequest()
resp = client.DescribeDBInstances(req)
for item in resp.Items:
    print(f"{item.InstanceId}: {item.InstanceName} — Status={item.Status}, Spec={item.Memory}MB/{item.Volume}GB")
EOF
python3 /data/scripts/cdb_health_check.py
```

---

## 3. Local CLI Setup

```bash
# Install tccli
pip install tccli

# Verify
tccli version
tccli cdb help

# Set credentials
export TENCENTCLOUD_SECRET_ID="AKIDxxxx"
export TENCENTCLOUD_SECRET_KEY="xxxxx"
export TENCENTCLOUD_REGION="ap-guangzhou"

# Quick test
tccli cdb DescribeDBInstances --Region ap-guangzhou --Limit 5
```

---

## 4. Local Python SDK Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install CDB SDK
pip install tencentcloud-sdk-python-cdb
# Or full SDK suite
pip install tencentcloud-sdk-python
```

### SDK Verification Script

```python
#!/usr/bin/env python3
"""CDB SDK connection test."""
import os
from tencentcloud.common import credential
from tencentcloud.cdb.v20170320 import cdb_client, models

def test_connection():
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = cdb_client.CdbClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))
    req = models.DescribeDBInstancesRequest()
    req.Limit = 5
    resp = client.DescribeDBInstances(req)
    print(f"Connected. Found {resp.TotalCount} MySQL instances.")
    return True

test_connection()
```

---

## 5. Cross-Skill Delegation Patterns

### CDB + VPC (Network Verification Before CreateInstance)

```bash
# 1. Delegate to qcloud-vpc-ops: verify VPC/subnet exist
# Task: tccli vpc DescribeVpcs --VpcIds '["vpc-xxxxxx"]'

# 2. Create MySQL instance in verified VPC
tccli cdb CreateDBInstance \
  --Region ap-guangzhou \
  --Memory 4000 \
  --Volume 200 \
  --Period 1 \
  --GoodsNum 1 \
  --Zone ap-guangzhou-3 \
  --UniqVpcId "vpc-xxxxxx" \
  --UniqSubnetId "subnet-xxxxxx" \
  --EngineVersion "8.0"
```

### CDB + CVM (Application Connection Troubleshooting)

```bash
# Scenario: Application on CVM cannot connect to MySQL

# 1. Delegate to qcloud-cvm-ops: check network interface
# Task: tccli cvm DescribeInstances --InstanceIds '["ins-xxxxxx"]'
# Verify CVM is in same VPC as CDB

# 2. Use qcloud-vpc-ops to verify security group allows MySQL port (3306)
# Task: tccli vpc DescribeSecurityGroupRules --SecurityGroupId "sg-xxxxxx"

# 3. Test MySQL connectivity from CVM
# mysql -h <cdb_vip> -P 3306 -u dbuser -p -e "SELECT 1"
```

### CDB + Monitor (Dashboard and Alarms)

```bash
# Delegate to qcloud-monitor-ops: set up dashboards and alarms
# Task: Create alarm for CpuUseRate > 80% with 10-minute evaluation
# Task: Create alarm for VolumeRate > 90%
# Task: Create dashboard for CPU, memory, disk, connections, slow queries
```

### CDB + DTS (Database Migration)

For migration scenarios (on-premise → CDB, CDB → CDB), refer to:
- Tencent Cloud DTS (Data Transmission Service) documentation
- Replication, schema migration, and full data migration are handled by DTS independently
- DTS has its own dedicated console and API

---

## 6. CI/CD Integration

### GitHub Actions Example

```yaml
name: CDB Backup Check

on:
  schedule:
    - cron: '0 6 * * 1'  # Every Monday at 6:00

jobs:
  cdb-backup-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check CDB Backup Status
        run: |
          pip install tccli
          export TENCENTCLOUD_SECRET_ID=${{ secrets.TENCENTCLOUD_SECRET_ID }}
          export TENCENTCLOUD_SECRET_KEY=${{ secrets.TENCENTCLOUD_SECRET_KEY }}
          
          # Check latest backup
          tccli cdb DescribeBackups \
            --InstanceId "cdb-xxxxxx" \
            --Limit 1 | python3 -c "
import sys,json
d=json.load(sys.stdin)
if d['Response']['Items']:
    b = d['Response']['Items'][0]
    print(f'Latest backup: {b[\"Date\"]}')
    print(f'Status: {b[\"Status\"]}')
    print(f'Size: {b[\"BackupSize\"]}MB')
    if b['Status'] != 'SUCCESS':
        exit(1)
else:
    print('No backups found!')
    exit(1)
"
```

### Terraform Integration

```hcl
# Example: Reference CDB instance in Terraform
data "tencentcloud_mysql_instance" "cdb" {
  instance_id = "cdb-xxxxxx"
}

output "cdb_vip" {
  value = data.tencentcloud_mysql_instance.cdb.vip
}

output "cdb_vport" {
  value = data.tencentcloud_mysql_instance.cdb.vport
}
```

---

## 7. Environment Variables Summary

| Variable | Required | Description |
|----------|----------|-------------|
| `TENCENTCLOUD_SECRET_ID` | Yes | API secret ID |
| `TENCENTCLOUD_SECRET_KEY` | Yes | API secret key |
| `TENCENTCLOUD_REGION` | Yes | Default region (e.g., ap-guangzhou) |
| `CDB_PASSWORD` | For create | MySQL account password |
| `https_proxy` | Optional | HTTP proxy if needed |

---

## 8. Common Script Templates

### Bulk Instance Inventory

```python
#!/usr/bin/env python3
"""List all CDB instances across regions with key metadata."""
import os, json
from tencentcloud.common import credential
from tencentcloud.cdb.v20170320 import cdb_client, models

REGIONS = ["ap-guangzhou", "ap-shanghai", "ap-beijing", "ap-chengdu", "ap-singapore", "ap-hongkong"]
STATUS_MAP = {"0": "Creating", "1": "Running", "4": "Isolating", "5": "Isolated"}

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)

print(f"{'Region':<20} {'Instance':<25} {'Status':<12} {'Spec':<18} {'IP':<20}")
print("="*100)
for region in REGIONS:
    try:
        client = cdb_client.CdbClient(cred, region)
        req = models.DescribeDBInstancesRequest()
        resp = client.DescribeDBInstances(req)
        for item in resp.Items:
            status = STATUS_MAP.get(str(item.Status), f"Unknown({item.Status})")
            spec = f"{item.Memory}MB/{item.Volume}GB"
            ip = f"{item.Vip}:{item.Vport}"
            print(f"{region:<20} {item.InstanceName or item.InstanceId:<25} {status:<12} {spec:<18} {ip:<20}")
    except Exception as e:
        print(f"{region:<20} {'ERROR':<25} {str(e)[:30]:<12}")
```

### Backup Retention Cleanup

```bash
#!/bin/bash
# Delete backups older than N days
INSTANCE_ID="${1:-cdb-xxxxxx}"
RETENTION_DAYS="${2:-30}"
CUTOFF=$(date -v-${RETENTION_DAYS}d +%Y-%m-%d)

tccli cdb DescribeBackups --InstanceId "$INSTANCE_ID" --Limit 100 | python3 -c "
import sys,json,subprocess
d=json.load(sys.stdin)
cutoff = '$CUTOFF'
deleted = 0
for b in d['Response'].get('Items', []):
    backup_date = b['Date'][:10]
    if backup_date < cutoff:
        bid = b['BackupId']
        print(f'Deleting backup #{bid} from {backup_date}')
        subprocess.run(['tccli','cdb','DeleteBackups',
            '--InstanceId', '$INSTANCE_ID',
            '--BackupIds', f'[{bid}]'])
        deleted += 1
print(f'Deleted {deleted} old backups')
" 2>&1 | grep -v '^{'
```

### Parameter Audit

```python
#!/usr/bin/env python3
"""Audit CDB instance parameters against best practices."""
import os, json
from tencentcloud.common import credential
from tencentcloud.cdb.v20170320 import cdb_client, models

RECOMMENDED = {
    "max_connections": "1000",
    "wait_timeout": "28800",
    "innodb_buffer_pool_size": "2147483648",  # 2GB default
    "slow_query_log": "ON",
    "long_query_time": "2"
}

instance_id = os.environ.get("CDB_INSTANCE_ID", "cdb-xxxxxx")
cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = cdb_client.CdbClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))

req = models.DescribeInstanceParamsRequest()
req.InstanceId = instance_id
resp = client.DescribeInstanceParams(req)

current = {p.Name: p.CurrentValue for p in resp.Items if hasattr(p, 'CurrentValue')}

for param, recommended in RECOMMENDED.items():
    actual = current.get(param, "N/A")
    status = "✅" if actual == recommended else "⚠️"
    print(f"{status} {param}: {actual} (recommended: {recommended})")
```
