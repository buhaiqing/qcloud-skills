# CDB Execution Flows (CLI/SDK Commands)

> **What vs. How**: This file describes **how to execute** each operation (CLI/SDK code blocks).
> For **what** each operation does, see `SKILL.md` § Execution Flows.

## Index

| # | Operation | CLI Command | SDK Command | Notes |
|---|-----------|-------------|-------------|-------|
| 1 | CreateDBInstance | `tccli cdb CreateDBInstance ...` | `client.CreateDBInstance(req)` | Prepaid instance |
| 2 | DescribeDBInstances | `tccli cdb DescribeDBInstances ...` | `client.DescribeDBInstances(req)` | List/filter instances |
| 3 | UpgradeDBInstance | `tccli cdb UpgradeDBInstance ...` | `client.UpgradeDBInstance(req)` | Scale instance |
| 4 | RestartDBInstances | `tccli cdb RestartDBInstances ...` | `client.RestartDBInstances(req)` | Restart instance |
| 5 | IsolateDBInstance | `tccli cdb IsolateDBInstance ...` | — | Destructive, see SKILL.md Safety Gates |
| 6 | CreateBackup | `tccli cdb CreateBackup ...` | `client.CreateBackup(req)` | Manual backup |
| 7 | ModifyInstanceParam | `tccli cdb ModifyInstanceParam ...` | `client.ModifyInstanceParam(req)` | Parameter change |
| 8 | CreateAccount | `tccli cdb CreateAccounts ...` | `client.CreateAccounts(req)` | Create DB account |
| 9 | DescribeAccounts | `tccli cdb DescribeAccounts ...` | `client.DescribeAccounts(req)` | List accounts |
| 10 | ModifyAccountPassword | `tccli cdb ModifyAccountPassword ...` | `client.ModifyAccountPassword(req)` | Change password |
| 11 | DescribeSlowLogData | `tccli cdb DescribeSlowLogData ...` | — | Slow query log |
| 12 | DescribeBackups | `tccli cdb DescribeBackups ...` | — | List backups (validation) |

---

## 1. CreateDBInstance (Create MySQL Instance — Prepaid)

### CLI

```bash
tccli cdb CreateDBInstance \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Memory 1000 \
  --Volume 50 \
  --Period 1 \
  --GoodsNum 1 \
  --Zone "{{user.zone}}" \
  --UniqVpcId "{{user.vpc_id}}" \
  --UniqSubnetId "{{user.subnet_id}}" \
  --EngineVersion "8.0" \
  --InstanceRole "master" \
  --ProjectId 0
```

### SDK

```python
from __future__ import annotations
import json
from tencentcloud.cdb.v20170320 import models, CdbClient
from tencentcloud.common import Credential
from tencentcloud.common.profile import HttpProfile, ClientProfile

cred = Credential("{{env.TENCENTCLOUD_SECRET_ID}}", "{{env.TENCENTCLOUD_SECRET_KEY}}")
http_profile = HttpProfile()
http_profile.endpoint = "cdb.tencentcloudapi.com"
client_profile = ClientProfile(http_profile=http_profile)
client = CdbClient(cred, "{{env.TENCENTCLOUD_REGION}}", client_profile)

req = models.CreateDBInstanceRequest()
req.Memory = 1000
req.Volume = 50
req.Period = 1
req.GoodsNum = 1
req.Zone = "{{user.zone}}"
req.EngineVersion = "8.0"
req.InstanceRole = "master"
req.ProjectId = 0

resp = client.CreateDBInstance(req)
print(resp.to_json_string())
```

---

## 2. DescribeDBInstances (List Instances)

### CLI

```bash
# List all instances
tccli cdb DescribeDBInstances --Region {{env.TENCENTCLOUD_REGION}} --Offset 0 --Limit 20

# Filter by instance ID
tccli cdb DescribeDBInstances --InstanceIds '["cdb-xxxxxx"]'

# Filter by status (1=running)
tccli cdb DescribeDBInstances --Status "[1]"

# Filter by project
tccli cdb DescribeDBInstances --ProjectId 0
```

### SDK

```python
from __future__ import annotations
import json
from tencentcloud.cdb.v20170320 import models, CdbClient
from tencentcloud.common import Credential
from tencentcloud.common.profile import HttpProfile, ClientProfile

cred = Credential("{{env.TENCENTCLOUD_SECRET_ID}}", "{{env.TENCENTCLOUD_SECRET_KEY}}")
http_profile = HttpProfile()
http_profile.endpoint = "cdb.tencentcloudapi.com"
client_profile = ClientProfile(http_profile=http_profile)
client = CdbClient(cred, "{{env.TENCENTCLOUD_REGION}}", client_profile)

req = models.DescribeDBInstancesRequest()
req.Offset = 0
req.Limit = 20
# Optional filters:
# req.InstanceIds = ["cdb-xxxxxx"]
# req.Status = [1]  # 1=running

resp = client.DescribeDBInstances(req)
print(resp.to_json_string())
```

---

## 3. UpgradeDBInstance (Scale Instance)

### CLI

```bash
tccli cdb UpgradeDBInstance \
  --InstanceId "{{user.instance_id}}" \
  --Memory 4000 \
  --Volume 200 \
  --WaitSwitch 1
```

### SDK

```python
from __future__ import annotations
import json
from tencentcloud.cdb.v20170320 import models, CdbClient
from tencentcloud.common import Credential
from tencentcloud.common.profile import HttpProfile, ClientProfile

cred = Credential("{{env.TENCENTCLOUD_SECRET_ID}}", "{{env.TENCENTCLOUD_SECRET_KEY}}")
http_profile = HttpProfile()
http_profile.endpoint = "cdb.tencentcloudapi.com"
client_profile = ClientProfile(http_profile=http_profile)
client = CdbClient(cred, "{{env.TENCENTCLOUD_REGION}}", client_profile)

req = models.UpgradeDBInstanceRequest()
req.InstanceId = "{{user.instance_id}}"
req.Memory = 4000
req.Volume = 200
req.WaitSwitch = 1  # 0=immediate, 1=maintain window

resp = client.UpgradeDBInstance(req)
print(resp.to_json_string())
```

---

## 4. RestartDBInstances

### CLI

```bash
tccli cdb RestartDBInstances --InstanceIds '["{{user.instance_id}}"]'
```

### SDK

```python
from __future__ import annotations
import json
from tencentcloud.cdb.v20170320 import models, CdbClient
from tencentcloud.common import Credential
from tencentcloud.common.profile import HttpProfile, ClientProfile

cred = Credential("{{env.TENCENTCLOUD_SECRET_ID}}", "{{env.TENCENTCLOUD_SECRET_KEY}}")
http_profile = HttpProfile()
http_profile.endpoint = "cdb.tencentcloudapi.com"
client_profile = ClientProfile(http_profile=http_profile)
client = CdbClient(cred, "{{env.TENCENTCLOUD_REGION}}", client_profile)

req = models.RestartDBInstancesRequest()
req.InstanceIds = ["{{user.instance_id}}"]

resp = client.RestartDBInstances(req)
print(resp.to_json_string())
```

---

## 5. IsolateDBInstance (Destructive)

> **Safety Gates apply**: See `SKILL.md` § Safety Gates before executing.
> SDK not shown — isolate requires explicit user confirmation (Safety Gate).

### CLI

```bash
tccli cdb IsolateDBInstance --InstanceId "{{user.instance_id}}"
```

---

## 6. CreateBackup (Manual Backup)

### CLI

```bash
tccli cdb CreateBackup \
  --InstanceId "{{user.instance_id}}" \
  --BackupMethod "logical" \
  --BackupDBTableList '[{"Db":"mysql","Table":"user"}]'
```

### SDK

```python
from __future__ import annotations
import json
from tencentcloud.cdb.v20170320 import models, CdbClient
from tencentcloud.common import Credential
from tencentcloud.common.profile import HttpProfile, ClientProfile

cred = Credential("{{env.TENCENTCLOUD_SECRET_ID}}", "{{env.TENCENTCLOUD_SECRET_KEY}}")
http_profile = HttpProfile()
http_profile.endpoint = "cdb.tencentcloudapi.com"
client_profile = ClientProfile(http_profile=http_profile)
client = CdbClient(cred, "{{env.TENCENTCLOUD_REGION}}", client_profile)

req = models.CreateBackupRequest()
req.InstanceId = "{{user.instance_id}}"
req.BackupMethod = "physical"  # or "logical"

# Optional: backup specific tables
# table_item = models.BackupItem()
# table_item.Db = "mysql"
# table_item.Table = "user"
# req.BackupDBTableList = [table_item]

resp = client.CreateBackup(req)
print(resp.to_json_string())
```

### DescribeBackups (Validation)

```bash
tccli cdb DescribeBackups --InstanceId "{{user.instance_id}}" --Offset 0 --Limit 1
```

---

## 7. ModifyInstanceParam (Parameter Change)

### CLI

```bash
tccli cdb ModifyInstanceParam \
  --InstanceIds '["{{user.instance_id}}"]' \
  --ParamList '[{"Name":"auto_increment_increment","CurrentValue":"2"},{"Name":"max_connections","CurrentValue":"1000"}]'
```

### SDK

```python
from __future__ import annotations
import json
from tencentcloud.cdb.v20170320 import models, CdbClient
from tencentcloud.common import Credential
from tencentcloud.common.profile import HttpProfile, ClientProfile

cred = Credential("{{env.TENCENTCLOUD_SECRET_ID}}", "{{env.TENCENTCLOUD_SECRET_KEY}}")
http_profile = HttpProfile()
http_profile.endpoint = "cdb.tencentcloudapi.com"
client_profile = ClientProfile(http_profile=http_profile)
client = CdbClient(cred, "{{env.TENCENTCLOUD_REGION}}", client_profile)

req = models.ModifyInstanceParamRequest()
req.InstanceIds = ["{{user.instance_id}}"]

param1 = models.Parameter()
param1.Name = "auto_increment_increment"
param1.CurrentValue = "2"

param2 = models.Parameter()
param2.Name = "max_connections"
param2.CurrentValue = "1000"

req.ParamList = [param1, param2]

resp = client.ModifyInstanceParam(req)
print(resp.to_json_string())
```

---

## 8. CreateAccount

### CLI

```bash
tccli cdb CreateAccounts \
  --InstanceId "{{user.instance_id}}" \
  --Accounts '[{"User":"dbuser","Host":"%"}]' \
  --Password "{{user.password}}" \
  --Description "Application account"
```

### SDK

```python
from __future__ import annotations
import json
from tencentcloud.cdb.v20170320 import models, CdbClient
from tencentcloud.common import Credential
from tencentcloud.common.profile import HttpProfile, ClientProfile

cred = Credential("{{env.TENCENTCLOUD_SECRET_ID}}", "{{env.TENCENTCLOUD_SECRET_KEY}}")
http_profile = HttpProfile()
http_profile.endpoint = "cdb.tencentcloudapi.com"
client_profile = ClientProfile(http_profile=http_profile)
client = CdbClient(cred, "{{env.TENCENTCLOUD_REGION}}", client_profile)

req = models.CreateAccountsRequest()
req.InstanceId = "{{user.instance_id}}"

account = models.Account()
account.User = "dbuser"
account.Host = "%"

req.Accounts = [account]
req.Password = "{{user.password}}"
req.Description = "Application account"

resp = client.CreateAccounts(req)
print(resp.to_json_string())
```

---

## 9. DescribeAccounts

### CLI

```bash
tccli cdb DescribeAccounts --InstanceId "{{user.instance_id}}" --Limit 20
```

### SDK

```python
from __future__ import annotations
import json
from tencentcloud.cdb.v20170320 import models, CdbClient
from tencentcloud.common import Credential
from tencentcloud.common.profile import HttpProfile, ClientProfile

cred = Credential("{{env.TENCENTCLOUD_SECRET_ID}}", "{{env.TENCENTCLOUD_SECRET_KEY}}")
http_profile = HttpProfile()
http_profile.endpoint = "cdb.tencentcloudapi.com"
client_profile = ClientProfile(http_profile=http_profile)
client = CdbClient(cred, "{{env.TENCENTCLOUD_REGION}}", client_profile)

req = models.DescribeAccountsRequest()
req.InstanceId = "{{user.instance_id}}"
req.Limit = 20

resp = client.DescribeAccounts(req)
print(resp.to_json_string())
```

---

## 10. ModifyAccountPassword

### CLI

```bash
tccli cdb ModifyAccountPassword \
  --InstanceId "{{user.instance_id}}" \
  --Accounts '[{"User":"dbuser","Host":"%"}]' \
  --NewPassword "{{user.new_password}}"
```

### SDK

```python
from __future__ import annotations
import json
from tencentcloud.cdb.v20170320 import models, CdbClient
from tencentcloud.common import Credential
from tencentcloud.common.profile import HttpProfile, ClientProfile

cred = Credential("{{env.TENCENTCLOUD_SECRET_ID}}", "{{env.TENCENTCLOUD_SECRET_KEY}}")
http_profile = HttpProfile()
http_profile.endpoint = "cdb.tencentcloudapi.com"
client_profile = ClientProfile(http_profile=http_profile)
client = CdbClient(cred, "{{env.TENCENTCLOUD_REGION}}", client_profile)

req = models.ModifyAccountPasswordRequest()
req.InstanceId = "{{user.instance_id}}"

account = models.Account()
account.User = "dbuser"
account.Host = "%"

req.Accounts = [account]
req.NewPassword = "{{user.new_password}}"

resp = client.ModifyAccountPassword(req)
print(resp.to_json_string())
```

---

## 11. DescribeSlowLogData (Slow Query Log)

### CLI

```bash
tccli cdb DescribeSlowLogData \
  --InstanceId "{{user.instance_id}}" \
  --StartTime "2026-05-20 00:00:00" \
  --EndTime "2026-05-21 00:00:00" \
  --Limit 20
```

### Quick Check Commands

```bash
# Confirm slow queries exist (last 1 hour)
tccli cdb DescribeSlowLogData \
  --InstanceId "{{user.instance_id}}" \
  --StartTime "$(date -v-1H +'%Y-%m-%d %H:%M:%S')" \
  --EndTime "$(date +'%Y-%m-%d %H:%M:%S')" \
  --Limit 5 \
  --OrderBy "QueryTime" \
  --Order "DESC"

# Check if slow query log is enabled
tccli cdb DescribeInstanceParams \
  --InstanceId "{{user.instance_id}}" \
  --ParamNames '["slow_query_log","long_query_time"]'
```

---

## Key Response Fields Reference

| Operation | Field | JSON Path |
|-----------|-------|-----------|
| CreateDBInstance | DealId | `$.Response.DealIds[0]` |
| CreateDBInstance | InstanceId | `$.Response.InstanceIds[0]` |
| DescribeDBInstances | InstanceId | `$.Response.Items[].InstanceId` |
| DescribeDBInstances | Status | `$.Response.Items[].Status` (0=creating, 1=running, 4=isolating, 5=isolated) |
| DescribeDBInstances | Memory | `$.Response.Items[].Memory` (MB) |
| DescribeDBInstances | Volume | `$.Response.Items[].Volume` (GB) |
| DescribeDBInstances | Vip:Vport | `$.Response.Items[].Vip:$.Response.Items[].Vport` |
| CreateBackup | BackupId | `$.Response.BackupId` |
| CreateBackup | AsyncRequestId | `$.Response.AsyncRequestId` |
