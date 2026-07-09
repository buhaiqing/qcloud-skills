# API Gateway API & SDK Usage

Dual-path execution. `tccli apigateway` is primary; `tencentcloud-sdk-python` is the fallback
for operations the CLI does not expose or for programmatic batch work.

## SDK module

```python
from tencentcloud.apigateway import apigateway_client, models
from tencentcloud.common import credential
```

## Coverage map

| Operation | `tccli` | SDK |
|---|---|---|
| CreateService / DeleteService | ✅ | ✅ |
| CreateApi / DeleteApi / ModifyApi | ✅ | ✅ |
| ReleaseService / UnReleaseService | ✅ | ✅ |
| CreateUsagePlan / BindSecretIds / BindEnvironment | ✅ | ✅ |
| BindSubDomain | ✅ | ✅ |
| Describe* | ✅ | ✅ |

CLI covers all flows in this skill; SDK fallback is documented in
[references/sdk-code-examples.md](sdk-code-examples.md).

## API version

`2018-08-08` (recommended) per `tccli apigateway help`.

## Response envelope

All responses follow `{"Response": {"RequestId": "...", ...}}`. Errors follow
`{"Response": {"Error": {"Code": "...", "Message": "..."}}}`.
