# Diagnostic Workflows — AIOps Decision Trees

## Workflow 1: Performance Degradation

```
Symptom: High latency / Slow response
  ↓
Check CPU:
  CPU > 90%?
    ↓YES                    ↓NO
Check NetworkIn:          Check MemUsage:
  NetworkIn high?            MemUsage > 90%?
    ↓YES       ↓NO             ↓YES        ↓NO
Traffic   App CPU-bound      Check OOM:     Check DiskIO:
spike     → Profile code      OOM logs?      DiskIO > 80%?
→ Scale    → Optimize          ↓YES ↓NO       ↓YES        ↓NO
  out/limit                    Memory    Check    Disk I/O    Check network
                               leak    GC pause bottleneck  latency
```

## Workflow 2: Availability Failure

```
Symptom: Connection refused / Timeout
  ↓
Check service status:
  Service running?
    ↓YES                    ↓NO
Check network path:        Service crashed?
  Port open from client?    ↓YES                ↓NO
    ↓YES      ↓NO          Restart service     Check health endpoint
  Firewall     VPC route                          ↓
  block        misconfigured                    Crash reason?
  → Fix ACL   → Fix route                      → Fix root cause
```

## Workflow 3: Capacity Exhaustion

```
Symptom: Disk full / Quota exceeded
  ↓
Check resource:
  Disk > 95%?
    ↓YES                    ↓NO
Check large files:         Quota > 90%?
  Logs?   Data?   Temp?      ↓YES               ↓NO
  ↓       ↓       ↓         Request quota      Check if metric spike
  Rotate  Archive Delete     increase           is transient
```

## Workflow 4: Security Incident

```
Symptom: Access denied / Unauthorized
  ↓
Check credentials:
  SecretId valid?
    ↓YES                    ↓NO
Check permissions:         Refresh credentials
  CAM policy attached?       → Reconfigure env
    ↓YES         ↓NO
  Policy allows           Attach policy
  this action?
    ↓YES          ↓NO
  Resource scope         Modify policy
  correct?               to allow action
```

## Escalation Rules

| Time Elapsed | Status | Action |
|-------------|--------|--------|
| < 5 min | Investigating | Continue diagnosis workflow |
| 5-15 min | Root cause identified | Apply fix, monitor |
| 15-30 min | Fix not working | Escalate to on-call |
| > 30 min | Incident unresolved | Emergency response: failover, rollback |
