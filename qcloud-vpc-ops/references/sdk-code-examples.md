# VPC SDK Code Examples

> **Note:** These Python SDK code examples are extracted from `SKILL.md` for token efficiency.
> Refer to this file when implementing SDK fallback paths for VPC operations.

## Create VPC

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.vpc import vpc_client, models
import os, json

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = vpc_client.VpcClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.CreateVpcRequest()
req.VpcName = "{{user.vpc_name}}"
req.CidrBlock = "{{user.cidr_block}}"
req.ClientToken = str(int(time.time() * 1000000))

resp = client.CreateVpc(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

## Describe VPCs

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.vpc import vpc_client, models
import os, json

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = vpc_client.VpcClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.DescribeVpcsRequest()
req.VpcIds = [os.environ.get("VPC_ID", "vpc-xxx")]

resp = client.DescribeVpcs(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## Delete VPC

```python
req = models.DeleteVpcRequest()
req.VpcId = "{{user.vpc_id}}"
resp = client.DeleteVpc(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## Create Subnet

```python
req = models.CreateSubnetRequest()
req.VpcId = "{{output.vpc_id}}"
req.SubnetName = "{{user.subnet_name}}"
req.CidrBlock = "{{user.subnet_cidr}}"
req.Zone = "{{user.zone}}"
resp = client.CreateSubnet(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## Delete Subnet

```python
req = models.DeleteSubnetRequest()
req.SubnetId = "{{user.subnet_id}}"
resp = client.DeleteSubnet(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## Describe Subnets

```python
req = models.DescribeSubnetsRequest()
req.VpcId = "{{user.vpc_id}}"
req.Offset = 0
req.Limit = 100
resp = client.DescribeSubnets(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## Create Route Table

```python
req = models.CreateRouteTableRequest()
req.VpcId = "{{user.vpc_id}}"
req.RouteTableName = "{{user.route_table_name}}"
resp = client.CreateRouteTable(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## Describe Route Tables

```python
req = models.DescribeRouteTablesRequest()
req.RouteTableIds = ["{{user.route_table_id}}"]
resp = client.DescribeRouteTables(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## Delete Route Table

```python
req = models.DeleteRouteTableRequest()
req.RouteTableId = "{{user.route_table_id}}"
resp = client.DeleteRouteTable(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## Create VPC Peering Connection

```python
req = models.CreateVpcPeeringConnectionRequest()
req.VpcId = "{{user.local_vpc_id}}"
req.PeerVpcId = "{{user.peer_vpc_id}}"
req.PeerRegion = os.environ.get("TENCENTCLOUD_REGION")
req.PeeringConnectionName = "{{user.peering_name}}"
if "{{user.peer_account_id}}":
    req.PeerAccountId = "{{user.peer_account_id}}"
resp = client.CreateVpcPeeringConnection(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

## Accept VPC Peering Connection

```python
req = models.AcceptVpcPeeringConnectionRequest()
req.PeeringConnectionId = "{{user.peering_connection_id}}"
resp = client.AcceptVpcPeeringConnection(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

## Describe VPC Peering Connections

```python
req = models.DescribeVpcPeeringConnectionsRequest()
req.Filters = [{"Name": "vpc-id", "Values": ["{{user.vpc_id}}"]}]
req.Offset = 0
req.Limit = 100
resp = client.DescribeVpcPeeringConnections(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## Delete VPC Peering Connection

```python
req = models.DeleteVpcPeeringConnectionRequest()
req.PeeringConnectionId = "{{user.peering_connection_id}}"
resp = client.DeleteVpcPeeringConnection(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```
