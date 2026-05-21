# CVM Well-Architected Assessment

Four-pillar assessment based on Tencent Cloud Well-Architected Framework: Reliability, Security, Cost, Efficiency.

---

## 1. Framework Overview

Tencent Cloud Well-Architected Framework defines four pillars for cloud resource design:

| Pillar | Focus | CVM Assessment Scope |
|--------|-------|---------------------|
| **可靠性 (Reliability)** | Availability, DR, recovery | Multi-AZ, backup, auto-recovery |
| **安全性 (Security)** | Access control, encryption, network isolation | CAM, SSH keys, VPC, encryption |
| **成本 (Cost)** | Resource optimization, waste reduction | Right-sizing, prepaid, idle detection |
| **效率 (Efficiency)** | Automation, batch operations, CI/CD | Auto-scaling, scheduling, IaC |

---

## 2. Reliability Pillar (可靠性)

### Multi-AZ Deployment

| Pattern | Description | Risk Level |
|---------|-------------|------------|
| Single Zone | All instances in one zone | High (zone outage = total failure) |
| Multi-AZ with CLB | Instances across zones + load balancer | Low (zone outage = partial degradation) |
| Cross-Region | Instances in multiple regions + global DNS | Very Low (region outage = fallback) |

**Assessment Checklist**:

```bash
# Check instance zone distribution
tccli cvm DescribeInstances --Region ap-guangzhou | jq '.Response.InstanceSet[].Zone' | sort | uniq -c

# Expected: ≥ 2 zones for production
```

### Backup and Recovery

| Metric | Requirement | Assessment |
|--------|-------------|------------|
| RPO (Recovery Point Objective) | Max data loss window | Snapshot frequency |
| RTO (Recovery Time Objective) | Max recovery time | Image creation + restore time |

**Snapshot Policy**:

```bash
# Check existing snapshots
tccli cbs DescribeSnapshots --Region ap-guangzhou | jq '.Response.SnapshotSet[].CreatedTime'

# Recommended: Daily snapshots for production instances
# Retention: 7-30 days based on RPO requirement
```

### DR Runbook (Phase 1 → 2 → 3)

**Phase 1: Immediate Recovery (0-15 min)**

```bash
# 1. Identify failed instance
tccli cvm DescribeInstances --Region ap-guangzhou --Filters '[{"Name":"instance-status","Values":["SHUTDOWN","TERMINATED"]}]'

# 2. Launch replacement from image
tccli cvm RunInstances \
  --Region ap-guangzhou \
  --Placement '{"Zone":"ap-guangzhou-3"}' \
  --InstanceType S5.LARGE4 \
  --ImageId "{{user.backup_image_id}}" \
  --VpcId "{{user.vpc_id}}" \
  --SubnetId "{{user.subnet_id}}"
```

**Phase 2: Data Recovery (15-60 min)**

```bash
# 1. Create disk from snapshot
tccli cbs CreateDisks \
  --Region ap-guangzhou \
  --SnapshotId "{{user.snapshot_id}}" \
  --DiskType CLOUD_PREMIUM \
  --DiskSize 100

# 2. Attach disk to new instance
tccli cbs AttachDisk \
  --Region ap-guangzhou \
  --DiskId "{{output.disk_id}}" \
  --InstanceId "{{output.instance_id}}"
```

**Phase 3: Service Restoration (60+ min)**

- Update DNS/CLB to point to new instance
- Verify application health
- Document recovery time vs RTO target

### Auto-Recovery Configuration

```bash
# Enable auto-recovery on instance creation
tccli cvm RunInstances \
  --Region ap-guangzhou \
  --DisableMonitorService false \
  --DisableSecurityService false
```

---

## 3. Security Pillar (安全性)

### CAM Permissions

**Minimum Required Permissions for CVM Operations**:

```json
{
  "version": "2.0",
  "statement": [
    {
      "effect": "allow",
      "action": [
        "cvm:DescribeInstances",
        "cvm:RunInstances",
        "cvm:StartInstances",
        "cvm:StopInstances",
        "cvm:RebootInstances",
        "cvm:TerminateInstances",
        "cvm:ModifyInstanceAttribute",
        "cvm:CreateImage",
        "cvm:DescribeImages"
      ],
      "resource": "*"
    }
  ]
}
```

**Assessment Checklist**:

```bash
# Check user CAM permissions
tccli cam DescribePolicyList --TargetUin "{{user.account_id}}" | jq '.Response.Policies[] | select(.PolicyName | contains("CVM"))'
```

### SSH Key Management

| Method | Security Level | Recommendation |
|--------|---------------|----------------|
| Password | Low | Disable for production |
| SSH Key Pair | High | Required for all instances |
| CAM Role | Highest | For instance-to-instance access |

```bash
# Create and attach SSH key pair
tccli cvm CreateKeyPair --Region ap-guangzhou --KeyName "prod-key"

# Disable password login (via image config or UserData)
# UserData script:
# #!/bin/bash
# sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
# systemctl restart sshd
```

### Network Isolation

| Layer | Configuration | Assessment |
|-------|---------------|------------|
| VPC | Private network isolation | Required for all production |
| Security Group | Firewall rules | Whitelist-only, no 0.0.0.0/0 for SSH |
| Subnet | Network segmentation | Separate subnets for web/db |

```bash
# Check security group rules
tccli vpc DescribeSecurityGroupPolicies --Region ap-guangzhou --SecurityGroupId sg-xxx

# Risk: SSH (22) open to 0.0.0.0/0
# Fix: Restrict to known IP ranges or VPN
```

### Encryption

| Data Type | Encryption Option | Status |
|-----------|------------------|--------|
| System Disk | CBS encryption | Optional (key management required) |
| Data Disk | CBS encryption | Recommended for sensitive data |
| Network | VPC encryption | Via VPN or Direct Connect |

---

## 4. Cost Pillar (成本)

### Billing Model Comparison

| Model | Billing Cycle | Cost | Use Case |
|-------|---------------|------|----------|
| Pay-by-hour (Postpaid) | Hourly | Variable | Dev/test, variable workloads |
| Monthly (Prepaid) | Monthly | Fixed | Stable production workloads |
| Annual (Prepaid) | Yearly | Discount | Long-term production |
| 3-Year (Prepaid) | 3 years | 50% discount | Core infrastructure |

```bash
# Price inquiry
tccli cvm InquiryPriceRunInstances \
  --Region ap-guangzhou \
  --InstanceType S5.LARGE4 \
  --InstanceChargeType POSTPAID_BY_HOUR

tccli cvm InquiryPriceRunInstances \
  --Region ap-guangzhou \
  --InstanceType S5.LARGE4 \
  --InstanceChargeType PREPAID \
  --InstanceChargePrepaid '{"Period":12}'
```

### Right-Sizing Assessment

| Metric | Threshold | Recommendation |
|--------|-----------|----------------|
| Avg CPU < 20% (7 days) | Downsize candidate | Reduce instance type |
| Avg CPU 20-60% | Optimal | Maintain current |
| Avg CPU > 70% | Upsize candidate | Increase instance type or scale out |
| Avg Memory < 30% | Memory waste | Reduce memory config |

```python
# Right-sizing analysis
def assess_right_sizing(client, instance_id):
    cpu_data = get_cpu_usage(client, instance_id, hours=168)
    mem_data = get_memory_usage(client, instance_id, hours=168)
    
    if cpu_data["avg"] < 20 and mem_data["avg"] < 30:
        return "Downsize: Instance underutilized"
    elif cpu_data["avg"] > 70 or cpu_data["max"] > 90:
        return "Upsize: Instance overloaded"
    else:
        return "Normal: Instance well-sized"
```

### Idle Resource Detection

```bash
# Find stopped instances (idle > 24h)
tccli cvm DescribeInstances --Region ap-guangzhou --Filters '[{"Name":"instance-status","Values":["STOPPED"]}]'

# Check CreatedTime for duration
# Recommendation: Delete instances stopped > 7 days
```

### Reserved Instances

| Duration | Discount | Commitment |
|----------|----------|------------|
| Monthly | 0% | 1 month |
| 1 year | 30-40% | 12 months |
| 3 years | 50% | 36 months |

---

## 5. Efficiency Pillar (效率)

### Batch Operations

| Operation | Batch Size Limit | Automation |
|-----------|-----------------|------------|
| DescribeInstances | 100 | Pagination loop |
| StartInstances | 20 | Batch with chunking |
| StopInstances | 20 | Batch with chunking |
| TerminateInstances | 20 | Batch with chunking |

```python
# Batch stop pattern
def batch_stop(client, instance_ids):
    batch_size = 20
    for i in range(0, len(instance_ids), batch_size):
        chunk = instance_ids[i:i+batch_size]
        req = models.StopInstancesRequest()
        req.InstanceIds = chunk
        resp = client.StopInstances(req)
        print(f"Stopped batch: {chunk}")
```

### Auto-Scaling Integration

```bash
# Create auto-scaling group (requires AS skill)
# Delegate to qcloud-as-ops for scaling policy
```

### Scheduled Operations

| Schedule | Operation | Benefit |
|----------|-----------|---------|
| Night shutdown | Stop dev/test instances | Cost savings |
| Morning startup | Start dev/test instances | Ready for work |
| Weekly backup | Create snapshots | Data protection |

```bash
# Scheduled stop (via timer or Lambda)
# Stop all instances with tag Environment=Dev at 22:00

tccli cvm DescribeInstances \
  --Region ap-guangzhou \
  --Filters '[{"Name":"tag-value","Values":["Dev"]}]' \
  | jq '.Response.InstanceSet[].InstanceId' \
  | while read id; do
      tccli cvm StopInstances --Region ap-guangzhou --InstanceIds "[\"$id\"]"
    done
```

### CI/CD Integration

| Tool | CVM Integration | Use Case |
|------|----------------|----------|
| Terraform | Infrastructure as Code | Provisioning automation |
| Ansible | Configuration management | Post-provision config |
| Jenkins | Pipeline integration | Deploy from CI |
| GitLab CI | Runner on CVM | CI execution |

---

## 6. Assessment Checklist (Four Pillars)

### Reliability Checklist

- [ ] Multi-AZ deployment (≥ 2 zones)
- [ ] Daily snapshots with retention policy
- [ ] Custom image for DR recovery
- [ ] RTO documented (< target time)
- [ ] Auto-recovery enabled
- [ ] Health monitoring configured

### Security Checklist

- [ ] VPC isolation (not Basic Network)
- [ ] Security Group whitelist-only
- [ ] SSH key pair (no password login)
- [ ] CAM least-privilege permissions
- [ ] Disk encryption for sensitive data
- [ ] Regular security audit

### Cost Checklist

- [ ] Right-sizing analysis (CPU/Memory utilization)
- [ ] Prepaid for stable workloads
- [ ] Reserved instances for core infrastructure
- [ ] Idle resource cleanup (stopped instances)
- [ ] Bandwidth optimization (pay-by-traffic for variable)
- [ ] Monthly cost review

### Efficiency Checklist

- [ ] Batch operations documented
- [ ] Auto-scaling enabled (variable workloads)
- [ ] Scheduled shutdown/startup (dev/test)
- [ ] Infrastructure as Code (Terraform/Ansible)
- [ ] CI/CD pipeline integration
- [ ] Tag-based resource management

---

## 7. Well-Architected Score Calculation

| Pillar | Weight | Score Criteria |
|--------|--------|---------------|
| Reliability | 30% | Checklist items passed / total |
| Security | 30% | Checklist items passed / total |
| Cost | 20% | Checklist items passed / total |
| Efficiency | 20% | Checklist items passed / total |

**Example Score Calculation**:

```
Reliability: 5/6 items passed = 83% → 83 * 0.30 = 24.9
Security: 6/6 items passed = 100% → 100 * 0.30 = 30.0
Cost: 4/6 items passed = 67% → 67 * 0.20 = 13.4
Efficiency: 3/6 items passed = 50% → 50 * 0.20 = 10.0

Total: 24.9 + 30.0 + 13.4 + 10.0 = 78.3 / 100
```

**Score Interpretation**:

| Score | Status | Action |
|-------|--------|--------|
| 90-100 | Excellent | Maintain best practices |
| 70-89 | Good | Address specific gaps |
| 50-69 | Moderate | Prioritize reliability/security |
| < 50 | Poor | Immediate improvement required |

---

## References

- [Tencent Cloud Well-Architected Framework](https://cloud.tencent.com/document/product/xxx)
- [CVM Best Practices](https://cloud.tencent.com/document/product/213)
- [CAM Policy Examples](https://cloud.tencent.com/document/product/598)