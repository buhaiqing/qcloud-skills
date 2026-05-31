# CLB × CLS 聚合分析流程

> 结合 CLB（负载均衡）与 CLS（日志服务），实现 FinOps 成本优化和 AiOps 智能诊断的全流程自动化分析。

---

## 流程总览

```
┌─────────────────────────────────────────────────────────────────┐
│               CLB × CLS 聚合分析全流程自动化                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌───────────┐    ┌─────────┐  │
│  │ 资源发现  │ →  │ 数据采集  │ →  │ 智能分析   │ →  │ 动作输出 │  │
│  │ (CLB)    │    │ (可选)   │    │ (FinOps/  │    │ (建议/  │  │
│  │          │    │  CLS    │    │  AiOps)   │    │  报告)  │  │
│  └──────────┘    └──────────┘    └───────────┘    └─────────┘  │
│                                                                  │
│    持续执行 ←────────────────────────────────── 反馈闭环          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 前置条件

| 条件 | 检查方法 | 说明 | 是否必须 |
|------|---------|------|---------|
| CLB 为 7 层监听器 | `tccli clb DescribeListeners --LoadBalancerId {{lb_id}}` | 仅 HTTP/HTTPS 支持访问日志 | 仅日志场景 |
| CLS 日志主题已创建 | `tccli cls DescribeTopics` | 用于接收 CLB 访问日志 | 仅日志场景 |
| CLB → CLS 日志采集已开启 | CLS 控制台「云产品中心 → 负载均衡 CLB」配置 | 每个 CLB 实例单独开启 | 仅日志场景 |
| CLS 凭证已配置 | `TENCENTCLOUD_SECRET_ID/KEY` | 必须拥有 CLS 读写权限 | 仅日志场景 |
| 日志主题索引已配置 | `tccli cls DescribeIndex --TopicId {{topic_id}}` | 需按下方模板创建 KV 索引 | 仅日志场景 |
| CLB API 凭证 | `TENCENTCLOUD_SECRET_ID/KEY` | DescribeLoadBalancers 等基础 API | 所有场景 |
| Monitor API 凭证 | 同上 | GetMonitorData 获取监控指标 | 非日志场景 |

### 开启 CLB → CLS 日志采集

```
CLS 控制台 → 云产品中心 → 负载均衡 CLB → 接入管理 → 实例接入
  → 勾选目标 CLB 实例 → 开启日志采集 → 选择/创建日志主题
```

**注意：**
- 每个 CLB 实例绑定一个日志主题；**多个 CLB 可共享同一主题**（通过 `server_addr` 区分）
- 开启后约 1-3 分钟日志开始到达
- **大流量场景支持抽样采集**（比例可配，用于降低成本），分析时注意数据是抽样而非全量

确认采集已生效：
```bash
tccli cls SearchLog \
  --TopicId "{{topic_id}}" \
  --From $(date -d '5 minutes ago' +%s)000 \
  --To $(date +%s)000 \
  --Query '*' \
  --Limit 5
```

---

## CLB 访问日志字段参考

> 来源：腾讯云官方文档。字段名**大小写敏感**（如 `remote_addr`、`status`）。

| # | 字段名 | 类型 | 含义 | 示例值 | FinOps | AiOps |
|---|--------|------|------|--------|--------|-------|
| 1 | `stgw_request_id` | text | 请求 ID | `abc123` | - | 全链路追踪 |
| 2 | `time_local` | text | 访问时间与时区 | `01/Jul/2024:11:11:00 +0800` | 时间聚合 | 时间序列 |
| 3 | `protocol_type` | text | 协议类型 | `HTTP`、`HTTPS`、`HTTP2` | - | SSL 分析 |
| 4 | `server_protocol` | text | CLB 协议 | `HTTP/1.1`、`HTTP/2` | - | 兼容性 |
| 5 | `server_addr` | text | CLB VIP | `1.2.3.4` | ✅ | ✅ |
| 6 | `server_port` | long | 监听端口 | `443` | ✅ | - |
| 7 | `server_name` | text | 监听器域名 | `api.example.com` | ✅ | ✅ |
| 8 | `remote_addr` | text | 客户端 IP | `192.168.1.100` | - | ✅ |
| 9 | `remote_port` | long | 客户端端口 | `54321` | - | - |
| 10 | `status` | long | CLB 返回状态码 | `200`、`502` | ✅ | ✅ |
| 11 | `upstream_addr` | text | 后端服务器地址 | `10.0.0.10:8080` | ✅ | ✅ |
| 12 | `upstream_status` | long | 后端状态码 | `200`、`500` | ✅ | ✅ |
| 13 | `request_method` | text | HTTP 方法 | `GET`、`POST` | - | - |
| 14 | `uri` | text | 资源标识符 | `/api/v1/users` | ✅ | ✅ |
| 15 | `request` | text | 完整请求行 | `GET /api/v1/users HTTP/1.1` | - | - |
| 16 | `request_length` | long | 请求字节数 | `1234` | ✅ | - |
| 17 | `bytes_sent` | long | 发送字节数 | `5678` | ✅ **带宽** | - |
| 18 | `request_time` | double | 请求处理时间（秒） | `0.123` | ✅ 延迟 | ✅ **慢请求** |
| 19 | `upstream_response_time` | double | 后端耗时（秒） | `0.100` | ✅ 后端延迟 | ✅ **后端瓶颈** |
| 20 | `upstream_connect_time` | double | 后端建连耗时（秒） | `0.010` | ✅ 网络质量 | ✅ **连接问题** |
| 21 | `upstream_header_time` | double | 接收后端头部耗时（秒） | `0.050` | - | ✅ 后端处理 |
| 22 | `http_host` | text | 请求域名 | `api.example.com` | ✅ 域名流量 | ✅ 域名定位 |
| 23 | `http_user_agent` | text | User-Agent | `Mozilla/5.0` | - | ✅ 客户端画像 |
| 24 | `http_referer` | text | 请求来源 | `https://example.com/home` | - | ✅ 来源分析 |
| 25 | `http_x_forwarded_for` | text | X-Forwarded-For | `10.0.0.1` | - | ✅ 真实IP |
| 26 | `ssl_handshake_time` | text | SSL 握手耗时 | `0.010` | - | ✅ SSL 性能 |
| 27 | `ssl_cipher` | text | SSL 加密套件 | `ECDHE-RSA-AES128-GCM` | - | ✅ 安全性 |
| 28 | `ssl_protocol` | text | SSL 协议版本 | `TLSv1.2` | - | ✅ 兼容性 |
| 29 | `tcpinfo_rtt` | long | TCP RTT | `5` | - | ✅ 网络质量 |
| 30 | `connection_requests` | long | 连接上的请求数 | `1` | ✅ 复用率 | - |
| 31 | `vip_vpcid` | text | 私有网络 ID | `vpc-abc123`、`-1` | ✅ 网络类型 | - |

---

## 索引配置

> **前置条件**：必须在日志主题上创建 Key-Value 索引才能执行分析查询。

```json
{
  "FullText": {
    "CaseSensitive": false,
    "Tokenizer": "@&?|#()='\"/:;,\\[\\]{} \t\n",
    "ContainZH": true
  },
  "KeyValue": {
    "CaseSensitive": true,
    "KeyValues": [
      {"Key": "remote_addr",          "Value": {"Type": "text"}},
      {"Key": "server_addr",          "Value": {"Type": "text"}},
      {"Key": "server_port",          "Value": {"Type": "long"}},
      {"Key": "server_name",          "Value": {"Type": "text"}},
      {"Key": "status",               "Value": {"Type": "long"}},
      {"Key": "upstream_status",      "Value": {"Type": "long"}},
      {"Key": "upstream_addr",        "Value": {"Type": "text"}},
      {"Key": "request_method",       "Value": {"Type": "text"}},
      {"Key": "uri",                  "Value": {"Type": "text"}},
      {"Key": "http_host",            "Value": {"Type": "text"}},
      {"Key": "http_user_agent",      "Value": {"Type": "text"}},
      {"Key": "http_referer",         "Value": {"Type": "text"}},
      {"Key": "http_x_forwarded_for", "Value": {"Type": "text"}},
      {"Key": "request_time",         "Value": {"Type": "double"}},
      {"Key": "upstream_response_time", "Value": {"Type": "double"}},
      {"Key": "upstream_connect_time",  "Value": {"Type": "double"}},
      {"Key": "bytes_sent",           "Value": {"Type": "long"}},
      {"Key": "protocol_type",        "Value": {"Type": "text"}},
      {"Key": "ssl_protocol",         "Value": {"Type": "text"}},
      {"Key": "ssl_cipher",           "Value": {"Type": "text"}},
      {"Key": "connection_requests",  "Value": {"Type": "long"}}
    ]
  }
}
```

---

## CLS SQL 分析须知

> CLS SQL 使用 Presto 兼容语法。以下为常用函数和注意事项：

| 类别 | 函数 | 说明 | 注意 |
|------|------|------|------|
| **时间处理** | `date_parse(text, format)` | 将文本转时间戳 | `time_local` 格式：`'%d/%b/%Y:%H:%i:%s +0800'` |
| | `date_trunc(unit, ts)` | 按粒度截断时间 | unit: second/minute/hour/day/week/month |
| | `date_format(ts, format)` | 格式化输出 | 如 `'%Y-%m-%d %H:%i:%s'` |
| **聚合** | `count_if(cond)` | 条件计数 | ⚠️ 小写+下划线，不是 `countIf` |
| | `approx_percentile(key, p)` | 近似百分位 | ⚠️ 不是 `percentile`/`p50`/`p95`/`p99` |
| | `sum`, `avg`, `max`, `min` | 标准聚合 | 常规使用 |
| **条件** | `CASE WHEN ... END` | 条件分支 | 完整支持 |
| | `IF(cond, t, f)` | 简单条件 | 简化版 CASE |
| **过滤** | `HAVING` | 聚合后过滤 | `GROUP BY ... HAVING count > 100` |
| **注意** | `time_local` 是文本 | 不能直接传给 `date_trunc` | 需先用 `date_parse` 转换 |
| | SQL 仅支持标准存储 | 低频存储不支持 SQL 分析 | 检查日志主题存储类型 |
| | 抽样采集 | 大流量场景可能只采部分 | 分析结果需乘以采样比 |

### 时间处理示例

```sql
-- ❌ 错误：time_local 是文本，不能直接用
* | select date_trunc('hour', time_local)

-- ✅ 正确：先用 date_parse 转换（精确，但计算量大）
* | select date_trunc('hour', date_parse(time_local, '%d/%b/%Y:%H:%i:%s +0800')) as hour

-- ✅ 更简洁的替代方案：直接使用 __TIMESTAMP__ 元数据字段（CLS 采集时间，无需转换）
--   注意：__TIMESTAMP__ 是 CLS 接收日志的时间，与原始请求时间有秒级偏差
--   对趋势分析（小时级/天级聚合）影响可忽略
* | select date_trunc('hour', __TIMESTAMP__) as hour, count(*) as req_count group by hour order by hour

-- ✅ 按天聚合（推荐使用 __TIMESTAMP__ 简化查询）
* | select date_format(__TIMESTAMP__, '%Y-%m-%d') as day,
          count(*) as req_count,
          sum(bytes_sent)/1048576 as total_mb
   group by day
   order by day
```

---

## 全场景清单（含 CLS 依赖标注）

| 类别 | # | 场景 | 依赖 CLS? | 无 CLS 替代方案 | 复杂度 |
|------|---|------|-----------|-----------------|--------|
| **FinOps** | F1 | 闲置资源检测与回收 | ⚡ 可选 | CLB API 检测无监听器/无后端 | ⭐ |
| | F2 | 带宽规格匹配分析 | ⚡ 可选 | Monitor 提供带宽指标（QCE/LB_PUBLIC） | ⭐⭐ |
| | F3 | 流量消费排行分析 | **🔴 必须** | CLS 独有：URI/后端/客户端级详情 | ⭐ |
| | F4 | 计费模式优化建议 | ⚡ 可选 | Billing API + Monitor 指标 | ⭐⭐⭐ |
| | F5 | 跨 CLB 成本对比 | ⚡ 可选 | Billing API + CLB API | ⭐⭐ |
| | F6 | 流量季节性模式分析 | ⚡ 可选 | Monitor 时间序列指标 | ⭐⭐ |
| | F7 | 连接复用率与资源效率 | **🔴 必须** | CLS 独有：`connection_requests` | ⭐⭐ |
| | F8 | 大流量 URI 缓存优化建议 | **🔴 必须** | CLS 独有：URI 级流量详情 | ⭐⭐⭐ |
| **AiOps** | A1 | 5XX 错误分层诊断 | ⚡ 可选 | Monitor 提供 HttpCode5XX 指标（无 URI 级） | ⭐⭐ |
| | A2 | 慢请求三段式瓶颈分析 | **🔴 必须** | CLS 独有：`request_time`/`upstream_time` 分段 | ⭐⭐ |
| | A3 | 客户端异常行为检测 | **🔴 必须** | CLS 独有：`remote_addr`/`User-Agent`/`uri` | ⭐⭐ |
| | A4 | SSL/TLS 安全分析 | **🔴 必须** | CLS 独有：`ssl_protocol`/`ssl_cipher` | ⭐ |
| | A5 | 后端健康与容量分析 | ⚡ 可选 | CLB DescribeTargetHealth API | ⭐⭐ |
| | A6 | 告警风暴关联分析 | ⚡ 可选 | Monitor 告警 + 指标（不含日志详情） | ⭐⭐⭐ |
| | A7 | 容量趋势预测 | ⚡ 可选 | Monitor 历史指标 | ⭐⭐ |
| | A8 | 版本发布影响对比 | **🔴 必须** | CLS 独有：时间窗口 URI 级对比 | ⭐⭐⭐ |
| | A9 | 全链路故障诊断 | **🔴 必须** | CLS 独有：逐请求追踪 | ⭐⭐⭐⭐ |
| | A10 | 慢客户端识别与告警 | **🔴 必须** | CLS 独有：逐客户端延迟数据 | ⭐⭐ |

**图例：**
- **🔴 必须** = 该类数据仅 CLS 日志能提供，无后备方案
- ⚡ 可选 = Monitor/CLB API 可提供基础数据，CLS 增加精度和深度
- 基础数据 = CLB 实例级/监听器级信息（DescribeLoadBalancers、DescribeListeners）
- Monitor 指标 = 分钟级聚合指标（连接数、流量、错误码等）
- CLS 日志 = 逐请求级详情（URI、状态码、延迟、IP、SSL 等）

---

## FinOps 场景（F1-F8）

---

### F1 — 闲置资源检测与回收
**CLS 依赖：** ⚡ 可选（无 CLS 可用 CLB API 兜底）

扫描所有 CLB，识别零/低流量实例，推荐删除或降配。

#### 无 CLS 的兜底方案（CLB API 级别）

```bash
# 检测无监听器的 CLB
tccli clb DescribeLoadBalancers | jq -c '.Response.LoadBalancerSet[]' | while read lb; do
  LB_ID=$(echo "$lb" | jq -r '.LoadBalancerId')
  LISTENER_COUNT=$(tccli clb DescribeListeners --LoadBalancerId "$LB_ID" | jq '.Response.ListenerSet | length')
  [ "$LISTENER_COUNT" -eq 0 ] && echo "❌ 闲置（无监听器）: $LB_ID"
done
```

#### 有 CLS 的增强方案

```bash
#!/bin/bash
# 遍历 CLB，在 CLS 中检查 7 天流量
TOPIC_ID="{{topic_id}}"
NOW=$(date +%s)
SEVEN_DAYS_AGO=$((NOW - 604800))

tccli clb DescribeLoadBalancers | jq -c '.Response.LoadBalancerSet[]' | while read lb; do
  VIP=$(echo "$lb" | jq -r '.LoadBalancerVips[0] // empty')
  NAME=$(echo "$lb" | jq -r '.LoadBalancerName')
  [ -z "$VIP" ] && continue

  COUNT=$(tccli cls SearchLog \
    --TopicId "$TOPIC_ID" \
    --From "${SEVEN_DAYS_AGO}000" --To "${NOW}000" \
    --Query "server_addr:\"$VIP\"" --Limit 1 | jq -r '.Response.Results | length')

  if [ "$COUNT" -eq 0 ]; then
    echo "❌ 闲置（7天零流量）: $NAME VIP=$VIP"
  fi
done
```

#### 提示词示例

```
请帮我做 CLB 闲置资源检测：
1. 列出所有 CLB，优先通过 CLS 检查过去 7 天的访问日志量
2. 如果该 CLB 未接入 CLS（无日志主题），改用 CLB API 检查是否有监听器和后端
3. 标记闲置和低负载 CLB
4. 给出删除或降配建议
```

---

### F2 — 带宽规格匹配分析
**CLS 依赖：** ⚡ 可选（Monitor 指标可兜底）

对比 CLB 带宽规格与实际峰值。

#### 无 CLS 的兜底方案（Monitor 指标）

```bash
# 使用 Monitor API 获取带宽指标
tccli monitor GetMonitorData \
  --Namespace "QCE/LB_PUBLIC" \
  --MetricName "ClientOutputTraffic" \
  --Period 300 \
  --StartTime "$(date -d '7 days ago' -u +%Y-%m-%dT%H:%M:%S+00:00)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)" \
  --Dimensions "[{\"Name\":\"LoadBalancerId\",\"Value\":\"{{lb_id}}\"}]"
```

#### 有 CLS 的增强方案

```sql
-- 按分钟聚合带宽峰值（需先转换 time_local）
* | select date_trunc('minute', date_parse(time_local, '%d/%b/%Y:%H:%i:%s +0800')) as minute,
          sum(bytes_sent)*8/1048576 as bandwidth_mbps
   from {{topic_id}}
   where server_addr="{{vip}}"
   group by minute
   order by bandwidth_mbps desc
   limit 20
```

#### 提示词示例

```
分析 CLB {{lb_id}} 的带宽规格是否合理：
1. 查看该 CLB 的带宽规格配置
2. 如果有 CLS 日志，从日志统计过去 7 天每分钟的实际带宽峰值
3. 如果无 CLS 日志，改用 Monitor API 获取 ClientOutputTraffic 指标
4. 对比：峰值/规格 < 30% → 降配建议；峰值/规格 > 80% → 升配建议
5. 输出调整建议并估算节省金额
```

---

### F3 — 流量消费排行分析
**CLS 依赖：** 🔴 必须（无 CLS 无法获取 URI/客户端级数据）

#### 提示词示例

```
分析 CLB {{lb_id}} 的流量消费构成（需要 CLS 日志）：

1. 按 URI 统计过去 7 天总流量 TOP 20
  → server_addr:"{{vip}}" | select uri, request_method, count(*) as req_count, sum(bytes_sent)/1048576 as total_mb, avg(bytes_sent) as avg_bytes, max(bytes_sent)/1048576 as max_mb group by uri, request_method order by total_mb desc limit 20

2. 按后端服务器统计流量占比
  → server_addr:"{{vip}}" | select upstream_addr, count(*) as req_count, sum(bytes_sent)/1048576 as total_mb, round(sum(bytes_sent)*100.0/(select sum(bytes_sent) from {{topic_id}} where server_addr="{{vip}}"), 2) as pct group by upstream_addr order by total_mb desc

3. 按客户端 IP 统计下载量 TOP 10
  → server_addr:"{{vip}}" | select remote_addr, sum(bytes_sent)/1048576 as download_mb, count(*) as req_count, count(distinct uri) as unique_uris group by remote_addr order by download_mb desc limit 10

4. 区分"高频小流量"和"低频大流量"两类 URI
  → server_addr:"{{vip}}" | select case when count(*)*avg(bytes_sent) > 104857600 then 'heavy' when count(*) > 10000 then 'frequent' else 'normal' end as pattern, uri, count(*) as req_count, sum(bytes_sent)/1048576 as total_mb group by pattern, uri order by total_mb desc
```

---

### F4 — 计费模式优化建议
**CLS 依赖：** ⚡ 可选（Billing/Monitor API 可兜底）

根据流量模式推荐按量带宽或共享带宽包。

#### 提示词示例

```
分析 CLB {{lb_id}} 的最佳计费模式：
1. 查看该 CLB 当前计费方式
2. 如果有 CLS：分析过去 30 天的带宽波动率（峰值/均值比）
3. 如果无 CLS：通过 Monitor API 获取 ClientOutputTraffic 的日均和峰值
4. 建议规则：
   - 带宽稳定（峰值/均值 < 2）→ 按量带宽固定规格
   - 带宽波动大（峰值/均值 > 3）→ 共享带宽包
   - 多 CLB 流量互补 → 合并到同一共享带宽包
5. 输出变更建议和预估节省
```

---

### F5 — 跨 CLB 成本对比
**CLS 依赖：** ⚡ 可选（CLB API + 计费数据可兜底）

#### 提示词示例

```
对比 {{region}} 所有 CLB 的成本效率：
1. 列出所有 CLB 型号和规格
2. 如果有 CLS：从日志统计每 CLB 的请求量、总流量、平均 QPS
3. 如果无 CLS：从 Monitor 获取各 CLB 的连接数和流量指标
4. 计算每 GB 流量成本、每百万请求成本
5. 标记成本异常偏高的 CLB
```

---

### F6 — 流量季节性模式分析
**CLS 依赖：** ⚡ 可选（Monitor 指标可兜底）

#### 提示词示例

```
分析 CLB {{lb_id}} 的流量模式：
1. 如果有 CLS：按天+小时聚合过去 7 天的请求量和带宽
  → server_addr:"{{vip}}" | select date_format(date_parse(time_local, '%d/%b/%Y:%H:%i:%s +0800'), '%Y-%m-%d %H:00') as hour, count(*) as req_count, sum(bytes_sent)/1048576 as mb group by hour order by hour

2. 如果无 CLS：从 Monitor 获取 7 天小时级 ClientConnum 指标
3. 分析：工作日 vs 周末、早高峰 vs 晚高峰、是否存在可预测的峰谷
4. 输出模式报告，用于指导带宽规格和计费方式选择
```

---

### F7 — 连接复用率与资源效率
**CLS 依赖：** 🔴 必须（`connection_requests` 仅 CLS 日志提供）

#### 提示词示例

```
分析 CLB {{lb_id}} 的连接复用效率（需要 CLS 日志）：

1. 连接复用率分布
  → server_addr:"{{vip}}" | select case when connection_requests=1 then '单次连接' when connection_requests<=5 then '低复用(2-5)' when connection_requests<=10 then '中复用(6-10)' else '高复用(>10)' end as reuse_level, count(*) as req_count, count(distinct connection) as conn_count, round(count(*)*1.0/nullif(count(distinct connection),0), 2) as avg_reuse_rate group by reuse_level order by reuse_level

2. 低复用连接的客户端
  → connection_requests=1 AND server_addr:"{{vip}}" | select remote_addr, http_user_agent, count(*) as req_count, count(distinct connection) as conn_count group by remote_addr, http_user_agent order by req_count desc limit 20
```

---

### F8 — 大流量 URI 缓存优化建议
**CLS 依赖：** 🔴 必须（URI 级流量数据仅 CLS 提供）

#### 提示词示例

```
分析 CLB {{lb_id}} 中适合缓存的大流量 URI（需要 CLS 日志）：

→ request_method:GET AND status:200 AND server_addr:"{{vip}}" AND bytes_sent:>102400 | select uri, count(*) as req_count, avg(bytes_sent)/1024 as avg_kb, sum(bytes_sent)/1048576 as total_mb, count(distinct remote_addr) as unique_clients group by uri order by total_mb desc limit 20

过滤出静态资源特征（js/css/png/jpg/woff 等），评估使用 CDN 可节省的带宽比例。
```

---

## AiOps 场景（A1-A10）

---

### A1 — 5XX 错误分层诊断
**CLS 依赖：** ⚡ 可选（Monitor 提供 HttpCode5XX 指标，但无 URI/后端级详情）

#### 无 CLS 的兜底方案

```bash
# Monitor API 可获取 5XX 概览，但无 URI/后端维度
tccli monitor GetMonitorData \
  --Namespace "QCE/LB_PUBLIC" \
  --MetricName "HttpCode5XX" \
  --Period 300 \
  --StartTime "$(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%S+00:00)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)" \
  --Dimensions "[{\"Name\":\"LoadBalancerId\",\"Value\":\"{{lb_id}}\"}]"
```

#### 有 CLS 的分层诊断（5 层逐层下钻）

```
Layer 1: 状态码分布 → 502/503/504 各多少
Layer 2: URI 级别 → 哪个接口问题最大
Layer 3: 后端级别 → 哪个后端故障
Layer 4: 客户端级别 → 是否客户端问题
Layer 5: 时间线 → 错误是否集中在某时段
```

#### 提示词示例

```
诊断 CLB {{lb_id}} 的 5XX 错误：
1. 如果有 CLS 日志，执行 5 层下钻
2. 如果无 CLS，从 Monitor 获取 HttpCode5XX 整体趋势，然后委托 qcloud-cvm-ops 逐个检查后端
3. CLS 分层查询：
  Layer1 → server_addr:"{{vip}}" AND status:>=500 | select status, count(*) as c group by status
  Layer2 → status:>=500 AND server_addr:"{{vip}}" | select uri, count(*) as c group by uri order by c desc limit 10
  Layer3 → status:>=500 AND server_addr:"{{vip}}" | select upstream_addr, status, count(*) as c group by upstream_addr, status order by c desc limit 20
  Layer4 → status:>=500 AND server_addr:"{{vip}}" | select date_trunc('minute', date_parse(time_local, '%d/%b/%Y:%H:%i:%s +0800')) as t, count(*) as c group by t order by t
  Layer5 → status:>=500 AND server_addr:"{{vip}}" | select time_local, remote_addr, request_method, uri, status, upstream_status, upstream_addr, upstream_response_time order by time_local desc limit 10
```

---

### A2 — 慢请求三段式瓶颈分析
**CLS 依赖：** 🔴 必须（`request_time`/`upstream_response_time` 仅 CLS 提供）

#### 提示词示例

```
诊断 CLB {{lb_id}} 的慢请求（需要 CLS 日志）：

三段式拆解：
  request_time = CLB开销 + 网络建连 + 后端处理
  其中:
  - 网络建连   = upstream_connect_time（正常 < 10ms）
  - 后端处理   = upstream_response_time（取决于业务）
  - CLB 开销   = upstream_header_time - upstream_connect_time（正常 < 5ms）

1. 整体统计 → server_addr:"{{vip}}" | select avg(request_time) as avg_total, avg(upstream_response_time) as avg_backend, avg(upstream_connect_time) as avg_connect, avg(upstream_header_time - upstream_connect_time) as avg_clb

2. 瓶颈在后端的慢请求 → upstream_response_time:>1 AND server_addr:"{{vip}}" | select uri, upstream_addr, request_time, upstream_response_time, upstream_connect_time order by request_time desc limit 20

3. 瓶颈在建连的慢请求 → upstream_connect_time:>0.1 AND server_addr:"{{vip}}" | select uri, upstream_addr, remote_addr, upstream_connect_time, request_time order by upstream_connect_time desc limit 20

4. 慢请求客户端特征 → request_time:>5 AND server_addr:"{{vip}}" | select remote_addr, http_user_agent, count(*) as c, avg(request_time) as avg_time group by remote_addr, http_user_agent order by c desc limit 10
```

---

### A3 — 客户端异常行为检测
**CLS 依赖：** 🔴 必须（`remote_addr`/`User-Agent`/`uri` 仅 CLS 提供）

#### 提示词示例

```
检测 CLB {{lb_id}} 的客户端异常行为（需要 CLS 日志）：

1. 热点 IP TOP 20（含错误率）
  → server_addr:"{{vip}}" | select remote_addr, count(*) as req_count, count_if(status>=400) as error_count, round(count_if(status>=400)*100.0/count(*), 2) as error_pct, count(distinct uri) as unique_uris group by remote_addr order by req_count desc limit 20

2. 突发流量检测（单分钟 RPM > 100）
  → server_addr:"{{vip}}" | select remote_addr, date_format(date_parse(time_local, '%d/%b/%Y:%H:%i:%s +0800'), '%Y-%m-%d %H:%i') as minute, count(*) as rpm group by remote_addr, minute having rpm > 100 order by rpm desc limit 30

3. 异常 User-Agent
  → server_addr:"{{vip}}" | select http_user_agent, count(*) as req_count, count(distinct remote_addr) as unique_ips, count(distinct uri) as unique_uris group by http_user_agent order by req_count desc limit 20

4. 疑似扫描 IP（访问大量不同 URI）
  → server_addr:"{{vip}}" | select remote_addr, count(*) as req_count, count(distinct uri) as unique_uris, count_if(status=404) as not_found_count group by remote_addr having unique_uris > 50 order by req_count desc limit 10
```

---

### A4 — SSL/TLS 安全分析
**CLS 依赖：** 🔴 必须（`ssl_protocol`/`ssl_cipher` 仅 CLS 提供）

#### 提示词示例

```
分析 CLB {{lb_id}} 的 SSL/TLS 安全性（需要 CLS 日志）：

1. 协议版本分布
  → protocol_type:HTTPS AND ssl_protocol:* AND server_addr:"{{vip}}" | select ssl_protocol, count(*) as c, count(distinct remote_addr) as unique_clients group by ssl_protocol order by c desc

2. 弱协议客户端详情（TLSv1/v1.1 应禁用）
  → ssl_protocol:(TLSv1 OR TLSv1.1) AND server_addr:"{{vip}}" | select remote_addr, ssl_cipher, http_user_agent, count(*) as c group by remote_addr, ssl_cipher, http_user_agent order by c desc

3. SSL 握手耗时
  → protocol_type:HTTPS AND server_addr:"{{vip}}" | select case when cast(ssl_handshake_time as double) <= 0.05 then 'fast' when cast(ssl_handshake_time as double) <= 0.2 then 'normal' else 'slow' end as speed, count(*) as c group by speed

4. 加密套件排行
  → protocol_type:HTTPS AND ssl_cipher:* AND server_addr:"{{vip}}" | select ssl_cipher, count(*) as c group by ssl_cipher order by c desc limit 10
```

> **注意**：`ssl_handshake_time` 字段类型为 text，需用 `cast(... as double)` 转换后再比较。

---

### A5 — 后端健康与容量分析
**CLS 依赖：** ⚡ 可选（CLB DescribeTargetHealth API 可兜底）

#### 无 CLS 的兜底方案

```bash
# CLB API 直接获取后端健康状态
tccli clb DescribeTargetHealth --LoadBalancerId "{{lb_id}}" | jq '.Response.Targets[] | {InstanceId, HealthStatus, HealthStatusDetail}'
```

#### 有 CLS 的增强方案

```sql
-- 后端响应时间分布
server_addr:"{{vip}}" | select upstream_addr, count(*) as req_count, avg(upstream_response_time) as avg_time, max(upstream_response_time) as max_time, approx_percentile(upstream_response_time, 0.95) as p95, approx_percentile(upstream_response_time, 0.99) as p99 group by upstream_addr order by avg_time desc

-- 后端非 2XX 比例
server_addr:"{{vip}}" | select upstream_addr, count(*) as total, count_if(upstream_status>=400) as errors, round(count_if(upstream_status>=400)*100.0/count(*), 2) as error_pct group by upstream_addr order by error_pct desc

-- 后端建连异常
upstream_connect_time:>1 AND server_addr:"{{vip}}" | select upstream_addr, count(*) as slow_connects, avg(upstream_connect_time) as avg_connect_time group by upstream_addr order by slow_connects desc
```

---

### A6 — 告警风暴关联分析
**CLS 依赖：** ⚡ 可选（Monitor 告警可触发，但日志级根因分析需 CLS）

#### 提示词示例

```
CLB {{lb_id}} 触发 HttpCode5XX 告警，分析根因：

1. 无 CLS：先通过 Monitor API 查看 HttpCode5XX 趋势，再委托 qcloud-cvm-ops 逐个排查后端
2. 有 CLS：执行以下分析
   a. 告警窗口 5XX 时间序列
     → status:>=500 AND server_addr:"{{vip}}" | select date_format(date_parse(time_local, '%d/%b/%Y:%H:%i:%s +0800'), '%Y-%m-%d %H:%i') as t, count(*) as c group by t order by t
   b. 按 URI 聚合错误
     → status:>=500 AND server_addr:"{{vip}}" | select uri, count(*) as c group by uri order by c desc
   c. 按后端聚合
     → status:>=500 AND server_addr:"{{vip}}" | select upstream_addr, status, count(*) as c group by upstream_addr, status order by c desc
```

---

### A7 — 容量趋势预测
**CLS 依赖：** ⚡ 可选（Monitor 历史指标可兜底）

#### 提示词示例

```
预测 CLB {{lb_id}} 的流量增长趋势：
1. 如果有 CLS：按天统计过去 30 天的请求量和带宽
  → server_addr:"{{vip}}" | select date_format(date_parse(time_local, '%d/%b/%Y:%H:%i:%s +0800'), '%Y-%m-%d') as day, count(*) as req_count, sum(bytes_sent)/1048576 as mb group by day order by day
2. 如果无 CLS：从 Monitor 获取 ClientConnum 的 30 天日平均值
3. 计算日均增长率，预测 7 天、30 天后的峰值
4. 对比当前带宽规格，给出扩容建议和最佳时间点
```

---

### A8 — 版本发布影响对比
**CLS 依赖：** 🔴 必须（URL 级 + 时间窗级对比仅 CLS 提供）

#### 提示词示例

```
评估 CLB {{lb_id}} 版本发布 {{deploy_start}} ~ {{deploy_end}} 的影响（需要 CLS 日志）：

1. 错误率对比
  → 发布前: status:>=500 AND server_addr:"{{vip}}" AND time_local:[{{before_start}} TO {{deploy_start}}] | select count(*) as before_errors
  → 发布后: status:>=500 AND server_addr:"{{vip}}" AND time_local:[{{deploy_end}} TO {{after_end}}] | select count(*) as after_errors

2. 延迟对比
  → 发布前: server_addr:"{{vip}}" AND time_local:[{{before_start}} TO {{deploy_start}}] | select avg(request_time) as avg_before, max(request_time) as max_before
  → 发布后: server_addr:"{{vip}}" AND time_local:[{{deploy_end}} TO {{after_end}}] | select avg(request_time) as avg_after, max(request_time) as max_after

3. 按 URI 下钻新增错误
  → status:>=500 AND server_addr:"{{vip}}" AND time_local:[{{deploy_end}} TO {{after_end}}] | select uri, count(*) as c group by uri order by c desc

4. 判定：错误率上升 > 1% 或延迟上升 > 20% → 标记为发布异常
```

---

### A9 — 全链路故障诊断
**CLS 依赖：** 🔴 必须（逐请求追踪仅 CLS 提供）

#### 提示词示例

```
诊断客户端 {{client_ip}} 访问 CLB {{lb_id}} 的故障（需要 CLS 日志）：

1. 查看该客户端近 1 小时的所有请求
  → remote_addr:"{{client_ip}}" AND server_addr:"{{vip}}" | select time_local, request_method, uri, status, upstream_status, request_time, upstream_response_time, upstream_addr order by time_local desc limit 50

2. 如果 CLB 转发正常但后端异常 → 委托 qcloud-cvm-ops 检查后端实例状态和应用日志

3. 各段耗时分析
  → remote_addr:"{{client_ip}}" AND server_addr:"{{vip}}" | select avg(request_time) as avg_total, avg(upstream_response_time) as avg_upstream, avg(upstream_connect_time) as avg_connect, avg(upstream_header_time - upstream_connect_time) as avg_clb group by upstream_addr
```

---

### A10 — 慢客户端识别与告警
**CLS 依赖：** 🔴 必须（逐客户端延迟数据仅 CLS 提供）

#### 提示词示例

```
分析 CLB {{lb_id}} 的慢客户端（需要 CLS 日志）：

1. 慢请求（request_time > 5s）按客户端聚合
  → request_time:>5 AND server_addr:"{{vip}}" | select remote_addr, count(*) as slow_count, avg(request_time) as avg_slow_time, max(request_time) as max_slow_time group by remote_addr order by slow_count desc limit 20

2. 慢请求的 User-Agent 分布
  → request_time:>5 AND server_addr:"{{vip}}" | select http_user_agent, count(*) as c group by http_user_agent order by c desc limit 10

3. 慢请求的 URI 分布
  → request_time:>5 AND server_addr:"{{vip}}" | select uri, count(*) as c, avg(request_time) as avg_time, max(request_time) as max_time group by uri order by c desc limit 10
```

---

## 无 CLS 时的分析能力矩阵

| 能力维度 | 无 CLS（仅 CLB API + Monitor） | 有 CLS |
|---------|-------------------------------|--------|
| **资源发现** | 所有 CLB 实例 | ✅ 同左 |
| **闲置检测** | 检测无监听器/无后端的 CLB | ✅ 额外检测零流量的 CLB |
| **带宽分析** | 分钟级带宽指标（Monitor） | ✅ 秒级精度、按 URI/IP 维度 |
| **错误概览** | HttpCode5XX 聚合数值 | ✅ 5XX 分层到 URI/后端/客户端 |
| **客户端分析** | 无（Monitor 无客户端 IP 维度） | ✅ 逐 IP 分析 |
| **性能分析** | 无（Monitor 无请求级延迟） | ✅ 逐请求 request_time/upstream_time |
| **SSL 分析** | 无 | ✅ ssl_protocol/cipher/handshake |
| **URI 分析** | 无 | ✅ 逐 URI 请求量/流量/延迟 |
| **连接复用** | 无 | ✅ connection_requests |
| **逐请求追踪** | 无 | ✅ stgw_request_id 全网追踪 |

---

## 跨技能委托链路

| 场景 | 数据来源 | 委托技能 | 传递参数 |
|------|---------|---------|---------|
| 后端 502 错误 | CLS → upstream_status | `qcloud-cvm-ops` | `instance_id`、错误时间窗、错误 URI |
| 后端连接超时 | CLS → upstream_connect_time | `qcloud-cvm-ops` | `instance_id`、`port`、超时模式 |
| 客户端异常 IP | CLS → remote_addr 分析 | `qcloud-aiops-diagnosis` | 异常 IP、请求模式、时间线 |
| 全链路诊断 | CLS → 多维度聚合 | `qcloud-aiops-diagnosis` | 所有 CLS 聚合结果 |
| 监控指标交叉验证 | Monitor API | `qcloud-monitor-ops` | CLB ID、时间窗 |
| 缓存优化 | CLS → URI 流量排行 | `qcloud-cdn-ops`(CDN) 或 `qcloud-cos-ops`(COS 静态站) | 大流量 URI 列表 |

---

## 最佳实践

### 字段索引优先级

| 优先级 | 字段 | 理由 |
|--------|------|------|
| **必索引** | `remote_addr`, `status`, `uri`, `server_addr`, `request_method`, `upstream_addr` | 几乎所有分析场景都需要 |
| **推荐索引** | `request_time`, `upstream_response_time`, `http_host`, `http_user_agent`, `bytes_sent`, `upstream_connect_time` | 性能分析和安全审计 |
| **按需索引** | `ssl_protocol`, `ssl_cipher`, `connection_requests`, `http_x_forwarded_for` | SSL/连接复用分析 |
| **可不索引** | `stgw_request_id`, `proxy_host`, `connection`, `vip_vpcid` | 极少用于检索 |

### 查询优化

1. **时间字段转换**：`time_local` 为文本，使用 `date_parse(time_local, '%d/%b/%Y:%H:%i:%s +0800')` 转为 TIMESTAMP
2. **区分大小写**：CLB 日志字段均为小写，如 `remote_addr` 不是 `RemoteAddr`
3. **分步分析**：先概览聚合 → 再下钻详情，避免一次拉取大量数据
4. **善用字段过滤**：`server_addr:"{{vip}}" AND status:>=500` 比全文搜索快 10 倍+
5. **导出大量数据**：使用 `CreateExport` 而非 `SearchLog` 拉取超大数据集
6. **抽样感知**：如果开启了 CLB 日志抽样，分析结果需乘以采样倍率

### 错误码速查

| CLB 状态码 | 含义 | CLS 关联查询 | 排查方向 |
|-----------|------|-------------|---------|
| `502` | Bad Gateway | `upstream_status:>=500` | 后端应用报错 |
| `503` | Service Unavailable | `upstream_response_time:>30` | 后端过载/熔断 |
| `504` | Gateway Timeout | `upstream_connect_time:>10` | 后端连接超时 |
| `499` | Client Closed | `status:499` | 客户端提前断开 |
| `429` | Too Many Requests | `status:429` | 触发了限流 |
| `000` | - | `upstream_status:000` | 后端无响应 |

---

## 参考链接

- [CLS CLB 访问日志分析](https://cloud.tencent.com/document/product/614/61257) — 官方文档
- [CLB 配置访问日志](https://cloud.tencent.com/document/product/214/41379) — CLB 日志投递配置
- [CLS 检索语法](https://cloud.tencent.com/document/product/614/47044) — 查询语法参考
- [CLS SQL 分析](https://cloud.tencent.com/document/product/614/58981) — SQL 分析功能
- [CLS SQL 函数](https://cloud.tencent.com/document/product/614/86137) — 全部函数支持
- [CLS 日期和时间函数](https://cloud.tencent.com/document/product/614/44061) — 时间处理参考
- [抽样采集日志](https://cloud.tencent.com/document/product/214/65779) — 大流量场景成本控制
- [Monitor API](https://cloud.tencent.com/document/product/248/30342) — 云监控指标查询
