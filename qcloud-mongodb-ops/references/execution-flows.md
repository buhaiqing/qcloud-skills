# MongoDB Execution Flows

> 从 `SKILL.md` 提取。所有操作的 Pre-flight → Execute → Validate → Recover 流程。

## Create Instance

### Pre-flight

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI | `tccli version` | Exit code 0 | Install CLI |
| Credentials | Check env vars | Non-empty | HALT; configure env |
| Region | `tccli mongodb DescribeSpecInfo` | Valid region returned | Suggest valid region |
| Spec availability | Query DescribeSpecInfo for zone | Requested spec on sale | Show available specs |
| Quota/Price | `InquirePriceCreateDBInstances` | Price returned | HALT; check limits |

### CLI (Monthly)

```bash
tccli mongodb CreateDBInstance \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Zone "{{user.zone}}" \
  --NodeNum 3 \
  --Memory 4 \
  --Volume 10 \
  --MongoVersion "MONGO_60_WT" \
  --MachineCode "HCD" \
  --GoodsNum 1 \
  --ClusterType 0 \
  --Period 1
```

### CLI (Hourly)

```bash
tccli mongodb CreateDBInstanceHour \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Zone "{{user.zone}}" \
  --NodeNum 3 \
  --Memory 4 \
  --Volume 10 \
  --MongoVersion "MONGO_60_WT" \
  --MachineCode "HCD" \
  --GoodsNum 1 \
  --ClusterType 0
```

**Parameters:** `NodeNum`=3 (replica set), `Memory`/`Volume` in GB, `MongoVersion`=MONGO_42/50/60/70/80_WT, `MachineCode`=HIO10G/HCD, `ClusterType`=0(replica)/1(sharded), `Period`=months (prepaid only)

### Python SDK

```python
#!/usr/bin/env python3
import os, json
from tencentcloud.common import credential
from tencentcloud.mongodb.v20190725 import mongodb_client, models

cred = credential.Credential(os.environ["TENCENTCLOUD_SECRET_ID"], os.environ["TENCENTCLOUD_SECRET_KEY"])
client = mongodb_client.MongodbClient(cred, os.environ["TENCENTCLOUD_REGION"])

req = models.CreateDBInstanceHourRequest()
req.Zone = "ap-guangzhou-3"
req.NodeNum = 3
req.Memory = 4
req.Volume = 10
req.MongoVersion = "MONGO_60_WT"
req.MachineCode = "HCD"
req.GoodsNum = 1
req.ClusterType = 0

resp = client.CreateDBInstanceHour(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

### Post-execution

1. Parse `{{output.deal_id}}` from response
2. Poll `DescribeAsyncRequestInfo --DealId` until status=success
3. Call `DescribeDBInstances` to get `{{output.instance_id}}`, verify status=2 (running)

### Failure Recovery

| Error Code | Recovery |
|------------|----------|
| InvalidParameterValue.SpecNotOnSale | Use DescribeSpecInfo to list available specs |
| InvalidParameterValue.ZoneClosed | Choose different AZ |
| InvalidParameterValue.PostPaidInstanceBeyondLimit | Delete unused or switch to prepaid |
| InvalidParameterValue.PasswordRuleFailed | 8-32 chars with letters, digits, special chars |
| InternalError.TradeError | Retry 3x with 5s backoff |
| LimitExceeded.TooManyRequests | Retry 3x with exponential backoff |
| AuthFailure | HALT; check credentials |

---

## Describe Instance

```bash
tccli mongodb DescribeDBInstances --InstanceIds '["{{user.instance_id}}"]'
```

**Key fields:** InstanceId, Status (0=creating, 2=running, 3=isolated, -2=deleted), MongoVersion, Memory, Volume, Vip, Vport

---

## Modify Instance Spec

```bash
tccli mongodb ModifyDBInstanceSpec \
  --InstanceId "{{user.instance_id}}" \
  --Memory 8 --Volume 20
```

> Memory and Volume must both increase or both decrease.

| Error Code | Recovery |
|------------|----------|
| InvalidParameterValue.ModifyModeError | Memory and disk must scale together |
| InvalidParameterValue.SetDiskLessThanUsed | Set disk ≥ 1.2× current used disk |

---

## Delete Instance (High Risk)

1. **Confirm** explicitly with user
2. **Backup** first: `tccli mongodb CreateBackupDBInstance`
3. **Isolate** (postpaid): `tccli mongodb IsolateDBInstance`
   or **Terminate** (prepaid): `tccli mongodb TerminateDBInstances`
4. **Offline**: `tccli mongodb OfflineIsolatedDBInstance`

---

## Backup Instance

```bash
tccli mongodb CreateBackupDBInstance --InstanceId "{{user.instance_id}}"
tccli mongodb DescribeDBBackups --InstanceId "{{user.instance_id}}" --Limit 5
```

**Auto backup:** `tccli mongodb SetBackupRules --InstanceId ... --BackupType 0 --BackupTime "01:00-02:00" --BackupRetentionPeriod 7`

---

## Restore Instance

```bash
tccli mongodb DescribeDBBackups --InstanceId "{{user.instance_id}}"
tccli mongodb RestoreDBInstance --InstanceId "{{user.instance_id}}" --BackupId 12345
```

> Warn: restore overwrites current data.

---

## Account Management

```bash
# Create
tccli mongodb CreateAccountUser --InstanceId "{{user.instance_id}}" \
  --UserName "{{user.account_name}}" --Password "{{user.password}}" \
  --AuthRole '[{"Mask":1,"NameSpace":"admin"}]'

# List
tccli mongodb DescribeAccountUsers --InstanceId "{{user.instance_id}}"

# Set privilege (Mask: 0=none, 1=read-only, 3=read-write)
tccli mongodb SetAccountUserPrivilege --InstanceId "{{user.instance_id}}" \
  --UserName "{{user.account_name}}" --AuthRole '[{"Mask":3,"NameSpace":"testdb"}]'

# Reset password
tccli mongodb ResetDBInstancePassword --InstanceId "{{user.instance_id}}" \
  --UserName "{{user.account_name}}" --Password "{{user.new_password}}"
```

---

## Parameter Management

```bash
tccli mongodb DescribeInstanceParams --InstanceId "{{user.instance_id}}"
tccli mongodb ModifyInstanceParams --InstanceId "{{user.instance_id}}" \
  --InstanceParams '[{"Key":"net.messageMaxBytes","Value":"16777216"}]'
```

**Common params:** `net.messageMaxBytes`, `operationProfiling.slowOpThresholdMs`, `net.maxIncomingConnections`

---

## Slow Log Diagnosis

```bash
tccli mongodb DescribeSlowLogs --InstanceId "{{user.instance_id}}" \
  --StartTime "2026-05-22 00:00:00" --EndTime "2026-05-29 00:00:00" --SlowMS 100

tccli mongodb DescribeSlowLogPatterns --InstanceId "{{user.instance_id}}" \
  --StartTime "2026-05-22 00:00:00" --EndTime "2026-05-29 00:00:00" --SlowMS 100

tccli mongodb DescribeDetailedSlowLogs --InstanceId "{{user.instance_id}}" \
  --StartTime "2026-05-22 00:00:00" --EndTime "2026-05-29 00:00:00" --SlowMS 100
```

---

## SSL/TLS Management

```bash
tccli mongodb DescribeInstanceSSL --InstanceId "{{user.instance_id}}"
tccli mongodb InstanceEnableSSL --InstanceId "{{user.instance_id}}" --SslSwitch "on"
```

---

## Audit Service Management

```bash
tccli mongodb DescribeAuditConfig --InstanceId "{{user.instance_id}}"
tccli mongodb OpenAuditService --InstanceId "{{user.instance_id}}" --LogExpireDay 30
tccli mongodb ModifyAuditService --InstanceId "{{user.instance_id}}" --LogExpireDay 60
tccli mongodb DescribeAuditLogs --InstanceId "{{user.instance_id}}" \
  --StartTime "2026-05-22 00:00:00" --EndTime "2026-05-29 00:00:00"
tccli mongodb CloseAuditService --InstanceId "{{user.instance_id}}"
```

---

## Connection Diagnosis

```bash
tccli mongodb DescribeDBInstanceURL --InstanceId "{{user.instance_id}}"
tccli mongodb DescribeClientConnections --InstanceId "{{user.instance_id}}"
tccli mongodb DescribeDBInstanceNamespace --InstanceId "{{user.instance_id}}"
```

---

## Current Operations & Kill Ops

```bash
tccli mongodb DescribeCurrentOp --InstanceId "{{user.instance_id}}"
tccli mongodb KillOps --InstanceId "{{user.instance_id}}" \
  --Operations '[{"OpId":12345,"Ns":"testdb.$cmd","Op":"query"}]'
```

> MUST show operation list and confirm opId(s) with user before killing.

---

## FlashBack (High Risk)

```bash
tccli mongodb FlashBackDBInstance --InstanceId "{{user.instance_id}}" \
  --TargetFlashbackTime "{{user.flashback_time}}" \
  --TargetDatabases '[{"DbName":"testdb","CollectionNames":["orders"]}]'
```

> Warn: overwrites data. Suggest pre-flashback backup.

---

## Version Upgrade

```bash
tccli mongodb UpgradeDbInstanceVersion --InstanceId "{{user.instance_id}}" \
  --MongoVersion "{{user.target_mongo_version}}" --InMaintenance 1
```

> Warn: triggers restart (30-120s downtime). Test in non-prod first.

---

## Transparent Data Encryption (TDE)

```bash
tccli mongodb DescribeTransparentDataEncryptionStatus --InstanceId "{{user.instance_id}}"
tccli mongodb EnableTransparentDataEncryption --InstanceId "{{user.instance_id}}" --KeyId "kms-xxxxx"
```

> TDE instances only support logical backup. Irreversible.

---

## Security Group Management

```bash
tccli mongodb DescribeSecurityGroup --InstanceId "{{user.instance_id}}"
tccli mongodb ModifyDBInstanceSecurityGroup --InstanceId "{{user.instance_id}}" \
  --SecurityGroupIds '["sg-xxxxx"]'
```
