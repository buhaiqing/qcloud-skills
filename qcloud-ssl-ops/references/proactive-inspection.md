# SSL Proactive Inspection

> **delegate-from:** `qcloud-proactive-inspection` — read-only discovery/collection for **ssl**.
> Do **not** mutate resources. Architecture scoring → `qcloud-well-architected-review`.

## Discovery [inspection-readonly]

| Resource | Primary API |
|----------|-------------|
| Inventory | `tccli ssl DescribeCertificates` (paginate `--Limit 100`) |

SDK fallback: see product `references/api-sdk-usage.md` or `references/cli-usage.md`.

## Collection

| Signal | Source |
|--------|--------|
| Utilization | `GetMonitorData` via `qcloud-monitor-ops` or product metrics |
| Config state | `DescribeCertificates` response fields (status, backup, expiry) |

## Detection rules

| Rule ID | Check | Warning | Critical |
|---------|-------|---------|----------|
| ssl-001 | Cert expiry | <30d | <7d |
| ssl-002 | Cert not deployed | Unused cert | Prod domain no cert |

## Output to orchestrator

Return `{{output.inspection_findings}}` per [inspection-output-schema.md](../../qcloud-proactive-inspection/references/inspection-output-schema.md).

| Field | Value |
|-------|-------|
| `skill_id` | `qcloud-ssl-ops` |
| `product` | `ssl` |
| Finding `id` | `ssl-NNN` (matches rule ID) |

Mask credentials in `trace.commands`.

## References

- [qcloud-proactive-inspection/SKILL.md](../../qcloud-proactive-inspection/SKILL.md)
- Product `SKILL.md` § Trigger & Scope
