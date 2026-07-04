# CDB SDK Templates

Common boilerplate used by SDK blocks in `SKILL.md`. Each operation block imports from here instead of duplicating every time.

## Common Initialization

```python
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cdb.v20170320 import cdb_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = cdb_client.CdbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
```

## Try-Except Wrapper

```python
def main():
    try:
        # ... operation code ...
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

## Polling Helper

```python
import time

def poll_task(client, async_request_id, timeout=300, interval=5):
    start = time.time()
    req = models.DescribeAsyncRequestInfoRequest()
    req.AsyncRequestId = async_request_id
    while time.time() - start < timeout:
        resp = client.DescribeAsyncRequestInfo(req)
        status = resp.Status  # RUNNING/SUCCESS/FAILED
        if status == "SUCCESS":
            return resp
        if status == "FAILED":
            raise Exception(f"Task failed: {resp.Message}")
        time.sleep(interval)
    raise TimeoutError(f"Task did not complete within {timeout}s")
```