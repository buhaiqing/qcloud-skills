# TencentDB for Redis Core Concepts

## Architecture Overview

TencentDB for Redis is a fully managed, in-memory data store compatible with Redis protocol.

### Instance Types (Redis Modes)

| Mode | Architecture | Description | Use Case |
|------|-------------|-------------|----------|
| **Standalone** (单机版) | Single node | No replica; data loss on node failure | Development, testing, non-critical cache |
| **Master-Replica** (主从版) | Master 1 node + 1-3 replicas | Automatic failover; reads from replica possible | Production HA, general-purpose |
| **Cluster** (集群版) | Multiple shards, each with master+replica | Horizontal scaling; data distributed across shards | Large-scale, high-throughput workloads |

### Instance Specifications

| Spec Code Pattern | Memory | Approx. QPS | Network Bandwidth | Max Connections |
|-------------------|--------|-------------|-------------------|-----------------|
| `standard1` | 1 GB | ~50K | 100 Mbps | 10,000 |
| `standard2` | 2 GB | ~50K | 100 Mbps | 10,000 |
| `standard4` | 4 GB | ~50K | 100 Mbps | 10,000 |
| `standard8` | 8 GB | ~50K | 100 Mbps | 10,000 |
| `standard16` | 16 GB | ~50K | 100 Mbps | 20,000 |
| `standard32` | 32 GB | ~50K | 100 Mbps | 20,000 |
| `standard64` | 64 GB | ~50K | 100 Mbps | 20,000 |

> Query exact specs via `DescribeProductInfo` API — availability varies by region and zone.

### Resource Hierarchy

```
Account
└── Redis Instance (crs-xxx)
    ├── Master node
    ├── Replica node(s) (for master-replica/cluster)
    ├── Backup records
    ├── Security groups
    ├── Whitelist (client IP ranges)
    └── Parameters (timeout, maxmemory-policy, etc.)
```

### Key Dependencies

| Dependency | Purpose | Delegate Skill |
|------------|---------|----------------|
| **VPC** (Virtual Private Cloud) | Private network isolation | `qcloud-vpc-ops` |
| **Subnet** | Network segment for instance | `qcloud-vpc-ops` |
| **Monitor** | Metrics, alarms, dashboards | `qcloud-monitor-ops` |

### Network Access

| Access Type | Description |
|-------------|-------------|
| **Internal (内网)** | Via VPC private IP; recommended for production; no public exposure |
| **External (外网)** | Via public IP; available on request; security risk — use whitelist |

### Lifecycle States

| Status | Meaning |
|--------|---------|
| `0` | Initializing — instance created but not ready |
| `1` | Running (legacy status) — mostly equivalent to status 2 |
| `2` | Running — instance fully operational |
| `3` | Isolating/Deleting — instance in deletion pipeline |
| `4` | Isolated — instance soft-deleted, data retained |
| `5` | Unisolate — restoring from isolated state |

## Limits and Quotas

| Resource | Default Limit | Notes |
|----------|---------------|-------|
| Instances per account | Varies by region | Check DescribeInstances for current count |
| Memory per instance | Up to 256 GB (cluster mode) | Depends on instance type |
| Backup retention | Up to 30 days | Configurable via ModifyAutoBackupConfig |
| Whitelist rules per instance | 200 IP ranges | CIDR or single IP |
| Parameter templates | Per product spec | Use DescribeParamTemplateInfo |

## Supported Regions

TencentDB for Redis is available in all major Tencent Cloud regions including Guangzhou, Shanghai, Beijing, Hong Kong, Singapore, and others. Availability of specific instance types varies by zone.

## Redis Version Support

| Version | Status | Notes |
|---------|--------|-------|
| Redis 7.0 | Latest | Recommended for new instances |
| Redis 6.0 | Stable | Widely deployed |
| Redis 5.0 | Maintenance | Legacy; plan migration |

## Backup and Recovery

| Feature | Description |
|---------|-------------|
| Auto Backup | Daily automatic backup; configurable time window |
| Manual Backup | On-demand backup via API |
| Backup Retention | 1-30 days (configurable) |
| Recovery | Can restore backup data; note this requires manual import via redis-cli |

> The CreateInstanceBackupRecords API creates a backup snapshot. Instance data is backed up via RDB snapshots stored internally.

## Cost Model

| Billing Mode | Description |
|--------------|-------------|
| Pay-as-you-go (按量计费) | Hourly billing based on actual usage |
| Prepaid (包年包月) | Monthly/annual commitment; significant discount vs pay-as-you-go |

> Prepaid instances require renewal (AutoRenewInstance or ManualRenewInstance). Expired instances are isolated automatically.