# COS Core Concepts

## Architecture Overview

Tencent Cloud COS (Cloud Object Storage) provides a distributed object storage service for storing and retrieving any amount of data, anytime, from anywhere.

### Key Components

| Component | Description | Limits |
|-----------|-------------|--------|
| **Bucket** | Container for objects | 200 per account (default) |
| **Object** | File + metadata stored in bucket | No size limit (5TB per object) |
| **Storage Class** | STANDARD/STANDARD_IA/ARCHIVE | Per object |
| **ACL** | Access control (private/public/read) | Per bucket/object |
| **Bucket Policy** | JSON policy for fine-grained access | Per bucket |
| **Lifecycle Rule** | Auto-tier/delete rules | 1000 per bucket |
| **Versioning** | Object version history | Per bucket |
| **Cross-region Replication** | Backup to another region | Per bucket |

## Bucket Naming Rules

### RFC 952 Naming Convention

| Rule | Example |
|------|---------|
| Lowercase only | `my-bucket-123` ✓ |
| No underscore | `my_bucket` ✗ |
| Start with letter/number | `abc-123` ✓ |
| Length: 3-63 chars | ✓ |
| Globally unique | Must be unique across all accounts |
| No IP address format | `192.168.1.1` ✗ |
| Valid chars: a-z, 0-9, hyphen | ✓ |

**Naming Pattern:**
```
<app-name>-<env>-<region>-<random-id>
Example: myapp-prod-gz-12345
```

## Storage Classes

### Class Comparison

| Class | Name | Min Storage Duration | Retrieval Time | Cost Factor |
|-------|------|---------------------|----------------|-------------|
| STANDARD | 标准存储 | No minimum | Real-time | 1.0x |
| STANDARD_IA | 低频存储 | 30 days | Real-time | 0.5x |
| ARCHIVE | 影归存储 | 60 days | Minutes to hours | 0.1x |
| DEEP_ARCHIVE | 深度归档 | 180 days | Hours to days | 0.05x |

### Cost Optimization

```
Hot data (< 30 days) → STANDARD
Infrequent access (30-180 days) → STANDARD_IA
Archive (> 180 days) → ARCHIVE or DEEP_ARCHIVE
```

## Regions and Endpoints

### Bucket Endpoint Format

```
https://<bucket-name>.cos.<region>.myqcloud.com
```

### Supported Regions

| Region | Code | Endpoint Domain |
|--------|------|-----------------|
| 广州 | `ap-guangzhou` | cos.ap-guangzhou.myqcloud.com |
| 上海 | `ap-shanghai` | cos.ap-shanghai.myqcloud.com |
| 北京 | `ap-beijing` | cos.ap-beijing.myqcloud.com |
| 成都 | `ap-chengdu` | cos.ap-chengdu.myqcloud.com |
| 重庆 | `ap-chongqing` | cos.ap-chongqing.myqcloud.com |
| 香港 | `ap-hongkong` | cos.ap-hongkong.myqcloud.com |
| 新加坡 | `ap-singapore` | cos.ap-singapore.myqcloud.com |
| 东京 | `ap-tokyo` | cos.ap-tokyo.myqcloud.com |
| 美东 | `na-ashburn` | cos.na-ashburn.myqcloud.com |
| 美西 | `na-siliconvalley` | cos.na-siliconvalley.myqcloud.com |
| 欧洲 | `eu-frankfurt` | cos.eu-frankfurt.myqcloud.com |

## Object Metadata

### System Metadata

| Metadata | Description |
|----------|-------------|
| `Content-Type` | MIME type (e.g., image/jpeg) |
| `Content-Length` | Object size in bytes |
| `ETag` | MD5 hash of content |
| `Last-Modified` | Modification timestamp |
| `Storage-Class` | STANDARD/STANDARD_IA/ARCHIVE |
| `x-cos-version-id` | Version ID (if versioning enabled) |

### User Metadata

Custom headers prefixed with `x-cos-meta-`:
```
x-cos-meta-author: ops-team
x-cos-meta-project: myapp
x-cos-meta-backup-date: 2026-05-21
```

## Access Control

### ACL Types

| ACL | Access Level |
|-----|--------------|
| `private` | Owner only (default) |
| `public-read` | Anyone can read |
| `public-read-write` | Anyone can read/write |
| `authenticated-read` | Authenticated users |

### Bucket Policy Structure

```json
{
  "version": "2.0",
  "statement": [
    {
      "action": [
        "cos:GetObject",
        "cos:PutObject"
      ],
      "effect": "allow",
      "principal": {
        "qcs": ["qcs::cam::uin/123456:root"]
      },
      "resource": ["qcs::cos:ap-guangzhou:uid/123456:bucket-xxx/*"],
      "condition": {}
    }
  ]
}
```

## Lifecycle Management

### Rule Structure

```json
{
  "ID": "archive-rule",
  "Status": "Enabled",
  "Filter": {
    "Prefix": "logs/"
  },
  "Transition": {
    "Days": 30,
    "StorageClass": "ARCHIVE"
  },
  "Expiration": {
    "Days": 365
  },
  "NoncurrentVersionExpiration": {
    "NoncurrentDays": 30
  }
}
```

### Lifecycle Scenarios

| Scenario | Rules |
|----------|-------|
| Log archiving | Transition logs/ to ARCHIVE after 30 days |
| Temp file cleanup | Delete temp/ after 7 days |
| Backup retention | Keep backups/ for 365 days, then delete |
| Version cleanup | Delete old versions after 30 days |

## Versioning

### Versioning States

| State | Behavior |
|-------|----------|
| Enabled | All versions retained |
| Suspended | New versions not created, old kept |
| Disabled | No versioning (default) |

### Version ID

- Each upload creates new version ID
- Delete without version ID creates delete marker
- Retrieve specific version by `versionId` parameter

## Multipart Upload

### Upload Flow

```
1. InitiateMultipartUpload → get UploadId
2. UploadPart (multiple, each ≤ 5GB) → get ETag per part
3. CompleteMultipartUpload → combine parts
```

### Chunk Size Guidelines

| File Size | Chunk Size |
|-----------|------------|
| 100MB - 1GB | 10MB |
| 1GB - 5GB | 50MB |
| 5GB - 50GB | 100MB |
| > 50GB | 200MB |

### Resumable Upload

```bash
coscmd upload --multipart --max-thread 10 large-file.mp4 /bucket/videos/large.mp4
```

## Cross-region Replication

### Replication Rules

| Source Region | Destination | Use Case |
|---------------|-------------|----------|
| ap-guangzhou | ap-shanghai | DR backup |
| ap-beijing | ap-hongkong | Hybrid cloud |
| na-ashburn | eu-frankfurt | Global distribution |

### Replication Metrics

| Metric | Description |
|--------|-------------|
| PendingReplicationBytes | Bytes not yet replicated |
| ReplicationLatency | Time lag between regions |

## Quotas and Limits

### Default Limits

| Resource | Limit | Adjustable |
|----------|-------|------------|
| Buckets per account | 200 | Yes (max 1000) |
| Objects per bucket | No limit | — |
| Object size | 5TB per object | — |
| Lifecycle rules per bucket | 1000 | — |
| Multipart upload parts | 10000 | — |
| Upload concurrency | 1000 per bucket | — |

## CDN Integration

### CDN Acceleration

```
Origin: https://bucket.cos.region.myqcloud.com
CDN Domain: https://bucket-xxx.cdn.dnsv1.com
```

### CDN Use Cases

| Scenario | CDN Configuration |
|----------|-------------------|
| Static website | Full-site acceleration |
| Image hosting | Image optimization |
| Video streaming | Media acceleration |
| File download | Download acceleration |

## Static Website Hosting

### Configuration

```json
{
  "IndexDocument": {
    "Suffix": "index.html"
  },
  "ErrorDocument": {
    "Key": "error.html"
  }
}
```

### Website Endpoint

```
https://<bucket-name>.cos-website.<region>.myqcloud.com
```

## Design Patterns

### Backup Architecture

```
Source Bucket (STANDARD)
    ↓ Lifecycle Rule (30 days)
Archive Bucket (ARCHIVE)
    ↓ Cross-region Replication
DR Bucket (another region)
```

### Data Lake Pattern

```
Raw Data Layer (STANDARD)
    ↓ ETL Processing
Processed Layer (STANDARD_IA)
    ↓ Analytics
Analytics Layer (STANDARD)
```

## References

- [COS Documentation](https://cloud.tencent.com/document/product/436)
- [Storage Classes](https://cloud.tencent.com/document/product/436/32810)
- [Bucket Naming](https://cloud.tencent.com/document/product/436/13322)