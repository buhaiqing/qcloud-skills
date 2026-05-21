# Monitor CLI Usage

## Overview

`tccli monitor` commands for Cloud Monitoring operations. CLI is **primary execution path** per `cli_applicability: dual-path`.

## Prerequisites

```bash
pip install tccli
export TENCENTCLOUD_SECRET_ID="your-secret-id"
export TENCENTCLOUD_SECRET_KEY="your-secret-key"
export TENCENTCLOUD_REGION="ap-guangzhou"
```

## Alarm Policy Commands

```bash
# Create alarm policy
tccli monitor CreateAlarmPolicy \
  --Module "monitor" \
  --PolicyName "my-cpu-alert" \
  --Namespace "QCE/CVM" \
  --Conditions "[{\"CalcType\":\"Greater\",\"CalcValue\":\"80\",\"ContinueTime\":60,\"MetricName\":\"CPUUsage\"}]"

# Describe alarm policies
tccli monitor DescribeAlarmPolicies \
  --Module "monitor" \
  --Namespace "QCE/CVM"

# Get specific policy
tccli monitor DescribeAlarmPolicy \
  --Module "monitor" \
  --PolicyId "policy-xxx"

# Enable/disable policy
tccli monitor ModifyAlarmPolicyStatus \
  --Module "monitor" \
  --PolicyId "policy-xxx" \
  --Status "OPEN"  # or "CLOSED"

# Delete alarm policy
tccli monitor DeleteAlarmPolicy \
  --Module "monitor" \
  --PolicyIds "[\"policy-xxx\"]"

# Modify policy info
tccli monitor ModifyAlarmPolicyInfo \
  --Module "monitor" \
  --PolicyId "policy-xxx" \
  --PolicyName "updated-name"

# Modify policy conditions
tccli monitor ModifyAlarmPolicyCondition \
  --Module "monitor" \
  --PolicyId "policy-xxx" \
  --Conditions "[{\"CalcType\":\"Greater\",\"CalcValue\":\"90\",\"ContinueTime\":300,\"MetricName\":\"CPUUsage\"}]"

# Bind policy to objects
tccli monitor BindingPolicyObject \
  --Module "monitor" \
  --PolicyId "policy-xxx" \
  --Dimensions "[{\"Key\":\"InstanceId\",\"Value\":\"ins-xxx\"}]"

# Unbind policy objects
tccli monitor UnBindingPolicyObject \
  --Module "monitor" \
  --PolicyId "policy-xxx" \
  --Dimensions "[{\"Key\":\"InstanceId\",\"Value\":\"ins-xxx\"}]"
```

## Metric Query Commands

```bash
# Get monitor data
tccli monitor GetMonitorData \
  --Namespace "QCE/CVM" \
  --MetricName "CPUUsage" \
  --Dimensions "[{\"Name\":\"InstanceId\",\"Value\":\"ins-xxx\"}]" \
  --StartTime "2026-05-20T00:00:00+08:00" \
  --EndTime "2026-05-21T00:00:00+08:00" \
  --Period 300

# Describe all namespaces
tccli monitor DescribeAllNamespaces \
  --Module "monitor"

# Describe alarm metrics
tccli monitor DescribeAlarmMetrics \
  --Module "monitor" \
  --Namespace "QCE/CVM"

# Describe alarm events
tccli monitor DescribeAlarmEvents \
  --Module "monitor" \
  --Namespace "QCE/CVM"
```

## Alarm History Commands

```bash
# Query alarm history
tccli monitor DescribeAlarmHistories \
  --Module "monitor" \
  --StartTime "2026-05-01" \
  --EndTime "2026-05-21"

# Query notification history
tccli monitor DescribeAlarmNotifyHistories \
  --Module "monitor"
```

## Notification Template Commands

```bash
# Create notification template
tccli monitor CreateAlarmNotice \
  --Module "monitor" \
  --NoticeName "my-notice"

# Describe notification templates
tccli monitor DescribeAlarmNotices \
  --Module "monitor"

# Modify notification template
tccli monitor ModifyAlarmNotice \
  --Module "monitor" \
  --NoticeId "notice-xxx" \
  --NoticeName "updated-name"

# Delete notification templates
tccli monitor DeleteAlarmNotices \
  --Module "monitor" \
  --NoticeIds "[\"notice-xxx\"]"
```

## JSON Output Parsing

```bash
# Get policy ID
POLICY_ID=$(tccli monitor CreateAlarmPolicy ... | jq -r '.Response.PolicyId')

# Get metric values
VALUES=$(tccli monitor GetMonitorData ... | jq -r '.Response.MetricDataPoints[0].Values')

# Check alarm status
STATUS=$(tccli monitor DescribeAlarmHistories ... | jq -r '.Response.Histories[0].AlarmStatus')
```

## Rate Limits

| API | Limit |
|-----|-------|
| CreateAlarmPolicy | 20/s |
| DescribeAlarmPolicies | 20/s |
| DeleteAlarmPolicy | 20/s |
| GetMonitorData | 20/s |

## Common Patterns

### Bulk Metric Query
```bash
# Query multiple instances
for ins in ins-1 ins-2 ins-3; do
  tccli monitor GetMonitorData \
    --Namespace "QCE/CVM" \
    --MetricName "CPUUsage" \
    --Dimensions "[{\"Name\":\"InstanceId\",\"Value\":\"$ins\"}]"
done
```

### Policy Template Reuse
```bash
# Create similar policies for different thresholds
for threshold in 70 80 90; do
  tccli monitor CreateAlarmPolicy \
    --PolicyName "cpu-alert-$threshold" \
    --Namespace "QCE/CVM" \
    --Conditions "[{\"CalcType\":\"Greater\",\"CalcValue\":\"$threshold\",\"ContinueTime\":60,\"MetricName\":\"CPUUsage\"}]"
done
```