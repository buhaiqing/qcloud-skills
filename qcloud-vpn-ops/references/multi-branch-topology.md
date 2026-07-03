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

### 配置步骤

1. **创建 VPN 网关** (Hub):
   ```bash
   tccli vpc CreateVpnGateway \
     --VpcId "vpc-xxx" \
     --VpnGatewayName "hub-vpn-gateway" \
     --InternetMaxBandwidthOut 100 \
     --Type IPSEC
   ```

2. **创建对端网关** (每个分支):
   ```bash
   # 分支1
   tccli vpc CreateCustomerGateway \
     --VpnGatewayName "branch1-cgw" \
     --PublicIp "203.0.113.1"
   
   # 分支2
   tccli vpc CreateCustomerGateway \
     --VpnGatewayName "branch2-cgw" \
     --PublicIp "203.0.113.2"
   ```

3. **创建 VPN 隧道**:
   ```bash
   tccli vpc CreateVpnConnection \
     --VpnGatewayId "vpngw-xxx" \
     --CustomerGatewayId "cgw-branch1" \
     --VpnConnectionName "branch1-tunnel" \
     --PreShareKey "YourSecureKey123"
   ```

4. **配置路由**:
   - 在 VPC 路由表中添加分支网段路由，指向 VPN 网关
   - 在各分支路由器上配置到云端网段的静态路由

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

1. **主隧道配置** (优先级高):
   ```bash
   tccli vpc CreateVpnConnection \
     --VpnGatewayId "vpngw-primary" \
     --CustomerGatewayId "cgw-branch" \
     --VpnConnectionName "branch-primary" \
     --IKEOptionsSpecification '{"PropoAuthenAlgorithm":"MD5","PropoEncryAlgorithm":"3DES","ExchangeMode":"MAIN","LocalIdentity":"ADDRESS","RemoteIdentity":"ADDRESS","LocalAddress":"1.2.3.4","RemoteAddress":"5.6.7.8"}' \
     --IPSECOptionsSpecification '{"EncryptAlgorithm":"3DES","IntegratAlgorithm":"MD5"}'
   ```

2. **备隧道配置** (优先级低):
   ```bash
   tccli vpc CreateVpnConnection \
     --VpnGatewayId "vpngw-backup" \
     --CustomerGatewayId "cgw-branch" \
     --VpnConnectionName "branch-backup" \
     --IKEOptionsSpecification '{...}'
   ```

3. **路由优先级设置**:
   - 主隧道路由: 优先级 100
   - 备隧道路由: 优先级 200
   - 监控检测: ICMP/HTTP 探测主隧道

### 故障切换检测

```bash
# 检查 VPN 连接状态
tccli vpc DescribeVpnConnections \
  --Filters "Name=vpn-gateway-id,Values=vpngw-primary"

# 预期输出检查
# State = "AVAILABLE" 表示正常
# State = "FAILED" 表示需要切换到备用
```

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

1. **IPSec VPN**: 配置见场景一
2. **SSL VPN**: 使用腾讯 SSL VPN 服务
3. **访问控制**: 使用不同网段区分 IPSec 和 SSL 接入用户
4. **安全策略**: SSL VPN 用户限制访问范围（只访问必要资源）

## 参考

- VPN 核心概念: [core-concepts.md](core-concepts.md)
- CLI 使用: [cli-usage.md](cli-usage.md)
- 故障排查: [troubleshooting.md](troubleshooting.md)
- 专线备份: [qcloud-dc-ops](../qcloud-dc-ops/references/core-concepts.md)
