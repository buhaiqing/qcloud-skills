# API & SDK Usage — TencentDB for MongoDB

## SDK Module

```bash
pip install tencentcloud-sdk-python-mongodb
```

```python
from tencentcloud.mongodb.v20190725 import mongodb_client, models
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
```

## Client Initialization

```python
def get_client() -> mongodb_client.MongodbClient:
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    return mongodb_client.MongodbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
```

## Operation Map (79 Actions)

### Instance Operations

| Action | Key Params | Description |
|--------|------------|-------------|
| CreateDBInstance | Zone, NodeNum, Memory, Volume, MongoVersion, MachineCode, ClusterType, Period | Create prepaid instance |
| CreateDBInstanceHour | Zone, NodeNum, Memory, Volume, MongoVersion, MachineCode, ClusterType | Create postpaid instance |
| DescribeDBInstances | InstanceIds[], Limit, Offset | List/describe instances |
| ModifyDBInstanceSpec | InstanceId, Memory, Volume, NodeNum, OpType | Scale instance up/down |
| IsolateDBInstance | InstanceId | Isolate postpaid instance |
| OfflineIsolatedDBInstance | InstanceId | Permanently delete isolated instance |
| TerminateDBInstances | InstanceId | Return prepaid instance |
| RenameInstance | InstanceId, NewName | Rename instance |
| AssignProject | InstanceIds[], ProjectId | Assign to project |
| SetDBInstanceDeletionProtection | InstanceId, ProtectionFlag | Toggle deletion protection |
| DescribeDBInstanceDeal | DealId | Get order details |
| DescribeAsyncRequestInfo | DealId | Track async task status |
| ModifyInstanceAz | InstanceId, Zone | Change node AZ |
| RestartNodes | InstanceId, NodeIds[] | Restart specific nodes |
| UpgradeDBInstanceKernelVersion | InstanceId | Upgrade kernel version |
| UpgradeDbInstanceVersion | InstanceId, MongoVersion | Upgrade DB version |
| DescribeSpecInfo | Zone | List available specs |
| InquirePriceCreateDBInstances | Zone, Memory, Volume, NodeNum, MongoVersion | Price inquiry for create |
| InquirePriceModifyDBInstanceSpec | InstanceId, Memory, Volume | Price inquiry for modify |
| InquirePriceRenewDBInstances | InstanceId, Period | Price inquiry for renew |
| RenewDBInstances | InstanceId, Period | Renew prepaid instance |
| DescribeInstanceParams | InstanceId | List modifiable params |
| ModifyInstanceParams | InstanceId, InstanceParams[] | Modify params |
| DescribeCurrentOp | InstanceId, OpId, Ns, Operation | List current operations |
| KillOps | InstanceId, Operations[] | Kill specific operations |
| DescribeClientConnections | InstanceId | List client connections |
| DescribeDBInstanceNodeProperty | InstanceId | List node properties |
| DescribeDBInstanceURL | InstanceId | Get connection URI |
| DescribeDBInstanceNamespace | InstanceId | List databases/tables |
| DescribeInstanceSSL | InstanceId | Check SSL status |
| InstanceEnableSSL | InstanceId, SslSwitch | Enable/disable SSL |
| DescribeSecurityGroup | InstanceId | List security groups |
| ModifyDBInstanceSecurityGroup | InstanceId, SecurityGroupIds[] | Change security groups |
| DescribeTransparentDataEncryptionStatus | InstanceId | Check TDE status |
| EnableTransparentDataEncryption | InstanceId, KeyId | Enable TDE |
| EnableWanService | InstanceId, VipVport[], ListenerPort[] | Enable public access |
| ModifyDBInstanceNetworkAddress | InstanceId, NetworkAddresses[] | Modify network settings |
| SetInstanceMaintenance | InstanceId, MaintenanceStart, MaintenanceEnd | Set maintenance window |
| DescribeSRVConnectionDomain | InstanceId | Get SRV domain |
| EnableSRVConnectionUrl | InstanceId | Enable SRV access |
| DisableSRVConnectionUrl | InstanceId | Disable SRV access |
| ModifySRVConnectionUrl | InstanceId, Url | Modify SRV URL |

### Backup Operations

| Action | Key Params | Description |
|--------|------------|-------------|
| CreateBackupDBInstance | InstanceId | Create manual backup |
| DescribeDBBackups | InstanceId, BackupMethod, Limit, Offset | List backups |
| DeleteDBBackups | InstanceId, BackupIds[] | Delete backups |
| SetBackupRules | InstanceId, BackupType, BackupTime, BackupRetentionPeriod | Set auto backup config |
| DescribeBackupRules | InstanceId | Get backup config |
| RestoreDBInstance | InstanceId, BackupId | Restore from backup |
| CreateBackupDownloadTask | InstanceId, ReplicaSetIds[] | Create download task |
| DescribeBackupDownloadTask | InstanceId, Limit, Offset | Query download tasks |

### Account Operations

| Action | Key Params | Description |
|--------|------------|-------------|
| CreateAccountUser | InstanceId, UserName, Password, AuthRole[] | Create account |
| DescribeAccountUsers | InstanceId | List accounts |
| DeleteAccountUser | InstanceId, UserName | Delete account |
| ResetDBInstancePassword | InstanceId, UserName, Password | Reset password |
| SetAccountUserPrivilege | InstanceId, UserName, AuthRole[] | Set permissions |
| DescribePasswordRotation | InstanceId | Check rotation status |
| EnablePasswordRotation | InstanceId, UserName | Enable rotation |

### Audit Operations

| Action | Key Params | Description |
|--------|------------|-------------|
| OpenAuditService | InstanceId, LogExpireDay | Enable audit |
| CloseAuditService | InstanceId | Disable audit |
| ModifyAuditService | InstanceId, LogExpireDay | Change audit config |
| DescribeAuditConfig | InstanceId | Get audit config |
| DescribeAuditInstanceList | Filters[], Limit, Offset | List audit-enabled instances |
| CreateAuditLogFile | InstanceId, StartTime, EndTime, AuditLogFilter | Create audit log file |
| DeleteAuditLogFile | InstanceId, FileName | Delete audit log file |
| DescribeAuditLogFiles | InstanceId, Limit, Offset | List audit log files |
| DescribeAuditLogs | InstanceId, StartTime, EndTime, Limit, Offset | Query audit logs |

### Parameter Template Operations

| Action | Key Params | Description |
|--------|------------|-------------|
| CreateDBInstanceParamTpl | MongoVersion, ClusterType, TplName, Params[] | Create template |
| DescribeDBInstanceParamTpl | MongoVersion, ClusterType, Limit, Offset | List templates |
| DescribeDBInstanceParamTplDetail | TplId | Get template details |
| DropDBInstanceParamTpl | TplId | Delete template |
| ModifyDBInstanceParamTpl | TplId, TplName, Params[] | Modify template |

### Other Operations

| Action | Key Params | Description |
|--------|------------|-------------|
| FlashBackDBInstance | InstanceId, Databases[] | Key-based flashback |
| FlushInstanceRouterConfig | InstanceId | Refresh shard routing |
| DescribeMongodbLogs | InstanceId, StartTime, EndTime | Query error logs |
| DescribeSlowLogs | InstanceId, StartTime, EndTime, SlowMS | Query slow logs |
| DescribeSlowLogPatterns | InstanceId, StartTime, EndTime, SlowMS | Get slow log patterns |
| DescribeDetailedSlowLogs | InstanceId, StartTime, EndTime, SlowMS | Get detailed slow logs |
| CreateLogDownloadTask | InstanceId, StartTime, EndTime | Create log download |
| DescribeLogDownloadTasks | InstanceId | Query download tasks |

## Pagination

All list operations support pagination:
- `Limit`: 1-100 (default 20)
- `Offset`: 0-10000

```bash
tccli mongodb DescribeDBInstances --Limit 20 --Offset 0
```

## Async Operation Pattern

Operations like Create, Modify, Restore return a DealId. Track via:
```bash
tccli mongodb DescribeAsyncRequestInfo --DealId "{{output.deal_id}}"
```

Status values: `initial` → `executing` → `success` | `error`

## Common Response Paths

| Field | Path |
|-------|------|
| InstanceId | `$.Response.InstanceDetails[0].InstanceId` |
| InstanceList | `$.Response.InstanceDetails[*]` |
| Status | `$.Response.InstanceDetails[0].Status` |
| TotalCount | `$.Response.TotalCount` |
| DealId | `$.Response.DealId` |
| RequestId | `$.Response.RequestId` |
| BackupId | `$.Response.BackupList[0].BackId` |
| ErrorCode | `$.Response.Error.Code` |
| ErrorMessage | `$.Response.Error.Message` |
