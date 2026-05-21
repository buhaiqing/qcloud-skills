# Security Pillar — Tencent Cloud Well-Architected Framework

## Overview

The Security pillar ensures Tencent Cloud resources follow the principle of least privilege, proper credential management, network isolation, and encryption at rest/in transit.

## 1. CAM (Cloud Access Management) Permissions

### 1.1 Minimum Permissions Assessment

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| Role-based access | `tccli cam ListAttachedRolePolicies` | Roles used instead of direct user permissions |
| Least privilege | Review policy documents | Policies grant only required permissions |
| No wildcard `*` | Search policy documents | No `action: "*"` or `resource: "*"` unless required |

### 1.2 CAM Policy Template

```json
{
  "version": "2.0",
  "statement": [
    {
      "action": [
        "cvm:DescribeInstances",
        "cvm:RunInstances"
      ],
      "effect": "allow",
      "resource": "*"
    }
  ]
}
```

## 2. Credential Management

| Requirement | Assessment | Pass Criteria |
|-------------|-----------|---------------|
| Environment variables | Use `TENCENTCLOUD_SECRET_ID/KEY` | Not hardcoded in scripts |
| Credential masking | No SecretKey in output/logs | All masking enforced |
| Key rotation | API key age < 90 days | Rotation policy exists |
| MFA enabled | CAM user MFA status | MFA enabled for all human accounts |

## 3. Network Isolation

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| VPC isolation | `tccli vpc DescribeVpcs` | Resources in private VPC, not default |
| Security groups | `tccli vpc DescribeSecurityGroups` | Ingress rules restrict access |
| Network ACLs | `tccli vpc DescribeNetworkAcls` | Subnet-level filtering enabled |
| Public IP exposure | `DescribeInstances` output | Only necessary resources have public IPs |

## 4. Encryption

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| Data at rest | `Describe*` for encryption status | SSE enabled for storage products |
| Data in transit | HTTPS/TLS check | TLS 1.2+ required |
| Key management | KMS integration Check | Customer-managed keys where required |

## 5. Security Assessment Score

| Score | Criteria |
|-------|----------|
| 90-100 | Least privilege, MFA enabled, encrypted at rest + transit, no public IPs |
| 70-89 | Role-based access, encryption in transit, some public IPs justified |
| 50-69 | Basic security groups, password auth, no encryption at rest |
| < 50 | Default VPC, open security groups, credentials in code |

## Common Security Anti-Patterns

| Anti-Pattern | Risk | Remediation |
|-------------|------|-------------|
| `0.0.0.0/0` security groups | Critical | Restrict to specific CIDRs |
| Root account for daily ops | Critical | Create role-based accounts |
| Credentials in git repos | Critical | Use environment variables + vault |
| No MFA on privileged accounts | High | Enable MFA immediately |
| Default passwords on DBs | High | Change and enforce rotation |
