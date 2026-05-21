# ES Core Concepts

Architecture, node types, storage hierarchy, limits, and resource relationships for Tencent Cloud Elasticsearch Service.

---

## 1. Architecture Overview

Tencent Cloud ES provides a fully managed, elastically scalable cloud-native search and analytics engine built on open-source Elasticsearch, fully compatible with the ELK stack.

### Cluster Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Region (ap-guangzhou)                          │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    VPC (Virtual Private Cloud)               │ │
│  │  ┌─────────────────────────────────────────────────────────┐│ │
│  │  │              ES Cluster (es-xxxxxx)                      ││ │
│  │  │  ┌──────────┐  ┌────────────┐  ┌──────────────────────┐  ││ │
│  │  │  │ Data Node│  │Data Node   │  │  Dedicated Master    │  ││ │
│  │  │  │ (hot)    │  │(warm)      │  │  Nodes (optional)    │  ││ │
│  │  │  ├──────────┤  ├────────────┤  ├──────────────────────┤  ││ │
│  │  │  │CPU,Mem,  │  │CPU,Mem,    │  │  Cluster management, │  ││ │
│  │  │  │Disk(CBS) │  │Disk(COS)   │  │  stability           │  ││ │
│  │  │  └──────────┘  └────────────┘  └──────────────────────┘  ││ │
│  │  │                                                           ││ │
│  │  │  ┌──────────────────────────────────────────────────────┐ ││ │
│  │  │  │  Kibana（web UI for Dashboards & Queries）             │ ││ │
│  │  │  └──────────────────────────────────────────────────────┘ ││ │
│  │  └─────────────────────────────────────────────────────────┘│ │
│  │                                                               │ │
│  │  ┌────────────────────────────────┐  ┌──────────────────────┐  │ │
│  │  │  COS Bucket (Snapshot Backup)  │  │  Cloud Monitor       │  │ │
│  │  └────────────────────────────────┘  └──────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Scope |
|-----------|---------|-------|
| **Cluster Instance** | ES cluster with one or more nodes | Zone-specific |
| **Data Node** | Handles indexing and search workloads | Zone-specific |
| **Dedicated Master Node** | Cluster management, metadata, stability (optional) | Zone-specific |
| **Kibana** | Built-in web UI for data visualization, query, and cluster management | Cluster-level |
| **COS Snapshot** | Automated backup to COS for disaster recovery | Region-wide |
| **Cloud Monitor** | Metrics, alarms, dashboards for cluster health | Region-wide |

---

## 2. Node Types

### ES Node Specification Families

| Family | Code | Use Case | Examples |
|--------|------|----------|----------|
| **Standard** | ES.S1 | General-purpose search and analytics | ES.S1.MEDIUM4, ES.S1.LARGE8 |
| **Compute** | ES.C1 | High-CPU workloads (log processing, aggregations) | ES.C1.MEDIUM4, ES.C1.LARGE8 |
| **Memory** | ES.M1 | High-memory workloads (heavy caching, large indices) | ES.M1.LARGE16, ES.M1.2XLARGE32 |

### Node Type Matrix

| Type | vCPU | Memory (GB) | Disk Range (GB) | Use Case |
|------|------|-------------|-----------------|----------|
| ES.S1.MEDIUM2 | 2 | 4 | 100-500 | Dev/test, light search |
| ES.S1.MEDIUM4 | 2 | 8 | 100-1000 | Small production clusters |
| ES.S1.LARGE4 | 4 | 8 | 100-2000 | General production |
| ES.S1.LARGE8 | 4 | 16 | 100-3000 | Medium workloads |
| ES.S1.2XLARGE8 | 8 | 16 | 100-3000 | Heavy indexing |
| ES.S1.2XLARGE16 | 8 | 32 | 100-3000 | Search-heavy workloads |
| ES.S1.4XLARGE16 | 16 | 32 | 100-3000 | Large-scale clusters |
| ES.S1.4XLARGE32 | 16 | 64 | 100-3000 | Memory-intensive workloads |

### Dedicated Master Node Types

| Type | vCPU | Memory (GB) | Disk (GB) |
|------|------|-------------|-----------|
| ES.S1.MEDIUM2 | 2 | 4 | 20 |
| ES.S1.MEDIUM4 | 2 | 8 | 50 |

> **Recommendation:** For production clusters with ≥ 6 data nodes, enable dedicated master nodes (3 nodes recommended) to prevent cluster instability.

---

## 3. Disk Types

| Disk Type | Description | Use Case |
|-----------|-------------|----------|
| `CLOUD_SSD` | Cloud SSD — balanced performance | General-purpose production |
| `CLOUD_PREMIUM` | Premium cloud disk — cost-effective | Dev/test, less critical workloads |
| `CLOUD_HSSD` | Enhanced SSD — high IOPS | Write-heavy indexing workloads |
| `LOCAL_SSD` | Local SSD — low latency | High-performance search |

> Local SSD provides the lowest latency but data is not preserved if the CVM instance is terminated. Use CLOUD_SSD or CLOUD_HSSD for production data safety.

---

## 4. Elasticsearch Versions

| Version | Tencent Cloud Support | Notes |
|---------|----------------------|-------|
| 7.5.x | Available | Legacy, upgrade recommended |
| 7.10.x | Available | Stable, widely used |
| 7.14.x | Available | **Recommended** — latest 7.x features |
| 8.x (when available) | Available | Newer features, breaking changes from 7.x |

> Version 7.14.2 is the recommended default for new clusters.

---

## 5. Regional Availability

ES is available in most Tencent Cloud regions. Check via:

```bash
# Verify ES support in a region
tccli es DescribeInstances --Region ap-guangzhou --Limit 1
# If error: region not supported, try another region
```

Common ES-supported regions:

| Region | Zone ID | Nodes per Cluster (Max) | Kibana Enabled |
|--------|---------|------------------------|----------------|
| Guangzhou | ap-guangzhou-3, ap-guangzhou-6 | 50 | Yes |
| Shanghai | ap-shanghai-4, ap-shanghai-5 | 50 | Yes |
| Beijing | ap-beijing-3, ap-beijing-7 | 50 | Yes |
| Singapore | ap-singapore-1 | 30 | Yes |
| Silicon Valley | na-siliconvalley-1 | 30 | Yes |

---

## 6. Quotas and Limits

| Resource | Default Limit | How to Raise |
|----------|--------------|--------------|
| ES clusters per account | 20 | Submit ticket to Tencent Cloud |
| Nodes per cluster | 50 | Submit ticket |
| Disk per node | 3000 GB | Depends on disk type |
| Snapshot backups per cluster | 100 | Submit ticket |
| Max indices per cluster | 1000 (recommended by ES) | Depends on heap size |

---

## 7. Health Status

| Status | Code | Meaning |
|--------|------|---------|
| Green | 0 | All primary and replica shards are active |
| Yellow | 1 | All primary shards active, some replicas unassigned |
| Red | 2 | Some primary shards are not active — data unavailable |
| Unknown | -1 | Cluster status cannot be determined |

---

## 8. Cluster Status

| Status | Code | Meaning |
|--------|------|---------|
| Processing | 0 | Cluster being created, upgraded, or modified |
| Normal | 1 | Cluster is running normally |
| Stopped | -1 | Cluster is stopped (isolated) |

---

## 9. Resource Relationships

```
Account
 └── ES Cluster (InstanceId: es-xxxxxx)
      ├── Data Nodes (NodeType, NodeNum, DiskSize)
      ├── Dedicated Master Nodes (optional: MasterNodeNum, MasterNodeType)
      ├── Kibana (built-in web UI)
      ├── Indices (CreateIndex, DescribeIndexList, DeleteIndex)
      ├── Dictionaries (UpdateDictionaries — user-defined IK dictionaries)
      ├── Plugins (UpdatePlugins — analysis plugins)
      ├── Snapshots (CreateClusterSnapshot → COS bucket)
      └── Logs (DescribeInstanceLogs)
```

### Dependencies

| Resource | ES Relationship | Skill |
|----------|----------------|-------|
| VPC | ES cluster must be deployed in a VPC | `qcloud-vpc-ops` |
| Subnet | ES cluster must be in a subnet | `qcloud-vpc-ops` |
| Security Group | ES cluster uses security groups for network access | `qcloud-vpc-ops` |
| COS Bucket | ES snapshot backups are stored in COS | `qcloud-cos-ops` |
| Cloud Monitor | Metrics and alarms for ES cluster | `qcloud-monitor-ops` |
