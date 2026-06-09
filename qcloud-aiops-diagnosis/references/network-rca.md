# Network RCA — Rule G (VPC Path Diagnosis)

> **Read-only network path evidence.** Rule **G** extends multi-source RCA when symptoms suggest connectivity failure but compute/data layers look healthy. Collection delegated read-only to `qcloud-vpc-ops` patterns; mutations stay with product skills.

## 1. When to Apply Rule G

| Symptom pattern | Rule G? | Also run |
|---|---|---|
| Connection timeout / refused; CVM/CDB/Redis metrics normal | **Yes** | Product rule H/I + CLS logs |
| `NodeNotReady` but CVM `DescribeInstances` = Running, disk/CPU normal | **Yes** | Rule D |
| CLB 5xx; backends Running; pod not CrashLoop | **Yes** | Rule A |
| CloudAudit `ModifySecurityGroupPolicies` in window | **Yes** | Rule F (F4) |
| Pure app bug with no network signals | No | Product RCA only |

## 2. Evidence Model Extensions

```json
{
  "entity_type": "security_group|route_table|nat_gateway|vpc_subnet|network_acl",
  "source": "vpc|cloudaudit|monitor",
  "signal": "config|status|metric",
  "metric_or_pattern": "SgDrop|NatConn|RouteMissing|AclDeny",
  "linkage": {
    "vpc_id": "vpc-xxx",
    "subnet_id": "subnet-xxx",
    "security_group_id": "sg-xxx",
    "instance_id": "ins-xxx",
    "nat_gateway_id": "nat-xxx"
  }
}
```

Resolve `vpc_id` / `subnet_id` from CVM `DescribeInstances`, CDB/Redis `DescribeInstances`, or TKE cluster network fields when not supplied.

## 3. Collection (Read-Only)

| Step | CLI | Purpose |
|---|---|---|
| 1 | `tccli cvm DescribeInstances --InstanceIds '["{{user.instance_id}}"]'` | SG IDs, VPC/subnet, private IP |
| 2 | `tccli vpc DescribeSecurityGroups --Filters '[{"Name":"security-group-id","Values":["sg-xxx"]}]'` | Inbound/outbound rules |
| 3 | `tccli vpc DescribeSecurityGroupPolicies --SecurityGroupId sg-xxx` | Rule detail (if API available in env) |
| 4 | `tccli vpc DescribeRouteTables --Filters '[{"Name":"vpc-id","Values":["{{user.vpc_id}}"]}]'` | Missing route / wrong next-hop |
| 5 | `tccli vpc DescribeNatGateways --Filters '[{"Name":"vpc-id","Values":["{{user.vpc_id}}"]}]'` | NAT state, connection capacity |
| 6 | `tccli cloudaudit LookUpEvents` (network event names) | Recent SG/route/NAT changes |

> Verify actions with `tccli vpc help`. Field names vary; preserve raw excerpts on mapping failure.

**Degraded:** Missing `vpc_id` → infer from instance; if still unknown, skip VPC layer, warn, avoid HIGH for network-root hypotheses.

## 4. Rule G: Scoring

| Evidence Layer | Signal | Scoring |
|---|---|---|
| CLS/app logs | `Connection timed out`, `ECONNREFUSED`, `no route to host` | Trigger |
| Security group | New deny rule; missing allow on service port; `0.0.0.0/0` removed | +3 root if change precedes symptom |
| Route table | No route to destination; blackhole; wrong peering next-hop | +3 root |
| NAT gateway | State not AVAILABLE; connection count at limit | +2 root |
| CVM/CDB/backend | Instance Running; product metrics normal | +1 supports network (not compute) root |
| CloudAudit | `ModifySecurityGroupPolicies` / `ModifyRouteTable` in lead window | +2 with Rule F F4 |
| CLB | Healthy targets but client timeout | +1 symptom of path not backend |

### Hypotheses

| ID | Narrative | Root entity | HIGH when |
|---|---|---|---|
| **G1** | SG change blocked service port → connection refused | `security_group` | Audit + SG rule gap + symptom match |
| **G2** | Route missing / peering broken → timeout | `route_table` | No valid route to CIDR; peering DOWN |
| **G3** | NAT exhaustion or failure → egress broken | `nat_gateway` | NAT not AVAILABLE or conn limit |
| **G4** | NACL / subnet isolation (rare) | `vpc_subnet` | ACL deny + same subnet path |
| **G5** | Backend/app issue (network ruled out) | `app` or product layer | All VPC checks pass |

### Verification steps

```bash
tccli cvm DescribeInstances --InstanceIds '["{{user.instance_id}}"]'
tccli vpc DescribeSecurityGroups --Filters '[{"Name":"vpc-id","Values":["{{user.vpc_id}}"]}]'
tccli vpc DescribeRouteTables --Filters '[{"Name":"vpc-id","Values":["{{user.vpc_id}}"]}]'
tccli vpc DescribeNatGateways --Filters '[{"Name":"vpc-id","Values":["{{user.vpc_id}}"]}]'
tccli cloudaudit LookUpEvents --StartTime {{user.time_start_epoch}} --EndTime {{user.time_end_epoch}} --MaxResults 100
```

## 5. Topology Links (Network Layer)

```json
[
  {"from_type":"cvm_instance","from_id":"ins-xxx","to_type":"security_group","to_id":"sg-xxx","via":"SecurityGroupIds"},
  {"from_type":"cvm_instance","from_id":"ins-xxx","to_type":"vpc_subnet","to_id":"subnet-xxx","via":"SubnetId"},
  {"from_type":"vpc_subnet","from_id":"subnet-xxx","to_type":"route_table","to_id":"rtb-xxx","via":"RouteTableId"},
  {"from_type":"vpc_subnet","from_id":"subnet-xxx","to_type":"nat_gateway","to_id":"nat-xxx","via":"NatGatewayId"}
]
```

## 6. RCA Bundle Fields

```json
"evidence_by_layer": {
  "vpc_network": {
    "sources_used": 3,
    "evidence_count": 4,
    "status": "complete|partial|unavailable",
    "latest_timestamp": "2026-06-09T10:12:00+08:00"
  }
},
"network_rca": {
  "rule": "G",
  "top_hypothesis_id": "G1",
  "vpc_id": "vpc-xxx",
  "findings": ["SG sg-xxx missing inbound TCP/443 after 10:01 change"]
}
```

Link Rule **F4** (change-correlation): when `likely_change_trigger.change_type=network`, set `hypothesis_id` to **G1** or **G2** and merge change timeline.

## 7. Delegation

| Finding | Delegate to |
|---|---|
| SG rule fix | `qcloud-vpc-ops` |
| Route / peering | `qcloud-vpc-ops` |
| NAT scale / replace | `qcloud-vpc-ops` |
| Backend still unhealthy after network clean | Product skill (CVM/CDB/TKE/CLB) |

All recommendations: `RECOMMENDATION (not execution)`.

## 8. Changelog

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-06-09 | Rule G VPC path diagnosis, SG/route/NAT evidence, topology links, F4 integration |
