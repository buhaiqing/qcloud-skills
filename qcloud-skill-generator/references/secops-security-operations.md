# SecOps Security Operations Module

Security operations patterns for Tencent Cloud skills.

---

## Overview

Every generated skill MUST implement SecOps patterns:
- Security audit log analysis
- Credential rotation strategy
- Security Group best practices
- Network isolation patterns
- Compliance checklist

---

## 1. Security Audit Logs

### 1.1 CAM Audit Log Query

```python
def query_cam_audit_logs(start_time: str, end_time: str) -> List[AuditEvent]:
    # Query CAM (Cloud Access Management) audit logs
    # Use CloudAudit API
    request = models.LookUpEventsRequest()
    request.StartTime = start_time
    request.EndTime = end_time
    request.MaxResults = 100
    
    response = cloudaudit_client.LookUpEvents(request)
    
    # Filter for security-relevant events
    security_events = [
        AuditEvent(
            event_id=e.EventId,
            event_type=e.EventName,
            user=e.Username,
            resource=e.Resources[0].ResourceName,
            action=e.EventName,
            time=e.EventTime,
            result=e.ErrorCode
        )
        for e in response.Events
        if is_security_event(e.EventName)
    ]
    
    return security_events

def is_security_event(event_name: str) -> bool:
    # Filter security-relevant events
    security_actions = [
        'CreateUser',
        'DeleteUser',
        'CreateRole',
        'DeleteRole',
        'AttachUserPolicy',
        'DetachUserPolicy',
        'CreatePolicy',
        'DeletePolicy',
        'CreateSecretKey',
        'DeleteSecretKey',
        'ModifySecurityGroup',
        'CreateSecurityGroup',
        'DeleteSecurityGroup',
    ]
    return event_name in security_actions
```

### 1.2 Audit Log Analysis

```python
def analyze_audit_logs(events: List[AuditEvent]) -> SecurityReport:
    # Analyze audit logs for security insights
    report = SecurityReport()
    
    # Count by action type
    action_counts = Counter(e.action for e in events)
    report.action_breakdown = action_counts
    
    # High-risk actions
    high_risk_actions = ['DeleteUser', 'DeleteRole', 'DeletePolicy', 'DeleteSecretKey']
    high_risk_events = [e for e in events if e.action in high_risk_actions]
    
    if len(high_risk_events) > 0:
        report.warnings.append(
            f"⚠️ {len(high_risk_events)} high-risk actions detected: "
            f"{[e.action for e in high_risk_events]}"
        )
    
    # Failed actions
    failed_events = [e for e in events if e.result != '0']
    if len(failed_events) > 0:
        report.warnings.append(
            f"⚠️ {len(failed_events)} failed permission attempts detected"
        )
    
    # User activity anomaly
    user_counts = Counter(e.user for e in events)
    for user, count in user_counts.items():
        if count > 100:  # > 100 actions in period
            report.warnings.append(
                f"⚠️ User {user} has high activity: {count} actions"
            )
    
    return report
```

---

## 2. Credential Rotation Strategy

### 2.1 Rotation Schedule

| Credential Type | Rotation Frequency | Method |
|-----------------|-------------------|--------|
| API SecretKey | Every 90 days | Generate new, disable old |
| SSH Key | Every 180 days | Generate new, remove old |
| Database Password | Every 90 days | Update via ModifyInstance |
| Service Account Key | Every 365 days | Renew via CAM |

### 2.2 Rotation Implementation

```yaml
credential_rotation:
  schedule:
    api_key:
      interval: 90d
      reminder: 80d  # Alert 10 days before expiry
      
    ssh_key:
      interval: 180d
      reminder: 170d
      
  process:
    step_1: "Generate new credential"
    step_2: "Update applications with new credential"
    step_3: "Verify new credential works"
    step_4: "Disable/delete old credential"
    step_5: "Document rotation in audit log"
    
  safety:
    - Never delete before verifying new works
    - Keep old credential temporarily for rollback
    - Audit log every rotation action
```

### 2.3 Rotation Notification

```markdown
**Credential Rotation Reminder**

Your credentials will expire soon:

| Credential | Type | Expiry Date | Days Remaining |
|------------|------|-------------|----------------|
| [ID] | API SecretKey | [date] | [days] |

**Recommended Actions**:
1. Generate new SecretKey in CAM console
2. Update environment variables in applications
3. Verify applications still working
4. Disable old SecretKey

**Safety**: Do NOT delete old key until new key verified.
```

---

## 3. Security Group Best Practices

### 3.1 Security Group Checklist

| Check | Rule | Status |
|-------|------|--------|
| ✓/✗ | No 0.0.0.0/0 inbound (except HTTP/HTTPS) | Review |
| ✓/✗ | SSH (22) restricted to specific IPs | Review |
| ✓/✗ | Database ports not exposed to public | Review |
| ✓/✗ | Outbound rules not overly permissive | Review |
| ✓/✗ | Security Group attached to all instances | Review |
| ✓/✗ | No unused Security Groups | Review |

### 3.2 Security Group Audit

```python
def audit_security_groups(sgs: List[SecurityGroup]) -> List[SecurityIssue]:
    # Audit security groups for best practices
    issues = []
    
    for sg in sgs:
        # Check inbound rules
        for rule in sg.InboundRules:
            # Public exposure check
            if rule.CidrBlock == '0.0.0.0/0':
                if rule.Port not in [80, 443]:  # HTTP/HTTPS OK
                    issues.append(SecurityIssue(
                        sg_id=sg.SecurityGroupId,
                        issue='public_exposure',
                        detail=f"Port {rule.Port} exposed to public",
                        severity='HIGH',
                        recommendation=f"Restrict port {rule.Port} to specific IPs"
                    ))
            
            # SSH check
            if rule.Port == 22 and rule.CidrBlock == '0.0.0.0/0':
                issues.append(SecurityIssue(
                    sg_id=sg.SecurityGroupId,
                    issue='ssh_public',
                    detail="SSH exposed to public",
                    severity='CRITICAL',
                    recommendation="Restrict SSH to office IPs or VPN"
                ))
            
            # Database port check
            db_ports = [3306, 5432, 6379, 27017, 11211]
            if rule.Port in db_ports and rule.CidrBlock != '10.0.0.0/8':
                issues.append(SecurityIssue(
                    sg_id=sg.SecurityGroupId,
                    issue='database_exposed',
                    detail=f"Database port {rule.Port} not restricted to VPC",
                    severity='HIGH',
                    recommendation="Restrict database ports to VPC CIDR"
                ))
    
    return issues
```

### 3.3 Recommended Security Group Configuration

```yaml
security_group_template:
  # Web tier - public facing
  web_sg:
    inbound:
      - port: 80
        cidr: 0.0.0.0/0
        protocol: tcp
      - port: 443
        cidr: 0.0.0.0/0
        protocol: tcp
    outbound:
      - port: all
        cidr: 10.0.0.0/8  # Internal only
        protocol: all
        
  # App tier - internal
  app_sg:
    inbound:
      - port: 8080
        cidr: 10.0.0.0/8  # From web tier
        protocol: tcp
    outbound:
      - port: all
        cidr: 10.0.0.0/8
        
  # Database tier - most restricted
  db_sg:
    inbound:
      - port: 3306
        cidr: sg-app-id  # Reference app SG
        protocol: tcp
    outbound: []  # No outbound needed
```

---

## 4. Network Isolation Patterns

### 4.1 VPC Architecture

```yaml
vpc_isolation:
  production:
    cidr: 10.0.0.0/16
    
    subnets:
      public:
        cidr: 10.0.0.0/24
        type: public
        resources: [CLB, NAT Gateway]
        
      app_private:
        cidr: 10.0.1.0/24
        type: private
        resources: [CVM]
        
      db_private:
        cidr: 10.0.2.0/24
        type: private
        resources: [MySQL, Redis]
        
  # No direct public access to private subnets
  # Use CLB for ingress, NAT for egress
```

### 4.2 Network ACL Rules

```yaml
network_acl:
  # Public subnet ACL
  public_acl:
    inbound:
      - rule: allow
        port: 80
        cidr: 0.0.0.0/0
      - rule: allow
        port: 443
        cidr: 0.0.0.0/0
        
    outbound:
      - rule: allow
        port: all
        cidr: 10.0.0.0/8  # Only to private
        
  # Private subnet ACL
  private_acl:
    inbound:
      - rule: allow
        port: all
        cidr: 10.0.0.0/16  # Only from VPC
        
    outbound:
      - rule: allow
        port: all
        cidr: 10.0.0.0/16
```

---

## 5. Compliance Checklist

### 5.1 Security Compliance Checklist

```markdown
## Security Compliance Checklist

### Authentication & Access

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | CAM policies use least privilege | ✓/✗ | |
| 2 | No shared credentials | ✓/✗ | |
| 3 | API keys rotated < 90 days | ✓/✗ | |
| 4 | SSH keys rotated < 180 days | ✓/✗ | |
| 5 | Root account not used daily | ✓/✗ | |

### Network Security

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 6 | VPC isolation implemented | ✓/✗ | |
| 7 | Security Groups reviewed | ✓/✗ | |
| 8 | No public database exposure | ✓/✗ | |
| 9 | SSH restricted to VPN/IPs | ✓/✗ | |
| 10 | Network ACLs configured | ✓/✗ | |

### Encryption

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 11 | Storage encryption enabled | ✓/✗ | |
| 12 | Transmission encryption (TLS) | ✓/✗ | |
| 13 | KMS keys managed | ✓/✗ | |

### Monitoring & Audit

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 14 | CloudAudit enabled | ✓/✗ | |
| 15 | Security alerts configured | ✓/✗ | |
| 16 | Regular audit reviews | ✓/✗ | |
```

---

## Integration in Generated Skills

```markdown
## SecOps Security Operations

### Security Audit

Query security events with CloudAudit:
```bash
tccli cloudaudit LookUpEvents --StartTime [start] --EndTime [end]
```

### Credential Rotation

Remind user to rotate credentials every:
- API SecretKey: 90 days
- SSH Key: 180 days

### Security Group Checklist

Before deployment, verify:
- [ ] No 0.0.0.0/0 on non-web ports
- [ ] SSH restricted to office IPs
- [ ] Database ports in private subnet
```

---

## References

- [Tencent Cloud CAM Documentation](https://cloud.tencent.com/document/product/598)
- [CloudAudit API](https://cloud.tencent.com/document/product/xxx)
- [Security Group Best Practices](https://cloud.tencent.com/document/product/xxx)