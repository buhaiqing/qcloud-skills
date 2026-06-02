# API 校对清单与错误码速查

> 本文件由 `SKILL.md` 引用。**首次落地前必做**：对照腾讯云官方文档逐项核对本清单。

## 1. 校对清单

### 1.1 账单产品 API

- [ ] `DescribeBillSummaryByMonth`（Month / PayType / ResourceId）
- [ ] `DescribeBillSummaryByProduct`（Month / PayType）
- [ ] `DescribeBillSummaryByProject`（Month / PayType）
- [ ] `DescribeBillSummaryByRegion`（Month / PayType）
- [ ] `DescribeBillSummaryByPayMode`（Month / PayType）
- [ ] `DescribeBillList`（Offset / Limit / SortType / PayType）
- [ ] `DescribeBillResourceSummary`（Month / PayType / ResourceId）
- [ ] `DescribeBillDetail`（BillId）
- [ ] `DescribeCostSummary`（Month / DimensionType）
- [ ] `DescribeCostDetail`（DimensionType / DimensionTagKey / DimensionPeriodType）
- [ ] `DescribeAccountBalance`（返回字段命名：Balance / CashCreditBalance / AvailableCredit）
- [ ] `DescribeBillAdjust`（Month）
- [ ] `DescribeResourcePackageList`（参数与返回字段）
- [ ] `DescribeResourcePackageUsage`（ResourcePackageId）

### 1.2 订单/交易 API

- [ ] `DescribeOrders`（Status 枚举：unpaid / paid / cancelled / refunding / refunded）
- [ ] `DescribePayDeals`（StartTime / EndTime 格式）
- [ ] `DescribeDeal`（DealId）

### 1.3 代金券 API

- [ ] `DescribeVoucherList`（Status 枚举：unused / used / expired / freezed）
- [ ] `DescribeVoucherInfo`（VoucherId）

### 1.4 标签 API

- [ ] `GetTagKeys`（分页参数：Offset / Limit）
- [ ] `GetTagValues`（TagKey / Offset / Limit）
- [ ] `GetResources`（TagFilters / ResourceList）
- [ ] `DescribeResourceTags`（Resource）

### 1.5 监控 API（联动 monitor skill）

- [ ] `DescribeStatisticData`（Namespace / MetricName / Period / Instances / StartTime / EndTime）
- [ ] `DescribeAlarmRules`（返回字段）
- [ ] `CreateAlarmRule`（策略定义）

## 2. 官方文档参考

| 文档 | URL |
|---|---|
| 账单 API 完整索引 | https://cloud.tencent.com/document/api/555 |
| 订单/交易 API | https://cloud.tencent.com/document/api/557 |
| 代金券 API | https://cloud.tencent.com/document/api/558 |
| 标签 API | https://cloud.tencent.com/document/api/651 |
| 监控告警 API | https://cloud.tencent.com/document/api/248 |
| 计费规则总览 | https://cloud.tencent.com/document/product/555 |
| 控制台费用中心 | https://console.cloud.tencent.com/expense |

## 3. 错误码速查

### 3.1 通用错误

| 错误码 | 含义 | 解决方案 |
|---|---|---|
| `AuthFailure` | 凭证错误 | 检查 SecretID/Key |
| `AuthFailure.SignatureFailure` | 签名失败 | 检查密钥 + 同步时间 |
| `AuthFailure.SignatureExpired` | 签名过期 | 系统时间偏差 |
| `AuthFailure.InvalidSecretId` | SecretID 错 | CAM 控制台确认 |
| `UnauthorizedOperation` | 权限不足 | 追加 CAM 策略 |
| `InvalidParameter` | 参数错误 | 检查参数类型/格式 |
| `MissingParameter` | 缺必填参数 | 对照 API 文档 |
| `InternalError` | 服务内部错误 | 退避重试 + 报警 |
| `ResourceNotFound` | 资源不存在 | 跳过此资源 |
| `ResourceInUse` | 资源使用中 | 等待或强制操作 |

### 3.2 限流错误

| 错误码 | 含义 | 解决方案 |
|---|---|---|
| `LimitExceeded` | 接口级限流 | 退避重试 |
| `LimitExceeded.Frequency` | QPS 超限 | 降低并发 |
| `RequestLimitExceeded` | 账号级限流 | 退避重试 |
| `Throttling` | API 网关限流 | 退避重试 |
| `Throttling.User` | 用户级限流 | 等待 |

### 3.3 业务错误

| 错误码 | 含义 | 解决方案 |
|---|---|---|
| `InvalidParameter.Month` | 月份格式错 | 用 `YYYY-MM` |
| `InvalidParameter.Offset` | 越界 | 重新分页 |
| `InvalidParameter.Limit` | 过大 | 最大 1000 |
| `ResourcePackage.NotFound` | 资源包不存在 | 跳过 |
| `Order.NotFound` | 订单不存在 | 跳过 |
| `Voucher.NotFound` | 代金券不存在 | 跳过 |
| `Balance.Insufficient` | 余额不足 | 充值 |

## 4. 校对步骤建议

### 4.1 首次落地（必做）

```bash
# 1. 检查 tccli 版本
tccli --version

# 2. 检查 Python SDK 版本
pip show tencentcloud-sdk-python

# 3. 测试连接
tccli billing DescribeAccountBalance

# 4. 核对 Month 参数
tccli billing DescribeBillSummaryByMonth --Month "2026-05"

# 5. 核对账单明细
tccli billing DescribeBillList --Month "2026-05" --Limit 1
```

### 4.2 季度更新（建议）

每季度对照官方文档做一次校对：

1. 打开 `https://cloud.tencent.com/document/api/555`
2. 拉取 API 列表，与本文件 §1 清单对照
3. 拉取错误码，与本文件 §3 对照
4. 记录差异，更新 SKILL.md 和 references

### 4.3 重大变更（必做）

腾讯云公告重大变更时（如计费规则调整、API 弃用）：

1. 立即评估影响
2. 更新本文件
3. 通知团队
4. 更新 `eval_queries.json` 测试用例

## 5. 变更记录

| 日期 | 变更类型 | 影响范围 | 操作人 |
|---|---|---|---|
| 2026-06-03 | 初始版本 | - | finops-skill-generator |

> 后续变更请记录在此表，便于审计和回溯。
