# Reliability Pillar — Tencent Cloud Well-Architected Framework

## Overview

The Reliability pillar ensures your Tencent Cloud architecture can withstand failures and recover quickly. Assessment covers: backup/recovery, disaster recovery, multi-AZ deployment, health checks, and safety gates.

## 1. Multi-AZ Deployment

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| Cross-AZ nodes | `DescribeInstances` for each product | Resources deployed across ≥ 2 AZs |
| Single-AZ risk | Count instances per AZ | No single point of failure if AZ goes down |
| Region failover | Check DR documentation | Runbook exists for region failover |

**CLI pattern:**
```bash
# Check CVM AZ distribution
tccli cvm DescribeInstances --Region {{env.TENCENTCLOUD_REGION}} \
  --Filter '{"Name":"zone","Values":["ap-guangzhou-1","ap-guangzhou-2"]}' \
  | jq '.InstanceSet[] | {InstanceId, Zone}' | jq -s 'group_by(.Zone) | map({zone: .[0].Zone, count: length})'
```

## 2. Backup & Recovery Operations

### 2.1 Backup Coverage Checklist

| Operation | Required | Assessment Method |
|-----------|----------|-------------------|
| Automated backup enabled | Yes | Check backup config per instance |
| Backup frequency adequate | Yes | Daily for production, weekly for dev |
| RPO ≤ target | Yes | Compare backup frequency to RPO requirement |
| RTO ≤ target | Yes | Test restore time against RTO target |
| Backup retention policy | Yes | Check retention period (default: 7 days) |

### 2.2 Per-Product Backup Assessment

| Product | Backup Command | Verification |
|---------|---------------|--------------|
| CVM | `tccli cvm DescribeImages` | Latest snapshot < 24h old |
| CDB | `tccli cdb DescribeBackups` | Latest backup < 24h old |
| Redis | `tccli redis DescribeInstanceBackupRecords` | Latest backup < 24h old |
| ES | Snapshot configuration in `DescribeInstances` | Snapshot enabled |

## 3. Failure-Oriented Design

### 3.1 Failure Scenarios & Runbooks

| Scenario | Runbook Required | Assessment |
|----------|-----------------|------------|
| Instance failure | Recovery procedure exists | ✓ if runbook documented |
| Region outage | Cross-region failover | ✓ if multi-region deployed |
| Data corruption | Backup restore procedure | ✓ if restore tested recently |
| Network partition | Connectivity recovery steps | ✓ if VPC/config documented |

### 3.2 Health Check Assessment

| Check | Assessment | Pass Criteria |
|-------|-----------|---------------|
| Pre-flight validation | Resource existence, quota, dependencies | Documented in skill |
| Post-operation polling | State verification until terminal | Terminal state names documented |
| Ongoing monitoring | Integration with TCOP | Alert rules configured |

## 4. Safety Gates for Destructive Operations

| Gate | Required | Assessment |
|------|----------|------------|
| Explicit confirmation | Before every destructive operation | ✓ if confirmation step present |
| Pre-backup reminder | Before delete/terminate | ✓ if backup suggestion documented |
| Dependency check | Before delete with attachments | ✓ if dependency verification present |
| Post-delete verification | Poll until 404 | ✓ if poll-until-gone documented |

## Scoring Rubric

| Score | Criteria |
|-------|----------|
| 90-100 | Multi-AZ deployed, automated backup, DR runbook tested quarterly |
| 70-89 | Multi-AZ partial, backup configured but recovery not tested |
| 50-69 | Single AZ, backup configured manually, no DR runbook |
| < 50 | Single AZ, no backup, no recovery plan |
