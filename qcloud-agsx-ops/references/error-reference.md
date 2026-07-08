# AGSX Error Code Reference (TE-6)

This file contains the AGSX-specific error code taxonomy, moved from SKILL.md (TE-6: Token Efficiency).

---

## Error Code Reference (10 Product-Specific Codes)

| Code | Meaning | Retry? | Agent Action |
|------|---------|--------|--------------|
| `InvalidParameter` | Parameter validation failed | No | Fix parameter; retry with correct value |
| `ResourceNotFound` | Target resource not found | No | Verify resource ID; suggest Describe |
| `ResourceInsufficient` | Quota or capacity exhausted | No | HALT; request quota increase |
| `InvalidSecretKey` | Credential invalid | No | HALT; fix credentials via CAM |
| `RequestLimitExceeded` | API rate limit | Yes (3×) | Exponential backoff |
| `InternalError` | Server-side error | Yes (3×) | Retry 2s/4s/8s; escalate with RequestId |
| `OperationConflict` | Concurrent operation conflict | Yes (3×, 30s) | Wait; retry after stable state |
| `UnauthorizedOperation` | CAM policy denies action | No | HALT; grant `ags:*` permission |
| `UnsupportedOperation` | API not supported in region | No | Switch to supported region |
| `QuotaExceeded` | Account quota reached | No | HALT; apply for quota increase |
