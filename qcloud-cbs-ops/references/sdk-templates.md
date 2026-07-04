# CBS SDK Templates

Common boilerplate for Python SDK fallback blocks in `SKILL.md`. Each operation's Execution — Python SDK section references these instead of repeating 25+ lines of identical init code.

## Common Init

```python
#!/usr/bin/env python3
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cbs import cbs_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = cbs_client.CbsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        # === REQUEST-SPECIFIC LINES BELOW ===

        resp = client.<Operation>(req)
        result = json.loads(resp.to_json_string())
        print(json.dumps(result, indent=2))
        # === CAPTURE OUTPUT BELOW ===
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

## Polling Helper (state check loop)

```bash
for i in $(seq 1 <MAX_RETRIES>); do
  STATE=$(<describe-command> | jq -r '<STATE_PATH>')
  [ "$STATE" = "<TARGET>" ] && echo "✅ <DESCRIPTION>" && break
  echo "⏳ <PROGRESS_MSG>... current: $STATE"
  sleep <INTERVAL>
done
```

## Try-Except Wrapper (for inline scripts)

```python
try:
    # operation-specific code
except TencentCloudSDKException as err:
    print(f"[ERROR] {err}")
```