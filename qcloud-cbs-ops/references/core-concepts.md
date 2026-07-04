# CBS Core Concepts

Architecture, disk types, states, performance, quotas, and resource relationships for Tencent Cloud CBS.

---

## 1. Architecture Overview

CBS (Cloud Block Storage) provides persistent block storage for CVM instances with high availability, snapshot backup, and flexible expansion capabilities.

### CBS Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Region (ap-guangzhou)                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐│
│  │   Zone 1         │  │   Zone 2         │  │   Zone 3       ││
│  │  ┌────────────┐  │  │  ┌────────────┐  │  │ ┌────────────┐ ││
│  │  │  CVM Host  │  │  │  │  CVM Host  │  │  │ │  CVM Host  │ ││
│  │  │ ┌────────┐ │  │  │  │ ┌────────┐ │  │  │ │ ┌────────┐ │ ││
│  │  │ │Instance│ │  │  │  │ │Instance│ │  │  │ │ │Instance│ │ ││
│  │  │ │ System │ │  │  │  │ │ System │ │  │  │ │ │ System │ │ ││
│  │  │ │  Disk  │ │  │  │  │ │  Disk  │ │  │  │ │ │  Disk  │ │ ││
│  │  │ └────────┘ │  │  │  │ └────────┘ │  │  │ │ └────────┘ │ ││
│  │  │ ┌────────┐ │  │  │  │ ┌────────┐ │  │  │ │ ┌────────┐ │ ││
│  │  │ │  Data  │ │  │  │  │ │  Data  │ │  │  │ │ │  Data  │ │ ││
│  │  │ │  Disk  │ │  │  │  │ │  Disk  │ │  │  │ │ │  Disk  │ │ ││
│  │  │ └────────┘ │  │  │  │ └────────┘ │  │  │ │ └────────┘ │ ││
│  │  └────────────┘  │  │  └────────────┘  │  │ └────────────┘ ││
│  └──────────────────┘  └──────────────────┘  └────────────────┘│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                      CBS Storage Layer                      ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐ ││
│  │  │  Cloud SSD  │  │   Premium   │  │   Enhanced SSD       │ ││
│  │  │  (High IOPS)│  │ (Balanced)  │  │   (Max Performance)  │ ││
│  │  └─────────────┘  └─────────────┘  └──────────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Snapshot Backup Layer                    ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐ ││
│  │  │  Snapshot 1 │  │  Snapshot 2 │  │   Auto-Policy        │ ││
│  │  │ (Point-in-  │  │ (Point-in-  │  │   (Scheduled)        │ ││
│  │  │  time)      │  │  time)      │  │                      │ ││
│  │  └─────────────┘  └─────────────┘  └──────────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Scope |
|-----------|---------|-------|
| **Cloud Disk** | Persistent block storage (system/data) | Zone-specific |
| **Snapshot** | Point-in-time backup of disk | Region-wide |
| **Auto-Snapshot Policy** | Automated scheduled backups | Region-wide |
| **Disk Type** | Performance tier (SSD/Premium/HSSD) | Zone-specific |
| **Encryption** | Data-at-rest encryption | Disk-level |

### Resource Relationships

```
CVM Instance
├── System Disk (CBS)
│   └── Mandatory, created with instance
│   └── Fixed disk type per image
│   └── Size: 20-500 GB
│
├── Data Disks (CBS)
│   └── Optional, separately managed
│   └── Configurable type and size
│   └── Size: 10-32,000 GB
│   └── Attach/Detach independently
│
└── Snapshots
    ├── Created from any CBS disk
    ├── Used for backup/restore
    └── Can create new disk/image
```

---

## 2. Disk Types

<!-- Use API for latest: `tccli cbs DescribeDiskConfigQuota --Region {{env.TENCENTCLOUD_REGION}} --InquiryType INQUIRY_CBS_CONFIG` -->

### Type Comparison

| Type | Code | Performance | Use Case | Best For |
|------|------|-------------|----------|----------|
| **Premium Cloud** | `CLOUD_PREMIUM` | High throughput, good IOPS | General workloads | Web servers, mid-size DB |
| **SSD Cloud** | `CLOUD_SSD` | Ultra-high IOPS | I/O intensive | High-performance DB, NoSQL |
| **Enhanced SSD** | `CLOUD_HSSD` | Maximum IOPS & throughput | Mission-critical | Core DB, big data |
| **Basic Cloud** | `CLOUD_BASIC` | Standard performance | Cost-sensitive | Archive, backup, dev/test |

### Performance Specifications

#### Performance Specifications

<!-- Use API for latest: `tccli cbs DescribeDiskConfigQuota ...` — specs below are representative as of 2026-05 -->

| Disk Type | Size Range | Base IOPS | Max IOPS | Max Throughput | Latency |
|-----------|-----------|-----------|----------|----------------|---------|
| CLOUD_PREMIUM | 10–32,000 GB | 1,800 | 2,500 | 130 MB/s | <10ms |
| CLOUD_SSD | 20–32,000 GB | 2,600 | 26,000 | 260 MB/s | <3ms |
| CLOUD_HSSD | 20–32,000 GB | 8,000 | 100,000 | 1,000 MB/s | <1ms |
| CLOUD_BASIC | 10–32,000 GB | — | — | — | — |

#### Performance Calculation Formula

```
Base IOPS: Fixed minimum per disk type
Extra IOPS: Calculated based on disk size

Total IOPS = Base IOPS + (Disk Size × IOPS per GB)

Example (CLOUD_SSD, 500GB):
= 2,600 + (500 × 50)
= 2,600 + 25,000
= 27,600 IOPS (capped at 26,000)
```

### Type Selection Guide

| Workload | Recommended Type | Rationale |
|----------|------------------|-----------|
| Web server logs | `CLOUD_PREMIUM` | Sequential write, cost-effective |
| MySQL/PostgreSQL | `CLOUD_SSD` | High random IOPS |
| Redis/MongoDB | `CLOUD_HSSD` | Ultra-low latency |
| Analytics/big data | `CLOUD_HSSD` | High throughput |
| Development/test | `CLOUD_BASIC` | Cost-optimized |
| Backup storage | `CLOUD_BASIC` | Sequential I/O, low cost |

---

## 3. Disk State Machine

### State Transitions

```
┌───────────┐     CreateDisks       ┌───────────┐
│   (new)   │ ───────────────────▶  │ CREATING  │
└───────────┘                       └─────┬─────┘
                                          │
                       ┌──────────────────┘
                       │
                       ▼
                ┌───────────┐
                │UNATTACHED │◀─────────────────┐
                └─────┬─────┘                  │
                      │                        │
      AttachDisks     │     DetachDisks        │
                      ▼                        │
                ┌───────────┐                  │
                │ ATTACHING │                  │
                └─────┬─────┘                  │
                      │                        │
                      ▼                        │
                ┌───────────┐                  │
                │  ATTACHED │──────────────────┘
                └─────┬─────┘   (after detach)
                      │
    ResizeDisk        │     DeleteDisks
                      ▼                        ▼
                ┌───────────┐            ┌───────────┐
                │ EXPANDING │            │ DELETING  │
                └─────┬─────┘            └─────┬─────┘
                      │                        │
                      ▼                        ▼
                ┌───────────┐            ┌───────────┐
                │  ATTACHED │            │  DELETED  │
                │ (resized) │            │           │
                └───────────┘            └───────────┘
```

### State Definitions

| State | Code | Description | Allowed Operations |
|-------|------|-------------|-------------------|
| `CREATING` | Initializing | Disk is being created | Poll only |
| `UNATTACHED` | Available | Disk not attached to any instance | Attach, Delete, Create Snapshot |
| `ATTACHING` | In Progress | Disk is being attached to instance | Poll only |
| `ATTACHED` | In Use | Disk attached to CVM instance | Detach, Resize, Create Snapshot |
| `DETACHING` | In Progress | Disk is being detached | Poll only |
| `EXPANDING` | In Progress | Disk capacity is being expanded | Poll only |
| `ROLLBACKING` | In Progress | Disk is being restored from snapshot | Poll only |
| `TORECYCLE` | Pending | Disk pending recycling | Recover or Delete |
| `DUMPING` | Exporting | Disk data is being exported | Poll only |

### State Transition Table

| From State | Operation | To State | Max Wait Time |
|------------|-----------|----------|---------------|
| — | CreateDisks | CREATING | 120s |
| CREATING | (auto) | UNATTACHED | 120s |
| UNATTACHED | AttachDisks | ATTACHING | 120s |
| ATTACHING | (auto) | ATTACHED | 120s |
| ATTACHED | DetachDisks | DETACHING | 120s |
| DETACHING | (auto) | UNATTACHED | 120s |
| ATTACHED | ResizeDisk | EXPANDING | 300s |
| UNATTACHED | ResizeDisk | EXPANDING | 300s |
| EXPANDING | (auto) | ATTACHED/UNATTACHED | 300s |
| ATTACHED | ApplySnapshot | ROLLBACKING | 300s |
| UNATTACHED | ApplySnapshot | ROLLBACKING | 300s |
| ROLLBACKING | (auto) | ATTACHED/UNATTACHED | 300s |
| UNATTACHED | DeleteDisks | DELETED | 60s |
| ATTACHED | DeleteDisks | Not allowed | — |

---

## 4. Performance Metrics

### Key Metrics

| Metric | Unit | Description | Alert Threshold |
|--------|------|-------------|-----------------|
| **IOPS** | ops/sec | Input/Output Operations Per Second | > 80% of max |
| **Throughput** | MB/s | Data transfer rate | > 80% of max |
| **Latency** | ms | Response time | > 10ms |
| **Queue Depth** | count | Pending I/O requests | > 32 |
| **Disk Usage** | % | Used space percentage | > 85% |
| **Burst Balance** | % | Burst credit balance | < 20% |

### IOPS vs Throughput

| Workload Pattern | Metric Focus | Optimization |
|------------------|--------------|--------------|
| Small random I/O | IOPS | Use SSD/HSSD, larger size |
| Large sequential I/O | Throughput | Use HSSD, stripe volumes |
| Mixed workload | Both | Right-size disk type |

### Performance Monitoring

```bash
# Monitor disk IOPS (via Cloud Monitor)
tccli monitor GetMonitorData \
  --Namespace QCE/CBS \
  --MetricName IopsRead \
  --Dimensions '[{"Name":"DiskId","Value":"disk-xxx"}]' \
  --Period 300 \
  --StartTime "2026-05-28T00:00:00+08:00" \
  --EndTime "2026-05-28T23:59:59+08:00"

# Monitor disk throughput
tccli monitor GetMonitorData \
  --Namespace QCE/CBS \
  --MetricName ThroughputRead \
  --Dimensions '[{"Name":"DiskId","Value":"disk-xxx"}]' \
  --Period 300
```

---

## 5. Quotas and Limits

### Default Quotas

<!-- Use API for latest: `tccli cbs DescribeDiskConfigQuota ...` and `tccli cbs DescribeSnapshotQuota ...` — defaults below may vary by region/account -->

| Resource | Default Quota | Scope |
|----------|---------------|-------|
| Max CBS disks per region | 100 | Per region |
| Max snapshots per region | 64 | Per region |
| Max auto-snapshot policies | 20 | Per region |
| Max disks per instance | 20 | Per CVM |
| Max snapshots per disk | 64 | Per disk |
| Max scheduled snapshots | 7 per policy | Per policy |

### Disk Size Limits

| Disk Type | Min Size | Max Size | Notes |
|-----------|----------|----------|-------|
| System disk | 20 GB | 500 GB | Depends on image |
| Data disk (CLOUD_BASIC) | 10 GB | 32,000 GB | — |
| Data disk (CLOUD_PREMIUM) | 10 GB | 32,000 GB | — |
| Data disk (CLOUD_SSD) | 20 GB | 32,000 GB | — |
| Data disk (CLOUD_HSSD) | 20 GB | 32,000 GB | — |

### Performance Limits

| Limit | Value |
|-------|-------|
| Max IOPS per disk | 100,000 (CLOUD_HSSD) |
| Max throughput per disk | 1,000 MB/s (CLOUD_HSSD) |
| Max IOPS per instance | 260,000 |
| Max throughput per instance | 4,000 MB/s |

### Request Quota Increase

- Console: https://console.cloud.tencent.com/cbs
- Ticket: Provide use case, expected growth, timeline

---

## 6. Billing Models

<!-- Use API for latest pricing: `tccli cbs InquiryPriceCreateDisks --Region {{env.TENCENTCLOUD_REGION}} --DiskType CLOUD_SSD --DiskSize 500 --DiskChargeType POSTPAID_BY_HOUR` -->

### Charge Types

| Type | Code | Billing Cycle | Use Case |
|------|------|---------------|----------|
| **Postpaid (Hourly)** | `POSTPAID_BY_HOUR` | Per hour | Variable workloads |
| **Prepaid (Monthly)** | `PREPAID` | Monthly/yearly | Stable workloads |

### Pricing Factors

| Factor | Impact | Notes |
|--------|--------|-------|
| Disk type | SSD > Premium > Basic | Higher performance = higher cost |
| Disk size | Linear scaling | Per GB pricing |
| Charge type | Prepaid 30-50% cheaper | Long-term commitment |
| Region | Varies by region | Check regional pricing |

### Cost Optimization

| Strategy | Description | Savings |
|----------|-------------|---------|
| Right-size disk type | Use BASIC for archive, SSD for DB | 20-50% |
| Prepaid for stable | Commit to 1-3 years | 30-50% |
| Scheduled shutdown | Stop disks with instances | 100% when stopped |
| Snapshot lifecycle | Auto-delete old snapshots | 10-30% |
| Disk sharing | Share snapshots across accounts | Reduce duplicate |

### Billing Calculation

```
Hourly Cost = Disk Size (GB) × Unit Price (per GB/hour)

Example (CLOUD_SSD, 500GB, Postpaid):
= 500 GB × $0.0003/GB/hour
= $0.15/hour
= ~$110/month (730 hours)

Prepaid (1 year, 30% discount):
= $110 × 12 × 0.7
= ~$924/year
```

---

## 7. Dependencies

### CBS Resource Dependencies

```
Disk Operations Require:
├── CVM Instance (for attach/detach)
│   └── Instance must exist in same zone
│   └── Instance state: RUNNING or STOPPED
│
├── VPC/Subnet (for network-attached storage)
│   └── Disk is network-attached to instance
│   └── Network latency affects performance
│
└── Snapshots
    ├── Source disk must exist
    └── Disk state must be stable
```

### Cross-Product Dependencies

| Product | Dependency | Skill |
|---------|------------|-------|
| CVM | Instance for disk attachment | `qcloud-cvm-ops` |
| VPC | Network for storage access | `qcloud-vpc-ops` |
| CAM | Permission for CBS operations | `qcloud-cam-ops` |
| Monitor | Metrics and alerts | `qcloud-monitor-ops` |

---

## 8. Anti-Patterns

| Anti-Pattern | Risk | Recommendation |
|--------------|------|----------------|
| Single disk for critical data | Data loss risk | Multi-disk RAID + snapshots |
| No snapshot policy | No backup coverage | Enable auto-snapshot |
| Oversized disk type | Cost waste | Right-size by IOPS needs |
| Attaching disk while in use | Data corruption | Unmount before detach |
| Local disk for persistent data | Data loss on termination | Use CBS cloud disks |
| No encryption for sensitive data | Security risk | Enable disk encryption |
| Keeping unused disks | Unnecessary cost | Terminate unused disks |
| Manual snapshot only | Human error | Auto-snapshot policy |

---

## 9. Best Practices Summary

### Reliability

- Enable auto-snapshot for critical disks
- Use multi-AZ deployment for high availability
- Test snapshot restore procedures regularly
- Monitor disk health metrics

### Performance

- Choose disk type based on IOPS requirements
- Monitor queue depth and latency
- Use larger disks for higher baseline IOPS
- Consider HSSD for mission-critical databases

### Security

- Enable disk encryption for sensitive data
- Control snapshot access with CAM
- Regular security audits
- Encrypt data in transit

### Cost

- Use prepaid for stable workloads
- Right-size disk types
- Implement snapshot lifecycle policy
- Terminate unused disks

---

## References

- [CBS API Reference](https://cloud.tencent.com/document/api/362)
- [CVM Core Concepts](../qcloud-cvm-ops/references/core-concepts.md)
- [Well-Architected Assessment](well-architected-assessment.md)
