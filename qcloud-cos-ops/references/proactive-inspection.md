# COS Proactive Inspection

> **delegate-from:** `qcloud-proactive-inspection` — read-only discovery/collection for **cos**.
> Do **not** mutate resources. Architecture scoring → `qcloud-well-architected-review`.

## Discovery [inspection-readonly]

| Resource | Primary API |
|----------|-------------|
| Inventory | Python SDK `qcloud_cos.CosS3Client.list_buckets` / `list_objects` (paginate `Marker`/`MaxKeys`) — no `tccli cos` service |

SDK fallback: see product `references/api-sdk-usage.md` or `references/cli-usage.md`.

## Collection

| Signal | Source |
|--------|--------|
| Utilization | `GetMonitorData` via `qcloud-monitor-ops` or product metrics |
| Config state | `ListBuckets` response fields (status, backup, expiry) |

## Detection rules

| Rule ID | Check | Warning | Critical |
|---------|-------|---------|----------|
| cos-001 | Public bucket ACL | Public read | Public write |
| cos-002 | No lifecycle on infrequent bucket | Large std storage | Unbounded growth |

## Output to orchestrator

Return `{{output.inspection_findings}}` per [inspection-output-schema.md](../../qcloud-proactive-inspection/references/inspection-output-schema.md).

| Field | Value |
|-------|-------|
| `skill_id` | `qcloud-cos-ops` |
| `product` | `cos` |
| Finding `id` | `cos-NNN` (matches rule ID) |

Mask credentials in `trace.commands`.

## References

- [qcloud-proactive-inspection/SKILL.md](../../qcloud-proactive-inspection/SKILL.md)
- Product `SKILL.md` § Trigger & Scope
