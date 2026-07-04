# CCN Execution Flows

> 从 `SKILL.md` 提取。所有操作的 Pre-flight → Execute → Validate → Recover 流程。

## Create CCN

### Pre-flight

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI | `tccli version` | Exit 0 | Install CLI |
| Credentials | Check env vars | Non-empty | HALT |
| Region | `tccli vpc DescribeRegions` | Valid region | Suggest valid region |

### CLI

```bash
tccli vpc CreateCcn \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnName "{{user.ccn_name}}" \
  --CcnDescription "CCN created by agent" \
  --QosLevel "AG"
```

### SDK

```python
req = models.CreateCcnRequest()
req.CcnName = "global-mesh"
req.CcnDescription = "CCN created by agent"
req.QosLevel = "AG"
resp = client.CreateCcn(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

### Post-execution

```bash
for i in $(seq 1 60); do
  STATE=$(tccli vpc DescribeCcnRegions \
    --CcnId "{{output.ccn_id}}" \
    --Region "{{env.TENCENTCLOUD_REGION}}" \
    | jq -r '.Response.CcnRegionStateSet[0].State // "UNKNOWN"')
  [ "$STATE" = "AVAILABLE" ] && break
  sleep 5
done
```

---

## Describe CCNs

```bash
tccli vpc DescribeCcnRegions \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=ccn-id,Values={{user.ccn_id}}"
```

---

## Attach Instances

```bash
tccli vpc AttachCcnInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnId "{{output.ccn_id}}" \
  --InstanceType "VPC" \
  --InstanceId "{{user.vpc_id}}" \
  --InstanceRegion "ap-guangzhou" \
  --InstanceUin "1000xxxxxx"
```

### Post-execution

```bash
for i in $(seq 1 60); do
  STATE=$(tccli vpc DescribeCcnAttachedInstances \
    --Region "{{env.TENCENTCLOUD_REGION}}" \
    --Filters "Name=ccn-id,Values={{output.ccn_id}}" \
    | jq -r '.Response.InstanceSet[0].State // "UNKNOWN"')
  [ "$STATE" = "AVAILABLE" ] && break
  sleep 5
done
```

---

## Detach Instances

```bash
tccli vpc DetachCcnInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnId "{{output.ccn_id}}" \
  --InstanceType "VPC" \
  --InstanceId "{{user.vpc_id}}" \
  --InstanceRegion "ap-guangzhou" \
  --InstanceUin "1000xxxxxx"
```

---

## Set Bandwidth

```bash
tccli vpc SetCcnRegionBandwidthLimits \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnId "{{output.ccn_id}}" \
  --CcnRegionBandwidthLimit '[{"CcnRegion1":"ap-guangzhou","CcnRegion2":"ap-shanghai","Bandwidth":1000}]'
```

---

## Add Static Route

```bash
tccli vpc CreateCcnRoute \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnId "{{output.ccn_id}}" \
  --DestinationCidrBlock "10.1.0.0/16" \
  --InstanceType "VPC" \
  --InstanceId "{{user.vpc_id}}" \
  --InstanceRegion "ap-guangzhou" \
  --RoutePolicy "CUSTOM"
```

---

## Describe Routes

```bash
tccli vpc DescribeCcnRoutes \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnId "{{output.ccn_id}}"
```

---

## Delete Route

```bash
tccli vpc DeleteCcnRoute \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnId "{{output.ccn_id}}" \
  --DestinationCidrBlock "10.1.0.0/16"
```

---

## Delete CCN

```bash
tccli vpc DeleteCcn \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnId "{{output.ccn_id}}"
```

---

## SD-WAN Hub-Spoke 拓扑部署

1. 创建 CCN（`CreateCCN`）
2. 关联总部 VPC（`AttachCcnInstances`，Hub）
3. 关联分支机构 VPC（`AttachCcnInstances`，Spokes）
4. 验证路由传播（`DescribeCcnRoutes`）

```bash
tccli vpc DescribeCcnAttachedInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=ccn-id,Values={{output.ccn_id}}"

tccli vpc DescribeCcnRoutes \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnId "{{output.ccn_id}}"
```

---

## QoS 策略配置

1. 查看当前带宽限制（`DescribeCcnRegionBandwidthLimits`）
2. 配置带宽限制（`SetCcnRegionBandwidthLimits`）
3. 验证配置（`DescribeCcnRegionBandwidthLimits`）

---

## 混合云互联（VPN over CCN）

1. 创建 VPN 网关（`qcloud-vpn-ops`）
2. 关联 VPN 网关到 CCN（`AttachCcnInstances`，`InstanceType=VPNGW`）
3. 配置 IPSec 隧道（`qcloud-vpn-ops`）
4. 配置路由（`CreateCcnRoute`）

---

## 故障切换（主备 CCN）

1. 检测主 CCN 故障（`DescribeCcnAttachedInstances`）
2. 切换流量到备用 CCN（更新 VPC 路由表或 DNS）
3. 验证切换（连通性测试）

---

## 应用感知路由配置

1. 定义应用分类（CIDR + DSCP）
2. 配置带宽限制（`SetCcnRegionBandwidthLimits`）
3. 配置静态路由（`CreateCcnRoute`）
4. 验证策略（`DescribeCcnRoutes`）
