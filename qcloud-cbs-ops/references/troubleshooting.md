# CBS Troubleshooting Guide

CBS-specific error codes, diagnostic steps, and recovery patterns.

---

## 1. Error Code Reference (CBS-Specific)

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter` | Generic parameter error | Fix per API spec |
| `InvalidParameter.DiskTypeNotSupported` | Disk type not available in zone | Use supported type (CLOUD_PREMIUM/SSD/HSSD) |
| `InvalidParameterValue.DiskSizeNotSupported` | Disk size out of range | Check min/max limits for disk type |
| `InvalidParameterValue.DiskSizeTooSmall` | New size smaller than current | Resize must increase size only |
| `InvalidDisk.NotFound` | Disk ID invalid | Verify via DescribeDisks |
| `InvalidDisk.Attached` | Disk already attached | Detach first or use another disk |
| `InvalidDisk.NotAttached` | Disk not attached | Attach before operation |
| `InvalidDisk.ZoneMismatch` | Disk and instance in different zones | Use resources in same zone |
| `InvalidDisk.ResizeNotSupported` | Disk type cannot be resized | Use CLOUD_PREMIUM/SSD/HSSD |
| `InvalidDisk.Creating` | Disk still being created | Wait for UNATTACHED state |
| `InvalidDisk.Detaching` | Disk is being detached | Wait for operation to complete |
| `InvalidDisk.Attaching` | Disk is being attached | Wait for operation to complete |
| `InvalidDisk.Expanding` | Disk is being expanded | Wait for operation to complete |
| `InvalidDisk.Rollbacking` | Disk is being rolled back | Wait for operation to complete |
| `InvalidSnapshot.NotFound` | Snapshot ID invalid | Verify via DescribeSnapshots |
| `InvalidSnapshot.InUse` | Snapshot being used for image | Wait for completion |
| `InvalidSnapshot.Creating` | Snapshot is being created | Wait for NORMAL state |
| `InvalidSnapshot.NotSupported` | Operation not supported on snapshot | Check snapshot state |
| `InvalidInstance.NotFound` | Instance ID invalid | Verify via DescribeInstances |
| `InvalidInstance.NotRunning` | Instance not in valid state | Wait for RUNNING/STOPPED |
| `QuotaExceeded.DiskQuota` | Disk quota exceeded | Request quota increase or delete disks |
| `QuotaExceeded.SnapshotQuota` | Snapshot quota exceeded | Delete old snapshots |
| `LimitExceeded.AttachedDiskQuota` | Instance disk quota exceeded | Detach unused disks |
| `LimitExceeded.AutoSnapshotPolicyQuota` | Auto-snapshot policy quota exceeded | Delete old policies |
| `ResourceInsufficient.ZoneResourceInsufficient` | Zone resource insufficient | Retry or use different zone |
| `ResourceInsufficient.DiskInsufficient` | Disk resource insufficient | Retry with exponential backoff |
| `ResourceInsufficient.InsufficientBalance` | Account balance insufficient | Recharge account |
| `OperationConflict.DiskOperationConflict` | Another disk operation in progress | Retry (3x, 30s) |
| `OperationConflict.SnapshotOperationConflict` | Another snapshot operation in progress | Retry (3x, 30s) |
| `OperationDenied.DiskNotSupported` | Operation not supported for disk type | Use supported disk type |
| `OperationDenied.DiskAttached` | Cannot delete attached disk | Detach before delete |
| `OperationDenied.SnapshotCreating` | Cannot delete snapshot being created | Wait for completion |
| `RequestLimitExceeded` | API rate limit exceeded | Retry (3x, exp backoff) |
| `InternalError` | Server-side error | Retry (3x); escalate if persists |
| `InternalError.ResourceOpFailed` | Resource operation failed | Retry (3x); check RequestId |
| `UnauthorizedOperation` | No CAM permission | Grant CAM policy |
| `UnsupportedOperation.InvalidDiskState` | Disk state invalid for operation | Wait for correct state |
| `UnsupportedOperation.InvalidSnapshotState` | Snapshot state invalid for operation | Wait for correct state |

---

## 2. Diagnostic Workflow

### Step 1: Check Disk Exists

```bash
tccli cbs DescribeDisks --Region ap-guangzhou --DiskIds '["disk-xxx"]'
```

- If `TotalCount: 0` → Disk not found
- If `DiskState: DELETED` → Disk already deleted

### Step 2: Check Disk State

```bash
STATE=$(tccli cbs DescribeDisks --Region ap-guangzhou --DiskIds '["disk-xxx"]' | jq -r '.Response.DiskSet[0].DiskState')
echo "Disk state: $STATE"
```

Valid states for operations:
- AttachDisks → `UNATTACHED`
- DetachDisks → `ATTACHED`
- ResizeDisk → `ATTACHED` or `UNATTACHED`
- DeleteDisks → `UNATTACHED`
- CreateSnapshot → `ATTACHED` or `UNATTACHED`

### Step 3: Check Instance (for attach operations)

```bash
# Delegate to CVM skill
tccli cvm DescribeInstances --Region ap-guangzhou --InstanceIds '["ins-xxx"]'
```

- Instance must exist
- Instance state must be `RUNNING` or `STOPPED`
- Instance and disk must be in same zone

### Step 4: Check Zone Match

```bash
DISK_ZONE=$(tccli cbs DescribeDisks --Region ap-guangzhou --DiskIds '["disk-xxx"]' | jq -r '.Response.DiskSet[0].Zone')
CVM_ZONE=$(tccli cvm DescribeInstances --Region ap-guangzhou --InstanceIds '["ins-xxx"]' | jq -r '.Response.InstanceSet[0].Zone')
[ "$DISK_ZONE" = "$CVM_ZONE" ] && echo "✅ Zones match" || echo "❌ Zone mismatch"
```

### Step 5: Check Quota

```bash
# Check disk quota
tccli cbs DescribeDiskConfigQuota --Region ap-guangzhou --InquiryType INQUIRY_CBS_CONFIG

# Check snapshot quota
tccli cbs DescribeSnapshotQuota --Region ap-guangzhou
```

### Step 6: Check Disk Type Compatibility

```bash
DISK_TYPE=$(tccli cbs DescribeDisks --Region ap-guangzhou --DiskIds '["disk-xxx"]' | jq -r '.Response.DiskSet[0].DiskType')
echo "Disk type: $DISK_TYPE"
```

Local disk types (`LOCAL_BASIC`, `LOCAL_SSD`) cannot:
- Be resized
- Create snapshots
- Be detached from instance

---

## 3. Common Failure Scenarios

### Scenario 1: Disk Creation Fails

**Error**: `InvalidParameter.DiskTypeNotSupported`

**Root Cause**: Selected disk type not available in target zone

**Diagnosis**:
```bash
# Check available disk types in zone
tccli cbs DescribeDiskConfigQuota \
  --Region ap-guangzhou \
  --InquiryType INQUIRY_CBS_CONFIG \
  --Filters '[{"Name":"zone","Values":["ap-guangzhou-3"]}]'
```

**Fix**:
1. Query available disk types in zone
2. Select supported type (CLOUD_PREMIUM, CLOUD_SSD, CLOUD_HSSD)
3. Retry with valid type

---

### Scenario 2: Disk Attach Fails

**Error**: `InvalidDisk.ZoneMismatch`

**Root Cause**: Disk and instance are in different availability zones

**Diagnosis**:
```bash
# Check disk zone
DISK_ZONE=$(tccli cbs DescribeDisks \
  --Region ap-guangzhou \
  --DiskIds '["disk-xxx"]' | jq -r '.Response.DiskSet[0].Zone')

# Check instance zone
CVM_ZONE=$(tccli cvm DescribeInstances \
  --Region ap-guangzhou \
  --InstanceIds '["ins-xxx"]' | jq -r '.Response.InstanceSet[0].Zone')

echo "Disk zone: $DISK_ZONE"
echo "CVM zone: $CVM_ZONE"
```

**Fix**:
1. Create new disk in same zone as instance, OR
2. Create new instance in same zone as disk, OR
3. Create snapshot of disk and restore to new disk in target zone

---

### Scenario 3: Disk Already Attached

**Error**: `InvalidDisk.Attached`

**Root Cause**: Disk is already attached to another instance

**Diagnosis**:
```bash
# Check current attachment
tccli cbs DescribeDisks \
  --Region ap-guangzhou \
  --DiskIds '["disk-xxx"]' | jq '.Response.DiskSet[0] | {DiskState, InstanceId, AttachMode}'
```

**Fix**:
1. Detach disk from current instance:
```bash
tccli cbs DetachDisks --Region ap-guangzhou --DiskIds '["disk-xxx"]'
```
2. Wait for `UNATTACHED` state
3. Attach to target instance

---

### Scenario 4: Resize Not Supported

**Error**: `InvalidDisk.ResizeNotSupported`

**Root Cause**: Disk type does not support resizing

**Diagnosis**:
```bash
DISK_TYPE=$(tccli cbs DescribeDisks \
  --Region ap-guangzhou \
  --DiskIds '["disk-xxx"]' | jq -r '.Response.DiskSet[0].DiskType')
echo "Disk type: $DISK_TYPE (Local disks cannot be resized)"
```

**Fix**:
1. Create snapshot of current disk
2. Create new larger disk from snapshot
3. Replace old disk with new disk
4. Extend filesystem inside OS

**Resize-Supported Types**:
- CLOUD_PREMIUM
- CLOUD_SSD
- CLOUD_HSSD

**Resize-Unsupported Types**:
- LOCAL_BASIC
- LOCAL_SSD

---

### Scenario 5: Quota Exceeded

**Error**: `QuotaExceeded.DiskQuota` or `QuotaExceeded.SnapshotQuota`

**Root Cause**: Account reached resource limit

**Diagnosis**:
```bash
# Check current disk usage
tccli cbs DescribeDisks --Region ap-guangzhou | jq '.Response.TotalCount'

# Check snapshot usage
tccli cbs DescribeSnapshotQuota --Region ap-guangzhou

# Check auto-snapshot policy count
tccli cbs DescribeAutoSnapshotPolicies --Region ap-guangzhou | jq '.Response.TotalCount'
```

**Fix**:
1. Delete unused resources:
```bash
# Delete unused disks
tccli cbs DeleteDisks --Region ap-guangzhou --DiskIds '["disk-xxx"]'

# Delete old snapshots
tccli cbs DeleteSnapshots --Region ap-guangzhou --SnapshotIds '["snap-xxx"]'
```
2. Request quota increase via console ticket

---

### Scenario 6: Operation Conflict

**Error**: `OperationConflict.DiskOperationConflict`

**Root Cause**: Another operation is in progress on the disk

**Diagnosis**:
```bash
# Check disk state and latest operation
tccli cbs DescribeDisks \
  --Region ap-guangzhou \
  --DiskIds '["disk-xxx"]' | jq '.Response.DiskSet[0] | {DiskState, LatestOperation, LatestOperationState}'
```

**Fix**:
1. Wait for current operation to complete
2. Poll until stable state:
```bash
for i in $(seq 1 30); do
  STATE=$(tccli cbs DescribeDisks --Region ap-guangzhou --DiskIds '["disk-xxx"]' | jq -r '.Response.DiskSet[0].DiskState')
  [ "$STATE" = "UNATTACHED" ] || [ "$STATE" = "ATTACHED" ] && echo "✅ Ready" && break
  echo "⏳ Waiting... state: $STATE"
  sleep 10
done
```
3. Retry operation

---

### Scenario 7: Snapshot Creation Stuck

**Symptom**: Snapshot state `CREATING` for > 30 minutes

**Diagnosis**:
```bash
tccli cbs DescribeSnapshots \
  --Region ap-guangzhou \
  --SnapshotIds '["snap-xxx"]' | jq '.Response.SnapshotSet[0] | {SnapshotState, Percent, CreateTime}'
```

**Fix**:
1. Check progress percentage
2. Large disks (>1TB) may take longer
3. If stuck > 2 hours → escalate with RequestId

---

### Scenario 8: Snapshot Restore Fails

**Error**: `UnsupportedOperation.InvalidSnapshotState`

**Root Cause**: Snapshot not in NORMAL state

**Diagnosis**:
```bash
SNAP_STATE=$(tccli cbs DescribeSnapshots \
  --Region ap-guangzhou \
  --SnapshotIds '["snap-xxx"]' | jq -r '.Response.SnapshotSet[0].SnapshotState')
echo "Snapshot state: $SNAP_STATE"
```

**Fix**:
1. Wait for snapshot to reach `NORMAL` state
2. Poll until ready:
```bash
for i in $(seq 1 60); do
  STATE=$(tccli cbs DescribeSnapshots --Region ap-guangzhou --SnapshotIds '["snap-xxx"]' | jq -r '.Response.SnapshotSet[0].SnapshotState')
  [ "$STATE" = "NORMAL" ] && echo "✅ Snapshot ready" && break
  echo "⏳ Snapshot creating..."
  sleep 10
done
```

---

### Scenario 9: Delete Disk Fails

**Error**: `OperationDenied.DiskAttached`

**Root Cause**: Cannot delete attached disk

**Fix**:
1. Detach disk first:
```bash
# Detach disk
tccli cbs DetachDisks --Region ap-guangzhou --DiskIds '["disk-xxx"]'

# Wait for UNATTACHED
for i in $(seq 1 24); do
  STATE=$(tccli cbs DescribeDisks --Region ap-guangzhou --DiskIds '["disk-xxx"]' | jq -r '.Response.DiskSet[0].DiskState')
  [ "$STATE" = "UNATTACHED" ] && echo "✅ Detached" && break
  sleep 5
done

# Delete disk
tccli cbs DeleteDisks --Region ap-guangzhou --DiskIds '["disk-xxx"]'
```

---

### Scenario 10: Instance Disk Quota Exceeded

**Error**: `LimitExceeded.AttachedDiskQuota`

**Root Cause**: Instance reached max attached disk limit (20 disks)

**Diagnosis**:
```bash
# Count attached disks
tccli cbs DescribeDisks \
  --Region ap-guangzhou \
  --Filters '[{"Name":"instance-id","Values":["ins-xxx"]}]' | jq '.Response.TotalCount'
```

**Fix**:
1. List attached disks:
```bash
tccli cbs DescribeDisks \
  --Region ap-guangzhou \
  --Filters '[{"Name":"instance-id","Values":["ins-xxx"]}]' | jq '.Response.DiskSet[].DiskId'
```
2. Detach unused disks:
```bash
tccli cbs DetachDisks --Region ap-guangzhou --DiskIds '["disk-unused"]'
```
3. Or combine data into fewer larger disks

---

## 4. Error Message Format

Tencent Cloud API error response:

```json
{
  "Response": {
    "RequestId": "abc123",
    "Error": {
      "Code": "InvalidDisk.NotFound",
      "Message": "The disk [disk-invalid] is not found."
    }
  }
}
```

**Agent UX Feedback Template**:

```
[ERROR] {Code}: {Summary}

What happened: {Description}

How to fix: {Remediation steps}

Next step: {Specific action to take}
```

---

## 5. Multi-Round Diagnosis Pattern

### Round 1: Basic Checks

```python
def diagnose_disk(client, disk_id):
    """Round 1: Basic existence and state check"""
    from tencentcloud.cbs import cbs_client, models
    
    req = models.DescribeDisksRequest()
    req.DiskIds = [disk_id]
    
    resp = client.DescribeDisks(req)
    
    if resp.TotalCount == 0:
        return {"error": "DiskNotFound", "fix": "Verify disk ID or create new disk"}
    
    disk = resp.DiskSet[0]
    return {
        "disk_id": disk.DiskId,
        "disk_name": disk.DiskName,
        "disk_state": disk.DiskState,
        "disk_type": disk.DiskType,
        "disk_size": disk.DiskSize,
        "zone": disk.Zone,
        "instance_id": disk.InstanceId if hasattr(disk, 'InstanceId') else None,
        "latest_operation": disk.LatestOperation if hasattr(disk, 'LatestOperation') else None
    }
```

### Round 2: Instance Check (for attach/detach)

```python
def diagnose_attachment(cbs_client, cvm_client, disk_id, instance_id=None):
    """Round 2: Check attachment compatibility"""
    from tencentcloud.cbs import models as cbs_models
    from tencentcloud.cvm import models as cvm_models
    
    # Get disk info
    disk_info = diagnose_disk(cbs_client, disk_id)
    if "error" in disk_info:
        return disk_info
    
    result = {"disk": disk_info}
    
    # Check instance if provided
    if instance_id:
        cvm_req = cvm_models.DescribeInstancesRequest()
        cvm_req.InstanceIds = [instance_id]
        cvm_resp = cvm_client.DescribeInstances(cvm_req)
        
        if cvm_resp.TotalCount == 0:
            result["error"] = "InstanceNotFound"
            result["fix"] = "Verify instance ID"
            return result
        
        instance = cvm_resp.InstanceSet[0]
        result["instance"] = {
            "instance_id": instance.InstanceId,
            "instance_state": instance.Status,
            "zone": instance.Zone
        }
        
        # Check zone match
        if disk_info["zone"] != instance.Zone:
            result["error"] = "ZoneMismatch"
            result["fix"] = f"Disk in {disk_info['zone']}, Instance in {instance.Zone}"
    
    return result
```

### Round 3: Quota and Performance Check

```python
def diagnose_quota_and_performance(cbs_client, disk_id):
    """Round 3: Check quota and performance metrics"""
    from tencentcloud.cbs import models
    
    # Check disk quota
    quota_req = models.DescribeDiskConfigQuotaRequest()
    quota_req.InquiryType = "INQUIRY_CBS_CONFIG"
    quota_resp = cbs_client.DescribeDiskConfigQuota(quota_req)
    
    # Check snapshot quota
    snap_quota_req = models.DescribeSnapshotQuotaRequest()
    snap_quota_resp = cbs_client.DescribeSnapshotQuota(snap_quota_req)
    
    # Get disk info
    disk_info = diagnose_disk(cbs_client, disk_id)
    
    return {
        "disk": disk_info,
        "disk_quota_available": len(quota_resp.DiskConfigQuotaSet) > 0,
        "snapshot_quota": {
            "total": snap_quota_resp.SnapshotQuotaSet[0].TotalQuota,
            "used": snap_quota_resp.SnapshotQuotaSet[0].UsedQuota,
            "remaining": snap_quota_resp.SnapshotQuotaSet[0].RemainingQuota
        }
    }
```

---

## 6. Ordered Diagnostic Steps

For any CBS issue:

```
1. DescribeDisks → Check existence and state
2. DescribeDiskConfigQuota → Check disk type availability
3. DescribeSnapshotQuota → Check snapshot quota
4. DescribeInstances (delegate) → Check instance for attach/detach
5. Compare zones → Verify zone match for attachment
6. Check LatestOperationState → Verify no operation in progress
7. DescribeSnapshots → Check snapshot state
8. GetMonitorData → Check performance metrics
```

---

## 7. Rate Limit Recovery

| Error | Max Retries | Backoff Strategy |
|-------|-------------|------------------|
| `RequestLimitExceeded` | 3 | Exponential: 2s → 4s → 8s |
| `RequestLimitExceeded.UinLimitExceeded` | 3 | Linear: 60s each |

```python
def retry_with_backoff(func, max_retries=3):
    """Execute function with exponential backoff"""
    import time
    from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
    
    for attempt in range(max_retries):
        try:
            return func()
        except TencentCloudSDKException as err:
            if err.code != "RequestLimitExceeded":
                raise
            if attempt == max_retries - 1:
                raise
            backoff = 2 ** attempt  # 2, 4, 8 seconds
            print(f"Rate limited, retrying in {backoff}s...")
            time.sleep(backoff)
```

---

## 8. Upgrade Criteria

When to escalate to human or higher support:

| Scenario | Escalate After | Required Info |
|----------|----------------|---------------|
| Operation stuck | > 1 hour | DiskId, RequestId, Operation |
| Repeated internal errors | 3 retries | Error codes, timestamps |
| Data loss concern | Immediate | DiskId, last known state |
| Performance degradation | Investigation | Metrics, timeline |
| Billing dispute | N/A | Account details, resource IDs |

---

## References

- [CBS Error Codes](https://cloud.tencent.com/document/api/362)
- [CVM Troubleshooting](../qcloud-cvm-ops/references/troubleshooting.md)
- [CBS Core Concepts](core-concepts.md)
