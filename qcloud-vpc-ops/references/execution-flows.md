# VPC Execution Flows

> **Detailed CLI/SDK steps for all VPC operations**: This file provides operation-level hints and safety gates.

## Operation Index

| # | Operation | Key Hints |
|---|-----------|-----------|
| 1 | Create VPC | Verify CIDR format, check quota (≤5 VPCs default), use ClientToken for idempotency |
| 2 | Describe VPCs | Filter by VPC ID or region; paginate with Offset/Limit |
| 3 | Delete VPC | **Safety Gate**: Check no instances/CLB/NAT attached; confirm user |
| 4 | Create Subnet | Verify VPC exists, CIDR within VPC range, zone in region |
| 5 | Describe Subnets | Filter by VPC ID; check AvailableIpCount |
| 6 | Delete Subnet | **Safety Gate**: Check no CVM instances; warn disconnect |
| 7 | Create Route Table | Verify VPC exists; unique name required |
| 8 | Describe Route Tables | Filter by VPC ID or route table ID |
| 9 | Delete Route Table | **Safety Gate**: Check no subnets associated |
| 10 | Create VPC Peering | Verify both VPCs exist, same region, CIDR non-overlapping |
| 11 | Accept VPC Peering | Cross-account only; use acceptor credentials |
| 12 | Describe VPC Peering | Filter by VPC ID or peering ID |
| 13 | Delete VPC Peering | **Safety Gate**: Check route tables; warn blackhole risk |

---

## 1. Create VPC

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI installed | `tccli version` | Exit code 0 | Install tccli |
| Credentials | Check env vars | Non-empty | HALT; user configures |
| Region valid | `tccli vpc DescribeRegions` | Region exists | Suggest valid region |
| Quota | Describe quota API | ≤ 5 VPCs default | HALT if quota exceeded |
| CIDR format | Validate regex | Valid CIDR notation | Ask user for valid CIDR |

**CIDR Validation Example**:
```bash
# Validate CIDR format before API call
echo "{{user.cidr_block}}" | grep -qE '^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$' || { echo "Invalid CIDR format"; exit 1; }
```

### Execution — CLI (`tccli`) (Primary Path)

```bash
tccli vpc CreateVpc \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpcName "{{user.vpc_name}}" \
  --CidrBlock "{{user.cidr_block}}" \
  --ClientToken "$(date +%s%N)"
```

### Execution — Python SDK (Fallback Path)

> SDK code: see [sdk-code-examples.md](sdk-code-examples.md).

### Post-execution Validation

1. Capture `{{output.vpc_id}}` from `$.Response.Vpc.VpcId`
2. Poll DescribeVpcs until status = `AVAILABLE`:

```bash
for i in $(seq 1 24); do
  STATUS=$(tccli vpc DescribeVpcs --VpcIds "[\"{{output.vpc_id}}\"]" | jq -r '.Response.VpcSet[0].State')
  [ "$STATUS" = "AVAILABLE" ] && break
  sleep 5
done
```

### Failure Recovery

| Error pattern | Recovery |
|--------------|----------|
| `InvalidParameter.InvalidCidr` | Fix CIDR format |
| `ResourceQuotaExceeded.Vpc` | HALT; suggest quota increase |
| `InvalidSecretKey` | HALT; fix credentials |
| `ResourceAlreadyExists.Vpc` | Ask reuse or new name |
| `RequestLimitExceeded` | Backoff retry (2s,4s,8s) |

---

## 2. Describe VPCs

### Execution

```bash
tccli vpc DescribeVpcs \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpcIds "[\"{{user.vpc_id}}\"]"
```

### Execution — Python SDK (Fallback Path)

> SDK code: see [sdk-code-examples.md](sdk-code-examples.md).

### Present to User

| Field | Path |
|-------|------|
| VPC ID | `vpc.id` |
| VPC Name | `vpc.name` |
| CIDR | `vpc.cidr` |
| State | `vpc.state` |
| Subnets | `$.Response.VpcSet[0].SubnetSet` |

---

## 3. Delete VPC

### Pre-flight (Safety Gate)

- **MUST** check: no instances in VPC's subnets
- **MUST** check: no CLB or NAT gateway attached
- **MUST** obtain explicit user confirmation

**Pre-flight Validation Scripts**:
```bash
# Check no CVM instances in VPC subnets
tccli cvm DescribeInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=vpc-id,Values={{user.vpc_id}}"

# Check no CLB attached to VPC
tccli clb DescribeLoadBalancers \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=vpc-id,Values={{user.vpc_id}}"

# Check no NAT gateway attached
tccli vpc DescribeNatGateways \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=vpc-id,Values={{user.vpc_id}}"
```

### Execution

```bash
tccli vpc DeleteVpc \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpcId "{{user.vpc_id}}"
```

### Execution — Python SDK (Fallback Path)

> SDK code: see [sdk-code-examples.md](sdk-code-examples.md).

### Post-execution Validation

Poll DescribeVpcs until 404 or empty response (max 60s).

---

## 4. Create Subnet

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| VPC exists | DescribeVpcs | VPC AVAILABLE | HALT; create VPC first |
| CIDR subset | Validate CIDR | Within VPC CIDR | Ask valid subnet CIDR |
| No overlap | DescribeSubnets | No CIDR conflict | Ask different CIDR |
| Zone available | DescribeZones | Zone in region | Suggest valid zone |

### Execution — CLI

```bash
tccli vpc CreateSubnet \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpcId "{{output.vpc_id}}" \
  --SubnetName "{{user.subnet_name}}" \
  --CidrBlock "{{user.subnet_cidr}}" \
  --Zone "{{user.zone}}"
```

### Execution — Python SDK (Fallback Path)

> SDK code: see [sdk-code-examples.md](sdk-code-examples.md).

### Validation

Capture `{{output.subnet_id}}`, poll until `AVAILABLE`.

---

## 5. Delete Subnet

### Pre-flight (Safety Gate)

- **MUST** check: no CVM instances in subnet
- **MUST** check: subnet not default subnet
- **MUST** warn: instances will be disconnected

### Execution — CLI

```bash
tccli vpc DeleteSubnet \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --SubnetId "{{user.subnet_id}}"
```

### Execution — Python SDK (Fallback Path)

> SDK code: see [sdk-code-examples.md](sdk-code-examples.md).

### Validation

Poll DescribeSubnets until 404 or empty response (max 60s).

---

## 6. Describe Subnets

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| VPC exists | DescribeVpcs | VPC AVAILABLE | HALT; create VPC first |

### Execution — CLI

```bash
tccli vpc DescribeSubnets \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpcId "{{user.vpc_id}}"
```

### Execution — Python SDK (Fallback Path)

> SDK code: see [sdk-code-examples.md](sdk-code-examples.md).

### Present to User

| Field | Path |
|-------|------|
| Subnet ID | `subnet.id` |
| Subnet Name | `subnet.name` |
| CIDR | `subnet.cidr` |
| State | `vpc.state` |
| Zone | `subnet.zone` |
| Available IPs | `subnet.ips` |

---

## 7. Create Route Table

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| VPC exists | DescribeVpcs | VPC AVAILABLE | HALT; create VPC first |
| Route table name unique | DescribeRouteTables | No duplicate name | Use different name |

### Execution — CLI

```bash
tccli vpc CreateRouteTable \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpcId "{{user.vpc_id}}" \
  --RouteTableName "{{user.route_table_name}}"
```

### Execution — Python SDK (Fallback Path)

> SDK code: see [sdk-code-examples.md](sdk-code-examples.md).

### Validation

Capture `{{output.route_table_id}}` from `$.Response.RouteTable.RouteTableId`, poll until `AVAILABLE`.

---

## 8. Describe Route Tables

### Execution — CLI

```bash
tccli vpc DescribeRouteTables \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --RouteTableIds "[\"{{user.route_table_id}}\"]"
```

### Execution — Python SDK (Fallback Path)

> SDK code: see [sdk-code-examples.md](sdk-code-examples.md).

### Present to User

| Field | Path |
|-------|------|
| Route Table ID | `rtable.id` |
| Route Table Name | `rtable.name` |
| Routes | `rtable.routes` |
| Association | `$.Response.RouteTableSet[0].AssociationSet` |

---

## 9. Delete Route Table

### Pre-flight (Safety Gate)

- **MUST** check: no subnets associated with route table
- **MUST** obtain explicit user confirmation

### Execution — CLI

```bash
tccli vpc DeleteRouteTable \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --RouteTableId "{{user.route_table_id}}"
```

### Execution — Python SDK (Fallback Path)

> SDK code: see [sdk-code-examples.md](sdk-code-examples.md).

### Validation

Poll DescribeRouteTables until 404 or empty response (max 60s).

---

## 10. Create VPC Peering Connection

> **Scope boundary:** This operation covers **same-region, same- or cross-account VPC peering only**. For cross-region, multi-VPC hub-and-spoke, or internet-grade multi-account orchestration, use `qcloud-ccn-ops`. Peering is **non-transitive**: VPC A ↔ VPC B and VPC B ↔ VPC C do **not** enable A ↔ C.

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Both VPCs exist | `tccli vpc DescribeVpcs` for initiator + acceptor | Both `AVAILABLE` | HALT; create or recover missing VPC |
| Region match | Both `Region` fields equal | Same region | HALT — different regions require `qcloud-ccn-ops` |
| CIDR disjointness | Compute `{{user.local_cidr}}` ∩ `{{user.peer_cidr}}` | Empty intersection | HALT — overlap is rejected by API; would also break routing even if accepted |
| Quota | `tccli vpc DescribeVpcPeeringConnections` (count by region) | ≤ region quota | HALT; raise quota |
| Cross-account approval | Confirm peer account has the request accepted (or auto-accept flag set) | Approval path clear | For cross-account: HALT until requester has `AccepterUin` and peer account runs `AcceptVpcPeeringConnection` |

### Execution — CLI

```bash
# Initiator side: create the peering request
tccli vpc CreateVpcPeeringConnection \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpcId "{{user.local_vpc_id}}" \
  --PeerVpcId "{{user.peer_vpc_id}}" \
  --PeerRegion "{{env.TENCENTCLOUD_REGION}}" \
  --PeeringConnectionName "{{user.peering_name}}" \
  --PeerAccountId "{{user.peer_account_id}}"  # omit if same account
```

### Execution — Python SDK (Fallback Path)

> SDK code: see [sdk-code-examples.md](sdk-code-examples.md).

### Post-execution Validation

1. Capture `{{output.peering_connection_id}}` from `$.Response.PeeringConnectionId` (initial state: `PENDING_ACCEPTANCE` for cross-account, `ACTIVE` for same-account).
2. If cross-account, run the **Accept** flow below from the acceptor side; then **both** sides must add a route table entry to make the path routable (peering is a wire, **not** a route).
3. Poll until `Status = ACTIVE`:

```bash
for i in $(seq 1 24); do
  STATUS=$(tccli vpc DescribeVpcPeeringConnections \
    --PeeringConnectionIds "[\"{{output.peering_connection_id}}\"]" | \
    jq -r '.Response.PcSet[0].Status')
  case "$STATUS" in
    ACTIVE)            echo "peering active"; break ;;
    REJECTED|EXPIRED|DELETED) echo "terminal failure: $STATUS"; exit 1 ;;
  esac
  sleep 5
done
```

### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `InvalidParameter.CidrConflict` | The two VPC CIDR blocks overlap; pick a non-overlapping peer VPC or migrate one VPC's CIDR (irreversible) |
| `InvalidParameter.InvalidRegion` | Cross-region peering requested; delegate to `qcloud-ccn-ops` |
| `ResourceQuotaExceeded.PeerConn` | HALT; raise peering quota via console |
| `InvalidVpc.NotFound` | Verify `{{user.peer_vpc_id}}`; same-account only — for cross-account, use peer account's VPC ID |

---

## 11. Accept VPC Peering Connection (cross-account)

> **Required when:** initiator and acceptor belong to different accounts. The initiator creates a `PENDING_ACCEPTANCE` request; only the acceptor's credentials (running against their `TENCENTCLOUD_SECRET_ID/KEY`) can flip it to `ACTIVE`.

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Peer request pending | `DescribeVpcPeeringConnections` filtered by `PeeringConnectionName` | Status `PENDING_ACCEPTANCE` | HALT; nothing to accept |
| Accepting credentials | `TENCENTCLOUD_SECRET_ID` belongs to the **peer (acceptor) account** | Match | HALT; switch credentials to the accepting account |
| Accepting region | Run from a region in the same country/region family as the initiator | Same-region API endpoint | If API returns `InvalidParameter`, retry with the initiator's region |

### Execution — CLI

```bash
# Run with ACCEPTOR's credentials
tccli vpc AcceptVpcPeeringConnection \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --PeeringConnectionId "{{user.peering_connection_id}}"
```

### Execution — Python SDK (Fallback Path)

> SDK code: see [sdk-code-examples.md](sdk-code-examples.md).

### Post-execution Validation

Poll `DescribeVpcPeeringConnections` until `Status = ACTIVE` (max 60s). Then remind the user to **add route table entries on both sides** (peering is up but not yet routable).

### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `InvalidParameter.PendingAcceptanceNotFound` | Peering already accepted, expired, or deleted; re-query |
| `UnauthorizedOperation` | Running with initiator's credentials, not acceptor's; switch credentials |

---

## 12. Describe VPC Peering Connections

### Execution — CLI

```bash
tccli vpc DescribeVpcPeeringConnections \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --PeeringConnectionIds "[\"{{user.peering_connection_id}}\"]"
```

Filter by VPC ID (one-side pagination):

```bash
tccli vpc DescribeVpcPeeringConnections \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=vpc-id,Values={{user.vpc_id}}"
```

### Execution — Python SDK (Fallback Path)

> SDK code: see [sdk-code-examples.md](sdk-code-examples.md).

### Present to User

| Field | Path |
|-------|------|
| Peering ID | `$.Response.PcSet[].PeeringConnectionId` |
| Name | `$.Response.PcSet[].PeeringConnectionName` |
| Local VPC | `$.Response.PcSet[].VpcId` |
| Peer VPC | `$.Response.PcSet[].PeerVpcId` |
| Peer account | `$.Response.PcSet[].PeerAccountId` (Uin) |
| Region | `$.Response.PcSet[].PeerRegion` |
| Status | `$.Response.PcSet[].Status` (`PENDING_ACCEPTANCE` / `ACTIVE` / `REJECTED` / `EXPIRED` / `DELETED`) |
| Created | `$.Response.PcSet[].CreatedTime` |

---

## 13. Delete VPC Peering Connection

> **Important:** Deleting a peering connection does **not** automatically remove the route table entries that point at it. After deletion, those routes become blackholes and must be cleaned up — see [troubleshooting](troubleshooting.md).

### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation with both VPC IDs and the peering name.
- **MUST** list active route table entries that use the peering as next hop (via `DescribeRouteTables` on both sides); warn user that those routes will become blackholes unless they are removed **before or right after** the delete.
- **MUST** warn: any running CVM-to-CVM cross-VPC traffic over this peering will drop.

### Execution — CLI

```bash
tccli vpc DeleteVpcPeeringConnection \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --PeeringConnectionId "{{user.peering_connection_id}}"
```

### Execution — Python SDK (Fallback Path)

> SDK code: see [sdk-code-examples.md](sdk-code-examples.md).

### Post-execution Validation

Poll `DescribeVpcPeeringConnections` for the ID; expect empty / 404 within 60s.

### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.PeerConn` | Already deleted; treat as success |
| `ResourceInUse.PeerConn` | A route table still references the peering as next hop; delete the routes first, then retry |
| `InvalidStatus.NotActive` | Peering is `PENDING_ACCEPTANCE`; either accept first or have the initiator cancel |
