# CVM Core Concepts

Architecture, limits, regions, quotas, and resource relationships for Tencent Cloud CVM.

---

## 1. Architecture Overview

CVM (Cloud Virtual Machine) provides scalable virtual servers on Tencent Cloud infrastructure.

### Compute Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Region (ap-guangzhou)                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐│
│  │   Zone 1         │  │   Zone 2         │  │   Zone 3       ││
│  │  ┌────────────┐  │  │  ┌────────────┐  │  │ ┌────────────┐ ││
│  │  │  CVM Host  │  │  │  │  CVM Host  │  │  │ │  CVM Host  │ ││
│  │  │ ┌────────┐ │  │  │  │ ┌────────┐ │  │  │ │ ┌────────┐ │ ││
│  │  │ │Instance│ │  │  │  │ │Instance│ │  │  │ │ │Instance│ │ ││
│  │  │ └──CBS───┘ │  │  │  │ └──CBS───┘ │  │  │ │ └──CBS───┘ │ ││
│  │  └────────────┘  │  │  └────────────┘  │  │ └────────────┘ ││
│  └──────────────────┘  └──────────────────┘  └────────────────┘│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                      VPC (Virtual Private Cloud)            ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐ ││
│  │  │  Subnet A   │  │  Subnet B   │  │   Security Group     │ ││
│  │  │  (Zone 1)   │  │  (Zone 2)   │  │   (Firewall Rules)   │ ││
│  │  └─────────────┘  └─────────────┘  └──────────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Scope |
|-----------|---------|-------|
| **Instance** | Virtual compute unit (CPU, Memory, Network) | Zone-specific |
| **CBS Disk** | Block storage attached to instance | Zone-specific |
| **Image** | OS template for instance creation | Region-wide |
| **Snapshot** | Point-in-time backup of CBS disk | Region-wide |
| **Security Group** | Virtual firewall rules | Region-wide |
| **VPC/Subnet** | Network isolation layer | Region-wide |
| **Dedicated Host** | Physical server isolation (CDH) | Zone-specific |

---

## 2. Instance Types

### Instance Type Families

| Family | Code | Use Case | Examples |
|--------|------|----------|----------|
| **Standard S** | S5, SA2, SA3 | General-purpose web/apps | S5.SMALL1, SA2.MEDIUM4 |
| **Compute C** | C5, C6 | High CPU compute | C5.LARGE8, C6.LARGE16 |
| **Memory M** | M5, M6 | High memory DB/cache | M5.LARGE16, M6.2XLARGE32 |
| **Big Data D** | D2, D3 | Big data, Hadoop | D2.8XLARGE64 |
| **GPU GN** | GN7, GN8 | AI/ML, rendering | GN7.8XLARGE32 |
| **FPGA FX** | FX3 | Hardware acceleration | FX3.4XLARGE32 |
| **High IO IT** | IT5 | Low-latency IO | IT5.4XLARGE32 |
| **Bursted B** | B1, B2 | Cost-sensitive variable loads | B1.SMALL1 |

### Type Naming Convention

```
[Family][Generation].[Size]
Example: S5.SMALL1

- S5: Standard family, generation 5
- SMALL1: 1 vCPU, 1GB memory

Size codes:
- SMALL: 1 vCPU
- MEDIUM: 2 vCPU
- LARGE: 4 vCPU
- XLARGE: 8 vCPU
- 2XLARGE: 16 vCPU
- 4XLARGE: 32 vCPU
```

### Instance Type Matrix (S5 Family)

Check available instance types via API:

```bash
# Query all S5 types available in a zone
tccli cvm DescribeZoneInstanceConfigInfos --Region ap-guangzhou --Zone ap-guangzhou-3 | jq '.Response.InstanceTypeQuotaSet[] | select(.Status=="AVAILABLE" and (.InstanceFamily|test("S5"))) | {InstanceType, Cpu, Memory}'
```

---

## 3. Storage (CBS)

### CBS Disk Types

| Type | Code | Performance | Use Case |
|------|------|-------------|----------|
| **Premium Cloud** | `CLOUD_PREMIUM` | High throughput, good IOPS | General workloads |
| **SSD Cloud** | `CLOUD_SSD` | Ultra-high IOPS | Database, critical |
| **Enhanced SSD** | `CLOUD_HSSD` | Maximum IOPS | High-performance DB |
| **Basic Cloud** | `CLOUD_BASIC` | Standard performance | Archive, backup |
| **Local SSD** | `LOCAL_SSD` | Ultra-fast ephemeral | Temp high-IO |

### CBS Limits

| Limit | Value |
|-------|-------|
| Max disks per instance | 20 |
| System disk max size | 500 GB |
| Data disk max size | 32,000 GB |
| Single disk type change | Not supported (must create new) |

### Disk Attachment

- System disk: auto-created with instance, type fixed
- Data disks: separate CBS resource, attached/detached
- Attachment requires same zone as instance

---

## 4. Regions and Zones

### Regions (China)

Query via API:

```bash
tccli cvm DescribeRegions | jq '.Response.RegionSet[] | select(.RegionState=="AVAILABLE")'
```

### Regions (International)

Same API returns international regions — filter where needed.

### Zone Selection Criteria

1. **Instance type availability**: Some types only in certain zones
2. **Service availability**: Some services zone-specific
3. **Cross-zone latency**: 1-3ms within region
4. **Disaster recovery**: Multi-zone deployment for HA

---

## 5. Quotas and Limits

### Instance Quotas

Query actual account quotas via API:

```bash
tccli cvm DescribeAccountQuota --Region ap-guangzhou
```

### Check Quota

```bash
tccli cvm DescribeAccountQuota --Region ap-guangzhou
```

### CBS Quotas (defaults)

| Limit | Value |
|-------|-------|
| Max CBS disks per region | 100 |
| Max snapshots per region | 64 |
| Max images per region | 50 |

Instance quotas vary by account type; query with `DescribeAccountQuota`.

### Request Quota Increase

- Console: https://console.cloud.tencent.com/cvm
- Ticket: Provide use case, expected growth, timeline

---

## 6. Instance States

### State Transitions

```
┌───────────┐     RunInstances      ┌───────────┐
│   (new)   │ ──────────────────▶   │ PENDING   │
└───────────┘                        └─────┬─────┘
                                           │
                    ┌──────────────────────┘
                    │
                    ▼
              ┌───────────┐
              │  RUNNING  │◀─────────────────┐
              └─────┬─────┘                  │
                    │                        │
     StartInstances │                        │ RebootInstances
                    │ StopInstances          │
                    ▼                        │
              ┌───────────┐                  │
              │  STOPPED  │──────────────────┘
              └─────┬─────┘
                    │
                    │ TerminateInstances
                    ▼
              ┌───────────┐
              │TERMINATED │ (deleted)
              └───────────┘
```

### State Definitions

| State | Code | Description |
|-------|------|-------------|
| `PENDING` | Creating | Instance initializing |
| `RUNNING` | Active | Instance operational |
| `STOPPED` | Shutdown | Instance stopped, resources retained |
| `SHUTDOWN` | Stopping | Transition to STOPPED |
| `TERMINATED` | Deleted | Instance released, cannot recover |

---

## 7. Network Configuration

### Network Types

| Type | Code | Description |
|------|------|-------------|
| **VPC** | `VPC` | Virtual private cloud (recommended) |
| **Basic Network** | `BASIC` | Classic network (legacy) |

### Internet Access Options

| Option | Charge Type | Description |
|--------|-------------|-------------|
| `TRAFFIC_POSTPAID_BY_HOUR` | Pay by traffic | Variable bandwidth |
| `BANDWIDTH_POSTPAID_BY_HOUR` | Pay by bandwidth | Fixed bandwidth |
| `BANDWIDTH_PREPAID` | Monthly bandwidth | Prepaid fixed |

### Security Groups

- Region-level resource, applies to instances
- Can attach up to 5 security groups per instance
- Rules: inbound/outbound, protocol, port, source/dest

---

## 8. Billing Models

### Instance Charge Types

| Type | Code | Billing Cycle | Use Case |
|------|------|---------------|----------|
| **Postpaid** | `POSTPAID_BY_HOUR` | Hourly | Variable workloads |
| **Prepaid** | `PREPAID` | Monthly/yearly | Stable workloads |

### Prepaid Renewal Options

- Auto-renewal on expiration
- Manual renewal before expiry
- Terminate after expiry (prepaid resources released)

### Cost Optimization

| Strategy | Description |
|----------|-------------|
| Reserved instances | 3-year prepaid, up to 50% discount |
| Spot instances | 90% discount, volatile availability |
| Scheduled instances | Prepaid at specific times |
| Scheduled shutdown | Stop non-production at night |

---

## 9. Dependencies

### Resource Dependencies

```
Instance creation requires:
├── VPC (Virtual Private Cloud)
├── Subnet (within VPC)
├── Security Group (firewall rules)
├── Image (OS template)
│   └── Public image (pre-built)
│   └── Custom image (from instance)
│       └── Snapshot (backup)
└── Key pair (SSH access)
└── CBS Disk (storage)
    └── System disk (auto-created)
    └── Data disks (optional)
```

### Cross-Product Dependencies

| Product | Dependency | Skill |
|---------|------------|-------|
| VPC | Network isolation | `qcloud-vpc-ops` |
| CLB | Load distribution | `qcloud-clb-ops` |
| MySQL | Database backend | `qcloud-cdb-ops` |
| COS | Object storage | `qcloud-cos-ops` |
| CAM | Permission control | `qcloud-cam-ops` |

---

## 10. Anti-Patterns

| Anti-Pattern | Risk | Recommendation |
|--------------|------|----------------|
| Single-zone deployment | Zone outage = total failure | Multi-zone with CLB |
| No backup policy | Data loss risk | Scheduled snapshots |
| Public IP for internal services | Security risk | Use VPC private IP + NAT |
| Oversized instances | Cost waste | Right-size based on metrics |
| Manual scaling | Operational burden | Auto-scaling group |
| No monitoring | Undetected issues | Cloud Monitor + alerts |
| Hardcoded passwords | Security risk | SSH key pair + CAM |

---

## 11. Best Practices Summary

### Reliability

- Multi-zone deployment with auto-recovery
- Regular snapshot backups
- Cross-region image replication for DR
- Monitor CPU/memory/disk metrics

### Security

- Security group whitelist (not open all ports)
- SSH key pair (disable password login)
- CAM least-privilege permissions
- VPC isolation for sensitive workloads

### Cost

- Right-size based on utilization (CPU < 70%)
- Prepaid for stable workloads
- Stop/terminate unused instances
- Use scheduled shutdown for dev/test

### Efficiency

- Auto-scaling for variable loads
- Batch operations via CLI/SDK
- Infrastructure as code (terraform)
- Scheduled tasks via timer