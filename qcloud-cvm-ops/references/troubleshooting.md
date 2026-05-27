# CVM Troubleshooting Guide

CVM-specific error codes, diagnostic steps, and recovery patterns.

---

## 1. Error Code Reference (CVM-Specific)

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter` | Generic parameter error | Fix per API spec |
| `InvalidParameter.ImageIdMalformed` | Image ID format invalid | Use `img-xxx` format |
| `InvalidParameter.SubnetIdMalformed` | Subnet ID format invalid | Use `subnet-xxx` |
| `InvalidParameter.VpcIdMalformed` | VPC ID format invalid | Use `vpc-xxx` |
| `InvalidParameterValue` | Value out of valid range | Check enum/range in spec |
| `InvalidParameterValue.InstanceTypeUnsupported` | Instance type not in zone | DescribeZoneInstanceConfigInfos |
| `InvalidParameterValue.ZoneNotSupported` | Zone invalid for region | DescribeZones |
| `InvalidParameterValue.RangeNotAllowed` | Disk size not allowed | Check disk size limits |
| `MissingParameter` | Required param missing | Add required param |
| `ResourceNotFound` | Generic not found | Verify resource exists |
| `ResourceNotFound.InstanceNotFound` | Instance ID invalid | DescribeInstances to verify |
| `ResourceNotFound.ImageNotFound` | Image ID invalid | DescribeImages to verify |
| `ResourceNotFound.VpcNotFound` | VPC ID invalid | Delegate to VPC skill |
| `ResourceNotFound.SubnetNotFound` | Subnet ID invalid | Delegate to VPC skill |
| `ResourceNotFound.SecurityGroupNotFound` | SG ID invalid | Delegate to VPC skill |
| `ResourceInsufficient` | Generic resource shortage | HALT |
| `ResourceInsufficient.CvmInstanceQuotaIsFull` | Instance quota exceeded | Request quota increase |
| `ResourceInsufficient.DiskQuotaIsFull` | CBS disk quota exceeded | Request quota increase |
| `QuotaExceeded.SecurityGroupLimit` | SG quota exceeded | Use existing SG |
| `QuotaExceeded.SnapshotLimit` | Snapshot quota exceeded | Delete old snapshots |
| `InvalidVpc.NotFound` | VPC not found | Delegate to VPC skill |
| `InvalidSubnet.NotFound` | Subnet not found | Delegate to VPC skill |
| `InvalidSecurityGroupID.NotFound` | SG not found | Delegate to VPC skill |
| `InvalidKeyPair.NotFound` | Key pair not found | CreateKeyPair first |
| `OperationDenied` | Operation not allowed | Check account/instance state |
| `OperationDenied.InstanceOperationConflict` | Another operation in progress | Retry (3x, 30s) |
| `OperationDenied.ImageStateConflict` | Image being modified | Retry (3x, 30s) |
| `RequestLimitExceeded` | API rate limit exceeded | Retry (3x, exp backoff) |
| `RequestLimitExceeded.UinLimitExceeded` | Account-level rate limit | Retry (3x, 60s) |
| `InternalError` | Server-side error | Retry (3x); escalate if persists |
| `InternalError.ResourceOpFailed` | Resource operation failed | Retry (3x); check RequestId |
| `UnauthorizedOperation` | No CAM permission | Grant CAM policy |
| `UnauthorizedOperation.CamUnauthorized` | CAM permission denied | Add permission to policy |
| `UnsupportedOperation` | Operation not supported | Check instance/region |
| `UnsupportedOperation.InvalidInstanceState` | Instance state invalid for op | Wait for correct state |

---

## 2. Diagnostic Workflow

### Step 1: Check Instance Exists

```bash
tccli cvm DescribeInstances --Region ap-guangzhou --InstanceIds "[\"ins-xxx\"]"
```

- If `TotalCount: 0` → Instance not found
- If `Status: TERMINATED` → Instance already deleted

### Step 2: Check Instance State

```bash
STATUS=$(tccli cvm DescribeInstances --Region ap-guangzhou --InstanceIds "[\"ins-xxx\"]" | jq -r '.Response.InstanceSet[0].Status')
echo "Instance state: $STATUS"
```

Valid states for operations:
- StartInstances → `STOPPED`
- StopInstances → `RUNNING`
- RebootInstances → `RUNNING` or `STOPPED`
- TerminateInstances → Any stable state

### Step 3: Check Quota

```bash
tccli cvm DescribeAccountQuota --Region ap-guangzhou
```

### Step 4: Check Instance Type Availability

```bash
tccli cvm DescribeZoneInstanceConfigInfos --Region ap-guangzhou --Zone ap-guangzhou-3 | jq '.Response.InstanceTypeQuotaSet[] | select(.Status=="AVAILABLE")'
```

### Step 5: Check Image Availability

```bash
tccli cvm DescribeImages --Region ap-guangzhou --Filters '[{"Name":"image-id","Values":["img-xxx"]}]' | jq '.Response.ImageSet[0].ImageState'
```

---

## 3. Common Failure Scenarios

### Scenario 1: Instance Creation Fails

**Error**: `InvalidParameterValue.InstanceTypeUnsupported`

**Root Cause**: Instance type not available in selected zone

**Fix**:
1. Check zone-instance type matrix:
   ```bash
   tccli cvm DescribeZoneInstanceConfigInfos --Region ap-guangzhou --Zone ap-guangzhou-3
   ```
2. Select a supported type (filter by `Status: AVAILABLE`)
3. Retry with valid type

---

### Scenario 2: Quota Exceeded

**Error**: `ResourceInsufficient.CvmInstanceQuotaIsFull`

**Root Cause**: Account reached instance limit for region

**Fix**:
1. Check current quota:
   ```bash
   tccli cvm DescribeAccountQuota --Region ap-guangzhou
   ```
2. Delete unused instances
3. Request quota increase via console ticket

---

### Scenario 3: Operation Conflict

**Error**: `OperationDenied.InstanceOperationConflict`

**Root Cause**: Another operation in progress on instance

**Fix**:
1. Wait 30 seconds
2. Retry operation (max 3 times)
3. Check `LatestOperation` field:
   ```bash
   tccli cvm DescribeInstances --Region ap-guangzhou --InstanceIds "[\"ins-xxx\"]" | jq '.Response.InstanceSet[0].LatestOperation'
   ```

---

### Scenario 4: Instance Stuck in Pending

**Symptom**: Instance status `PENDING` for > 5 minutes

**Diagnosis**:
1. Check operation state:
   ```bash
   tccli cvm DescribeInstances --Region ap-guangzhou --InstanceIds "[\"ins-xxx\"]" | jq '.Response.InstanceSet[0]'
   ```
2. Check `LatestOperationState`

**Fix**:
- If state is `RUNNING` → wait longer
- If state is `FAILED` → check error code
- If stuck > 10 min → escalate with RequestId

---

### Scenario 5: SSH Connection Failed

**Symptom**: Cannot SSH to instance after creation

**Diagnosis Steps**:
1. Check instance status is `RUNNING`
2. Check security group allows port 22:
   ```bash
   tccli vpc DescribeSecurityGroupPolicies --Region ap-guangzhou --SecurityGroupId sg-xxx
   ```
3. Check public IP assigned:
   ```bash
   tccli cvm DescribeInstances --Region ap-guangzhou --InstanceIds "[\"ins-xxx\"]" | jq '.Response.InstanceSet[0].PublicIpAddresses'
   ```
4. Check key pair attached:
   ```bash
   tccli cvm DescribeInstances --Region ap-guangzhou --InstanceIds "[\"ins-xxx\"]" | jq '.Response.InstanceSet[0].LoginSettings'
   ```

**Fix**:
- Add SSH inbound rule to security group
- Associate key pair with instance
- Verify instance has public IP (or use VPN/Direct Connect)

---

### Scenario 6: Disk Resize Failed

**Error**: `InvalidParameterValue.RangeNotAllowed`

**Root Cause**: Target disk size not supported

**Fix**:
1. Check disk type limits:
   - CLOUD_PREMIUM: 10-32000 GB
   - CLOUD_SSD: 20-32000 GB
2. Resize must increase (not decrease)
3. Verify current disk size

---

### Scenario 7: Image Creation Failed

**Error**: `UnsupportedOperation.InvalidInstanceState`

**Root Cause**: Instance not in stable state

**Fix**:
1. Stop instance first:
   ```bash
   tccli cvm StopInstances --Region ap-guangzhou --InstanceIds "[\"ins-xxx\"]"
   ```
2. Wait for `STOPPED`
3. CreateImage with `ForcePoweroff=TRUE`

---

## 4. Error Message Format

Tencent Cloud API error response:

```json
{
  "Response": {
    "RequestId": "abc123",
    "Error": {
      "Code": "InvalidParameter.ImageIdMalformed",
      "Message": "The image ID [img-invalid] is malformed. Image ID format: img-xxxxxxxx"
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
def diagnose_instance(client, instance_id):
    # Round 1: Basic existence and state check
    req = models.DescribeInstancesRequest()
    req.InstanceIds = [instance_id]
    
    resp = client.DescribeInstances(req)
    
    if resp.TotalCount == 0:
        return {"error": "InstanceNotFound", "fix": "Verify instance ID or create new"}
    
    instance = resp.InstanceSet[0]
    return {
        "instance_id": instance.InstanceId,
        "status": instance.Status,
        "cpu": instance.CPU,
        "memory": instance.Memory,
        "latest_operation": instance.LatestOperation,
        "latest_operation_state": instance.LatestOperationState
    }
```

### Round 2: Network Check

```python
def diagnose_network(client, instance_id, vpc_client):
    # Round 2: Network configuration check
    # Get instance VPC info
    instance_info = diagnose_instance(client, instance_id)
    
    if "error" in instance_info:
        return instance_info
    
    # Check VPC
    vpc_req = models.DescribeVpcsRequest()
    vpc_req.VpcIds = [instance_info["vpc_id"]]
    vpc_resp = vpc_client.DescribeVpcs(vpc_req)
    
    # Check Security Group
    sg_req = models.DescribeSecurityGroupsRequest()
    sg_req.SecurityGroupIds = instance_info["security_group_ids"]
    sg_resp = vpc_client.DescribeSecurityGroups(sg_req)
    
    return {
        "vpc_state": vpc_resp.VpcSet[0].State,
        "sg_count": len(sg_resp.SecurityGroupSet),
        "public_ip": instance_info.get("public_ip", "N/A")
    }
```

### Round 3: Metrics Check

```python
def diagnose_metrics(monitor_client, instance_id):
    # Round 3: Check recent metrics for performance issues
    req = models.GetMonitorDataRequest()
    req.Namespace = "QCE/CVM"
    req.MetricName = "CPUUsage"
    req.Dimensions = [{"Name": "InstanceId", "Value": instance_id}]
    req.StartTime = "2026-05-20T00:00:00+08:00"
    req.EndTime = "2026-05-21T00:00:00+08:00"
    req.Period = 300
    
    resp = monitor_client.GetMonitorData(req)
    max_cpu = max([dp.Value for dp in resp.DataPoints])
    
    if max_cpu > 90:
        return {"warning": "HighCPU", "max_value": max_cpu, "recommendation": "Scale out or optimize"}
    
    return {"status": "Normal", "max_cpu": max_cpu}
```

---

## 6. Ordered Diagnostic Steps

For any CVM issue:

```
1. DescribeInstances → Check existence and state
2. DescribeAccountQuota → Check quota limits
3. DescribeZoneInstanceConfigInfos → Check type availability
4. DescribeImages → Check image availability
5. DescribeVpcs (delegate) → Check network
6. DescribeSecurityGroupPolicies (delegate) → Check firewall
7. GetMonitorData → Check performance metrics
8. DescribeDisks → Check disk status
9. DescribeSnapshots → Check backup status
```

---

## 7. Rate Limit Recovery

| Error | Max Retries | Backoff Strategy |
|-------|-------------|------------------|
| `RequestLimitExceeded` | 3 | Exponential: 2s → 4s → 8s |
| `RequestLimitExceeded.UinLimitExceeded` | 3 | Linear: 60s each |

```python
def retry_with_backoff(func, max_retries=3):
    # Execute function with exponential backoff
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

## References

- [CVM Error Codes](https://cloud.tencent.com/document/api/213)
- [API Debugging Guide](https://cloud.tencent.com/document/product/213)