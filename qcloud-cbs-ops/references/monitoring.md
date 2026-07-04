# CBS Monitoring & Alerts

> CBS metrics and alarm configuration via Cloud Monitor.

## Key Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| DiskUsage | Disk capacity utilization | % |
| DiskReadIops | Disk read IOPS | counts/s |
| DiskWriteIops | Disk write IOPS | counts/s |
| DiskReadThroughput | Disk read throughput | MB/s |
| DiskWriteThroughput | Disk write throughput | MB/s |
| DiskIOPSUtilization | IOPS utilization | % |
| DiskTraffic | Disk traffic | MB/s |

## Alarm Configuration

Configure alarms via Cloud Monitor console: https://console.cloud.tencent.com/monitor

### Recommended Alarm Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| DiskUsage | > 70% | > 85% |
| DiskIOPSUtilization | > 70% | > 90% |
| DiskReadThroughput | > 80% of limit | > 95% of limit |

## See also
- [Core Concepts](core-concepts.md)
- [Troubleshooting](troubleshooting.md)
