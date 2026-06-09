# SCF Proactive Inspection

> **delegate-from:** `qcloud-proactive-inspection` — read-only discovery/collection for **scf**.
> Do **not** mutate resources. Architecture scoring → `qcloud-well-architected-review`.

## Discovery [inspection-readonly]

| Resource | Primary API |
|----------|-------------|
| Inventory | `tccli scf ListFunctions` (paginate `--Limit 100`) |

SDK fallback: see product `references/api-sdk-usage.md` or `references/cli-usage.md`.

## Collection

| Signal | Source |
|--------|--------|
| Utilization | `GetMonitorData` via `qcloud-monitor-ops` or product metrics |
| Config state | `ListFunctions` response fields (status, backup, expiry) |

## Detection rules

| Rule ID | Check | Warning | Critical |
|---------|-------|---------|----------|
| scf-001 | Error rate | >1% invocations | >5% invocations |
| scf-002 | No DLQ on async | Async without DLQ | Prod async no DLQ |

## Output to orchestrator

Return `{{output.inspection_findings}}` per [inspection-output-schema.md](../../qcloud-proactive-inspection/references/inspection-output-schema.md).

| Field | Value |
|-------|-------|
| `skill_id` | `qcloud-scf-ops` |
| `product` | `scf` |
| Finding `id` | `scf-NNN` (matches rule ID) |

Mask credentials in `trace.commands`.

## References

- [qcloud-proactive-inspection/SKILL.md](../../qcloud-proactive-inspection/SKILL.md)
- Product `SKILL.md` § Trigger & Scope
