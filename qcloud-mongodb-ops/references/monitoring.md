# Monitoring & Alerts — TencentDB for MongoDB

## Monitoring Metrics (Namespace: QCE/CMONGO)

### Instance-Level Metrics

| Metric | Name | Unit | Description |
|--------|------|------|-------------|
| Inserts | 写入请求次数 | 次 | Unit time write count |
| Reads | 读取请求次数 | 次 | Unit time read count |
| Qps | 每秒成功请求次数 | 次/秒 | CRUD operations per second |
| ClusterConn | 集群连接数 | 次 | Total proxy connections |
| Connper | 连接使用率 | % | Connection utilization |
| ClusterDiskUsage | 磁盘使用率 | % | Storage utilization |
| MonogdMaxCpuUsage | Mongod最大CPU使用率 | % | Max CPU across mongod nodes |
| MonogdAvgCpuUsage | Mongod平均CPU使用率 | % | Average CPU across mongod nodes |
| ClusterNetin | 入流量 | Bytes | Inbound network traffic |
| ClusterNetout | 出流量 | Bytes | Outbound network traffic |
| AvgAllRequestDelay | 所有请求平均延迟 | ms | Average request latency |
| AvgReadDelay | 读平均时延 | ms | Read request latency |
| AvgInsertDelay | 插入平均延迟 | ms | Insert request latency |
| AvgUpdateDelay | 更新平均延迟 | ms | Update request latency |
| AvgDeleteDelay | 删除平均延迟 | ms | Delete request latency |

### Replica Set-Level Metrics

| Metric | Name | Unit | Description |
|--------|------|------|-------------|
| SlaveDelay | 主从延迟 | 秒 | Primary-secondary replication lag |
| OplogReservedTime | Oplog保存时间 | 小时 | Oplog window duration |
| HitRatio | Cache命中率 | % | WiredTiger cache hit ratio |
| CacheDirty | Cache脏数据百分比 | % | Dirty data in cache |
| CacheUsed | Cache使用百分比 | % | Cache memory utilization |
| ReplicaDiskUsage | 磁盘使用率 | % | Replica set disk utilization |

### Node-Level Metrics (Mongod)

| Metric | Name | Unit | Description |
|--------|------|------|-------------|
| CpuUsage | CPU使用率 | % | Per-node CPU |
| MemUsage | 内存使用率 | % | Per-node memory |
| DiskUsage | 节点磁盘使用率 | % | Node disk |
| Conn | 连接数 | 次 | Node-level connections |
| ActiveSession | 活跃session数 | 次 | Active sessions |
| NodeSlavedelay | 主从延迟 | s | Node replication lag |
| NodeHitRatio | Cache命中率 | % | Node-level cache hit |
| NodeCacheUsed | Cache使用百分比 | % | Node cache usage |
| IoRead | 磁盘读次数 | 次/秒 | Disk read IOPS |
| IoWrite | 磁盘写次数 | 次/秒 | Disk write IOPS |

### Node-Level Metrics (Mongos)

Same as Mongod node metrics for CPU, memory, connections, latency, requests.

## Recommended Alarm Thresholds

| Metric | Warning | Critical | Description |
|--------|---------|----------|-------------|
| ClusterDiskUsage | > 80% | > 90% | Disk full → instance read-only |
| MonogdMaxCpuUsage | > 80% | > 90% | CPU bottleneck → scale up |
| Connper | > 80% | > 90% | Connection limit approaching |
| SlaveDelay | > 60s | > 300s | Replication lag → data loss risk |
| OplogReservedTime | < 4h | < 2h | Oplog too small → secondary can't catch up |
| AvgAllRequestDelay | > 200ms | > 1000ms | Performance degradation |
| CacheHitRatio | < 80% | < 60% | Working set too large for memory |

## Common Anomaly Patterns

### High CPU Usage

Metric: MonogdMaxCpuUsage > 80%

Possible causes:
- Missing indexes causing collection scans
- Frequent aggregation pipelines
- High write volume
- Inefficient queries

Diagnosis:
1. DescribeCurrentOp to find long-running operations
2. DescribeSlowLogPatterns to identify query patterns
3. Check index usage via MongoDB shell

### Connection Saturation

Metric: Connper > 80%

Possible causes:
- Application connection pool too large
- Connection leaks
- DDoS or unexpected traffic spike

Diagnosis:
1. DescribeClientConnections to see source IPs
2. Check application connection pool settings
3. Consider connection limiting via parameters

### Replication Lag

Metric: SlaveDelay > 60s

Possible causes:
- Large write operations blocking primary
- Secondary node under-provisioned
- Network latency between nodes

Diagnosis:
1. DescribeDBInstanceNodeProperty to check node status
2. Monitor network traffic (ClusterNetin/ClusterNetout)
3. Check if secondary has sufficient resources

### Disk Full

Metric: ClusterDiskUsage > 90%

Possible causes:
- Data growth exceeding projections
- Insufficient oplog size configuration
- Backup retention too long

Diagnosis:
1. DescribeDBBackups to check backup sizes
2. DescribeDBInstances.UsedVolume for actual usage
3. Consider ModifyDBInstanceSpec to increase Volume

## Querying Metrics via API

```bash
# Query by instance target dimension
# Namespace=QCE/CMONGO, Dimensions.N.0.Name=target, Dimensions.N.0.Value=cmgo-xxxxx
```

Refer to [Cloud Monitor API](https://cloud.tencent.com/document/product/248) for detailed query methods.
