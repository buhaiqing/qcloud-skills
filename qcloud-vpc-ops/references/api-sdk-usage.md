# VPC API & SDK Usage

## API Reference

Official API documentation: https://cloud.tencent.com/document/api/215

### Supported APIs

#### VPC Operations

| API | Method | Description | Required Fields |
|-----|--------|-------------|-----------------|
| CreateVpc | POST | Create VPC | `VpcName`, `CidrBlock` |
| DescribeVpcs | POST | List VPCs | None (optional `VpcIds`) |
| DescribeVpcEx | POST | Extended VPC info | `VpcId` |
| ModifyVpcAttribute | POST | Update VPC name | `VpcId`, `VpcName` |
| DeleteVpc | POST | Delete VPC | `VpcId` |

#### Subnet Operations

| API | Method | Description | Required Fields |
|-----|--------|-------------|-----------------|
| CreateSubnet | POST | Create subnet | `VpcId`, `SubnetName`, `CidrBlock`, `Zone` |
| DescribeSubnets | POST | List subnets | None (optional `SubnetIds`, `VpcId`) |
| ModifySubnetAttribute | POST | Update subnet | `SubnetId` |
| DeleteSubnet | POST | Delete subnet | `SubnetId` |

#### Route Table Operations

| API | Method | Description | Required Fields |
|-----|--------|-------------|-----------------|
| CreateRouteTable | POST | Create route table | `VpcId`, `RouteTableName` |
| DescribeRouteTables | POST | List route tables | None (optional `RouteTableIds`) |
| DeleteRouteTable | POST | Delete route table | `RouteTableId` |
| CreateRoutes | POST | Add routes | `RouteTableId`, `Routes` |
| DeleteRoutes | POST | Remove routes | `RouteTableId`, `RouteIds` |

#### Network ACL Operations

| API | Method | Description | Required Fields |
|-----|--------|-------------|-----------------|
| CreateNetworkAcl | POST | Create ACL | `VpcId` |
| DescribeNetworkAcls | POST | List ACLs | None (optional `NetworkAclIds`) |
| DeleteNetworkAcl | POST | Delete ACL | `NetworkAclId` |

### Request Parameters

#### CreateVpc

```json
{
  "VpcName": "my-vpc",
  "CidrBlock": "10.0.0.0/16",
  "EnableMulticast": "false",
  "Tags": [
    {
      "Key": "env",
      "Value": "prod"
    }
  ]
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| VpcName | string | Yes | VPC name (≤60 chars) |
| CidrBlock | string | Yes | CIDR range (10.0.0.0/16 ~ 10.255.0.0/16, 172.16.0.0/16 ~ 172.31.0.0/16, 192.168.0.0/16) |
| EnableMulticast | string | No | Enable multicast (default: false) |
| Tags | array | No | Resource tags |

#### CreateSubnet

```json
{
  "VpcId": "vpc-abcdefgh",
  "SubnetName": "web-subnet",
  "CidrBlock": "10.0.1.0/24",
  "Zone": "ap-guangzhou-1",
  "Tags": []
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| VpcId | string | Yes | VPC ID |
| SubnetName | string | Yes | Subnet name (≤60 chars) |
| CidrBlock | string | Yes | Must be subset of VPC CIDR |
| Zone | string | Yes | Availability zone |
| RouteTableId | string | No | Default route table used if not specified |

### Response Fields

#### CreateVpc Response

```json
{
  "Response": {
    "Vpc": {
      "VpcId": "vpc-abcdefgh",
      "VpcName": "my-vpc",
      "CidrBlock": "10.0.0.0/16",
      "State": "CREATING",
      "CreatedTime": "2026-05-21 10:00:00",
      "EnableMulticast": "false",
      "TagSet": []
    },
    "RequestId": "abc123"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| Vpc.VpcId | string | VPC unique identifier |
| Vpc.State | string | CREATING / AVAILABLE / DELETING |
| Vpc.CidrBlock | string | CIDR range |
| Vpc.CreatedTime | string | ISO timestamp |

#### DescribeVpcs Response

```json
{
  "Response": {
    "VpcSet": [
      {
        "VpcId": "vpc-xxx",
        "VpcName": "prod-vpc",
        "CidrBlock": "10.0.0.0/16",
        "State": "AVAILABLE",
        "SubnetSet": [
          {
            "SubnetId": "subnet-xxx",
            "SubnetName": "web-subnet"
          }
        ]
      }
    ],
    "TotalCount": 1,
    "RequestId": "abc123"
  }
}
```

### Pagination

For `DescribeVpcs`, `DescribeSubnets`, `DescribeRouteTables`:

| Parameter | Description | Default | Max |
|-----------|-------------|---------|-----|
| Offset | Skip first N records | 0 | — |
| Limit | Return N records | 20 | 100 |

```bash
# Paginated query
tccli vpc DescribeVpcs --Offset 0 --Limit 50
```

## Python SDK Usage

### Installation

```bash
pip install tencentcloud-sdk-python-vpc
```

### Import Structure

```python
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.vpc import vpc_client, models
import os
```

### Create VPC Example

```python
def create_vpc():
    # Credential from environment
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    
    # Client with region
    client = vpc_client.VpcClient(cred, "ap-guangzhou")
    
    # Request
    req = models.CreateVpcRequest()
    req.VpcName = "sdk-vpc"
    req.CidrBlock = "10.0.0.0/16"
    
    # Execute
    try:
        resp = client.CreateVpc(req)
        print(f"VPC created: {resp.Vpc.VpcId}")
        return resp.Vpc.VpcId
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")
        return None
```

### Describe VPCs Example

```python
def describe_vpcs(vpc_ids=None):
    client = vpc_client.VpcClient(cred, "ap-guangzhou")
    
    req = models.DescribeVpcsRequest()
    if vpc_ids:
        req.VpcIds = vpc_ids
    
    resp = client.DescribeVpcs(req)
    
    for vpc in resp.VpcSet:
        print(f"{vpc.VpcId}: {vpc.VpcName} ({vpc.CidrBlock})")
    
    return resp.VpcSet
```

### Create Subnet Example

```python
def create_subnet(vpc_id, zone):
    client = vpc_client.VpcClient(cred, "ap-guangzhou")
    
    req = models.CreateSubnetRequest()
    req.VpcId = vpc_id
    req.SubnetName = "web-subnet"
    req.CidrBlock = "10.0.1.0/24"
    req.Zone = zone
    
    resp = client.CreateSubnet(req)
    return resp.Subnet.SubnetId
```

### Error Handling

```python
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

try:
    resp = client.CreateVpc(req)
except TencentCloudSDKException as err:
    if err.code == "ResourceQuotaExceeded.Vpc":
        print("VPC quota exceeded - contact support")
    elif err.code == "InvalidParameter.InvalidCidr":
        print("Invalid CIDR format - use RFC 1918 ranges")
    else:
        print(f"Unexpected error: {err}")
```

### Async Operations

For polling after create:

```python
import time

def wait_vpc_available(vpc_id, timeout=120):
    client = vpc_client.VpcClient(cred, "ap-guangzhou")
    req = models.DescribeVpcsRequest()
    req.VpcIds = [vpc_id]
    
    for i in range(timeout // 5):
        resp = client.DescribeVpcs(req)
        if resp.VpcSet[0].State == "AVAILABLE":
            return True
        time.sleep(5)
    
    return False
```

## Request/Response Format

All VPC API requests use JSON format with `Response` wrapper:

**Success Response:**
```json
{
  "Response": {
    "RequestId": "req-xxx",
    "Vpc": { ... }
  }
}
```

**Error Response:**
```json
{
  "Response": {
    "RequestId": "req-xxx",
    "Error": {
      "Code": "InvalidParameter",
      "Message": "Invalid CIDR format"
    }
  }
}
```

## SDK Type Definitions

### Vpc Object

```python
class Vpc:
    VpcId: str
    VpcName: str
    CidrBlock: str
    State: str  # CREATING, AVAILABLE, DELETING
    CreatedTime: str
    EnableMulticast: str
    TagSet: List[Tag]
    SubnetSet: List[Subnet]
```

### Subnet Object

```python
class Subnet:
    SubnetId: str
    SubnetName: str
    CidrBlock: str
    Zone: str
    VpcId: str
    State: str
    CreatedTime: str
    RouteTableId: str
    TotalIpCount: int
    AvailableIpCount: int
```

## References

- [VPC API Documentation](https://cloud.tencent.com/document/api/215)
- [Python SDK Guide](https://cloud.tencent.com/document/sdk/Python)