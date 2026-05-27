# CLB Integration

## Overview

SDK setup, environment configuration, and cross-skill integration for CLB.

---

## Environment Setup

### Required Environment Variables

```bash
export TENCENTCLOUD_SECRET_ID="your-secret-id"
export TENCENTCLOUD_SECRET_KEY="your-secret-key"  # NEVER print this value
export TENCENTCLOUD_REGION="ap-guangzhou"
```

### Python SDK Installation

```bash
# Install SDK
pip install tencentcloud-sdk-python-clb

# Verify installation
python -c "from tencentcloud.clb.v20180317 import clb_client; print('✅ CLB SDK installed')"
```

### CLI Installation

```bash
# Install tccli
pip install tccli

# Verify CLI
tccli clb help
```

---

## Cross-Skill Integration

### Dependencies

| Dependency | Skill | Integration Point |
|------------|-------|-------------------|
| VPC/Subnet | `qcloud-vpc-ops` | Required before CreateLoadBalancer |
| Backend CVM | `qcloud-cvm-ops` | Required before RegisterTargets |
| Security Groups | `qcloud-vpc-ops` | Optional for LB security |
| SSL Certificates | `qcloud-ssl-ops` | Required for HTTPS listeners |
| Monitoring | `qcloud-monitor-ops` | CLB metrics namespace |

### Integration Flow

```yaml
clb_integration_flow:
  step_1_vpc:
    skill: qcloud-vpc-ops
    action: verify_vpc_exists
    output: vpc_id, subnet_id
    
  step_2_clb:
    skill: qcloud-clb-ops
    action: CreateLoadBalancer
    input: vpc_id, subnet_id
    output: loadbalancer_id
    
  step_3_cvm:
    skill: qcloud-cvm-ops
    action: verify_instances_running
    output: instance_ids
    
  step_4_listener:
    skill: qcloud-clb-ops
    action: CreateListener
    input: loadbalancer_id
    
  step_5_register:
    skill: qcloud-clb-ops
    action: RegisterTargets
    input: loadbalancer_id, listener_id, instance_ids
```

---

## Delegation Rules

### From CLB to Other Skills

```markdown
## Delegation Protocol

### CLB → VPC

When CreateLoadBalancer fails with VPC error:

```
Error: InvalidParameter.VpcNotFound
Resolution: Delegate to qcloud-vpc-ops
Action: Create VPC or verify VPC ID
```

### CLB → CVM

When RegisterTargets fails or backend unhealthy:

```
Trigger: HealthCheckFailedNum > 0
Delegate: qcloud-cvm-ops
Context:
  - InstanceId: [ins-xxx]
  - Issue: Backend health check failed
  - Port: [8080]
  
CVM Action:
  - Check instance status
  - Check port binding
  - Check security group
```

### CLB → Monitor

For CLB monitoring setup:

```
Delegate: qcloud-monitor-ops
Namespace: QCE/LB_PUBLIC
Dimension: LoadBalancerId
Metrics: ClientConnum, TrafficOut, HealthStatus
```
```

---

## Authentication

### CAM Roles

Recommended: Use CAM role instead of static credentials for production.

```yaml
# For CVM instances needing CLB API access
cam_role:
  name: "CLB-Operator"
  policies:
    - clb:Describe*
    - clb:RegisterTargets
    - clb:DeregisterTargets
```

---

## Best Practices

### Credential Security

| Practice | Implementation |
|----------|----------------|
| Never log SecretKey | Mask in all outputs |
| Use environment variables | Never hardcode |
| CAM role preferred | Over static keys |
| Rotate credentials | Every 90 days |

### API Rate Limiting

| API | Rate Limit | Retry Strategy |
|-----|------------|----------------|
| DescribeLoadBalancers | 20/s | Exponential backoff |
| CreateLoadBalancer | 20/s | Backoff 2s, 4s, 8s |
| RegisterTargets | 20/s | Batch reduce calls |

---

## Error Recovery Integration

### Cross-Skill Error Handling

```python
def handle_clb_error_with_delegation(error_code: str, context: Dict) -> Dict:
    # Handle CLB errors with skill delegation
    
    delegation_map = {
        'InvalidParameter.VpcNotFound': {
            'delegate': 'qcloud-vpc-ops',
            'action': 'verify_vpc'
        },
        'InvalidParameter.InstanceNotFound': {
            'delegate': 'qcloud-cvm-ops',
            'action': 'verify_instance'
        },
        'FailedOperation.InvalidLBStatus': {
            'self_handle': True,
            'action': 'wait_and_retry'
        }
    }
    
    if error_code in delegation_map:
        delegation = delegation_map[error_code]
        
        if delegation.get('self_handle'):
            # Handle within CLB skill
            return self_recovery(delegation['action'], context)
        else:
            # Delegate to target skill
            return invoke_skill(
                delegation['delegate'],
                delegation['action'],
                context
            )
    
    return {'error': 'unhandled', 'code': error_code}
```