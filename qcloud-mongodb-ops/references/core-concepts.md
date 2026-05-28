# Core Concepts — TencentDB for MongoDB

## Architecture

TencentDB for MongoDB supports two cluster architectures:

### Replica Set (副本集)
- Default deployment: 1 PRIMARY + 2 SECONDARY nodes
- Automatic failover: if PRIMARY fails, a SECONDARY is elected automatically
- Node roles: PRIMARY (read/write), SECONDARY (read-only), ARBITER (voting only), HIDDEN (backup/diagnostics)
- Best for: production workloads up to moderate scale

### Sharded Cluster (分片集群)
- Components: mongos (routing), config servers (metadata), shards (data)
- Each shard is a replica set (usually 3 nodes)
- Horizontal scaling: add more shards to increase capacity
- Best for: large-scale data (>1TB), high throughput workloads

## Instance States

| Code | State | Description |
|------|-------|-------------|
| 0 | Creating | Instance is being provisioned |
| 1 | In progress | Instance in maintenance/transition |
| 2 | Running | Instance is active and serving |
| 3 | Isolated | Instance is isolated (unpaid or manually isolated) |
| -2 | Deleted | Instance has been permanently deleted |

State transition: Creating(0) → Running(2) ↔ In progress(1) → Isolated(3) → Deleted(-2)

## Storage Engine

All MongoDB versions use **WiredTiger** as the default storage engine:
- Document-level concurrency control
- Compression (snappy/zlib/zstd)
- Checkpoint-based snapshots

## Supported MongoDB Versions

| Version Code | MongoDB Version | Status |
|-------------|-----------------|--------|
| MONGO_36_WT | 3.6 | Legacy |
| MONGO_40_WT | 4.0 | Available |
| MONGO_42_WT | 4.2 | Available |
| MONGO_50_WT | 5.0 | Available |
| MONGO_60_WT | 6.0 | Available |
| MONGO_70_WT | 7.0 | Available |
| MONGO_80_WT | 8.0 | Available |

> Note: Cloud Disk Edition (HCD) supports versions 4.0-6.0 only (not 7.0/8.0).

## Machine Types

| Type | Code | Description | Backup Method |
|------|------|-------------|---------------|
| High IO 10 Gigabit | HIO10G | Local NVMe SSD, high IOPS | Logical backup |
| Cloud Disk Edition | HCD | Cloud-based storage, snapshot backup, elastic scaling | Snapshot/physical backup |

## Cluster Types

| Code | Type | Description |
|------|------|-------------|
| 0 | Replica set | Primary + Secondaries, automatic failover |
| 1 | Sharded cluster | Multiple shards + mongos + config servers |

## Payment Modes

| Mode | Code | Description | Use Case |
|------|------|-------------|----------|
| Postpaid | 0 | Pay-as-you-go, hourly billing | Dev/test, variable workloads |
| Prepaid | 1 | Monthly/yearly, reserved discount | Production, stable workloads |

## Network Types

| Code | Type | Description |
|------|------|-------------|
| 0 | Classic network | Legacy, shared network segment |
| 1 | VPC | Virtual Private Cloud, isolated network |

**Recommendation:** Always use VPC for production deployments.

## Resource Relationships

```
Project
  └── MongoDB Instance (DBInstance)
        ├── Security Groups (0+)
        ├── Backups (0+)
        │     ├── Full backups (logical/physical/snapshot)
        │     └── Oplog (incremental)
        ├── Accounts (0+)
        ├── Replica Sets / Shards
        │     └── Nodes (PRIMARY, SECONDARY, READONLY, ARBITER)
        ├── Monitoring Metrics (QCE/CMONGO)
        └── Parameter Template (0-1)
```

## Regions and Availability Zones

Available regions include but are not limited to:
- ap-guangzhou (Guangzhou)
- ap-shanghai (Shanghai)
- ap-beijing (Beijing)
- ap-hongkong (Hong Kong)
- ap-singapore (Singapore)
- ap-tokyo (Tokyo)
- ap-siliconvalley (Silicon Valley)

Query current availability:
```bash
tccli mongodb DescribeSpecInfo
```

## Spec Ranges

Query current per-region specs via API (TE-1: dynamic query, not hardcoded):
```bash
tccli mongodb DescribeSpecInfo --Region ap-guangzhou
```

Key spec parameters: CPU cores, Memory (MB), Volume (MB), Max connections, Max QPS, Node limits.

## Key Limits

- **Slow log query range:** Max 7 days (InvalidParameterValue.QueryTimeOutOfRange)
- **Backup retention:** Configurable via SetBackupRules
- **Oplog size:** 10%-90% of disk capacity (InvalidParameterValue.OplogSizeOutOfRange)
- **Disk resize:** Must be ≥ 1.2× current used disk (InvalidParameterValue.SetDiskLessThanUsed)
- **Postpaid instances per region:** Limited (InvalidParameterValue.PostPaidInstanceBeyondLimit)
- **Password:** 8-32 characters, must include letters, digits, and special characters
- **DescribeDBInstances Offset:** 0-10000
- **DescribeDBInstances Limit:** 1-100
