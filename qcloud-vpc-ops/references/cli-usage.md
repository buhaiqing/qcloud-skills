# VPC CLI Usage

## tccli Overview

`tccli` is the official Tencent Cloud CLI tool for managing VPC resources. It supports JSON output by default and uses environment credentials.

### Installation

```bash
pip install tccli
tccli version
```

### Configuration

```bash
# Environment variables (recommended for agents)
export TENCENTCLOUD_SECRET_ID="AKID..."
export TENCENTCLOUD_SECRET_KEY="..."
export TENCENTCLOUD_REGION="ap-guangzhou"

# Or interactive config
tccli configure
```

## CLI Command Structure

```bash
tccli vpc <Action> [--Param1 value1] [--Param2 value2] ...
```

### Common Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| --Region | Target region | `ap-guangzhou` |
| --VpcId | VPC ID | `vpc-abcdefgh` |
| --SubnetId | Subnet ID | `subnet-xxx` |

## VPC Operations

### Create VPC

```bash
tccli vpc CreateVpc \
  --Region ap-guangzhou \
  --VpcName "my-vpc" \
  --CidrBlock "10.0.0.0/16"
```

**Output:**
```json
{
  "Response": {
    "Vpc": {
      "VpcId": "vpc-abcdefgh",
      "VpcName": "my-vpc",
      "CidrBlock": "10.0.0.0/16",
      "State": "CREATING"
    },
    "RequestId": "abc123"
  }
}
```

**Parse VpcId:**
```bash
VPC_ID=$(tccli vpc CreateVpc --Region ap-guangzhou --VpcName "test" --CidrBlock "10.0.0.0/16" | jq -r '.Response.Vpc.VpcId')
echo "Created VPC: $VPC_ID"
```

### Describe VPCs

```bash
# List all VPCs
tccli vpc DescribeVpcs --Region ap-guangzhou

# Describe specific VPC
tccli vpc DescribeVpcs --Region ap-guangzhou --VpcIds "[\"vpc-xxx\"]"

# Paginated query
tccli vpc DescribeVpcs --Region ap-guangzhou --Offset 0 --Limit 50
```

**Parse fields:**
```bash
# Get VPC count
COUNT=$(tccli vpc DescribeVpcs --Region ap-guangzhou | jq -r '.Response.TotalCount')

# List VPC IDs
tccli vpc DescribeVpcs --Region ap-guangzhou | jq -r '.Response.VpcSet[].VpcId'

# Get specific VPC state
tccli vpc DescribeVpcs --VpcIds "[\"vpc-xxx\"]" | jq -r '.Response.VpcSet[0].State'
```

### Modify VPC Attribute

```bash
tccli vpc ModifyVpcAttribute \
  --Region ap-guangzhou \
  --VpcId "vpc-xxx" \
  --VpcName "renamed-vpc"
```

### Delete VPC

```bash
tccli vpc DeleteVpc \
  --Region ap-guangzhou \
  --VpcId "vpc-xxx"
```

**Safety check before deletion:**
```bash
# Verify no instances in VPC
INSTANCE_COUNT=$(tccli cvm DescribeInstances --Filters "[{\"Name\":\"vpc-id\",\"Values\":[\"vpc-xxx\"]}]" | jq -r '.Response.TotalCount')

if [ "$INSTANCE_COUNT" -eq 0 ]; then
  tccli vpc DeleteVpc --VpcId "vpc-xxx"
else
  echo "Cannot delete: $INSTANCE_COUNT instances in VPC"
fi
```

## Subnet Operations

### Create Subnet

```bash
tccli vpc CreateSubnet \
  --Region ap-guangzhou \
  --VpcId "vpc-xxx" \
  --SubnetName "web-subnet" \
  --CidrBlock "10.0.1.0/24" \
  --Zone "ap-guangzhou-1"
```

**Parse SubnetId:**
```bash
SUBNET_ID=$(tccli vpc CreateSubnet \
  --VpcId "vpc-xxx" \
  --SubnetName "web" \
  --CidrBlock "10.0.1.0/24" \
  --Zone "ap-guangzhou-1" | jq -r '.Response.Subnet.SubnetId')
```

### Describe Subnets

```bash
# List all subnets in region
tccli vpc DescribeSubnets --Region ap-guangzhou

# List subnets in specific VPC
tccli vpc DescribeSubnets --Region ap-guangzhou --Filters "[{\"Name\":\"vpc-id\",\"Values\":[\"vpc-xxx\"]}]"

# Describe specific subnet
tccli vpc DescribeSubnets --SubnetIds "[\"subnet-xxx\"]"
```

### Delete Subnet

```bash
tccli vpc DeleteSubnet \
  --Region ap-guangzhou \
  --SubnetId "subnet-xxx"
```

## Route Table Operations

### Create Route Table

```bash
tccli vpc CreateRouteTable \
  --Region ap-guangzhou \
  --VpcId "vpc-xxx" \
  --RouteTableName "custom-route"
```

### Describe Route Tables

```bash
tccli vpc DescribeRouteTables \
  --Region ap-guangzhou \
  --Filters "[{\"Name\":\"vpc-id\",\"Values\":[\"vpc-xxx\"]}]"
```

### Delete Route Table

```bash
tccli vpc DeleteRouteTable \
  --Region ap-guangzhou \
  --RouteTableId "rtb-xxx"
```

## Network ACL Operations

### Create Network ACL

```bash
tccli vpc CreateNetworkAcl \
  --Region ap-guangzhou \
  --VpcId "vpc-xxx"
```

### Describe Network ACLs

```bash
tccli vpc DescribeNetworkAcls \
  --Region ap-guangzhou \
  --Filters "[{\"Name\":\"vpc-id\",\"Values\":[\"vpc-xxx\"]}]"
```

## Filter Usage

Filters allow flexible querying:

| Filter Name | Values | Description |
|-------------|--------|-------------|
| vpc-id | ["vpc-xxx"] | Filter by VPC |
| subnet-id | ["subnet-xxx"] | Filter by subnet |
| zone | ["ap-guangzhou-1"] | Filter by zone |
| is-default | ["true"] | Filter default VPC |
| cidr-block | ["10.0.0.0/16"] | Filter by CIDR |

**Example:**
```bash
# Find VPC by CIDR
tccli vpc DescribeVpcs --Filters "[{\"Name\":\"cidr-block\",\"Values\":[\"10.0.0.0/16\"]}]"

# Find subnets in zone
tccli vpc DescribeSubnets --Filters "[{\"Name\":\"zone\",\"Values\":[\"ap-guangzhou-1\"]}]"
```

## jq Parsing Patterns

### Common Extraction Patterns

```bash
# Extract single field
jq -r '.Response.Vpc.VpcId'

# Extract array elements
jq -r '.Response.VpcSet[].VpcId'

# Extract nested object
jq -r '.Response.VpcSet[0].SubnetSet[].SubnetId'

# Count results
jq -r '.Response.TotalCount'

# Filter by state
jq '.Response.VpcSet[] | select(.State == "AVAILABLE")'

# Format as table
jq -r '.Response.VpcSet[] | [.VpcId, .VpcName, .CidrBlock] | @tsv'
```

### Full Pipeline Example

```bash
# Create VPC and wait for availability
VPC_ID=$(tccli vpc CreateVpc \
  --VpcName "test" \
  --CidrBlock "10.0.0.0/16" | jq -r '.Response.Vpc.VpcId')

for i in $(seq 1 24); do
  STATE=$(tccli vpc DescribeVpcs --VpcIds "[\"$VPC_ID\"]" | jq -r '.Response.VpcSet[0].State')
  [ "$STATE" = "AVAILABLE" ] && break
  sleep 5
done

echo "VPC $VPC_ID is ready"
```

## Coverage vs SDK

| Operation | CLI Support | SDK Required? |
|-----------|-------------|---------------|
| CreateVpc | ✓ | No |
| DescribeVpcs | ✓ | No |
| DeleteVpc | ✓ | No |
| CreateSubnet | ✓ | No |
| DescribeSubnets | ✓ | No |
| DeleteSubnet | ✓ | No |
| CreateRouteTable | ✓ | No |
| DescribeRouteTables | ✓ | No |
| DeleteRouteTable | ✓ | No |
| CreateRoutes | ✓ | No |
| DeleteRoutes | ✓ | No |
| ModifyRouteTableAttribute | ✓ | No |
| CreateNetworkAcl | ✓ | No |
| DescribeNetworkAcls | ✓ | No |
| DeleteNetworkAcl | ✓ | No |

**Note:** VPC has full CLI coverage. SDK is rarely needed except for complex multi-step workflows.

## Environment Variables

CLI respects these environment variables:

| Variable | Priority | Description |
|----------|----------|-------------|
| TENCENTCLOUD_SECRET_ID | Highest | API key ID |
| TENCENTCLOUD_SECRET_KEY | Highest | API secret key |
| TENCENTCLOUD_REGION | Highest | Default region |

**Verification:**
```bash
# Check credentials (safe)
test -n "$TENCENTCLOUD_SECRET_ID" && echo "✓ SecretId configured"
test -n "$TENCENTCLOUD_SECRET_KEY" && echo "✓ SecretKey configured"
test -n "$TENCENTCLOUD_REGION" && echo "✓ Region: $TENCENTCLOUD_REGION"
```

## Debug Mode

```bash
# Debug (mask credentials in output)
tccli vpc DescribeVpcs --debug 2>&1 | grep -v "SecretKey"
```

## References

- [tccli Documentation](https://cloud.tencent.com/document/product/440)
- [VPC CLI Reference](https://cloud.tencent.com/document/product/215/41817)