# CLS Proactive Inspection

> **delegate-from:** `qcloud-proactive-inspection` — read-only discovery/collection for **cls**.
> Do **not** mutate resources. Architecture scoring → `qcloud-well-architected-review`.

## Discovery [inspection-readonly]

| Resource | Primary API |
|----------|-------------|
| Inventory | `tccli cls DescribeLogsets` (paginate `--Limit 100`) |

SDK fallback: see product `references/api-sdk-usage.md` or `references/cli-usage.md`.

## Collection

| Signal | Source |
|--------|--------|
| Utilization | `GetMonitorData` via `qcloud-monitor-ops` or product metrics |
| Config state | `DescribeLogsets` response fields (status, backup, expiry) |

## Detection rules

| Rule ID | Check | Warning | Critical |
|---------|-------|---------|----------|
| cls-001 | Ingest failure | Agent offline hosts | >20% hosts not shipping |
| cls-002 | Retention unbounded | >90d no archive | Compliance risk |

## Output to orchestrator

Return `{{output.inspection_findings}}` per [inspection-output-schema.md](../../qcloud-proactive-inspection/references/inspection-output-schema.md).

| Field | Value |
|-------|-------|
| `skill_id` | `qcloud-cls-ops` |
| `product` | `cls` |
| Finding `id` | `cls-NNN` (matches rule ID) |

Mask credentials in `trace.commands`.

## References

- [qcloud-proactive-inspection/SKILL.md](../../qcloud-proactive-inspection/SKILL.md)
- Product `SKILL.md` § Trigger & Scope
