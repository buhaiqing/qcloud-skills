# CDB CLI Usage Guide

Detailed `tccli cdb` command reference for TencentDB for MySQL (CDB) operations.

---

## 1. CLI Overview

### Installation

```bash
pip install tccli
```

### Verify

```bash
tccli version
tccli cdb help
```

### Credential Setup

```bash
export TENCENTCLOUD_SECRET_ID="AKIDxxxx"
export TENCENTCLOUD_SECRET_KEY="xxxxx"
export TENCENTCLOUD_REGION="ap-guangzhou"
```

---

## 2. Common Patterns

### JSON Parameter Convention

`tccli cdb` uses JSON string parameters for complex arguments:

```bash
# InstanceIds as JSON array
tccli cdb DescribeDBInstances --InstanceIds '["cdb-xxxxxx"]'

# Status filter
tccli cdb DescribeDBInstances --Status "[1]"

# ParamList format
tccli cdb ModifyInstanceParam \
  --InstanceIds '["cdb-xxxxxx"]' \
  --ParamList '[{"Name":"max_connections","CurrentValue":"1000"}]'

# Accounts format
tccli cdb CreateAccounts \
  --InstanceId "cdb-xxxxxx" \
  --Accounts '[{"User":"dbuser","Host":"%"}]'

# BackupDBTableList format
tccli cdb CreateBackup \
  --InstanceId "cdb-xxxxxx" \
  --BackupMethod "logical" \
  --BackupDBTableList '[{"Db":"mydb","Table":"users"}]'
```

---

## 3. Instance Operations

### 3.1 DescribeDBInstances

```bash
# List all instances
tccli cdb DescribeDBInstances --Region ap-guangzhou --Offset 0 --Limit 20

# Filter by instance ID
tccli cdb DescribeDBInstances --InstanceIds '["cdb-xxxxxx"]'

# Filter by status (1=running)
tccli cdb DescribeDBInstances --Status "[1]"

# Filter by project
tccli cdb DescribeDBInstances --ProjectId 0

# Response
# {
#   "Response": {
#     "TotalCount": 3,
#     "Items": [
#       {
#         "InstanceId": "cdb-xxxxxx",
#         "InstanceName": "production-db",
#         "Status": 1,
#         "Memory": 4000,
#         "Volume": 200,
#         "EngineVersion": "8.0",
#         "Vip": "10.0.0.10",
#         "Vport": 3306,
#         "Zone": "ap-guangzhou-3",
#         "InstanceType": 1,
#         "AutoRenew": 1,
#         "CreateTime": "2026-05-01T10:00:00+08:00"
#       }
#     ],
#     "RequestId": "..."
#   }
# }
```

### 3.2 CreateDBInstance (Prepaid)

```bash
# Minimal create
tccli cdb CreateDBInstance \
  --Region ap-guangzhou \
  --Memory 1000 \
  --Volume 50 \
  --Period 1 \
  --GoodsNum 1 \
  --Zone ap-guangzhou-3 \
  --EngineVersion "8.0" \
  --InstanceRole "master"

# With VPC and custom port
tccli cdb CreateDBInstance \
  --Region ap-guangzhou \
  --Memory 4000 \
  --Volume 200 \
  --Period 12 \
  --GoodsNum 1 \
  --Zone ap-guangzhou-3 \
  --UniqVpcId "vpc-xxxxxx" \
  --UniqSubnetId "subnet-xxxxxx" \
  --Port 3306 \
  --EngineVersion "8.0" \
  --InstanceRole "master" \
  --ProjectId 0

# Check price first
tccli cdb DescribeDBPrice \
  --Memory 4000 \
  --Volume 200 \
  --Period 1 \
  --InstanceRole "master" \
  --Zone ap-guangzhou-3

# Response
# { "Response": { "DealIds": ["20260521xxxx"], "InstanceIds": ["cdb-xxxxxx"], "RequestId": "..." } }
```

### 3.3 CreateDBInstanceHour (Postpaid/Hourly)

```bash
tccli cdb CreateDBInstanceHour \
  --Region ap-guangzhou \
  --Memory 4000 \
  --Volume 200 \
  --GoodsNum 1 \
  --Zone ap-guangzhou-3 \
  --UniqVpcId "vpc-xxxxxx" \
  --UniqSubnetId "subnet-xxxxxx" \
  --EngineVersion "8.0" \
  --InstanceRole "master"
```

### 3.4 UpgradeDBInstance

```bash
tccli cdb UpgradeDBInstance \
  --InstanceId "cdb-xxxxxx" \
  --Memory 8000 \
  --Volume 500 \
  --WaitSwitch 1    # 0=immediate, 1=during maintenance window

# Response
# { "Response": { "DealIds": ["20260521xxxx"], "RequestId": "..." } }
```

### 3.5 RestartDBInstances

```bash
tccli cdb RestartDBInstances --InstanceIds '["cdb-xxxxxx"]'
# Response: { "Response": { "RequestId": "..." } }
```

### 3.6 IsolateDBInstance

```bash
tccli cdb IsolateDBInstance --InstanceId "cdb-xxxxxx"
# Response: { "Response": { "RequestId": "..." } }
```

### 3.7 ReleaseIsolatedDBInstances (FINAL DELETE)

```bash
tccli cdb ReleaseIsolatedDBInstances --InstanceIds '["cdb-xxxxxx"]'
# ⚠️ Warning: This permanently deletes the instance and all data
```

### 3.8 RenewDBInstance

```bash
# Renew for 6 months
tccli cdb RenewDBInstance \
  --InstanceId "cdb-xxxxxx" \
  --TimeSpan 6 \
  --ModifyPayType 0   # 0=keep same billing mode

# Response
# { "Response": { "DealId": "20260521xxxx", "RequestId": "..." } }
```

### 3.9 ModifyDBInstance

```bash
# Rename
tccli cdb ModifyDBInstanceName \
  --InstanceId "cdb-xxxxxx" \
  --InstanceName "new-production-db"

# Change project
tccli cdb ModifyDBInstanceProject \
  --InstanceIds '["cdb-xxxxxx"]' \
  --ProjectId 1
```

---

## 4. Backup Operations

### 4.1 CreateBackup

```bash
# Physical backup (default, recommended)
tccli cdb CreateBackup \
  --InstanceId "cdb-xxxxxx" \
  --BackupMethod "physical"

# Logical backup (mysqldump)
tccli cdb CreateBackup \
  --InstanceId "cdb-xxxxxx" \
  --BackupMethod "logical"

# Logical backup of specific tables
tccli cdb CreateBackup \
  --InstanceId "cdb-xxxxxx" \
  --BackupMethod "logical" \
  --BackupDBTableList '[{"Db":"mydb","Table":"users"}]'

# Response
# { "Response": { "BackupId": 12345, "RequestId": "..." } }
```

### 4.2 DescribeBackups

```bash
tccli cdb DescribeBackups \
  --InstanceId "cdb-xxxxxx" \
  --Offset 0 \
  --Limit 10

# Response
# {
#   "Response": {
#     "Items": [
#       {
#         "BackupId": 12345,
#         "InstanceId": "cdb-xxxxxx",
#         "BackupType": "manual",
#         "BackupMethod": "physical",
#         "BackupSize": 1024,
#         "Date": "2026-05-21 10:00:00",
#         "Status": "SUCCESS",
#         "FinishTime": "2026-05-21 10:30:00"
#       }
#     ],
#     "TotalCount": 5,
#     "RequestId": "..."
#   }
# }
```

### 4.3 DeleteBackups

```bash
tccli cdb DeleteBackups \
  --InstanceId "cdb-xxxxxx" \
  --BackupIds "[12345]"
```

### 4.4 ModifyBackupConfig

```bash
tccli cdb ModifyBackupConfig \
  --InstanceId "cdb-xxxxxx" \
  --BackupTimeStart "02:00" \
  --BackupTimeEnd "06:00" \
  --BackupModel "physical" \
  --BackupPeriods '["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]' \
  --BackupRetentionDays 30
```

### 4.5 CreateCloneInstance (Restore from Backup)

```bash
# Clone from specific backup
tccli cdb CreateCloneInstance \
  --InstanceId "cdb-xxxxxx" \
  --SpecifyBackupId 12345 \
  --SpecifyBackupType "BackupId"

# Clone with different specs
tccli cdb CreateCloneInstance \
  --InstanceId "cdb-xxxxxx" \
  --SpecifyBackupId 12345 \
  --SpecifyBackupType "BackupId" \
  --NewInstanceMemory 8000 \
  --NewInstanceVolume 500

# Clone to point-in-time
tccli cdb CreateCloneInstance \
  --InstanceId "cdb-xxxxxx" \
  --SpecifyBackupType "Timepoint" \
  --SpecifyBackupTime "2026-05-21 12:00:00"
```

---

## 5. Account Operations

### 5.1 CreateAccounts

```bash
tccli cdb CreateAccounts \
  --InstanceId "cdb-xxxxxx" \
  --Accounts '[{"User":"app_user","Host":"%"}]' \
  --Password "SecurePassword123!" \
  --Description "Application account"

# Multiple accounts at once
tccli cdb CreateAccounts \
  --InstanceId "cdb-xxxxxx" \
  --Accounts '[{"User":"readonly","Host":"10.0.%"},{"User":"admin","Host":"localhost"}]' \
  --Password "AnotherPass456!"
```

### 5.2 DescribeAccounts

```bash
tccli cdb DescribeAccounts --InstanceId "cdb-xxxxxx" --Limit 20
```

### 5.3 ModifyAccountPassword

```bash
tccli cdb ModifyAccountPassword \
  --InstanceId "cdb-xxxxxx" \
  --Accounts '[{"User":"app_user","Host":"%"}]' \
  --NewPassword "NewSecurePass789!"
```

### 5.4 ModifyAccountPrivileges

```bash
# Grant global privileges
tccli cdb ModifyAccountPrivileges \
  --InstanceId "cdb-xxxxxx" \
  --Accounts '[{"User":"app_user","Host":"%"}]' \
  --GlobalPrivileges '["SELECT","INSERT","UPDATE","DELETE","CREATE"]'

# Grant database-specific privileges
tccli cdb ModifyAccountPrivileges \
  --InstanceId "cdb-xxxxxx" \
  --Accounts '[{"User":"app_user","Host":"%"}]' \
  --DatabasePrivileges '[{"Database":"mydb","Privileges":["SELECT","INSERT","UPDATE","DELETE"]}]'
```

### 5.5 DeleteAccounts

```bash
tccli cdb DeleteAccounts \
  --InstanceId "cdb-xxxxxx" \
  --Accounts '[{"User":"old_user","Host":"%"}]'
```

---

## 6. Parameter Operations

### 6.1 DescribeInstanceParams

```bash
tccli cdb DescribeInstanceParams --InstanceId "cdb-xxxxxx"
```

### 6.2 ModifyInstanceParam

```bash
# Single parameter
tccli cdb ModifyInstanceParam \
  --InstanceIds '["cdb-xxxxxx"]' \
  --ParamList '[{"Name":"max_connections","CurrentValue":"1000"}]'

# Multiple parameters
tccli cdb ModifyInstanceParam \
  --InstanceIds '["cdb-xxxxxx"]' \
  --ParamList '[{"Name":"max_connections","CurrentValue":"1000"},{"Name":"wait_timeout","CurrentValue":"28800"},{"Name":"innodb_buffer_pool_size","CurrentValue":"2147483648"}]'

# Response
# { "Response": { "AsyncRequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", "RequestId": "..." } }
```

---

## 7. Security Operations

### 7.1 SSL Operations

```bash
# Enable SSL
tccli cdb OpenSSL --InstanceId "cdb-xxxxxx"

# Disable SSL
tccli cdb CloseSSL --InstanceId "cdb-xxxxxx"

# Check SSL status
tccli cdb DescribeSSLStatus --InstanceId "cdb-xxxxxx"
# Response: { "Response": { "SSLStatus": "ON", "RequestId": "..." } }
```

### 7.2 Encryption Operations

```bash
# Enable data-at-rest encryption
tccli cdb OpenDBInstanceEncryption \
  --InstanceId "cdb-xxxxxx" \
  --KeyId "kms-xxxxxx"

# Check encryption status
tccli cdb DescribeDBInstanceEncryption --InstanceId "cdb-xxxxxx"
```

---

## 8. Network Operations

```bash
# Open public (WAN) access
tccli cdb OpenWanService --InstanceId "cdb-xxxxxx"
# ⚠️ Warning: This exposes the database to the internet

# Close public access
tccli cdb CloseWanService --InstanceId "cdb-xxxxxx"

# Modify internal VIP/Vport
tccli cdb ModifyDBInstanceVipVport \
  --InstanceId "cdb-xxxxxx" \
  --Vip "10.0.0.20" \
  --Vport 3306
```

---

## 9. Log and Analysis Operations

### 9.1 DescribeSlowLogData

```bash
tccli cdb DescribeSlowLogData \
  --InstanceId "cdb-xxxxxx" \
  --StartTime "2026-05-20 00:00:00" \
  --EndTime "2026-05-21 00:00:00" \
  --Limit 20
```

### 9.2 DescribeErrorLogData

```bash
tccli cdb DescribeErrorLogData \
  --InstanceId "cdb-xxxxxx" \
  --StartTime "2026-05-20 00:00:00" \
  --EndTime "2026-05-21 00:00:00" \
  --Limit 20
```

### 9.3 DescribeDBPrice

```bash
# Check price for new instance
tccli cdb DescribeDBPrice \
  --Memory 4000 \
  --Volume 200 \
  --Period 1 \
  --InstanceRole "master" \
  --Zone ap-guangzhou-3
```

---

## 10. Version Operations

```bash
# Check upgrade feasibility
tccli cdb DescribeSupportedEngineVersions --InstanceId "cdb-xxxxxx"

# Upgrade to MySQL 8.0
tccli cdb UpgradeDBInstanceEngineVersion \
  --InstanceId "cdb-xxxxxx" \
  --EngineVersion "8.0"
```

---

## 11. Task Operations

```bash
# List recent tasks
tccli cdb DescribeTasks \
  --InstanceId "cdb-xxxxxx" \
  --StartTimeBegin "2026-05-20 00:00:00" \
  --StartTimeEnd "2026-05-21 00:00:00"

# Check async task status
tccli cdb DescribeAsyncRequestInfo \
  --AsyncRequestId "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

---

## 12. CLI Coverage Gap Table

Most CDB operations are supported by `tccli cdb`. The following operations may require SDK fallback:

| Operation | CLI Support | SDK Fallback Needed? |
|-----------|-------------|---------------------|
| DescribeDBInstances | ✅ Full | No |
| CreateDBInstance | ✅ Full | No |
| CreateDBInstanceHour | ✅ Full | No |
| UpgradeDBInstance | ✅ Full | No |
| RestartDBInstances | ✅ Full | No |
| IsolateDBInstance | ✅ Full | No |
| ReleaseIsolatedDBInstances | ✅ Full | No |
| RenewDBInstance | ✅ Full | No |
| CreateBackup | ✅ Full | No |
| DescribeBackups | ✅ Full | No |
| DeleteBackups | ✅ Full | No |
| ModifyBackupConfig | ✅ Full | No |
| CreateCloneInstance | ✅ Full | No |
| CreateAccounts | ✅ Full | No |
| DescribeAccounts | ✅ Full | No |
| ModifyAccountPassword | ✅ Full | No |
| ModifyAccountPrivileges | ✅ Full | No |
| DeleteAccounts | ✅ Full | No |
| ModifyInstanceParam | ✅ Full | No |
| DescribeInstanceParams | ✅ Full | No |
| OpenSSL | ✅ Full | No |
| CloseSSL | ✅ Full | No |
| DescribeSSLStatus | ✅ Full | No |
| OpenWanService | ✅ Full | No |
| CloseWanService | ✅ Full | No |
| DescribeSlowLogData | ✅ Full | No |
| DescribeErrorLogData | ✅ Full | No |
| UpgradeDBInstanceEngineVersion | ✅ Full | No |
| DescribeTasks | ✅ Full | No |
| DescribeAsyncRequestInfo | ✅ Full | No |
