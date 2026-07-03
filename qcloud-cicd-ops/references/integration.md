# Integration Guide

## SDK Setup

```bash
pip install tencentcloud-sdk-python
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TENCENTCLOUD_SECRET_ID` | Yes | API Secret ID |
| `TENCENTCLOUD_SECRET_KEY` | Yes | API Secret Key |
| `TENCENTCLOUD_REGION` | Yes | Region (e.g., ap-guangzhou) |

## Cross-Skill Delegation

| Scenario | Delegate To |
|----------|------------|
| K8s deployment | `qcloud-tke-ops` |
| SCF function deploy | `qcloud-scf-ops` |
| Pipeline monitoring | `qcloud-monitor-ops` |
| Cost tracking | `qcloud-finops-ops` |
| VPC/network config | `qcloud-vpc-ops` |

## CI/CD Pipeline Integration Example

```python
#!/usr/bin/env python3
"""
Example: Pipeline that deploys to multiple targets
"""
import os
from tencentcloud.common import credential

# 1. CI/CD pipeline operations (this skill)
# - Create/trigger pipeline
# - Run build and tests

# 2. Delegate to product-specific skills for deployment:
# - TKE deployment -> use qcloud-tke-ops
# - SCF deployment -> use qcloud-scf-ops
# - COS upload -> use qcloud-cos-ops
```

## Best Practices

1. **Idempotency**: Design pipelines to be safely retryable
2. **Secrets Management**: Never log credentials
3. **Error Handling**: Implement proper error handling at each stage
4. **Notification**: Set up alerts for pipeline failures
