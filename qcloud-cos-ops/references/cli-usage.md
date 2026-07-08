# COS CLI Usage

> **Path policy (verified):** Tencent Cloud has **no** `tccli cos` service. COS object operations use the **coscmd** CLI; bucket/lifecycle/ACL/versioning operations use the **Python SDK** (`cos-python-sdk-v5`, module `qcloud_cos`). Do not emit `tccli cos ...` commands — they are not valid.

## coscmd vs Python SDK

| Tool | Primary Use | Installation |
|------|-------------|--------------|
| coscmd | Object operations (Upload/Download/List/Delete/Copy) | `pip install coscmd` |
| Python SDK (`qcloud_cos`) | Bucket ops, lifecycle, ACL, versioning, multipart, batch delete | `pip install cos-python-sdk-v5` |

**Recommendation:** Use coscmd for interactive object operations; use the Python SDK for bucket management, lifecycle, ACL, and any automated/programmatic flow.

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

| Operation | coscmd | Python SDK (`qcloud_cos`) |
|-----------|--------|----------------------------------|
| CreateBucket | — | ✓ |
| DeleteBucket | — | ✓ |
| ListBuckets | — | ✓ |
| UploadObject | ✓ | ✓ |
| DownloadObject | ✓ | ✓ |
| ListObjects | ✓ | ✓ |
| DeleteObject | ✓ | ✓ |
| BatchDelete | — | ✓ |
| MultipartUpload | ✓ | ✓ |
| SetLifecycle | — | ✓ |
| SetBucketPolicy | — | ✓ |
| SetBucketACL | — | ✓ |
| SetObjectACL | ✓ | ✓ |

**Note:** Bucket-level operations (create/delete/list buckets, lifecycle, ACL, policy, versioning) are **SDK-only**; coscmd covers object-level operations only. Batch delete requires the Python SDK.

## jq Parsing Patterns

```bash
# coscmd does not emit JSON; parse its text output for object counts
OBJECT_COUNT=$(coscmd list bucket | wc -l)

# ETag is returned by the Python SDK response (resp.ETag), not coscmd stdout
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