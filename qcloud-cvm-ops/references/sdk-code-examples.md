# CVM SDK Code Examples

This file contains all Python SDK code examples extracted from the main SKILL.md file, organized by operation name.

## RunInstances (Create CVM)

```python
req = models.RunInstancesRequest()
req.Placement = models.Placement()
req.Placement.Zone = os.environ.get("ZONE", "ap-guangzhou-3")
req.InstanceType = os.environ.get("INSTANCE_TYPE", "S5.SMALL1")
req.ImageId = os.environ.get("IMAGE_ID", "img-xxx")
req.InstanceName = os.environ.get("INSTANCE_NAME", "test-instance")
req.SystemDisk = models.SystemDisk()
req.SystemDisk.DiskType = "CLOUD_PREMIUM"
req.SystemDisk.DiskSize = 50
req.InstanceChargeType = "POSTPAID_BY_HOUR"
req.ClientToken = str(int(time.time() * 1000000))
req.VpcId = os.environ.get("VPC_ID", "")
req.SubnetId = os.environ.get("SUBNET_ID", "")
req.SecurityGroupIds = os.environ.get("SECURITY_GROUP_IDS", "").split(",")
req.InternetAccessible = models.InternetAccessible()
req.InternetAccessible.InternetChargeType = "TRAFFIC_POSTPAID_BY_HOUR"
req.InternetAccessible.InternetMaxBandwidthOut = 1

resp = client.RunInstances(req)
print(json.loads(resp.to_json_string()))
```

## DescribeInstances

```python
req = models.DescribeInstancesRequest()
req.InstanceIds = [os.environ.get("INSTANCE_ID", "ins-xxx")]
req.Offset = 0
req.Limit = 100

resp = client.DescribeInstances(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## StartInstances

```python
req = models.StartInstancesRequest()
req.InstanceIds = ["{{user.instance_id}}"]
resp = client.StartInstances(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## StopInstances

```python
req = models.StopInstancesRequest()
req.InstanceIds = ["{{user.instance_id}}"]
req.StopType = "SOFT"  # or "HARD"
resp = client.StopInstances(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## RebootInstances

```python
req = models.RebootInstancesRequest()
req.InstanceIds = ["{{user.instance_id}}"]
req.RebootType = "SOFT"  # or "HARD"
resp = client.RebootInstances(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## ResetInstance (Re-image)

```python
req = models.ResetInstanceRequest()
req.InstanceId = "{{user.instance_id}}"
req.ImageId = "{{user.image_id}}"
resp = client.ResetInstance(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## TerminateInstances (Delete)

```python
req = models.TerminateInstancesRequest()
req.InstanceIds = ["{{user.instance_id}}"]
resp = client.TerminateInstances(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## ModifyInstanceSpec (Change Instance Type)

```python
req = models.ModifyInstanceSpecRequest()
req.InstanceId = "{{user.instance_id}}"
req.InstanceType = "{{user.new_instance_type}}"

resp = client.ModifyInstanceSpec(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## ResizeInstanceDisk (CBS Disk Expansion)

```python
req = models.ResizeInstanceDisksRequest()
req.InstanceId = "{{user.instance_id}}"
req.DataDisks = [
    models.DataDisk(
        DiskId="{{user.disk_id}}",
        DiskSize={{user.new_disk_size}}
    )
]
resp = client.ResizeInstanceDisks(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## CreateSnapshot (Backup)

```python
import time

req = cbs_models.CreateSnapshotRequest()
req.DiskId = "{{user.disk_id}}"
req.SnapshotName = "backup-" + "{{user.instance_id}}" + "-" + time.strftime("%Y%m%d-%H%M%S")
resp = client.CreateSnapshot(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## CreateImage (Custom Image)

```python
import time

req = models.CreateImageRequest()
req.InstanceId = "{{user.instance_id}}"
req.ImageName = "{{user.image_name}}"
req.ImageDescription = "Custom image created at " + time.strftime("%Y%m%d-%H%M%S")
resp = client.CreateImage(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## AttachDisks (Attach CBS Disks)

```python
req = cbs_models.AttachDisksRequest()
req.InstanceId = "{{user.instance_id}}"
req.DiskIds = ["{{user.disk_id}}"]

resp = client.AttachDisks(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## DetachDisk (Detach CBS Disk)

```python
req = cbs_models.DetachDiskRequest()
req.InstanceId = "{{user.instance_id}}"
req.DiskId = "{{user.disk_id}}"

resp = client.DetachDisk(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```