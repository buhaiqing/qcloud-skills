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

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-apigw-ops` |
| `product` | `apigw` |
| Finding `id` pattern | `apigw-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

### Pillar → checklist map

| `pillars` key | Checklist source in this document |
|---------------|-------------------------------------|
| `reliability` | 可靠性 (Reliability) section |
| `security` | 安全性 (Security) section |
| `cost` | 成本 (Cost) section |
| `efficiency` | 效率 (Efficiency) section |

### Example `{{output.product_assessment}}`

```json
{
  "skill_id": "qcloud-apigw-ops",
  "product": "apigw",
  "region": "ap-guangzhou",
  "scope": "service-wide",
  "assessment_date": "2026-07-10T10:00:00+08:00",
  "status": "OK",
  "partial": false,
  "resource_count": 4,
  "pillars": {
    "reliability": {
      "score": 80,
      "status": "assessed",
      "findings": [
        {
          "id": "apigw-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "No rollback drill for release environment",
          "evidence": "ReleaseService used without verified UnReleaseService rollback procedure",
          "recommendation": "Document and periodically drill UnReleaseService rollback per environment",
          "effort": "medium"
        }
      ]
    },
    "security": {
      "score": 75,
      "status": "assessed",
      "findings": [
        {
          "id": "apigw-sec-001",
          "severity": "Medium",
          "confidence": "MEDIUM",
          "title": "AuthType=NONE on public APIs",
          "evidence": "APIs exposed without APP/OAUTH auth",
          "recommendation": "Set AuthType to APP or OAUTH for public-facing APIs",
          "effort": "medium"
        }
      ]
    },
    "cost": {
      "score": 70,
      "status": "assessed",
      "findings": []
    },
    "efficiency": {
      "score": 82,
      "status": "assessed",
      "findings": []
    }
  },
  "recommendations": [
    {
      "priority": "High",
      "pillar": "reliability",
      "action": "Document and drill UnReleaseService rollback procedure",
      "effort": "medium"
    },
    {
      "priority": "Medium",
      "pillar": "security",
      "action": "Switch public APIs from AuthType=NONE to APP/OAUTH",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [
      "tccli apigw DescribeServicesStatus (SecretKey=<masked>)",
      "tccli apigw DescribeApiInfo (SecretKey=<masked>)"
    ],
    "request_ids": [
      "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    ]
  },
  "errors": []
}
```
