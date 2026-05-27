# CDB Core Concepts

Architecture, instance types, storage engines, limits, and resource relationships for Tencent Cloud TencentDB for MySQL (CDB).

---

## 1. Architecture Overview

TencentDB for MySQL (CDB) provides a stable, reliable, and elastically scalable relational database service with comprehensive backup recovery, monitoring, disaster recovery, fast scaling, and data migration capabilities.

### Instance Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Region (ap-guangzhou)                          │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    VPC (Virtual Private Cloud)               │ │
│  │                                                               │ │
│  │  ┌──────────────────┐      ┌──────────────────┐               │ │
│  │  │   Zone A         │      │   Zone B         │               │ │
│  │  │  ┌────────────┐  │      │  ┌────────────┐  │               │ │
│  │  │  │ Master     │  │      │  │ Disaster   │  │               │ │
│  │  │  │ Instance   │  │◄────►│  │ Recovery   │  │               │ │
│  │  │  │ (Read/Write)│  │ sync │  │ Instance   │  │               │ │
│  │  │  └────────────┘  │      │  │ (Standby)  │  │               │ │
│  │  │                  │      │  └────────────┘  │               │ │
│  │  └──────────────────┘      └──────────────────┘               │ │
│  │                                                               │ │
│  │  ┌────────────────────────────────────────────────────────┐   │ │
│  │  │  Read-only Replica (Zone A)         Read-only (Zone B) │   │ │
│  │  └────────────────────────────────────────────────────────┘   │ │
│  │                                                               │ │
│  │  ┌──────────────────┐  ┌──────────────────────────────────┐   │ │
│  │  │  Backup Storage  │  │  Cloud Monitor (Metrics/Alarms)  │   │ │
│  │  └──────────────────┘  └──────────────────────────────────┘   │ │
│  └──────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose |
|-----------|---------|
| **Master Instance** | Primary instance handling read/write operations |
| **Disaster Recovery Instance** | Cross-AZ or cross-region standby for failover |
| **Read-only Replica** | Horizontal read scaling (up to 5 replicas) |
| **Backup Storage** | Automatic and manual backups (data + binlog) |
| **Cloud Monitor** | Metrics, alarms, dashboards for database health |

---

## 2. Instance Types

### By Role

| Type | Description | Use Case |
|------|-------------|----------|
| **Master (InstanceRole=master)** | Primary read/write instance | All production workloads |
| **Disaster Recovery (InstanceRole=dr)** | Cross-region standby | DR, compliance |
| **Read-only (InstanceRole=ro)** | Read-only replica | Read scaling, reporting |

### By Billing Model

| Model | Description | Use Case |
|-------|-------------|----------|
| **Prepaid (monthly/yearly)** | Pay upfront, lower unit cost | Stable, predictable workloads |
| **Postpaid (hourly)** | Pay per hour, flexible | Variable loads, dev/test |

### By Specification

Query available specifications dynamically:

```bash
tccli cdb DescribeDBInstanceSpecs
```

Sample output fields: `SpecName`, `Memory (MB)`, `Volume (GB)`, `MaxConnections`, `IOPS`.

---

## 3. Engine Versions

Check supported versions per instance:

```bash
tccli cdb DescribeSupportedEngineVersions --InstanceId "cdb-xxxxxx"
```

> **Recommendation:** Use MySQL 8.0 for new instances. Migrate from 5.5/5.6 to 5.7 or 8.0 for better performance and security.

---

## 4. Storage

| Type | Description | Use Case |
|------|-------------|----------|
| **Cloud SSD (CLOUD_SSD)** | High-performance SSD storage | General production |
| **Premium Cloud (CLOUD_PREMIUM)** | Cost-effective SSD storage | Dev/test, low I/O |
| **Enhanced SSD (CLOUD_HSSD)** | High IOPS, low latency | Write-intensive workloads |

### Disk Size Limits

Check per-version limits via spec query:

```bash
tccli cdb DescribeDBInstanceSpecs | python3 -c "import sys,json;d=json.load(sys.stdin);[(print(f'{s[\"SpecName\"]}: {s.get(\"MinDiskSize\",20)}-{s.get(\"MaxDiskSize\",\"?\")}GB')) for s in d.get('Response',{}).get('Items',[])]"
```

> Disk expansion is online — no restart required. Disk shrinkage is NOT supported.

---

## 5. Regional Availability

CDB is available in all Tencent Cloud regions. Query available zones dynamically:

```bash
tccli cdb DescribeDBInstanceSpecs --Region "ap-guangzhou"
# The Region flag controls which regional specs are returned
```

To list all regions and zone counts:
```bash
tccli cam DescribeRegions --Product "cdb"
tccli cam DescribeZones --Region "ap-guangzhou"
```

---

## 6. Quotas and Limits

Check account-level quotas dynamically (tencentcloud-sdk-python-cdb required):

```python
from tencentcloud.cdb.v20170320 import cdb_client, models
# Use DescribeDBInstanceQuota or check via DescribeDBInstances pagination
req = models.DescribeDBInstancesRequest()
req.Limit = 0  # Count only, no items
resp = client.DescribeDBInstances(req)
print(f"Current instance count: {resp.TotalCount}")
```

Key limits to be aware of:
- Read-only replicas per master: **max 5**
- Databases per instance: **max 100**
- Accounts per instance: **max 100**
- Backup retention: **7-1830 days**
- Backup file size: **200% of instance storage**

---

## 7. Instance States

| Status | Code | Meaning |
|--------|------|---------|
| Creating | 0 | Instance being provisioned |
| Running | 1 | Normal operation |
| Isolating | 4 | Instance being isolated (payment overdue) |
| Isolated | 5 | Instance isolated (can be recovered within retention period) |
| Deleting | 10 | Instance being deleted |

---

## 8. Backup Types

| Type | Description | Retention |
|------|-------------|-----------|
| **Automatic Backup** | Daily backup (configurable time window) | Configurable (7-1830 days) |
| **Manual Backup** | User-initiated backup | Until manually deleted |
| **Binlog Backup** | Continuous binary log backup | Same as data backup retention |

### Backup Methods

| Method | Description | Size | Use Case |
|--------|-------------|------|----------|
| **Physical Backup** | Raw data file backup (xtrabackup) | Smaller, faster restore | Default for production |
| **Logical Backup** | SQL dump (mysqldump) | Larger, slower | Selective restore, cross-version |

---

## 9. Resource Relationships

```
Account
 └── CDB Instance (InstanceId: cdb-xxxxxx)
      ├── Master Instance (InstanceType=1)
      ├── Disaster Recovery Instance (InstanceType=2, cross-region)
      ├── Read-only Replicas (InstanceType=3, max 5)
      ├── Databases (user-created databases)
      ├── Accounts (CreateAccounts, ModifyAccountPrivileges)
      ├── Parameters (ModifyInstanceParam)
      ├── Backups (CreateBackup, DescribeBackups)
      ├── Security: SSL (OpenSSL/CloseSSL)
      ├── Encryption (OpenDBInstanceEncryption)
      └── Logs (DescribeErrorLogData, DescribeSlowLogData)
```

### Dependencies

| Resource | CDB Relationship | Skill |
|----------|-----------------|-------|
| VPC | CDB instance must be deployed in a VPC | `qcloud-vpc-ops` |
| Subnet | CDB instance must be in a subnet | `qcloud-vpc-ops` |
| Security Group | CDB uses security groups for network access | `qcloud-vpc-ops` |
| Cloud Monitor | Metrics and alarms for CDB | `qcloud-monitor-ops` |
| CVM | Application servers connecting to CDB | `qcloud-cvm-ops` |

### Cross-Skill Delegation

- **MySQL connection issues?** Check CVM network configuration via `qcloud-cvm-ops`
- **VPC/subnet issues?** Delegate to `qcloud-vpc-ops`
- **Monitor dashboard/alarms?** Delegate to `qcloud-monitor-ops`
- **Elasticsearch/Redis/PostgreSQL?** Route to their respective skills
