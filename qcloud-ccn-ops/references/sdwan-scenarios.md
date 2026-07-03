# SD-WAN 场景指南 — 云联网 (CCN)

> 本文档描述使用 CCN 构建 SD-WAN 架构的场景和最佳实践。

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
   tccli ccn CreateCcn \
     --CcnName "sdwan-hub-spoke" \
     --CcnDescription "SD-WAN Hub-Spoke拓扑"
   ```

2. **关联 VPC 到 CCN**:
   ```bash
   # 关联总部 VPC (Hub)
   tccli ccn AttachCcnInstances \
     --CcnId "ccn-xxx" \
     --Instances '[{"InstanceId":"vpc-hub","InstanceType":"VPC","InstanceRegion":"ap-guangzhou"}]'
   
   # 关联分支 VPCs (Spokes)
   tccli ccn AttachCcnInstances \
     --CcnId "ccn-xxx" \
     --Instances '[{"InstanceId":"vpc-branch1","InstanceType":"VPC","InstanceRegion":"ap-beijing"}]'
   ```

3. **配置路由传播**:
   - 启用自动路由传播
   - 分支间路由通过 Hub 中转（避免全互联）

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
# 配置带宽限制
tccli ccn SetCcnRegionBandwidthLimits \
  --CcnId "ccn-xxx" \
  --CcnRegionBandwidthLimits '[{"Region":"ap-beijing","BandwidthLimit":500}]'
```

## 场景三：分支上云最佳实践

### 带宽规划

| 分支规模 | 建议带宽 | CCN 连接方式 |
|----------|----------|--------------|
| 小型 (<50人) | 50-100 Mbps | VPC 直接关联 |
| 中型 (50-200人) | 100-500 Mbps | VPC + 专线备份 |
| 大型 (>200人) | 500+ Mbps | 多 VPC + 专线主备 |

### 路由设计原则

1. **汇聚路由**: 在 Hub VPC 汇总分支路由，减少路由条目
2. **路由过滤**: 使用路由表控制分支间互访
3. **黑洞路由**: 为未分配网段配置黑洞路由防止环路

## 场景四：故障切换（主备 CCN）

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
   tccli ccn DescribeCcnAttachedInstances \
     --CcnId "ccn-primary" \
     --query 'Response.InstanceSet[*].State'
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

## 监控与告警

| 指标 | 告警阈值 | 处理建议 |
|------|----------|----------|
| 带宽利用率 | > 80% | 考虑扩容或流量调度 |
| 丢包率 | > 0.1% | 检查链路质量 |
| 延迟 | > 50ms | 检查路由路径 |
| CCN 实例状态 | 非 AVAILABLE | 立即检查 |

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
