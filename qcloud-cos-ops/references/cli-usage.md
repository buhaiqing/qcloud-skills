# COS CLI Usage

## tccli vs coscmd

| Tool | Primary Use | Installation |
|------|-------------|--------------|
| tccli cos | Bucket operations (Create/Delete/List) | `pip install tccli` |
| coscmd | Object operations (Upload/Download/Sync) | `pip install coscmd` |

**Recommendation:** Use tccli for bucket management; use coscmd for object operations.

## tccli cos Commands

### Create Bucket

```bash
tccli cos PutBucket \
  --Bucket "my-bucket-12345" \
  --Region ap-guangzhou
```

**Output:**
```json
{
  "Response": {
    "RequestId": "abc123",
    "Location": "my-bucket-12345.cos.ap-guangzhou.myqcloud.com"
  }
}
```

### List Buckets

```bash
tccli cos GetService
```

### Delete Bucket

```bash
tccli cos DeleteBucket \
  --Bucket "my-bucket-12345" \
  --Region ap-guangzhou
```

**Safety Check:**
```bash
OBJECTS=$(coscmd list my-bucket-12345 | wc -l)
if [ "$OBJECTS" -gt 0 ]; then
  echo "Bucket not empty - cannot delete"
  exit 1
fi
```

### Set Bucket ACL

```bash
tccli cos PutBucketACL \
  --Bucket "my-bucket-12345" \
  --ACL "public-read"
```

### Set Lifecycle

```bash
tccli cos PutBucketLifecycle \
  --Bucket "my-bucket-12345" \
  --LifecycleConfiguration '{"Rule":[{"ID":"archive-rule","Status":"Enabled","Filter":{"Prefix":""},"Transition":{"Days":30,"StorageClass":"ARCHIVE"}}]}'
```

## coscmd Commands

### Configuration

```bash
coscmd config \
  -a "$TENCENTCLOUD_SECRET_ID" \
  -s "$TENCENTCLOUD_SECRET_KEY" \
  -b "my-bucket-12345" \
  -r "ap-guangzhou"
```

### Upload

```bash
coscmd upload local-file.txt /my-bucket-12345/path/file.txt

coscmd upload --multipart large.mp4 /my-bucket-12345/videos/large.mp4

coscmd upload -r /local/dir/ /my-bucket-12345/remote-dir/

coscmd upload --max-thread 10 big-file.zip /my-bucket-12345/big.zip
```

### Download

```bash
coscmd download /my-bucket-12345/path/file.txt ./local-file.txt

coscmd download -r /my-bucket-12345/remote-dir/ ./local-dir/
```

### List

```bash
coscmd list my-bucket-12345

coscmd list my-bucket-12345 -p logs/

coscmd list my-bucket-12345 -a
```

### Delete

```bash
coscmd delete /my-bucket-12345/path/file.txt

coscmd delete -r /my-bucket-12345/remote-dir/
```

## CLI Coverage vs SDK

| Operation | tccli | coscmd | SDK Required |
|-----------|-------|--------|--------------|
| CreateBucket | ✓ | ✓ | No |
| DeleteBucket | ✓ | ✓ | No |
| ListBuckets | ✓ | ✓ | No |
| UploadObject | — | ✓ | No |
| DownloadObject | — | ✓ | No |
| ListObjects | ✓ | ✓ | No |
| DeleteObject | — | ✓ | No |
| BatchDelete | — | — | Yes |
| MultipartUpload | — | ✓ | No |
| SetLifecycle | ✓ | — | No |
| SetBucketPolicy | ✓ | — | No |
| SetBucketACL | ✓ | — | No |
| SetObjectACL | ✓ | ✓ | No |

**Note:** Batch delete requires SDK or multiple coscmd calls.

## jq Parsing Patterns

```bash
VPC_ID=$(tccli cos PutBucket ... | jq -r '.Response.Location')

ETAG=$(coscmd upload ... 2>&1 | grep "ETag" | cut -d'"' -f2)

OBJECT_COUNT=$(coscmd list bucket | wc -l)
```

## Pagination

```bash
for i in 1 2 3; do
  OBJECTS=$(coscmd list bucket --marker "obj$i")
  echo "$OBJECTS"
done
```

## References

- [coscmd Documentation](https://cloud.tencent.com/document/product/436/10976)