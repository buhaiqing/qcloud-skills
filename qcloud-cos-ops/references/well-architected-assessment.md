# COS Well-Architected Assessment

## Four Pillars

### Reliability (可靠性)

| Requirement | Implementation |
|-------------|---------------|
| Cross-region replication | Configure replication rules |
| Versioning | Enable versioning for backup |
| Lifecycle backup | Archive objects automatically |

### Security (安全性)

| Requirement | Implementation |
|-------------|---------------|
| ACL policies | Configure bucket/object ACL |
| Encryption | Enable server-side encryption |
| Access logging | Enable COS logging |

### Cost (成本)

| Requirement | Implementation |
|-------------|---------------|
| Storage tier optimization | Lifecycle rules to ARCHIVE |
| Idle bucket detection | Monitor bucket access |
| Cost comparison | STANDARD vs ARCHIVE costs |

### Efficiency (效率)

| Requirement | Implementation |
|-------------|---------------|
| Multipart upload | Use coscmd for large files |
| Batch operations | SDK batch delete |
| CDN integration | Static website + CDN |

## Cost Comparison

| Storage Class | 30 Days | 90 Days | 365 Days |
|---------------|---------|---------|----------|
| STANDARD | ¥0.118/GB | ¥3.54/GB | ¥14.36/GB |
| STANDARD_IA | ¥0.08/GB | ¥2.4/GB | ¥9.72/GB |
| ARCHIVE | ¥0.033/GB | ¥0.99/GB | ¥4.03/GB |

## CAM Policy

```json
{
  "version": "2.0",
  "statement": [
    {
      "action": [
        "cos:GetObject",
        "cos:PutObject",
        "cos:DeleteObject"
      ],
      "effect": "allow",
      "resource": "qcs::cos:*:*:bucket-xxx/*"
    }
  ]
}
```

## References

- [COS Well-Architected](https://cloud.tencent.com/document/product/436)