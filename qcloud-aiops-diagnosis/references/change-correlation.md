# Change Correlation — Post-Change Regression & Causal Candidates

> **Read-only change evidence collection.** This layer gathers deployment, configuration, and infrastructure change events in the diagnosis window. It does not execute changes. Mutation recommendations remain `RECOMMENDATION (not execution)` and delegated to product skills.

## 1. Change Evidence Model

Every change event is normalized before correlation:

```json
{
  "change_id": "chg-20260609-001",
  "source": "cloudaudit|cls_k8s_event|cls_app_log|monitor_policy",
  "change_type": "deploy|scale|config|network|credential|addon|alarm_policy|other",
  "actor": "sub-account-uin|system|unknown",
  "resource_type": "deployment|statefulset|clb|security_group|cvm|tke_cluster|addon|alarm_policy",
  "resource_id": "api-deploy|lb-xxx|sg-xxx|cls-xxx",
  "action": "RollingUpdate|ModifyLoadBalancerAttributes|ModifySecurityGroupPolicies",
  "summary": "Deployment api-deploy rolled out revision 42",
  "timestamp": "2026-06-09T10:02:00+08:00",
  "window_start": "2026-06-09T09:47:00+08:00",
  "window_end": "2026-06-09T10:17:00+08:00",
  "linkage": {
    "cluster_id": "cls-xxx",
    "namespace": "prod",
    "workload": "api-deploy",
    "load_balancer_id": "lb-xxx",
    "instance_id": "ins-xxx"
  },
  "confidence": "HIGH|MEDIUM|LOW",
  "raw_excerpt": {}
}
```

### Change Type Taxonomy

| change_type | Typical signals | Primary source |
|---|---|---|
| `deploy` | K8s Deployment/StatefulSet rollout, image tag change | CLS K8s events |
| `scale` | Node pool resize, HPA scale, CVM count change | CloudAudit + TKE inventory delta |
| `config` | CLB listener/backend weight, probe timeout, env var | CloudAudit + CLS app logs |
| `network` | SG rule, route table, NAT, VPC peering | CloudAudit (`ModifySecurityGroupPolicies`, etc.) |
| `credential` | CAM key rotation, secret update | CloudAudit |
| `addon` | TKE addon install/upgrade | CloudAudit + `DescribeAddon` status delta |
| `alarm_policy` | Monitor policy create/modify | CloudAudit |
| `other` | Unclassified API mutation in window | CloudAudit |

## 2. Collection (Read-Only)

### Step 1: CloudAudit API mutations

Query mutations in `[diagnosis_window - 15min, diagnosis_window_end + 5min]` to capture leading changes:

```bash
tccli cloudaudit LookUpEvents \
  --StartTime {{user.time_start_epoch}} \
  --EndTime {{user.time_end_epoch}} \
  --MaxResults 100
```

Filter events relevant to the incident scope (best effort):

| Incident scope | CloudAudit event name patterns to prioritize |
|---|---|
| TKE / Pod | `ModifyCluster*`, `CreateCluster*`, `InstallAddon`, `UpgradeCluster*`, `ModifyNodePool*`, `DrainClusterNode` |
| CLB | `ModifyLoadBalancer*`, `ModifyListener*`, `ModifyTargetWeight*`, `RegisterTargets`, `DeregisterTargets` |
| CVM / Node | `ModifyInstanceAttribute`, `RebootInstances`, `ResetInstance`, `ModifyInstancesAttribute` |
| Network | `ModifySecurityGroupPolicies`, `CreateSecurityGroup`, `ModifyRouteTable*`, `AllocateAddresses` |
| Monitor | `ModifyAlarmPolicy*`, `CreateAlarmPolicy`, `BindingPolicyObject` |

> Field names vary by API version. Preserve raw `Events[].CloudAuditEvent` excerpt when mapping is uncertain; set `confidence=LOW` and add a warning.

**Degraded behavior:** If CloudAudit is disabled, empty, or `AccessDenied`, set `evidence_by_layer.change_events.status=unavailable`, `data_quality.degraded=true`, and continue without change-based HIGH confidence.

### Step 2: CLS Kubernetes deployment / rollout events

When `{{user.tke_event_topic_id}}` is configured:

```bash
tccli cls SearchLog \
  --TopicId "{{user.tke_event_topic_id}}" \
  --From {{user.time_start_epoch}} \
  --To {{user.time_end_epoch}} \
  --QueryString "cluster_id:{{user.cluster_id}} AND (reason:ScalingReplicaSet OR reason:RollingUpdate OR type:Warning) AND involvedObject.kind:(Deployment OR StatefulSet OR DaemonSet)" \
  --Limit 100
```

Map records to `change_type=deploy` when `reason` contains `RollingUpdate`, `ScalingReplicaSet`, or image/version fields change.

### Step 3: Optional app config change logs

When `{{user.app_log_topic_id}}` is configured:

```bash
tccli cls SearchLog \
  --TopicId "{{user.app_log_topic_id}}" \
  --From {{user.time_start_epoch}} \
  --To {{user.time_end_epoch}} \
  --QueryString "(config changed OR configuration reload OR feature flag OR rollout) AND namespace:{{user.namespace}}" \
  --Limit 50
```

### Step 4: Inventory delta (best-effort)

Compare TKE `DescribeAddon` / `DescribeClusterNodePools` snapshots only when two time-bounded reads are feasible within the same session; otherwise skip and note `inventory_delta: unavailable`.

## 3. Change Correlation Window

| Parameter | Default | Config key |
|---|---|---|
| Lead window (change before symptom) | 15 min | `change_correlation.lead_window_minutes` |
| Lag window (symptom after change) | 30 min | `change_correlation.lag_window_minutes` |
| Min confidence for change-as-root | HIGH evidence + symptom within lag | — |

A change is **temporally correlated** when:

```
change.timestamp <= symptom.first_fire <= change.timestamp + lag_window
AND change.timestamp >= symptom.first_fire - lead_window
```

## 4. Rule F: Post-Change Regression

Apply when symptoms appear within the correlation window after a detected change.

| Evidence Layer | Signal | Scoring |
|---|---|---|
| Change | `deploy` / `config` / `scale` in lead window | Trigger (+3 if HIGH confidence mapping) |
| Pod | CrashLoopBackOff, restart spike, OOMKilled after change | +2 if pod workload matches change resource |
| CLB | 5xx / HealthCheckFail after change | +1 symptom if backend serves changed workload |
| Node | NodeNotReady after change | +1 if change was node-pool scale or CVM reboot |
| Metric | Error rate / latency spike after change timestamp | +1 if spike starts within 10 min of change |
| Baseline | Node/CVM metrics normal before change | +1 supports regression (not capacity) |

### Hypotheses

| ID | Narrative | Root entity | When HIGH |
|---|---|---|---|
| **F1** | Deployment/config change caused app regression → pod crash → CLB 5xx | `deployment` / `workload` | Deploy event + matching workload CrashLoop + node metrics normal |
| **F2** | CLB/backend config change caused 5xx without pod crash | `clb` | `ModifyListener*` / weight change + 5xx without pod restart |
| **F3** | Node pool scale / CVM reboot caused transient unavailability | `node_pool` / `cvm` | Scale/reboot event + NodeNotReady within lag window |
| **F4** | Network/SG change blocked traffic | `security_group` / `network` | SG/route change + connection timeout/refused pattern; merge with Rule G ([`network-rca.md`](network-rca.md)) |
| **F5** | Change unrelated (coincidental) | — | Change exists but topology/time do not link; score < 2 |

### Verification steps (read-only)

```bash
tccli cloudaudit LookUpEvents --StartTime {{user.time_start_epoch}} --EndTime {{user.time_end_epoch}} --MaxResults 100
tccli cls SearchLog --TopicId "{{user.tke_event_topic_id}}" --QueryString "involvedObject.name:{{user.workload}} AND reason:RollingUpdate"
tccli tke DescribeClusterNodePools --ClusterId "{{user.cluster_id}}"
tccli clb DescribeTargets --LoadBalancerId "{{user.load_balancer_id}}"
```

## 5. Hypothesis Scoring Integration

Merge Rule F scores with existing Rules A–E in [`multi-source-rca.md`](multi-source-rca.md) §3:

| Factor | Points | Notes |
|---|---|---|
| Change precedes symptom (lead-lag valid) | +3 | Required for change-as-root HIGH |
| Workload/topology match | +2 | Same `namespace/workload` or `load_balancer_id` |
| Symptom onset within lag window | +1 | Time coincidence |
| Metrics normal pre-change | +1 | Supports regression vs capacity |
| Conflicting change (multiple deploys) | -1 | Lower confidence; list all candidates |

**Change-as-root HIGH** requires: total score ≥ 5 including the +3 lead-lag factor, and no higher-scoring infrastructure hypothesis (Rules A–E) without change linkage.

Populate RCA Bundle fields:

```json
"change_timeline": [ /* normalized Change Evidence Model entries, time-sorted */ ],
"likely_change_trigger": {
  "change_id": "chg-20260609-001",
  "change_type": "deploy",
  "resource_id": "api-deploy",
  "timestamp": "2026-06-09T10:02:00+08:00",
  "confidence": "HIGH",
  "hypothesis_id": "F1"
}
```

Set `likely_change_trigger` to `null` when no change evidence is collected or best candidate score < 3.

## 6. Delegation

| Change type | Read evidence from | Delegate mutation fix to |
|---|---|---|
| `deploy` / workload | CLS K8s events + TKE | `qcloud-tke-ops` (rollback rollout); app owner for code |
| `config` CLB | CloudAudit + CLB Describe* | `qcloud-clb-ops` |
| `network` | CloudAudit + VPC | `qcloud-vpc-ops` |
| `scale` / node pool | CloudAudit + TKE | `qcloud-tke-ops` |
| `credential` | CloudAudit | `qcloud-cam-ops` |
| `alarm_policy` | CloudAudit + Monitor | `qcloud-monitor-ops` |

## 7. Changelog

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-06-09 | Initial release — Change Evidence Model, CloudAudit/CLS collection, Rule F post-change regression, lead-lag windows, RCA Bundle `change_timeline` / `likely_change_trigger` integration |
