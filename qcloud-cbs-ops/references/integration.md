# CBS Integration

> CBS integration with other Tencent Cloud services.

## CVM Integration

CBS disks attach to CVM instances via `AttachDisks` API. Prerequisites:
- CVM instance must be in the same region as the disk
- Disk and CVM must be in the same VPC (for enhanced CBS)
- CVM instance state must be `RUNNING` or `STOPPED`

## Attachment Flow

1. Create or select a CBS disk via `CreateDisks` or `DescribeDisks`
2. Verify CVM exists and is in valid state via `qcloud-cvm-ops`
3. Attach disk: `tccli cbs AttachDisks --DiskId disk-xxx --InstanceId ins-xxx`
4. Verify attachment: check `AttachStatus` in DescribeDisks response
5. Partition and mount the disk inside the CVM OS

## Snapshot Integration

Snapshots can be used to:
- Restore a disk to a previous state via `ApplySnapshot`
- Create a new disk from a snapshot via `CreateDisks --SnapshotId`
- Create CVM images from snapshot data

## See also
- [Core Concepts](core-concepts.md)
- [CLI Usage](cli-usage.md)
