# Extended Variables — AIOps Diagnosis

Optional and derived placeholders. Core variables remain in [`SKILL.md`](../SKILL.md#variables).

| Variable | Source | Example |
|----------|--------|---------|
| `{{user.tke_event_logset_id}}` | User | `logset-xxxxxx` |
| `{{user.tke_event_topic_id}}` | User | `topic-xxxxxx` |
| `{{user.node_pool_id}}` | User | `np-xxxxxx` |
| `{{user.addon_name}}` | User | `coredns` |
| `{{user.pod_cpu_filter}}` | User | `0.5` |
| `{{user.pod_memory_filter}}` | User | `1` |
| `{{user.load_balancer_id}}` | User | `lb-xxxxxx` |
| `{{user.instance_id}}` | User | `ins-xxxxxx` |
| `{{user.namespace}}` | User | `prod` |
| `{{user.workload}}` | User | `api-deploy` |
| `{{user.app_log_topic_id}}` | User | `topic-xxxxxx` |
| `{{user.baseline_yesterday_start}}` | Derived | `2026-06-08T10:00:00+08:00` |
| `{{user.baseline_yesterday_end}}` | Derived | `2026-06-08T11:00:00+08:00` |
| `{{user.baseline_week_start}}` | Derived | `2026-06-02T10:00:00+08:00` |
| `{{user.baseline_week_end}}` | Derived | `2026-06-02T11:00:00+08:00` |
| `{{user.anomaly_mode}}` | User | `baseline_primary` |
| `{{user.vpc_id}}` | User | `vpc-xxxxxx` |
| `{{user.security_group_id}}` | User | `sg-xxxxxx` |
| `{{user.subnet_id}}` | User | `subnet-xxxxxx` |
| `{{user.business_criticality}}` | User | `P1` |
| `{{user.slo_name}}` | User | `api-latency-slo` |
| `{{user.feedback_was_accurate}}` | User | `true` |
| `{{user.feedback_actual_root_cause}}` | User | `Disk full` |
| `{{user.mask_resource_ids}}` | User | `false` |
| `{{user.bucket_name}}` | User | `my-bucket` |
| `{{user.app_id}}` | User/Derived | `1250000000` |
| `{{user.function_name}}` | User | `my-function` |
| `{{user.scf_namespace}}` | User | `default` |
| `{{user.domain}}` | User | `cdn.example.com` |
| `{{user.auto_dispatch_inspection}}` | Config | `true` |

Handoff payloads: see [`cross-skill-orchestration.md`](cross-skill-orchestration.md) §2; validate against `assets/finops-handoff.schema.json` and `assets/inspection-handoff.schema.json`.
