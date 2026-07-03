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
| Target CVM creation | `qcloud-cvm-ops` |
| Target VPC setup | `qcloud-vpc-ops` |
| Target database setup | `qcloud-cdb-ops` / `qcloud-postgres-ops` |
| Post-migration validation | Product-specific ops skills |
| Application deployment | `qcloud-cicd-ops` |
| Monitoring setup | `qcloud-monitor-ops` |

## Migration Workflow Example

```python
#!/usr/bin/env python3
"""
Example: Complete migration workflow with delegation
"""
import os
from tencentcloud.common import credential

# 1. Pre-migration: Create target infrastructure
#    Delegate to: qcloud-vpc-ops, qcloud-cvm-ops

# 2. Register migration task (this skill)
#    - RegisterMigrationTask
#    - Monitor progress

# 3. Post-migration validation
#    Delegate to: qcloud-cvm-ops (DescribeInstances)
#                qcloud-monitor-ops (setup monitoring)

# 4. Application deployment
#    Delegate to: qcloud-cicd-ops
```

## Best Practices

1. **Phased Approach**: Migrate non-critical workloads first
2. **Testing**: Validate each phase before proceeding
3. **Communication**: Keep stakeholders informed of progress
4. **Documentation**: Document all configuration changes
