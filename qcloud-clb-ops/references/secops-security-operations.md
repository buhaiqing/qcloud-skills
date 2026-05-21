# CLB SecOps Security Operations

## Overview

Security operations patterns for CLB (Load Balancer).

---

## 1. CAM Permissions

### Minimum CAM Policy

```json
{
  "version": "2.0",
  "statement": [
    {
      "effect": "allow",
      "action": [
        "clb:DescribeLoadBalancers",
        "clb:DescribeListeners",
        "clb:DescribeTargets",
        "clb:DescribeTargetHealth"
      ],
      "resource": "*"
    },
    {
      "effect": "allow",
      "action": [
        "clb:CreateLoadBalancer",
        "clb:DeleteLoadBalancer",
        "clb:ModifyLoadBalancerAttributes"
      ],
      "resource": "qcs:clb:*:*:*/*",
      "condition": {
        "string_equal": {
          "qcs:resource_tag": ["Environment:production"]
        }
      }
    }
  ]
}
```

### Role-Based Access

| Role | Permissions | Use Case |
|------|--------------|----------|
| **CLB-Viewer** | Describe* only | Monitoring, auditing |
| **CLB-Operator** | Describe*, RegisterTargets, DeregisterTargets | Backend management |
| **CLB-Admin** | All actions | Full management |

---

## 2. Security Group Configuration

### CLB Security Group Best Practices

| Port | Source | Protocol | Security Level |
|------|--------|----------|----------------|
| 80 | 0.0.0.0/0 | HTTP | Public web |
| 443 | 0.0.0.0/0 | HTTPS | Public secure web |
| 8080 | 10.0.0.0/8 | HTTP | Internal only |
| 22 | Office IP only | SSH | Never public |
| 3306 | VPC CIDR only | MySQL | Never public |

### Security Group Template

```yaml
clb_security_group:
  name: "clb-web-sg"
  
  inbound_rules:
    - port: 80
      protocol: tcp
      cidr: "0.0.0.0/0"  # HTTP public
      action: accept
      
    - port: 443
      protocol: tcp  
      cidr: "0.0.0.0/0"  # HTTPS public
      action: accept
      
    - port: 8080
      protocol: tcp
      cidr: "10.0.0.0/8"  # Internal only
      action: accept
      
  outbound_rules:
    - port: all
      protocol: all
      cidr: "10.0.0.0/8"  # Backend servers only
      action: accept
```

### Security Group Audit

```python
def audit_clb_security_groups(sg_rules: List) -> List[SecurityIssue]:
    """Audit CLB security group for risks"""
    issues = []
    
    for rule in sg_rules:
        # Check public database exposure
        db_ports = [3306, 5432, 6379, 27017]
        if rule.port in db_ports and rule.cidr == "0.0.0.0/0":
            issues.append({
                "severity": "CRITICAL",
                "issue": f"Database port {rule.port} exposed to public",
                "recommendation": "Restrict to VPC CIDR"
            })
        
        # Check SSH exposure
        if rule.port == 22 and rule.cidr == "0.0.0.0/0":
            issues.append({
                "severity": "HIGH",
                "issue": "SSH exposed to public",
                "recommendation": "Restrict to office IPs or VPN"
            })
    
    return issues
```

---

## 3. SSL/TLS Security

### Certificate Requirements

| Requirement | Implementation |
|-------------|----------------|
| TLS version | Use TLS 1.2+ minimum |
| Certificate renewal | Monitor expiry, auto-renew |
| Domain validation | Verify cert matches listener domain |
| Private key protection | Never expose private key |

### Certificate Checklist

| Check | Action |
|-------|--------|
| ✓ TLS 1.2+ enabled | Disable TLS 1.0/1.1 |
| ✓ Cert expiry < 30 days | Renew certificate |
| ✓ Domain matches | Verify cert domain |
| ✓ Private key secured | Use CAM/KMS |

---

## 4. Network Isolation

### VPC Architecture

```yaml
clb_vpc_isolation:
  public_subnet:
    cidr: 10.0.0.0/24
    resources: [CLB, NAT Gateway]
    
  app_subnet:
    cidr: 10.0.1.0/24
    resources: [Backend CVM]
    
  db_subnet:
    cidr: 10.0.2.0/24
    resources: [MySQL, Redis]
    
  rules:
    - CLB in public subnet
    - Backend in private subnet
    - Database in isolated subnet
    - CLB → Backend allowed
    - Public → Database blocked
```

---

## 5. Credential Security

### API Key Management

| Practice | Implementation |
|----------|----------------|
| Environment variables | `TENCENTCLOUD_SECRET_ID/KEY` |
| Never log | Mask in all outputs |
| CAM role preferred | Over static keys |
| Rotation | Every 90 days |

### Credential Masking

```bash
# Safe: Check existence only
test -n "$TENCENTCLOUD_SECRET_KEY" && echo "✅ Key configured"

# Unsafe: Never do this
echo $TENCENTCLOUD_SECRET_KEY  # ❌ SECURITY VIOLATION
```

---

## 6. Audit Logging

### CloudAudit Integration

```bash
# Query CLB-related audit logs
tccli cloudaudit LookUpEvents \
  --StartTime "2026-05-01T00:00:00+08:00" \
  --EndTime "2026-05-21T00:00:00+08:00" \
  --Resource "qcs:clb:*:*:lb-xxx"
```

### Key Audit Events

| Event | Security Level | Action |
|-------|----------------|--------|
| CreateLoadBalancer | Medium | Log creation |
| DeleteLoadBalancer | High | Alert + log |
| RegisterTargets | Medium | Log binding |
| ModifyListener | Medium | Log config change |

---

## 7. Compliance Checklist

| # | Check | Status |
|---|-------|--------|
| 1 | CAM least privilege | ✓ |
| 2 | No public database ports | ✓ |
| 3 | SSH restricted | ✓ |
| 4 | TLS 1.2+ enabled | ✓ |
| 5 | Certificate valid | ✓ |
| 6 | Security groups reviewed | ✓ |
| 7 | VPC isolation | ✓ |
| 8 | Audit logging enabled | ✓ |
| 9 | Credentials masked | ✓ |
| 10 | Key rotation policy | ✓ |