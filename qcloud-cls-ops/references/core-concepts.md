# CLS Core Concepts

## Architecture Overview

Tencent Cloud CLS (Cloud Log Service) is a one-stop log data service platform that provides real-time log collection, storage, search, analysis, and visualization capabilities.

```
┌─────────────────────────────────────────────────────────────┐
│                        CLS Architecture                      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ LogSource│    │LogSource │    │LogSource │   ...        │
│  │(LogFiles)│    │(API/SDK) │    │(K8s Pod) │              │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘              │
│       │               │               │                      │
│       └───────────────┼───────────────┘                      │
│                       │                                      │
│  ┌────────────────────┴────────────────────┐                │
│  │           LogListener Agent              │                │
│  │  - File monitoring                        │                │
│  │  - Real-time collection                   │                │
│  │  - Local buffering                        │                │
│  └────────────────────┬────────────────────┘                │
│                       │                                      │
│  ┌────────────────────▼────────────────────┐                │
│  │          CLS Service Platform           │                │
│  │  ┌─────────────────────────────────┐   │                │
│  │  │ Logset → Topic → Index          │   │                │
│  │  │  - Storage management            │   │                │
│  │  │  - Index optimization            │   │                │
│  │  └─────────────────────────────────┘   │                │
│  │  ┌─────────────────────────────────┐   │                │
│  │  │ Search & Analysis Engine        │   │                │
│  │  │  - Full-text search              │   │                │
│  │  │  - SQL analysis                  │   │                │
│  │  │  - Visualization                 │   │                │
│  │  └─────────────────────────────────┘   │                │
│  └─────────────────────────────────────────┘                │
│                       │                                      │
│  ┌────────────────────▼────────────────────┐                │
│  │        Consumption & Delivery           │                │
│  │  - Kafka consumer                        │                │
│  │  - COS shipping                          │                │
│  │  - Ckafka export                         │                │
│  └─────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

## Core Concepts

### Logset (日志集)

| Attribute | Description | Limits |
|-----------|-------------|--------|
| **LogsetId** | Unique identifier | System generated |
| **LogsetName** | Human-readable name | 1-63 characters |
| **Region** | Data storage region | Cannot be changed |
| **TopicCount** | Number of topics | Max 500 per logset |
| **CreateTime** | Creation timestamp | ISO 8601 format |
| **Tags** | Resource tags | Max 10 per logset |

**Usage Pattern:**
```
Logset per application/environment:
- myapp-prod-logset
- myapp-staging-logset
- myapp-dev-logset
```

### Topic (日志主题)

| Attribute | Description | Limits |
|-----------|-------------|--------|
| **TopicId** | Unique identifier | System generated |
| **TopicName** | Human-readable name | 1-63 characters |
| **LogsetId** | Parent logset | Required |
| **PartitionCount** | Write partitions | 1-50, default 1 |
| **Storage** | Storage type | hot/cold |
| **Period** | Retention days | 1-3600 days |
| **AutoSplit** | Auto partition split | true/false |
| **MaxSplitPartitions** | Max partitions | 50 default |

**Partition Strategy:**
| Scenario | Partition Count | Reason |
|----------|-----------------|--------|
| < 1000 logs/sec | 1 | Cost efficient |
| 1000-10000 logs/sec | 3-5 | Balance cost/perf |
| > 10000 logs/sec | 10+ | High throughput |
| Burst traffic | AutoSplit enabled | Handle spikes |

**Topic Naming Convention:**
```
<service>-<logtype>-<version>
Examples:
- nginx-access-v1
- app-error-v2
- mysql-slow-query-v1
```

### Index (索引规则)

| Index Type | Description | Use Case |
|------------|-------------|----------|
| **Full-Text Index** | Index entire log content | Unstructured text search |
| **Key-Value Index** | Index specific fields | Structured log analysis |
| **Metadata Index** | Index system fields | Time, source, filename |

#### Full-Text Index Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| **CaseSensitive** | Case sensitive search | false |
| **Tokenizer** | Word delimiters | `@&?|#()='<>/: "` |
| **ContainZH** | Support Chinese | true |

#### Key-Value Index Field Types

| Type | Description | Example Query |
|------|-------------|---------------|
| `text` | Full-text searchable | `level:error` |
| `long` | 64-bit integer | `status_code:200` |
| `double` | Floating point | `response_time:>1.5` |
| `json` | Nested JSON | `user.name:admin` |

**Index Best Practices:**
```
✓ Index high-cardinality fields (trace_id, request_id)
✓ Index frequently filtered fields (level, status)
✗ Avoid indexing low-cardinality fields (constant values)
✗ Avoid indexing very long text fields (>32KB)
```

### MachineGroup (机器组)

| Type | Description | Use Case |
|------|-------------|----------|
| **IP-based** | Fixed IP list | Traditional servers |
| **Label-based** | Auto-discover by label | Kubernetes, auto-scaling |

| Attribute | Description |
|-----------|-------------|
| **GroupId** | Unique identifier |
| **GroupName** | Human-readable name |
| **MachineGroupType** | IP or label based |
| **CreateTime** | Creation timestamp |
| **AgentStatus** | Agent health status |

### Config (采集配置)

| Attribute | Description | Required |
|-----------|-------------|----------|
| **ConfigId** | Unique identifier | System |
| **Name** | Configuration name | Yes |
| **Output** | Target topic ID | Yes |
| **Path** | Log file path pattern | Yes |
| **LogType** | Log format type | Yes |
| **ExtractRule** | Parsing rules | Format dependent |
| **ExcludePaths** | Files to exclude | No |

#### Log Type Support

| LogType | Description | ExtractRule Required |
|---------|-------------|---------------------|
| `minimalist_log` | Single line text | No |
| `delimiter_log` | CSV/TSV delimited | Yes |
| `json_log` | JSON format | Optional |
| `fullregex_log` | Full regex match | Yes |

#### ExtractRule Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| **TimeKey** | Timestamp field name | `timestamp` |
| **TimeFormat** | Timestamp format | `%Y-%m-%d %H:%M:%S` |
| **Delimiter** | Field delimiter (CSV) | `,` or `\t` |
| **LogRegex** | Regex pattern | `(\d+).*`
| **Keys** | Field names array | `["time","level","msg"]` |
| **FilterKeyRegex** | Filter rules | `[{"Key":"level","Regex":"ERROR"}]` |

**Time Format Specifiers:**
| Specifier | Description | Example |
|-----------|-------------|---------|
| `%Y` | 4-digit year | 2026 |
| `%m` | Month (01-12) | 05 |
| `%d` | Day (01-31) | 28 |
| `%H` | Hour (00-23) | 14 |
| `%M` | Minute (00-59) | 30 |
| `%S` | Second (00-59) | 00 |
| `%f` | Microsecond | 000000 |

## Log Collection Methods

### 1. LogListener (Log Agent)

**Deployment:**
```bash
# Install on Linux
wget https://mirrors.tencent.com/install/cls/ti-linux.sh
sh ti-linux.sh install

# Configure
/etc/loglistener.conf
```

**Capabilities:**
| Feature | Description |
|---------|-------------|
| Real-time collection | < 1 second delay |
| Local buffering | Network tolerant |
| File rotation | Handle log rotation |
| Multi-line merge | Stack traces support |
| Resource limit | CPU/memory throttling |

**Supported Platforms:**
- Linux (CentOS, Ubuntu, Debian)
- Windows Server
- Kubernetes (DaemonSet)

### 2. API/SDK Upload

| Method | Use Case | Latency |
|--------|----------|---------|
| **UploadLog** | Real-time streaming | < 100ms |
| **UploadLogByFile** | Batch upload | Seconds |

**SDK Support:**
- Python SDK
- Go SDK
- Java SDK
- JavaScript/Node.js SDK
- PHP SDK

### 3. Cloud Product Integration

| Source | Collection Method | Configuration |
|--------|-------------------|---------------|
| **CVM** | LogListener | Machine group |
| **TKE** | LogListener (DaemonSet) | Container label |
| **SCF** | Native integration | Function config |
| **CDN** | Native integration | Domain config |
| **CLB** | Native integration | Load balancer config |
| **API Gateway** | Native integration | API config |

## Storage and Retention

### Storage Types

| Type | Retention | Use Case | Cost Factor |
|------|-----------|----------|-------------|
| **Hot Storage** | 1-3600 days | Frequent query | 1.0x |
| **Cold Storage** | 7-3600 days | Archival only | 0.3x |

**Storage Transition:**
```
Hot → Cold (automatic based on age)
Cold → Hot (manual restore required)
```

### Retention Periods

| Scenario | Recommended Period | Reason |
|----------|-------------------|--------|
| Production debug | 7-30 days | Recent issues |
| Compliance audit | 180-365 days | Regulatory requirement |
| Security analysis | 90-180 days | Incident investigation |
| Cost optimization | 7 days + COS ship | Archive to COS |

### Cost Components

| Component | Billing Unit | Optimization |
|-----------|--------------|--------------|
| **Storage** | GB/day | Reduce retention, use cold storage |
| **Write traffic** | GB ingested | Compress logs, filter at source |
| **Index traffic** | GB indexed | Optimize index rules |
| **Read traffic** | GB queried | Use sampling, limit time range |
| **Analysis compute** | CU (compute unit) | Optimize SQL queries |

## Query Syntax

### Basic Search

| Syntax | Description | Example |
|--------|-------------|---------|
| `keyword` | Full-text search | `error` |
| `"phrase"` | Phrase search | `"connection refused"` |
| `field:value` | Field match | `level:ERROR` |
| `field:>value` | Range query | `status:>400` |

### Boolean Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `AND` | Both terms | `error AND timeout` |
| `OR` | Either term | `error OR warning` |
| `NOT` | Exclude | `error NOT debug` |
| `()` | Grouping | `(error OR warning) AND api` |

**Operator Precedence:**
```
() > NOT > AND > OR
```

### Wildcards

| Wildcard | Description | Example |
|----------|-------------|---------|
| `*` | Match any chars | `api.*.error` |
| `?` | Match single char | `status:5??` |

**Wildcard Limitations:**
- Cannot start with `*` or `?`
- Minimum 3 chars before wildcard
- Performance impact on large datasets

### Metadata Fields

| Field | Description | Example Query |
|-------|-------------|---------------|
| `__SOURCE__` | Source IP | `__SOURCE__:172.16.0.1` |
| `__FILENAME__` | Log file name | `__FILENAME__:access.log` |
| `__TIMESTAMP__` | Log timestamp | `__TIMESTAMP__:>1716192000` |

### SQL Analysis

```sql
-- Basic aggregation
SELECT level, COUNT(*) as count
FROM topic-id
GROUP BY level

-- Time series
SELECT HISTOGRAM(__TIMESTAMP__, INTERVAL 5 MINUTE) as time,
       COUNT(*) as count
FROM topic-id
WHERE level = 'ERROR'
GROUP BY time

-- Top N
SELECT user_id, COUNT(*) as requests
FROM topic-id
GROUP BY user_id
ORDER BY requests DESC
LIMIT 10
```

## Index Types Deep Dive

### Full-Text Index

**Tokenization Example:**
```
Log: "User login failed from 192.168.1.1"
Tokens: User, login, failed, from, 192.168.1.1
```

**When to Use:**
- Unstructured logs
- Debug messages
- Error stack traces
- User-generated content

### Key-Value Index

**Field Mapping Example:**
```json
{
  "timestamp": "2026-05-28 14:30:00",
  "level": "ERROR",
  "service": "api-gateway",
  "request_id": "abc123",
  "response_time": 1250
}
```

**Index Configuration:**
```json
{
  "KeyValue": {
    "KeyValues": [
      {"Key": "level", "Value": {"Type": "text"}},
      {"Key": "service", "Value": {"Type": "text"}},
      {"Key": "request_id", "Value": {"Type": "text"}},
      {"Key": "response_time", "Value": {"Type": "long"}}
    ]
  }
}
```

**Query Examples:**
```
level:ERROR AND service:api-gateway
response_time:>1000
request_id:abc123
```

### Metadata Index

Always indexed by default:
- `__TIMESTAMP__` - Log timestamp
- `__SOURCE__` - Source IP/hostname
- `__FILENAME__` - Source file path
- `__PKG_ID__` - Internal package ID
- `__TOPIC_ID__` - Topic identifier

## Quotas and Limits

| Resource | Default Limit | Adjustable |
|----------|---------------|------------|
| Logsets per region | 100 | Yes (max 500) |
| Topics per logset | 500 | Yes (max 1000) |
| Partitions per topic | 50 | Yes (max 100) |
| Machine groups | 100 | Yes (max 500) |
| Configs per topic | 50 | No |
| Index fields | 500 | No |
| Log size | 512KB per log | No |
| Query time range | 31 days | No |
| Query result limit | 1,000,000 | No |

## References

- [CLS Product Documentation](https://cloud.tencent.com/document/product/614)
- [LogListener Installation](https://cloud.tencent.com/document/product/614/17414)
- [Index Configuration](https://cloud.tencent.com/document/product/614/50925)
- [Search Syntax](https://cloud.tencent.com/document/product/614/47044)
- [SQL Analysis](https://cloud.tencent.com/document/product/614/58981)
- [Pricing](https://cloud.tencent.com/document/product/614/54218)
