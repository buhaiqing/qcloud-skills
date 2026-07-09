# API Gateway Integration

## Upstream / backend delegation

| Need | Delegate to |
|---|---|
| SCF function as backend | `qcloud-scf-ops` (function code/logic) |
| CVM/container backend | `qcloud-cvm-ops`, `qcloud-tke-ops` |
| Layer-4/7 ingress routing | `qcloud-clb-ops` |
| CAM policy for gateway roles | `qcloud-cam-ops` |
| TLS certificate for custom domain | `qcloud-ssl-ops` |
| Metrics / alarms | `qcloud-monitor-ops` |

## Handoff payload (cross-skill)

When another skill needs to reference an API Gateway endpoint:

```json
{
  "skill": "qcloud-apigw-ops",
  "service_id": "{{output.service_id}}",
  "api_id": "{{output.api_id}}",
  "environment": "{{user.environment}}",
  "endpoint": "https://{{user.sub_domain}}/hello"
}
```

## Cross-skill trigger

If a request mentions function/business logic or LB routing, hand off to the owning skill and
keep only the API Gateway resource management in scope.
