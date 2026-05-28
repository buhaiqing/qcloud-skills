# CBS CLI Usage Guide

Detailed `tccli cbs` command reference for CBS (Cloud Block Storage) operations.

---

## 1. CLI Overview

### Installation

```bash
pip install tccli
```

### Verify

```bash
tccli version
tccli cbs help
```

### Credential Setup

```bash
export TENCENTCLOUD_SECRET_ID="AKIDxxxx"
export TENCENTCLOUD_SECRET_KEY="xxxxx"
export TENCENTCLOUD_REGION="ap-guangzhou"
```

---

## 2. CLI to API Mapping Table

| Operation | CLI Command | API Method | Category |
|-----------|-------------|------------|----------|
| **List Disks** | `tccli cbs DescribeDisks` | DescribeDisks | Disk Query |
| **Create Disk** | `tccli cbs CreateDisks` | CreateDisks | Disk Lifecycle |
| **Delete Disk** | `tccli cbs DeleteDisks` | DeleteDisks | Disk Lifecycle |
| **Attach Disk** | `tccli cbs AttachDisks` | AttachDisks | Disk Lifecycle |
| **Detach Disk** | `tccli cbs DetachDisks` | DetachDisks | Disk Lifecycle |
| **Resize Disk** | `tccli cbs ResizeDisk` | ResizeDisk | Disk Lifecycle |
| **Modify Disk Attributes** | `tccli cbs ModifyDiskAttributes` | ModifyDiskAttributes | Disk Config |
| **Modify Disk Extra Performance** | `tccli cbs ModifyDiskExtraPerformance` | ModifyDiskExtraPerformance | Disk Config |
| **Inquiry Disk Price** | `tccli cbs InquiryPriceCreateDisks` | InquiryPriceCreateDisks | Billing |
| **Inquiry Resize Price** | `tccli cbs InquiryPriceResizeDisk` | InquiryPriceResizeDisk | Billing |
| **Create Snapshot** | `tccli cbs CreateSnapshot` | CreateSnapshot | Snapshot |
| **Delete Snapshots** | `tccli cbs DeleteSnapshots` | DeleteSnapshots | Snapshot |
| **List Snapshots** | `tccli cbs DescribeSnapshots` | DescribeSnapshots | Snapshot Query |
| **Apply Snapshot** | `tccli cbs ApplySnapshot` | ApplySnapshot | Snapshot |
| **Modify Snapshot** | `tccli cbs ModifySnapshotAttribute` | ModifySnapshotAttribute | Snapshot Config |
| **Create Image from Snapshot** | `tccli cbs CreateImage` | CreateImage | Snapshot |
| **List Snapshot Shares** | `tccli cbs DescribeSnapshotSharePermission` | DescribeSnapshotSharePermission | Snapshot Query |
| **Modify Snapshot Share** | `tccli cbs ModifySnapshotSharePermission` | ModifySnapshotSharePermission | Snapshot Config |
| **Create Auto-Snapshot Policy** | `tccli cbs CreateAutoSnapshotPolicy` | CreateAutoSnapshotPolicy | Auto Snapshot |
| **Delete Auto-Snapshot Policy** | `tccli cbs DeleteAutoSnapshotPolicies` | DeleteAutoSnapshotPolicies | Auto Snapshot |
| **List Auto-Snapshot Policies** | `tccli cbs DescribeAutoSnapshotPolicies` | DescribeAutoSnapshotPolicies | Auto Snapshot Query |
| **Modify Auto-Snapshot Policy** | `tccli cbs ModifyAutoSnapshotPolicyAttribute` | ModifyAutoSnapshotPolicyAttribute | Auto Snapshot Config |
| **Bind Auto-Snapshot Policy** | `tccli cbs BindAutoSnapshotPolicy` | BindAutoSnapshotPolicy | Auto Snapshot |
| **Unbind Auto-Snapshot Policy** | `tccli cbs UnbindAutoSnapshotPolicy` | UnbindAutoSnapshotPolicy | Auto Snapshot |
| **Query Disk Config Quota** | `tccli cbs DescribeDiskConfigQuota` | DescribeDiskConfigQuota | Quota |
| **Query Snapshot Quota** | `tccli cbs DescribeSnapshotQuota` | DescribeSnapshotQuota | Quota |
| **Query Disk Associated Snapshots** | `tccli cbs DescribeDiskAssociatedSnapshots` | DescribeDiskAssociatedSnapshots | Snapshot Query |
| **Initialize Disk** | `tccli cbs InitializeDisks` | InitializeDisks | Disk Lifecycle |
| **Terminate Disk** | `tccli cbs TerminateDisks` | TerminateDisks | Disk Lifecycle |
| **Renew Disk** | `tccli cbs RenewDisk` | RenewDisk | Billing |
| **Inquiry Price Renew** | `tccli cbs InquiryPriceRenewDisks` | InquiryPriceRenewDisks | Billing |

---

## 3. Disk Operations

### 3.1 DescribeDisks (Query Disks)

```bash
# List all disks
tccli cbs DescribeDisks --Region ap-guangzhou --Limit 100

# Query specific disk
tccli cbs DescribeDisks \
  --Region ap-guangzhou \
  --DiskIds '["disk-xxx"]'

# Filter by status
tccli cbs DescribeDisks \
  --Region ap-guangzhou \
  --Filters '[{"Name":"disk-state","Values":["UNATTACHED"]}]'

# Filter by disk type
tccli cbs DescribeDisks \
  --Region ap-guangzhou \
  --Filters '[{"Name":"disk-type","Values":["CLOUD_SSD"]}]'

# Output
{
  "Response": {
    "RequestId": "...",
    "TotalCount": 10,
    "DiskSet": [
      {
        "DiskId": "disk-xxx",
        "DiskName": "data-disk-01",
        "DiskType": "CLOUD_PREMIUM",
        "DiskState": "ATTACHED",
        "DiskSize": 100,
        "InstanceId": "ins-xxx",
        "Zone": "ap-guangzhou-3",
        "CreateTime": "2026-05-28T10:00:00+08:00",
        "DiskChargeType": "POSTPAID_BY_HOUR"
      }
    ]
  }
}
```

### 3.2 CreateDisks (Create Disk)

```bash
# Minimal creation
tccli cbs CreateDisks \
  --Region ap-guangzhou \
  --Placement '{"Zone":"ap-guangzhou-3"}' \
  --DiskSize 100 \
  --DiskType CLOUD_PREMIUM

# Full creation with options
tccli cbs CreateDisks \
  --Region ap-guangzhou \
  --Placement '{"Zone":"ap-guangzhou-3"}' \
  --DiskSize 500 \
  --DiskType CLOUD_SSD \
  --DiskName "high-performance-disk" \
  --DiskChargeType POSTPAID_BY_HOUR \
  --ClientToken "unique-token-$(date +%s%N)"

# Output
{
  "Response": {
    "RequestId": "...",
    "DiskIdSet": ["disk-xxx"]
  }
}
```

### 3.3 AttachDisks (Attach Disk)

```bash
tccli cbs AttachDisks \
  --Region ap-guangzhou \
  --DiskIds '["disk-xxx"]' \
  --InstanceId ins-yyy

# Output
{
  "Response": {
    "RequestId": "..."
  }
}
```

### 3.4 DetachDisks (Detach Disk)

```bash
tccli cbs DetachDisks \
  --Region ap-guangzhou \
  --DiskIds '["disk-xxx"]'

# Output
{
  "Response": {
    "RequestId": "..."
  }
}
```

### 3.5 ResizeDisk (Expand Disk)

```bash
tccli cbs ResizeDisk \
  --Region ap-guangzhou \
  --DiskId disk-xxx \
  --DiskSize 200

# Output
{
  "Response": {
    "RequestId": "..."
  }
}
```

### 3.6 DeleteDisks (Delete Disk)

```bash
tccli cbs DeleteDisks \
  --Region ap-guangzhou \
  --DiskIds '["disk-xxx"]'

# Output
{
  "Response": {
    "RequestId": "..."
  }
}
```

### 3.7 ModifyDiskAttributes (Modify Disk)

```bash
# Change disk name
tccli cbs ModifyDiskAttributes \
  --Region ap-guangzhou \
  --DiskId disk-xxx \
  --DiskName "new-disk-name"

# Change project
tccli cbs ModifyDiskAttributes \
  --Region ap-guangzhou \
  --DiskId disk-xxx \
  --ProjectId 0

# Delete with disk
tccli cbs ModifyDiskAttributes \
  --Region ap-guangzhou \
  --DiskId disk-xxx \
  --DeleteWithInstance "TRUE"

# Output
{
  "Response": {
    "RequestId": "..."
  }
}
```

---

## 4. Snapshot Operations

### 4.1 DescribeSnapshots (Query Snapshots)

```bash
# List all snapshots
tccli cbs DescribeSnapshots --Region ap-guangzhou --Limit 100

# Query specific snapshot
tccli cbs DescribeSnapshots \
  --Region ap-guangzhou \
  --SnapshotIds '["snap-xxx"]'

# Filter by disk
tccli cbs DescribeSnapshots \
  --Region ap-guangzhou \
  --Filters '[{"Name":"disk-id","Values":["disk-xxx"]}]'

# Output
{
  "Response": {
    "RequestId": "...",
    "TotalCount": 5,
    "SnapshotSet": [
      {
        "SnapshotId": "snap-xxx",
        "SnapshotName": "backup-20260528",
        "DiskId": "disk-yyy",
        "DiskSize": 100,
        "SnapshotState": "NORMAL",
        "CreateTime": "2026-05-28T10:00:00+08:00",
        "Percent": 100
      }
    ]
  }
}
```

### 4.2 CreateSnapshot (Create Snapshot)

```bash
tccli cbs CreateSnapshot \
  --Region ap-guangzhou \
  --DiskId disk-xxx \
  --SnapshotName "backup-$(date +%Y%m%d)"

# Output
{
  "Response": {
    "RequestId": "...",
    "SnapshotId": "snap-xxx"
  }
}
```

### 4.3 DeleteSnapshots (Delete Snapshot)

```bash
tccli cbs DeleteSnapshots \
  --Region ap-guangzhou \
  --SnapshotIds '["snap-xxx"]'

# Output
{
  "Response": {
    "RequestId": "..."
  }
}
```

### 4.4 ApplySnapshot (Restore from Snapshot)

```bash
tccli cbs ApplySnapshot \
  --Region ap-guangzhou \
  --DiskId disk-xxx \
  --SnapshotId snap-yyy

# Output
{
  "Response": {
    "RequestId": "..."
  }
}
```

### 4.5 ModifySnapshotAttribute (Modify Snapshot)

```bash
# Change snapshot name
tccli cbs ModifySnapshotAttribute \
  --Region ap-guangzhou \
  --SnapshotId snap-xxx \
  --SnapshotName "renamed-snapshot"

# Output
{
  "Response": {
    "RequestId": "..."
  }
}
```

---

## 5. Auto-Snapshot Policy Operations

### 5.1 DescribeAutoSnapshotPolicies (Query Policies)

```bash
tccli cbs DescribeAutoSnapshotPolicies \
  --Region ap-guangzhou

# Output
{
  "Response": {
    "RequestId": "...",
    "TotalCount": 3,
    "AutoSnapshotPolicySet": [
      {
        "AutoSnapshotPolicyId": "asp-xxx",
        "AutoSnapshotPolicyName": "daily-backup",
        "Policy": [
          {"DayOfWeek": [0, 1, 2, 3, 4, 5, 6], "Hour": [2]}
        ],
        "RetentionDays": 7,
        "CreateTime": "2026-05-01T00:00:00+08:00"
      }
    ]
  }
}
```

### 5.2 CreateAutoSnapshotPolicy (Create Policy)

```bash
tccli cbs CreateAutoSnapshotPolicy \
  --Region ap-guangzhou \
  --AutoSnapshotPolicyName "daily-backup" \
  --Policy '[{"DayOfWeek":[1,2,3,4,5],"Hour":[2]}]' \
  --RetentionDays 7

# Output
{
  "Response": {
    "RequestId": "...",
    "AutoSnapshotPolicyId": "asp-xxx"
  }
}
```

### 5.3 BindAutoSnapshotPolicy (Bind Policy)

```bash
tccli cbs BindAutoSnapshotPolicy \
  --Region ap-guangzhou \
  --AutoSnapshotPolicyId asp-xxx \
  --DiskIds '["disk-xxx", "disk-yyy"]'

# Output
{
  "Response": {
    "RequestId": "..."
  }
}
```

### 5.4 UnbindAutoSnapshotPolicy (Unbind Policy)

```bash
tccli cbs UnbindAutoSnapshotPolicy \
  --Region ap-guangzhou \
  --AutoSnapshotPolicyId asp-xxx \
  --DiskIds '["disk-xxx"]'

# Output
{
  "Response": {
    "RequestId": "..."
  }
}
```

### 5.5 DeleteAutoSnapshotPolicies (Delete Policy)

```bash
tccli cbs DeleteAutoSnapshotPolicies \
  --Region ap-guangzhou \
  --AutoSnapshotPolicyIds '["asp-xxx"]'

# Output
{
  "Response": {
    "RequestId": "..."
  }
}
```

---

## 6. Quota Operations

### 6.1 DescribeDiskConfigQuota (Disk Quota)

```bash
tccli cbs DescribeDiskConfigQuota \
  --Region ap-guangzhou \
  --InquiryType INQUIRY_CBS_CONFIG

# Output
{
  "Response": {
    "RequestId": "...",
    "DiskConfigQuotaSet": [
      {
        "Zone": "ap-guangzhou-3",
        "DiskType": "CLOUD_PREMIUM",
        "DiskMinSize": 10,
        "DiskMaxSize": 32000
      },
      {
        "Zone": "ap-guangzhou-3",
        "DiskType": "CLOUD_SSD",
        "DiskMinSize": 20,
        "DiskMaxSize": 32000
      }
    ]
  }
}
```

### 6.2 DescribeSnapshotQuota (Snapshot Quota)

```bash
tccli cbs DescribeSnapshotQuota --Region ap-guangzhou

# Output
{
  "Response": {
    "RequestId": "...",
    "TotalCount": 1,
    "SnapshotQuotaSet": [
      {
        "TotalQuota": 64,
        "UsedQuota": 15,
        "RemainingQuota": 49
      }
    ]
  }
}
```

---

## 7. Billing Operations

### 7.1 InquiryPriceCreateDisks

```bash
tccli cbs InquiryPriceCreateDisks \
  --Region ap-guangzhou \
  --DiskType CLOUD_SSD \
  --DiskSize 500 \
  --DiskChargeType POSTPAID_BY_HOUR

# Output
{
  "Response": {
    "RequestId": "...",
    "Price": {
      "DiscountPrice": 2.5,
      "OriginalPrice": 2.5,
      "UnitPrice": 2.5
    }
  }
}
```

### 7.2 InquiryPriceResizeDisk

```bash
tccli cbs InquiryPriceResizeDisk \
  --Region ap-guangzhou \
  --DiskId disk-xxx \
  --DiskSize 200

# Output
{
  "Response": {
    "RequestId": "...",
    "Price": {
      "DiscountPrice": 0,
      "OriginalPrice": 0
    }
  }
}
```

---

## 8. CLI Coverage Analysis

| Operation Category | CLI Support | SDK Fallback Required |
|-------------------|-------------|----------------------|
| **Disk Lifecycle** | | |
| CreateDisks | Full | No |
| DeleteDisks | Full | No |
| AttachDisks | Full | No |
| DetachDisks | Full | No |
| ResizeDisk | Full | No |
| ModifyDiskAttributes | Full | No |
| InitializeDisks | Full | No |
| TerminateDisks | Full | No |
| **Snapshot** | | |
| CreateSnapshot | Full | No |
| DeleteSnapshots | Full | No |
| DescribeSnapshots | Full | No |
| ApplySnapshot | Full | No |
| ModifySnapshotAttribute | Full | No |
| **Auto-Snapshot Policy** | | |
| CreateAutoSnapshotPolicy | Full | No |
| DeleteAutoSnapshotPolicies | Full | No |
| DescribeAutoSnapshotPolicies | Full | No |
| BindAutoSnapshotPolicy | Full | No |
| UnbindAutoSnapshotPolicy | Full | No |
| ModifyAutoSnapshotPolicyAttribute | Full | No |
| **Quota & Billing** | | |
| DescribeDiskConfigQuota | Full | No |
| DescribeSnapshotQuota | Full | No |
| InquiryPriceCreateDisks | Full | No |
| InquiryPriceResizeDisk | Full | No |
| **Advanced Operations** | | |
| ModifyDiskExtraPerformance | Full | No |
| CreateImage (from snapshot) | Partial | SDK recommended |
| Cross-region copy | Limited | SDK recommended |
| Batch async operations | Limited | SDK recommended |

---

## 9. Common Filters

### Disk Filters

| Filter Name | Values | Example |
|-------------|--------|---------|
| `disk-id` | disk-xxx | `["disk-xxx"]` |
| `disk-name` | Wildcard | `data-*` |
| `disk-state` | UNATTACHED, ATTACHED, ATTACHING, DETACHING | `ATTACHED` |
| `disk-type` | CLOUD_BASIC, CLOUD_PREMIUM, CLOUD_SSD, CLOUD_HSSD | `CLOUD_SSD` |
| `disk-usage` | SYSTEM_DISK, DATA_DISK | `DATA_DISK` |
| `instance-id` | ins-xxx | `ins-xxx` |
| `zone` | ap-guangzhou-3 | `ap-guangzhou-3` |
| `project-id` | 0, 123 | `0` |
| `disk-charge-type` | POSTPAID_BY_HOUR, PREPAID | `POSTPAID_BY_HOUR` |

### Snapshot Filters

| Filter Name | Values | Example |
|-------------|--------|---------|
| `snapshot-id` | snap-xxx | `["snap-xxx"]` |
| `snapshot-name` | Wildcard | `backup-*` |
| `disk-id` | disk-xxx | `disk-xxx` |
| `snapshot-state` | NORMAL, CREATING | `NORMAL` |

---

## 10. Polling Patterns

### Poll Disk State

```bash
DISK_ID="disk-xxx"
for i in $(seq 1 24); do
  STATE=$(tccli cbs DescribeDisks \
    --Region ap-guangzhou \
    --DiskIds "[\"$DISK_ID\"]" | jq -r '.Response.DiskSet[0].DiskState')
  echo "[$i] State: $STATE"
  [ "$STATE" = "ATTACHED" ] && echo "✅ Disk attached" && break
  sleep 5
done
```

### Poll Snapshot Creation

```bash
SNAPSHOT_ID="snap-xxx"
for i in $(seq 1 120); do
  STATE=$(tccli cbs DescribeSnapshots \
    --Region ap-guangzhou \
    --SnapshotIds "[\"$SNAPSHOT_ID\"]" | jq -r '.Response.SnapshotSet[0].SnapshotState')
  PERCENT=$(tccli cbs DescribeSnapshots \
    --Region ap-guangzhou \
    --SnapshotIds "[\"$SNAPSHOT_ID\"]" | jq -r '.Response.SnapshotSet[0].Percent')
  echo "[$i] State: $STATE, Progress: $PERCENT%"
  [ "$STATE" = "NORMAL" ] && echo "✅ Snapshot created" && break
  sleep 5
done
```

---

## 11. Pagination Pattern

```bash
OFFSET=0
LIMIT=100
while true; do
  RESP=$(tccli cbs DescribeDisks \
    --Region ap-guangzhou \
    --Offset $OFFSET \
    --Limit $LIMIT)
  
  COUNT=$(echo "$RESP" | jq '.Response.DiskSet | length')
  [ "$COUNT" -eq 0 ] && break
  
  echo "$RESP" | jq '.Response.DiskSet[].DiskId'
  OFFSET=$((OFFSET + LIMIT))
done
```

---

## References

- [tccli Official Docs](https://cloud.tencent.com/document/product/440)
- [CBS API Reference](https://cloud.tencent.com/document/api/362)
- [CLI Behavioral Notes](../qcloud-skill-generator/references/cli-behavior.md)
