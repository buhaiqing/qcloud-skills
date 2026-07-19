# CVM SecOps Checklist

Security operations, compliance audit, credential rotation, and network isolation for CVM.

---

## Overview

SecOps for CVM focuses on:
1. Security audit log analysis
2. Credential rotation strategy
3. Security Group audit
4. Network isolation verification
5. Compliance checklist execution

---

## 1. Security Audit Logs

### 1.1 CloudAudit Query CLI

```bash
# Query audit events for CVM operations
tccli cloudaudit LookUpEvents \
  --StartTime 2026-05-01T00:00:00+08:00 \
  --EndTime 2026-05-21T00:00:00+08:00 \
  --MaxResults 100

# Filter by CVM-related events
tccli cloudaudit LookUpEvents \
  --StartTime 2026-05-01T00:00:00+08:00 \
  --EndTime 2026-05-21T00:00:00+08:00 \
  --ActionNames "[\"RunInstances\",\"TerminateInstances\",\"ModifyInstanceAttribute\"]"
```

### 1.2 Security-Relevant Events

| Event Category | Events | Risk Level |
|----------------|--------|------------|
| **Instance Lifecycle** | `RunInstances`, `TerminateInstances`, `StartInstances`, `StopInstances` | Medium |
| **Configuration Change** | `ModifyInstanceAttribute`, `ModifyInstancesProject` | Medium |
| **Security Group** | `CreateSecurityGroup`, `ModifySecurityGroupPolicies`, `DeleteSecurityGroup` | High |
| **Credential** | `CreateSecretKey`, `DeleteSecretKey` | Critical |
| **Key Pair** | `CreateKeyPair`, `DeleteKeyPairs`, `AssociateInstancesKeyPairs` | High |

### 1.3 Audit Log Analysis Script

```python
def analyze_audit_logs(events: List[AuditEvent]) -> SecurityAuditReport:
    # Analyze audit logs for security insights
    
    report = SecurityAuditReport()
    
    # Critical events
    critical_events = [
        'DeleteSecretKey', 'DeleteKeyPairs', 
        'DeleteSecurityGroup', 'TerminateInstances'
    ]
    
    critical_found = [e for e in events if e.action in critical_events]
    if critical_found:
        report.warnings.append({
            'type': 'critical_operations',
            'count': len(critical_found),
            'events': [e.action for e in critical_found],
            'users': [e.user for e in critical_found],
            'recommendation': 'Review critical operations for authorization'
        })
    
    # Failed operations
    failed_events = [e for e in events if e.error_code != '0']
    if len(failed_events) > 5:
        report.warnings.append({
            'type': 'failed_operations',
            'count': len(failed_events),
            'recommendation': 'Review failed permission attempts - potential unauthorized access'
        })
    
    # User activity anomaly
    user_activity = Counter(e.user for e in events)
    for user, count in user_activity.items():
        if count > 50:
            report.warnings.append({
                'type': 'high_user_activity',
                'user': user,
                'count': count,
                'recommendation': 'Verify user activity is legitimate'
            })
    
    # Off-hours activity (22:00 - 06:00)
    off_hours_events = [e for e in events if e.hour < 6 or e.hour > 22]
    if off_hours_events:
        report.warnings.append({
            'type': 'off_hours_activity',
            'count': len(off_hours_events),
            'recommendation': 'Review off-hours operations'
        })
    
    return report
```

---

## 2. Credential Rotation Strategy

### 2.1 Rotation Schedule

| Credential Type | Rotation Frequency | Reminder | Method |
|-----------------|-------------------|----------|--------|
| API SecretKey | 90 days | 80 days | CAM console |
| SSH Key Pair | 180 days | 170 days | CreateKeyPair |
| Database Password | 90 days | 80 days | Application config |
| Service Account | 365 days | 350 days | CAM role |

### 2.2 Credential Expiry Check

```bash
# Check API key creation time (via CAM)
tccli cam DescribeSecretKeyList \
  --TargetUin "{{user.account_id}}" \
  | jq '.Response.SecretKeyList[] | {SecretKeyId, CreateTime}'
```

### 2.3 Rotation Process

```yaml
rotation_process:
  steps:
    1_generate_new:
      action: "Generate new credential"
      verify: "New credential created"
      
    2_update_apps:
      action: "Update all applications with new credential"
      verify: "Applications tested with new credential"
      
    3_verify:
      action: "Verify new credential works"
      verify: "All services operational"
      
    4_disable_old:
      action: "Disable old credential"
      verify: "Old credential disabled"
      
    5_audit_log:
      action: "Document rotation in audit log"
      verify: "Rotation recorded"
      
  safety_rules:
    - "NEVER delete old credential before verifying new works"
    - "Keep old credential for rollback if needed"
    - "Test with new credential in staging first"
    - "Audit log every rotation action"
```

### 2.4 Rotation Notification Template

```markdown
**Credential Rotation Reminder**

Your API SecretKey will expire soon:

| Credential | Type | Expiry Date | Days Remaining |
|------------|------|-------------|----------------|
| [SecretKeyId] | API SecretKey | [expiry_date] | [days] |

**Recommended Actions**:
1. Login to CAM console → Create new SecretKey
2. Update environment variables: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
3. Verify applications still working
4. Disable old SecretKey after verification

**Safety**: Do NOT delete old key until new key is verified.
```

---

## 3. Security Group Audit

### 3.1 Security Group Query CLI

```bash
# Describe all security groups
tccli vpc DescribeSecurityGroups \
  --Region ap-guangzhou

# Describe security group rules
tccli vpc DescribeSecurityGroupPolicies \
  --Region ap-guangzhou \
  --SecurityGroupId sg-xxx
```

### 3.2 Security Group Best Practices Checklist

| Check | Rule | Severity | Fix |
|-------|------|----------|-----|
| ✓/✗ | SSH (22) NOT open to 0.0.0.0/0 | **CRITICAL** | Restrict to VPN/IPs |
| ✓/✗ | RDP (3389) NOT open to 0.0.0.0/0 | **CRITICAL** | Restrict to VPN/IPs |
| ✓/✗ | Database ports NOT exposed (3306, 5432, 6379) | **CRITICAL** | VPC-only access |
| ✓/✗ | HTTP/HTTPS (80/443) can be public | OK | Normal |
| ✓/✗ | Outbound rules not overly permissive | MEDIUM | Restrict if needed |
| ✓/✗ | Security Group attached to instances | LOW | Attach if detached |
| ✓/✗ | No unused Security Groups | LOW | Delete unused |

### 3.3 Security Group Audit Script

```python
def audit_security_group(sg: SecurityGroup) -> List[SecurityIssue]:
    # Audit security group for best practices
    
    issues = []
    
    # Database ports that should never be public
    db_ports = [3306, 5432, 6379, 27017, 11211, 9092]
    
    # Admin ports that should be restricted
    admin_ports = [22, 3389, 23]
    
    # Check inbound rules
    for rule in sg.InboundRules:
        # Public exposure check
        if rule.CidrBlock == '0.0.0.0/0':
            # SSH public - critical
            if rule.Port in admin_ports:
                issues.append(SecurityIssue(
                    sg_id=sg.SecurityGroupId,
                    sg_name=sg.SecurityGroupName,
                    severity='CRITICAL',
                    issue='public_ssh_rdp',
                    detail=f"Port {rule.Port} exposed to public internet",
                    recommendation=f"Restrict port {rule.Port} to office IPs or VPN CIDR"
                ))
            
            # Database public - critical
            if rule.Port in db_ports:
                issues.append(SecurityIssue(
                    sg_id=sg.SecurityGroupId,
                    sg_name=sg.SecurityGroupName,
                    severity='CRITICAL',
                    issue='public_database',
                    detail=f"Database port {rule.Port} exposed to public",
                    recommendation="Restrict database ports to VPC CIDR only (10.0.0.0/8)"
                ))
        
        # Wide VPC access for sensitive ports
        if rule.Port in db_ports:
            if rule.CidrBlock not in ['10.0.0.0/8', sg.VpcId]:
                issues.append(SecurityIssue(
                    sg_id=sg.SecurityGroupId,
                    sg_name=sg.SecurityGroupName,
                    severity='HIGH',
                    issue='wide_db_access',
                    detail=f"Database port {rule.Port} not restricted to VPC",
                    recommendation="Use specific subnet CIDR for database access"
                ))
    
    return issues
```

### 3.4 Security Group Audit Report

```markdown
# Security Group Audit Report

**Region**: ap-guangzhou
**Generated**: 2026-05-21

## Critical Issues (Immediate Fix Required)

| SG ID | SG Name | Issue | Port | Recommendation |
|-------|---------|-------|------|----------------|
| sg-xxx | sg-public-ssh | SSH public | 22 | Restrict to VPN IPs |
| sg-yyy | sg-db-exposed | MySQL public | 3306 | VPC-only access |

## High Issues

| SG ID | SG Name | Issue | Recommendation |
|-------|---------|-------|----------------|
| sg-aaa | sg-wide-db | Wide DB access | Restrict to app subnet |

## Passed Checks

| SG ID | SG Name | Status |
|-------|---------|--------|
| sg-prod-web | Production Web | ✅ All checks passed |
| sg-prod-app | Production App | ✅ All checks passed |

## Recommendations

1. **Immediate**: Fix SSH/RDP public exposure
2. **Immediate**: Fix database port public exposure
3. **Review**: Audit wide database access rules
```

---

## 4. Network Isolation Verification

### 4.1 VPC Isolation Check

```bash
# Verify instance is in VPC (not Basic Network)
tccli cvm DescribeInstances \
  --Region ap-guangzhou \
  --InstanceIds "[\"ins-xxx\"]" \
  | jq '.Response.InstanceSet[0].VirtualPrivateCloud'

# Expected: {"VpcId": "vpc-xxx", "SubnetId": "subnet-xxx"}
# Risk: If empty or null → Basic Network (legacy, less secure)
```

### 4.2 Network Tier Architecture

```yaml
network_tiers:
  public_tier:
    subnets:
      - cidr: 10.0.0.0/24
        type: public
        resources: [CLB, NAT Gateway]
        
  application_tier:
    subnets:
      - cidr: 10.0.1.0/24
        type: private
        resources: [CVM]
        
  database_tier:
    subnets:
      - cidr: 10.0.2.0/24
        type: private
        resources: [MySQL, Redis]
        
  isolation_rules:
    - public_tier cannot access database_tier directly
    - application_tier accesses database_tier only
    - database_tier has no outbound to public
```

### 4.3 Network Isolation Checklist

| Check | Requirement | Status |
|-------|-------------|--------|
| ✓/✗ | VPC used (not Basic Network) | Required |
| ✓/✗ | Public subnet for web tier | Recommended |
| ✓/✗ | Private subnet for app tier | Recommended |
| ✓/✗ | Private subnet for DB tier | Required |
| ✓/✗ | Security Group per tier | Recommended |
| ✓/✗ | No public IP for DB instances | Required |
| ✓/✗ | NAT Gateway for private egress | Recommended |

---

## 5. Compliance Checklist

### 5.1 CVM Security Compliance Checklist

```markdown
## CVM Security Compliance Checklist

### 1. Authentication & Access Control

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1.1 | CAM policies use least privilege | [✓/✗] | |
| 1.2 | No shared credentials between users | [✓/✗] | |
| 1.3 | API SecretKey rotated < 90 days | [✓/✗] | |
| 1.4 | SSH Key Pair rotated < 180 days | [✓/✗] | |
| 1.5 | Root account not used for daily ops | [✓/✗] | |
| 1.6 | MFA enabled for root account | [✓/✗] | |

### 2. Network Security

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 2.1 | VPC isolation implemented | [✓/✗] | |
| 2.2 | Security Groups reviewed quarterly | [✓/✗] | |
| 2.3 | SSH (22) restricted to VPN/IPs | [✓/✗] | |
| 2.4 | Database ports NOT public | [✓/✗] | |
| 2.5 | Network ACLs configured | [✓/✗] | |
| 2.6 | No unused Security Groups | [✓/✗] | |

### 3. Instance Security

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 3.1 | SSH password login disabled | [✓/✗] | |
| 3.2 | SSH key pair attached | [✓/✗] | |
| 3.3 | Security Group attached | [✓/✗] | |
| 3.4 | No public IP for DB servers | [✓/✗] | |
| 3.5 | System disk encryption enabled | [✓/✗] | |
| 3.6 | Data disk encryption for sensitive data | [✓/✗] | |

### 4. Monitoring & Audit

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 4.1 | CloudAudit enabled | [✓/✗] | |
| 4.2 | Security alerts configured | [✓/✗] | |
| 4.3 | Regular audit log review | [✓/✗] | |
| 4.4 | Failed login attempts monitored | [✓/✗] | |
| 4.5 | Critical operation alerts | [✓/✗] | |

### 5. Data Protection

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 5.1 | Regular snapshot backups | [✓/✗] | |
| 5.2 | Snapshot retention policy | [✓/✗] | |
| 5.3 | Cross-region image backup (DR) | [✓/✗] | |
| 5.4 | No sensitive data on public instances | [✓/✗] | |

## Compliance Score

**Passed**: [N]/[Total]
**Score**: [%]
**Status**: [Excellent/Good/Moderate/Poor]
```

### 5.2 Compliance Score Calculation

```python
def calculate_compliance_score(checklist: Dict) -> ComplianceResult:
    # Calculate compliance score from checklist
    
    total_checks = sum(len(category) for category in checklist.values())
    passed_checks = sum(
        1 for category in checklist.values() 
        for check in category if check['status'] == '✓'
    )
    
    score = (passed_checks / total_checks) * 100
    
    result = ComplianceResult()
    result.total_checks = total_checks
    result.passed_checks = passed_checks
    result.score = score
    
    if score >= 90:
        result.status = 'Excellent'
        result.message = "High compliance - maintain best practices"
    elif score >= 70:
        result.status = 'Good'
        result.message = "Good compliance - address specific gaps"
    elif score >= 50:
        result.status = 'Moderate'
        result.message = "Moderate compliance - prioritize security"
    else:
        result.status = 'Poor'
        result.message = "Poor compliance - immediate improvement required"
    
    return result
```

---

## 6. High-Risk Operation Alerts

### 6.1 High-Risk Operations

| Operation | Risk Level | Requires Confirmation | Audit |
|-----------|------------|----------------------|-------|
| TerminateInstances | **Critical** | YES + snapshot check | Mandatory |
| DeleteSecurityGroup | **High** | YES | Mandatory |
| ModifySecurityGroupPolicies | **High** | YES (for open rules) | Mandatory |
| DeleteKeyPair | **High** | YES | Mandatory |
| Open SSH to 0.0.0.0/0 | **Critical** | YES | Mandatory |

### 6.2 Pre-Operation Security Gate

```yaml
security_gate:
  terminate_instances:
    checks:
      - name: snapshot_backup
        condition: "Snapshot exists for all attached disks"
        action: "Remind: Create snapshot before termination"
        
      - name: dependency_check
        condition: "No active CLB attachments"
        action: "Check CLB backend registration"
        
      - name: explicit_confirmation
        condition: "User confirms with resource ID"
        action: "Require: 'CONFIRM ins-xxx termination'"
        
  modify_sg_open_ssh:
    checks:
      - name: ip_restriction
        condition: "NOT 0.0.0.0/0"
        action: "Block: SSH must be restricted to specific IPs"
        
      - name: explicit_confirmation
        condition: "User confirms risk"
        action: "Require: 'CONFIRM SSH open to [CIDR]'"
```

## 7. CVM Audit Rules Integration

This section cross-references SecOps checklist items with the centralized audit rules in [audit-rules.md](audit-rules.md).

### Rule Mapping

| SecOps Section | Audit Rules | Severity |
|----------------|-------------|----------|
| Security Group Audit (Section 3) | `SEC-001` SSH, `SEC-002` RDP, `SEC-003` DB | CRITICAL |
| Credential Rotation (Section 4) | `AUTH-001` SSH Key, `AUTH-002` Rotation | HIGH |
| Network Isolation (Section 5) | `CFG-002` Zone, `SEC-001/2/3` | HIGH |
| Compliance Audit (Section 6) | `TAG-001/2`, `COST-001/2` | MEDIUM |

### Audit Coverage Matrix

| Check | SecOps Checklist | Audit Rule ID | Automated? |
|-------|-----------------|---------------|------------|
| VPC isolation | ✅ Section 5 | `CFG-001` | Yes (CLI) |
| SSH restricted to VPN | ✅ Section 3 | `SEC-001` | Yes (CLI) |
| Database ports not public | ✅ Section 3 | `SEC-003` | Yes (CLI) |
| CAM least-privilege | ✅ Section 4 | `AUTH-003` | Semi (manual) |
| Credential rotation | ✅ Section 4 | `AUTH-002` | Yes (CLI) |
| Backup snapshot | — | `BKUP-001` | Yes (CLI) |
| Cost tags | — | `TAG-001/2` | Yes (CLI) |
| CPU/Mem alarm | — | `MON-001/2` | Yes (CLI) |

### Quick Audit Integration

Add the audit script path to the CVM skill's **Execution Flows** section:

```bash
# One-shot comprehensive audit
bash /data/scripts/cvm_audit.sh
```

---

## References

- [Audit Rules](audit-rules.md) — Complete CVM audit rules checklist
- [Tencent Cloud CAM Documentation](https://cloud.tencent.com/document/product/598)
- [CloudAudit API](https://cloud.tencent.com/document/product/xxx)
- [Security Group Best Practices](https://cloud.tencent.com/document/product/xxx)
- [SecOps Security Operations Module](../qcloud-skill-generator/references/secops-security-operations.md)