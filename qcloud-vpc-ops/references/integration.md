# VPC Integration Guide

## SDK Setup

### Installation

```bash
# Full SDK
pip install tencentcloud-sdk-python

# VPC-specific module (lighter)
pip install tencentcloud-sdk-python-vpc
```

### Python Version Requirements

- Minimum: Python 3.8+
- Recommended: Python 3.10+

### Dependency Management

**requirements.txt:**
```
tencentcloud-sdk-python-vpc>=3.0.0
```

**Virtual Environment:**
```bash
python3 -m venv ~/.qcloud-venv
source ~/.qcloud-venv/bin/activate
pip install tencentcloud-sdk-python-vpc
```

## Environment Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| TENCENTCLOUD_SECRET_ID | API Secret ID | AKIDxxxx |
| TENCENTCLOUD_SECRET_KEY | API Secret Key | xxxx |
| TENCENTCLOUD_REGION | Default region | ap-guangzhou |

### Setup Methods

**Method 1: Environment Variables (Recommended)**
```bash
export TENCENTCLOUD_SECRET_ID="AKID..."
export TENCENTCLOUD_SECRET_KEY="..."
export TENCENTCLOUD_REGION="ap-guangzhou"
```

**Method 2: Config File**
```yaml
# ~/.tccli/config
default:
  secretId: AKID...
  secretKey: ...
  region: ap-guangzhou
```

**Method 3: Python Code**
```python
import os
os.environ["TENCENTCLOUD_SECRET_ID"] = "AKID..."
os.environ["TENCENTCLOUD_SECRET_KEY"] = "..."
os.environ["TENCENTCLOUD_REGION"] = "ap-guangzhou"
```

## SDK Usage Patterns

### Import Structure

```python
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.vpc import vpc_client, models
import os
```

### Credential Creation

```python
# From environment variables
cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)

# From config file (alternative) — NOT recommended: use env vars instead
# cred = credential.Credential(secret_id=os.environ.get("TENCENTCLOUD_SECRET_ID"), secret_key=os.environ.get("TENCENTCLOUD_SECRET_KEY"))
```

### Client Initialization

```python
# Basic client
region = os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou")
client = vpc_client.VpcClient(cred, region)

# With HTTP profile (timeout)
from tencentcloud.common.profile.http_profile import HttpProfile
http_profile = HttpProfile(timeout=30)
client = vpc_client.VpcClient(cred, region, http_profile)

# With client profile
from tencentcloud.common.profile.client_profile import ClientProfile
client_profile = ClientProfile(http_profile=http_profile)
client = vpc_client.VpcClient(cred, "ap-guangzhou", client_profile)
```

### Request Creation

```python
# Simple request
req = models.CreateVpcRequest()
req.VpcName = "test-vpc"
req.CidrBlock = "10.0.0.0/16"

# Complex request with tags
req = models.CreateVpcRequest()
req.VpcName = "prod-vpc"
req.CidrBlock = "172.16.0.0/16"
req.Tags = [
    models.Tag(Key="env", Value="production"),
    models.Tag(Key="owner", Value="ops-team")
]
```

### Response Handling

```python
# Parse response
resp = client.CreateVpc(req)
vpc_id = resp.Vpc.VpcId
vpc_state = resp.Vpc.State

# JSON export
import json
print(json.dumps(resp.to_json_string(), indent=2))

# Field extraction
print(f"Created VPC: {resp.Vpc.VpcId}")
print(f"CIDR: {resp.Vpc.CidrBlock}")
```

### Error Handling

```python
try:
    resp = client.CreateVpc(req)
    print(f"Success: {resp.Vpc.VpcId}")
except TencentCloudSDKException as err:
    print(f"[ERROR] {err.code}: {err.message}")
    
    if err.code == "ResourceQuotaExceeded.Vpc":
        print("Action: Delete unused VPCs or request quota increase")
    elif err.code == "InvalidParameter.InvalidCidr":
        print("Action: Use valid RFC 1918 CIDR (10.x, 172.16-31.x, 192.168.x)")
    else:
        print(f"RequestId: {err.requestId}")
```

## Cross-Skill Delegation

### VPC → CVM Delegation

When creating CVM instances after VPC setup:

```python
# VPC skill creates VPC/Subnet
vpc_id = create_vpc()
subnet_id = create_subnet(vpc_id)

# Delegate to CVM skill for instance creation
# (CVM skill uses subnet_id from VPC skill output)
print(f"VPC ready. Delegate to qcloud-cvm-ops with subnet_id={subnet_id}")
```

### VPC → CLB Delegation

When creating load balancer:

```python
# VPC skill provides subnet IDs
subnets = describe_subnets(vpc_id)

# Delegate to CLB skill
# CLB skill requires subnet_ids parameter
print(f"Delegate to qcloud-clb-ops with subnet_ids={subnets}")
```

### Delegation Matrix

| From VPC | To Skill | Required Output |
|----------|----------|-----------------|
| Create VPC/Subnet | qcloud-cvm-ops | `vpc_id`, `subnet_id` |
| Create VPC/Subnet | qcloud-clb-ops | `vpc_id`, `subnet_ids` |
| Create VPC/Subnet | qcloud-cdb-ops | `vpc_id`, `subnet_ids` |
| Create VPC/Subnet | qcloud-redis-ops | `vpc_id`, `subnet_ids` |

## Async Operations

### Polling Pattern

```python
import time

def wait_vpc_available(client, vpc_id, timeout=120):
    req = models.DescribeVpcsRequest()
    req.VpcIds = [vpc_id]
    
    for i in range(timeout // 5):
        resp = client.DescribeVpcs(req)
        state = resp.VpcSet[0].State
        
        if state == "AVAILABLE":
            return True
        elif state in ["FAILED", "DELETING"]:
            return False
        
        time.sleep(5)
    
    return False  # Timeout
```

### Batch Creation Pattern

```python
def create_multi_subnet(vpc_id, zones):
    client = vpc_client.VpcClient(cred, region)
    subnet_ids = []
    
    for i, zone in enumerate(zones):
        req = models.CreateSubnetRequest()
        req.VpcId = vpc_id
        req.SubnetName = f"subnet-tier{i+1}"
        req.CidrBlock = f"10.0.{i+1}.0/24"
        req.Zone = zone
        
        resp = client.CreateSubnet(req)
        subnet_ids.append(resp.Subnet.SubnetId)
        
        # Wait to avoid conflicts
        time.sleep(2)
    
    return subnet_ids
```

## Security Best Practices

### Credential Security

```python
# NEVER print credentials
# Safe verification only
if os.environ.get("TENCENTCLOUD_SECRET_ID"):
    print("✓ Credentials configured")
else:
    raise Exception("Missing TENCENTCLOUD_SECRET_ID")

# NEVER log credentials
# Unsafe:
logging.info(f"Key: {os.environ.get('SECRET_KEY')}")  # ❌

# Safe:
logging.info("Credentials validated")  # ✓
```

### IAM Integration

```python
# Use CAM role instead of static credentials (recommended)
from tencentcloud.common import credential

# Role-based credential (for CVM instances)
cred = credential.Credential.from_sts_role(
    role_arn="qcs::cam::uin/xxx:roleName/xxx",
    external_id="xxx"
)
```

## Testing

### Unit Test Example

```python
import unittest
from unittest.mock import Mock, patch

class TestVPCOps(unittest.TestCase):
    @patch('vpc_client.VpcClient')
    def test_create_vpc(self, mock_client):
        # Mock response
        mock_resp = Mock()
        mock_resp.Vpc.VpcId = "vpc-test123"
        mock_client.CreateVpc.return_value = mock_resp
        
        # Test
        vpc_id = create_vpc("test", "10.0.0.0/16")
        self.assertEqual(vpc_id, "vpc-test123")
```

### Integration Test

```python
def test_vpc_workflow():
    # Requires real credentials
    vpc_id = create_vpc()
    assert vpc_id.startswith("vpc-")
    
    subnet_id = create_subnet(vpc_id)
    assert subnet_id.startswith("subnet-")
    
    # Cleanup
    delete_subnet(subnet_id)
    delete_vpc(vpc_id)
```

## Troubleshooting SDK Issues

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: vpc` | SDK not installed | `pip install tencentcloud-sdk-python-vpc` |
| `InvalidSecretKey` | Wrong credentials | Verify env vars |
| `Timeout` | Network issue | Increase timeout in HttpProfile |
| `SSLError` | Certificate issue | Update certifi package |

### Debug Mode

```python
import logging

# Enable debug (caution: may expose credentials)
logging.basicConfig(level=logging.DEBUG)

# Use HttpProfile debug
http_profile = HttpProfile(timeout=30)
http_profile.req_method = "POST"
http_profile.req_timeout = 30
```

## Performance Optimization

### Connection Pooling

```python
# Reuse client across operations
class VPCManager:
    def __init__(self, cred, region):
        self.client = vpc_client.VpcClient(cred, region)
    
    def create_vpc(self, name, cidr):
        req = models.CreateVpcRequest()
        req.VpcName = name
        req.CidrBlock = cidr
        return self.client.CreateVpc(req)
    
    def describe_vpcs(self):
        req = models.DescribeVpcsRequest()
        return self.client.DescribeVpcs(req)
```

### Batch Operations

```python
# Use Describe API with pagination for bulk queries
def list_all_subnets(client, vpc_id):
    req = models.DescribeSubnetsRequest()
    req.Filters = [
        models.Filter(Name="vpc-id", Values=[vpc_id])
    ]
    
    all_subnets = []
    offset = 0
    limit = 100
    
    while True:
        req.Offset = offset
        req.Limit = limit
        resp = client.DescribeSubnets(req)
        
        all_subnets.extend(resp.SubnetSet)
        
        if len(resp.SubnetSet) < limit:
            break
        offset += limit
    
    return all_subnets
```

## References

- [Python SDK Documentation](https://cloud.tencent.com/document/sdk/Python)
- [VPC API Reference](https://cloud.tencent.com/document/api/215)
- [SDK Source Code](https://github.com/TencentCloud/tencentcloud-sdk-python)