# CBS Error Code Reference

<!-- Use API for latest error codes: `tccli cbs help` → per-operation error docs at https://cloud.tencent.com/document/api/362/ -->
<!-- Query quotas via `tccli cbs DescribeDiskConfigQuota --Region {{env.TENCENTCLOUD_REGION}} --InquiryType INQUIRY_CBS_CONFIG` and `tccli cbs DescribeSnapshotQuota --Region {{env.TENCENTCLOUD_REGION}}` -->

## 1. CBS Error Taxonomy

> Referenced by SKILL.md §Failure Recovery tables (per operation) and `references/troubleshooting.md`.

| Code | HALT? | Retry? | Agent Action |
|------|-------|--------|-------------|
| `InvalidParameter` | — | 0 | Fix per API spec |
| `InvalidParameter.DiskTypeNotSupported` | ✓ | 0 | Use supported type (CLOUD_PREMIUM/SSD/HSSD) |
| `InvalidParameterValue.DiskSizeNotSupported` | ✓ | 0 | Check min/max limits for disk type |
| `InvalidParameterValue.DiskSizeTooSmall` | ✓ | 0 | Resize must increase size only |
| `InvalidDisk.NotFound` | ✓ | 0 | Verify via DescribeDisks |
| `InvalidDisk.Attached` | ✓ | 0 | Detach first or use another disk |
| `InvalidDisk.NotAttached` | ✓ | 0 | Attach before operation |
| `InvalidDisk.ZoneMismatch` | ✓ | 0 | Use resources in same zone |
| `InvalidDisk.ResizeNotSupported` | ✓ | 0 | Use CLOUD_PREMIUM/SSD/HSSD |
| `InvalidDisk.Creating` | — | 0 | Wait for UNATTACHED state |
| `InvalidDisk.Detaching` | — | 0 | Wait for operation to complete |
| `InvalidDisk.Attaching` | — | 0 | Wait for operation to complete |
| `InvalidDisk.Expanding` | — | 0 | Wait for operation to complete |
| `InvalidDisk.Rollbacking` | — | 0 | Wait for operation to complete |
| `InvalidSnapshot.NotFound` | ✓ | 0 | Verify via DescribeSnapshots |
| `InvalidSnapshot.InUse` | ✓ | 0 | Wait for completion |
| `InvalidSnapshot.Creating` | — | 0 | Wait for NORMAL state |
| `InvalidSnapshot.NotSupported` | ✓ | 0 | Check snapshot state |
| `InvalidInstance.NotFound` | ✓ | 0 | Verify via DescribeInstances |
| `InvalidInstance.NotRunning` | — | 0 | Wait for RUNNING/STOPPED |
| `QuotaExceeded.DiskQuota` | ✓ | 0 | Delete unused disks or request increase |
| `QuotaExceeded.SnapshotQuota` | ✓ | 0 | Delete old snapshots |
| `LimitExceeded.AttachedDiskQuota` | ✓ | 0 | Detach unused disks |
| `LimitExceeded.AutoSnapshotPolicyQuota` | ✓ | 0 | Delete old policies |
| `ResourceInsufficient.ZoneResourceInsufficient` | — | 3, 30s | Retry or use different zone |
| `ResourceInsufficient.DiskInsufficient` | — | 3, exp | Retry with exponential backoff |
| `ResourceInsufficient.InsufficientBalance` | ✓ | 0 | Recharge account |
| `OperationConflict.DiskOperationConflict` | — | 3, 30s | Retry; another operation in progress |
| `OperationConflict.SnapshotOperationConflict` | — | 3, 30s | Retry; snapshot operation in progress |
| `OperationDenied.DiskNotSupported` | ✓ | 0 | Use supported disk type |
| `OperationDenied.DiskAttached` | ✓ | 0 | Detach before delete |
| `OperationDenied.SnapshotCreating` | — | 0 | Wait for completion |
| `RequestLimitExceeded` | — | 3, exp | Back off and retry |
| `InternalError` | — | 3, 2s/4s/8s | Retry; HALT if persists |
| `InternalError.ResourceOpFailed` | — | 3, 2s/4s/8s | Retry; check RequestId |
| `UnauthorizedOperation` | ✓ | 0 | Grant CAM policy |
| `UnsupportedOperation.InvalidDiskState` | — | 0 | Wait for correct state |
| `UnsupportedOperation.InvalidSnapshotState` | — | 0 | Wait for correct state |

## 2. Per-Operation Error Quick-Reference

> Compact lookup for execution flows.

| Operation | Common errors | Gate |
|-----------|-------------|------|
| CreateDisks | `DiskTypeNotSupported`, `DiskSizeNotSupported`, `ZoneResourceInsufficient`, `DiskQuota` | HALT |
| AttachDisks | `InvalidDisk.NotFound`, `NotAttached`, `ZoneMismatch`, `AttachedDiskQuota` | HALT |
| DetachDisks | `NotAttached`, `DiskOperationConflict` | HALT |
| ResizeDisk | `ResizeNotSupported`, `DiskSizeTooSmall`, `DiskOperationConflict` | HALT |
| CreateSnapshot | `NotFound`, `SnapshotQuota`, `DiskOperationConflict` | HALT |
| DeleteSnapshots | `NotFound`, `InUse`, `SnapshotOperationConflict` | HALT |
| Any | `RequestLimitExceeded`, `InternalError` | Retry 3× |
