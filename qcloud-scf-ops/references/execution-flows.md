# SCF Execution Flows (How-To Reference)

This file contains detailed CLI and SDK command blocks for each SCF operation.
SKILL.md describes **what to do** (high-level steps); this file shows **how to do it** (exact commands).

## Index

| Section | Operation | CLI Command | SDK Command |
|---------|-----------|-------------|-------------|
| §1 | CreateFunction | `tccli scf CreateFunction --FunctionName ...` | `client.CreateFunction(req)` |
| §2 | UpdateFunctionCode | `tccli scf UpdateFunctionCode --FunctionName ...` | `client.UpdateFunctionCode(req)` |
| §3 | DeleteFunction | `tccli scf DeleteFunction --FunctionName ...` | `client.DeleteFunction(req)` |
| §4 | PublishVersion | `tccli scf PublishVersion --FunctionName ...` | `client.PublishVersion(req)` |
| §5 | CreateAlias | `tccli scf CreateAlias --FunctionName ...` | `client.CreateAlias(req)` |
| §6 | CreateTrigger | `tccli scf CreateTrigger --TriggerName ...` | `client.CreateTrigger(req)` |
| §7 | GetFunctionLogs | `tccli scf GetFunctionLogs --FunctionName ...` | `client.GetFunctionLogs(req)` |
| §8 | CreateLayer | `tccli scf CreateLayer --LayerName ...` | `client.CreateLayer(req)` |
| §9 | DeleteLayerVersion | `tccli scf DeleteLayerVersion --LayerName ... --LayerVersion ...` | `client.DeleteLayerVersion(req)` |

---

## §1 Operation: CreateFunction

### CLI (Primary Path)

```bash
# Create function with zip package
tccli scf CreateFunction \
  --FunctionName "{{user.function_name}}" \
  --Handler "{{user.handler}}" \
  --Runtime "{{user.runtime}}" \
  --Namespace "{{user.namespace}}" \
  --MemorySize {{user.memory_size}} \
  --Timeout {{user.timeout}} \
  --Code.ZipFile "{{user.zip_file_path}}" \
  --Description "Serverless function deployed via agent" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

### Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
"""SDK fallback: SCF CreateFunction"""
import os, json, base64
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.scf import scf_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = scf_client.ScfClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.CreateFunctionRequest()
        req.FunctionName = os.environ.get("FUNCTION_NAME")
        req.Handler = os.environ.get("HANDLER", "index.handler")
        req.Runtime = os.environ.get("RUNTIME", "Python3.8")
        req.MemorySize = int(os.environ.get("MEMORY_SIZE", "512"))
        req.Timeout = int(os.environ.get("TIMEOUT", "30"))
        req.Namespace = os.environ.get("NAMESPACE", "default")

        # Read zip file and encode
        with open(os.environ.get("ZIP_FILE_PATH"), "rb") as f:
            zip_content = f.read()
        req.Code = models.Code()
        req.Code.ZipFile = base64.b64encode(zip_content).decode("utf-8")

        resp = client.CreateFunction(req)
        print(resp.to_json_string())
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

### Post-execution Validation

```bash
for i in $(seq 1 30); do
  STATUS=$(tccli scf GetFunction --Region {{env.TENCENTCLOUD_REGION}} --FunctionName "{{user.function_name}}" | jq -r '.Response.Status')
  [ "$STATUS" = "Active" ] && break
  sleep 2
done

# Check timeout
if [ "$STATUS" != "Active" ]; then
  echo "[ERROR] Timeout waiting for function Active status (current: $STATUS)"
  exit 1
fi
```

---

## §2 Operation: UpdateFunctionCode

### CLI (Primary Path)

```bash
tccli scf UpdateFunctionCode \
  --FunctionName "{{user.function_name}}" \
  --Handler "{{user.handler}}" \
  --Code.ZipFile "{{user.zip_file_path}}" \
  --Namespace "{{user.namespace}}" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

### Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
"""SDK fallback: SCF UpdateFunctionCode"""
import os, json, base64
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.scf import scf_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = scf_client.ScfClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.UpdateFunctionCodeRequest()
        req.FunctionName = os.environ.get("FUNCTION_NAME")
        req.Handler = os.environ.get("HANDLER", "index.handler")
        with open(os.environ.get("ZIP_FILE_PATH"), "rb") as f:
            req.Code = models.Code()
            req.Code.ZipFile = base64.b64encode(f.read()).decode("utf-8")
        req.Namespace = os.environ.get("NAMESPACE", "default")

        resp = client.UpdateFunctionCode(req)
        print(resp.to_json_string())
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

---

## §3 Operation: DeleteFunction

### CLI (Primary Path)

```bash
tccli scf DeleteFunction \
  --FunctionName "{{user.function_name}}" \
  --Namespace "{{user.namespace}}" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

### Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
"""SDK fallback: SCF DeleteFunction"""
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.scf import scf_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = scf_client.ScfClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.DeleteFunctionRequest()
        req.FunctionName = os.environ.get("FUNCTION_NAME")
        req.Namespace = os.environ.get("NAMESPACE", "default")

        resp = client.DeleteFunction(req)
        print(resp.to_json_string())
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

### Post-execution Validation

```bash
# Poll until function returns NotFound (max 60s)
for i in $(seq 1 30); do
  RESULT=$(tccli scf GetFunction \
    --Region {{env.TENCENTCLOUD_REGION}} \
    --FunctionName "{{user.function_name}}" \
    --Namespace "{{user.namespace}}" 2>&1)
  if echo "$RESULT" | grep -q "ResourceNotFound"; then
    echo "[OK] Function deleted successfully"
    break
  fi
  sleep 2
done
```

---

## §4 Operation: PublishVersion

### CLI (Primary Path)

```bash
# Publish $LATEST as a new version
tccli scf PublishVersion \
  --FunctionName "{{user.function_name}}" \
  --Namespace "{{user.namespace}}" \
  --Description "Version published $(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

### Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
"""SDK fallback: SCF PublishVersion"""
import os, json
from datetime import datetime
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.scf import scf_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = scf_client.ScfClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.PublishVersionRequest()
        req.FunctionName = os.environ.get("FUNCTION_NAME")
        req.Namespace = os.environ.get("NAMESPACE", "default")
        req.Description = f"Published {datetime.utcnow().isoformat()}Z"

        resp = client.PublishVersion(req)
        print(resp.to_json_string())
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

---

## §5 Operation: CreateAlias

### CLI (Primary Path)

```bash
tccli scf CreateAlias \
  --FunctionName "{{user.function_name}}" \
  --Name "{{user.alias_name}}" \
  --FunctionVersion "{{user.version}}" \
  --Namespace "{{user.namespace}}" \
  --Description "Alias for {{user.alias_name}} environment" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

### Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
"""SDK fallback: SCF CreateAlias"""
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.scf import scf_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = scf_client.ScfClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.CreateAliasRequest()
        req.FunctionName = os.environ.get("FUNCTION_NAME")
        req.Name = os.environ.get("ALIAS_NAME")
        req.FunctionVersion = os.environ.get("FUNCTION_VERSION", "$LATEST")
        req.Namespace = os.environ.get("NAMESPACE", "default")

        resp = client.CreateAlias(req)
        print(resp.to_json_string())
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

---

## §6 Operation: CreateTrigger

### CLI — Timer Trigger (Primary Path)

```bash
# Create timer trigger (cron expression)
tccli scf CreateTrigger \
  --FunctionName "{{user.function_name}}" \
  --TriggerName "{{user.trigger_name}}" \
  --Type "timer" \
  --TriggerDesc '{"cron": "0 */2 * * * *"}' \
  --Enable "OPEN" \
  --Namespace "{{user.namespace}}" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

### CLI — COS Trigger (Primary Path)

```bash
# Create COS bucket trigger
tccli scf CreateTrigger \
  --FunctionName "{{user.function_name}}" \
  --TriggerName "{{user.trigger_name}}" \
  --Type "cos" \
  --TriggerDesc '{"bucketUrl": "mybucket-example.cos.{{env.TENCENTCLOUD_REGION}}.myqcloud.com", "event": "cos:ObjectCreated:*", "filter": {"Prefix": "uploads/", "Suffix": ".jpg"}}' \
  --Enable "OPEN" \
  --Namespace "{{user.namespace}}" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

### Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
"""SDK fallback: SCF CreateTrigger"""
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.scf import scf_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = scf_client.ScfClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.CreateTriggerRequest()
        req.FunctionName = os.environ.get("FUNCTION_NAME")
        req.TriggerName = os.environ.get("TRIGGER_NAME")
        req.Type = os.environ.get("TRIGGER_TYPE")
        req.Namespace = os.environ.get("NAMESPACE", "default")
        req.Enable = "OPEN"

        # TriggerDesc varies by type
        trigger_type = os.environ.get("TRIGGER_TYPE")
        if trigger_type == "timer":
            req.TriggerDesc = '{"cron": "0 */2 * * * *"}'
        elif trigger_type == "cos":
            req.TriggerDesc = '{"bucketUrl": "...", "event": "cos:ObjectCreated:*"}'

        resp = client.CreateTrigger(req)
        print(resp.to_json_string())
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

---

## §7 Operation: GetFunctionLogs

### CLI (Primary Path)

```bash
# Get recent function logs
tccli scf GetFunctionLogs \
  --FunctionName "{{user.function_name}}" \
  --Namespace "{{user.namespace}}" \
  --Limit 100 \
  --Order "DESC" \
  --Region {{env.TENCENTCLOUD_REGION}}

# Filter by request ID
tccli scf GetFunctionLogs \
  --FunctionName "{{user.function_name}}" \
  --Namespace "{{user.namespace}}" \
  --FunctionRequestId "{{user.request_id}}" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

### Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
"""SDK fallback: SCF GetFunctionLogs"""
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.scf import scf_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = scf_client.ScfClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.GetFunctionLogsRequest()
        req.FunctionName = os.environ.get("FUNCTION_NAME")
        req.Namespace = os.environ.get("NAMESPACE", "default")
        req.Limit = int(os.environ.get("LIMIT", "100"))
        req.Order = os.environ.get("ORDER", "DESC")

        request_id = os.environ.get("REQUEST_ID")
        if request_id:
            req.FunctionRequestId = request_id

        resp = client.GetFunctionLogs(req)
        for log in resp.Data:
            print(f"{log.StartTime} - {log.FunctionName} - {log.Log}")
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

---

## §8 Operation: CreateLayer

### CLI (Primary Path)

```bash
# Create a new layer version
tccli scf CreateLayer \
  --LayerName "{{user.layer_name}}" \
  --LayerZipUri "{{user.zip_file_path}}" \
  --Description "Layer version $(date -u +%Y-%m-%d)" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

### Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
"""SDK fallback: SCF CreateLayer"""
import os, json, base64
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.scf import scf_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = scf_client.ScfClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.CreateLayerRequest()
        req.LayerName = os.environ.get("LAYER_NAME")
        req.LayerZipUri = os.environ.get("ZIP_FILE_PATH")
        req.Description = f"Layer version"

        resp = client.CreateLayer(req)
        print(resp.to_json_string())
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

### Post-execution Validation

1. Read new layer version from `$.Response.LayerVersion`
2. Verify layer exists via ListLayers

---

## §9 Operation: DeleteLayerVersion

### Pre-flight (Safety Gate)

- **MUST** enumerate functions using this layer version via `ListLayerVersions` and `GetFunction`
- **MUST** warn: deleting a layer version will cause functions using it to fail on next cold start
- **MUST** obtain explicit confirmation

### CLI (Primary Path)

```bash
# Delete a specific layer version
tccli scf DeleteLayerVersion \
  --LayerName "{{user.layer_name}}" \
  --LayerVersion "{{user.version}}" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

### Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
"""SDK fallback: SCF DeleteLayerVersion"""
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.scf import scf_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = scf_client.ScfClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.DeleteLayerVersionRequest()
        req.LayerName = os.environ.get("LAYER_NAME")
        req.LayerVersion = int(os.environ.get("LAYER_VERSION"))

        resp = client.DeleteLayerVersion(req)
        print(resp.to_json_string())
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

### Post-execution Validation

1. Verify layer version no longer appears in ListLayerVersions

---

## Pre-flight Check Commands

### Verify CLI and Credentials

```bash
# Check CLI is installed and credentials are set
tccli scf ListFunctions --Region {{env.TENCENTCLOUD_REGION}} --Namespace default --Limit 1
```

### Check Function Exists

```bash
# Check if function name is available (expect ResourceNotFound = available)
tccli scf GetFunction \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --FunctionName "{{user.function_name}}" \
  --Namespace "{{user.namespace}}"
```

### Check Zip File Size

```bash
# Verify zip file exists and size < 500MB
test -f "{{user.zip_file_path}}" && stat -f%z "{{user.zip_file_path}}" | awk '{if ($1 < 524288000) exit 0; else exit 1}'
```
