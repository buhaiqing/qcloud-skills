# VPC Troubleshooting Guide

## Error Code Reference

### Common VPC Errors

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter.InvalidCidr` | CIDR format invalid | Use valid RFC 1918 CIDR |
| `InvalidParameter.InvalidVpcName` | VPC name invalid | Use 1-60 alphanumeric chars |
| `InvalidParameter.InvalidSubnetName` | Subnet name invalid | Use valid name format |
| `InvalidParameter.InvalidZone` | Zone not in region | Use zone from DescribeZones |
| `ResourceNotFound.InvalidVpc` | VPC not found | Verify VpcId via DescribeVpcs |
| `ResourceNotFound.InvalidSubnet` | Subnet not found | Verify SubnetId |
| `ResourceNotFound.InvalidRouteTableId` | Route table not found | Verify route table ID |
| `ResourceQuotaExceeded.Vpc` | VPC quota exceeded | Delete unused or request increase |
| `ResourceQuotaExceeded.Subnet` | Subnet quota exceeded | Delete unused or increase quota |
| `InvalidVpc.StateMismatch` | VPC state error | Wait for VPC to reach stable state |
| `InvalidSubnet.CidrConflict` | CIDR overlap | Use different CIDR |
| `InvalidSubnet.NotInVpcCidr` | Subnet CIDR outside VPC | Use subset of VPC CIDR |
| `InvalidSecretKey` | Credential invalid | Verify SecretKey configuration |
| `InvalidSecretId` | Credential ID invalid | Verify SecretId |
| `RequestLimitExceeded` | API rate limit | Exponential backoff (2s, 4s, 8s) |
| `InternalError` | Server error | Retry; escalate with RequestId |
| `OperationConflict` | Concurrent operation | Wait 30s and retry (3x) |

## Diagnostic Procedures

### Issue 1: VPC Creation Failure

**Symptom:** CreateVpc returns error

**Diagnosis Steps:**
1. Check CIDR format validity
2. Verify quota (DescribeVpcs to count existing)
3. Check credentials
4. Validate region

**Resolution:**
```bash
# Step 1: Verify CIDR format
CIDR="10.0.0.0/16"
if [[ $CIDR =~ ^10\. ]] || [[ $CIDR =~ ^172\.(1[6-9]|2[0-9]|3[0-1])\. ]] || [[ $CIDR =~ ^192\.168\. ]]; then
  echo "Valid RFC 1918 CIDR"
else
  echo "Invalid CIDR - use 10.0.0.0/16 or 172.16.0.0/16"
fi

# Step 2: Check quota
COUNT=$(tccli vpc DescribeVpcs | jq -r '.Response.TotalCount')
if [ $COUNT -ge 5 ]; then
  echo "Quota exceeded - delete unused or request increase"
fi

# Step 3: Verify credentials
tccli vpc DescribeZones --Region ap-guangzhou || echo "Credential error"
```

### Issue 2: Subnet CIDR Conflict

**Symptom:** CreateSubnet fails with `InvalidSubnet.CidrConflict`

**Diagnosis:**
```bash
# List existing subnet CIDRs in VPC
tccli vpc DescribeSubnets \
  --Filters "[{\"Name\":\"vpc-id\",\"Values\":[\"vpc-xxx\"]}]" \
  | jq -r '.Response.SubnetSet[].CidrBlock'

# Check if proposed CIDR overlaps
PROPOSED_CIDR="10.0.1.0/24"
EXISTING_CIDRS=$(tccli vpc DescribeSubnets --Filters "[{\"Name\":\"vpc-id\",\"Values\":[\"vpc-xxx\"]}]" | jq -r '.Response.SubnetSet[].CidrBlock')

# Simple overlap check (use Python for complex CIDR math)
python3 -c "
import ipaddress
proposed = ipaddress.ip_network('$PROPOSED_CIDR')
existing = [ipaddress.ip_network(cidr) for cidr in '$EXISTING_CIDRS'.split()]
for net in existing:
    if proposed.overlaps(net):
        print(f'Conflict with {net}')
"
```

**Resolution:**
- Choose non-overlapping CIDR
- Use systematic allocation (10.0.1.0/24, 10.0.2.0/24, etc.)

### Issue 3: Cannot Delete VPC

**Symptom:** DeleteVpc fails

**Causes:**
1. VPC contains subnets
2. Subnets contain CVM instances
3. VPC has CLB attachments
4. VPC has NAT gateway
5. VPC has VPN gateway

**Diagnosis:**
```bash
# Check for subnets
tccli vpc DescribeSubnets --Filters "[{\"Name\":\"vpc-id\",\"Values\":[\"vpc-xxx\"]}]" | jq -r '.Response.TotalCount'

# Check for instances (requires cvm skill)
tccli cvm DescribeInstances --Filters "[{\"Name\":\"vpc-id\",\"Values\":[\"vpc-xxx\"]}]" | jq -r '.Response.TotalCount'

# Check for CLB (requires clb skill)
tccli clb DescribeLoadBalancers --Filters "[{\"Name\":\"vpc-id\",\"Values\":[\"vpc-xxx\"]}]" | jq -r '.Response.TotalCount'
```

**Resolution:**
1. Delete instances first
2. Delete CLBs
3. Delete NAT/VPN gateways
4. Delete subnets
5. Delete VPC

### Issue 4: Connectivity Issues

**Symptom:** CVM in subnet cannot connect to internet or other instances

**Diagnosis Flow:**

```
1. Check subnet has route table
   ↓
2. Check route table has internet route (via NAT or EIP)
   ↓
3. Check CVM has security group allowing traffic
   ↓
4. Check subnet has network ACL allowing traffic
   ↓
5. Check CVM has public IP or NAT gateway exists
```

**Diagnostic Commands:**
```bash
# Check subnet route table
tccli vpc DescribeSubnets --SubnetIds "[\"subnet-xxx\"]" | jq -r '.Response.SubnetSet[0].RouteTableId'

# Check route table routes
ROUTE_TABLE_ID="rtb-xxx"
tccli vpc DescribeRouteTables --RouteTableIds "[\"$ROUTE_TABLE_ID\"]" | jq '.Response.RouteTableSet[0].RouteSet'

# Check CVM security groups
tccli cvm DescribeInstances --InstanceIds "[\"ins-xxx\"]" | jq '.Response.InstanceSet[0].SecurityGroupSet'
```

**Resolution:**
- Add route: 0.0.0.0/0 → NAT Gateway or EIP
- Modify security group to allow outbound
- Modify network ACL if restrictive

### Issue 5: VPC Peering Connection Issues

**Symptom:** Instances in peered VPCs cannot communicate

**Causes:**
1. Peering connection not accepted
2. Route table missing peering route
3. Security group blocking traffic
4. Network ACL blocking traffic

**Diagnosis:**
```bash
# Check peering connection status
tccli vpc DescribeVpcPeeringConnections --Filters "[{\"Name\":\"vpc-id\",\"Values\":[\"vpc-xxx\"]}]"

# Check route table has peering route
tccli vpc DescribeRouteTables --RouteTableIds "[\"rtb-xxx\"]" | jq '.Response.RouteTableSet[0].RouteSet[] | select(.NextHopType == "PEERCONNECTION")'
```

### Issue 6: Rate Limiting

**Symptom:** `RequestLimitExceeded` error

**Resolution:**
```bash
# Implement exponential backoff
for i in 1 2 3; do
  RESULT=$(tccli vpc DescribeVpcs --Region ap-guangzhou)
  if echo "$RESULT" | jq -e '.Response.Error.Code == "RequestLimitExceeded"'; then
    sleep $((2**i))
    continue
  fi
  break
done
```

## Product-Specific Patterns

### Pattern: Subnet Creation Loop

**Issue:** Creating multiple subnets in sequence fails

**Cause:** Concurrent operation conflict

**Solution:**
```bash
# Sequential with wait
for ZONE in "ap-guangzhou-1" "ap-guangzhou-2" "ap-guangzhou-3"; do
  tccli vpc CreateSubnet \
    --VpcId "vpc-xxx" \
    --SubnetName "subnet-$ZONE" \
    --CidrBlock "10.0.$((i)).0/24" \
    --Zone "$ZONE"
  
  # Wait 5 seconds between operations
  sleep 5
done
```

### Pattern: CIDR Planning Error

**Issue:** Subnet CIDR overlaps with on-premise network

**Cause:** Hybrid cloud conflict

**Solution:**
- Document on-premise CIDR ranges before planning
- Use dedicated CIDR block for cloud (avoid overlap)
- Consider using CCN for routing between networks

## Agent Diagnostic Workflow

```
User reports VPC issue
    ↓
1. Ask: VPC ID, error message, desired outcome
    ↓
2. Run DescribeVpcs/DescribeSubnets to verify existence
    ↓
3. Check state (AVAILABLE/CREATING/etc.)
    ↓
4. Identify error code from API response
    ↓
5. Map error to recovery action
    ↓
6. Execute fix with validation
    ↓
7. Report result with evidence
```

## Error Message Format

**Standard format for agent responses:**
```
[ERROR] <Code>: <Summary>

What happened: <Context>

How to fix: <Specific action>

Next step: <Agent action or user guidance>
```

**Example:**
```
[ERROR] InvalidSubnet.CidrConflict: Subnet CIDR overlaps

What happened: Proposed CIDR 10.0.1.0/24 conflicts with existing subnet subnet-xxx (10.0.1.0/24)

How to fix: Use non-overlapping CIDR from VPC range. Available CIDRs: 10.0.2.0/24, 10.0.3.0/24

Next step: Ask user to choose available CIDR or retry with suggested CIDR
```

## References

- [VPC Error Codes](https://cloud.tencent.com/document/api/215/32811)
- [VPC Troubleshooting](https://cloud.tencent.com/document/product/215/39110)