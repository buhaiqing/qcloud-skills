# Python SDK 兜底路径

> 本文件由 `SKILL.md` 引用。CLI 字段不全、特殊参数、复杂逻辑、批量操作时使用 Python SDK 兜底。

## 1. 环境准备

### 1.1 安装

```bash
pip install tencentcloud-sdk-python
# 或指定产品
pip install tencentcloud-sdk-python-billing
pip install tencentcloud-sdk-python-trade
```

### 1.2 凭证初始化

```python
import os
from tencentcloud.common import credential

cred = credential.Credential(
    os.getenv("TENCENTCLOUD_SECRET_ID"),
    os.getenv("TENCENTCLOUD_SECRET_KEY")
)
```

## 2. 账单 SDK

### 2.1 客户端初始化

```python
from tencentcloud.billing.v20180709 import billing_client, models

client = billing_client.BillingClient(cred, "ap-guangzhou")
```

### 2.2 月度账单汇总

```python
req = models.DescribeBillSummaryByMonthRequest()
req.Month = "2026-05"
req.PayType = "prePayAndPostPay"

resp = client.DescribeBillSummaryByMonth(req)
print(f"Total: {resp.SummaryTotal.RealTotalCost}")
```

### 2.3 账单明细分页拉取

```python
def fetch_all_bills(month: str) -> list:
    all_bills = []
    offset = 0
    page_size = 1000

    while True:
        req = models.DescribeBillListRequest()
        req.Month = month
        req.Offset = offset
        req.Limit = page_size
        req.SortType = "desc"
        req.PayType = "prePayAndPostPay"

        resp = client.DescribeBillList(req)
        all_bills.extend(resp.Data)

        if len(resp.Data) < page_size:
            break
        offset += page_size

    return all_bills
```

### 2.4 资源级账单

```python
req = models.DescribeBillResourceSummaryRequest()
req.Month = "2026-05"
req.PayType = "postPay"
req.ResourceId = "cvm-abc123"

resp = client.DescribeBillResourceSummary(req)
for item in resp.Data:
    print(f"{item.ResourceName}: ¥{item.RealCost}")
```

### 2.5 成本分析

```python
req = models.DescribeCostDetailRequest()
req.Month = "2026-05"
req.DimensionType = "tag"
req.DimensionTagKey = "业务部门"
req.DimensionPeriodType = "MONTH"

resp = client.DescribeCostDetail(req)
for item in resp.Data:
    print(f"{item.TagValue}: ¥{item.Cost}")
```

### 2.6 账户余额

```python
req = models.DescribeAccountBalanceRequest()
resp = client.DescribeAccountBalance(req)
print(f"Cash: ¥{resp.Balance}")
print(f"Available Credit: ¥{resp.AvailableCredit}")
```

## 3. Trade SDK

### 3.1 客户端初始化

```python
from tencentcloud.trade.v20220708 import trade_client, models

trade = trade_client.TradeClient(cred, "ap-guangzhou")
```

### 3.2 订单查询

```python
req = models.DescribeOrdersRequest()
req.Status = "unpaid"
req.Offset = 0
req.Limit = 100

resp = trade.DescribeOrders(req)
for order in resp.Orders:
    print(f"Order {order.OrderId}: {order.Status} - ¥{order.RealTotalAmount}")
```

### 3.3 收支明细

```python
req = models.DescribePayDealsRequest()
req.StartTime = "2026-05-01 00:00:00"
req.EndTime = "2026-05-31 23:59:59"

resp = trade.DescribePayDeals(req)
total_pay = sum(d.PayAmount for d in resp.Deals if d.Status == "PAID")
print(f"Total paid: ¥{total_pay}")
```

## 4. Voucher SDK

### 4.1 客户端初始化

```python
from tencentcloud.voucher.v20170316 import voucher_client, models

voucher = voucher_client.VoucherClient(cred, "ap-guangzhou")
```

### 4.2 代金券查询

```python
req = models.DescribeVoucherListRequest()
req.Status = "unused"
req.Limit = 100

resp = voucher.DescribeVoucherList(req)
total_value = sum(v.Amount for v in resp.VoucherList)
print(f"Available voucher: ¥{total_value}")
```

## 5. Tag SDK

### 5.1 客户端初始化

```python
from tencentcloud.tag.v20180813 import tag_client, models

tag = tag_client.TagClient(cred, "ap-guangzhou")
```

### 5.2 拉取 Tag Keys

```python
req = models.GetTagKeysRequest()
req.Offset = 0
req.Limit = 100

resp = tag.GetTagKeys(req)
for key in resp.TagKeys:
    print(f"Tag Key: {key}")
```

### 5.3 拉取 Tag Values

```python
req = models.GetTagValuesRequest()
req.TagKey = "业务部门"
req.Offset = 0
req.Limit = 100

resp = tag.GetTagValues(req)
for value in resp.TagValues:
    print(f"Tag Value: {value}")
```

## 6. 高级模式

### 6.1 异步并发

```python
import asyncio
from tencentcloud.common.aio import http

async def fetch_bills_async(month: str) -> dict:
    # 腾讯云 SDK 同步调用，可用 ThreadPoolExecutor 转异步
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fetch_bills, month)

async def main():
    months = ["2026-03", "2026-04", "2026-05"]
    tasks = [fetch_bills_async(m) for m in months]
    results = await asyncio.gather(*tasks)
    return results
```

### 6.2 错误处理

```python
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

try:
    resp = client.DescribeBillList(req)
except TencentCloudSDKException as e:
    if "AuthFailure" in e.code:
        # 凭证错误
        raise
    elif "LimitExceeded" in e.code:
        # 限流，指数退避
        import time
        time.sleep(2 ** retry_count)
        retry()
    else:
        raise
```

### 6.3 客户端连接池

```python
# 复用客户端，避免重复建连
_client_cache = {}

def get_billing_client():
    if "billing" not in _client_cache:
        _client_cache["billing"] = billing_client.BillingClient(cred, "ap-guangzhou")
    return _client_cache["billing"]
```

## 7. SDK 错误码速查

| 错误码 | 含义 | 解决方案 |
|---|---|---|
| `AuthFailure` | 凭证错误 | 检查 SecretID/Key |
| `InvalidParameter` | 参数错误 | 检查参数类型/格式 |
| `ResourceNotFound` | 资源不存在 | 跳过此资源 |
| `LimitExceeded` | 限流 | 退避重试 |
| `InternalError` | 服务内部错误 | 退避重试 + 报警 |
| `UnauthorizedOperation` | 权限不足 | 追加 CAM 策略 |
| `RequestLimitExceeded` | 账号级 QPS 限流 | 降低并发 |

详细错误码 → `references/api-cross-check.md`。
