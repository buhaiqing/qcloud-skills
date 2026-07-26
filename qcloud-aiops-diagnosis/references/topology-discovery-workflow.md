# Topology Discovery Workflow

> Phase 1 of the active inspection cycle. Discovers CVM / CLB / VPC resources and builds a topology graph used by `selective_workflow` to determine which analyzers to run.

## Entry Condition

User triggers one of:
- `"巡检 [region]"`, `"cruise [region]"` → full discovery
- `"只巡检 CVM"`, `"cruise --services cvm,clb"` → selective discovery

## Topology Discovery Steps

### Step 1 — VPC Discovery

```bash
tccli vpc DescribeVpcs --region {{env.TENCENTCLOUD_REGION}} --output json
```

- Extract `VpcId`, `VpcName`, `CidrBlock`, `IsDefault`
- Add VPC nodes to graph

### Step 2 — CVM Instance Discovery

```bash
tccli cvm DescribeInstances \
  --region {{env.TENCENTCLOUD_REGION}} \
  --Filters.0.Name vpc-id \
  --Filters.0.Values.0 "{{user.vpc_id}}" \
  --output json
```

- Extract `InstanceId`, `InstanceName`, `InstanceType`, `InstanceState`
- Extract `VirtualPrivateCloud.VpcId` → bind CVM to VPC edge (`contains`)
- If no `vpc_id` given, enumerate all regions/zones

### Step 3 — CLB Discovery

```bash
tccli clb DescribeLoadBalancers --region {{env.TENCENTCLOUD_REGION}} --output json
```

- Extract `LoadBalancerId`, `LoadBalancerName`, `AddressType`, `VpcId`
- Bind CLB to VPC edge (`contains`)
- For each LB, call `DescribeTargets` to find backend CVMs → edge (`loadbalances`)

### Step 4 — VPC Peering

```bash
tccli vpc DescribeVpcPeeringConnections --region {{env.TENCENTCLOUD_REGION}} --output json
```

- Extract peering connections → node type `vpc_peering`
- Edge (`peers_with`) connects accepter VPC to requester VPC

### Step 5 — ENI Discovery

```bash
tccli vpc DescribeNetworkInterfaces \
  --region {{env.TENCENTCLOUD_REGION}} \
  --Filters.0.Name vpc-id \
  --Filters.0.Values.0 "{{user.vpc_id}}" \
  --output json
```

- Extract ENI → node type `eni`
- Bind ENI to parent CVM via edge (`binds_to`)

## Output Schema

```json
{
  "nodes": [
    {
      "id": "vpc-xxx",
      "type": "vpc | cvm | clb | eni | vpc_peering",
      "region": "ap-guangzhou",
      "name": "My VPC",
      "status": "available | running | ...",
      "metadata": {}
    }
  ],
  "edges": [
    {
      "source": "vpc-xxx",
      "target": "ins-xxx",
      "rel": "contains | loadbalances | peers_with | binds_to",
      "metadata": {}
    }
  ]
}
```

## Tier Priority (for selective workflow)

| Tier | Resource Type | Diagnostic Priority |
|------|-------------|-------------------|
| 0 | VPC | First — network foundation |
| 1 | CVM, CLB | Core compute/load balancing |
| 2 | ENI, EIP, NAT | Attachment resources |
| 3 | VPC Peering | Cross-VPC paths |
| 4 | CDN | Edge/cache layer |

## Error Handling

| Error | Action |
|-------|--------|
| `AuthFailure.SecretIdNotFound` | HALT — check `TENCENTCLOUD_SECRET_ID` |
| `ResourceNotFound` (empty result) | Continue with empty graph; analyzers will skip gracefully |
| `InternalError` | RETRY up to 3× with exponential backoff; then HALT |
| `InvalidParameter` (region) | RETRY with `ap-guangzhou` as fallback |
