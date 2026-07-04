# SCF Integration

> SCF integration patterns with other Tencent Cloud services.

## Common Integrations

| Service | Trigger Type | Use Case |
|---------|--------------|----------|
| API Gateway | HTTP trigger | REST API endpoints |
| COS | COS trigger | File processing on upload |
| CKafka | CKafka trigger | Event stream processing |
| Timer | Timer trigger | Scheduled batch jobs |
| CLS | Log trigger | Log analysis pipeline |

## API Gateway Integration

Deploy SCF as HTTP backend:
1. Create API Gateway API via `qcloud-apigw-ops`
2. Configure SCF as backend: `tccli apigw CreateApi --ServiceType SCF`
3. Set request method and path mapping

## COS Integration

Process files on COS upload:

```bash
tccli scf CreateTrigger --FunctionName my-func --TriggerName cos-trigger --TriggerType COS --TriggerDesc '{"bucket":"my-bucket.cos.ap-guangzhou.myqcloud.com","filter":{"Prefix":"","Suffix":".log"}}'
```

## See also
- [Core Concepts](core-concepts.md)
- [CLI Usage](cli-usage.md)
