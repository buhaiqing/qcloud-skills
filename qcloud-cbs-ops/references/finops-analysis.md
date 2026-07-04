# CBS FinOps Analysis

> CBS cost optimization and idle resource analysis.

## Cost Optimization Strategies

| Strategy | Description |适用场景 |
|----------|-------------|---------|
| Snapshot lifecycle | Auto-delete snapshots older than 30 days | Reduce snapshot storage costs |
| Disk type selection | Use SSD only for performance-critical workloads | Balance cost and performance |
| Idle disk detection | Identify unused disks (not attached, no I/O) | Reduce waste |
| Pay-as-you-go vs prepaid | Prepaid for stable long-term workloads | Save ~20% on stable disks |
| Resize disk | Shrink disk if over-provisioned | Reduce unused capacity |

## Idle Disk Detection Query

```bash
tccli cbs DescribeDisks --DiskState AVAILABLE --Offset 0 --Limit 100
```

## Disk Type Cost Comparison

| Type |性能| Price |
|------|------|-------|
| CLOUD_PREMIUM | Lower | ~$0.05/GB/month |
| CLOUD_SSD | High | ~$0.15/GB/month |
| CLOUD_HSSD | Ultra high | ~$0.35/GB/month |

## See also
- [Core Concepts](core-concepts.md)
- [Monitoring](monitoring.md)
