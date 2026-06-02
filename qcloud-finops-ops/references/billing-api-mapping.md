# Billing / Trade / Tag API 速查表

> 本文件由 `SKILL.md` 引用。腾讯云账单/订单/标签相关 API 完整速查，按模块分组。

## 1. 账单产品（cloud.tencent.com/document/api/555）

### 1.1 账单汇总

| API | 用途 | 关键参数 |
|---|---|---|
| `DescribeBillSummaryByMonth` | 月度账单汇总 | Month, PayType, ResourceId |
| `DescribeBillSummaryByProduct` | 按产品汇总 | Month, PayType |
| `DescribeBillSummaryByProject` | 按项目汇总 | Month, PayType |
| `DescribeBillSummaryByRegion` | 按区域汇总 | Month, PayType |
| `DescribeBillSummaryByPayMode` | 按计费模式汇总 | Month, PayType |

### 1.2 账单明细

| API | 用途 | 关键参数 |
|---|---|---|
| `DescribeBillList` | L0-L3 明细流水 | Month, Offset, Limit, SortType, PayType |
| `DescribeBillResourceSummary` | 资源级账单 | Month, PayType, ResourceId |
| `DescribeBillDetail` | 账单详情 | BillId |

### 1.3 成本分析

| API | 用途 | 关键参数 |
|---|---|---|
| `DescribeCostSummary` | 成本汇总 | Month, DimensionType |
| `DescribeCostDetail` | 成本明细 | Month, DimensionType, DimensionTagKey, DimensionPeriodType |
| `DescribeCostSummaryByResource` | 按资源成本汇总 | Month |
| `DescribeCostSummaryByProduct` | 按产品成本汇总 | Month |

### 1.4 账户与资金

| API | 用途 | 关键参数 |
|---|---|---|
| `DescribeAccountBalance` | 账户余额 | - |
| `DescribeBillAdjust` | 账单调整（退费/补偿）| Month |
| `DescribeVoucherInfo` | 代金券详情 | VoucherId |
| `DescribeResourcePackageList` | 资源包列表 | - |
| `DescribeResourcePackageUsage` | 资源包使用量 | ResourcePackageId |

## 2. 订单/交易（cloud.tencent.com/document/api/557）

| API | 用途 | 关键参数 |
|---|---|---|
| `DescribeOrders` | 订单列表 | Status, CreateTimeStart, CreateTimeEnd, Offset, Limit |
| `DescribePayDeals` | 收支明细（pay deals）| StartTime, EndTime, Offset, Limit |
| `DescribeDeal` | 订单详情 | DealId |
| `Refund` | 退订 | DealId |

**订单 Status 枚举**（以官方为准）：
- `unpaid` - 未支付
- `paid` - 已支付
- `cancelled` - 已取消
- `refunding` - 退款中
- `refunded` - 已退款

## 3. 代金券（cloud.tencent.com/document/api/558）

| API | 用途 | 关键参数 |
|---|---|---|
| `DescribeVoucherList` | 代金券列表 | Status, VoucherId, Offset, Limit |
| `DescribeVoucherInfo` | 代金券详情 | VoucherId |

**代金券 Status 枚举**（以官方为准）：
- `unused` - 未使用（可用）
- `used` - 已使用
- `expired` - 已过期
- `freezed` - 冻结中

## 4. 标签（cloud.tencent.com/document/api/651）

| API | 用途 | 关键参数 |
|---|---|---|
| `GetTagKeys` | 拉取所有 Tag Key | Offset, Limit, ShowProject |
| `GetTagValues` | 拉取指定 Key 的 Value | TagKey, Offset, Limit |
| `GetResources` | 按 Tag 查资源 | TagFilters, ResourceList |
| `DescribeTagKeys` | 标签键列表（标签服务）| - |
| `DescribeResourceTags` | 资源标签 | Resource |

> **重要**：账单 API 的 `DimensionTagKey` 需要先在 Tag 服务中存在，否则返回空。

## 5. 监控（cloud.tencent.com/document/api/248）

> 通过 `qcloud-monitor-ops` 联动使用，本 skill 不直接调用。

| API | 用途 |
|---|---|
| `DescribeStatisticData` | 拉监控指标 |
| `DescribeAlarmRules` | 告警策略列表 |
| `CreateAlarmRule` | 创建告警策略 |
| `DescribeAlarmCallbacks` | 告警通道 |

## 6. 各产品元数据 API（联动分析用）

> 用于模块 5 优化建议和模块 3 成本归因。完整列表见各产品 skill。

| 产品 | 主要 API | 用途 |
|---|---|---|
| CVM | `DescribeInstances` | 实例规格/标签/状态 |
| CDB | `DescribeDBInstances` | 数据库实例 |
| CLB | `DescribeLoadBalancers` | 负载均衡 |
| COS | `GetBucket` / `ListBucket` | 存储桶 |
| ES | `DescribeInstances` | ES 集群 |
| Redis | `DescribeInstances` | Redis 实例 |
| VPC | `DescribeNatGateways` / `DescribeAddresses` | NAT/EIP |
| CBS | `DescribeDisks` | 磁盘 |

## 7. 关键参数说明

### 7.1 Month 格式

统一使用 `YYYY-MM`：
```bash
tccli billing DescribeBillList --Month "2026-05"
```

### 7.2 PayType 枚举

- `prePay` - 预付费（包年包月）
- `postPay` - 后付费（按量计费）
- `prePayAndPostPay` - 全部（推荐默认）

### 7.3 分页参数

- `Offset` - 起始位置
- `Limit` - 每页条数（最大 1000）
- 循环拉取：`(Offset += Limit) until total < Limit`

### 7.4 排序

- `SortType` - `asc` / `desc`
- 按 `Fee`（金额）/ `Time`（时间）排序

## 8. 限流与重试

| 接口 | 默认 QPS 限制 | 退避建议 |
|---|---|---|
| 账单类 | 20 QPS | 指数退避 1s → 2s → 4s |
| 订单类 | 10 QPS | 退避 2s → 4s → 8s |
| 标签类 | 30 QPS | 退避 1s → 2s → 4s |

详细错误码 → `references/api-cross-check.md`。
