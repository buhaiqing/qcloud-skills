# CLB Troubleshooting Guide

> **Platform:** Date commands differ between macOS and Linux. Use the cross-platform helper below:
> ```bash
> # Cross-platform: compute timestamp N minutes ago
> date_minus_minutes() {
>   local mins=$1
>   if date -v-"${mins}"M +%s >/dev/null 2>&1; then
>     date -u -v-"${mins}"M +%Y-%m-%dT%H:%M:%S+00:00  # macOS
>   else
>     date -u -d "-${mins} minutes" +%Y-%m-%dT%H:%M:%S+00:00  # Linux
>   fi
> }
> ```

> **Tool dependency:** All `jq` commands below require `jq` installed. Verify before use:
> ```bash
> command -v jq >/dev/null 2>&1 || { echo "[ERROR] jq not installed — install via: brew install jq / apt install jq"; exit 1; }
> ```

> **Environment validation:** Ensure required environment variables are set:
> ```bash
> test -n "$TENCENTCLOUD_SECRET_ID" || { echo "[ERROR] TENCENTCLOUD_SECRET_ID not set"; exit 1; }
> test -n "$TENCENTCLOUD_SECRET_KEY" || { echo "[ERROR] TENCENTCLOUD_SECRET_KEY not set"; exit 1; }
> ```

## Quick Diagnosis: 5xx Errors (MTTR < 30 min)

> **When `HttpCode5XX` alarm fires**, use the fast diagnosis path below instead of general troubleshooting.

### Fast Triage (2 min)

1. **Query 5xx metric trend + backend health in parallel:**

```bash
# 5xx trend (last 15 min)
START_TIME=$(date_minus_minutes 15)
tccli monitor GetMonitorData \
  --Namespace "QCE/LB_PUBLIC" \
  --MetricName "HttpCode5XX" \
  --Dimensions "[{\"Name\":\"LoadBalancerId\",\"Value\":\"{{user.loadbalancer_id}}\"}]" \
  --Period 60 \
  --StartTime "$START_TIME" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)" \
  --Region "{{env.TENCENTCLOUD_REGION}}"

# Backend health status
tccli clb DescribeTargetHealth \
  --LoadBalancerId "{{user.loadbalancer_id}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}"
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
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  | jq '[.Response.Targets[] | {InstanceId, Weight, HealthStatus}]'

# Scale: register additional backends
tccli clb RegisterTargets \
  --LoadBalancerId "{{user.loadbalancer_id}}" \
  --ListenerId "{{user.listener_id}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Targets "[{\"InstanceId\":\"{{user.new_instance_id}}\",\"Port\":{{user.target_port}},\"Weight\":10}]"

# SDK fallback: Python equivalent
# import json
# from tencentcloud.common import credential
# from tencentcloud.clb.v20180317 import clb_client, models
# cred = credential.Credential("{{env.TENCENTCLOUD_SECRET_ID}}", "{{env.TENCENTCLOUD_SECRET_KEY}}")
# client = clb_client.ClbClient(cred, "{{env.TENCENTCLOUD_REGION}}")
# req = models.RegisterTargetsRequest()
# req.LoadBalancerId = "{{user.loadbalancer_id}}"
# req.ListenerId = "{{user.listener_id}}"
# req.Targets = [models.TargetInfo(InstanceId="{{user.new_instance_id}}", Port={{user.target_port}}, Weight=10)]
# resp = client.RegisterTargets(req)
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
tccli clb DescribeListeners --LoadBalancerId "{{user.loadbalancer_id}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  | jq '.Response.ListenerSet[0].HealthCheck'

# SDK fallback: Python equivalent
# import json
# from tencentcloud.common import credential
# from tencentcloud.clb.v20180317 import clb_client, models
# cred = credential.Credential("{{env.TENCENTCLOUD_SECRET_ID}}", "{{env.TENCENTCLOUD_SECRET_KEY}}")
# client = clb_client.ClbClient(cred, "{{env.TENCENTCLOUD_REGION}}")
# req = models.DescribeListenersRequest()
# req.LoadBalancerId = "{{user.loadbalancer_id}}"
# resp = client.DescribeListeners(req)
# health_check = resp.ListenerSet[0].HealthCheck
```
2. Verify backend port is open
```bash
# Check if backend port responds
# WARNING: Never log or expose backend IPs in agent output. Mask with <masked>.
curl -v http://<masked>:<masked>/health-check-path
```
3. Check security group rules
```bash
# Extract SG IDs from LB, then check rules
SG_IDS=$(tccli clb DescribeLoadBalancers \
  --LoadBalancerIds "[\"{{user.loadbalancer_id}}\"]" \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  | jq -r '.Response.LoadBalancerSet[0].SecurityGroups[]')
for SG_ID in $SG_IDS; do
  tccli vpc DescribeSecurityGroups --SecurityGroupIds "[\"$SG_ID\"]" \
    --Region "{{env.TENCENTCLOUD_REGION}}"
done

# SDK fallback: Python equivalent
# import json
# from tencentcloud.common import credential
# from tencentcloud.clb.v20180317 import clb_client, models
# cred = credential.Credential("{{env.TENCENTCLOUD_SECRET_ID}}", "{{env.TENCENTCLOUD_SECRET_KEY}}")
# client = clb_client.ClbClient(cred, "{{env.TENCENTCLOUD_REGION}}")
# req = models.DescribeLoadBalancersRequest()
# req.LoadBalancerIds = ["{{user.loadbalancer_id}}"]
# resp = client.DescribeLoadBalancers(req)
# sg_ids = resp.LoadBalancerSet[0].SecurityGroups
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
tccli clb DescribeLoadBalancers --LoadBalancerIds "[\"{{user.loadbalancer_id}}\"]" \
  --Region "{{env.TENCENTCLOUD_REGION}}" | jq '.Response.LoadBalancerSet[0].Status'
```
2. Check listener configuration
```bash
tccli clb DescribeListeners --LoadBalancerId "{{user.loadbalancer_id}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}"
```
3. Verify backend binding
```bash
tccli clb DescribeTargets --LoadBalancerId "{{user.loadbalancer_id}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}"
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
tccli ssl DescribeCertificates --CertificateIds "[\"{{user.certificate_id}}\"]" \
  --Region "{{env.TENCENTCLOUD_REGION}}"
```
2. Check certificate expiration
```bash
# Get certificate expiry date
tccli ssl DescribeCertificates --CertificateIds "[\"{{user.certificate_id}}\"]" \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  | jq '.Response.Certificates[0].CertExpireTime'
```

# SDK fallback: Python equivalent
# import json
# from tencentcloud.common import credential
# from tencentcloud.ssl.v20191205 import ssl_client, models
# cred = credential.Credential("{{env.TENCENTCLOUD_SECRET_ID}}", "{{env.TENCENTCLOUD_SECRET_KEY}}")
# client = ssl_client.SslClient(cred, "{{env.TENCENTCLOUD_REGION}}")
# req = models.DescribeCertificatesRequest()
# req.CertificateIds = ["{{user.certificate_id}}"]
# resp = client.DescribeCertificates(req)
# expire_time = resp.Certificates[0].CertExpireTime

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
tccli clb DescribeTargets --LoadBalancerId "{{user.loadbalancer_id}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  | jq '.Response.Targets[].Weight'
```
2. Verify health status
```bash
tccli clb DescribeTargetHealth --LoadBalancerId "{{user.loadbalancer_id}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}"
```

# SDK fallback: Python equivalent
# import json
# from tencentcloud.common import credential
# from tencentcloud.clb.v20180317 import clb_client, models
# cred = credential.Credential("{{env.TENCENTCLOUD_SECRET_ID}}", "{{env.TENCENTCLOUD_SECRET_KEY}}")
# client = clb_client.ClbClient(cred, "{{env.TENCENTCLOUD_REGION}}")
# req = models.DescribeTargetsRequest()
# req.LoadBalancerId = "{{user.loadbalancer_id}}"
# resp = client.DescribeTargets(req)
# weights = [t.Weight for t in resp.Targets]

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

