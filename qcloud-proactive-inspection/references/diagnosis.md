# Diagnosis Workflows — Proactive Inspection

## per-Anomaly Diagnostic Flows

### CPU Anomaly Diagnosis
```
CPU > threshold?
  ↓YES
Check NetworkIn:
  NetworkIn > baseline × 2?
    ↓YES → Traffic spike diagnosis → Recommend: rate limiting, CDN, scale out
    ↓NO
Check process list:
  Single process > 80% CPU?
    ↓YES → Application CPU-bound → Recommend: profile, optimize, restart
    ↓NO
Check scheduled tasks:
  Backup/cron running?
    ↓YES → Expected load → Recommend: reschedule to off-peak
    ↓NO → Investigate further
```

### Memory Anomaly Diagnosis
```
Memory > threshold?
  ↓YES
Check Java heap (if Java app):
  Heap > 90%?
    ↓YES → GC pressure → Recommend: heap dump, GC analysis, restart
    ↓NO
Check cache size:
  Cache > 70% of memory?
    ↓YES → Cache growth → Recommend: set cache max, eviction policy
    ↓NO → Check for memory leak in other processes
```

### Disk Anomaly Diagnosis
```
Disk > threshold?
  ↓YES
Check largest directories:
  Logs > 50% of usage?
    ↓YES → Log bloat → Recommend: implement rotation, delete old logs
    ↓NO
  Data > 50% of usage?
    ↓YES → Data growth → Recommend: archive old data, expand disk
    ↓NO
  Temp files > 20% of usage?
    ↓YES → Temp accumulation → Recommend: cleanup script, cron job
```
