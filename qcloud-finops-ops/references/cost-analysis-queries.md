# 账单查询模式与示例

> 本文件由 `SKILL.md` 引用。常用账单查询 CLI/SDK 模式、完整异常工作流示例、报告生成代码。

## 1. 基础查询模式

### 1.1 本月账单总览

**tccli**：
```bash
tccli billing DescribeBillSummaryByMonth \
  --Month "2026-05" \
  --PayType "prePayAndPostPay"
```

**Python SDK**：
```python
from tencentcloud.billing.v20180709 import billing_client, models
client = billing_client.BillingClient(cred, "ap-guangzhou")
req = models.DescribeBillSummaryByMonthRequest()
req.Month, req.PayType = "2026-05", "prePayAndPostPay"
resp = client.DescribeBillSummaryByMonth(req)
print(resp.to_json_string())
```

### 1.2 按产品汇总

```bash
tccli billing DescribeBillSummaryByProduct \
  --Month "2026-05" \
  --PayType "prePayAndPostPay"
```

返回示例（伪）：
```json
{
  "SummaryTotal": { "RealTotalCost": "128450.20" },
  "SummaryProducts": [
    { "BusinessCodeName": "云服务器CVM", "RealTotalCost": "45000.00", "Ratio": "35.04%" },
    { "BusinessCodeName": "云数据库MySQL", "RealTotalCost": "28000.00", "Ratio": "21.80%" },
    { "BusinessCodeName": "对象存储COS", "RealTotalCost": "15000.00", "Ratio": "11.68%" }
  ]
}
```

### 1.3 账单明细（L3 级）

```bash
tccli billing DescribeBillList \
  --Month "2026-05" \
  --Offset 0 \
  --Limit 100 \
  --SortType "desc" \
  --PayType "prePayAndPostPay"
```

**L0/L1/L2/L3 层级说明**：
- L0：汇总
- L1：产品 + 区域
- L2：产品 + 区域 + 计费模式
- L3：产品 + 区域 + 计费模式 + 实例 + 用量（最细）

L3 包含实例 ID 和计费项，最适合做"非预期增量"分析。

### 1.4 资源级账单

```bash
tccli billing DescribeBillResourceSummary \
  --Month "2026-05" \
  --PayType "postPay" \
  --ResourceId "cvm-abc123"
```

### 1.5 成本分析（按 Tag）

```bash
# 先拉 tag key
tccli tag GetTagKeys

# 按 tag 聚合
tccli billing DescribeCostDetail \
  --Month "2026-05" \
  --DimensionType "tag" \
  --DimensionTagKey "业务部门" \
  --DimensionPeriodType "MONTH"
```

## 2. 账户与资金查询

### 2.1 账户余额

```bash
tccli billing DescribeAccountBalance
```

返回字段：
- `Balance` - 现金余额
- `CashCreditBalance` - 现金信用余额
- `AvailableCredit` - 可用信用额度

### 2.2 代金券

```bash
# 可用代金券
tccli voucher DescribeVoucherList --Status "unused" --Limit 100

# 已使用
tccli voucher DescribeVoucherList --Status "used"

# 已过期
tccli voucher DescribeVoucherList --Status "expired"
```

### 2.3 订单

```bash
# 未支付订单
tccli trade DescribeOrders --Status "unpaid"

# 时间范围
tccli trade DescribeOrders \
  --CreateTimeStart "2026-05-01 00:00:00" \
  --CreateTimeEnd "2026-05-31 23:59:59"
```

## 3. 资源包查询

```bash
# 资源包列表
tccli billing DescribeResourcePackageList

# 资源包使用量
tccli billing DescribeResourcePackageUsage --ResourcePackageId xxx
```

**资源包使用率分析**（伪代码）：
```python
packages = describe_resource_package_list()
for pkg in packages:
    usage = describe_resource_package_usage(pkg.id)
    utilization = usage.used / pkg.total
    if utilization > 0.9:
        # 资源包快用完，建议追加
        recommend_resource_package(pkg)
    elif utilization < 0.3 and pkg.expire_days < 30:
        # 资源包快过期但用不完，建议停购
        warn_resource_package_waste(pkg)
```

## 4. 趋势分析

### 4.1 近 6 月趋势

```bash
for month in 2025-12 2026-01 2026-02 2026-03 2026-04 2026-05; do
  tccli billing DescribeBillSummaryByMonth --Month "$month" --PayType "prePayAndPostPay"
done
```

聚合为趋势表（伪代码）：
```python
months = []
for m in last_6_months:
    total = describe_bill_summary_by_month(m).RealTotalCost
    months.append({"month": m, "total": total})

# 线性回归预测下月
from sklearn.linear_model import LinearRegression
X = [[i] for i in range(len(months))]
y = [m["total"] for m in months]
model = LinearRegression().fit(X, y)
next_month_pred = model.predict([[len(months)]])[0]
```

## 5. 跨产品联动查询

### 5.1 CVM 成本归因

```bash
# 1. 拉账单（产品维度）
tccli billing DescribeBillSummaryByProduct --Month "2026-05"

# 2. 拉 CVM 实例
tccli cvm DescribeInstances --Limit 100

# 3. 拉监控（识别闲置）
tccli monitor DescribeStatisticData \
  --Namespace "QCE/CVM" \
  --MetricName "CPUUsage" \
  --Period 300 \
  --Instances.0.Dimensions.0.Name "InstanceId" \
  --Instances.0.Dimensions.0.Value "cvm-abc123" \
  --StartTime "2026-05-01 00:00:00" \
  --EndTime "2026-05-31 23:59:59"
```

### 5.2 COS 存储分层建议

```bash
# 1. 拉 COS bucket
tccli cos GetBucket --Bucket "my-bucket" --Region "ap-guangzhou"

# 2. 拉 bucket 用量
tccli cos GetBucketInventory --Bucket "my-bucket"

# 3. 拉对象最后访问时间
tccli cos GetBucketIntelligentTiering --Bucket "my-bucket"
```

## 6. 完整工作流示例：异常账单 → 根因分析

### 6.1 触发条件

```python
# 异常检测（详见 finops-methodology.md §2）
result = is_anomaly(current=128450, history_3m=[98000, 99500, 101000], budget=100000)
# → {"confidence": "HIGH", "ii_violated": True, "iii_violated": True}
```

### 6.2 完整步骤

```python
def handle_anomaly(month: str, anomaly: dict):
    # Step 1: 拉取账单明细
    details = describe_bill_list(month, page_all=True)

    # Step 2: 按产品聚合
    product_totals = aggregate_by_product(details)

    # Step 3: 对比上月，识别增量 Top 5
    last_month = get_previous_month(month)
    last_totals = describe_bill_summary_by_product(last_month)
    deltas = compute_delta(product_totals, last_totals)
    top5 = sorted(deltas, key=lambda x: x["delta"], reverse=True)[:5]

    # Step 4: 对每个 Top 产品，delegate 到对应产品 skill
    for item in top5:
        product = item["product"]
        delegate_to_product_skill(product, month, item["delta"])

    # Step 5: 生成根因报告
    report = generate_root_cause_report(anomaly, top5, details)

    # Step 6: 派发巡检工单
    if anomaly["confidence"] == "HIGH":
        dispatch_inspection_ticket(report, priority="HIGH")

    # Step 7: 通知告警通道
    send_alert(report, channels=["sms", "email", "wecom"])

    return report
```

### 6.3 根因报告输出

```markdown
# 异常账单根因报告 · 2026-05

## 1. 异常概览
- 本月费用：¥128,450（环比 +30.8%，超预算 28.5%）
- 置信度：**HIGH**（ii + iii 双维度违反）
- 触发时间：2026-05-31 23:59:59

## 2. Top 5 异常产品
| 排名 | 产品 | 本月 | 上月 | 增量 | 占比 |
|---|---|---|---|---|---|
| 1 | CVM | ¥45,000 | ¥30,000 | +¥15,000 | 50% |
| 2 | CDB | ¥28,000 | ¥20,000 | +¥8,000 | 27% |
| 3 | COS | ¥15,000 | ¥10,000 | +¥5,000 | 17% |
| 4 | CLB | ¥8,000 | ¥5,000 | +¥3,000 | 10% |
| 5 | 其他 | ¥32,450 | ¥33,200 | -¥750 | -3% |

## 3. CVM 异常根因（delegate qcloud-cvm-ops）
- **新增资源**：
  - cvm-abc1（8C16G 包月）+¥500/月
  - cvm-abc2（8C16G 包月）+¥500/月
  - cvm-abc3（8C16G 包月）+¥500/月
  - 合计 +¥1,500/月（占增量 10%）
- **既有资源涨价**：
  - cvm-xyz1（4C8G 按量）日均用量增长 3 倍
  - 触发原因：2026-05-15 业务上线新活动
  - 增量 +¥13,500/月
- **未变资源**：其余 12 台 CVM 用量稳定

## 4. CDB 异常根因（delegate qcloud-cdb-ops）
- 新增 1 个只读实例（cdb-ro-001）+¥3,000/月
- 主实例慢查询激增，CPU 从 30% 升至 70%
- 可能原因：缺少索引（见 qcloud-aiops-diagnosis 报告）

## 5. COS 异常根因（delegate qcloud-cos-ops）
- 新增 bucket（logs-2026）+¥2,000/月
- 既有 bucket 数据增长 50%，未配置生命周期规则

## 6. 优化建议
- **短期**（成本可控）：将新增 3 台 CVM 转为包年（节省 20%）
- **中期**（业务确认）：使用 TKE 弹性伸缩应对活动流量
- **长期**（流程改进）：建立"业务上线前成本评估"流程

## 7. 巡检工单
- **标题**：【FinOps 告警】2026-05 账单异常 · HIGH 置信度
- **派发**：业务方 + 财务
- **截止**：3 个工作日内回复
- **附件**：完整账单明细 CSV
```

## 7. 性能优化建议

### 7.1 大账单数据拉取

```python
# 分页拉取
def fetch_all_bills(month: str, page_size: int = 1000):
    offset = 0
    all_bills = []
    while True:
        resp = describe_bill_list(month, offset=offset, limit=page_size)
        all_bills.extend(resp.Data)
        if len(resp.Data) < page_size:
            break
        offset += page_size
    return all_bills
```

### 7.2 并行拉取多产品

```python
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = {
        executor.submit(describe_bill_summary_by_product, m): m
        for m in months
    }
    results = {f.result(): f for f in concurrent.futures.as_completed(futures)}
```

### 7.3 数据落盘

```python
# 大账单建议落 COS
import cos
cos.upload_file("bill-2026-05.json", "/tmp/bill-2026-05.json")
```
