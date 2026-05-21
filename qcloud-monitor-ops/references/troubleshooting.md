# Monitor Troubleshooting Guide

## Common Issues

### Alarm Policy Not Triggering

**Symptom:** Threshold exceeded but no alert received

**Diagnostic Steps:**
1. Check policy status
```bash
tccli monitor DescribeAlarmPolicy --Module monitor --PolicyId policy-xxx | jq '.Response.Status'
```
2. Verify binding objects
```bash
tccli monitor DescribeBindingPolicyObjectList --Module monitor --PolicyId policy-xxx
```
3. Check notification template
```bash
tccli monitor DescribeAlarmNotice --Module monitor --NoticeId notice-xxx
```

**Root Causes:**
| Cause | Resolution |
|-------|------------|
| Policy disabled | Enable via ModifyAlarmPolicyStatus |
| Not bound to resource | Bind via BindingPolicyObject |
| Notification template missing | Create and bind template |
| Threshold never met | Review condition configuration |

### Metric Query Returns Empty

**Symptom:** GetMonitorData returns no data points

**Diagnostic Steps:**
1. Verify namespace
```bash
tccli monitor DescribeAllNamespaces --Module monitor
```
2. Check dimension value
```bash
# Verify resource ID exists
tccli monitor DescribeAlarmMetrics --Module monitor --Namespace QCE/CVM
```

**Root Causes:**
| Cause | Resolution |
|-------|------------|
| Wrong namespace | Use correct namespace for product |
| Dimension value invalid | Verify resource ID exists |
| Time range too narrow | Expand time range |
| Metric not collected yet | Wait for collection interval |

### Notification Not Delivered

**Symptom:** Alarm triggered but notification not received

**Diagnostic Steps:**
1. Check notification history
```bash
tccli monitor DescribeAlarmNotifyHistories --Module monitor
```
2. Verify contact information

**Root Causes:**
| Cause | Resolution |
|-------|------------|
| Contact info outdated | Update notification template |
| Webhook URL invalid | Test webhook endpoint |
| SMS quota exceeded | Contact support |
| Email blocked | Check spam folder |

## Error Codes

| Code | Diagnosis | Resolution |
|------|-----------|------------|
| `FailedOperation.AlertPolicyCreateFailed` | Policy creation failed | Check parameter validity |
| `FailedOperation.AlertPolicyDeleteFailed` | Policy deletion failed | Check policy bindings |
| `FailedOperation.DbQueryFailed` | Database error | Retry operation |
| `FailedOperation.DataQueryFailed` | Data query error | Reduce query scope |
| `FailedOperation.AccessSTSFail` | STS token issue | Check CAM permissions |
| `InvalidParameter.ParamError` | Invalid parameters | Validate all inputs |
| `LimitExceeded.MetricQuotaExceeded` | Metric quota limit | Delete unused policies |
| `UnauthorizedOperation.CamNoAuth` | No CAM permission | Grant monitor permissions |

## Diagnostic Flowchart

```
Alarm Issue
├── Not Triggering?
│   ├── Check Policy Status → Disabled? → Enable
│   ├── Check Binding → Not bound? → Bind objects
│   ├── Check Conditions → Threshold unreachable? → Adjust
│   └── Check Notification → Template missing? → Create
│
├── No Metric Data?
│   ├── Check Namespace → Wrong? → Use correct namespace
│   ├── Check Dimension → Invalid value? -> Verify resource
│   └── Check Time Range → Too narrow? → Expand range
│
└── Notification Not Sent?
    ├── Check History → No history? → Check trigger
    ├── Check Template → Missing channels? → Configure
    └── Check Contacts → Invalid? → Update
```