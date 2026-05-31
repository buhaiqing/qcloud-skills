# Core Concepts — TencentDB for PostgreSQL

## Architecture

TencentDB for PostgreSQL supports two deployment architectures:

### Single-Node (基础版)
- Single compute node with local/cloud disk storage
- No automatic failover; suitable for development and testing
- Cost-effective for non-production workloads

### Multi-Node (双节点高可用版)
- 1 PRIMARY + 1 STANDBY node across availability zones
- Automatic failover: if PRIMARY fails, STANDBY is promoted automatically
- Synchronous/async replication configurable
- Best for: production workloads requiring high availability

### Read-Only Replica (只读实例)
- Read-only copy of the primary instance
- Supports up to 3 read-only replicas per instance
- Reduces load on primary for read-heavy workloads

## Instance States

| State | Description |
|-------|-------------|
| creating | Instance is being provisioned |
| running | Instance is active and serving |
| isolated | Instance is isolated (unpaid or manually isolated) |
| deleting | Instance is being deleted |
| deleted | Instance has been permanently deleted |

State transition: creating → running ↔ (modifying) → isolated → deleting → deleted

## Storage Engine

TencentDB for PostgreSQL uses the standard PostgreSQL storage engine:
- MVCC (Multi-Version Concurrency Control)
- WAL (Write-Ahead Logging) for crash recovery
- Full-text search (GIN/GIST indexes)
- JSONB support
- Partial indexes, expression indexes

## Supported PostgreSQL Versions

| Version | Release Year | Status |
|---------|-------------|--------|
| 12 | 2019 | Available |
| 13 | 2020 | Available |
| 14 | 2021 | Available |
| 15 | 2022 | Available |
| 16 | 2023 | Available |

> Note: Verify current version availability via `tccli postgres DescribeDBVersions`.

## Resource Limits

| Resource | Limit |
|----------|-------|
| Max storage per instance | 3000 GB |
| Min storage per instance | 10 GB |
| Max connections | Varies by memory (default: memory*4 ~ 100-1000+) |
| Max databases per instance | 100 |
| Max read-only replicas | 3 |
| Backup retention | 1-730 days (configurable) |
| Backup storage | Free up to 50% of instance storage |

## Network

- Deployed in VPC (Virtual Private Cloud)
- Supports Classic Network (legacy, not recommended)
- Private IP: stable within VPC lifecycle
- Public IP: optional, extra cost (recommended for emergencies only)

## Billing

| Model | Description | Suitability |
|-------|-------------|-------------|
| Prepaid (包年包月) | Pay upfront; 1-36 months | Stable production workloads |
| Postpaid (按量计费) | Pay per hour | Elastic/dev/test workloads |

## Regions and AZs

TencentDB for PostgreSQL is available in most Tencent Cloud regions:
- China: Beijing, Shanghai, Guangzhou, Chengdu, Chongqing, Nanjing, etc.
- Asia Pacific: Hong Kong, Singapore, Bangkok, Tokyo, Mumbai, etc.
- Other: Frankfurt, Silicon Valley, Virginia, Moscow, etc.

Verify availability per region: `tccli postgres DescribeProductConfig --Zone ap-guangzhou-3`
