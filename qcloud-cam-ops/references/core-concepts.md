# CAM Core Concepts

## Architecture

CAM (Cloud Access Management) provides identity and access management for Tencent Cloud resources through four entities:

### Entity Relationships
```
User ─→ Group ─→ Policy
  │               ↑
  └───── Role ────┘
        ↑
  AssumeRole (service/application)
```

### Entity Definitions

| Entity | Description | Max Count |
|--------|-------------|-----------|
| User | Individual identity (human or service account) | 500 per account |
| Group | Collection of users with shared permissions | 100 per account |
| Role | Identity assumed by trusted entities | 500 per account |
| Policy | JSON document defining permissions | 2000 per account |

## Policy Syntax

```json
{
  "version": "2.0",
  "statement": [
    {
      "sid": "AllowCVMReadOnly",
      "effect": "allow",
      "action": ["cvm:Describe*"],
      "resource": ["*"],
      "condition": {}
    }
  ]
}
```

### Policy Elements

| Element | Required | Description |
|---------|----------|-------------|
| version | Yes | Policy version ("2.0") |
| statement | Yes | Array of permission statements |
| statement[].sid | No | Statement identifier |
| statement[].effect | Yes | "allow" or "deny" |
| statement[].action | Yes | API operations (e.g., "cvm:DescribeInstances") |
| statement[].resource | Yes | Resource scope (e.g., "qcs:cvm:ap-guangzhou:*:instance/*") |
| statement[].condition | No | Conditional expressions |

## Permission Evaluation Logic

1. **Explicit deny** always wins — if any policy denies, access is denied
2. **Explicit allow** needed — at least one policy must allow the action
3. **No matching policy** = deny by default
4. **Policy precedence**: User policies + Group policies + Role (temporary) policies are combined

## Trust Policy

> Trust policies control **who can assume** a role. They are NOT permission policies.
> Confusing the two is the #1 CAM role-authoring mistake (see rubric §4 rule 4).

### Trust Policy Structure

```json
{
  "version": "2.0",
  "statement": [
    {
      "effect": "allow",
      "principal": {
        "service": ["cvm.tencentcloudapi.com"]   // TKE / CVM / CAM services
      },
      "action": ["sts:AssumeRole"],
      "resource": ["qcs::cam::uin/<account_id>:role/<role_name>"]
    }
  ]
}
```

### Principal Forms

| Form | Allows | Risk |
|---|---|---|
| `{"service": ["cvm.tencentcloudapi.com"]}` | Any CVM in the account | Low (service-scoped) |
| `{"service": ["cls.tencentcloudapi.com"]}` | Any CLS in the account | Low |
| `{"qcs": ["qcs::cam::uin/123456789:role/AdminRole"]}` | Specific cross-account role | Medium (verify the target account) |
| `{"qcs": ["*"]}` | **ANY Tencent Cloud account** | 🔴 **CRITICAL** — ABORT unless explicitly confirmed |

### Automated Principal=`*` Detection

```python
# ponytail: 3-line check, no dependency — matches rubric §4 rule 4
import json, sys
for f in sys.argv[1:]:
    doc = json.load(open(f))
    for s in doc.get("statement", []):
        p = s.get("principal", {})
        if "*" in str(p):
            print(f"BLOCKER: {f} — Principal=* found: {p}")
```

```bash
# Usage: python3 trust_check.py role_policy.json
# Exit 1 if Principal=* found (hook into GCL pre-flight)
```

---

## Common Policy Types

| Policy | Scope | Use Case |
|--------|-------|----------|
| QcloudFullAccess | All products | Admin |
| QcloudCVMFullAccess | CVM only | CVM admin |
| QcloudCVMReadOnlyAccess | CVM read-only | Auditor |
| QcloudCamReadOnlyAccess | CAM read-only | Security auditor |
| Custom policies | Product-specific | Least-privilege access |
