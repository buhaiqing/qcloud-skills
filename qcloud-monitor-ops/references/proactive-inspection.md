# Monitor Proactive Inspection

> **delegate-from:** `qcloud-proactive-inspection` — read-only discovery/collection for **monitor**.
> Do **not** mutate resources. Architecture scoring → `qcloud-well-architected-review`.

## Discovery [inspection-readonly]

| Resource | Primary API |
|----------|-------------|
| Inventory | `tccli monitor DescribeAlarmPolicies` (paginate `--Limit 100`) |

SDK fallback: see product `references/api-sdk-usage.md` or `references/cli-usage.md`.

## Collection

| Signal | Source |
|--------|--------|
| Utilization | `GetMonitorData` via `qcloud-monitor-ops` or product metrics |
| Config state | `DescribeAlarmPolicies` response fields (status, backup, expiry) |

## Detection rules

| Rule ID | Check | Warning | Critical |
|---------|-------|---------|----------|
| monitor-001 | Prod resource no alarm | Missing CPU alarm | No alarm on critical tier |
| monitor-002 | Alarm in ALARM long | >24h unacked | >72h unacked |

## Output to orchestrator

Return `{{output.inspection_findings}}` per [inspection-output-schema.md](../../qcloud-proactive-inspection/references/inspection-output-schema.md).

| Field | Value |
|-------|-------|
| `skill_id` | `qcloud-monitor-ops` |
| `product` | `monitor` |
| Finding `id` | `monitor-NNN` (matches rule ID) |

Mask credentials in `trace.commands`.

## References

- [qcloud-proactive-inspection/SKILL.md](../../qcloud-proactive-inspection/SKILL.md)
- Product `SKILL.md` § Trigger & Scope
