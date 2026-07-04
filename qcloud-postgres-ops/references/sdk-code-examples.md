# PostgreSQL SDK Code Examples

Python SDK fallback code examples for operations where `tccli` fields are incomplete or complex JSON parameters are needed.

## Create Instance (SDK Fallback)

```python
#!/usr/bin/env python3
import os, json, time
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.postgres.v20170312 import postgres_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = postgres_client.PostgresClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.CreateDBInstancesRequest()
        req.Zone = "ap-guangzhou-3"
        req.DBVersion = "16"
        req.Memory = 4
        req.Storage = 100
        req.DBNodeSet = [{"Role": "Primary", "Zone": "ap-guangzhou-3"}, {"Role": "Standby", "Zone": "ap-guangzhou-3"}]
        req.DBInstanceCount = 1
        req.InstanceChargeType = "postpaid"

        resp = client.CreateDBInstances(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

## Describe Instances (SDK Fallback)

```python
req = models.DescribeDBInstancesRequest()
req.Filters = [{"Name": "db-instance-id", "Values": ["postgres-xxxxx"]}]
resp = client.DescribeDBInstances(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

## Modify Instance Spec (SDK Fallback)

```python
req = models.UpgradeDBInstanceRequest()
req.DBInstanceId = "{{user.instance_id}}"
req.Memory = 8
req.Storage = 200
resp = client.UpgradeDBInstance(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

## Create Backup (SDK Fallback)

```python
req = models.CreateBackupRequest()
req.DBInstanceId = "{{user.instance_id}}"
req.BackupType = "physical"
req.BackupName = "manual-backup-20260531"
resp = client.CreateBackup(req)
print(json.dumps(resp.to_json_string(), indent=2))
```
