# qcloud-mongodb-ops Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a complete `qcloud-mongodb-ops` Agent Skill for Tencent Cloud MongoDB operational management, following the qcloud-skill-generator template.

**Architecture:** Monorepo skill directory at `qcloud-mongodb-ops/` with SKILL.md as the main entry point, plus 8 reference files and 2 asset files. Uses `cli_applicability: dual-path` (tccli CLI primary, Python SDK fallback). API version: 2019-07-25.

**Tech Stack:** tccli CLI, tencentcloud-sdk-python-mongodb, Python 3.8+, Markdown/YAML skill files.

**Product Info:**
- Product: TencentDB for MongoDB (云数据库 MongoDB)
- CLI slug: `mongodb`
- API version: `2019-07-25`
- SDK: `tencentcloud-sdk-python-mongodb` (`from tencentcloud.mongodb.v20190725 import mongodb_client, models`)
- CLI applicability: `dual-path` (verified: `tccli mongodb help` lists 79 actions)
- Primary resource: `DBInstance` (实例)
- Instance types: replica set (0), sharded cluster (1)
- Payment modes: prepaid (1), postpaid (0)

**Key Operations:** Create/Describe/Modify/Delete instances, backup/restore, accounts, parameters, monitoring, SSL, audit, slow logs, security groups.

---

### Task 1: Create skill directory structure

**Files:** Create the entire `qcloud-mongodb-ops/` directory layout

- [ ] **Create directory tree**

```bash
mkdir -p qcloud-mongodb-ops/{references,assets}
```

Expected: Empty directories created.

- [ ] **Verify layout**

```bash
ls -la qcloud-mongodb-ops/
ls -la qcloud-mongodb-ops/references/
ls -la qcloud-mongodb-ops/assets/
```

Expected: Both directories exist and are empty.

---

### Task 2: Create SKILL.md (main skill file)

**Files:**
- Create: `qcloud-mongodb-ops/SKILL.md`

- [ ] **Write SKILL.md with complete content**

This is the largest file. It should include:
1. Frontmatter with product metadata
2. Overview with CLI applicability
3. Five Core Standards table
4. Well-Architected Framework Integration
5. Trigger & Scope (SHOULD/SHOULD NOT Use)
6. Variable Convention (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`)
7. API and Response Conventions with field tables
8. Quick Start section
9. Capabilities at a Glance
10. **Execution Flows:**
    - Create Instance (monthly + hourly)
    - Describe Instance
    - Modify Instance Spec (vertical scaling)
    - Delete Instance (Isolate + Offline)
    - Backup Instance (manual + auto backup rules)
    - Restore Instance
    - Account Management (create, describe, set privilege, reset password)
    - Parameter Management (describe, modify)
    - Monitoring & Slow Logs
    - SSL/TLS Management
    - Audit Service Management
    - Security Group Management
11. Error Code Reference (≥ 10 product-specific codes)
12. Safety Gates section
13. Output Schema
14. Changelog

Use all the Mongo-specific data collected: API operations, error codes, state transitions (instance statuses: 0=creating, 1=in progress, 2=running, 3=isolated, -2=deleted), data structures.

```markdown
---
name: qcloud-mongodb-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Tencent
  Cloud MongoDB (TencentDB for MongoDB / 云数据库 MongoDB) — instance lifecycle,
  backup/restore, account management, parameter tuning, slow log analysis, audit
  configuration, SSL/TLS, security groups, and performance diagnostics. User
  mentions MongoDB, Mongo, 云数据库 MongoDB, TencentDB MongoDB, or describes
  database connection issues, performance degradation, backup failures, or
  instance creation/modification/deletion scenarios even without naming the
  product directly. Not for basic VPC/CAM/billing operations which have their
  own ops skills.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python-mongodb),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.0.0"
  last_updated: "2026-05-29"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/240 — 2019-07-25"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli mongodb help` — 79 available actions for version
    2019-07-25, covering all major instance, backup, account, audit, and
    parameter operations. Python SDK fallback for edge cases.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

...
```

Full content follows the template structure with MongoDB-specific details. Could you implement this file first following the pattern from qcloud-skill-generator/references/qcloud-skill-template.md?

Wait — this is an AI agent instruction. Let me restructure this task to be concrete:

- [ ] **Step 1: Write SKILL.md frontmatter and opening sections**

Write the frontmatter (as shown above), Overview, Five Core Standards, Well-Architected Framework, and Trigger & Scope sections.

```yaml
# In the frontmatter, use exactly:
name: qcloud-mongodb-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Tencent
  Cloud MongoDB (TencentDB for MongoDB / 云数据库 MongoDB) — instance lifecycle,
  backup/restore, account management, parameter tuning, slow log analysis, audit
  configuration, SSL/TLS, security groups, and performance diagnostics. User
  mentions MongoDB, Mongo, 云数据库 MongoDB, TencentDB MongoDB, or describes
  database connection issues, performance degradation, backup failures, or
  instance creation/modification/deletion scenarios even without naming the
  product directly. Not for basic VPC/CAM/billing operations which have their
  own ops skills.
```

- [ ] **Step 2: Write Variable Convention, API Conventions, Quick Start sections**

Variables:
```
| Placeholder | Source | Meaning | Agent Action |
|-------------|--------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | Environment | Tencent Cloud Secret ID | NEVER ask user |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | Environment | Tencent Cloud Secret Key | NEVER ask user |
| `{{env.TENCENTCLOUD_REGION}}` | Environment | Region | Use documented default |
| `{{user.instance_id}}` | User input | MongoDB instance ID (cmgo-xxxx) | Ask once; reuse |
| `{{user.instance_name}}` | User input | Instance display name | Ask once; reuse |
| `{{user.region}}` | User input | Override region | Ask only if needed |
| `{{output.instance_id}}` | API response | New instance ID | Parse from CreateDBInstance |
| `{{output.deal_id}}` | API response | Order/deal ID | Parse from CreateDBInstance |
| `{{output.backup_id}}` | API response | Backup ID | Parse from CreateBackupDBInstance |
```

- [ ] **Step 3: Write execution flows - Create Instance (monthly + hourly)**

Include both `tccli mongodb CreateDBInstance` and `tccli mongodb CreateDBInstanceHour` paths. Show pre-flight (check quota, credentials, region), execute with spec parameters, poll `DescribeAsyncRequestInfo` for async task completion, validate via `DescribeDBInstances`.

Pre-flight checks:
| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Credentials | Check env vars | Non-empty | HALT |
| Region | `tccli mongodb DescribeSpecInfo` | Specs available | Suggest valid region |
| Spec | Query available specs | Requested spec on sale | Show available specs |
| Quota | InquirePrice | Price returned | HALT; check limits |

CLI execution path (monthly):
```bash
tccli mongodb CreateDBInstance \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --NodeNum 3 \
  --Memory 4 \
  --Volume 10 \
  --MongoVersion "MONGO_42_WT" \
  --MachineCode "HIO10G" \
  --GoodsNum 1 \
  --Zone "{{user.zone}}" \
  --ClusterType 0 \
  --Period 1
```

CLI execution path (hourly):
```bash
tccli mongodb CreateDBInstanceHour \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --NodeNum 3 \
  --Memory 4 \
  --Volume 10 \
  --MongoVersion "MONGO_42_WT" \
  --MachineCode "HIO10G" \
  --GoodsNum 1 \
  --Zone "{{user.zone}}" \
  --ClusterType 0
```

Post-execution validation:
1. Parse `{{output.deal_id}}` from response
2. Poll `DescribeAsyncRequestInfo` with DealId every 5s, max 600s
3. Wait for status=executing → success
4. Call `DescribeDBInstances` to get `{{output.instance_id}}` and status

- [ ] **Step 4: Write execution flows - Describe, Modify, Delete Instance**

**Describe:**
```bash
tccli mongodb DescribeDBInstances --InstanceIds '["{{user.instance_id}}"]'
```

Present key fields: InstanceId, InstanceName, Status, MongoVersion, Memory, Volume, Zone, Vip, Vport, CreateTime, DeadLine.

Instance status mapping: 0=creating, 1=in progress, 2=running, 3=isolated, -2=deleted.

**Modify (scale up/down):**
```bash
tccli mongodb ModifyDBInstanceSpec \
  --InstanceId "{{user.instance_id}}" \
  --Memory 8 \
  --Volume 20 \
  --NodeNum 3 \
  --OpType "UPGRADE"
```

Pre-flight: Check current spec, ensure new memory/volume > current, validate `ModifyModeError` (disk and memory must scale together).

**Delete (two-step: Isolate → Offline):**
Step 1: Isolate (for postpaid) or Terminate (for prepaid):
```bash
tccli mongodb IsolateDBInstance --InstanceId "{{user.instance_id}}"
```

Safety gate: MUST confirm instance ID and name. Warn prepaid instances use `TerminateDBInstances` instead.

Step 2 (after isolation, within recovery window):
```bash
tccli mongodb OfflineIsolatedDBInstance --InstanceId "{{user.instance_id}}"
```

- [ ] **Step 5: Write execution flows - Backup, Restore, Accounts, Parameters**

**Backup (manual):**
```bash
tccli mongodb CreateBackupDBInstance --InstanceId "{{user.instance_id}}"
```
Poll `DescribeDBBackups` until status=2 (success).

**Auto-backup rules:**
```bash
tccli mongodb SetBackupRules \
  --InstanceId "{{user.instance_id}}" \
  --BackupType 0 \
  --BackupTime "01:00-02:00" \
  --BackupRetentionPeriod 7
```

**Restore:**
```bash
tccli mongodb RestoreDBInstance \
  --InstanceId "{{user.instance_id}}" \
  --BackupId 12345
```

**Accounts:**
```bash
# Create account
tccli mongodb CreateAccountUser \
  --InstanceId "{{user.instance_id}}" \
  --UserName "{{user.account_name}}" \
  --Password "{{user.password}}" \
  --AuthRole '[{"Mask":1,"NameSpace":"admin"}]'

# List accounts
tccli mongodb DescribeAccountUsers --InstanceId "{{user.instance_id}}"

# Set privilege
tccli mongodb SetAccountUserPrivilege \
  --InstanceId "{{user.instance_id}}" \
  --UserName "{{user.account_name}}" \
  --AuthRole '[{"Mask":3,"NameSpace":"testdb"}]'

# Reset password
tccli mongodb ResetDBInstancePassword \
  --InstanceId "{{user.instance_id}}" \
  --UserName "{{user.account_name}}" \
  --Password "{{user.new_password}}"
```

**Parameters:**
```bash
# List parameters
tccli mongodb DescribeInstanceParams --InstanceId "{{user.instance_id}}"

# Modify parameters  
tccli mongodb ModifyInstanceParams \
  --InstanceId "{{user.instance_id}}" \
  --InstanceParams '[{"Key":"net.messageMaxBytes","Value":"8388608"}]'
```

- [ ] **Step 6: Write execution flows - Monitoring, SSL, Audit, Security Groups**

**Slow Logs:**
```bash
tccli mongodb DescribeSlowLogs \
  --InstanceId "{{user.instance_id}}" \
  --StartTime "2026-05-28 00:00:00" \
  --EndTime "2026-05-29 00:00:00" \
  --SlowMS 100

tccli mongodb DescribeSlowLogPatterns \
  --InstanceId "{{user.instance_id}}" \
  --StartTime "2026-05-28 00:00:00" \
  --EndTime "2026-05-29 00:00:00" \
  --SlowMS 100
```

**SSL:**
```bash
# Check SSL status
tccli mongodb DescribeInstanceSSL --InstanceId "{{user.instance_id}}"

# Enable/disable SSL
tccli mongodb InstanceEnableSSL \
  --InstanceId "{{user.instance_id}}" \
  --SslSwitch "on"  # or "off"
```

**Audit:**
```bash
# Check audit config
tccli mongodb DescribeAuditConfig --InstanceId "{{user.instance_id}}"

# Open audit service
tccli mongodb OpenAuditService \
  --InstanceId "{{user.instance_id}}" \
  --LogExpireDay 30

# Query audit logs
tccli mongodb DescribeAuditLogs \
  --InstanceId "{{user.instance_id}}" \
  --StartTime "2026-05-28 00:00:00" \
  --EndTime "2026-05-29 00:00:00"
```

**Security Groups:**
```bash
# Describe security group
tccli mongodb DescribeSecurityGroup --InstanceId "{{user.instance_id}}"

# Modify security group
tccli mongodb ModifyDBInstanceSecurityGroup \
  --InstanceId "{{user.instance_id}}" \
  --SecurityGroupIds '["sg-xxxx"]'
```

- [ ] **Step 7: Write Error Code Reference and Safety Gates**

Error code table with MongoDB-specific codes (select ≥ 10 from the 96 business codes):

| Code | Meaning | Retry? | Agent Action |
|------|---------|--------|--------------|
| `InvalidParameterValue.IllegalInstanceStatus` | 实例状态不允许操作 | No | Check instance status via DescribeDBInstances |
| `InvalidParameterValue.NotFoundInstance` | 实例不存在 | No | Verify instance ID; suggest DescribeDBInstances |
| `InvalidParameterValue.ModifyModeError` | 内存和磁盘必须同时升配或降配 | No | Adjust both Memory and Volume parameters |
| `InvalidParameterValue.PasswordRuleFailed` | 密码不符合规范 | No | Use 8-32 chars with letters, digits, special chars |
| `InvalidParameterValue.SpecNotOnSale` | 购买规格错误 | No | Use DescribeSpecInfo to list available specs |
| `InvalidParameterValue.ZoneClosed` | 可用区已关闭售卖 | No | Choose a different availability zone |
| `InvalidParameterValue.PostPaidInstanceBeyondLimit` | 后付费实例超限 | No | HALT; delete unused instances or switch to prepaid |
| `FailedOperation.DeletionProtectionEnabled` | 实例开启了销毁保护 | No | Disable deletion protection first via SetDBInstanceDeletionProtection |
| `FailedOperation.OperationNotAllowedInInstanceLocking` | 实例锁定中 | Yes (3x, 30s) | Wait for lock to release; retry |
| `AuthFailure` | CAM签名/鉴权错误 | No | HALT; check credentials and permissions |
| `LimitExceeded.TooManyRequests` | 请求太过频繁 | Yes (3x) | Exponential backoff |
| `InternalError.TradeError` | 交易系统错误 | Yes (3x, 5s) | Retry; escalate if persistent |

- [ ] **Step 8: Run self-check on SKILL.md**

Verify:
- [ ] Frontmatter complete (name, description, license, compatibility, metadata)
- [ ] SHOULD Use conditions present
- [ ] SHOULD NOT Use conditions present
- [ ] Five Core Standards section present
- [ ] Well-Architected Framework section present
- [ ] Variables section with `{{env.*}}`/`{{user.*}}`/`{{output.*}}`
- [ ] Each flow has Pre-flight → Execute → Validate → Recover
- [ ] Error codes ≥ 10 product-specific
- [ ] Safety gates for destructive operations
- [ ] Token Efficiency rules applied (TE-1 to TE-7)

---

### Task 3: Create references/core-concepts.md

**Files:**
- Create: `qcloud-mongodb-ops/references/core-concepts.md`

- [ ] **Write core-concepts.md**

Cover:
1. Architecture — MongoDB instance types (replica set, sharded cluster), components (mongod, mongos, config server)
2. Instance states lifecycle (creating → running → isolating → isolated → offline/deleted)
3. Node roles (PRIMARY, SECONDARY, READONLY, ARBITER, HIDDEN)
4. Storage engines (WiredTiger)
5. Supported MongoDB versions (MONGO_36_WT, MONGO_40_WT, MONGO_42_WT, MONGO_50_WT, MONGO_60_WT, MONGO_70_WT, MONGO_80_WT)
6. Machine types (HIO10G — High IO 10 Gigabit, HCD — Cloud Disk)
7. Cluster types (0: replica set, 1: sharded cluster)
8. Payment modes (prepaid/postpaid)
9. Network types (0: classic network, 1: VPC)
10. Resource relationships (instance → security groups, instance → backup, instance → accounts)
11. Regions and availability zones (general info, query via DescribeSpecInfo)
12. Limits and quotas (spec limits from DescribeSpecInfo)

---

### Task 4: Create references/api-sdk-usage.md

**Files:**
- Create: `qcloud-mongodb-ops/references/api-sdk-usage.md`

- [ ] **Write api-sdk-usage.md**

Cover:
1. SDK module: `tencentcloud-sdk-python-mongodb`, import path: `from tencentcloud.mongodb.v20190725 import mongodb_client, models`
2. Client initialization
3. Operation map with all 79 API actions grouped by category
4. Required fields table for each critical operation
5. Pagination pattern (Offset/Limit)
6. Async operation pattern (DescribeAsyncRequestInfo)
7. Python SDK code examples for each operation category (using `#` comments, no docstrings per TE-2)
8. JSON response paths reference

Important: Per TE-2, use `#` line comments instead of function docstrings.

---

### Task 5: Create references/cli-usage.md

**Files:**
- Create: `qcloud-mongodb-ops/references/cli-usage.md`

- [ ] **Write cli-usage.md**

Cover:
1. tccli mongodb command map for all 79 actions
2. Coverage notes: CLI supports all major operations
3. Invocation patterns: `tccli mongodb <Action> [options]`
4. JSON output handling with `jq` examples
5. Credential configuration
6. Version selection: always use `--version 2019-07-25`

---

### Task 6: Create references/troubleshooting.md

**Files:**
- Create: `qcloud-mongodb-ops/references/troubleshooting.md`

- [ ] **Write troubleshooting.md**

Cover:
1. Full error code taxonomy (select 30+ important codes from the 96 MongoDB business codes + public codes)
2. Ordered diagnostic workflows:
   - Instance creation failure
   - Connection timeout/unreachable
   - Slow query performance
   - Backup failure
   - Account authentication failure
   - Spec modification failure
   - Instance deletion protection
3. Common patterns with diagnostic steps
4. Multi-round diagnosis guidance

---

### Task 7: Create references/monitoring.md

**Files:**
- Create: `qcloud-mongodb-ops/references/monitoring.md`

- [ ] **Write monitoring.md**

Cover:
1. All monitoring metrics organized by dimension (instance, replica set, mongod node, mongos node)
2. Namespace: `QCE/CMONGO`
3. Dimension: `target` (instance ID, replica set ID, node ID)
4. Key alarm metrics table:
   - ClusterDiskUsage (>80% warning, >90% critical)
   - Connper (>80% warning)
   - MonogdMaxCpuUsage (>80% warning)
   - SlaveDelay (>60s warning)
   - OplogReservedTime (<2h critical)
5. Recommended alarm policies
6. Common anomaly patterns and their metric signatures

---

### Task 8: Create references/integration.md

**Files:**
- Create: `qcloud-mongodb-ops/references/integration.md`

- [ ] **Write integration.md**

Cover:
1. Python SDK setup: `pip install tencentcloud-sdk-python-mongodb`
2. Environment variables
3. Cross-skill delegation matrix
4. CI/CD integration patterns
5. Script execution patterns

---

### Task 9: Create references/well-architected-assessment.md

**Files:**
- Create: `qcloud-mongodb-ops/references/well-architected-assessment.md`

- [ ] **Write well-architected-assessment.md**

Cover four pillars:
1. **Reliability** — Multi-AZ deployment, backup strategies (auto/manual), restore procedures, DR (disaster recovery instances), RTO/RPO guidelines, failure scenarios
2. **Security** — CAM minimum permissions table, SSL/TLS configuration, transparent data encryption, audit logging, security groups, network isolation (VPC), password policies, password rotation
3. **Cost** — Billing model comparison (prepaid vs postpaid), instance right-sizing, reserved instances, cost optimization via monitoring (idle instances), backup cost management
4. **Efficiency** — Batch operations, parameter templates, CI/CD automation, scaling patterns, connection pooling recommendations

---

### Task 10: Create assets/example-config.yaml

**Files:**
- Create: `qcloud-mongodb-ops/assets/example-config.yaml`

- [ ] **Write example-config.yaml**

Include examples for:
1. Basic replica set instance (3 nodes, 4GB RAM, 10GB disk)
2. Sharded cluster instance (2 shards, 3 nodes each)
3. Production deployment with monitoring alarms
4. Multi-AZ replica set
5. Parameter configs (e.g., slowMS, maxConns, messageMaxBytes)

Use YAML anchors per TE-5:

```yaml
x-default-thresholds: &default-thresholds
  disk_usage_warning: 80
  disk_usage_critical: 90
  cpu_usage_warning: 80
  conn_usage_warning: 80

mongodb-instance:
  basic-replica-set:
    instance_name: "my-mongo-replica"
    cluster_type: 0  # 0=replica set, 1=sharded
    node_num: 3
    memory_gb: 4
    storage_gb: 10
    mongo_version: "MONGO_60_WT"
    machine_type: "HCD"
    zone: "ap-guangzhou-3"
    thresholds:
      <<: *default-thresholds
      slave_delay_warning: 30
```

---

### Task 11: Create assets/eval_queries.json

**Files:**
- Create: `qcloud-mongodb-ops/assets/eval_queries.json`

- [ ] **Write eval_queries.json**

Create ~20 eval queries (10 should-trigger, 10 should-not-trigger):

```json
[
  { "query": "帮我创建一个MongoDB实例，4核8G，副本集", "should_trigger": true, "reason": "Explicit MongoDB creation request in Chinese" },
  { "query": "查看我的MongoDB实例列表", "should_trigger": true, "reason": "MongoDB list query" },
  { "query": "我的MongoDB连接不上，帮我看看", "should_trigger": true, "reason": "Troubleshooting MongoDB connection" },
  { "query": "给MongoDB做个备份", "should_trigger": true, "reason": "MongoDB backup operation" },
  { "query": "MongoDB慢查询太多，查一下慢日志", "should_trigger": true, "reason": "MongoDB slow log diagnosis" },
  { "query": "MongoDB实例扩容，升配到8核16G", "should_trigger": true, "reason": "MongoDB spec modification" },
  { "query": "检查我MongoDB的SSL状态", "should_trigger": true, "reason": "MongoDB SSL management" },
  { "query": "tccli mongodb DescribeDBInstances", "should_trigger": true, "reason": "CLI command suggests MongoDB skill" },
  { "query": "List my TencentDB MongoDB instances", "should_trigger": true, "reason": "English MongoDB query" },
  { "query": "Mongo 实例状态是隔离的，怎么恢复？", "should_trigger": true, "reason": "MongoDB instance recovery question" },
  { "query": "查看我的CVM实例列表", "should_trigger": false, "reason": "CVM operation, different skill" },
  { "query": "创建一台云服务器", "should_trigger": false, "reason": "CVM creation, not MongoDB" },
  { "query": "检查腾讯云账户余额", "should_trigger": false, "reason": "Billing operation, different skill" },
  { "query": "给Redis实例做个备份", "should_trigger": false, "reason": "Redis operation, different skill" },
  { "query": "配置CLB负载均衡", "should_trigger": false, "reason": "CLB operation, different skill" },
  { "query": "修改VPC路由表", "should_trigger": false, "reason": "VPC operation, different skill" },
  { "query": "我的MySQL数据库连不上", "should_trigger": false, "reason": "CDB/MySQL operation, different skill" },
  { "query": "帮我写一个MongoDB的查询语句", "should_trigger": false, "reason": "MongoDB query writing, not cloud operations" },
  { "query": "Kubernetes集群如何部署MongoDB", "should_trigger": false, "reason": "Self-hosted MongoDB, not Tencent Cloud MongoDB" },
  { "query": "给COS存储桶设置权限", "should_trigger": false, "reason": "COS operation, different skill" }
]
```

---

### Task 12: Final verification and charter compliance check

**Files:** (read all created files)

- [ ] **Run C1-C6 charter compliance checks**

```bash
# C1: Frontmatter
head -3 qcloud-mongodb-ops/SKILL.md | grep -q "^---" && echo "C1 PASS: Frontmatter starts with ---"
grep -q "name: qcloud-mongodb-ops" qcloud-mongodb-ops/SKILL.md && echo "C1: name OK"
grep -q "description:" qcloud-mongodb-ops/SKILL.md && echo "C1: description OK"
grep -q "license: MIT" qcloud-mongodb-ops/SKILL.md && echo "C1: license OK"
grep -q "compatibility:" qcloud-mongodb-ops/SKILL.md && echo "C1: compatibility OK"

# C2: SHOULD/SHOULD NOT
grep -c "SHOULD Use" qcloud-mongodb-ops/SKILL.md
grep -c "SHOULD NOT" qcloud-mongodb-ops/SKILL.md

# C3: Five Core Standards
grep -c "Five Core Standards" qcloud-mongodb-ops/SKILL.md

# C4: Well-Architected
grep -c "Well-Architected Framework" qcloud-mongodb-ops/SKILL.md

# C5: Variables
grep -c "^## Variables" qcloud-mongodb-ops/SKILL.md

# C6: Token Efficiency
grep -c "TE-" qcloud-mongodb-ops/SKILL.md
```

Expected: All C1-C6 checks pass.

- [ ] **Verify all files exist**

```bash
ls -la qcloud-mongodb-ops/SKILL.md
ls -la qcloud-mongodb-ops/references/core-concepts.md
ls -la qcloud-mongodb-ops/references/api-sdk-usage.md
ls -la qcloud-mongodb-ops/references/cli-usage.md
ls -la qcloud-mongodb-ops/references/troubleshooting.md
ls -la qcloud-mongodb-ops/references/monitoring.md
ls -la qcloud-mongodb-ops/references/integration.md
ls -la qcloud-mongodb-ops/references/well-architected-assessment.md
ls -la qcloud-mongodb-ops/assets/example-config.yaml
ls -la qcloud-mongodb-ops/assets/eval_queries.json
```

Expected: All 11 files exist and have content.

---

## Directory Layout Summary

```
qcloud-mongodb-ops/
├── SKILL.md                           # Main skill runbook (~500+ lines)
├── references/
│   ├── core-concepts.md               # Architecture, states, versions
│   ├── api-sdk-usage.md               # Python SDK + API operation map
│   ├── cli-usage.md                   # tccli mongodb command reference
│   ├── troubleshooting.md             # Error codes + diagnostic workflows
│   ├── monitoring.md                  # Metrics, alarms, anomaly patterns
│   ├── integration.md                 # SDK setup, env vars, delegation
│   └── well-architected-assessment.md # 4-pillar assessment
└── assets/
    ├── example-config.yaml            # YAML config examples
    └── eval_queries.json              # 20 trigger evaluation queries
```
