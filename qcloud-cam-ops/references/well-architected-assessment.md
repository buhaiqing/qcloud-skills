# CAM Well-Architected Assessment

> **Mode split:** `[assessment-readonly]` — Describe* / GetMonitorData only (Well-Architected worker).
> `[remediation-only]` — Create/Modify/Delete runbooks; **MUST NOT** execute when `{{user.mode}}=well-architected-readonly`.
> Worker JSON: **Worker Output Contract** at end of this file.

## Security Pillar Assessment

### Minimum CAM Permissions

| Operation | Required Actions | Recommended Policy |
|-----------|-----------------|-------------------|
| Read-only audit | `cam:Get*`, `cam:List*`, `cam:Describe*` | `QcloudCamReadOnlyAccess` |
| Policy management | `cam:CreatePolicy`, `cam:DeletePolicy`, `cam:UpdatePolicy` | Custom policy with specific actions |
| User management | `cam:AddUser`, `cam:DeleteUser`, `cam:GetUser`, `cam:ListUsers` | Custom policy |
| Role management | `cam:CreateRole`, `cam:DeleteRole`, `cam:AttachRolePolicy` | Custom policy |
| Full admin | All CAM actions | `QcloudCamFullAccess` |

### Credential Lifecycle

| Practice | Assessment | Recommendation |
|----------|-----------|----------------|
| API key rotation | Check key age via `ListApiKey` | Rotate keys every 90 days |
| MFA enforcement | Check user MFA status | Enable MFA for all human accounts |
| No hardcoded credentials | Scan scripts/repos | Use environment variables or vault |
| Role-based access | Check user attachment type | Use roles instead of direct permissions |

### Least-Privilege Enforcement

| Anti-Pattern | Risk | Fix |
|-------------|------|-----|
| `action: "*"` | Grants all permissions | Replace with specific actions |
| `resource: "*"` | Grants access to all resources | Scope to specific resources |
| No condition expressions | No time/IP restrictions | Add `DateLessThan`, `IpAddress` conditions |
| Shared accounts | No audit trail | Create individual accounts |

## SSO Integration

| Check | Assessment | Pass Criteria |
|-------|-----------|---------------|
| SAML provider configured | `GetSAMLProvider` | Provider exists, metadata valid |
| OIDC provider configured | `GetOIDCProvider` | Provider exists, client ID valid |
| Role trust relationship | `GetRole --RoleName <name>` | Role trusts identity provider |
| Session duration | Check provider config | Session timeout ≤ 12 hours |

## Scoring

| Score | Criteria |
|-------|----------|
| 90-100 | Least-privilege, MFA enabled, keys rotated quarterly, SSO configured |
| 70-89 | Role-based access, MFA for admins, keys < 180 days old |
| 50-69 | Mixed direct/role permissions, no MFA, keys > 180 days |
| < 50 | Wildcard permissions, shared accounts, hardcoded credentials |

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-cam-ops` |
| `product` | `cam` |
| Finding `id` pattern | `cam-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

### Pillar → checklist map

| `pillars` key | Checklist source in this document |
|---------------|-------------------------------------|
| `reliability` | N/A (typically skipped) |
| `security` | Security / least-privilege sections |
| `cost` | N/A (typically skipped) |
| `efficiency` | Automation sections (if any) |

### Populate rules

1. Include only pillar keys requested by orchestrator `{{user.pillars}}` (`all` = four keys).
2. `score = round(passed / applicable × 100)`; use `status=not_assessed` when data missing (omit score or null).
3. Each failed/warn checklist item → one `findings[]` entry with all six finding fields (§2.1 in schema).
4. `recommendations[]`: top 1–5 actions with `priority`, `pillar`, `action`, `effort` (§2.2 in schema).
5. `partial=true` when any pillar is `not_assessed`; top-level `status=PARTIAL`.
6. `trace.commands`: every read API call; mask credentials. `errors[]` on API failure (§3 in schema).
7. Local “Score Calculation” sections are for manual review only — **worker mode must emit this JSON**.

### Example `{{output.product_assessment}}`

```json
{
  "skill_id": "qcloud-cam-ops",
  "product": "cam",
  "region": "ap-guangzhou",
  "scope": "account-wide",
  "assessment_date": "2026-06-09T10:00:00+08:00",
  "status": "OK",
  "partial": false,
  "resource_count": 3,
  "pillars": {
    "reliability": {
      "score": null,
      "status": "skipped",
      "findings": []
    },
    "security": {
      "score": 75,
      "status": "assessed",
      "findings": [
        {
          "id": "cam-sec-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Wildcard action in policy",
          "evidence": "Policy contains action:*",
          "recommendation": "Replace wildcard with product-scoped actions",
          "effort": "medium"
        }
      ]
    },
    "cost": {
      "score": 72,
      "status": "assessed",
      "findings": []
    },
    "efficiency": {
      "score": 70,
      "status": "assessed",
      "findings": []
    }
  },
  "recommendations": [
    {
      "priority": "High",
      "pillar": "security",
      "action": "Replace wildcard with product-scoped actions",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [
      "tccli cam ListPolicies --Limit 100 (SecretKey=<masked>)"
    ],
    "request_ids": [
      "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    ]
  },
  "errors": []
}
```
