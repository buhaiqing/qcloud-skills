# Well-Architected Review — Troubleshooting

## Delegation failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| `WORKER_UNAVAILABLE` | Product skill not loaded | Install skill; re-run with correct `user.products` |
| `SCHEMA_MISMATCH` | Worker missing `product_assessment` fields | Fix worker per [worker-output-schema.md](worker-output-schema.md) |
| `DELEGATION_VIOLATION` | Orchestrator ran inline `tccli` | Remove direct CLI; delegate-to worker skill |
| Empty aggregation | All workers ERROR | Check credentials; see worker Error Code Reference |

## Worker partial failure

- Continue with successful workers; mark failed products **NOT ASSESSED**
- Include worker `errors[]` and `RequestId` in final report trace

## Cross-product gaps

- CVM multi-AZ but CLB single-AZ backends → see [cross-product-analysis.md](cross-product-analysis.md)
- FinOps cost spike without monitor idle data → delegate-to `qcloud-monitor-ops` worker

## Credential failures

- Verify env vars exist (never echo SecretKey)
- Workers inherit orchestrator credentials

## Pagination

- Workers responsible for Offset loops — orchestrator does not paginate

## Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-06-09 | Initial |
| 1.1.0 | 2026-06-09 | Orchestrator + Worker delegation troubleshooting |
