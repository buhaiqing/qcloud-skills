# FinOps CLI Usage Guide

`tccli billing / trade / voucher / tag` 命令速查。

> CLI 字段不全时回退 Python SDK：见 [sdk-usage.md](sdk-usage.md)

---

## 1. 环境准备

```bash
pip install tccli
export TENCENTCLOUD_SECRET_ID="AKIDxxxx"
export TENCENTCLOUD_SECRET_KEY="xxxxx"
export TENCENTCLOUD_REGION="ap-guangzhou"
```

## 2. 账单汇总

```bash
# 月度汇总
tccli billing DescribeBillSummaryByMonth --Month "2026-05" --PayType "prePayAndPostPay"

# 按产品
tccli billing DescribeBillSummaryByProduct --Month "2026-05" --PayType "prePayAndPostPay"

# 按项目
tccli billing DescribeBillSummaryByProject --Month "2026-05" --PayType "prePayAndPostPay"

# 按区域
tccli billing DescribeBillSummaryByRegion --Month "2026-05" --PayType "prePayAndPostPay"
```

## 3. 账单明细

```bash
# L0-L3 明细（分页）
tccli billing DescribeBillList --Month "2026-05" --PayType "prePayAndPostPay" --Offset 0 --Limit 100

# 资源级账单
tccli billing DescribeBillResourceSummary --Month "2026-05" --PayType "prePayAndPostPay"
```

## 4. 成本分析

```bash
# 成本汇总
tccli billing DescribeCostSummary --Month "2026-05" --DimensionType "TYPE"

# 成本明细（按 Tag 分摊）
tccli billing DescribeCostDetail --Month "2026-05" --DimensionTagKey "业务部门" --DimensionPeriodType "MONTH"
```

## 5. 账户与资金

```bash
# 账户余额
tccli billing DescribeAccountBalance

# 资源包
tccli billing DescribeResourcePackageList
tccli billing DescribeResourcePackageUsage --ResourcePackageId "rpk-xxx"
```

## 6. 订单与代金券

```bash
# 订单列表
tccli trade DescribeOrders --Offset 0 --Limit 20

# 收支明细
tccli trade DescribePayDeals --StartTime "2026-01-01" --EndTime "2026-05-31"

# 代金券
tccli voucher DescribeVoucherList --Offset 0 --Limit 20
```

## 7. 标签

```bash
tccli tag GetTagKeys
tccli tag GetTagValues --TagKey "业务部门"
```

## 8. 常见错误

| 错误码 | 原因 | 处理 |
|--------|------|------|
| `UnauthorizedOperation.Billing` | 无计费只读权限 | HALT；追加 `QcloudBillReadOnlyAccess` 策略 |
| `InvalidParameter.Month` | 月份格式错误 | 使用 `YYYY-MM` 格式 |
| `ResourceNotFound.Bill` | 当月无账单数据 | 提示"当前月份暂无账单" |

→ 完整错误码见 [troubleshooting.md](troubleshooting.md)
→ 完整 API 参数见 [billing-api-mapping.md](billing-api-mapping.md)
