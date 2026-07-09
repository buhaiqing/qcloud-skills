# API Gateway Troubleshooting

## Failure patterns

| Symptom | Likely cause | Fix |
|---|---|---|
| `ResourceNotFound.InvalidService` | Wrong/expired service ID | Re-list via `DescribeServicesStatus` |
| `ResourceNotFound.InvalidApi` | Wrong API ID | Re-list via `DescribeApisStatus` |
| `LimitExceeded.ServiceLimitExceeded` | Service quota hit | Raise quota in console → `qcloud-cam-ops` for permission |
| `LimitExceeded.ApiLimitExceeded` | API quota per service hit | Split service or raise quota |
| `UnsupportedOperation.ServiceInUse` | Delete blocked by child APIs / bindings | Delete all APIs, unbind domains/usage plans first |
| `FailedOperation.ServiceInUse` | Concurrent release/delete in progress | Wait 30s, retry |
| `InvalidParameterValue.CertificateId` | Bad TLS cert | Verify cert in `qcloud-ssl-ops` |
| `RequestLimitExceeded` | Throttled | Exponential backoff (2s,4s,8s) |

## Delete blocked — recovery order

1. `UnReleaseService` from all environments (test/prepub/release).
2. `UnBindSubDomain` / delete custom domains.
3. `DeleteApi` for each API in the service.
4. `DeleteService --SkipVerification 0`.

## Release to `release` went wrong

- `UnReleaseService --EnvironmentName release` to roll back to previous version.
- Verify previous `DescribeServiceReleaseVersion` before re-release.
