# CLB Troubleshooting Guide

## Common Issues and Solutions

### Health Check Failures

**Symptom:** Backend servers marked unhealthy despite running

**Diagnostic Steps:**
1. Check health check configuration
```bash
tccli clb DescribeListeners --LoadBalancerId lb-xxx | jq '.Response.ListenerSet[0].HealthCheck'
```
2. Verify backend port is open
```bash
# Check if backend port responds
curl -v http://<backend-ip>:<port>/health-check-path
```
3. Check security group rules
```bash
tccli vpc DescribeSecurityGroups --SecurityGroupIds "[\"sg-xxx\"]"
```

**Root Causes:**
| Cause | Resolution |
|-------|------------|
| Port mismatch | Update backend port in RegisterTargets |
| Security group blocks CLB VIP | Add CLB VIP to allowed sources |
| Health check path invalid | Update path in listener config |
| Backend timeout | Increase health check timeout |

### Connection Failures

**Symptom:** Clients cannot reach backend via CLB VIP

**Diagnostic Steps:**
1. Verify CLB status
```bash
tccli clb DescribeLoadBalancers --LoadBalancerIds "[\"lb-xxx\"]" | jq '.Response.LoadBalancerSet[0].Status'
```
2. Check listener configuration
```bash
tccli clb DescribeListeners --LoadBalancerId lb-xxx
```
3. Verify backend binding
```bash
tccli clb DescribeTargets --LoadBalancerId lb-xxx
```

**Root Causes:**
| Cause | Resolution |
|-------|------------|
| LB not running | Wait for LB creation completion |
| Listener not created | Create listener with correct protocol/port |
| Backend not registered | Register targets via RegisterTargets |
| Weight set to 0 | Modify target weight |

### SSL Certificate Issues

**Symptom:** HTTPS listener fails or clients get certificate errors

**Diagnostic Steps:**
1. Verify certificate ID
```bash
tccli ssl DescribeCertificates --CertificateIds "[\"cert-xxx\"]"
```
2. Check certificate expiration
```bash
# Get certificate expiry date
```

**Root Causes:**
| Cause | Resolution |
|-------|------------|
| Certificate expired | Renew and update listener |
| Certificate domain mismatch | Use correct domain certificate |
| Certificate not deployed | Deploy to CLB region |

### Traffic Distribution Issues

**Symptom:** Traffic not evenly distributed to backends

**Diagnostic Steps:**
1. Check backend weights
```bash
tccli clb DescribeTargets --LoadBalancerId lb-xxx | jq '.Response.Targets[].Weight'
```
2. Verify health status
```bash
tccli clb DescribeTargetHealth --LoadBalancerId lb-xxx
```

**Root Causes:**
| Cause | Resolution |
|-------|------------|
| Weight imbalance | Adjust weights via ModifyTargetWeight |
| Some backends unhealthy | Fix health check issues |
| Session persistence enabled | Disable or configure correctly |

### Cross-VPC Binding Failures

**Symptom:** Cannot bind CVM from different VPC

**Diagnostic Steps:**
1. Verify VPC configuration
```bash
tccli vpc DescribeVpcs --VpcIds "[\"vpc-xxx\"]"
```

**Root Causes:**
| Cause | Resolution |
|-------|------------|
| CVM in different VPC | Use CVM in same VPC or cross-region binding |
| Subnet mismatch | Ensure subnet in correct VPC |

## Error Code Reference

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter.LBIdNotFound` | LB ID incorrect | Verify via DescribeLoadBalancers |
| `InvalidParameter.ListenerIdNotFound` | Listener ID incorrect | Verify via DescribeListeners |
| `InvalidParameter.PortCheckFailed` | Port conflict | Use different port or delete conflicting listener |
| `InvalidParameter.ProtocolCheckFailed` | Protocol mismatch | Check protocol support per operation |
| `FailedOperation.InvalidLBStatus` | LB not in running state | Wait for LB to stabilize |
| `FailedOperation.ResourceInOperating` | Concurrent operation | Wait and retry |
| `FailedOperation.TrafficCheckRisk` | High traffic LB deletion | Confirm force delete or wait |

