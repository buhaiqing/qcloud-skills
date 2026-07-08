# COS API & SDK Usage

## API Reference

Official API: https://cloud.tencent.com/document/api/436

### Bucket Operations

| API | Method | Description | Required Fields |
|-----|--------|-------------|-----------------|
| PutBucket | PUT | Create bucket | `Bucket` |
| GetBucket | GET | List objects | `Bucket` |
| HeadBucket | HEAD | Check bucket existence | `Bucket` |
| DeleteBucket | DELETE | Delete empty bucket | `Bucket` |
| PutBucketACL | PUT | Set bucket ACL | `Bucket`, `ACL` |
| GetBucketACL | GET | Get bucket ACL | `Bucket` |
| PutBucketPolicy | PUT | Set bucket policy | `Bucket`, `Policy` |
| GetBucketPolicy | GET | Get bucket policy | `Bucket` |
| PutBucketLifecycle | PUT | Set lifecycle rules | `Bucket`, `LifecycleConfiguration` |
| GetBucketLifecycle | GET | Get lifecycle rules | `Bucket` |
| DeleteBucketLifecycle | DELETE | Remove lifecycle rules | `Bucket` |
| PutBucketVersioning | PUT | Enable/suspend versioning | `Bucket`, `Status` |
| GetBucketVersioning | GET | Get versioning status | `Bucket` |

### Object Operations

| API | Method | Description | Required Fields |
|-----|--------|-------------|-----------------|
| PutObject | PUT | Upload object | `Bucket`, `Key`, `Body` |
| GetObject | GET | Download object | `Bucket`, `Key` |
| HeadObject | HEAD | Get object metadata | `Bucket`, `Key` |
| DeleteObject | DELETE | Delete object | `Bucket`, `Key` |
| DeleteObjects | POST | Batch delete | `Bucket`, `Delete` (object list) |
| CopyObject | PUT | Copy object | `Bucket`, `Key`, `CopySource` |
| ListObjects | GET | List objects | `Bucket`, optional `Prefix`, `Delimiter`, `Marker`, `MaxKeys` |
| ListObjectVersions | GET | List object versions | `Bucket` |

### Multipart Upload Operations

| API | Method | Description | Required Fields |
|-----|--------|-------------|-----------------|
| InitiateMultipartUpload | POST | Start multipart upload | `Bucket`, `Key` |
| UploadPart | PUT | Upload part | `Bucket`, `Key`, `UploadId`, `PartNumber`, `Body` |
| CompleteMultipartUpload | POST | Complete upload | `Bucket`, `Key`, `UploadId`, `Parts` |
| AbortMultipartUpload | DELETE | Abort upload | `Bucket`, `Key`, `UploadId` |
| ListParts | GET | List uploaded parts | `Bucket`, `Key`, `UploadId` |
| ListMultipartUploads | GET | List in-progress uploads | `Bucket` |

## Request Parameters

### PutBucket

```json
PUT /?Bucket=my-bucket HTTP/1.1
Host: cos.ap-guangzhou.myqcloud.com

Headers:
  x-cos-acl: private
  x-cos-storage-class: STANDARD
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Bucket | string | Yes | Bucket name (globally unique) |
| x-cos-acl | string | No | private/public-read/public-read-write |
| x-cos-storage-class | string | No | STANDARD/STANDARD_IA/ARCHIVE |

### PutObject

```json
PUT /my-object.txt HTTP/1.1
Host: my-bucket.cos.ap-guangzhou.myqcloud.com
Content-Type: text/plain
Content-Length: 1234
x-cos-storage-class: STANDARD
x-cos-meta-author: ops-team

[Object content bytes]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| Bucket | string | Yes | From Host header |
| Key | string | Yes | Object path (URL path) |
| Body | bytes | Yes | Object content |
| Content-Type | string | Recommended | MIME type |
| x-cos-storage-class | string | No | Storage class |
| x-cos-meta-* | string | No | User metadata |

### ListObjects

```json
GET /?Prefix=logs/&Delimiter=/&Marker=obj100&MaxKeys=100 HTTP/1.1
Host: my-bucket.cos.ap-guangzhou.myqcloud.com
```

| Parameter | Type | Description |
|-----------|------|-------------|
| Prefix | string | Filter by prefix |
| Delimiter | string | Group by delimiter (usually `/`) |
| Marker | string | Pagination marker |
| MaxKeys | int | Max results (default 1000, max 1000) |

## Response Fields

### PutBucket Response

```json
HTTP/1.1 200 OK
x-cos-request-id: NjM...

Headers:
  Location: my-bucket.cos.ap-guangzhou.myqcloud.com
```

| Field | Type | Description |
|-------|------|-------------|
| Location | string | Bucket endpoint URL |

### PutObject Response

```json
HTTP/1.1 200 OK
x-cos-request-id: NjM...

Headers:
  ETag: "d41d8cd98f00b204e9800998ecf8427e"
  x-cos-version-id: MTg0NDY...
```

| Field | Type | Description |
|-------|------|-------------|
| ETag | string | MD5 hash (verify integrity) |
| x-cos-version-id | string | Version ID (if versioning enabled) |

### ListObjects Response

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult>
  <Name>my-bucket</Name>
  <Prefix>logs/</Prefix>
  <Marker></Marker>
  <MaxKeys>1000</MaxKeys>
  <Delimiter>/</Delimiter>
  <IsTruncated>false</IsTruncated>
  <Contents>
    <Key>logs/2026-05-21.log</Key>
    <LastModified>2026-05-21T10:00:00.000Z</LastModified>
    <ETag>"abc123"</ETag>
    <Size>1234</Size>
    <StorageClass>STANDARD</StorageClass>
  </Contents>
  <CommonPrefixes>
    <Prefix>logs/app1/</Prefix>
  </CommonPrefixes>
</ListBucketResult>
```

| Field | Type | Description |
|-------|------|-------------|
| Contents[].Key | string | Object path |
| Contents[].Size | int | Object size (bytes) |
| Contents[].ETag | string | MD5 hash |
| Contents[].StorageClass | string | Storage class |
| IsTruncated | boolean | More results available |
| NextMarker | string | Pagination continuation |

## Pagination

### Marker-based Pagination

```python
marker = None
all_objects = []

while True:
    req = models.ListObjectsRequest()
    req.Bucket = bucket_name
    req.Marker = marker
    req.MaxKeys = 1000
    
    resp = client.ListObjects(req)
    all_objects.extend(resp.Contents)
    
    if not resp.IsTruncated:
        break
    marker = resp.NextMarker
```

### MaxKeys Limit

- Default: 1000
- Maximum: 1000
- Use pagination for > 1000 objects

## Python SDK Usage

### Installation

```bash
pip install cos-python-sdk-v5
pip install coscmd
```

### Import

```python
from qcloud_cos import CosConfig, CosS3Client
import os
```

### Create Bucket

```python
def create_bucket(bucket_name, region="ap-guangzhou"):
    config = CosConfig(
        Region=region,
        SecretId=os.environ.get("TENCENTCLOUD_SECRET_ID"),
        SecretKey=os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = CosS3Client(config)
    
    resp = client.create_bucket(Bucket=bucket_name)
    return resp
```

### Upload Object

```python
def upload_object(bucket_name, key, file_path, storage_class="STANDARD"):
    config = CosConfig(
        Region="ap-guangzhou",
        SecretId=os.environ.get("TENCENTCLOUD_SECRET_ID"),
        SecretKey=os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = CosS3Client(config)
    
    with open(file_path, 'rb') as f:
        content = f.read()
    
    resp = client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=content,
        StorageClass=storage_class
    )
    return resp['ETag']
```

### Download Object

```python
def download_object(bucket_name, key, local_path):
    config = CosConfig(
        Region="ap-guangzhou",
        SecretId=os.environ.get("TENCENTCLOUD_SECRET_ID"),
        SecretKey=os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = CosS3Client(config)
    
    resp = client.get_object(Bucket=bucket_name, Key=key)
    
    with open(local_path, 'wb') as f:
        f.write(resp['Body'].get_raw_stream().read())
    
    return resp['ETag']
```

### List Objects

```python
def list_objects(bucket_name, prefix=""):
    config = CosConfig(
        Region="ap-guangzhou",
        SecretId=os.environ.get("TENCENTCLOUD_SECRET_ID"),
        SecretKey=os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = CosS3Client(config)
    
    resp = client.list_objects(
        Bucket=bucket_name,
        Prefix=prefix,
        MaxKeys=1000
    )
    
    contents = resp.get('Contents', [])
    return [(obj['Key'], obj['Size'], obj['StorageClass']) for obj in contents]
```

### Set Lifecycle

```python
def set_lifecycle(bucket_name, region="ap-guangzhou"):
    config = CosConfig(
        Region=region,
        SecretId=os.environ.get("TENCENTCLOUD_SECRET_ID"),
        SecretKey=os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = CosS3Client(config)
    
    resp = client.put_bucket_lifecycle(
        Bucket=bucket_name,
        LifecycleConfiguration={
            "Rule": [
                {
                    "ID": "archive-logs",
                    "Status": "Enabled",
                    "Filter": {"Prefix": "logs/"},
                    "Transition": {"Days": 30, "StorageClass": "ARCHIVE"}
                }
            ]
        }
    )
    return resp
```

## coscmd Tool

### Installation

```bash
pip install coscmd
coscmd config -a <secret_id> -s <secret_key> -b <bucket_name> -r <region>
```

### Upload Commands

```bash
# Simple upload
coscmd upload local.txt /bucket/remote.txt

# Multipart upload (>5GB)
coscmd upload --multipart large.mp4 /bucket/videos/large.mp4

# Sync directory
coscmd upload -r /local/dir/ /bucket/remote-dir/

# Multi-thread upload
coscmd upload --max-thread 10 large.zip /bucket/large.zip
```

### Download Commands

```bash
# Download file
coscmd download /bucket/remote.txt ./local.txt

# Download directory
coscmd download -r /bucket/remote-dir/ ./local-dir/
```

### Delete Commands

```bash
# Delete object
coscmd delete /bucket/remote.txt

# Delete directory
coscmd delete -r /bucket/remote-dir/

# Batch delete (use SDK for batch)
```

### List Commands

```bash
# List all objects
coscmd list bucket_name

# List with prefix
coscmd list bucket_name -p logs/

# List all (recursive)
coscmd list bucket_name -a
```

## Error Handling

```python
try:
    resp = client.PutObject(req)
except TencentCloudSDKException as err:
    if err.code == "EntityTooLarge":
        print("Use multipart upload for >5GB files")
    elif err.code == "NoSuchBucket":
        print("Create bucket first")
    elif err.code == "InvalidDigest":
        print("File corrupted - verify content")
```

## References

- [COS API](https://cloud.tencent.com/document/api/436)
- [Python SDK](https://cloud.tencent.com/document/sdk/Python)
- [coscmd Tool](https://cloud.tencent.com/document/product/436/10976)