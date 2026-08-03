# CVM Performance Diagnosis — AIOps Fast Path

> AIOps-native triage for CVM performance issues. Distinct from `qcloud-cvm-ops/references/troubleshooting.md` (product ops runbook) — this focuses on **alarm → multi-metric → root cause** correlation. Target MTTR < 45 min.

## Quick Start

```text
CVM CPU/Mem/Disk/Network spike alarm → fetch 4-dimension metrics → apply triage tree → RCA Bundle
```

## Triage Tree (Workflow 1 + 2 variant)

```
CVM perf symptom detected
  ↓
CPU > 90%?
  ↓YES                    ↓NO
NetworkIn high?          MemUsage > 90%?
  ↓YES       ↓NO           ↓YES        ↓NO
Traffic    Check App      OOM in      DiskIO > 80%?
spike      CPU-bound      logs?       ↓YES        ↓NO
→ traffic   → profile     ↓YES ↓NO   Disk     Check net
alleviation  code         Mem     GC   I/O      latency
             ↓             leak  pause bottleneck
             Check DiskIO → restart  ↓YES        ↓NO
                           + fix    Scale   Norm? → network
                                     down      I/O wait?
                                               ↓
                                     Check Disk await / iostat
```

## Metric Dimensions (tccli)

| Dimension | Metrics | Namespace |
|-----------|---------|-----------|
| CPU | `CpuUsage`, `CpuLoadavg` | `QCE/CVM` |
| Memory | `MemUsage`, `MemRealUsed` | `QCE/CVM` |
| Disk | `DiskUsage`, `DiskRdRate`, `DiskWrRate` | `QCE/CVM` |
| Network | `NetBandOut`, `NetBandIn`, `NetPacketOut`, `NetPacketIn` | `QCE/CVM` |

```bash
# 4-dimension fetch (parallel)
tccli monitor GetMonitorData \
  --Namespace QCE/CVM --MetricName CpuUsage \
  --Instances '[{"Dimensions":[{"Name":"InstanceId","Value":"{{user.resource_id}}"}]}]' \
  --StartTime "{{user.time_start}}" --EndTime "{{user.time_end}}" --Period 300

tccli monitor GetMonitorData --Namespace QCE/CVM --MetricName MemUsage ...
tccli monitor GetMonitorData --Namespace QCE/CVM --MetricName DiskUsage ...
tccli monitor GetMonitorData --Namespace QCE/CVM --MetricName NetBandOut ...
```

## Root Cause Classification

| Symptom pattern | Likely root | Hypothesis ID | Confidence |
|----------------|-------------|---------------|------------|
| CPU spike + NetworkIn high | Traffic spike / DDoS | CV1 | HIGH |
| CPU spike + NetworkIn normal | App CPU-bound | CV2 | MEDIUM |
| CPU spike + DiskRd high | I/O wait | CV3 | HIGH |
| MemUsage > 90% + OOM logs | Memory leak | CV4 | HIGH |
| MemUsage > 90% + GC pause | JVM/GC misconfig | CV5 | MEDIUM |
| DiskUsage > 85% | Disk full | CV6 | HIGH |
| DiskIO > 80% + CPU normal | I/O bottleneck | CV7 | MEDIUM |
| NetBandOut spike | Egress traffic spike | CV8 | HIGH |

## Anti-Patterns

- **CPU 85% but daily peak** → run baseline anomaly (`anomaly-detection.md`) first
- **Single metric flagging** → always correlate 3+ dimensions
- **OOM without logs** → check `dmesg` or CLS for `OutOfMemory`
- **Disk full + no large files found** → check hidden `.trash` or inodes

## Cross-Link Rules

| Trigger | Link to |
|---------|---------|
| CVM → TKE Pod on same Node | Rule A (`tke-node-pressure.md`) |
| CVM → CLB 5xx backend | Rule A (`clb-backend-health.md`) |
| CVM → CDB slow query | Rule H (`product-rca-rules.md` §2) |
| CVM → VPC SG/Route change | Rule F (`change-correlation.md`) |

## Output

`RCA Bundle` — see [`output-schemas.md`](output-schemas.md) §RCA Bundle.

**Delegate:** `qcloud-cvm-ops` for remediation actions (scale, restart, security patch).

## See also

- [`diagnostic-workflows.md`](diagnostic-workflows.md) Workflow 1 (Performance Degradation)
- [`anomaly-detection.md`](anomaly-detection.md) — baseline-first anomaly
- [`change-correlation.md`](change-correlation.md) — Rule F post-change regression
