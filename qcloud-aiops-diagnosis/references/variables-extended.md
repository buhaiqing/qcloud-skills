# Extended Variables — AIOps Diagnosis

Optional and derived placeholders. Core variables remain in [`SKILL.md`](../SKILL.md#variables).

| Variable | Source | Description | Example |
|----------|--------|-------------|---------|
| `{{user.tke_event_logset_id}}` | User | CLS logset for TKE K8s events | `logset-xxxxxx` |
| `{{user.tke_event_topic_id}}` | User | CLS topic for TKE events | `topic-xxxxxx` |
| `{{user.node_pool_id}}` | User | TKE node pool for capacity detail | `np-xxxxxx` |
| `{{user.addon_name}}` | User | TKE addon for degradation analysis | `coredns` |
| `{{user.pod_cpu_filter}}` | User | Required for degraded `DescribePodsBySpec` | `0.5` |
| `{{user.pod_memory_filter}}` | User | Required for degraded `DescribePodsBySpec` | `1` |
| `{{user.load_balancer_id}}` | User | CLB for 5xx/backend correlation | `lb-xxxxxx` |
| `{{user.instance_id}}` | User | CVM for node-level RCA | `ins-xxxxxx` |
| `{{user.namespace}}` | User | K8s namespace for Rule F | `prod` |
| `{{user.workload}}` | User | Deployment/StatefulSet for Rule F | `api-deploy` |
| `{{user.app_log_topic_id}}` | User | CLS app log topic | `topic-xxxxxx` |
| `{{user.baseline_yesterday_start}}` | Derived | `time_start` − 24h (ISO) | `2026-06-08T10:00:00+08:00` |
| `{{user.baseline_yesterday_end}}` | Derived | `time_end` − 24h (ISO) | `2026-06-08T11:00:00+08:00` |
| `{{user.baseline_week_start}}` | Derived | `time_start` − 7d (ISO) | `2026-06-02T10:00:00+08:00` |
| `{{user.baseline_week_end}}` | Derived | `time_end` − 7d (ISO) | `2026-06-02T11:00:00+08:00` |
| `{{user.anomaly_mode}}` | User | `baseline_primary` (default) or `static_only` | `baseline_primary` |
| `{{user.vpc_id}}` | User | VPC for Rule G | `vpc-xxxxxx` |
| `{{user.security_group_id}}` | User | Optional SG | `sg-xxxxxx` |
| `{{user.subnet_id}}` | User | Optional subnet | `subnet-xxxxxx` |
| `{{user.business_criticality}}` | User | Impact tier P0–P3 | `P1` |
| `{{user.slo_name}}` | User | SLO / Monitor policy name | `api-latency-slo` |
| `{{user.feedback_was_accurate}}` | User | Post-incident feedback | `true` |
| `{{user.feedback_actual_root_cause}}` | User | Verified root cause if different | `Disk full` |
| `{{user.mask_resource_ids}}` | User | Mask IDs in KB export | `false` |
| `{{user.bucket_name}}` | User | COS bucket short name (Rule K) | `my-bucket` |
| `{{user.app_id}}` | User/Derived | COS app id for Monitor bucket dimension | `1250000000` |
| `{{user.function_name}}` | User | SCF function name (Rule O) | `my-function` |
| `{{user.scf_namespace}}` | User | SCF namespace (default `default`) | `default` |
| `{{user.domain}}` | User | CDN加速域名 (Rule P) | `cdn.example.com` |
| `{{user.auto_dispatch_inspection}}` | Config | F1: auto inspection on finops HIGH | `true` |

Handoff payloads: see [`cross-skill-orchestration.md`](cross-skill-orchestration.md) §2; validate against `assets/finops-handoff.schema.json` and `assets/inspection-handoff.schema.json`.
