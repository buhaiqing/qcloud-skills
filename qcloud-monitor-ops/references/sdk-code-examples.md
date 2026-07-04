# Monitor SDK Code Examples

## Get Monitor Data

```python
#!/usr/bin/env python3
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.monitor.v20180724 import monitor_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = monitor_client.MonitorClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.GetMonitorDataRequest()
        req.Namespace = "{{user.namespace}}"
        req.MetricName = "{{user.metric_name}}"

        dimension = models.Dimension()
        dimension.Name = "{{user.dimension_name}}"
        dimension.Value = "{{user.dimension_value}}"
        req.Dimensions = [dimension]

        req.StartTime = "2026-05-20T00:00:00+08:00"
        req.EndTime = "2026-05-21T00:00:00+08:00"
        req.Period = 300

        resp = client.GetMonitorData(req)
        print(json.dumps(resp.to_json_string(), indent=2))

    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

## Delete Alarm Policy

```python
#!/usr/bin/env python3
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.monitor.v20180724 import monitor_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = monitor_client.MonitorClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.DeleteAlarmPolicyRequest()
        req.Module = "monitor"
        req.PolicyIds = ["{{user.policy_id}}"]

        resp = client.DeleteAlarmPolicy(req)
        print(json.dumps(resp.to_json_string(), indent=2))

    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```
