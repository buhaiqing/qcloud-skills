# CVM Audit Rules

Comprehensive audit rules for CVM instances — lifecycle, security, network, credentials, backup, cost, monitoring, and tagging. Every rule includes a CLI check command, pass criteria, severity, and remediation guidance.

---

## Overview

This document covers **54 audit rules** across 8 categories, plus automated audit scripts and scoring. Use these rules for:

- **Scheduled compliance audits** (daily/weekly/monthly checklists in Section 9)
- **Pre-deployment safety checks** (Section 10)
- **Post-incident forensics** (Section 11)
- **Automated audit pipelines** (Section 12)

Each rule is identified by a unique ID (e.g., `SEC-001`) for cross-referencing with SKILL.md execution flows, secops-checklist.md, and finops-analysis.md.

---

## 1. Instance Lifecycle Audit

| Rule ID | Category | Severity | CLI Check | Pass Criteria | Remediation |
|---------|----------|----------|-----------|---------------|-------------|
| `LIFE-001` | Pending | **CRITICAL** | `DescribeInstances --Filters '[{"Name":"instance-status","Values":["PENDING"]}]'` | No instances in PENDING > 5 min | Investigate stuck create/start; check CloudAudit for errors |
| `LIFE-002` | Running | HIGH | `DescribeInstances --Filters '[{"Name":"instance-status","Values":["STOPPED"]}]'` — then check CreatedTime | No production STOPPED > 24h | Restart, release, or confirm decommission |
| `LIFE-003` | Orphaned | MEDIUM | `DescribeInstances --Filters '[{"Name":"instance-status","Values":["TERMINATED"]}]'` | No zombie terminated records | Open support ticket to purge |
| `LIFE-004` | Age | MEDIUM | `DescribeInstances | jq '.InstanceSet[] | select(.CreatedTime < "2025-05-21T00:00:00+08:00") | .InstanceId'` | No running instance > 1 year without review | Schedule modernization assessment |
| `LIFE-005` | Operation | HIGH | `cloudaudit LookUpEvents --ActionNames "[\"TerminateInstances\"]" --StartTime "..." --EndTime "..."` | No unauthorized terminations | Review CAM permissions; add MFA protection |
| `LIFE-006` | Quota | LOW | `DescribeInstances --Limit 0 | jq '.Response.TotalCount'` (then check quota at DescribeCvmQuota) | Usage < 80% of quota | Request quota increase before hitting limit |
| `LIFE-007` | Reboot | MEDIUM | `cloudaudit LookUpEvents --ActionNames "[\"RebootInstances\"]" --MaxResults 100` | No >3 reboots per instance/month | Investigate instability; check OS logs |

**CLI execution**:
```bash
# Stuck pending instances
tccli cvm DescribeInstances --Region ap-guangzhou \
  --Filters '[{"Name":"instance-status","Values":["PENDING"]}]' \
  | jq '.Response.InstanceSet[] | {InstanceId, InstanceName, CreatedTime}'

# Stopped production instances (older than 24h)
tccli cvm DescribeInstances --Region ap-guangzhou \
  --Filters '[{"Name":"instance-status","Values":["STOPPED"]}]' \
  | jq '.Response.InstanceSet[] | select(.CreatedTime < "'$(date -d '-1 day' +'%Y-%m-%dT%H:%M:%S+08:00')'") | {InstanceId, InstanceName, CreatedTime}'
```

---

## 2. Security Group Audit

| Rule ID | Category | Severity | CLI Check | Pass Criteria | Remediation |
|---------|----------|----------|-----------|---------------|-------------|
| `SEC-001` | SSH | **CRITICAL** | `DescribeSecurityGroupPolicies --SecurityGroupId $SG \| jq '.Response.Inbound[] \| select(.CidrBlock=="0.0.0.0/0" and (.PortRange\|test("22")))'` | SSH NOT open to 0.0.0.0/0 | Restrict to `<your-vpn-cidr>`; add WAF if public SSH needed |
| `SEC-002` | RDP | **CRITICAL** | `DescribeSecurityGroupPolicies --SecurityGroupId $SG \| jq '.Response.Inbound[] \| select(.CidrBlock=="0.0.0.0/0" and (.PortRange\|test("3389")))'` | RDP NOT open to 0.0.0.0/0 | Restrict to VPN IPs; use SSM Session Manager instead |
| `SEC-003` | DB | **CRITICAL** | `DescribeSecurityGroupPolicies --SecurityGroupId $SG \| jq '.Response.Inbound[] \| select(.CidrBlock=="0.0.0.0/0" and (.PortRange\|test("3306|5432|6379|27017|11211")))'` | Database ports NOT public | Move DB to VPC-only; use security group references instead of CIDR |
| `SEC-004` | Elasticsearch | **CRITICAL** | `DescribeSecurityGroupPolicies --SecurityGroupId $SG \| jq '.Response.Inbound[] \| select(.CidrBlock=="0.0.0.0/0" and (.PortRange\|test("9200|5601")))'` | ES/Kibana NOT public | Internal-only access; enable ES authentication |
| `SEC-005` | Wide CIDR | HIGH | `DescribeSecurityGroupPolicies --SecurityGroupId $SG \| jq '.Response.Inbound[] \| select(.CidrBlock=="0.0.0.0/0") \| .PortRange'` | Minimize 0.0.0.0/0 rules | Replace with specific CIDR; document each exception |
| `SEC-006` | Unused SG | LOW | `DescribeSecurityGroups \| jq '.Response.SecurityGroupSet[] \| select(.SecurityGroupName\|test("default") and .Inbound\|length==0)'` | No empty/unused SGs | Delete unused security groups |
| `SEC-007` | SG-less instances | HIGH | `DescribeInstances \| jq '.Response.InstanceSet[] \| select(.SecurityGroupIds==[] or .SecurityGroupIds==null)'` | All instances have ≥1 SG | Associate default security group |
| `SEC-008` | Egress rules | MEDIUM | `DescribeSecurityGroupPolicies --SecurityGroupId $SG \| jq '.Response.Outbound[] \| select(.CidrBlock=="0.0.0.0/0" and .PolicyIndex=="0")'` | Document open egress | Restrict egress to specific CIDR + ports |
| `SEC-009` | Overly permissive | HIGH | `DescribeSecurityGroupPolicies --SecurityGroupId $SG \| jq '.Response.Inbound[] \| select(.CidrBlock=="0.0.0.0/0" and (.PortRange\|test("1-65535")))'` | No full port range open to public | Restrict to needed ports only |

**Iterate all security groups**:
```bash
#!/bin/bash
for SG in $(tccli vpc DescribeSecurityGroups --Region ap-guangzhou | jq -r '.Response.SecurityGroupSet[].SecurityGroupId'); do
  echo "=== $SG ==="
  tccli vpc DescribeSecurityGroupPolicies --Region ap-guangzhou --SecurityGroupId $SG \
    | jq '.Response.Inbound[] | select(.CidrBlock=="0.0.0.0/0") | {PortRange, CidrBlock}'
done
```

---

## 3. Network Isolation Audit

| Rule ID | Category | Severity | CLI Check | Pass Criteria | Remediation |
|---------|----------|----------|-----------|---------------|-------------|
| `NET-001` | VPC | **CRITICAL** | `DescribeInstances \| jq '.Response.InstanceSet[] \| select(.VirtualPrivateCloud==null) \| .InstanceId'` | All instances in VPC (NOT Basic Network) | Migrate to VPC; no Basic Network allowed for production |
| `NET-002` | Public IP | HIGH | `DescribeInstances \| jq '.Response.InstanceSet[] \| select(.PublicIpAddresses!=null and (.InstanceType\|test("mysql|redis|mongo|postgres\|test"))) \| {InstanceId, PublicIpAddresses}'` | No public IP on DB instances | Remove public IP; use SSH tunnel or bastion |
| `NET-003` | Elastic IP | MEDIUM | `DescribeAddresses \| jq '.Response.AddressSet[] \| select(.InstanceId==null) \| {AddressId, AddressIp}'` | No unassociated EIPs | Release unassigned EIPs (cost saving) |
| `NET-004` | Subnet tier | MEDIUM | `DescribeInstances \| jq '.Response.InstanceSet[].VirtualPrivateCloud.SubnetId' \| sort \| uniq -c` | Subnet per tier (web/app/db) | Reorganize subnet architecture |
| `NET-005` | NAT | HIGH | Check VPC route table for NAT Gateway | Private subnets have NAT egress | Configure NAT Gateway for private subnets |
| `NET-006` | ACL | LOW | `DescribeNetworkAcls --Region ap-guangzhou` | Network ACLs configured per subnet | Add ACLs as defense-in-depth layer |
| `NET-007` | Peering | MEDIUM | `DescribeVpcPeeringConnections \| jq '.PeeringConnectionSet[]'` | Peering connections documented | Audit cross-VPC traffic |

**CLI execution**:
```bash
# Basic Network instances (CRITICAL)
tccli cvm DescribeInstances --Region ap-guangzhou \
  | jq '.Response.InstanceSet[] | select(.VirtualPrivateCloud==null) | {InstanceId, InstanceName}'

# Unassociated EIPs (cost waste)
tccli vpc DescribeAddresses --Region ap-guangzhou \
  | jq '.Response.AddressSet[] | select(.InstanceId==null) | {AddressId, AddressIp}'
```

---

## 4. Credential and Access Audit

| Rule ID | Category | Severity | CLI Check | Pass Criteria | Remediation |
|---------|----------|----------|-----------|---------------|-------------|
| `AUTH-001` | SSH Key | **CRITICAL** | `DescribeInstances \| jq '.Response.InstanceSet[] \| select(.LoginSettings.KeyIds==null or .LoginSettings.KeyIds==[]) \| {InstanceId, InstanceName}'` | All instances have SSH key pair | `CreateKeyPair --KeyName prod-key` + `AssociateInstancesKeyPairs` |
| `AUTH-002` | Password | HIGH | Check image `UserData` or AMI config | `PasswordAuthentication no` in sshd_config | Disable password auth; SSM Session Manager for console access |
| `AUTH-003` | CAM | HIGH | `cam DescribePolicyList --TargetType "User" \| jq '.PolicyList[] \| select(.PolicyName\|test("AdministratorAccess"))'` | No admin policy on service accounts | Scope to `cvm:*` + resource-level constraints |
| `AUTH-004` | Secret key | HIGH | `cam DescribeSecretKeyList --TargetUin $UIN \| jq '.Response.SecretKeyList[] \| {SecretKeyId, CreateTime, Status}'` | Key rotated < 90 days | `DeleteSecretKey --SecretKeyId xxx` + create new key |
| `AUTH-005` | Root | **CRITICAL** | `cam GetUserAppList --TargetUin $ROOT_UIN \| jq '.Response'` | Root account used only for billing | Enable root MFA; use IAM sub-account for daily ops |
| `AUTH-006` | Sub-account | HIGH | `cam ListUsers \| jq '.Data[] \| select(.UserType==0) \| {UserName, CreateTime}'` | Review all sub-accounts | Disable unused accounts; enforce MFA |
| `AUTH-007` | MFA | HIGH | `cam ListUsers \| jq '.Data[] \| select(.UinMfaFlag==false) \| {UserName}'` | Admin accounts have MFA | `cam SetMfaFlag --LoginFlag '{"Flag":1}'` |
| `AUTH-008` | Key pair | MEDIUM | `DescribeKeyPairs \| jq '.Response.KeyPairSet[] \| .KeyPairName'` | Key pairs named by purpose | Rename/add tags for traceability |

**CLI execution**:
```bash
# Instances without SSH key
tccli cvm DescribeInstances --Region ap-guangzhou \
  | jq '.Response.InstanceSet[] | select(.LoginSettings.KeyIds==null or .LoginSettings.KeyIds==[]) | {InstanceId, InstanceName}'

# Secret key age
tccli cam DescribeSecretKeyList --TargetUin "{{user.account_id}}" \
  | jq '.Response.SecretKeyList[] | {SecretKeyId, CreateTime, DaysOld: (((now - (.CreateTime | strptime("%Y-%m-%d %H:%M:%S") | mktime)) / 86400) | floor)}'
```

---

## 5. Disk and Storage Audit

| Rule ID | Category | Severity | CLI Check | Pass Criteria | Remediation |
|---------|----------|----------|-----------|---------------|-------------|
| `DISK-001` | Unattached | HIGH | `DescribeDisks --Filters '[{"Name":"disk-state","Values":["UNATTACHED"]}]'` | No unattached disks > 7 days | Delete unattached disks or attach to instance |
| `DISK-002` | Large | MEDIUM | `DescribeDisks \| jq '.DiskSet[] \| select(.DiskSize>1000) \| {DiskId, DiskSize}'` | Large disks (>1TB) have documented purpose | Downsize or document business justification |
| `DISK-003` | Encryption | MEDIUM | `DescribeDisks \| jq '.DiskSet[] \| select(.Encrypt==false) \| .DiskId'` | Sensitive data disks encrypted | Enable CBS encryption via custom key |
| `DISK-004` | Type | MEDIUM | `DescribeDisks \| jq '[.DiskSet[].DiskType] \| group_by(.) \| map({type: .[0], count: length})'` | Production on PREMIUM/SSD (not CLOUD_BASIC) | Upgrade from CLOUD_BASIC to CLOUD_SSD |
| `DISK-005` | Delete flag | LOW | `DescribeDisks \| jq '.DiskSet[] \| select(.DeleteWithInstance==false) \| {DiskId, DiskSize}'` | Reviewed non-delete disks | Confirm retention need; set `DeleteWithInstance=true` for ephemeral data |
| `DISK-006` | IOPS | MEDIUM | Check disk type against workload IOPS needs | IOPS > 80% of provisioned for > 1h | Upgrade to higher IOPS tier |
| `DISK-007` | Throughput | LOW | Check disk throughput vs workload | Throughput > 80% of provisioned | Upgrade to throughput-optimized disk |

**CLI execution**:
```bash
# Unattached disks
tccli cbs DescribeDisks --Region ap-guangzhou \
  --Filters '[{"Name":"disk-state","Values":["UNATTACHED"]}]' \
  | jq '.Response.DiskSet[] | {DiskId, DiskSize, CreateTime}'

# Disk type distribution
tccli cbs DescribeDisks --Region ap-guangzhou \
  | jq '[.Response.DiskSet[].DiskType] | group_by(.) | map({type: .[0], count: length})'
```

---

## 6. Backup and Recovery Audit

| Rule ID | Category | Severity | CLI Check | Pass Criteria | Remediation |
|---------|----------|----------|-----------|---------------|-------------|
| `BKUP-001` | Frequency | **CRITICAL** | `DescribeSnapshots --Filters '[{"Name":"disk-id","Values":["disk-xxx"]}]' \| jq '.Response.SnapshotSet[].CreatedTime'` | Daily snapshot for each production disk | Create scheduled snapshot policy |
| `BKUP-002` | Retention | HIGH | `DescribeSnapshots \| jq '.Response.SnapshotSet[] \| {DiskId, Percent, CreateTime}'` | Retention ≥ 7 days (30 days recommended) | Adjust auto-snapshot policy retention |
| `BKUP-003` | Coverage | **CRITICAL** | Compare disk count vs snapshot count per disk | All critical disks have recent snapshot | Identify uncovered disks; create snapshot policy |
| `BKUP-004` | Custom image | MEDIUM | `DescribeImages --Filters '[{"Name":"image-type","Values":["PRIVATE_IMAGE"]}]'` | Custom image for each critical service | `CreateImage --InstanceId ins-xxx --ImageName "app-v1.2.3"` |
| `BKUP-005` | Cross-region | MEDIUM | `SyncImages --DestinationRegions '["ap-shanghai"]' \| jq '.'` | DR image synced to secondary region | `SyncImages --ImageIds img-xxx --DestinationRegions '["ap-shanghai"]'` |
| `BKUP-006` | RPO | HIGH | Calculate max time between snapshots | RPO ≤ 24h (or defined SLA) | Increase snapshot frequency |
| `BKUP-007` | Snapshot age | HIGH | `DescribeSnapshots \| jq '.SnapshotSet[] \| select(.Percent<100) \| {SnapshotId, Percent, CreateTime}'` | No incomplete snapshots > 2h | Investigate snapshot failures |

**CLI execution**:
```bash
# Snapshot policy coverage
tccli cbs DescribeDisks --Region ap-guangzhou \
  | jq '.Response.DiskSet[] | {DiskId, AttachedInstanceId, SnapshotCount: (.SnapshotCount // 0)}'

# Custom images
tccli cvm DescribeImages --Region ap-guangzhou \
  --Filters '[{"Name":"image-type","Values":["PRIVATE_IMAGE"]}]' \
  | jq '.Response.ImageSet[] | {ImageId, ImageName, ImageSize}'
```

---

## 7. Cost and Billing Audit

| Rule ID | Category | Severity | CLI Check | Pass Criteria | Remediation |
|---------|----------|----------|-----------|---------------|-------------|
| `COST-001` | Idle | MEDIUM | `DescribeInstances --Filters '[{"Name":"instance-status","Values":["STOPPED"]}]' \| jq '.Response.InstanceSet[] \| select(.CreatedTime < "'$(date -d '-7 days' +%Y-%m-%d)'")'` | No STOPPED instances > 7 days | Terminate or document purpose |
| `COST-002` | Low utilization | HIGH | `GetMonitorData --MetricName CPUUsage --Period 86400 \| jq '.DataPoints[0].Values \| add / length'` | Avg CPU ≤ 10% for 7 days → downsize | Change instance type to smaller spec |
| `COST-003` | RI eligibility | HIGH | Running hours > 720h/month × steady workload | RI candidates identified | `DescribeReservedInstancesOfferings` + `PurchaseReservedInstancesOffering` |
| `COST-004` | Charge type | HIGH | `DescribeInstances \| jq '.InstanceSet[] \| {InstanceId, InstanceChargeType}'` | Steady workloads on PREPAID | Convert POSTPAID → PREPAID for 24/7 instances |
| `COST-005` | Spot opportunity | MEDIUM | Check batch/CI/dev instance patterns | Spot-eligible workloads identified | Use POSTPAID_BY_HOUR with spot market price |
| `COST-006` | Bandwidth | MEDIUM | Check network billing mode | Pay-by-traffic for variable | Optimize bandwidth package billing |
| `COST-007` | Daily anomaly | HIGH | Compare today cost vs 7-day avg | Cost < 2× baseline | Investigate cost spike via Bill API |
| `COST-008` | Delete protection | LOW | `DescribeInstances \| jq '.InstanceSet[].DisableApiTermination'` | Critical instances have termination protection | `ModifyInstancesAttribute --DisableApiTermination TRUE` |

**CLI execution**:
```bash
# Charge type distribution
tccli cvm DescribeInstances --Region ap-guangzhou \
  | jq '[.Response.InstanceSet[].InstanceChargeType] | group_by(.) | map({type: .[0], count: length})'

# Daily CPU avg for right-sizing
tccli monitor GetMonitorData \
  --Namespace QCE/CVM \
  --MetricName CPUUsage \
  --Dimensions '[{"Name":"InstanceId","Value":"ins-xxx"}]' \
  --StartTime "$(date -d '-7 days' +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --EndTime "$(date +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --Period 86400 \
  | jq '.Response.DataPoints[0].Values | add / (length // 1)'
```

---

## 8. Monitoring and Tagging Audit

| Rule ID | Category | Severity | CLI Check | Pass Criteria | Remediation |
|---------|----------|----------|-----------|---------------|-------------|
| `MON-001` | CPU alarm | HIGH | `DescribeAlarmPolicies --Module monitor --Namespace QCE/CVM \| jq '.Policies[] \| select(.Conditions[].MetricName=="CPUUsage")'` | CPU alarm configured for all instances | Create alarm: `CPUUsage > 80% for 10 min` |
| `MON-002` | Memory alarm | HIGH | `DescribeAlarmPolicies --Module monitor \| jq '.Policies[] \| select(.Conditions[].MetricName=="MemUsage")'` | Memory alarm configured | Create alarm: `MemUsage > 85% for 10 min` |
| `MON-003` | Disk alarm | HIGH | `DescribeAlarmPolicies --Module monitor \| jq '.Policies[] \| select(.Conditions[].MetricName=="DiskUsage")'` | Disk alarm configured | Create alarm: `DiskUsage > 90%` |
| `MON-004` | Status alarm | MEDIUM | `DescribeAlarmPolicies --Module monitor \| jq '.Policies[] \| select(.PolicyName\|test("InstanceStatus"))'` | Instance status change alerts | Set alarm on `InstanceStateChange` |
| `MON-005` | Dashboard | LOW | Check Grafana/Cloud Monitor dashboard | CVM dashboard created | Create resource overview dashboard |
| `MON-006` | Network alarm | MEDIUM | `DescribeAlarmPolicies --Module monitor \| jq '.Policies[] \| select(.Conditions[].MetricName=="NetworkOut")'` | Network bandwidth alarm | Create alarm: `NetworkOut > 90% max` |
| `TAG-001` | Environment | HIGH | `DescribeInstances \| jq '.InstanceSet[].Tags[] \| select(.Key=="Environment") \| {InstanceId, Value}'` | All instances have Environment tag | Add tag: `Environment: production/staging/dev` |
| `TAG-002` | Project | HIGH | `DescribeInstances \| jq '.InstanceSet[].Tags[] \| select(.Key=="Project") \| {InstanceId, Value}'` | Project tag present | Add tag: `Project: <project-name>` |
| `TAG-003` | Owner | MEDIUM | `DescribeInstances \| jq '.InstanceSet[].Tags[] \| select(.Key=="Owner") \| {InstanceId, Value}'` | Owner identified | Add tag: `Owner: <team-name>` |
| `TAG-004` | CostCenter | MEDIUM | `DescribeInstances \| jq '.InstanceSet[].Tags[] \| select(.Key=="CostCenter") \| {InstanceId, Value}'` | Cost allocation tag present | Add tag: `CostCenter: <dept-code>` |
| `TAG-005` | Untagged | HIGH | `DescribeInstances \| jq '.InstanceSet[] \| select(.Tags==null or .Tags==[]) \| {InstanceId, InstanceName}'` | Zero untagged instances | Apply mandatory tags per tagging policy |

**CLI execution**:
```bash
# Untagged instances
tccli cvm DescribeInstances --Region ap-guangzhou \
  | jq '.Response.InstanceSet[] | select(.Tags==null or .Tags==[]) | {InstanceId, InstanceName}'

# Environment tag coverage
tccli cvm DescribeInstances --Region ap-guangzhou \
  | jq '[.Response.InstanceSet[].Tags[] | select(.Key=="Environment").Value] | group_by(.) | map({env: .[0], count: length})'
```

---

## 9. Scheduled Audit Checklists

### 9.1 Daily Checklist

```markdown
- [ ] `LIFE-001`: Check PENDING instances > 5 min
- [ ] `SEC-001`: Quick scan — SSH still not public?
- [ ] `COST-007`: Cost anomaly detection
- [ ] `MON-001/2/3`: Review active alarms
- [ ] `BKUP-007`: Check incomplete snapshots
```

### 9.2 Weekly Checklist

```markdown
- [ ] `LIFE-005`: Audit recent TerminateInstances events
- [ ] `SEC-003/4/5`: Full security group exposure scan
- [ ] `DISK-001`: Delete or attach unattached disks
- [ ] `COST-002`: Right-sizing review (idle instances)
- [ ] `AUTH-004`: Check secret key age
- [ ] `TAG-005`: Tagging compliance scan
```

### 9.3 Monthly Checklist

```markdown
- [ ] `LIFE-004`: Legacy instance review (> 1 year)
- [ ] `NET-003`: Release unassociated EIPs
- [ ] `COST-003/4`: RI conversion review
- [ ] `BKUP-005`: Cross-region image sync
- [ ] `AUTH-003`: CAM policy audit
- [ ] `SEC-006`: Delete unused security groups
- [ ] Full audit score calculation (Section 12)
```

---

## 10. Pre-Deployment Safety Checks

Before any `RunInstances`, `TerminateInstances`, or `ModifySecurityGroupPolicies`:

```bash
#!/bin/bash
# Pre-deployment safety check

echo "=== Pre-Deployment Audit ==="

# 1. Check quota
tccli cvm DescribeInstances --Limit 0 --Region ap-guangzhou | jq '.Response.TotalCount'

# 2. Validate security group (no 0.0.0.0/0 for SSH)
tccli vpc DescribeSecurityGroupPolicies --Region ap-guangzhou --SecurityGroupId sg-xxx \
  | jq '.Inbound[] | select(.CidrBlock=="0.0.0.0/0" and (.PortRange|contains("22")))' \
  && echo "⚠️ WARNING: SSH is public!"

# 3. Check disk quota
tccli cbs DescribeDisks --Region ap-guangzhou --Limit 0 | jq '.Response.TotalCount'

# 4. Verify VPC and subnet
tccli vpc DescribeSubnets --Region ap-guangzhou --SubnetIds '["subnet-xxx"]' | jq '.Response.SubnetSet[0].AvailableIpAddressCount'
```

---

## 11. Post-Incident Forensics Audit

After a security incident or unexpected termination:

```bash
#!/bin/bash
# Post-incident forensics

INSTANCE_ID="${1:?Usage: $0 <instance-id>}"
REGION="${2:-ap-guangzhou}"

echo "=== Forensics: $INSTANCE_ID ==="

# 1. Termination events
echo "### Termination Events"
tccli cloudaudit LookUpEvents \
  --StartTime "$(date -d '-30 days' +'%Y-%m-%dT00:00:00+08:00')" \
  --EndTime "$(date +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --ActionNames "[\"TerminateInstances\"]" \
  --LookupAttributes '[{"AttributeKey":"ResourceName","AttributeValue":"'"$INSTANCE_ID"'"}]'

# 2. Configuration changes
echo "### Configuration Changes"
tccli cloudaudit LookUpEvents \
  --StartTime "$(date -d '-30 days' +'%Y-%m-%dT00:00:00+08:00')" \
  --EndTime "$(date +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --ActionNames "[\"ModifyInstanceAttribute\",\"ModifyInstancesAttribute\",\"ResetInstance\"]" \
  --LookupAttributes '[{"AttributeKey":"ResourceName","AttributeValue":"'"$INSTANCE_ID"'"}]'

# 3. Associated disk events
echo "### Disk Operations"
tccli cloudaudit LookUpEvents \
  --StartTime "$(date -d '-30 days' +'%Y-%m-%dT00:00:00+08:00')" \
  --EndTime "$(date +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --ActionNames "[\"AttachDisks\",\"DetachDisks\",\"ModifyDiskAttributes\"]" \
  --LookupAttributes '[{"AttributeKey":"ResourceName","AttributeValue":"'"$INSTANCE_ID"'"}]'
```

---

## 12. Comprehensive Audit Script

```bash
#!/bin/bash
# ============================================
# CVM Comprehensive Audit
# Save: /data/scripts/cvm_full_audit.sh
# ============================================
set -euo pipefail

REGION="${2:-ap-guangzhou}"
OUTPUT_DIR="/data/audit"
AUDIT_DATE=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="${OUTPUT_DIR}/cvm_audit_${AUDIT_DATE}.md"

mkdir -p "${OUTPUT_DIR}"

exec > >(tee -a "${OUTPUT_FILE}") 2>&1

echo "# CVM Audit Report — $(date)"
echo "---"

# --- 1. Lifecycle ---
echo ""
echo "## 1. Instance Lifecycle"
echo ""
echo "### Pending instances"
tccli cvm DescribeInstances --Region $REGION \
  --Filters '[{"Name":"instance-status","Values":["PENDING"]}]' \
  | jq '.Response.InstanceSet[] | {InstanceId, InstanceName, CreatedTime}' || echo "None"
echo ""
echo "### Stopped instances > 24h"
tccli cvm DescribeInstances --Region $REGION \
  --Filters '[{"Name":"instance-status","Values":["STOPPED"]}]' \
  | jq '.Response.InstanceSet[] | select(.CreatedTime < "'$(date -d '-1 day' +'%Y-%m-%dT%H:%M:%S+08:00')'") | {InstanceId, InstanceName, CreatedTime}' || echo "None"
echo ""

# --- 2. Security Groups ---
echo "## 2. Security Groups"
echo ""
for SG in $(tccli vpc DescribeSecurityGroups --Region $REGION | jq -r '.Response.SecurityGroupSet[].SecurityGroupId'); do
  echo "### $SG"
  tccli vpc DescribeSecurityGroupPolicies --Region $REGION --SecurityGroupId $SG \
    | jq '.Response.Inbound[] | select(.CidrBlock=="0.0.0.0/0") | {PortRange, CidrBlock, Action}' || echo "No public rules"
  echo ""
done

# --- 3. Network ---
echo "## 3. Network"
echo ""
echo "### Basic Network instances"
tccli cvm DescribeInstances --Region $REGION \
  | jq '.Response.InstanceSet[] | select(.VirtualPrivateCloud==null) | {InstanceId, InstanceName}' || echo "None"
echo ""
echo "### Unassociated EIPs"
tccli vpc DescribeAddresses --Region $REGION \
  | jq '.Response.AddressSet[] | select(.InstanceId==null) | {AddressId, AddressIp}' || echo "None"
echo ""

# --- 4. Credential ---
echo "## 4. Credential"
echo ""
echo "### Instances without SSH key"
tccli cvm DescribeInstances --Region $REGION \
  | jq '.Response.InstanceSet[] | select(.LoginSettings.KeyIds==null or .LoginSettings.KeyIds==[]) | {InstanceId, InstanceName}' || echo "None"
echo ""

# --- 5. Disks ---
echo "## 5. Disks"
echo ""
echo "### Unattached disks"
tccli cbs DescribeDisks --Region $REGION \
  --Filters '[{"Name":"disk-state","Values":["UNATTACHED"]}]' \
  | jq '.Response.DiskSet[] | {DiskId, DiskSize, CreateTime}' || echo "None"
echo ""

# --- 6. Backup ---
echo "## 6. Backup"
echo ""
echo "### Custom images"
tccli cvm DescribeImages --Region $REGION \
  --Filters '[{"Name":"image-type","Values":["PRIVATE_IMAGE"]}]' \
  | jq '.Response.ImageSet[] | {ImageId, ImageName, ImageSize}' || echo "None"
echo ""

# --- 7. Tags ---
echo "## 7. Tagging"
echo ""
echo "### Untagged instances"
tccli cvm DescribeInstances --Region $REGION \
  | jq '.Response.InstanceSet[] | select(.Tags==null or .Tags==[]) | {InstanceId, InstanceName}' || echo "None"
echo ""

# --- Summary ---
echo "## Summary"
echo ""
TOTAL=$(tccli cvm DescribeInstances --Region $REGION --Limit 0 | jq '.Response.TotalCount')
echo "- Total instances: ${TOTAL}"
echo "- Audit report: ${OUTPUT_FILE}"
echo ""
echo "---"
echo "Audit complete at $(date)"
```

---

## 13. Audit Score Calculation

### Weight Matrix

| Category | Weight | Rules | Critical Items |
|----------|--------|-------|---------------|
| 1. Lifecycle | 10% | 7 | `LIFE-001` |
| 2. Security | 30% | 9 | `SEC-001/2/3/4` |
| 3. Network | 10% | 7 | `NET-001` |
| 4. Credential | 20% | 8 | `AUTH-001/5` |
| 5. Disk | 5% | 7 | — |
| 6. Backup | 5% | 7 | `BKUP-001/3` |
| 7. Cost | 8% | 8 | — |
| 8. Monitor+Tag | 12% | 11 | — |

### Python Score Engine

```python
"""cvm_audit_score.py — Calculate CVM compliance score"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class AuditCategory:
    name: str
    weight: float
    rules: List[str]
    passed: int = 0
    total: int = 0
    critical_failures: int = 0


@dataclass
class AuditResult:
    """Overall audit result with recommendations"""
    categories: Dict[str, AuditCategory] = field(default_factory=dict)
    score: float = 0.0
    grade: str = "F"

    def calculate(self) -> None:
        """Calculate weighted score and determine grade"""
        weighted_sum = 0.0
        total_critical = 0

        for cat in self.categories.values():
            if cat.total == 0:
                continue
            cat_score = (cat.passed / cat.total) * 100
            weighted_sum += cat_score * cat.weight
            total_critical += cat.critical_failures

        self.score = weighted_sum
        self.grade = self._grade(self.score, total_critical)

    @staticmethod
    def _grade(score: float, critical_failures: int) -> str:
        if critical_failures > 0:
            return "F"  # Any critical failure = F
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 70:
            return "C"
        if score >= 60:
            return "D"
        return "F"

    def summary(self) -> str:
        sections = []
        for name, cat in self.categories.items():
            status = "✅" if (cat.total > 0 and cat.passed == cat.total) else "⚠️"
            sections.append(
                f"| {name} | {cat.weight*100:.0f}% | "
                f"{cat.passed}/{cat.total} | "
                f"{cat.critical_failures} | {status} |"
            )
        header = "| Category | Weight | Score | Critical | Status |\n"
        header += "|----------|--------|-------|----------|--------|\n"
        body = "\n".join(sections)
        return (
            f"## Audit Score: {self.score:.1f}/100 — Grade: {self.grade}\n\n"
            + header + body
        )


def run_audit(rules_results: Dict[str, bool]) -> AuditResult:
    """Run audit from rule pass/fail results"""
    categories = {
        "Lifecycle": AuditCategory("Lifecycle", 0.10, ["LIFE-001","LIFE-002","LIFE-003","LIFE-004","LIFE-005","LIFE-006","LIFE-007"]),
        "Security": AuditCategory("Security", 0.30, ["SEC-001","SEC-002","SEC-003","SEC-004","SEC-005","SEC-006","SEC-007","SEC-008","SEC-009"]),
        "Network": AuditCategory("Network", 0.10, ["NET-001","NET-002","NET-003","NET-004","NET-005","NET-006","NET-007"]),
        "Credential": AuditCategory("Credential", 0.20, ["AUTH-001","AUTH-002","AUTH-003","AUTH-004","AUTH-005","AUTH-006","AUTH-007","AUTH-008"]),
        "Disk": AuditCategory("Disk", 0.05, ["DISK-001","DISK-002","DISK-003","DISK-004","DISK-005","DISK-006","DISK-007"]),
        "Backup": AuditCategory("Backup", 0.05, ["BKUP-001","BKUP-002","BKUP-003","BKUP-004","BKUP-005","BKUP-006","BKUP-007"]),
        "Cost": AuditCategory("Cost", 0.08, ["COST-001","COST-002","COST-003","COST-004","COST-005","COST-006","COST-007","COST-008"]),
        "Monitor+Tag": AuditCategory("Monitor+Tag", 0.12, ["MON-001","MON-002","MON-003","MON-004","MON-005","MON-006","TAG-001","TAG-002","TAG-003","TAG-004","TAG-005"]),
    }

    for rule_id, passed in rules_results.items():
        for cat in categories.values():
            if rule_id in cat.rules:
                cat.total += 1
                if passed:
                    cat.passed += 1
                else:
                    # Check if critical
                    critical_rules = {
                        "LIFE-001", "SEC-001", "SEC-002", "SEC-003", "SEC-004",
                        "NET-001", "AUTH-001", "AUTH-005", "BKUP-001", "BKUP-003",
                    }
                    if rule_id in critical_rules:
                        cat.critical_failures += 1

    result = AuditResult(categories=categories)
    result.calculate()
    return result
```

---

## Audit Rule Quick Reference

| ID | Category | Severity | Section |
|----|----------|----------|---------|
| `LIFE-001` to `LIFE-007` | Lifecycle | CRITICAL → LOW | 1 |
| `SEC-001` to `SEC-009` | Security Group | CRITICAL → LOW | 2 |
| `NET-001` to `NET-007` | Network | CRITICAL → LOW | 3 |
| `AUTH-001` to `AUTH-008` | Credential | CRITICAL → MEDIUM | 4 |
| `DISK-001` to `DISK-007` | Disk | HIGH → LOW | 5 |
| `BKUP-001` to `BKUP-007` | Backup | CRITICAL → HIGH | 6 |
| `COST-001` to `COST-008` | Cost | HIGH → LOW | 7 |
| `MON-001` to `MON-006` | Monitoring | HIGH → LOW | 8 |
| `TAG-001` to `TAG-005` | Tagging | HIGH → MEDIUM | 8 |

---

## Cross-References

| This File | Reference | Integration Point |
|-----------|-----------|-------------------|
| Audit Rules | [SecOps Checklist](secops-checklist.md) | Section 8: CVM Audit Rules Integration |
| Audit Rules | [FinOps Analysis](finops-analysis.md) | Cost rules align with `COST-001` to `COST-008` |
| Audit Rules | [Proactive Inspection](proactive-inspection.md) | Inspection triggers map to audit rule IDs |
| Audit Rules | [SKILL.md](../SKILL.md) | Execution flows reference audit rules via safety gates |
| SEC-001/2/3 | [Troubleshooting](troubleshooting.md) | Error codes for SG misconfiguration |
| MON-001/2/3 | [Monitoring](monitoring.md) | Alarm policy configuration details |