# SCF Core Concepts

## Architecture Overview

Tencent Serverless Cloud Function (SCF) is a serverless compute service that executes code in response to events without requiring server management.

```
Event Source (Trigger)
    │
    ▼
┌─────────────────────────────┐
│      SCF Platform           │
│  ┌───────────────────────┐  │
│  │   Function Runtime    │  │
│  │   (Container)         │  │
│  │  ┌─────────────────┐  │  │
│  │  │  Function Code  │  │  │
│  │  │  + Handler      │  │  │
│  │  └─────────────────┘  │  │
│  │                         │  │
│  │  + Environment Vars     │  │
│  │  + Layers               │  │
│  │  + VPC (optional)       │  │
│  └───────────────────────┘  │
│                             │
│  CloudWatch Logs ─────────► │
│  Cloud Monitor ──────────►  │
└─────────────────────────────┘
```

## Function Components

### Function Resource Model

| Component | Description | Example |
|-----------|-------------|---------|
| **Function** | The primary resource - code + configuration | `my-handler` |
| **Namespace** | Logical grouping of functions | `default`, `prod`, `dev` |
| **Version** | Immutable snapshot of function code/config | `$LATEST`, `1`, `2`, `3` |
| **Alias** | Named pointer to a version | `prod` → `3`, `dev` → `$LATEST` |
| **Trigger** | Event source that invokes function | Timer, COS, API GW, etc. |
| **Layer** | Shared code/libraries across functions | `numpy-layer`, `common-utils` |

## Runtimes

### Supported Runtimes

| Runtime | Version | Status | Use Case |
|---------|---------|--------|----------|
| **Python** | 3.8, 3.7, 3.6, 2.7 | Recommended | Data processing, ML, automation |
| **Node.js** | 16.13, 14.18, 12.16 | Recommended | Web APIs, real-time processing |
| **Go** | 1.16, 1.14, 1.11 | Supported | High performance, low latency |
| **Java** | 11, 8 | Supported | Enterprise apps, Spring Boot |
| **PHP** | 8.0, 7.4, 7.2 | Supported | Web applications |
| **Custom Runtime** | - | Advanced | Any language (container-based) |

### Runtime Handler Format

| Runtime | Handler Format | Example |
|---------|----------------|---------|
| Python | `file.function` | `index.handler` |
| Node.js | `file.function` | `index.handler` |
| Go | Compiled binary name | `main` |
| Java | `package.class::method` | `com.example.Handler::handleRequest` |
| PHP | `file.function` | `index.handler` |

## Function Lifecycle States

| State | Meaning | Actions Allowed |
|-------|---------|-----------------|
| `Creating` | Function being created | None (wait) |
| `CreateFailed` | Creation failed | Delete, retry Create |
| `Active` | Function ready | Update, Invoke, Publish |
| `Updating` | Configuration/code update in progress | None (wait) |
| `UpdateFailed` | Update failed | Retry Update |
| `Publishing` | Version being published | None (wait) |
| `Deleting` | Function being deleted | None (wait) |

## Triggers (Event Sources)

### Trigger Types

| Trigger | Type Value | Use Case | Invocation Mode |
|---------|------------|----------|-----------------|
| **Timer** | `timer` | Scheduled tasks | Async |
| **COS** | `cos` | Object storage events | Async |
| **API Gateway** | `apigw` | HTTP/REST APIs | Sync/Async |
| **CMQ** | `cmq` | Message queue | Async |
| **Ckafka** | `ckafka` | Kafka events | Async |
| **CLS** | `cls` | Log subscription | Async |
| **CDB** | `cdb` | Database events | Async |

### Timer Trigger (Cron)

```json
{
  "cron": "0 */2 * * * *",
  "timezone": "Asia/Shanghai"
}
```

**Cron Format:** `Seconds Minutes Hours Day Month Week`

| Example | Description |
|---------|-------------|
| `0 */5 * * * *` | Every 5 minutes |
| `0 0 2 * * *` | 2:00 AM daily |
| `0 0 */6 * * *` | Every 6 hours |
| `0 0 0 * * 1` | Every Monday midnight |

### COS Trigger

```json
{
  "bucketUrl": "mybucket-123456.cos.ap-guangzhou.myqcloud.com",
  "event": "cos:ObjectCreated:*",
  "filter": {
    "Prefix": "uploads/",
    "Suffix": ".jpg"
  }
}
```

**COS Events:**
- `cos:ObjectCreated:*` - Object created (upload, copy, post)
- `cos:ObjectCreated:Put` - Put object
- `cos:ObjectCreated:Post` - Post object
- `cos:ObjectCreated:Copy` - Copy object
- `cos:ObjectRemove:*` - Object removed
- `cos:ObjectRemove:Delete` - Delete object

### API Gateway Trigger

API Gateway triggers create RESTful endpoints for functions.

```json
{
  "apiId": "api-xxxxxxxx",
  "serviceId": "service-xxxxxxxx",
  "release": "release"
}
```

## Layers

### Layer Concept

Layers are ZIP archives containing libraries, dependencies, or custom runtimes that can be shared across multiple functions.

**Benefits:**
- Reduce deployment package size
- Share common code/libraries
- Separate dependencies from business logic
- Faster deployments

### Layer Structure

```
layer.zip
├── nodejs/          # For Node.js runtime
│   └── node_modules/
├── python/          # For Python runtime
│   └── lib/
│       └── python3.8/
│           └── site-packages/
├── java/            # For Java runtime
│   └── lib/
└── bin/             # Custom runtime binaries
```

### Layer Constraints

| Constraint | Limit |
|------------|-------|
| Max layer size | 500 MB (compressed) |
| Layers per function | 5 |
| Layer versions per layer | 200 |

## Concurrency and Scaling

### Concurrency Types

| Type | Description | Use Case |
|------|-------------|----------|
| **Reserved Concurrency** | Guaranteed concurrent executions | Protect critical functions from throttling |
| **Provisioned Concurrency** | Pre-warmed execution environments | Eliminate cold start latency |
| **Account Concurrency** | Total concurrency for account | 128,000 default |

### Concurrency Limits

| Resource | Default | Maximum |
|----------|---------|---------|
| Account concurrency | 128,000 | Request increase |
| Reserved per function | 0 | Account limit |
| Provisioned per function | 0 | 10,000 |
| Burst concurrency | 1,000-3,000 | Per region |

### Cold Start vs Warm Start

| Aspect | Cold Start | Warm Start |
|--------|------------|------------|
| **Definition** | First invocation or after idle | Reusing existing execution environment |
| **Latency** | 100ms - 10s (depends on runtime) | < 1ms - 10ms |
| **Causes** | First invoke, code update, concurrency scale, idle timeout | Subsequent invokes to warm container |
| **Mitigation** | Provisioned concurrency, keep-alive pings, smaller packages | N/A (already optimized) |

**Idle Timeout:** Execution environments are kept warm for approximately 5-15 minutes after last invocation.

## Environment Variables

### Built-in Environment Variables

| Variable | Description |
|----------|-------------|
| `TENCENTCLOUD_REGION` | Function deployment region |
| `TENCENTCLOUD_NAMESPACE` | Function namespace |
| `TENCENTCLOUD_FUNCTIONNAME` | Function name |
| `TENCENTCLOUD_FUNCTIONVERSION` | Function version |
| `TENCENTCLOUD_MEMORY` | Memory size in MB |
| `TENCENTCLOUD_TIMEOUT` | Timeout in seconds |
| `TENCENTCLOUD_REQUEST_ID` | Current request ID |

### Custom Environment Variables

- Max 128 variables per function
- Max 4KB total size
- Encrypted at rest
- Can reference Secrets Manager secrets

## Limits and Quotas

### Resource Limits

| Resource | Limit | Notes |
|----------|-------|-------|
| Function name length | 1-60 chars | Letters, numbers, underscores, hyphens |
| Function memory | 128-30,080 MB | 64MB increments |
| Function timeout | 1-900 seconds | 15 minutes max |
| Code package size | 500 MB (zip) | Unzipped: 2,048 MB |
| Environment variables | 128 variables | 4KB total |
| Layers per function | 5 | - |
| Triggers per function | 100 | - |
| Aliases per function | 50 | - |
| Versions per function | 1,000 | Excluding $LATEST |

### API Limits

| Metric | Default | Maximum |
|--------|---------|---------|
| Concurrent executions per function | 1,000 | Account limit |
| Invocation rate per function | 10,000/sec | Request increase |
| Request size (sync) | 6 MB | - |
| Response size (sync) | 6 MB | - |
| Request size (async) | 128 KB | - |

## Cost Model

### Billing Components

| Component | Billing Unit | Free Tier |
|-----------|--------------|-----------|
| **Requests** | Per 1M requests | 1M requests/month |
| **Duration** | GB-second | 400,000 GB-seconds/month |
| **Provisioned Concurrency** | GB-second | - |

### Duration Calculation

```
Duration Cost = Memory (GB) × Execution Time (seconds) × Rate
```

**Example:**
- Function with 512MB memory
- Executes in 200ms
- Duration = 0.5 GB × 0.2 s = 0.1 GB-seconds per invocation

### Cost Optimization Tips

1. **Right-size memory:** Use minimum memory needed (not too high, not too low)
2. **Optimize cold start:** Reduce package size, use layers, provisioned concurrency
3. **Use async where possible:** Async invocations are cheaper for high-throughput
4. **Reserved concurrency:** Protect critical functions from noisy neighbors
5. **Monitor and optimize:** Use Cloud Monitor to identify optimization opportunities

## Security

### VPC Connectivity

Functions can be configured to access resources within a VPC:

- Private subnets only (no public IP)
- Requires VPC configuration (subnet, security group)
- Slower cold starts (VPC networking setup)
- Use for: private RDS, Redis, internal APIs

### IAM and Permissions

| Action | Required Permission |
|--------|---------------------|
| Create function | `scf:CreateFunction` |
| Update function | `scf:UpdateFunctionCode` |
| Delete function | `scf:DeleteFunction` |
| Invoke function | `scf:InvokeFunction` |
| View logs | `cls:GetFunctionLog` |

### Best Practices

1. **Use execution roles:** Grant minimum required permissions
2. **Encrypt secrets:** Use environment variables + Secrets Manager
3. **VPC isolation:** Use VPC for private resource access
4. **Resource policies:** Control which services can invoke your function

## Integration Patterns

### API Gateway + SCF

```
Client → API Gateway → SCF Function → Backend Services
              ↓
         Response (JSON/HTML)
```

### COS + SCF (Event-driven)

```
File Upload → COS → SCF Trigger → Process File → Store Result
```

### CMQ + SCF (Queue Processing)

```
Producer → CMQ Topic/Queue → SCF Consumer → Process Message
```

### Scheduled Tasks

```
CloudWatch Timer → SCF Function → Execute Task → CloudWatch Logs
```

## Cross-Skill Delegation

| Dependency | Delegation Target | Use Case |
|------------|-------------------|----------|
| API Gateway | `qcloud-apigw-ops` | HTTP trigger configuration |
| COS | `qcloud-cos-ops` | Object storage triggers |
| CMQ/Ckafka | `qcloud-ckafka-ops` | Message queue triggers |
| VPC | `qcloud-vpc-ops` | VPC networking setup |
| Monitor | `qcloud-monitor-ops` | Metrics and alarms |
| CLS | `qcloud-cls-ops` | Log analysis and queries |
| CAM | `qcloud-cam-ops` | Permission management |
