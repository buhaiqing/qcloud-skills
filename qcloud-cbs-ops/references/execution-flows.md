# CBS Execution Flows

This file contains detailed CLI and SDK command blocks for CBS operations. SKILL.md describes the high-level workflow (what to do); this file provides the detailed commands (how to do).

## Index

| Section | Operation | CLI Command | SDK Command |
|---------|-----------|-------------|-------------|
| §1 | CreateDisks | `tccli cbs CreateDisks --Region ... --Placement ... --DiskSize ... --DiskType ...` | `client.CreateDisks(req)` |
| §2 | AttachDisks | `tccli cbs AttachDisks --Region ... --DiskIds ... --InstanceId ...` | `client.AttachDisks(req)` |
| §3 | DetachDisks | `tccli cbs DetachDisks --Region ... --DiskIds ...` | `client.DetachDisks(req)` |
| §4 | ResizeDisk | `tccli cbs ResizeDisk --Region ... --DiskId ... --DiskSize ...` | `client.ResizeDisk(req)` |
| §5 | CreateSnapshot | `tccli cbs CreateSnapshot --Region ... --DiskId ... --SnapshotName ...` | `client.CreateSnapshot(req)` |
| §6 | DeleteSnapshots | `tccli cbs DeleteSnapshots --Region ... --SnapshotIds ...` | `client.DeleteSnapshots(req)` |

---

## §1 CreateDisks

### CLI

```bash
tccli cbs CreateDisks \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Placement '{"Zone":"{{user.zone}}"}' \
  --DiskSize {{user.disk_size}} \
  --DiskType "{{user.disk_type}}" \
  --DiskName "{{user.disk_name}}" \
  --DiskChargeType "POSTPAID_BY_HOUR" \
  --ClientToken "$(date +%s%N)" > /tmp/response.json

DISK_ID=$(jq -r '.Response.DiskIdSet[0]' /tmp/response.json)
echo "Created disk: $DISK_ID"
```

### SDK

```python
import os, json, time
from tencentcloud.common import credential
from tencentcloud.cbs import cbs_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = cbs_client.CbsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.CreateDisksRequest()
req.Placement = models.Placement()
req.Placement.Zone = "{{user.zone}}"
req.DiskSize = {{user.disk_size}}
req.DiskType = "{{user.disk_type}}"
req.DiskName = "{{user.disk_name}}"
req.DiskChargeType = "POSTPAID_BY_HOUR"
req.ClientToken = str(int(time.time() * 1000000))

resp = client.CreateDisks(req)
result = json.loads(resp.to_json_string())
print(json.dumps(result, indent=2))
```

### Validation Poll

```bash
for i in $(seq 1 24); do
  STATE=$(tccli cbs DescribeDisks --Region {{env.TENCENTCLOUD_REGION}} --DiskIds "[\"{{output.disk_id}}\"]" | jq -r '.Response.DiskSet[0].DiskState')
  [ "$STATE" = "UNATTACHED" ] && echo "✅ Disk ready (UNATTACHED)" && break
  echo "⏳ Waiting for disk... current state: $STATE"
  sleep 5
done
```

---

## §2 AttachDisks

### CLI

```bash
tccli cbs AttachDisks \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --DiskIds '["{{user.disk_id}}"]' \
  --InstanceId "{{user.instance_id}}" > /tmp/response.json

echo "Attach request submitted: $(jq -r '.Response.RequestId' /tmp/response.json)"
```

### SDK

```python
import os, json
from tencentcloud.common import credential
from tencentcloud.cbs import cbs_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = cbs_client.CbsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.AttachDisksRequest()
req.DiskIds = ["{{user.disk_id}}"]
req.InstanceId = "{{user.instance_id}}"

resp = client.AttachDisks(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

### Validation Poll

```bash
for i in $(seq 1 24); do
  STATE=$(tccli cbs DescribeDisks --Region {{env.TENCENTCLOUD_REGION}} --DiskIds "[\"{{user.disk_id}}\"]" | jq -r '.Response.DiskSet[0].DiskState')
  INSTANCE=$(tccli cbs DescribeDisks --Region {{env.TENCENTCLOUD_REGION}} --DiskIds "[\"{{user.disk_id}}\"]" | jq -r '.Response.DiskSet[0].InstanceId')
  [ "$STATE" = "ATTACHED" ] && [ "$INSTANCE" = "{{user.instance_id}}" ] && echo "✅ Disk attached to {{user.instance_id}}" && break
  echo "⏳ Attaching disk... current state: $STATE"
  sleep 5
done
```

---

## §3 DetachDisks

### CLI

```bash
tccli cbs DetachDisks \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --DiskIds '["{{user.disk_id}}"]' > /tmp/response.json

echo "Detach request submitted: $(jq -r '.Response.RequestId' /tmp/response.json)"
```

### SDK

```python
import os, json
from tencentcloud.common import credential
from tencentcloud.cbs import cbs_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = cbs_client.CbsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.DetachDisksRequest()
req.DiskIds = ["{{user.disk_id}}"]

resp = client.DetachDisks(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

### Validation Poll

```bash
for i in $(seq 1 24); do
  STATE=$(tccli cbs DescribeDisks --Region {{env.TENCENTCLOUD_REGION}} --DiskIds "[\"{{user.disk_id}}\"]" | jq -r '.Response.DiskSet[0].DiskState')
  [ "$STATE" = "UNATTACHED" ] && echo "✅ Disk detached (UNATTACHED)" && break
  echo "⏳ Detaching disk... current state: $STATE"
  sleep 5
done
```

---

## §4 ResizeDisk

### CLI

```bash
tccli cbs ResizeDisk \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --DiskId "{{user.disk_id}}" \
  --DiskSize {{user.new_disk_size}} > /tmp/response.json

echo "Resize request submitted: $(jq -r '.Response.RequestId' /tmp/response.json)"
```

### SDK

```python
import os, json
from tencentcloud.common import credential
from tencentcloud.cbs import cbs_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = cbs_client.CbsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.ResizeDiskRequest()
req.DiskId = "{{user.disk_id}}"
req.DiskSize = {{user.new_disk_size}}

resp = client.ResizeDisk(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

### Validation Poll

```bash
for i in $(seq 1 60); do
  SIZE=$(tccli cbs DescribeDisks --Region {{env.TENCENTCLOUD_REGION}} --DiskIds "[\"{{user.disk_id}}\"]" | jq -r '.Response.DiskSet[0].DiskSize')
  STATE=$(tccli cbs DescribeDisks --Region {{env.TENCENTCLOUD_REGION}} --DiskIds "[\"{{user.disk_id}}\"]" | jq -r '.Response.DiskSet[0].DiskState')
  [ "$SIZE" = "{{user.new_disk_size}}" ] && [ "$STATE" != "EXPANDING" ] && echo "✅ Disk resized to ${SIZE}GB" && break
  echo "⏳ Resizing disk... current size: ${SIZE}GB, state: $STATE"
  sleep 5
done
```

---

## §5 CreateSnapshot

### CLI

```bash
tccli cbs CreateSnapshot \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --DiskId "{{user.disk_id}}" \
  --SnapshotName "{{user.snapshot_name}}" > /tmp/response.json

SNAPSHOT_ID=$(jq -r '.Response.SnapshotId' /tmp/response.json)
echo "Created snapshot: $SNAPSHOT_ID"
```

### SDK

```python
import os, json
from tencentcloud.common import credential
from tencentcloud.cbs import cbs_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = cbs_client.CbsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.CreateSnapshotRequest()
req.DiskId = "{{user.disk_id}}"
req.SnapshotName = "{{user.snapshot_name}}"

resp = client.CreateSnapshot(req)
result = json.loads(resp.to_json_string())
print(json.dumps(result, indent=2))
```

### Validation Poll

```bash
for i in $(seq 1 120); do
  STATE=$(tccli cbs DescribeSnapshots --Region {{env.TENCENTCLOUD_REGION}} --SnapshotIds "[\"{{output.snapshot_id}}\"]" | jq -r '.Response.SnapshotSet[0].SnapshotState')
  [ "$STATE" = "NORMAL" ] && echo "✅ Snapshot created successfully" && break
  echo "⏳ Creating snapshot... current state: $STATE"
  sleep 5
done
```

---

## §6 DeleteSnapshots

### CLI

```bash
tccli cbs DeleteSnapshots \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --SnapshotIds '["{{user.snapshot_id}}"]' > /tmp/response.json

echo "Delete request submitted: $(jq -r '.Response.RequestId' /tmp/response.json)"
```

### SDK

```python
import os, json
from tencentcloud.common import credential
from tencentcloud.cbs import cbs_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = cbs_client.CbsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.DeleteSnapshotsRequest()
req.SnapshotIds = ["{{user.snapshot_id}}"]

resp = client.DeleteSnapshots(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

### Validation Poll

```bash
for i in $(seq 1 24); do
  COUNT=$(tccli cbs DescribeSnapshots --Region {{env.TENCENTCLOUD_REGION}} --SnapshotIds "[\"{{user.snapshot_id}}\"]" | jq -r '.Response.SnapshotSet | length')
  [ "$COUNT" = "0" ] && echo "✅ Snapshot deleted" && break
  echo "⏳ Deleting snapshot..."
  sleep 5
done
```
