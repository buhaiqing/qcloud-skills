# SLB 5xx Fast Diagnosis — Optimized Runbook

> **Goal:** Reduce MTTR from 45–90 min to < 30 min for CLB 5xx error incidents.

> **Security:** Never log or expose backend IPs, instance IDs, or credentials in agent output. Mask all sensitive identifiers with `<masked>`.

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

## Time Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| **MTTD** (Mean Time to Detect) | 10–15 min | < 2 min | Alarm fires → Agent starts diagnosis |
| **MTTI** (Mean Time to Identify) | 20–40 min | < 10 min | Agent starts → root cause identified |
| **MTTR** (Mean Time to Recover) | 45–90 min | < 30 min | Alarm fires → service restored |

---

## Phase 1: Rapid Triage (< 2 min)

**Trigger:** `HttpCode5XX` metric spike detected via Cloud Monitor alarm.

**Objective:** Determine if the issue is CLB-layer or backend-layer within 2 minutes.

### Step 1: Query 5xx Metric Trend

```bash
# Get HttpCode5XX for the last 15 minutes
tccli monitor GetMonitorData \
  --Namespace "QCE/LB_PUBLIC" \
  --MetricName "HttpCode5XX" \
  --Dimensions "[{\"Name\":\"LoadBalancerId\",\"Value\":\"{{user.loadbalancer_id}}\"}]" \
  --Period 60 \
  --StartTime "$(date_minus_minutes 15)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"
```

### Step 2: Check Backend Health Status (parallel)

```bash
# Check all backend health
tccli clb DescribeTargetHealth \
  --LoadBalancerId "{{user.loadbalancer_id}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}"
```

### Step 3: Quick LB Status Check (parallel)

```bash
# Verify LB is running
tccli clb DescribeLoadBalancers \
  --LoadBalancerIds "[\"{{user.loadbalancer_id}}\"]" \
  --Region "{{env.TENCENTCLOUD_REGION}}"
```

### Triage Decision Matrix

| Condition | Diagnosis | Next Phase |
|-----------|-----------|------------|
| `HttpCode5XX` > 0 **AND** `HealthCheckFailedNum` > 0 | **Backend health failure** | Phase 2A |
| `HttpCode5XX` > 0 **AND** `HealthCheckFailedNum` = 0 **AND** `ClientConnum` normal | **Backend application error** | Phase 2B |
| `HttpCode5XX` > 0 **AND** `ClientConnum` spike | **Traffic overload** | Phase 2C |
| LB `Status` ≠ 2 | **LB not running** | Phase 2D |
| `HttpCode5XX` spike **AND** `HealthCheckCode` abnormal | **Health check misconfiguration** | Phase 2A |

---

## Phase 2A: Backend Health Failure Diagnosis

**Time budget:** < 8 min

### Step 1: Identify Unhealthy Backends

```bash
# Filter unhealthy targets
tccli clb DescribeTargetHealth \
  --LoadBalancerId "{{user.loadbalancer_id}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  | jq '[.Response.Targets[] | select(.HealthStatus != "alive")]'
```

### Step 2: Check Listener Health Check Configuration

```bash
# Get health check params
tccli clb DescribeListeners \
  --LoadBalancerId "{{user.loadbalancer_id}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  | jq '.Response.ListenerSet[].HealthCheck'
```

### Step 3: Verify Backend Port Reachability

```bash
# For each unhealthy backend, test port connectivity
# Replace <backend-ip> and <port> from DescribeTargetHealth output
curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 http://<backend-ip>:<port>/health-check-path
```

### Step 4: Check Security Group Rules

```bash
# Get security group IDs dynamically from LB configuration
SG_IDS=$(tccli clb DescribeLoadBalancers \
  --LoadBalancerIds "[\"{{user.loadbalancer_id}}\"]" \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  | jq -r '.Response.LoadBalancerSet[0].SecurityGroups[]')

# Verify security group allows CLB health check source
for SG_ID in $SG_IDS; do
  tccli vpc DescribeSecurityGroups \
    --SecurityGroupIds "[\"$SG_ID\"]" \
    --Region "{{env.TENCENTCLOUD_REGION}}" \
    | jq '.Response.SecurityGroupSet[0].SecurityGroupPolicySet'
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

### Common Root Causes & Fixes

| Root Cause | Evidence | Fix |
|------------|----------|-----|
| Backend port not listening | `curl` returns connection refused | Restart backend service; check port config |
| Security group blocks CLB | SG policy missing CLB VIP source | Add CLB source IP/CIDR to SG ingress |
| Health check path wrong | Health check returns 404/500 | Update listener health check path |
| Backend process crashed | Instance running but port dead | Restart application process on backend |

### Automated Recovery (if applicable)

```bash
# If backend is a CVM instance that needs restart, delegate to qcloud-cvm-ops
# Quick remediation: deregister unhealthy → fix → re-register
tccli clb DeregisterTargets \
  --LoadBalancerId "{{user.loadbalancer_id}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ListenerId "{{user.listener_id}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Targets "[{\"InstanceId\":\"{{user.instance_id}}\",\"Port\":{{user.target_port}}}]"

# After backend fix, re-register
tccli clb RegisterTargets \
  --LoadBalancerId "{{user.loadbalancer_id}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ListenerId "{{user.listener_id}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Targets "[{\"InstanceId\":\"{{user.instance_id}}\",\"Port\":{{user.target_port}},\"Weight\":10}]"
```

---

## Phase 2B: Backend Application Error Diagnosis

**Time budget:** < 10 min

### Step 1: Verify Backend Instance Status

```bash
# Check CVM instance status — delegate to qcloud-cvm-ops
# Key checks: instance RUNNING, CPU/memory, disk, application process
```

### Step 2: Check Backend Logs

```bash
# If using CLS for backend logs, delegate to qcloud-cls-ops
# Query backend error logs for the incident time window
# Key patterns: OOM, segfault, application exceptions
```

### Step 3: Check Connection Backend to CLB

```bash
# From backend, test connectivity back to CLB health check source
# This validates network path from backend → CLB

# Get LB VIP
tccli clb DescribeLoadBalancers \
  --LoadBalancerIds "[\"{{user.loadbalancer_id}}\"]" \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  | jq '.Response.LoadBalancerSet[0].VipIps[0]'
```

### Common Root Causes & Fixes

| Root Cause | Evidence | Fix |
|------------|----------|-----|
| Backend OOM | Instance memory maxed; process killed | Scale instance memory; optimize app |
| Application bug deployed | 5xx started after deployment | Rollback deployment |
| Database connection pool exhausted | Backend logs show connection timeout | Increase pool size; fix connection leak |
| Upstream dependency failure | Backend returns 502/503 upstream | Fix upstream service; add circuit breaker |

---

## Phase 2C: Traffic Overload Diagnosis

**Time budget:** < 8 min

### Step 1: Analyze Traffic Pattern

```bash
# Get connection metrics
tccli monitor GetMonitorData \
  --Namespace "QCE/LB_PUBLIC" \
  --MetricName "ClientConnum" \
  --Dimensions "[{\"Name\":\"LoadBalancerId\",\"Value\":\"{{user.loadbalancer_id}}\"}]" \
  --Period 60 \
  --StartTime "$(date_minus_minutes 30)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"

# Get bandwidth metrics
tccli monitor GetMonitorData \
  --Namespace "QCE/LB_PUBLIC" \
  --MetricName "TrafficOut" \
  --Dimensions "[{\"Name\":\"LoadBalancerId\",\"Value\":\"{{user.loadbalancer_id}}\"}]" \
  --Period 60 \
  --StartTime "$(date_minus_minutes 30)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"
```

### Step 2: Check Backend Capacity

```bash
# Get target weights and count
tccli clb DescribeTargets \
  --LoadBalancerId "{{user.loadbalancer_id}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  | jq '[.Response.Targets[] | {InstanceId, Port, Weight, HealthStatus}]'
```

### Common Root Causes & Fixes

| Root Cause | Evidence | Fix |
|------------|----------|-----|
| Traffic spike (promo/event) | `ClientConnum` suddenly 3–10x normal | Scale backends; enable auto-scaling |
| Backend capacity insufficient | All backends healthy but 5xx | Increase backend count or spec |
| Connection limit hit | `Connum` near backend limit | Tune OS/app connection limits |
| Bandwidth saturated | `TrafficOut` at LB bandwidth cap | Upgrade LB bandwidth |

### Automated Recovery

```bash
# Quick scale: register additional backend servers
tccli clb RegisterTargets \
  --LoadBalancerId "{{user.loadbalancer_id}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ListenerId "{{user.listener_id}}" \
  --Targets "[{\"InstanceId\":\"{{user.instance_id}}\",\"Port\":{{user.target_port}},\"Weight\":10}]"
```

---

## Phase 2D: LB Not Running Diagnosis

**Time budget:** < 5 min

### Step 1: Check LB Status Detail

```bash
tccli clb DescribeLoadBalancers \
  --LoadBalancerIds "[\"{{user.loadbalancer_id}}\"]" \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  | jq '.Response.LoadBalancerSet[0] | {LoadBalancerId, Status, LoadBalancerType, VpcId}'
```

### Common Root Causes & Fixes

| Status | Meaning | Fix |
|--------|---------|-----|
| `1` (creating) | LB still provisioning | Wait up to 5 min; if stuck, open ticket |
| Other | Abnormal state | Contact Tencent Cloud support |

---

## Phase 3: Recovery Verification (< 5 min)

After applying fixes from any Phase 2 branch:

### Step 1: Verify 5xx Rate Drops

```bash
# Monitor HttpCode5XX for 5 minutes after fix
for i in $(seq 1 5); do
  VALUE=$(tccli monitor GetMonitorData \
    --Namespace "QCE/LB_PUBLIC" \
    --MetricName "HttpCode5XX" \
    --Dimensions "[{\"Name\":\"LoadBalancerId\",\"Value\":\"{{user.loadbalancer_id}}\"}]" \
    --Period 60 \
    --StartTime "$(date_minus_minutes 2)" \
    --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)" \
    | jq '.Response.MetricDataSet[0].Values[-1]')
  echo "[$(date +%H:%M:%S)] HttpCode5XX = $VALUE"
  sleep 60
done
```

### Step 2: Verify Backend Health Recovery

```bash
tccli clb DescribeTargetHealth \
  --LoadBalancerId "{{user.loadbalancer_id}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  | jq '[.Response.Targets[] | select(.HealthStatus != "alive")] | length'
# Expected: 0 (all healthy)
```

### Step 3: Verify End-to-End Connectivity

```bash
# Test from client perspective
curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 https://{{user.vip}}/
# Expected: 200
```

---

## Phase 4: Post-Incident Actions

### 1. Document Root Cause

Update the incident record with:
- Root cause category (health/app/overload/LB)
- Affected backends (instance IDs)
- Time of detection → identification → recovery
- Fix applied

### 2. Prevent Recurrence

| Category | Prevention |
|----------|-----------|
| Health check misconfig | Add health check validation to deployment pipeline |
| Backend capacity | Configure auto-scaling policies |
| Application error | Add canary deployment; circuit breaker for upstream |
| LB capacity | Monitor bandwidth utilization; plan upgrades |

### 3. Update Alarm Thresholds

Based on this incident, review and adjust:
- `HttpCode5XX` threshold (default: > 100/min)
- `HealthCheckFailedNum` threshold (default: > 5)
- `ClientConnum` threshold (per-LB baseline)

---

## Quick Reference: Decision Tree

```
5xx Detected
    │
    ├─ HealthCheckFailedNum > 0?
    │   └─ YES → Phase 2A (Backend Health)
    │       ├─ Port not listening → Restart backend
    │       ├─ SG blocks CLB → Add CLB VIP to SG
    │       ├─ Wrong health path → Fix listener config
    │       └─ Backend crashed → Restart/re-register
    │
    ├─ ClientConnum spike?
    │   └─ YES → Phase 2C (Traffic Overload)
    │       ├─ Traffic spike → Scale backends
    │       ├─ Capacity limit → Upgrade/resize
    │       └─ Bandwidth cap → Upgrade LB bandwidth
    │
    ├─ LB Status != 2?
    │   └─ YES → Phase 2D (LB Not Running)
    │       ├─ Still creating → Wait
    │       └─ Abnormal → Contact support
    │
    └─ NONE of above → Phase 2B (Application Error)
        ├─ OOM → Scale memory
        ├─ Bad deploy → Rollback
        ├─ DB pool exhausted → Tune pool
        └─ Upstream failure → Fix upstream

After fix → Phase 3 (Verification)
After recovery → Phase 4 (Post-Incident)
```

---

## Cross-Skill Delegation

| Diagnosis | Delegate To | Context |
|-----------|-------------|---------|
| Backend CVM issue | `qcloud-cvm-ops` | Instance status, process restart, resource scaling |
| VPC/network issue | `qcloud-vpc-ops` | Security group, subnet, routing |
| SSL certificate issue | `qcloud-ssl-ops` | Certificate renewal, HTTPS listener fix |
| CLS log analysis | `qcloud-cls-ops` | Backend error log queries |
| Cloud Monitor alarms | `qcloud-monitor-ops` | Alarm threshold tuning |
