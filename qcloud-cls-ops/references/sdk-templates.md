# SDK Templates (Reusable Boilerplate)

> Reference for SKILL.md inline SDK snippets. Import these patterns instead of repeating full credentials/import scaffolding.

## Common Initialization (CLS Client)

```python
import os, json, time
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cls import cls_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = cls_client.ClsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
```

## Polling Helper

```python
def poll_until(client, describe_func, req, status_path, target_status, interval=5, max_wait=120):
    """Poll describe API until target status. Returns (status, elapsed_seconds)."""
    for i in range(max_wait // interval):
        resp = describe_func(req)
        current = json.loads(resp.to_json_string())
        val = current
        for key in status_path.strip("$.").split("."):
            if "[" in key:
                k, idx = key.split("[")
                idx = int(idx.strip("]"))
                val = val[k][idx]
            else:
                val = val[key]
        if val == target_status:
            return val, i * interval
        time.sleep(interval)
    return val, max_wait
```

## Common Try-Except Wrapper

```python
try:
    resp = client.SomeMethod(req)
    result = json.loads(resp.to_json_string())
    print(json.dumps(result, indent=2))
except TencentCloudSDKException as err:
    print(f"[ERROR] {err}")
```

## Usage in SKILL.md

Inline code blocks in SKILL.md SHOULD only contain the request-specific code. Reference this file with:

```
> See [SDK Templates](references/sdk-templates.md) for common init/poll/error boilerplate.
```

SKILL.md inline blocks use `client` and `models` as pre-initialized globals (from this template). If the inline block needs polling, include a `poll_until(...)` call.