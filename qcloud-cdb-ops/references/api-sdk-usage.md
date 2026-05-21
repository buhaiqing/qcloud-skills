# CDB API & SDK Usage

Operation map, method signatures, required parameters, and request/response examples for `tencentcloud-sdk-python-cdb`.

---

## 1. SDK Installation

```bash
pip install tencentcloud-sdk-python-cdb
```

---

## 2. Client Setup

```python
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cdb.v20170320 import cdb_client, models

# Credential from environment
cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)

# Client with region
client = cdb_client.CdbClient(cred, "ap-guangzhou")
```

---

## 3. Operation Map

### Instance Lifecycle Operations

| Operation | Method | Required Parameters | Response Fields |
|-----------|--------|-------------------|-----------------|
| CreateDBInstance | `CreateDBInstance` | `Memory`, `Volume`, `Period`, `GoodsNum`, `Zone` | `DealIds`, `InstanceIds` |
| CreateDBInstanceHour | `CreateDBInstanceHour` | `Memory`, `Volume`, `GoodsNum`, `Zone` | `DealIds`, `InstanceIds` |
| DescribeDBInstances | `DescribeDBInstances` | — | `Items`, `TotalCount` |
| UpgradeDBInstance | `UpgradeDBInstance` | `InstanceId`, `Memory`, `Volume` | `DealIds`, `RequestId` |
| RestartDBInstances | `RestartDBInstances` | `InstanceIds` | `RequestId` |
| IsolateDBInstance | `IsolateDBInstance` | `InstanceId` | `RequestId` |
| ReleaseIsolatedDBInstances | `ReleaseIsolatedDBInstances` | `InstanceIds` | `RequestId` |
| RenewDBInstance | `RenewDBInstance` | `InstanceId`, `TimeSpan`, `ModifyPayType` | `DealId` |
| ModifyDBInstanceName | `ModifyDBInstanceName` | `InstanceId`, `InstanceName` | `RequestId` |
| ModifyDBInstanceProject | `ModifyDBInstanceProject` | `InstanceIds`, `ProjectId` | `RequestId` |

### Backup Operations

| Operation | Method | Required Parameters | Response Fields |
|-----------|--------|-------------------|-----------------|
| CreateBackup | `CreateBackup` | `InstanceId`, `BackupMethod` | `BackupId`, `RequestId` |
| DescribeBackups | `DescribeBackups` | `InstanceId` | `Items`, `TotalCount` |
| DeleteBackups | `DeleteBackups` | `InstanceId`, `BackupIds` | `RequestId` |
| DescribeBackupConfig | `DescribeBackupConfig` | `InstanceId` | `StartTime`, `BackupModel` |
| ModifyBackupConfig | `ModifyBackupConfig` | `InstanceId` | `RequestId` |
| CreateCloneInstance | `CreateCloneInstance` | `InstanceId`, `SpecifyBackupId` | `DealIds`, `RequestId` |
| DescribeCloneList | `DescribeCloneList` | `InstanceId` | `Items` |

### Account Operations

| Operation | Method | Required Parameters | Response Fields |
|-----------|--------|-------------------|-----------------|
| CreateAccounts | `CreateAccounts` | `InstanceId`, `Accounts`, `Password` | `RequestId` |
| DescribeAccounts | `DescribeAccounts` | `InstanceId` | `Items`, `TotalCount` |
| ModifyAccountPassword | `ModifyAccountPassword` | `InstanceId`, `Accounts`, `NewPassword` | `RequestId` |
| ModifyAccountPrivileges | `ModifyAccountPrivileges` | `InstanceId`, `Accounts`, `DatabasePrivileges` | `RequestId` |
| DeleteAccounts | `DeleteAccounts` | `InstanceId`, `Accounts` | `RequestId` |

### Parameter Operations

| Operation | Method | Required Parameters | Response Fields |
|-----------|--------|-------------------|-----------------|
| DescribeInstanceParams | `DescribeInstanceParams` | `InstanceId` | `Items`, `TotalCount` |
| DescribeDefaultParams | `DescribeDefaultParams` | `EngineVersion` | `Items` |
| ModifyInstanceParam | `ModifyInstanceParam` | `InstanceIds`, `ParamList` | `RequestId`, `AsyncRequestId` |

### Security Operations

| Operation | Method | Required Parameters | Response Fields |
|-----------|--------|-------------------|-----------------|
| OpenSSL | `OpenSSL` | `InstanceId` | `RequestId` |
| CloseSSL | `CloseSSL` | `InstanceId` | `RequestId` |
| DescribeSSLStatus | `DescribeSSLStatus` | `InstanceId` | `SSLStatus`, `RequestId` |
| OpenDBInstanceEncryption | `OpenDBInstanceEncryption` | `InstanceId`, `KeyId` | `RequestId` |
| DescribeDBInstanceEncryption | `DescribeDBInstanceEncryption` | `InstanceId` | `EncryptionStatus` |

### Network Operations

| Operation | Method | Required Parameters | Response Fields |
|-----------|--------|-------------------|-----------------|
| OpenWanService | `OpenWanService` | `InstanceId` | `RequestId` |
| CloseWanService | `CloseWanService` | `InstanceId` | `RequestId` |
| ModifyDBInstanceVipVport | `ModifyDBInstanceVipVport` | `InstanceId`, `Vip`, `Vport` | `RequestId` |

### Log and Analysis Operations

| Operation | Method | Required Parameters | Response Fields |
|-----------|--------|-------------------|-----------------|
| DescribeErrorLogData | `DescribeErrorLogData` | `InstanceId`, `StartTime`, `EndTime` | `Items`, `TotalCount` |
| DescribeSlowLogData | `DescribeSlowLogData` | `InstanceId`, `StartTime`, `EndTime` | `Items`, `TotalCount` |
| DescribeSlowLogs | `DescribeSlowLogs` | `InstanceId` | `Items`, `TotalCount` |
| DescribeDBPrice | `DescribeDBPrice` | `Memory`, `Volume`, `Period`, `Zone` | `Price`, `OriginalPrice` |

### Version Operations

| Operation | Method | Required Parameters | Response Fields |
|-----------|--------|-------------------|-----------------|
| UpgradeDBInstanceEngineVersion | `UpgradeDBInstanceEngineVersion` | `InstanceId`, `EngineVersion` | `RequestId` |
| DescribeSupportedEngineVersions | `DescribeSupportedEngineVersions` | `InstanceId` | `EngineVersions` |

### Task Operations

| Operation | Method | Required Parameters | Response Fields |
|-----------|--------|-------------------|-----------------|
| DescribeTasks | `DescribeTasks` | `InstanceId`, `StartTimeBegin`, `StartTimeEnd` | `Items`, `TotalCount` |
| DescribeAsyncRequestInfo | `DescribeAsyncRequestInfo` | `AsyncRequestId` | `Status`, `Info` |

---

## 4. CreateDBInstance (Create MySQL Instance — Prepaid)

### Request Example

```python
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cdb.v20170320 import cdb_client, models

def create_mysql_instance():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = cdb_client.CdbClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))

        req = models.CreateDBInstanceRequest()
        req.Memory = 1000      # 1 GB
        req.Volume = 50        # 50 GB
        req.Period = 1         # 1 month
        req.GoodsNum = 1
        req.Zone = "ap-guangzhou-3"
        req.EngineVersion = "8.0"
        req.InstanceRole = "master"
        req.ProjectId = 0

        # Optional: VPC configuration
        req.UniqVpcId = "vpc-xxxxxx"
        req.UniqSubnetId = "subnet-xxxxxx"

        # Optional: port (default 3306)
        req.Port = 3306

        resp = client.CreateDBInstance(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

create_mysql_instance()
```

### Response Example

```json
{
  "Response": {
    "DealIds": ["20260521xxxxxx"],
    "InstanceIds": ["cdb-xxxxxx"],
    "RequestId": "abc-123-def-456"
  }
}
```

---

## 5. DescribeDBInstances (List MySQL Instances)

```python
def list_db_instances():
    try:
        client = cdb_client.CdbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.DescribeDBInstancesRequest()
        req.Offset = 0
        req.Limit = 20
        # Optional: filter by instance IDs
        # req.InstanceIds = ["cdb-xxxxxx"]
        # Optional: filter by status (1=running)
        # req.Status = ["1"]

        resp = client.DescribeDBInstances(req)
        print(json.dumps(resp.to_json_string(), indent=2))
        
        for item in resp.Items:
            print(f"ID: {item.InstanceId}, Name: {item.InstanceName}, "
                  f"Status: {item.Status}, Version: {item.EngineVersion}, "
                  f"IP: {item.Vip}:{item.Vport}")
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")
```

### Response Example

```json
{
  "Response": {
    "TotalCount": 3,
    "Items": [
      {
        "InstanceId": "cdb-xxxxxx",
        "InstanceName": "production-db",
        "Status": 1,
        "Memory": 4000,
        "Volume": 200,
        "EngineVersion": "8.0",
        "Vip": "10.0.0.10",
        "Vport": 3306,
        "Zone": "ap-guangzhou-3",
        "InstanceType": 1,
        "AutoRenew": 1,
        "CreateTime": "2026-05-01T10:00:00+08:00",
        "DeadTime": "2026-06-01T10:00:00+08:00",
        "Region": "ap-guangzhou"
      }
    ],
    "RequestId": "abc-123-def-456"
  }
}
```

---

## 6. UpgradeDBInstance (Scale Configuration)

```python
def upgrade_instance(instance_id, new_memory, new_volume):
    try:
        client = cdb_client.CdbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.UpgradeDBInstanceRequest()
        req.InstanceId = instance_id
        req.Memory = new_memory
        req.Volume = new_volume
        req.WaitSwitch = 1  # 0=immediate, 1=maintenance window

        resp = client.UpgradeDBInstance(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")
```

---

## 7. Backup Operations

### CreateBackup

```python
def create_backup(instance_id, method="physical"):
    try:
        client = cdb_client.CdbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.CreateBackupRequest()
        req.InstanceId = instance_id
        req.BackupMethod = method  # "physical" or "logical"
        
        # Optional: backup specific tables
        # req.BackupDBTableList = [{"Db": "mydb", "Table": "users"}]

        resp = client.CreateBackup(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")
```

### DescribeBackups

```python
def list_backups(instance_id):
    try:
        client = cdb_client.CdbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.DescribeBackupsRequest()
        req.InstanceId = instance_id
        req.Offset = 0
        req.Limit = 10

        resp = client.DescribeBackups(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")
```

### CreateCloneInstance (Restore from Backup)

```python
def clone_from_backup(instance_id, backup_id):
    try:
        client = cdb_client.CdbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.CreateCloneInstanceRequest()
        req.InstanceId = instance_id
        req.SpecifyBackupId = backup_id
        req.SpecifyBackupType = "BackupId"
        # Optional: specify memory/volume for new instance
        # req.NewInstanceMemory = 4000
        # req.NewInstanceVolume = 200
        # Optional: rollback to specific time
        # req.SpecifyBackupTime = "2026-05-21 12:00:00"

        resp = client.CreateCloneInstance(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")
```

---

## 8. Account Operations

### CreateAccounts

```python
def create_account(instance_id, username, password, host="%"):
    try:
        client = cdb_client.CdbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.CreateAccountsRequest()
        req.InstanceId = instance_id
        req.Accounts = [{"User": username, "Host": host}]
        req.Password = password
        req.Description = "Application account"

        resp = client.CreateAccounts(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")
```

### ModifyAccountPrivileges

```python
def grant_privileges(instance_id, username, host, db_name, privileges):
    try:
        client = cdb_client.CdbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.ModifyAccountPrivilegesRequest()
        req.InstanceId = instance_id
        req.Accounts = [{"User": username, "Host": host}]
        req.GlobalPrivileges = ["SELECT", "INSERT", "UPDATE", "DELETE"]
        # Or database-specific privileges:
        # req.DatabasePrivileges = [{
        #     "Database": db_name,
        #     "Privileges": privileges
        # }]

        resp = client.ModifyAccountPrivileges(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")
```

---

## 9. Parameter Modification

```python
def modify_params(instance_id, params_dict):
    try:
        client = cdb_client.CdbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.ModifyInstanceParamRequest()
        req.InstanceIds = [instance_id]
        req.ParamList = [{"Name": k, "CurrentValue": str(v)} for k, v in params_dict.items()]

        resp = client.ModifyInstanceParam(req)
        print(json.dumps(resp.to_json_string(), indent=2))
        
        # Track async task
        if resp.AsyncRequestId:
            print(f"Async task: {resp.AsyncRequestId}")
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

# Example: modify max_connections
modify_params("cdb-xxxxxx", {"max_connections": "1000", "wait_timeout": "28800"})
```

---

## 10. Slow Query Analysis

```python
def analyze_slow_queries(instance_id, start_time, end_time):
    try:
        client = cdb_client.CdbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.DescribeSlowLogDataRequest()
        req.InstanceId = instance_id
        req.StartTime = start_time
        req.EndTime = end_time
        req.Limit = 20

        resp = client.DescribeSlowLogData(req)
        print(json.dumps(resp.to_json_string(), indent=2))
        
        # Analyze slow queries
        for item in resp.Items:
            print(f"Query: {item.Sql[:100]}...")
            print(f"  ExecTime: {item.QueryTime}s, RowsExamined: {item.RowsExamined}")
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")
```

---

## 11. Error Log Query

```python
def get_error_logs(instance_id, start_time, end_time):
    try:
        client = cdb_client.CdbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.DescribeErrorLogDataRequest()
        req.InstanceId = instance_id
        req.StartTime = start_time
        req.EndTime = end_time
        req.Limit = 20

        resp = client.DescribeErrorLogData(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")
```

---

## 12. Pagination Pattern

```python
def paginate_all_instances():
    """Fetch all instances with pagination."""
    all_instances = []
    offset = 0
    limit = 100
    
    while True:
        req = models.DescribeDBInstancesRequest()
        req.Offset = offset
        req.Limit = limit
        
        resp = client.DescribeDBInstances(req)
        items = resp.Items
        if not items:
            break
        all_instances.extend(items)
        
        if len(items) < limit:
            break
        offset += limit
    
    return all_instances
```

---

## 13. Error Handling Pattern

```python
def safe_api_call(func, *args, max_retries=3, **kwargs):
    """Retry wrapper for CDB API calls."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except TencentCloudSDKException as err:
            last_error = err
            code = err.code
            if code in ["RequestLimitExceeded", "InternalError", "InternalError.DBError",
                        "FailedOperation.StatusConflict", "OperationDenied.InstanceLocked"]:
                import time
                wait = 2 ** attempt
                print(f"[RETRY] {code}: retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue
            else:
                raise
    raise last_error
```
