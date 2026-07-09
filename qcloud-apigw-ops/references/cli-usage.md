# API Gateway CLI Usage

Verified `tccli apigateway` commands (API version 2018-08-08).

## Service

```bash
# List services
tccli apigateway DescribeServicesStatus --Region "{{env.TENCENTCLOUD_REGION}}"

# Create service
tccli apigateway CreateService --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ServiceName "my-svc" --Protocol "http&https" --ServiceDesc "prod"

# Delete service (keep verification ON)
tccli apigateway DeleteService --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ServiceId "service-xxx" --SkipVerification 0
```

## API

```bash
# Create API
tccli apigateway CreateApi --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ServiceId "service-xxx" --ServiceType "http" --ServiceTimeout 15 \
  --Protocol "HTTP" --ApiName "hello" --AuthType "NONE" \
  --RequestConfig '{"Path":"/hello","Method":"GET"}' \
  --ServiceConfig '{"Product":"clb","BackendType":"HTTP","Url":"/","Method":"GET"}'

# Delete API
tccli apigateway DeleteApi --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ServiceId "service-xxx" --ApiId "api-xxx"
```

## Release / Environment

```bash
tccli apigateway ReleaseService --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ServiceId "service-xxx" --EnvironmentName "release" --ReleaseDesc "v1.0"
tccli apigateway UnReleaseService --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ServiceId "service-xxx" --EnvironmentName "release"
```

## Usage Plan + Secret + Environment

```bash
tccli apigateway CreateUsagePlan --Region "{{env.TENCENTCLOUD_REGION}}" \
  --UsagePlanName "plan-100qps" --MaxRequestNum 1000000 --MaxRequestNumPreSec 100
tccli apigateway BindSecretIds --Region "{{env.TENCENTCLOUD_REGION}}" \
  --UsagePlanId "usagePlan-xxx" --AccessKeyIds '["ak-xxx"]'
tccli apigateway BindEnvironment --Region "{{env.TENCENTCLOUD_REGION}}" \
  --UsagePlanIds '["usagePlan-xxx"]' --BindType "SERVICE" \
  --Environment "release" --ServiceId "service-xxx"
```

## Custom Domain

```bash
tccli apigateway BindSubDomain --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ServiceId "service-xxx" --SubDomain "api.example.com" --Protocol "https" \
  --NetType "OUTER" --IsDefaultMapping true --NetSubDomain "api.example.com" \
  --CertificateId "{{user.certificate_id}}"
```

> All commands use `--Region` from `{{env.TENCENTCLOUD_REGION}}`. Output is JSON by default.
> Complex `RequestConfig` / `ServiceConfig` are passed as inline JSON strings.
