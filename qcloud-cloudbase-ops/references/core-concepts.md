# CloudBase Core Concepts

## Architecture Overview

CloudBase (云开发, TCB) is a unified serverless platform for web and mini-program backends.

```
┌─────────────────────────────────────────────────────┐
│                  CloudBase Platform                  │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ Cloud Database│  │ Cloud Storage │  │Cloud Fn │ │
│  │ (MongoDB)    │  │   (COS)      │  │(hosted)  │ │
│  └──────────────┘  └──────────────┘  └──────────┘ │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │Static Hosting │  │  Auth/Domain │  │API Keys  │ │
│  │              │  │   Whitelist   │  │          │ │
│  └──────────────┘  └──────────────┘  └──────────┘ │
└─────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
    Tencent Cloud                     Web / Mini-Program
    COS + CVM + VPC                   Endpoints
```

## Environment (核心资源)

| Concept | Description |
|---------|-------------|
| **Environment (环境)** | Primary resource container — isolated unit with its own database, storage, functions, hosting |
| **EnvId** | Unique identifier — `env-xxxxxxxx` format |
| **EnvName** | User-defined name |
| **Status** | `0`=正常(RUNNING), `-1`=未初始化, `-2`=删除中 |

## Cloud Database

- **Type:** MongoDB-compatible document database
- **ACL Modes:** `admin` / `readOnly` / `writeOnly` / `none` (admin only)
- **Billing:** Included in environment package; additional reads/writes billed via resource points

## Cloud Storage

- Backed by COS (object storage)
- File path: `/path/to/file`
- Operations: upload, download, delete, list
- Access via SDK or REST API within environment context

## Cloud Functions (CloudBase-hosted)

- **Not** the same as standalone SCF — managed through CloudBase APIs
- Triggered by database events, HTTP requests, timers
- Integrated with CloudBase authentication

## Static Hosting

- Deploy static websites (HTML, CSS, JS, images)
- Custom domain binding via `CreateHostingDomain`
- Build service: `DescribeCloudBaseBuildService`
- CDN-accelerated

## Billing Model

### Resource Point Billing (新模式)

- Single "resource point" for all consumption (DB reads/writes, function executions, CDN traffic, storage)
- Standard: 1000 points = 1 CNY
- Deduction order: package → resource package (1-year validity) → pay-as-you-go

### Supported Metrics (DescribeCurveData)

| MetricName | Unit | Description |
|-----------|------|-------------|
| `FunctionCallCount` | count | Function invocations |
| `FunctionRunDuration` | ms | Function execution time |
| `DatabaseDiskUsage` | MB | Database storage used |
| `DatabaseReads` | count | Database read operations |
| `DatabaseWrites` | count | Database write operations |
| `StorageCapacity` | MB | Storage used |
| `CdnTraffic` | MB | CDN outbound traffic |
| `cdnBandwidth` | Mbps | CDN bandwidth |

## Limits and Quotas

| Resource | Limit | Notes |
|---------|-------|-------|
| Environments per account | 5 (personal) / 10+ (enterprise) | Varies by plan |
| Collections per env | Unlimited (practical limit ~1000) | |
| Storage per env | Based on package (10GB–unlimited) | |
| Auth domains per env | 50 | |
| API keys per account | 10 | |
| Static hosting domains per env | 10 | |

## Security Model

### Auth Domains (安全域名白名单)

- Browser-only access allowed for whitelisted domains
- Prevents XSS attacks from unknown origins
- Types: `web` (browser), `qiniu` (Qiniu CDN)

### Database ACL (数据库权限)

- Per-collection permission control
- Four modes: admin / readOnly / writeOnly / none
- Default: admin (all-access for editors)

### API Keys

- Used for CloudBase REST API authentication
- SecretKey shown **only once** at creation
- Manage via `DescribeApiKeyLists`, `CreateApiKey`, `DeleteApiKey`

## Related Products

| Product | Relationship | Delegation |
|---------|-------------|------------|
| SCF | CloudBase hosts functions differently from standalone SCF | Use CloudBase APIs, not `qcloud-scf-ops` |
| COS | CloudBase storage backed by COS | `qcloud-cos-ops` for direct COS ops |
| CAM | CloudBase uses CAM for permissions | `qcloud-cam-ops` for policy management |
| Monitor | CloudBase metrics via DescribeCurveData | `qcloud-monitor-ops` for alarm policies |

## References

- [CloudBase API Docs](https://cloud.tencent.com/document/api/876/36418)
- [CloudBase Console](https://console.cloud.tencent.com/tcb)
- [Billing Overview](https://cloud.tencent.com/document/product/876/56375)
