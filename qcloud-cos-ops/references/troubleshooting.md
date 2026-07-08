# COS Troubleshooting Guide

## Error Codes

| Code | Meaning | Retry? | Action |
|------|---------|--------|--------|
| `NoSuchBucket` | Bucket not found | No | Verify bucket name |
| `BucketAlreadyExists` | Name already taken | No | Use unique name |
| `AccessDenied` | Permission denied | No | Fix ACL/Policy |
| `InvalidBucketName` | Name invalid | No | RFC 952 naming |
| `QuotaExceeded` | Bucket quota reached | No | Request increase |
| `EntityTooLarge` | Object >5GB | No | Use multipart upload |
| `InvalidDigest` | ETag mismatch | No | Verify content |
| `RequestTimeout` | Upload timeout | Yes (3x) | Use smaller chunks |
| `SignatureDoesNotMatch` | Auth invalid | No | Fix credentials |
| `NoSuchKey` | Object not found | No | Verify key path |
| `InvalidStorageClass` | Unknown class | No | Use STANDARD/ARCHIVE |
| `MalformedXML` | Policy invalid | No | Fix JSON/XML |
| `BucketNotEmpty` | Cannot delete | No | Delete objects first |
| `InvalidRegion` | Region invalid | No | Use valid region |
| `InternalError` | Server error | Yes (3x) | Retry with RequestId |

## Diagnostic Procedures

### Upload Failures

**Step 1: Verify bucket exists**
```bash
coscmd list bucket-name || echo "Bucket not found"
```

**Step 2: Check file size**
```bash
FILE_SIZE=$(stat -f%z local-file.txt)
if [ $FILE_SIZE -gt 5368709120 ]; then
  echo "Use multipart upload for files >5GB"
fi
```

**Step 3: Verify credentials**
```bash
coscmd list bucket-name || echo "Credential error"
```

### Download Failures

**Step 1: Verify object exists**
```bash
coscmd list bucket-name -p path/file.txt
```

**Step 2: Check ACL** (SDK-only — no `tccli cos` service)
```python
from qcloud_cos import CosConfig, CosS3Client

config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
client = CosS3Client(config)
resp = client.get_bucket_acl(Bucket="bucket-name")
print(resp.get("ACL"))
```

### Bucket Creation Failures

**InvalidBucketName:**
- Use lowercase
- No underscore
- Length 3-63 chars
- Globally unique

**BucketAlreadyExists:**
- Add random suffix (bucket-name-12345)

## References

- [COS Errors](https://cloud.tencent.com/document/product/436/32811)