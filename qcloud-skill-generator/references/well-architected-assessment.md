# Well-Architected Assessment (Tencent Cloud)

This document defines the four-pillar Well-Architected Framework assessment for Tencent Cloud skills, adapted from the Tencent Cloud architecture best practices.

---

## Overview

Every generated `qcloud-[product]-ops` skill MUST integrate with Tencent Cloud's Well-Architected Framework across four pillars:

1. **可靠性 (Reliability)**
2. **安全性 (Security)**
3. **成本 (Cost)**
4. **效率 (Efficiency)**

Each skill maps its operations to these pillars in a dedicated assessment section.

---

## Pillar 1: Reliability (可靠性)

### 1.1 Multi-AZ Deployment

| Requirement | Skill Integration |
|-------------|-------------------|
| Cross-AZ capability | Document how to deploy across availability zones |
| Disaster recovery | Include DR runbook with region failover |
| Backup strategy | Define RPO/RTO and backup frequency |

### 1.2 Backup & Recovery Operations

Every writable skill MUST document:

| Operation | Coverage |
|-----------|----------|
| Create backup/snapshot | Document backup creation flow |
| Describe backups | List available backups |
| Restore from backup | Document restore flow with data validation |
| Delete backup | Safety gates for backup deletion |
| Backup retention | Default retention policy |

### 1.3 Failure-Oriented Design

| Scenario | Runbook Required |
|----------|-----------------|
| Instance failure | Document recovery steps |
| Region outage | Cross-region failover procedure |
| Data corruption | Backup restoration procedure |
| Network partition | Connectivity recovery |

### 1.4 Health Checks

| Requirement | Skill Coverage |
|-------------|----------------|
| Pre-flight validation | Resource existence, quota, dependency checks |
| Post-operation polling | State verification until terminal state |
| Ongoing monitoring | Integration with Tencent Cloud Monitor |

### 1.5 Safety Gates

**Mandatory for destructive operations:**

- Explicit user confirmation with resource identifier
- Pre-backup reminder (snapshot before delete)
- Dependency check (warn if resource has attachments)
- Post-delete verification (poll until 404)

---

## Pillar 2: Security (安全性)

### 2.1 CAM (Cloud Access Management) Permissions

| Requirement | Skill Integration |
|-------------|-------------------|
| Minimum permissions | Document required CAM policies |
| Role-based access | Suggest appropriate roles |
| Principle of least privilege | List specific API permissions |

**Example CAM Policy:**

```json
{
  "version": "2.0",
  "statement": [
    {
      "action": [
        "cvm:DescribeInstances",
        "cvm:RunInstances",
        "cvm:TerminateInstances"
      ],
      "effect": "allow",
      "resource": "*"
    }
  ]
}
```

### 2.2 Credential Management

| Requirement | Implementation |
|-------------|----------------|
| Environment variables | Use `TENCENTCLOUD_SECRET_ID/KEY` |
| Credential masking | NEVER print SecretKey in output |
| Secure storage | Recommend CAM roles over static keys |

### 2.3 Network Isolation

| Requirement | Skill Coverage |
|-------------|----------------|
| VPC configuration | Document VPC/VPC isolation |
| Security groups | Document security group management |
| Network ACLs | Include ACL configuration if applicable |

### 2.4 Encryption

| Requirement | Skill Coverage |
|-------------|----------------|
| Data encryption | Document encryption options (storage, transit) |
| Key management | Integration with KMS if applicable |
| Encryption status | Verify encryption in Describe operations |

---

## Pillar 3: Cost (成本)

### 3.1 Billing Model Documentation

| Model Type | Skill Coverage |
|------------|----------------|
| On-demand pricing | Document hourly/usage-based pricing |
| Reserved instances | Document reserved purchase options |
| Spot/preemptible | Document spot instance usage if available |

### 3.2 Cost Comparison Table

| Resource Type | Hourly Cost | Reserved Cost (1yr) | Reserved Cost (3yr) |
|---------------|-------------|---------------------|---------------------|
| [Type1] | $X/hr | $Y/mo | $Z/mo |
| [Type2] | $A/hr | $B/mo | $C/mo |

> Fill this table with actual pricing from Tencent Cloud official pricing page.

### 3.3 Idle Resource Detection

| Pattern | Detection Method | Recommendation |
|---------|-----------------|----------------|
| Low CPU utilization | CPU < 10% over 7 days | Downsize or terminate |
| Low memory utilization | Memory < 20% over 7 days | Downsize |
| Stopped instance | Instance STOPPED > 7 days | Review if needed |
| Unattached disk | CBS UNATTACHED > 30 days | Review if needed |

### 3.4 Right-Sizing Recommendations

| Current State | Recommendation |
|---------------|----------------|
| CPU > 80% sustained | Upsize CPU |
| Memory > 90% sustained | Upsize memory |
| CPU < 10% sustained | Downsize |
| Disk I/O near limit | Upgrade disk type |

---

## Pillar 4: Efficiency (效率)

### 4.1 Batch Operations

| Operation | Batch Support | Skill Coverage |
|-----------|---------------|----------------|
| Create | Yes (max 100) | Document batch create with instance IDs |
| Describe | Yes (pagination) | Document pagination loop |
| Modify | Yes | Document batch modify |
| Delete | Yes | Document batch delete with safety gate |

### 4.2 Automation Integration

| Integration | Skill Coverage |
|-------------|----------------|
| CI/CD pipeline | Document pipeline integration points |
| Infrastructure as Code | Terraform/CloudFormation examples |
| Scheduled operations | Document recurring job patterns |

### 4.3 Resource Scheduling

| Feature | Skill Coverage |
|---------|----------------|
| Start/Stop schedules | Document auto-scheduling if available |
| Maintenance windows | Document maintenance window configuration |
| Scaling policies | Document auto-scaling integration |

### 4.4 API Optimization

| Optimization | Skill Coverage |
|--------------|----------------|
| Pagination efficiency | Use appropriate Limit values |
| Batch API calls | Use batch operations where available |
| Caching | Document caching strategies for Describe |

---

## Assessment Template

Each generated skill includes this assessment section:

```markdown
## Well-Architected Assessment

### Reliability (可靠性)

| Requirement | Status | Documentation |
|-------------|--------|---------------|
| Multi-AZ deployment | ✓/✗ | [Reference or N/A] |
| Backup operations | ✓ | See Backup section |
| Recovery runbook | ✓ | See Restore section |
| Safety gates | ✓ | All destructive ops have confirmation |

### Security (安全性)

| Requirement | Status | Documentation |
|-------------|--------|---------------|
| Minimum CAM permissions | ✓ | See CAM section below |
| Credential masking | ✓ | Enforced in all paths |
| Network isolation | ✓/✗ | [VPC/Security Group docs] |
| Encryption | ✓/✗ | [Encryption options documented] |

### Cost (成本)

| Requirement | Status | Documentation |
|-------------|--------|---------------|
| Billing models | ✓ | See Cost section |
| Idle detection | ✓ | See Optimization section |
| Right-sizing | ✓ | See Recommendations |

### Efficiency (效率)

| Requirement | Status | Documentation |
|-------------|--------|---------------|
| Batch operations | ✓ | See Batch section |
| Automation support | ✓ | See Integration section |
| API optimization | ✓ | Pagination documented |

---

### CAM Policy Example

```json
{
  "version": "2.0",
  "statement": [
    {
      "action": [
        "[product]:Describe*",
        "[product]:Create*",
        "[product]:Modify*",
        "[product]:Delete*"
      ],
      "effect": "allow",
      "resource": "qcs:[product]:[region]:*:/*"
    }
  ]
}
```

---

## Worker Output Contract (generated skills)

Every product `references/well-architected-assessment.md` generated by `qcloud-skill-generator` **MUST** include a final **Worker Output Contract (Read-Only Assessment Mode)** section aligned with:

[worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

Required contents:

| Item | Rule |
|------|------|
| `skill_id` / `product` | Match the generated skill directory name and registry code |
| Finding `id` | `{product}-{rel\|sec\|cost\|eff}-NNN` |
| Example JSON | Full valid `{{output.product_assessment}}` with all schema fields |
| Pillar map | Link each `pillars.*` key to checklist sections in the same file |

Copy the section pattern from any Phase 1 worker (e.g. `qcloud-cvm-ops/references/well-architected-assessment.md`).

---

## References

- [Tencent Cloud Well-Architected Framework](https://cloud.tencent.com/document/product/xxx)
- [Tencent Cloud Architecture Best Practices](https://cloud.tencent.com/document/product/xxx)
- [CAM Policy Documentation](https://cloud.tencent.com/document/product/598)