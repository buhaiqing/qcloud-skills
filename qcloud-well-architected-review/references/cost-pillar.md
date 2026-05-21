# Cost Pillar — Tencent Cloud Well-Architected Framework

## Overview

The Cost pillar ensures Tencent Cloud resources are right-sized, idle resources are identified and addressed, billing models are understood, and cost optimization is automated.

## 1. Billing Model Documentation

| Model | Description | When to Use |
|-------|-------------|-------------|
| On-Demand (按量计费) | Pay per hour/usage | Variable workloads, testing |
| Monthly/Yearly (包年包月) | Prepaid for 1-3 years | Stable production workloads |
| Spot/Preemptible | Discounted, interruptible | Batch jobs, fault-tolerant workloads |

## 2. Idle Resource Detection

### 2.1 Detection Patterns

| Pattern | Detection Method | Threshold | Recommendation |
|---------|-----------------|-----------|----------------|
| Low CPU | `CPUUsage < 10%` over 7 days | 7-day average < 10% | Downsize or terminate |
| Low Memory | `MemUsage < 20%` over 7 days | 7-day average < 20% | Downsize |
| Stopped instance | Instance `STOPPED` > 7 days | Stop duration > 7d | Review if needed |
| Unattached disk | CBS `UNATTACHED` > 30 days | Detach duration > 30d | Delete or attach |
| Unused EIP | EIP not bound > 7 days | Unbound > 7d | Release |
| Empty COS bucket | Zero requests > 30 days | Requests = 0 for 30d | Archive or delete |

### 2.2 CLI Detection

```bash
# Check CVM instances with low CPU (Monitor API)
tccli monitor DescribeBaseMetrics \
  --MetricName CPUUsage \
  --Namespace QCE/CVM \
  --Period 86400 \
  --StartTime "2026-05-14 00:00:00" \
  --EndTime "2026-05-21 00:00:00"

# Check unattached CBS disks
tccli cbs DescribeDisks \
  --Filters '[{"Name":"attachment.instance-id","Values":[""]}]'
```

## 3. Right-Sizing Recommendations

| Current State | Recommendation |
|---------------|----------------|
| CPU > 80% sustained | Upsize CPU tier |
| Memory > 90% sustained | Upsize memory tier |
| CPU < 10% sustained | Downsize to smaller instance |
| Disk I/O near limit | Upgrade disk type (SSD) |
| Network bandwidth at limit | Upgrade bandwidth tier |

## 4. Cost Optimization Actions

| Action | Savings Estimate | Risk |
|--------|-----------------|------|
| Convert on-demand to monthly | 30-50% | Low (if workload stable) |
| Right-size oversized instances | 20-60% | Medium (monitor after resize) |
| Delete idle resources | 100% of resource cost | Low (verify first) |
| Use reserved instances for baseline | 40-70% | Low (for predictable workloads) |
| Delete old snapshots/backups | Variable | Medium (verify retention policy) |

## 5. Cost Assessment Score

| Score | Criteria |
|-------|----------|
| 90-100 | All resources right-sized, monthly billing for stable, no idle resources |
| 70-89 | Most resources optimized, some on-demand for stable workloads |
| 50-69 | Mix of billing models, some idle resources unaddressed |
| < 50 | All on-demand, significant idle resources, no cost monitoring |
