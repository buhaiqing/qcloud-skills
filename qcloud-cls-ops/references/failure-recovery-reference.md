# Failure Recovery Reference

> Canonical error taxonomy for CLS operations. Used by SKILL.md execution flows.
> Source: [SKILL.md Error Code Reference](../SKILL.md#error-code-reference)

## Error Recovery Patterns

| Error pattern | Retry | Recovery |
|---|---|---|
| `InvalidParameter.*` (name/format) | 0 | Fix format per API spec; retry once |
| `InvalidParameter.IndexRule` | 0 | Fix index rule format; refer to API spec |
| `InvalidParameter.QuerySyntax` | 0 | Fix query syntax |
| `InvalidParameter.TopicId` | 0 | HALT; verify CLS topic ID |
| `InvalidParameter.Bucket` | 0 | Verify bucket name and region |
| `ResourceInUse.*` | 0 | Use unique name or Modify/delete existing first |
| `ResourceNotFound.*` | 0 | HALT; verify resource ID |
| `QuotaExceeded.*` | 0 | HALT; request quota increase |
| `LimitExceeded.SearchTimeRange` | 0 | Reduce to max 31 days |
| `RequestLimitExceeded` | 3 | Exponential backoff |
| `OperationConflict` | 3, 30s backoff | Wait; retry |
| `InternalError` | 3, 2s/4s/8s | Retry; HALT if persists |
| `UnauthorizedOperation` | 0 | HALT; check CAM permissions |

## Operation-Specific Overrides

| Operation | Unique error | Override |
|---|---|---|
| CreateLogset | `InvalidParameter.LogsetName` | 0 retries — fix name format |
| CreateTopic | `InvalidParameter.TopicName` | 0 retries — fix name format |
| CreateMachineGroup | `ResourceInUse.GroupName` | 0 retries — name in use; use unique |
| CreateConfig | `InvalidParameter.ConfigName` / `InvalidParameter.InputConfig` | 0 retries — fix format |
| ImportCOSAccessLogs | `InvalidParameter.TopicId` | 0 retries — verify topic ID |
| CreateCosRecharge | `ResourceInUse.CosRechargeAlreadyExist` | Use ModifyCosRecharge or delete first |
| DeleteLogset | `ResourceNotFound.LogsetNotExist` | No-op (already deleted) |
| DeleteTopic | `ResourceNotFound.TopicNotExist` | No-op (already deleted) |
| DeleteIndex | `ResourceNotFound.IndexNotExist` | No-op (already deleted) |
