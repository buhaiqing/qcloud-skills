# API & SDK Usage — TencentDB for PostgreSQL

## API Version

- **API version:** `2017-03-12`
- **API spec:** https://cloud.tencent.com/document/api/409
- **SDK package:** `tencentcloud-sdk-python` (general)

## Operation Map

| Category | API Action | CLI Command | Description |
|----------|-----------|-------------|-------------|
| Instance | CreateDBInstances | postgres CreateDBInstances | Create PostgreSQL instances |
| Instance | DescribeDBInstances | postgres DescribeDBInstances | List/describe instances |
| Instance | DescribeDBInstanceAttribute | postgres DescribeDBInstanceAttribute | Get instance details |
| Instance | UpgradeDBInstance | postgres UpgradeDBInstance | Modify instance spec |
| Instance | IsolateDBInstance | postgres IsolateDBInstance | Isolate instance |
| Instance | DeleteDBInstance | postgres DeleteDBInstance | Delete isolated instance |
| Instance | DescribeDBVersions | postgres DescribeDBVersions | List available versions |
| Instance | DescribeProductConfig | postgres DescribeProductConfig | List available specs |
| Backup | CreateBackup | postgres CreateBackup | Create manual backup |
| Backup | DescribeDBBackups | postgres DescribeDBBackups | List backups |
| Backup | RestoreDBInstance | postgres RestoreDBInstance | Restore from backup |
| Backup | DescribeDBBackupDownloadUrl | postgres DescribeDBBackupDownloadUrl | Get backup download URL |
| Account | CreateAccount | postgres CreateAccount | Create database account |
| Account | DescribeAccounts | postgres DescribeAccounts | List accounts |
| Account | ResetAccountPassword | postgres ResetAccountPassword | Reset account password |
| Parameter | DescribeInstanceParameters | postgres DescribeInstanceParameters | List instance parameters |
| Parameter | ModifyDBInstanceParameters | postgres ModifyDBInstanceParameters | Modify parameters |
| Parameter | DescribeDefaultParameters | postgres DescribeDefaultParameters | List default parameters |
| Monitor | DescribeDBInstanceMonitor | postgres DescribeDBInstanceMonitor | Get monitoring config |
| Monitor | ModifyDBInstanceMonitor | postgres ModifyDBInstanceMonitor | Modify monitoring config |
| Slow Log | DescribeSlowQueryList | postgres DescribeSlowQueryList | List slow queries |
| Slow Log | DescribeSlowQueryDetail | postgres DescribeSlowQueryDetail | Get slow query details |
| Security | DescribeDBInstanceSecurityGroups | postgres DescribeDBInstanceSecurityGroups | List security groups |
| Security | ModifyDBInstanceSecurityGroups | postgres ModifyDBInstanceSecurityGroups | Modify security groups |
| SSL | DescribeDBInstanceSSL | postgres DescribeDBInstanceSSL | Get SSL status |
| SSL | ModifyDBInstanceSSL | postgres ModifyDBInstanceSSL | Enable/disable SSL |
| Migration | CreateMigrationJob | postgres CreateMigrationJob | Create migration job |
| Migration | DescribeMigrationJobs | postgres DescribeMigrationJobs | List migration jobs |
| Migration | ModifyMigrationJob | postgres ModifyMigrationJob | Modify migration job |

## Python SDK Examples

### Setup

```python
import os
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.postgres.v20170312 import postgres_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = postgres_client.PostgresClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
```

### Describe Instances

```python
def describe_instances(instance_id=None):
    # Describe all or specific instances
    req = models.DescribeDBInstancesRequest()
    req.Limit = 20

    if instance_id:
        req.Filters = [{"Name": "db-instance-id", "Values": [instance_id]}]

    resp = client.DescribeDBInstances(req)
    return resp.to_json_string()
```

### Create Backup

```python
def create_backup(instance_id, backup_name=None):
    req = models.CreateBackupRequest()
    req.DBInstanceId = instance_id
    req.BackupType = "physical"
    req.BackupName = backup_name or f"manual-backup-{datetime.now().strftime('%Y%m%d')}"
    resp = client.CreateBackup(req)
    return resp.to_json_string()
```

### Error Handling

```python
try:
    req = models.DescribeDBInstancesRequest()
    resp = client.DescribeDBInstances(req)
    print(resp.to_json_string())
except TencentCloudSDKException as err:
    print(f"[ERROR] Code={err.get_code()}, Message={err.get_message()}")
```

## Pagination

Use `Limit` and `Offset` for pagination:

```bash
# Page 1
tccli postgres DescribeDBInstances --Limit 20 --Offset 0
# Page 2
tccli postgres DescribeDBInstances --Limit 20 --Offset 20
```

Max `Limit` value: 100 per request.
