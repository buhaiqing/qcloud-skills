# CAM Well-Architected Assessment

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
