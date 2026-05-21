# CVM CLI Usage Guide

Detailed `tccli cvm` command reference for CVM operations.

---

## 1. CLI Overview

### Installation

```bash
pip install tccli
```

### Verify

```bash
tccli version
tccli cvm help
```

### Credential Setup

```bash
export TENCENTCLOUD_SECRET_ID="AKIDxxxx"
export TENCENTCLOUD_SECRET_KEY="xxxxx"
export TENCENTCLOUD_REGION="ap-guangzhou"
```

---

## 2. Common Operations

### 2.1 Describe Regions

```bash
tccli cvm DescribeRegions

# Output
{
  "Response": {
    "RequestId": "...",
    "RegionSet": [
      {"Region": "ap-guangzhou", "RegionName": "广州", "RegionState": "AVAILABLE"},
      {"Region": "ap-shanghai", "RegionName": "上海", "RegionState": "AVAILABLE"}
    ]
  }
}
```

### 2.2 Describe Zones

```bash
tccli cvm DescribeZones --Region ap-guangzhou

# Output
{
  "Response": {
    "ZoneSet": [
      {"Zone": "ap-guangzhou-1", "ZoneName": "广州一区", "ZoneState": "AVAILABLE"},
      {"Zone": "ap-guangzhou-3", "ZoneName": "广州三区", "ZoneState": "AVAILABLE"}
    ]
  }
}
```

### 2.3 Describe Instance Type Config

```bash
# Check available instance types in zone
tccli cvm DescribeZoneInstanceConfigInfos --Region ap-guangzhou --Zone ap-guangzhou-3

# Output
{
  "Response": {
    "InstanceTypeQuotaSet": [
      {
        "InstanceType": "S5.SMALL1",
        "Cpu": 1,
        "Memory": 1,
        "InstanceFamily": "S5",
        "Status": "AVAILABLE"
      }
    ]
  }
}
```

---

## 3. Instance Lifecycle

### 3.1 RunInstances (Create)

```bash
# Minimal creation
tccli cvm RunInstances \
  --Region ap-guangzhou \
  --Placement '{"Zone":"ap-guangzhou-3"}' \
  --InstanceType S5.SMALL1 \
  --ImageId img-xxx \
  --InstanceChargeType POSTPAID_BY_HOUR \
  --SystemDisk '{"DiskType":"CLOUD_PREMIUM","DiskSize":50}'

# Full creation with network
tccli cvm RunInstances \
  --Region ap-guangzhou \
  --Placement '{"Zone":"ap-guangzhou-3"}' \
  --InstanceType S5.LARGE4 \
  --ImageId img-xxx \
  --InstanceChargeType POSTPAID_BY_HOUR \
  --InstanceName "web-server-01" \
  --SystemDisk '{"DiskType":"CLOUD_PREMIUM","DiskSize":50}' \
  --DataDisks '[{"DiskType":"CLOUD_PREMIUM","DiskSize":100}]' \
  --InternetAccessible '{"InternetChargeType":"TRAFFIC_POSTPAID_BY_HOUR","PublicIpAssigned":true,"BandwidthPackage.Id":"", "Bandwidth":10}' \
  --VpcId vpc-xxx \
  --SubnetId subnet-xxx \
  --SecurityGroupIds "[\"sg-xxx\"]" \
  --LoginSettings '{"KeyIds":["skey-xxx"]}' \
  --ClientToken "unique-token-$(date +%s%N)"

# Output
{
  "Response": {
    "RequestId": "...",
    "InstanceIdSet": ["ins-xxx"]
  }
}
```

### 3.2 DescribeInstances (Query)

```bash
# Describe single instance
tccli cvm DescribeInstances \
  --Region ap-guangzhou \
  --InstanceIds "[\"ins-xxx\"]"

# Describe all instances
tccli cvm DescribeInstances \
  --Region ap-guangzhou \
  --Offset 0 \
  --Limit 100

# Filter by status
tccli cvm DescribeInstances \
  --Region ap-guangzhou \
  --Filters '[{"Name":"instance-status","Values":["RUNNING"]}]'

# Filter by name
tccli cvm DescribeInstances \
  --Region ap-guangzhou \
  --Filters '[{"Name":"instance-name","Values":["web-*"]}]'

# Output
{
  "Response": {
    "RequestId": "...",
    "TotalCount": 10,
    "InstanceSet": [
      {
        "InstanceId": "ins-xxx",
        "InstanceName": "web-server",
        "Status": "RUNNING",
        "CPU": 4,
        "Memory": 8,
        "InstanceType": "S5.LARGE4",
        "PrivateIpAddresses": ["10.0.0.1"],
        "PublicIpAddresses": ["123.123.123.123"],
        "CreatedTime": "2026-05-21T10:00:00+08:00",
        "Zone": "ap-guangzhou-3",
        "SystemDisk": {
          "DiskType": "CLOUD_PREMIUM",
          "DiskId": "disk-xxx",
          "DiskSize": 50
        },
        "DataDisks": [...]
      }
    ]
  }
}
```

### 3.3 StartInstances

```bash
tccli cvm StartInstances \
  --Region ap-guangzhou \
  --InstanceIds "[\"ins-xxx\"]"

# Output
{
  "Response": {
    "RequestId": "..."
  }
}
```

### 3.4 StopInstances

```bash
# Soft stop (graceful)
tccli cvm StopInstances \
  --Region ap-guangzhou \
  --InstanceIds "[\"ins-xxx\"]" \
  --StopType "SOFT"

# Hard stop (forced)
tccli cvm StopInstances \
  --Region ap-guangzhou \
  --InstanceIds "[\"ins-xxx\"]" \
  --StopType "HARD"
```

### 3.5 RebootInstances

```bash
# Soft reboot
tccli cvm RebootInstances \
  --Region ap-guangzhou \
  --InstanceIds "[\"ins-xxx\"]" \
  --RebootType "SOFT"

# Hard reboot
tccli cvm RebootInstances \
  --Region ap-guangzhou \
  --InstanceIds "[\"ins-xxx\"]" \
  --RebootType "HARD"
```

### 3.6 TerminateInstances (Delete)

```bash
tccli cvm TerminateInstances \
  --Region ap-guangzhou \
  --InstanceIds "[\"ins-xxx\"]"

# Output
{
  "Response": {
    "RequestId": "..."
  }
}
```

---

## 4. Instance Configuration

### 4.1 ModifyInstanceAttribute

```bash
# Modify name
tccli cvm ModifyInstanceAttribute \
  --Region ap-guangzhou \
  --InstanceId ins-xxx \
  --InstanceName "new-name"

# Modify security groups
tccli cvm ModifyInstanceAttribute \
  --Region ap-guangzhou \
  --InstanceId ins-xxx \
  --SecurityGroupIds "[\"sg-xxx\",\"sg-yyyy\"]"

# Modify project
tccli cvm ModifyInstanceAttribute \
  --Region ap-guangzhou \
  --InstanceId ins-xxx \
  --ProjectId 0
```

### 4.2 ModifyInstancesProject

```bash
tccli cvm ModifyInstancesProject \
  --Region ap-guangzhou \
  --InstanceIds "[\"ins-xxx\",\"ins-yyyy\"]" \
  --ProjectId 10
```

### 4.3 ModifyInstancesRenewFlag

```bash
# Set auto-renewal for prepaid instances
tccli cvm ModifyInstancesRenewFlag \
  --Region ap-guangzhou \
  --InstanceIds "[\"ins-xxx\"]" \
  --RenewFlag "NOTIFY_AND_AUTO_RENEW"
```

---

## 5. Disk Operations

### 5.1 ResizeInstanceDisks

```bash
tccli cvm ResizeInstanceDisks \
  --Region ap-guangzhou \
  --InstanceId ins-xxx \
  --DataDisks '[{"DiskId":"disk-xxx","DiskSize":200}]'
```

### 5.2 AttachDisk (via CBS CLI)

```bash
tccli cbs AttachDisk \
  --Region ap-guangzhou \
  --DiskId disk-xxx \
  --InstanceId ins-xxx
```

### 5.3 DetachDisk (via CBS CLI)

```bash
tccli cbs DetachDisk \
  --Region ap-guangzhou \
  --DiskId disk-xxx
```

---

## 6. Image Operations

### 6.1 DescribeImages

```bash
# Describe custom images
tccli cvm DescribeImages \
  --Region ap-guangzhou \
  --Filters '[{"Name":"image-type","Values":["PRIVATE_IMAGE"]}]'

# Describe public images
tccli cvm DescribeImages \
  --Region ap-guangzhou \
  --Filters '[{"Name":"image-type","Values":["PUBLIC_IMAGE"]}]' \
  --Filters '[{"Name":"platform","Values":["CentOS"]}]'

# Output
{
  "Response": {
    "TotalCount": 10,
    "ImageSet": [
      {
        "ImageId": "img-xxx",
        "ImageName": "CentOS 7.6",
        "ImageType": "PUBLIC_IMAGE",
        "Platform": "CentOS",
        "ImageState": "NORMAL",
        "ImageSize": 50
      }
    ]
  }
}
```

### 6.2 CreateImage

```bash
tccli cvm CreateImage \
  --Region ap-guangzhou \
  --InstanceId ins-xxx \
  --ImageName "my-custom-image" \
  --ImageDescription "Backup image for web server"
```

### 6.3 DeleteImage

```bash
tccli cvm DeleteImage \
  --Region ap-guangzhou \
  --ImageId img-xxx
```

### 6.4 ShareImage

```bash
tccli cvm ShareImage \
  --Region ap-guangzhou \
  --ImageId img-xxx \
  --AccountIds "[\"123456\"]"
```

### 6.5 SyncImage (Cross-region)

```bash
tccli cvm SyncImages \
  --Region ap-guangzhou \
  --ImageIds "[\"img-xxx\"]" \
  --DestinationRegions "[\"ap-shanghai\",\"ap-beijing\"]"
```

---

## 7. Snapshot Operations (via CBS)

### 7.1 CreateSnapshot

```bash
tccli cbs CreateSnapshot \
  --Region ap-guangzhou \
  --DiskId disk-xxx \
  --SnapshotName "backup-$(date +%Y%m%d)"
```

### 7.2 DescribeSnapshots

```bash
tccli cbs DescribeSnapshots \
  --Region ap-guangzhou \
  --Filters '[{"Name":"disk-id","Values":["disk-xxx"]}]'
```

### 7.3 DeleteSnapshot

```bash
tccli cbs DeleteSnapshot \
  --Region ap-guangzhou \
  --SnapshotId snap-xxx
```

---

## 8. Key Pair Operations

### 8.1 CreateKeyPair

```bash
tccli cvm CreateKeyPair \
  --Region ap-guangzhou \
  --KeyName "my-key" \
  --ProjectId 0

# Output (contains private key content - save securely)
{
  "Response": {
    "KeyId": "skey-xxx",
    "KeyName": "my-key",
    "PrivateKey": "..."
  }
}
```

### 8.2 DescribeKeyPairs

```bash
tccli cvm DescribeKeyPairs \
  --Region ap-guangzhou
```

### 8.3 AttachKeyPair

```bash
tccli cvm AssociateInstancesKeyPairs \
  --Region ap-guangzhou \
  --InstanceIds "[\"ins-xxx\"]" \
  --KeyIds "[\"skey-xxx\"]"
```

### 8.4 DeleteKeyPair

```bash
tccli cvm DeleteKeyPairs \
  --Region ap-guangzhou \
  --KeyIds "[\"skey-xxx\"]"
```

---

## 9. Dedicated Host (CDH)

### 9.1 AllocateHosts

```bash
tccli cvm AllocateHosts \
  --Region ap-guangzhou \
  --Zone ap-guangzhou-3 \
  --HostType "HS20" \
  --ChargeType "PREPAID" \
  --Prepaid '{"Period":12,"RenewFlag":"NOTIFY_AND_AUTO_RENEW"}'
```

### 9.2 DescribeHosts

```bash
tccli cvm DescribeHosts \
  --Region ap-guangzhou
```

---

## 10. Price Inquiry

### 10.1 InquiryPriceRunInstances

```bash
tccli cvm InquiryPriceRunInstances \
  --Region ap-guangzhou \
  --Placement '{"Zone":"ap-guangzhou-3"}' \
  --InstanceType S5.LARGE4 \
  --ImageId img-xxx \
  --InstanceChargeType POSTPAID_BY_HOUR
```

### 10.2 InquiryPriceModifyInstance

```bash
tccli cvm InquiryPriceResizeInstanceDisks \
  --Region ap-guangzhou \
  --InstanceId ins-xxx \
  --DataDisks '[{"DiskId":"disk-xxx","DiskSize":200}]'
```

---

## 11. Pagination Pattern

```bash
# Full pagination
OFFSET=0
LIMIT=100
while true; do
  RESP=$(tccli cvm DescribeInstances \
    --Region ap-guangzhou \
    --Offset $OFFSET \
    --Limit $LIMIT)
  
  COUNT=$(echo "$RESP" | jq '.Response.InstanceSet | length')
  [ "$COUNT" -eq 0 ] && break
  
  echo "$RESP" | jq '.Response.InstanceSet[].InstanceId'
  OFFSET=$((OFFSET + LIMIT))
done
```

---

## 12. Polling Pattern

```bash
# Poll instance status
INSTANCE_ID="ins-xxx"
for i in $(seq 1 60); do
  RESP=$(tccli cvm DescribeInstances \
    --Region ap-guangzhou \
    --InstanceIds "[\"$INSTANCE_ID\"]")
  
  STATUS=$(echo "$RESP" | jq -r '.Response.InstanceSet[0].Status')
  echo "[$i] Status: $STATUS"
  
  [ "$STATUS" = "RUNNING" ] && echo "✅ Instance ready" && break
  sleep 5
done
```

---

## 13. CLI Coverage Gap Table

Some CVM operations require Python SDK (CLI not exposed):

| Operation | CLI Support | SDK Fallback Required |
|-----------|-------------|----------------------|
| RunInstances | ✅ Full | No |
| DescribeInstances | ✅ Full | No |
| StartInstances | ✅ Full | No |
| StopInstances | ✅ Full | No |
| RebootInstances | ✅ Full | No |
| TerminateInstances | ✅ Full | No |
| ModifyInstanceAttribute | ✅ Full | No |
| CreateImage | ✅ Full | No |
| DescribeImages | ✅ Full | No |
| ResizeInstanceDisks | ✅ Full | No |
| DescribeDisks | ✅ Full (via `cbs`) | No |
| DescribeQuota | ✅ Full | No |
| Complex filter queries | ⚠️ Limited | SDK for complex logic |
| Batch async operations | ⚠️ Manual poll | SDK for async waiters |

---

## 14. Common Filters

| Filter Name | Values | Example |
|-------------|--------|---------|
| `instance-name` | Wildcard | `web-*` |
| `instance-status` | RUNNING, STOPPED, SHUTDOWN | `RUNNING` |
| `instance-type` | S5.SMALL1, etc. | `S5.LARGE4` |
| `zone` | ap-guangzhou-3 | `ap-guangzhou-3` |
| `image-id` | img-xxx | `img-xxx` |
| `vpc-id` | vpc-xxx | `vpc-xxx` |
| `tag-key` | Tag key name | `Environment` |
| `tag-value` | Tag value | `Production` |

---

## References

- [tccli Official Docs](https://cloud.tencent.com/document/product/440)
- [CVM API Reference](https://cloud.tencent.com/document/api/213)
- [CLI Behavioral Notes](../qcloud-skill-generator/references/cli-behavior.md)