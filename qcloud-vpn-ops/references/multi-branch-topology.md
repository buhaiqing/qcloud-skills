# 多分支 VPN 拓扑模板

> 本文档描述使用 VPN 连接多个分支机构和云端的拓扑模板和最佳实践。

## 场景一：Hub-Spoke VPN 拓扑

### 架构图

```
                      ┌──────────────────┐
                      │   腾讯云 VPC     │
                      │   (Hub)          │
                      │   VPN Gateway    │
                      └────────┬─────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
      ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
      │  分支1 VPN   │ │  分支2 VPN   │ │  分支3 VPN   │
      │  Customer GW │ │  Customer GW │ │  Customer GW │
      │  172.16.1.0/24│ │  172.16.2.0/24│ │  172.16.3.0/24│
      └──────────────┘ └──────────────┘ └──────────────┘
```

### 配置要点

1. **VPN 网关** (Hub): 创建单个 VPN Gateway，带宽需满足所有分支流量总和
2. **对端网关**: 每个分支创建一个 Customer Gateway
3. **VPN 隧道**: 每个分支一条 IPSec 隧道
4. **路由配置**: VPC 路由表添加各分支网段路由，指向 VPN Gateway

> **详细 CLI/SDK 步骤**: 参见 [execution-flows.md §12](execution-flows.md#12-multi-branch-hub-spoke-topology-deployment)

### 最佳实践

- **带宽规划**: Gateway 带宽 ≥ 所有分支带宽之和
- **CIDR 规划**: 各分支 CIDR 互不重叠，且与 VPC CIDR 不重叠
- **监控告警**: 为每条隧道配置 DOWN 告警

## 场景二：故障切换（主备 VPN 隧道）

### 架构图

```
     ┌──────────────────────────────────────────────┐
     │                腾讯云 VPC                     │
     │  ┌─────────────┐      ┌─────────────┐        │
     │  │ VPN Gateway │      │ VPN Gateway │        │
     │  │   (主)      │      │   (备)      │        │
     │  └──────┬──────┘      └──────┬──────┘        │
     │         │                    │               │
     └─────────┼────────────────────┼───────────────┘
               │                    │
               │         ┌──────────┘
               │         │ (故障切换)
               ▼         ▼
        ┌──────────────────────┐
        │    分支机构路由器     │
        │  (支持双 VPN 连接)    │
        └──────────────────────┘
```

### 主备切换配置

1. **主隧道**: 优先级高，路由优先级 100
2. **备隧道**: 优先级低，路由优先级 200
3. **故障检测**: 配置健康检查（BFD/NQA/ICMP），检测主隧道状态
4. **自动切换**: 主隧道 DOWN 时，路由自动切换到备隧道

### 路由优先级示例

```bash
# 主隧道路由 (优先级 100)
tccli vpc CreateRoutes \
  --RouteTableId "rtb-xxx" \
  --Routes '[{
    "DestinationCidrBlock": "172.16.1.0/24",
    "GatewayType": "VPNGW",
    "GatewayId": "vpngw-primary"
  }]'

# 备隧道路由 (优先级 200)
tccli vpc CreateRoutes \
  --RouteTableId "rtb-xxx" \
  --Routes '[{
    "DestinationCidrBlock": "172.16.1.0/24",
    "GatewayType": "VPNGW",
    "GatewayId": "vpngw-backup"
  }]'
```

### 最佳实践

- **双 Gateway**: 主备隧道使用不同的 VPN Gateway，避免单点故障
- **跨可用区**: 主备 Gateway 部署在不同可用区
- **监控**: 监控两条隧道状态，主隧道 DOWN 时触发告警
- **定期演练**: 定期验证备隧道可用性

## 场景三：分支上云带宽规划

### 带宽建议

| 分支规模 | 建议带宽 | 并发隧道数 | 加密算法 |
|----------|----------|------------|----------|
| 小型 (<20人) | 10-20 Mbps | 1 | AES-128 |
| 中型 (20-100人) | 50-100 Mbps | 1-2 | AES-128 |
| 大型 (100-500人) | 100-500 Mbps | 2 | AES-256 |
| 超大型 (>500人) | 500+ Mbps | 2+ | AES-256 + 专线备份 |

### 带宽优化技巧

1. **流量分类**: 区分关键业务和普通流量
2. **压缩**: 启用 IP Payload 压缩
3. **MTU 优化**: 考虑 IPSec 开销，调整 MTU 为 1400
4. **DPD (Dead Peer Detection)**: 快速检测对端故障

## 场景四：IPSec + SSL VPN 混合方案

### 架构图

```
                    ┌─────────────────┐
                    │   腾讯云 VPC    │
                    │                 │
                    │ ┌─────────────┐ │
                    │ │ IPSec VPN   │ │◄──── 固定站点 (分支)
                    │ │ Gateway     │ │      路由器/防火墙
                    │ └─────────────┘ │
                    │                 │
                    │ ┌─────────────┐ │
                    │ │ SSL VPN     │ │◄──── 移动用户/临时接入
                    │ │ Gateway     │ │      客户端软件
                    │ └─────────────┘ │
                    └─────────────────┘
```

### 使用场景

| 连接类型 | VPN 类型 | 适用场景 |
|----------|----------|----------|
| 站点到站点 | IPSec VPN | 固定分支机构、数据中心互联 |
| 客户端到站点 | SSL VPN | 远程办公、移动用户、临时接入 |
| 混合接入 | IPSec + SSL | 既有固定站点又有移动用户 |

### 配置要点

1. **IPSec VPN**: 用于固定站点互联
2. **SSL VPN**: 用于移动用户接入
3. **访问控制**: 使用不同网段区分 IPSec 和 SSL 接入用户
4. **安全策略**: SSL VPN 用户限制访问范围（只访问必要资源）

## 参考

- VPN 核心概念: [core-concepts.md](core-concepts.md)
- CLI 使用: [cli-usage.md](cli-usage.md)
- 故障排查: [troubleshooting.md](troubleshooting.md)
- 详细执行步骤: [execution-flows.md §12](execution-flows.md#12-multi-branch-hub-spoke-topology-deployment)
- 专线备份: [qcloud-dc-ops](../qcloud-dc-ops/references/core-concepts.md)
- 集成模式: [integration.md](integration.md)
