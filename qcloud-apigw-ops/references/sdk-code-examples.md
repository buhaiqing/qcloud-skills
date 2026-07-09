# API Gateway SDK Code Examples

`tencentcloud-sdk-python` fallback for flows whose CLI step you prefer to run programmatically.

## Create Service

```python
#!/usr/bin/env python3
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.apigateway import apigateway_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY"))
        client = apigateway_client.ApigatewayClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.CreateServiceRequest()
        req.ServiceName = os.environ.get("SERVICE_NAME", "my-svc")
        req.Protocol = "http&https"
        resp = client.CreateService(req)
        print(json.dumps(json.loads(resp.to_json_string()), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

## Create API

```python
req = models.CreateApiRequest()
req.ServiceId = os.environ.get("SERVICE_ID")
req.ServiceType = "http"
req.ServiceTimeout = 15
req.Protocol = "HTTP"
req.ApiName = "hello"
req.AuthType = "NONE"
req.RequestConfig = {"Path": "/hello", "Method": "GET"}
req.ServiceConfig = {"Product": "clb", "BackendType": "HTTP", "Url": "/", "Method": "GET"}
resp = client.CreateApi(req)
```

## Release Service

```python
req = models.ReleaseServiceRequest()
req.ServiceId = os.environ.get("SERVICE_ID")
req.EnvironmentName = "release"
req.ReleaseDesc = "v1.0"
resp = client.ReleaseService(req)
```

> Credentials are read from environment only; never print `SecretKey`.
