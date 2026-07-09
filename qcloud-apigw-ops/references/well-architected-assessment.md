# API Gateway Well-Architected Assessment

Maps `qcloud-apigw-ops` operations to Tencent Cloud Well-Architected Framework pillars.

## 可靠性 (Reliability)

- **Multi-environment release**: publish to `test` → `prepub` → `release`; verify at each step.
- **Rollback**: `UnReleaseService` reverts an environment to the prior version.
- **Graceful decommission**: un-release before delete to avoid client-facing 5xx.

## 安全性 (Security)

- **AuthType**: prefer `APP` (secretId + key) or `OAUTH` over `NONE` for sensitive APIs.
- **IP Strategy**: restrict caller CIDRs for internal APIs.
- **Credential masking**: never log `SecretKey`; use `{{env.TENCENTCLOUD_SECRET_KEY}}`.
- **CAM scoping**: grant only `apigateway:*` actions required; delegate policy edits to `qcloud-cam-ops`.

## 成本 (Cost)

- **Usage plans**: set `MaxRequestNumPreSec` and `MaxRequestNum` to cap cost and abuse.
- **Waste detection**: delete unused services/APIs and unbound usage plans.

## 效率 (Efficiency)

- **Batch bind**: bind a usage plan to many APIs via `BindEnvironment --ApiIds`.
- **CI/CD**: script `ReleaseService` per environment in pipelines.
- **Plugins**: reuse auth/CORS/throttling plugins across APIs instead of per-API config.
