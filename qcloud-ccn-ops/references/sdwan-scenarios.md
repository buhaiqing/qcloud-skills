# SD-WAN 场景指南 — 云联网 (CCN)

> 本文档描述使用 CCN 构建 SD-WAN 架构的场景和最佳实践。

## SD-WAN 概念

**SD-WAN (Software-Defined Wide Area Network)** 是软件定义广域网，通过集中控制、智能路由和应用感知来优化广域网连接。腾讯云 CCN 提供了 SD-WAN 的核心能力：

| SD-WAN 特性 | CCN 实现 |
|-------------|----------|
| 集中控制平面 | CCN 实例作为全局路由枢纽 |
| 智能路径选择 | CCN 路由表 + 策略路由 |
| 应用感知 | 基于 CIDR 的流量分类（需配合 CLB/SCF） |
| 加密传输 | VPN Gateway over CCN |
| 可观测性 | CCN 路由表 + Monitor 指标 |

## 场景一：多分支 Hub-Spoke 拓扑

### 架构图

```
                    ┌─────────────────┐
                    │   总部 (Hub)    │
                    │   VPC-Hub       │
                    │   10.0.0.0/16   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  分支1 VPC   │ │  分支2 VPC   │ │  分支3 VPC   │
    │  10.1.0.0/16 │ │  10.2.0.0/16 │ │  10.3.0.0/16 │
    └──────────────┘ └──────────────┘ └──────────────┘
```

### 配置步骤

1. **创建 CCN 实例**:
   ```bash
   tccli vpc CreateCCN \
     --Region "{{env.TENCENTCLOUD_REGION}}" \
     --CcnName "sdwan-hub-spoke" \
     --CcnDescription "SD-WAN Hub-Spoke拓扑" \
     --ClientToken "$(date +%s%N)"
   ```

2. **关联 VPC 到 CCN**:
   ```bash
   # 关联总部 VPC (Hub)
   tccli vpc AttachCcnInstances \
     --Region "{{env.TENCENTCLOUD_REGION}}" \
     --CcnId "{{output.ccn_id}}" \
     --Instances '[{"InstanceId":"{{user.hub_vpc_id}}","InstanceType":"VPC","InstanceRegion":"{{env.TENCENTCLOUD_REGION}}"}]'
   
   # 关联分支 VPCs (Spokes)
   tccli vpc AttachCcnInstances \
     --Region "{{env.TENCENTCLOUD_REGION}}" \
     --CcnId "{{output.ccn_id}}" \
     --Instances '[{"InstanceId":"{{user.branch1_vpc_id}}","InstanceType":"VPC","InstanceRegion":"{{user.branch1_region}}"}]'
   ```

3. **配置路由传播**:
   - 启用自动路由传播（默认）
   - 分支间路由通过 Hub 中转（避免全互联）

### 路由设计原则

| 原则 | 说明 | 实现方式 |
|------|------|----------|
| 汇聚路由 | 在 Hub VPC 汇总分支路由，减少路由条目 | CCN 路由表自动学习 |
| 路由过滤 | 控制分支间互访 | CCN 路由表策略路由 |
| 黑洞路由 | 为未分配网段配置黑洞路由防止环路 | CCN 静态路由 + 黑洞 CIDR |

## 场景二：QoS 策略配置

### 流量分类

| 优先级 | 应用类型 | DSCP 值 | 带宽保障 |
|--------|----------|---------|----------|
| P0 | VoIP / 视频会议 | EF (46) | 30% |
| P1 | 核心业务系统 | AF31 (26) | 40% |
| P2 | 普通办公流量 | AF21 (18) | 20% |
| P3 | 备份/批量传输 | BE (0) | 10% |

### 配置 QoS

```bash
# 配置带宽限制（跨区域）
tccli vpc SetCcnRegionBandwidthLimits \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnId "{{output.ccn_id}}" \
  --CcnBandwidthLimitSet '[{"SrcRegion":"{{env.TENCENTCLOUD_REGION}}","DestRegion":"{{user.remote_region}}","BandwidthLimit":500}]'
```

### QoS 最佳实践

| 场景 | 带宽策略 | 配置建议 |
|------|----------|----------|
| 优先级业务 | 保障带宽 | 设置最小带宽保障 |
| 批量传输 | 限速 | 设置最大带宽限制 |
| 突发流量 | 弹性带宽 | 使用按量计费模式 |

## 场景三：混合云互联（公有云与私有云）

### 架构图

```
┌─────────────────────────────────────────────────────────┐
│                     腾讯云 VPC                          │
│                    ┌─────────┐                          │
│                    │   CCN   │                          │
│                    └────┬────┘                          │
│                         │                              │
│         ┌───────────────┼───────────────┐              │
│         │               │               │              │
│         ▼               ▼               ▼              │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐          │
│   │ 云 VPC-A │   │ 云 VPC-B │   │ VPN GW   │          │
│   │ 广州     │   │ 上海     │   │          │          │
│   └──────────┘   └──────────┘   └─────┬────┘          │
└────────────────────────────────────────┼───────────────┘
                                         │
                                         │ IPSec VPN
                                         │
┌────────────────────────────────────────┼───────────────┐
│                    私有云 / 数据中心                     │
│                                    ┌──────────┐        │
│                                    │ Customer │        │
│                                    │ Gateway  │        │
│                                    └──────────┘        │
└────────────────────────────────────────────────────────┘
```

### 配置步骤

1. **创建 VPN 网关**（关联到 CCN）:
   ```bash
   tccli vpc CreateVpnGateway \
     --Region "{{env.TENCENTCLOUD_REGION}}" \
     --VpcId "{{user.vpc_id}}" \
     --VpnGatewayName "hybrid-vpn-gw" \
     --InternetMaxBandwidthOut 100
   ```

2. **关联 VPN 网关到 CCN**:
   ```bash
   tccli vpc AttachCcnInstances \
     --Region "{{env.TENCENTCLOUD_REGION}}" \
     --CcnId "{{output.ccn_id}}" \
     --Instances '[{"InstanceId":"{{output.vpn_gw_id}}","InstanceType":"VPNGW","InstanceRegion":"{{env.TENCENTCLOUD_REGION}}"}]'
   ```

3. **配置 IPSec 隧道**:
   ```bash
   tccli vpc CreateVpnConnection \
     --Region "{{env.TENCENTCLOUD_REGION}}" \
     --VpnGatewayId "{{output.vpn_gw_id}}" \
     --CustomerGatewayId "{{output.customer_gw_id}}" \
     --VpnConnectionName "dc-to-cloud" \
     --PreShareKey "{{user.pre_shared_key}}"
   ```

### 混合云路由设计

| 网段类型 | CIDR 示例 | 路由方式 |
|----------|-----------|----------|
| 云端 VPC | 10.0.0.0/16 | CCN 自动学习 |
| 私有云 | 172.16.0.0/12 | VPN 静态路由 → CCN |
| 分支机构 | 192.168.0.0/16 | CCN 自动学习 |

## 场景四：全球网络架构

### 架构图

```
┌─────────────────────────────────────────────────────────┐
│                      全球网络拓扑                       │
│                                                         │
│  ┌─────────────┐      ┌─────────────┐                  │
│  │  中国区 CCN │◄────►│  海外区 CCN  │                  │
│  │  (广州/上海) │      │  (香港/新加坡)│                  │
│  └──────┬──────┘      └──────┬──────┘                  │
│         │                    │                          │
│    ┌────┴────┐          ┌────┴────┐                    │
│    │         │          │         │                    │
│    ▼         ▼          ▼         ▼                    │
│ ┌─────┐ ┌─────┐     ┌─────┐ ┌─────┐                   │
│ │VPC-A│ │VPC-B│     │VPC-C│ │VPC-D│                   │
│ └─────┘ └─────┘     └─────┘ └─────┘                   │
└────────────────────────────────────────────────────────┘
```

### 全球组网配置

| 场景 | 配置方式 | 带宽建议 |
|------|----------|----------|
| 中国区互联 | 单 CCN，多区域 VPC | 100-500 Mbps |
| 中国-海外互联 | 双 CCN + 专线/VPN 互联 | 50-200 Mbps |
| 全球多区域 | 多 CCN 互联 | 按业务需求 |

### 全球网络最佳实践

1. **区域选择**: 根据用户分布选择就近接入点
2. **带宽规划**: 海外链路带宽通常小于中国区
3. **合规要求**: 遵守各区域数据本地化要求
4. **故障切换**: 配置跨区域主备链路

## 场景五：安全组网（VPN over CCN）

### 架构图

```
┌─────────────────────────────────────────────────────────┐
│                    腾讯云 VPC                            │
│                    ┌─────────┐                          │
│                    │   CCN   │                          │
│                    └────┬────┘                          │
│                         │                              │
│         ┌───────────────┼───────────────┐              │
│         │               │               │              │
│         ▼               ▼               ▼              │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐          │
│   │  VPC-A   │   │  VPC-B   │   │ VPN GW   │          │
│   │ (广州)   │   │ (上海)   │   │          │          │
│   └──────────┘   └──────────┘   └─────┬────┘          │
└────────────────────────────────────────┼───────────────┘
                                         │
                                         │ IPSec/SSL VPN
                                         │
┌────────────────────────────────────────┼───────────────┐
│                    分支机构                                │
│                                    ┌──────────┐        │
│                                    │ 分支路由器│        │
│                                    └──────────┘        │
└────────────────────────────────────────────────────────┘
```

### VPN over CCN 配置

1. **创建 VPN 网关**（关联到 CCN）:
   ```bash
   tccli vpc CreateVpnGateway \
     --Region "{{env.TENCENTCLOUD_REGION}}" \
     --VpcId "{{user.vpc_id}}" \
     --VpnGatewayName "branch-vpn-gw" \
     --InternetMaxBandwidthOut 100 \
     --Type "IPSEC"
   ```

2. **关联 VPN 网关到 CCN**:
   ```bash
   tccli vpc AttachCcnInstances \
     --Region "{{env.TENCENTCLOUD_REGION}}" \
     --CcnId "{{output.ccn_id}}" \
     --Instances '[{"InstanceId":"{{output.vpn_gw_id}}","InstanceType":"VPNGW","InstanceRegion":"{{env.TENCENTCLOUD_REGION}}"}]'
   ```

3. **配置分支 VPN 隧道**:
   ```bash
   tccli vpc CreateVpnConnection \
     --Region "{{env.TENCENTCLOUD_REGION}}" \
     --VpnGatewayId "{{output.vpn_gw_id}}" \
     --CustomerGatewayId "{{output.customer_gw_id}}" \
     --VpnConnectionName "branch-vpn" \
     --PreShareKey "{{user.pre_shared_key}}"
   ```

### 安全组网最佳实践

| 安全层 | 配置 | 说明 |
|--------|------|------|
| 传输加密 | IPSec/AES-256 | 所有流量加密 |
| 访问控制 | VPC 安全组 | 限制分支访问范围 |
| 认证 | 预共享密钥/证书 | VPN 隧道认证 |
| 审计 | CloudAudit | 记录所有网络操作 |

## 场景六：故障切换（主备 CCN）

### 架构图

```
     ┌─────────────────┐
     │    总部 VPC     │
     └────────┬────────┘
              │
    ┌─────────┴─────────┐
    │                   │
    ▼                   ▼
┌────────┐        ┌────────┐
│ CCN-主 │◄──────►│ CCN-备 │
│ Region1│  备份  │ Region2│
└────┬───┘        └────┬───┘
     │                 │
     ▼                 ▼
  分支 VPCs        分支 VPCs (只读/灾备)
```

### 故障切换步骤

1. **检测主 CCN 故障**:
   ```bash
   tccli vpc DescribeCcnAttachedInstances \
     --Region "{{env.TENCENTCLOUD_REGION}}" \
     --Filters "Name=ccn-id,Values={{user.primary_ccn_id}}"
   ```

2. **切换流量到备用 CCN**:
   - 更新 VPC 路由表指向备用 CCN
   - 或修改 DNS 解析指向备用区域

3. **验证切换**:
   ```bash
   # 检查分支连通性
   ping <hub-vpc-gateway>
   traceroute <core-service-ip>
   ```

### 故障切换最佳实践

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| 冷备 | 主故障后手动切换 | 低频访问 |
| 温备 | 主备同时关联，故障时切换路由 | 中频访问 |
| 热备 | 双活 CCN，负载均衡 | 高频访问 |

## 场景七：应用感知路由

### 架构图

```
┌─────────────────────────────────────────────────────────┐
│                    腾讯云 VPC                            │
│                    ┌─────────┐                          │
│                    │   CCN   │                          │
│                    └────┬────┘                          │
│                         │                              │
│         ┌───────────────┼───────────────┐              │
│         │               │               │              │
│         ▼               ▼               ▼              │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐          │
│   │  VPC-A   │   │  VPC-B   │   │  VPC-C   │          │
│   │ (VoIP)   │   │ (ERP)    │   │ (OA)     │          │
│   └──────────┘   └──────────┘   └──────────┘          │
└────────────────────────────────────────────────────────┘
```

### 应用分类

| 应用类型 | CIDR 示例 | QoS 优先级 | 带宽保障 |
|----------|-----------|------------|----------|
| VoIP/视频 | 10.0.1.0/24 | P0 | 30% |
| 核心业务 | 10.0.2.0/24 | P1 | 40% |
| 办公系统 | 10.0.3.0/24 | P2 | 20% |
| 批量传输 | 10.0.4.0/24 | P3 | 10% |

### 配置策略路由

```bash
# 为不同应用配置不同带宽限制
tccli vpc SetCcnRegionBandwidthLimits \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnId "{{output.ccn_id}}" \
  --CcnBandwidthLimitSet '[{"SrcRegion":"{{env.TENCENTCLOUD_REGION}}","DestRegion":"{{user.remote_region}}","BandwidthLimit":100}]'
```

## 场景八：运维与监控

### 监控指标

| 指标 | 告警阈值 | 处理建议 |
|------|----------|----------|
| 带宽利用率 | > 80% | 考虑扩容或流量调度 |
| 丢包率 | > 0.1% | 检查链路质量 |
| 延迟 | > 50ms | 检查路由路径 |
| CCN 实例状态 | 非 AVAILABLE | 立即检查 |

### 网络可视化

```bash
# 查看 CCN 路由表
tccli vpc DescribeCcnRoutes \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnId "{{output.ccn_id}}"

# 查看 CCN 关联实例
tccli vpc DescribeCcnAttachedInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=ccn-id,Values={{output.ccn_id}}"
```

### 故障诊断流程

1. **检查 CCN 状态**:
   ```bash
   tccli vpc DescribeCCNs \
     --Region "{{env.TENCENTCLOUD_REGION}}" \
     --CcnIds '["{{output.ccn_id}}"]'
   ```

2. **检查关联实例状态**:
   ```bash
   tccli vpc DescribeCcnAttachedInstances \
     --Region "{{env.TENCENTCLOUD_REGION}}" \
     --Filters "Name=ccn-id,Values={{output.ccn_id}}"
   ```

3. **检查路由表**:
   ```bash
   tccli vpc DescribeCcnRoutes \
     --Region "{{env.TENCENTCLOUD_REGION}}" \
     --CcnId "{{output.ccn_id}}"
   ```

4. **检查带宽限制**:
   ```bash
   tccli vpc DescribeCcnRegionBandwidthLimits \
     --Region "{{env.TENCENTCLOUD_REGION}}" \
     --CcnId "{{output.ccn_id}}"
   ```

## 场景九：高级配置与优化

### 路由策略配置

```bash
# 添加静态路由（覆盖自动学习路径）
tccli vpc CreateCcnRoute \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnId "{{output.ccn_id}}" \
  --RouteTableId "{{output.route_table_id}}" \
  --DestinationCidrBlock "{{user.destination_cidr}}" \
  --NextHopType "VPC" \
  --NextHopInstanceId "{{user.next_hop_instance_id}}"
```

### 负载均衡配置

| 策略 | 实现方式 | 适用场景 |
|------|----------|----------|
| 基于 CIDR | 静态路由 + CCN 路由表 | 不同分支访问不同后端 |
| 基于区域 | 带宽限制 + 路由表 | 跨区域流量调度 |
| 基于应用 | CLB + CCN | 应用级负载均衡 |

### 成本优化

| 优化项 | 建议 | 预期节省 |
|--------|------|----------|
| 带宽规划 | 根据实际使用量设置带宽限制 | 30-50% |
| 区域选择 | 就近接入减少跨区域流量 | 20-40% |
| 资源复用 | 多业务共享 CCN 实例 | 10-20% |

## 跨技能委托

| 场景 | 委托到 |
|------|--------|
| 专线接入 | `qcloud-dc-ops` |
| VPN 备份 | `qcloud-vpn-ops` |
| VPC 配置 | `qcloud-vpc-ops` |
| 监控告警 | `qcloud-monitor-ops` |
| 成本分析 | `qcloud-finops-ops` |

## 参考

- CCN 核心概念: [core-concepts.md](core-concepts.md)
- CLI 使用: [cli-usage.md](cli-usage.md)
- 故障排查: [troubleshooting.md](troubleshooting.md)
- 路由表配置: [cli-usage.md](cli-usage.md#inspect-routes)
- 带宽限制: [cli-usage.md](cli-usage.md#set-inter-region-bandwidth)
