# CBS API & SDK Usage

> CBS (Cloud Block Storage) API and SDK reference.

## SDK Installation

```bash
pip install tencentcloud-sdk-python-cbs
```

## API Reference

| API | Description | CLI Example |
|-----|-------------|-------------|
| DescribeDisks | Query cloud disk list | `tccli cbs DescribeDisks` |
| CreateDisks | Create cloud disks | `tccli cbs CreateDisks` |
| AttachDisks | Mount disk to CVM | `tccli cbs AttachDisks` |
| DetachDisks | Unmount disk from CVM | `tccli cbs DetachDisks` |
| DeleteDisks | Delete cloud disks | `tccli cbs DeleteDisks` |
| ResizeDisk | Expand disk capacity | `tccli cbs ResizeDisk` |
| CreateSnapshot | Create disk snapshot | `tccli cbs CreateSnapshot` |
| DescribeSnapshots | Query snapshot list | `tccli cbs DescribeSnapshots` |
| ApplySnapshot | Restore disk from snapshot | `tccli cbs ApplySnapshot` |

## SDK Code Example

```python
from tencentcloud.cbs.v20170312 import CbsClient
from tencentcloud.cbs.v20170312.models import DescribeDisksRequest

client = CbsClient(cred, region, profile)
req = DescribeDisksRequest()
req.DiskIds = ["disk-12345678"]
resp = client.DescribeDisks(req)
print(resp.DiskSet)
```

## Pagination

CBS API uses `Offset` and `Limit` for pagination:

```bash
tccli cbs DescribeDisks --Offset 0 --Limit 20
```

## Response Schema

All CBS APIs return a response with `RequestId` and a data array (e.g., `DiskSet`, `SnapshotSet`).

## See also
- [CLI Usage](cli-usage.md)
- [Core Concepts](core-concepts.md)
