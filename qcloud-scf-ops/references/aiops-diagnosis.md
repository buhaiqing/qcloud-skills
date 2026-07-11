# SCF AIOps Diagnosis — Delegation Stub

> **Do not run multi-metric correlation or cross-layer RCA from this file.** Delegate to [`qcloud-aiops-diagnosis`](../../qcloud-aiops-diagnosis/SKILL.md) (read-only); execute fixes via this skill per bundle recommendations.

## When to Delegate

| User intent | Delegate to | Pass variables |
|-------------|-------------|----------------|
| Error / timeout / throttle spike root cause | `qcloud-aiops-diagnosis` | `function_name`, `scf_namespace`, `resource_type=scf`, `time_range` |
| Cold start / InitDuration / first-invocation latency | `qcloud-aiops-diagnosis` | + `anomaly_mode=baseline_primary` if no clear window |
| Concurrency / account throttle (429) | `qcloud-aiops-diagnosis` | + Monitor `QCE/SCF` Throttle metric context |
| Downstream DB/VPC timeout in function logs | `qcloud-aiops-diagnosis` | + downstream `resource_id` if known (Rule O → H/I/G) |
| Alarm storm with SCF + API GW / trigger context | `qcloud-aiops-diagnosis` | + trigger type, optional `load_balancer_id` |
| Cross-service latency (SCF + COS + API GW) | `qcloud-aiops-diagnosis` | + trigger chain, optional `service_chain` |
| Cost anomaly (unexpected high duration) | `qcloud-aiops-diagnosis` | + `anomaly_mode=cost_focus`, duration spike window |

## When to Stay in SCF Skill

- Function CRUD, code deploy, version/alias, trigger CRUD
- Timeout/memory/concurrency **config change** after RCA identifies fix
- Single documented SCF error with known fix → [`troubleshooting.md`](troubleshooting.md)
- CAM/VPC-only issues → respective product skills

## Return Contract

AIOps returns Event Bundle, RCA Bundle, or Anomaly Bundle per [`output-schemas.md`](../../qcloud-aiops-diagnosis/references/output-schemas.md). Product RCA uses **Rule O** in [`product-rca-rules.md`](../../qcloud-aiops-diagnosis/references/product-rca-rules.md).

## SCF-Specific Diagnostic Matrix

### Cold Start Diagnosis

| Symptom | Primary Metrics | Correlated Metrics | Root Cause | Fix (this skill) |
|---------|----------------|-------------------|------------|-------------------|
| High first-invocation latency | Duration ↑ (first inv) | InitDuration in logs | Large package / VPC init | Reduce package; provisioned concurrency |
| Frequent cold starts | Duration spikes (periodic) | Idle timeout pattern | Low traffic + short timeout | Provisioned concurrency; keep-alive pings |
| VPC cold start overhead | Duration ↑ (VPC functions) | Network init time | VPC networking setup | Use public functions; minimize VPC |

### Concurrency & Throttle Diagnosis

| Symptom | Primary Metrics | Correlated Metrics | Root Cause | Fix (this skill) |
|---------|----------------|-------------------|------------|-------------------|
| 429 throttle errors | Throttle ↑ | Account concurrency | Account limit reached | Request quota increase |
| Function-specific throttle | Throttle (per function) | Reserved concurrency | Function reserved limit | Adjust reserved concurrency |
| Burst traffic throttle | Throttle (burst) | Burst concurrency | Burst limit exceeded | Async processing; queue buffering |

### Cross-Layer Diagnosis

| Symptom | Primary Metrics | Correlated Metrics | Root Cause | Fix (this skill) |
|---------|----------------|-------------------|------------|-------------------|
| Downstream DB timeout | Error ↑ + Duration ↑ | CDB/Redis metrics | Database overload | Fix downstream; optimize queries |
| API GW 502 errors | Error ↑ (API GW) | SCF error logs | Function exception | Fix function code |
| COS trigger delay | Event age ↑ | COS metrics | COS event delivery delay | Check COS permissions; retry |
| CMQ message loss | Message count ↓ | CMQ metrics | Message queue issue | Check CMQ config; retry |

## Fault Pattern Correlation

### Error Pattern → Root Cause → Fix Path

| Error Pattern | Primary Metric | Correlated | Typical Fix (this skill) |
|---------------|----------------|------------|--------------------------|
| Code exception | Error ↑ | Stack in GetFunctionLogs | Fix code / redeploy |
| Timeout budget | Duration at ceiling | Downstream errors in logs | Raise timeout or fix deps |
| Cold start | Duration spike (first inv) | InitDuration in logs | Reduce package / provisioned concurrency |
| Throttle | Throttle ↑ | 429 in logs | Raise concurrency / reserved config |
| Downstream DB | Error ↑ | CDB/Redis metrics (Rule H/I) | Fix downstream; not SCF-only |
| Memory OOM | Error + MemoryUsed ↑ | Memory limit reached | Increase memory; optimize code |
| IAM permission | Error (AccessDenied) | CAM policy | Update execution role permissions |

### Cross-Service Correlation

| Service Chain | Primary Metric | Correlated | Diagnosis Focus |
|---------------|----------------|------------|-----------------|
| SCF → API GW → Client | Latency ↑ | API GW metrics | Function latency + API GW config |
| SCF → COS → SCF | Event delay ↑ | COS event metrics | Event delivery + function processing |
| SCF → CDB/Redis | Query latency ↑ | Database metrics | Function queries + DB performance |
| SCF → CMQ/Ckafka | Message lag ↑ | Queue metrics | Message processing + queue config |

## Diagnostic Workflow Examples

### Example 1: Cold Start Performance Issue

```
Input: function_name=my-api, time_range=24h
→ Delegate to qcloud-aiops-diagnosis
→ Pass: function_name, scf_namespace, resource_type=scf, anomaly_mode=baseline_primary
→ AIOps returns: Anomaly Bundle with cold start pattern
→ Execute fix: Reduce package size + enable provisioned concurrency
```

### Example 2: Cross-Service Latency

```
Input: function_name=order-processor, trigger=cos, time_range=1h
→ Delegate to qcloud-aiops-diagnosis
→ Pass: function_name, trigger_type=cos, service_chain=scf-cos-sc
→ AIOps returns: RCA Bundle with COS event delivery delay
→ Execute fix: Check COS permissions + optimize function processing
```

### Example 3: Concurrency Throttle

```
Input: function_name=payment-handler, error=429, time_range=6h
→ Delegate to qcloud-aiops-diagnosis
→ Pass: function_name, error_type=throttle, metric_context=QCE/SCF Throttle
→ AIOps returns: Event Bundle with account concurrency pattern
→ Execute fix: Request quota increase + implement async processing
```

## Integration with qcloud-aiops-diagnosis

### Required Variables for Delegation

| Variable | Source | Required |
|----------|--------|----------|
| `function_name` | User input | Yes |
| `scf_namespace` | User input (default: "default") | Yes |
| `resource_type` | Fixed: "scf" | Yes |
| `time_range` | User input or default: "24h" | Yes |
| `anomaly_mode` | Based on symptom | Optional |
| `trigger_type` | If trigger-related | Optional |
| `downstream_resource_id` | If cross-layer | Optional |

### Return Value Processing

AIOps returns bundles with recommended fixes. Process as:

1. **Event Bundle**: Contains anomaly detection results
   - Extract recommended actions
   - Validate against SCF constraints
   - Execute config changes if safe

2. **RCA Bundle**: Contains root cause analysis
   - Parse root cause chain
   - Identify fix path
   - Execute fixes per bundle recommendations

3. **Anomaly Bundle**: Contains performance anomalies
   - Review anomaly patterns
   - Correlate with SCF metrics
   - Implement optimization recommendations

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-13 | Initial stub — Rule O reverse delegation (Phase F) |
| 1.1.0 | 2026-07-09 | Expanded diagnostic matrix, fault pattern correlation, workflow examples, integration details |
