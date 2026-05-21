# tccli CLI Behavioral Reference

Verified behavioral notes for Tencent Cloud CLI (`tccli`) based on official documentation and testing.

---

## 1. Output Format

### 1.1 Default Output: JSON

```bash
# Default output is JSON (no flag needed)
tccli cvm DescribeInstances --Region ap-guangzhou

# Output structure:
{
  "Response": {
    "RequestId": "abc123",
    "TotalCount": 10,
    "InstanceSet": [
      {
        "InstanceId": "ins-xxx",
        "InstanceName": "my-instance",
        "Status": "RUNNING",
        ...
      }
    ]
  }
}
```

### 1.2 Output Filtering

tccli does NOT have built-in JMESPath filtering like `aliyun`. Use `jq` for filtering:

```bash
# Filter with jq
tccli cvm DescribeInstances --Region ap-guangzhou | jq '.Response.InstanceSet[].InstanceId'

# Extract specific fields
tccli cvm DescribeInstances --Region ap-guangzhou | jq '.Response.InstanceSet[] | {InstanceId, InstanceName, Status}'
```

---

## 2. Parameter Conventions

### 2.1 Parameter Naming

- **Case-sensitive:** Use exact parameter names from API spec
- **Format:** `--ParamName value` (space, not `=`)
- **Arrays:** Use JSON array format `--Param "[value1,value2]"`

```bash
# Correct format
tccli cvm DescribeInstances --Region ap-guangzhou --InstanceIds "[\"ins-xxx\",\"ins-yyyy\"]"

# Wrong format (will fail)
tccli cvm DescribeInstances --Region=ap-guangzhou  # Don't use =
```

### 2.2 Required Parameters

| Parameter | Required | Source |
|-----------|----------|--------|
| `--Region` | Yes for most products | Environment or explicit |
| Action-specific | Per API spec | Check `tccli help` |

### 2.3 Region Parameter

```bash
# Region is lowercase 'R'
tccli cvm DescribeInstances --Region ap-guangzhou

# NOT --RegionId (that's Aliyun convention)
```

---

## 3. Credential Handling

### 3.1 Environment Variables (Primary)

```bash
# CLI reads from environment
export TENCENTCLOUD_SECRET_ID="AKIDxxxx"
export TENCENTCLOUD_SECRET_KEY="xxxxx"
export TENCENTCLOUD_REGION="ap-guangzhou"

# CLI uses these automatically
tccli cvm DescribeInstances  # No credential flags needed
```

### 3.2 Config File

CLI reads from `~/.tccli/config` if environment not set:

```yaml
default:
  secretId: AKIDxxxx
  secretKey: xxxxx
  region: ap-guangzhou
```

### 3.3 Command Line Override

```bash
# Override credentials inline (NOT recommended - security risk)
tccli cvm DescribeInstances --secretId AKIDxxxx --secretKey xxxxx
```

---

## 4. Response Structure

### 4.1 Standard Response

All tccli responses follow this structure:

```json
{
  "Response": {
    "RequestId": "unique-request-id",
    // Product-specific data
    "TotalCount": 10,
    "InstanceSet": [...]
  }
}
```

### 4.2 Error Response

```json
{
  "Response": {
    "RequestId": "abc123",
    "Error": {
      "Code": "InvalidParameter",
      "Message": "Parameter validation failed"
    }
  }
}
```

### 4.3 Extracting RequestId

```bash
# Always capture RequestId for debugging
tccli cvm DescribeInstances --Region ap-guangzhou | jq '.Response.RequestId'
```

---

## 5. Pagination

### 5.1 Pagination Parameters

```bash
# Pagination uses Offset and Limit
tccli cvm DescribeInstances --Region ap-guangzhou --Offset 0 --Limit 100

# Next page
tccli cvm DescribeInstances --Region ap-guangzhou --Offset 100 --Limit 100
```

### 5.2 Pagination Loop

```bash
# Full pagination example
OFFSET=0
LIMIT=100
while true; do
  RESP=$(tccli cvm DescribeInstances --Region ap-guangzhou --Offset $OFFSET --Limit $LIMIT)
  COUNT=$(echo "$RESP" | jq '.Response.InstanceSet | length')
  [ "$COUNT" -eq 0 ] && break
  echo "$RESP" | jq '.Response.InstanceSet[].InstanceId'
  OFFSET=$((OFFSET + LIMIT))
done
```

---

## 6. Async Operations

### 6.1 Polling Pattern

tccli does NOT have `--waiter` like Aliyun. Poll manually:

```bash
# Poll for instance status
INSTANCE_ID="ins-xxx"
for i in $(seq 1 60); do
  STATUS=$(tccli cvm DescribeInstances --Region ap-guangzhou --InstanceIds "[\"$INSTANCE_ID\"]" | jq -r '.Response.InstanceSet[0].Status')
  echo "Status: $STATUS (attempt $i)"
  [ "$STATUS" = "RUNNING" ] && break
  sleep 5
done
```

### 6.2 Common Status Values

| Product | States |
|---------|--------|
| CVM | `PENDING`, `RUNNING`, `STOPPED`, `SHUTDOWN`, `TERMINATED` |
| CBS | `CREATING`, `ATTACHED`, `UNATTACHED`, `DELETING` |
| MySQL | `CREATING`, `RUNNING`, `SHUTDOWN`, `DELETING` |

---

## 7. Product Coverage

### 7.1 Common Products

| Product | CLI slug | Notes |
|---------|----------|-------|
| CVM | `cvm` | Full coverage |
| CBS (Cloud Block Storage) | `cbs` | Full coverage |
| VPC | `vpc` | Full coverage |
| CLB | `clb` | Full coverage |
| MySQL (TencentDB) | `mysql` | Full coverage |
| Redis | `redis` | Full coverage |
| MongoDB | `mongodb` | Full coverage |
| COS (Cloud Object Storage) | `cos` | Limited CLI, use SDK |
| SCF (Serverless Cloud Function) | `scf` | Full coverage |
| CKafka | `ckafka` | Full coverage |

### 7.2 Checking Coverage

```bash
# Check if product is available in CLI
tccli help

# Check product actions
tccli cvm help
tccli mysql help
```

---

## 8. Common Patterns

### 8.1 Create Resource

```bash
# Create CVM instance
tccli cvm RunInstances --Region ap-guangzhou \
  --InstanceType "S5.SMALL1" \
  --ImageId "img-xxx" \
  --InstanceName "my-instance" \
  --SecurityGroupIds "[\"sg-xxx\"]" \
  --Placement '{"Zone":"ap-guangzhou-3"}'

# Capture InstanceId from response
INSTANCE_ID=$(tccli cvm RunInstances ... | jq -r '.Response.InstanceIdSet[0]')
```

### 8.2 Describe Resource

```bash
# Describe single instance
tccli cvm DescribeInstances --Region ap-guangzhou --InstanceIds "[\"ins-xxx\"]"

# Describe all instances
tccli cvm DescribeInstances --Region ap-guangzhou
```

### 8.3 Modify Resource

```bash
# Modify instance name
tccli cvm ModifyInstanceAttribute --Region ap-guangzhou --InstanceId "ins-xxx" --InstanceName "new-name"
```

### 8.4 Delete Resource

```bash
# Delete (terminate) instance
tccli cvm TerminateInstances --Region ap-guangzhou --InstanceIds "[\"ins-xxx\"]"
```

---

## 9. Error Handling

### 9.1 Common Errors

| Code | Meaning | CLI Exit Code |
|------|---------|---------------|
| `InvalidParameter` | Parameter error | Non-zero |
| `ResourceNotFound` | Resource missing | Non-zero |
| `InvalidSecretKey` | Credential error | Non-zero |
| `RequestLimitExceeded` | Rate limit | Non-zero |

### 9.2 Error Extraction

```bash
# Extract error from response
tccli cvm DescribeInstances --Region invalid-region 2>&1 | jq '.Response.Error'

# Or check if Error field exists
tccli cvm DescribeInstances ... 2>&1 | jq -e '.Response.Error' && echo "Error occurred"
```

---

## 10. Debugging

### 10.1 Debug Output

```bash
# Debug mode (be careful - may expose credentials)
tccli cvm DescribeInstances --Region ap-guangzhou --debug 2>&1 | grep -vE "SecretKey|SecretId"
```

### 10.2 Verbose Output

```bash
# Verbose mode
tccli cvm DescribeInstances --Region ap-guangzhou --verbose
```

---

## 11. Batch Operations

### 11.1 Array Parameters

```bash
# Pass array of IDs
tccli cvm DescribeInstances --Region ap-guangzhou --InstanceIds "[\"ins-xxx\",\"ins-yyyy\"]"

# Batch terminate
tccli cvm TerminateInstances --Region ap-guangzhou --InstanceIds "[\"ins-xxx\",\"ins-yyyy\"]"
```

### 11.2 Batch with jq

```bash
# Get all instance IDs
IDS=$(tccli cvm DescribeInstances --Region ap-guangzhou | jq -c '[.Response.InstanceSet[].InstanceId]')
echo "$IDS"

# Use IDs in another command
tccli cvm StopInstances --Region ap-guangzhou --InstanceIds "$IDS"
```

---

## 12. Comparison with Aliyun CLI

| Feature | tccli (Tencent) | aliyun (Alibaba) |
|---------|-----------------|------------------|
| Output format | JSON (default) | JSON (default) |
| JMESPath | No (use jq) | Yes (`--output cols/rows`) |
| Region param | `--Region` | `--RegionId` |
| Waiter | No (manual poll) | Yes (`--waiter`) |
| Credential env | `TENCENTCLOUD_SECRET_ID/KEY` | `ALIBABA_CLOUD_ACCESS_KEY_ID/SECRET` |
| Config file | `~/.tccli/config` (YAML) | `~/.aliyun/config.json` |
| Interactive config | `tccli configure` | `aliyun configure` |

---

## References

- [tccli Official Docs](https://cloud.tencent.com/document/product/440)
- [tccli GitHub](https://github.com/TencentCloud/tencentcloud-cli)