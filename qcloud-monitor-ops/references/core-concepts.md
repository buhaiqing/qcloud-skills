# Monitor Core Concepts

## Overview

Tencent Cloud Observability Platform (TCOP, 腾讯云可观测平台) provides unified monitoring across metrics, traces, logs, and events for operational efficiency.

## Key Components

### Alarm Policy (告警策略)
- Defines trigger conditions for metrics/events
- Bound to notification templates
- Applied to specific resources via binding

### Metric (指标)
- Time-series data representing resource state
- Organized by namespace (product-specific)
- Dimensions identify specific resource instances

### Namespace (命名空间)
- Product-specific metric grouping
- Examples: QCE/CVM, QCE/LB_PUBLIC, QCE/CDB
- Each namespace has unique metric definitions

### Dimension (维度)
- Metric identifier attributes
- Common: InstanceId, LoadBalancerId, DiskId
- Enables querying specific resource metrics

### Notification Template (通知模板)
- Alert delivery configuration
- Channels: SMS, email, webhook, WeChat
- Threshold escalation rules

### Dashboard (仪表盘)
- Visual metric aggregation
- Custom graphs and widgets
- Cross-resource comparison

## Metric Namespaces

| Namespace | Product | Key Metrics |
|-----------|---------|-------------|
| `QCE/CVM` | Cloud Virtual Machine | CPUUsage, MemUsage, DiskUsage |
| `QCE/LB_PUBLIC` | Load Balancer (Public) | ClientConnum, TrafficOut, HealthStatus |
| `QCE/CDB` | Cloud Database MySQL | CpuUseRate, MemoryUseRate, SlowQuery |
| `QCE/REDIS` | Cloud Redis | CmdExecuteCount, CacheHitRate |
| `QCE/VPC` | Virtual Private Cloud | VpcFlowMetric, EipTraffic |
| `QCE/CBS` | Cloud Block Storage | DiskUsage, DiskReadIops |

## Alarm Policy Structure

```
Alarm Policy
├── PolicyName
├── Namespace (QCE/CVM, etc.)
├── Conditions
│   ├── MetricName
│   ├── CalcType (Greater/Less/Equal)
│   ├── CalcValue (threshold)
│   └── ContinueTime (duration)
├── EventConditions (optional)
├── NoticeIds (notification templates)
└── BindingObjects (target resources)
```

## Alert Workflow

1. **Metric Collection** → Collect data at configured interval
2. **Condition Evaluation** → Check threshold vs collected value
3. **Alarm Trigger** → Fire alert when threshold exceeded
4. **Notification Delivery** → Send via configured channels
5. **Alarm History** → Record in history table

## Threshold Types

| Type | Operator | Use Case |
|------|----------|----------|
| Greater | > | CPU, memory usage alerts |
| Less | < | Available capacity, hit rate |
| Equal | = | Specific state detection |
| GreaterOrEqual | >= | Critical thresholds |
| LessOrEqual | <= | Minimum requirements |

## Notification Channels

| Channel | Speed | Best For |
|---------|-------|----------|
| SMS | Instant | Critical alerts, emergencies |
| Email | Fast | Detailed reports, batch alerts |
| WeChat Work | Instant | Team notifications |
| Webhook | Fast | Automation integration |
| Voice Call | Real-time | Critical system alerts |

## Limits and Quotas

| Resource | Default Limit |
|----------|---------------|
| Alarm policies per account | 100 |
| Metrics per policy | 5 |
| Notification templates | 50 |
| Dashboard widgets | 30 |

## AIOps Patterns

### Multi-Metric Correlation
Analyze multiple related metrics together:
- CVM: CPUUsage + MemUsage + DiskUsage + NetworkTraffic
- CLB: ClientConnum + TrafficOut + HealthStatus

### Alarm Storm Handling
When >50 alarms trigger in 5 minutes:
1. Aggregate by root cause
2. Suppress duplicates
3. Prioritize critical alerts

### Proactive Inspection
Scheduled metric analysis before issues:
- Trend prediction
- Threshold proximity alerts
- Historical comparison

## Integration Matrix

| Service | Integration |
|---------|-------------|
| CVM | Instance metrics |
| CLB | Listener metrics |
| MySQL | Database metrics |
| Redis | Cache metrics |
| VPC | Network metrics |
| SCF | Function metrics |

## Query Parameters

```yaml
GetMonitorData:
  Namespace: QCE/CVM
  MetricName: CPUUsage
  Dimensions:
    - Name: InstanceId
      Value: ins-xxx
  StartTime: 2026-05-20T00:00:00+08:00
  EndTime: 2026-05-21T00:00:00+08:00
  Period: 300  # seconds
```

## Monitoring Architecture

```
Data Collection Layer
├── CVM Agent → QCE/CVM metrics
├── CLB Probe → QCE/LB_PUBLIC metrics
├── DB Monitor → QCE/CDB metrics
│
Processing Layer
├── Metric Aggregation
├── Threshold Evaluation
├── Alarm Engine
│
Delivery Layer
├── Notification Gateway
├── Dashboard Service
├── History Storage
```