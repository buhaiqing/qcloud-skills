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

## Workflow 5: TKE Alarm Aggregation (Incident Bundle)

> Also see the [Multi-Source RCA Workflow](#workflow-6-multi-source-rca-pod--node--clb--cvm) for deeper hypothesis scoring and topology-based evidence linking across Pod/Node/CLB/CVM layers.

```
Multiple TKE alarms detected in time window
  ↓
Normalize each alarm into Canonical Alarm Event (resource_id, metric_name, cluster_id, labels)
  ↓
Group by (cluster_id, resource_type, topology):
  All NodeNotReady + pod alarms on same node → Node Pressure group
  All CLB 5xx + backend pod alarms → CLB 5xx chain
  All PodPending + capacity metrics → Capacity group
  All addon errors → Addon group
  ↓
Apply directional rules (root vs symptom):
  NodeNotReady → root; CrashLoopBackOff / PodRestart, CLB backend fail → symptoms
  CLB 5xx → symptom; pod CrashLoopBackOff → check root;
  PodPending → symptom; node pool at MaxNum → root
  ↓
Generate Event Bundle per group (§5 alarm-handling.md):
  - incident_class, severity, confidence
  - root_alarm + correlated_alarms (with output-only suppression flags)
  - evidence (metrics, logs, data_quality/missing_sources)
  - recommendations prefixed RECOMMENDATION (not execution) and delegated
  ↓
Output Event Bundle; delegate fix recommendations to qcloud-tke-ops / qcloud-clb-ops / qcloud-cvm-ops
  ↓
Do NOT execute any fix or mutate cloud-side alarm policies
```

## Workflow 6: Multi-Source RCA (Pod / Node / CLB / CVM)

Canonical details live in [`multi-source-rca.md`](multi-source-rca.md). Keep this workflow compact to avoid duplicating the evidence model and scoring tables.

```
Incident symptoms mention Pod + Node + CLB + CVM, or a product skill delegates multi-source RCA
  ↓
Collect read-only evidence:
  Monitor alarms/metrics + TKE inventory + CLB backend + CVM instance/metrics + CLS logs if configured
  ↓
Normalize each datum into the Multi-Source RCA evidence model:
  source, entity_id/type, signal, severity, confidence, timestamp/window, linkage labels
  ↓
Build topology links:
  Pod ↔ Node via node_name; Node ↔ CVM via instance_id; CLB backend ↔ CVM/Node via backend_id/instance_id
  ↓
Align time windows:
  Lower confidence if CLB, pod, node, and CVM evidence does not overlap
  ↓
Score hypotheses:
  CLB 5xx caused by unhealthy pod/node?
  CrashLoopBackOff caused by node pressure or app regression?
  Pending caused by node-pool capacity/quota?
  NodeNotReady caused by CVM/network/disk saturation?
  CVM saturation causing TKE pod/service symptoms?
  ↓
Output Multi-Source RCA Bundle:
  top_cause, hypotheses, evidence_by_layer, topology_links, time_alignment, data_quality, verification_steps
  ↓
Recommendations are advisory only:
  RECOMMENDATION (not execution) + delegate_to qcloud-tke-ops / qcloud-clb-ops / qcloud-cvm-ops / qcloud-monitor-ops
```

## Workflow 7: Incident Timeline Assembly

Canonical schema: [`incident-timeline.md`](incident-timeline.md). Change evidence: [`change-correlation.md`](change-correlation.md).

```
Event Bundle and/or RCA Bundle produced (Workflow 5 or 6)
  ↓
Collect change evidence (optional):
  CloudAudit LookUpEvents + CLS K8s rollout events in diagnosis window
  ↓
Normalize into Timeline Events (alarm, metric_spike, log_pattern, change)
  ↓
Sort by timestamp; assign roles (change | trigger | root_candidate | symptom | correlated)
  ↓
Build causal_chain edges from correlation rules + Rule F lead-lag
  ↓
Compose narrative_summary (≤280 chars when possible)
  ↓
Output Incident Timeline JSON; persist ./audit-results/incident-timeline-YYYYMMDD-HHMMSS.json
  ↓
Embed incident_timeline_ref in Event Bundle / RCA Bundle (summary + event_count only)
```

## Workflow 8: Dynamic Baseline Anomaly Scan

Canonical spec: [`anomaly-detection.md`](anomaly-detection.md).

```
User requests proactive anomaly OR metric analysis (Step 2 baseline-first)
  ↓
Resolve resource_type + resource_id + diagnosis window (max 24h for baseline mode)
  ↓
Select metrics from product catalog (§5); cap at max_metrics_per_run
  ↓
For each metric: GetMonitorData × 3 (current, yesterday −24h, last week −7d)
  ↓
Compute p50/p95/max; ratio deviation; slope spike; anomaly score (§4)
  ↓
If anomaly_severity ≥ MEDIUM: correlate with alarms/logs per existing workflows
  ↓
Output Anomaly Bundle; embed anomaly_findings[] in RCA Bundle when RCA also runs
  ↓
Persist optional: ./audit-results/anomaly-bundle-YYYYMMDD-HHMMSS.json
```

## Workflow 9: Product + Network RCA (all product rules H–P / VPC Rule G)

Canonical specs: [`product-rca-rules.md`](product-rca-rules.md), [`network-rca.md`](network-rca.md).

```
Symptom on any product (CDB/Redis/ES/COS/CKafka/MongoDB/Postgres/SCF/CDN) OR connection timeout with healthy compute metrics
  ↓
Set resource_type + resource_id; optional domain / function_name / scf_namespace / load_balancer_id / vpc_id
  ↓
Collect product metrics + Describe* (Rules H–P)
  ↓
If timeout/refused OR NodeNotReady+CVM healthy OR F4 network change:
  Collect VPC SG/route/NAT (Rule G)
  ↓
Score product hypotheses; cross-link CLB symptom layer if present
  ↓
If H4/I4/J4/K4/L4/M5/N5/O5/P5 or G5: downgrade product-root confidence; surface alternate layer
  ↓
Output RCA Bundle with product_rca / network_rca blocks + delegated recommendations
```

## Workflow 10: Impact, Similar Cases, and KB Persistence

Canonical spec: [`incident-knowledge.md`](incident-knowledge.md).

```
Event Bundle and/or RCA Bundle assembled (Workflow 5/6/9)
  ↓
Compute impact block (CLB backend health, alarm severity mix, optional {{user.business_criticality}})
  ↓
Load incident-kb-index.json OR glob ./audit-results/incident-kb-*.json
  ↓
Score similar cases (Jaccard on trigger_signals + hypothesis/incident_class match)
  ↓
Attach similar_incidents[] (top 3, score ≥ 40); add REFERENCE ONLY advisories
  ↓
Sort recommendations by impact.severity then technical priority
  ↓
Write incident-kb-YYYYMMDD-HHMMSS.json; update incident-kb-index.json
  ↓
Set feedback_loop.kb_id + status=pending_review on bundle
  ↓
On user feedback ({{user.feedback_was_accurate}}): update KB resolution fields
```

## Workflow 11: Cross-Skill Orchestration (FinOps · Inspection · AIOps)

Canonical spec: [`cross-skill-orchestration.md`](cross-skill-orchestration.md).

```
Resolve orchestration_mode (auto or F1/F2/P1/A1/A2) from handoff_source + confidence
  ↓
F1: finops HIGH → delegate qcloud-proactive-inspection → AIOps RCA on findings + top resources
F2: finops_handoff → joint bill/metric hypothesis scoring → RCA + anomaly bundles
P1: inspection_handoff CRITICAL/HIGH → validate with baseline + RCA (note inspection snapshot age)
A1: post-RCA → emit prevention_items[] → RECOMMENDATION delegate inspection
A2: capacity/drift signals → attach finops_advisory → delegate qcloud-finops-ops
  ↓
Merge artifacts into Cross-Skill Bundle; embed cross_skill_ref on RCA Bundle
  ↓
Persist ./audit-results/cross-skill-bundle-YYYYMMDD-HHMMSS.json
```
