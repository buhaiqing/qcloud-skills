# CLB Troubleshooting Guide

## Quick Diagnosis: 5xx Errors (MTTR < 30 min)

> **When `HttpCode5XX` alarm fires**, use the fast diagnosis path below instead of general troubleshooting.

### Fast Triage (2 min)

1. **Query 5xx metric trend + backend health in parallel:**

```bash
# 5xx trend (last 15 min)
# Cross-platform: macOS uses date -v-15M, Linux uses date -d '-15 minutes'
START_TIME=$(date -u -v-15M +%Y-%m-%dT%H:%M:%S+00:00 2>/dev/null || date -u -d '-15 minutes' +%Y-%m-%dT%H:%M:%S+00:00)
tccli monitor GetMonitorData \
  --Namespace "QCE/LB_PUBLIC" \
  --MetricName "HttpCode5XX" \
  --Dimensions "[{\"Name\":\"LoadBalancerId\",\"Value\":\"{{user.loadbalancer_id}}\"}]" \
  --Period 60 \
  --StartTime "$START_TIME" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"

# Backend health status
tccli clb DescribeTargetHealth \
  --LoadBalancerId "{{user.loadbalancer_id}}"
```

2. **Route by condition:**

| 5xx + HealthCheckFailedNum > 0 | Route to: [Health Check Failures](#health-check-failures) |
|---|---|
| 5xx + ClientConnum spike + health OK | Route to: [Traffic Overload](#traffic-overload) |
| 5xx + LB Status != 2 | Route to: [LB Not Running](#lb-not-running) |
| 5xx + all backends healthy | Route to: [Backend Application Error](#backend-application-error) |

3. **Detailed decision tree:** See [SLB 5xx Fast Diagnosis](slb-5xx-diagnosis-optimized.md) for the full Phase 1–4 runbook.

### Traffic Overload

**Symptom:** `HttpCode5XX` spikes with `ClientConnum` 3–10x normal, backends healthy

**Quick Fix:**
```bash
# Check current capacity
tccli clb DescribeTargets --LoadBalancerId "{{user.loadbalancer_id}}" \
  | jq '[.Response.Targets[] | {InstanceId, Weight, HealthStatus}]'

# Scale: register additional backends
tccli clb RegisterTargets \
  --LoadBalancerId "{{user.loadbalancer_id}}" \
  --ListenerId "{{user.listener_id}}" \
  --Targets "[{\"InstanceId\":\"{{user.new_instance_id}}\",\"Port\":{{user.target_port}},\"Weight\":10}]"
```

### Backend Application Error

**Symptom:** `HttpCode5XX` spikes, all backends healthy, `ClientConnum` normal

**Quick Check:**
- Was there a recent deployment? → Rollback
- Backend OOM? → Scale instance memory
- Upstream dependency failure? → Fix upstream; add circuit breaker

### LB Not Running

**Symptom:** `DescribeLoadBalancers` returns `Status` ≠ 2

**Action:** Wait up to 5 min if `Status=1` (creating). If stuck, contact Tencent Cloud support.

---

## Common Issues and Solutions

### Health Check Failures

**Symptom:** Backend servers marked unhealthy despite running

**Diagnostic Steps:**
1. Check health check configuration
```bash
tccli clb DescribeListeners --LoadBalancerId "{{user.loadbalancer_id}}" | jq '.Response.ListenerSet[0].HealthCheck'
```
2. Verify backend port is open
```bash
# Check if backend port responds
curl -v http://<backend-ip>:<port>/health-check-path
```
3. Check security group rules
```bash
# Extract SG IDs from LB, then check rules
SG_IDS=$(tccli clb DescribeLoadBalancers \
  --LoadBalancerIds "[\"{{user.loadbalancer_id}}\"]" \
  | jq -r '.Response.LoadBalancerSet[0].SecurityGroups[]')
for SG_ID in $SG_IDS; do
  tccli vpc DescribeSecurityGroups --SecurityGroupIds "[\"$SG_ID\"]"
done
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
tccli clb DescribeLoadBalancers --LoadBalancerIds "[\"{{user.loadbalancer_id}}\"]" | jq '.Response.LoadBalancerSet[0].Status'
```
2. Check listener configuration
```bash
tccli clb DescribeListeners --LoadBalancerId "{{user.loadbalancer_id}}"
```
3. Verify backend binding
```bash
tccli clb DescribeTargets --LoadBalancerId "{{user.loadbalancer_id}}"
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
tccli ssl DescribeCertificates --CertificateIds "[\"{{user.certificate_id}}\"]"
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
tccli clb DescribeTargets --LoadBalancerId "{{user.loadbalancer_id}}" | jq '.Response.Targets[].Weight'
```
2. Verify health status
```bash
tccli clb DescribeTargetHealth --LoadBalancerId "{{user.loadbalancer_id}}"
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
tccli vpc DescribeVpcs --VpcIds "[\"{{user.vpc_id}}\"]"
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

