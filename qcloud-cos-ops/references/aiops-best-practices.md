# COS AIOps Best Practices Module

## 1. Multi-Metric Correlation

### COS Correlation Patterns

| Pattern | Primary Metric | Secondary Metrics | Diagnosis |
|---------|---------------|-------------------|-----------|
| Upload bottleneck | UploadLatency | RequestCount, ErrorRate | Bandwidth limit |
| Storage growth | StorageSize | UploadCount, ObjectCount | Uncontrolled growth |
| Access pattern shift | RequestRate | StorageClass, DownloadCount | Hot/Cold data shift |

### Correlation Implementation

```python
import numpy as np

def correlate_cos_metrics(metrics: dict) -> dict:
    upload_latency = metrics.get('UploadLatency', [])
    request_count = metrics.get('RequestCount', [])
    
    if len(upload_latency) > 0 and len(request_count) > 0:
        correlation = np.corrcoef(upload_latency, request_count)[0, 1]
        
        return {
            'upload_request': {
                'value': correlation,
                'interpretation': interpret_correlation(correlation)
            }
        }

def interpret_correlation(value: float) -> str:
    if value > 0.7:
        return 'Upload latency increases with request count - bandwidth limit'
    elif value < -0.3:
        return 'Inverse correlation - unexpected pattern'
    else:
        return 'No significant correlation'
```

## 2. Cross-Skill Diagnosis Decision Tree

### COS Diagnosis Tree

```yaml
cos_diagnosis_tree:
  branches:
    - condition: "issue == 'upload_failure'"
      diagnosis: upload_issue
      sub_branches:
        - condition: "error_code == EntityTooLarge"
          diagnosis: multipart_needed
          actions: [use_multipart_upload]
        
        - condition: "error_code == AccessDenied"
          diagnosis: acl_issue
          actions: [check_bucket_acl, check_policy]
        
        - condition: "error_code == RequestTimeout"
          diagnosis: network_issue
          delegate: qcloud-vpc-ops
    
    - condition: "issue == 'download_slow'"
      diagnosis: download_performance
      sub_branches:
        - condition: "cdn_enabled == false"
          diagnosis: no_cdn
          delegate: qcloud-cdn-ops
        
        - condition: "storage_class == ARCHIVE"
          diagnosis: archive_retrieval
          actions: [restore_object_first]
```

## 3. Delegation Matrix

### COS Delegation Matrix

| Issue Type | Delegate To | Context |
|------------|-------------|---------|
| CDN performance | qcloud-cdn-ops | Bucket endpoint, CDN domain |
| Network issue | qcloud-vpc-ops | VPC ID, region |
| MySQL backup | qcloud-cdb-ops | Backup bucket, DB instance |

## 4. Proactive Inspection

### COS Inspection Schedule

| Category | Frequency | Checks |
|----------|-----------|--------|
| Daily | 24h | Bucket ACL, error rate |
| Weekly | 7d | Storage growth, lifecycle rules |
| Monthly | 30d | Cost analysis, class optimization |

### Proactive Alert Rules

```yaml
cos_alerts:
  - name: storage_growth_acceleration
    condition: "StorageSize growth_rate > 10%/week"
    severity: warning
    message: "Storage growing rapidly - review lifecycle"
  
  - name: public_bucket_exposure
    condition: "BucketACL == public-read"
    severity: critical
    message: "Bucket publicly accessible - security risk"
  
  - name: archive_retrieval_pending
    condition: "ArchiveRetrievalCount > 0"
    severity: info
    message: "Archive objects being retrieved - check access pattern"
```

## 5. Alarm Storm Handling

### COS Alarm Storm Detection

```python
from datetime import datetime, timedelta

def detect_cos_alarm_storm(alarm_events: list) -> dict:
    recent = [a for a in alarm_events if a['timestamp'] > datetime.now() - timedelta(minutes=5)]
    
    cos_alarms = [a for a in recent if 'cos' in a['resource_type'].lower()]
    
    if len(cos_alarms) > 10:
        return {
            'storm': True,
            'count': len(cos_alarms),
            'types': set(a['alarm_type'] for a in cos_alarms)
        }
    
    return {'storm': False}
```

## AIOps Compliance Checklist

| Requirement | Status | Location |
|-------------|--------|----------|
| Multi-metric correlation | ✓ | references/aiops-best-practices.md |
| Diagnosis decision tree | ✓ | references/aiops-best-practices.md |
| Delegation matrix | ✓ | SKILL.md Trigger & Scope |
| Proactive inspection | ✓ | references/aiops-best-practices.md |
| Alarm storm handling | ✓ | references/aiops-best-practices.md |

## References

- [AIOps Best Practices](../qcloud-skill-generator/references/aiops-best-practices.md)