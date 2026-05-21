# Monitor API & SDK Usage

## Overview

API operation map and Python SDK usage for Monitor (云监控).

---

## API Operation Map

### Alarm Policy Operations

| API | Description | Required Parameters | Rate Limit |
|-----|-------------|---------------------|------------|
| `CreateAlarmPolicy` | Create policy | Module, PolicyName, Namespace, Conditions | 20/s |
| `DescribeAlarmPolicies` | Query policies | Module | 20/s |
| `DescribeAlarmPolicy` | Get policy detail | Module, PolicyId | 60/s |
| `ModifyAlarmPolicyInfo` | Modify policy name | Module, PolicyId, PolicyName | 20/s |
| `ModifyAlarmPolicyCondition` | Modify conditions | Module, PolicyId, Conditions | 20/s |
| `ModifyAlarmPolicyStatus` | Enable/disable | Module, PolicyId, Status | 20/s |
| `DeleteAlarmPolicy` | Delete policy | Module, PolicyIds | 20/s |

### Binding Operations

| API | Description | Required Parameters | Rate Limit |
|-----|-------------|---------------------|------------|
| `BindingPolicyObject` | Bind to resources | Module, PolicyId, Dimensions | 20/s |
| `UnBindingPolicyObject` | Unbind resource | Module, PolicyId, Dimensions | 20/s |
| `UnBindingAllPolicyObject` | Remove all bindings | Module, PolicyId | 20/s |
| `DescribeBindingPolicyObjectList` | Query bindings | Module, PolicyId | 20/s |

### Metric Operations

| API | Description | Required Parameters | Rate Limit |
|-----|-------------|---------------------|------------|
| `GetMonitorData` | Query metric data | Namespace, MetricName, Dimensions | 20/s |
| `DescribeAlarmMetrics` | List metrics | Module, Namespace | 20/s |
| `DescribeAlarmEvents` | List events | Module, Namespace | 20/s |
| `DescribeAllNamespaces` | List namespaces | Module | 20/s |

### History Operations

| API | Description | Required Parameters | Rate Limit |
|-----|-------------|---------------------|------------|
| `DescribeAlarmHistories` | Query history | Module, StartTime, EndTime | 20/s |
| `DescribeAlarmNotifyHistories` | Notification history | Module | 20/s |

---

## Request/Response Schemas

### CreateAlarmPolicy

**Request:**
```json
{
  "Module": "monitor",
  "PolicyName": "high-cpu-alert",
  "Namespace": "QCE/CVM",
  "Conditions": [
    {
      "CalcType": "Greater",
      "CalcValue": "80",
      "ContinueTime": 60,
      "MetricName": "CPUUsage"
    }
  ],
  "EventConditions": [],
  "NoticeIds": ["notice-xxx"],
  "OriginId": 0
}
```

**Response:**
```json
{
  "Response": {
    "PolicyId": "policy-abc123",
    "RequestId": "req-xxx"
  }
}
```

### GetMonitorData

**Request:**
```json
{
  "Namespace": "QCE/CVM",
  "MetricName": "CPUUsage",
  "Dimensions": [
    {"Name": "InstanceId", "Value": "ins-xxx"}
  ],
  "StartTime": "2026-05-20T00:00:00+08:00",
  "EndTime": "2026-05-21T00:00:00+08:00",
  "Period": 300
}
```

**Response:**
```json
{
  "Response": {
    "MetricDataPoints": [
      {
        "Values": [45.2, 48.1, 52.3, ...],
        "Timestamps": [1716163200, 1716163500, ...]
      }
    ],
    "RequestId": "req-xxx"
  }
}
```

---

## Python SDK Usage

### Setup

```bash
pip install tencentcloud-sdk-python-monitor
```

### Client Initialization

```python
import os
from tencentcloud.common import credential
from tencentcloud.monitor.v20180317 import monitor_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)

client = monitor_client.MonitorClient(cred, "")
```

### Create Alarm Policy

```python
def create_alarm_policy(client, name, namespace, metric, threshold, duration=60):
    """Create alarm policy"""
    req = models.CreateAlarmPolicyRequest()
    req.Module = "monitor"
    req.PolicyName = name
    req.Namespace = namespace
    
    req.Conditions = [
        {
            "CalcType": "Greater",
            "CalcValue": threshold,
            "ContinueTime": duration,
            "MetricName": metric
        }
    ]
    
    resp = client.CreateAlarmPolicy(req)
    return resp.PolicyId

# Usage
policy_id = create_alarm_policy(
    client,
    "cpu-over-80",
    "QCE/CVM",
    "CPUUsage",
    "80"
)
```

### Get Monitor Data

```python
def get_monitor_data(client, namespace, metric, instance_id, start_time, end_time):
    """Query metric data"""
    req = models.GetMonitorDataRequest()
    req.Namespace = namespace
    req.MetricName = metric
    req.Dimensions = [{"Name": "InstanceId", "Value": instance_id}]
    req.StartTime = start_time
    req.EndTime = end_time
    req.Period = 300
    
    resp = client.GetMonitorData(req)
    
    return {
        "values": resp.MetricDataPoints[0].Values,
        "timestamps": resp.MetricDataPoints[0].Timestamps
    }
```

### Bind Policy to Object

```python
def bind_policy_to_instance(client, policy_id, instance_id):
    """Bind alarm policy to instance"""
    req = models.BindingPolicyObjectRequest()
    req.Module = "monitor"
    req.PolicyId = policy_id
    req.Dimensions = [
        {
            "Key": "InstanceId",
            "Value": instance_id
        }
    ]
    
    resp = client.BindingPolicyObject(req)
    return resp.RequestId
```

---

## Common Metric Namespaces

| Namespace | Product | Common Metrics |
|-----------|---------|----------------|
| `QCE/CVM` | CVM | CPUUsage, MemUsage, DiskUsage |
| `QCE/LB_PUBLIC` | CLB | ClientConnum, TrafficOut |
| `QCE/CDB` | MySQL | CpuUseRate, MemoryUseRate |
| `QCE/REDIS` | Redis | CmdExecuteCount, CacheHitRate |
| `QCE/VPC` | VPC | VpcFlowMetric |
| `QCE/CBS` | CBS | DiskUsage, DiskReadIops |

---

## Condition Types

| CalcType | Meaning | Example |
|----------|---------|---------|
| `Greater` | > threshold | CPUUsage > 80 |
| `Less` | < threshold | CacheHitRate < 50 |
| `Equal` | = threshold | Status = 0 |
| `GreaterOrEqual` | >= threshold | DiskUsage >= 90 |
| `LessOrEqual` | <= threshold | AvailableMemory <= 100 |