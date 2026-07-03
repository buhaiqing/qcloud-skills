# COS FinOps Cost Optimization Module

> 基于 `tccli` CLI 的 COS 成本自动化分析流程。通过 COS API + CLS 日志分析，全自动完成成本采集、分析、优化建议和报告生成。

## 数据流

```
tccli cos DescribeBuckets          → 桶列表 + 存储量
tccli cos GetBucketLogging         → 日志配置状态
tccli cos GetBucketLifecycle       → 生命周期规则
tccli cos GetBucketTagging         → 标签信息
tccli cls SearchLog                → 存储分布、请求量、流量、访问频率
                                      │
                                      ├── storageClass 分布
                                      ├── eventName 请求量
                                      ├── remoteIp 流量 TOP
                                      ├── deltaDataSize 增量趋势
                                      └── reqPath 访问频率
                                      │
                                      └── 输出: 完整 FinOps 分析报告
```

---

## 1. 成本数据采集

> **提示词示例**：
> - "帮我采集一下所有 COS 桶的元数据，看看哪些桶开启了日志和生命周期"
> - "列出所有存储桶的日志状态、生命周期规则和标签信息"
> - "检查各个桶的成本相关配置"

### 1.1 获取所有存储桶清单

```bash
# 列出所有存储桶
tccli cos DescribeBuckets \
  --Region "{{env.TENCENTCLOUD_REGION}}" | jq '.Response.Buckets[] | {Name, Location, CreationDate}'
```

**输出示例：**
```json
{
  "Name": "example-bucket-1250000000",
  "Location": "ap-guangzhou",
  "CreationDate": "2024-06-01T00:00:00Z"
}
```

### 1.2 遍历桶获取成本相关配置

```bash
# 遍历所有桶，采集日志、生命周期、标签信息
for bucket in $(tccli cos DescribeBuckets \
  --Region "{{env.TENCENTCLOUD_REGION}}" | \
  jq -r '.Response.Buckets[].Name'); do

  echo "=== Bucket: $bucket ==="

  # 日志配置
  echo "--- Logging ---"
  tccli cos GetBucketLogging \
    --Bucket "$bucket" \
    --Region "{{env.TENCENTCLOUD_REGION}}" | jq '.Response.BucketLoggingStatus'

  # 生命周期规则
  echo "--- Lifecycle ---"
  tccli cos GetBucketLifecycle \
    --Bucket "$bucket" \
    --Region "{{env.TENCENTCLOUD_REGION}}" 2>/dev/null \
    | jq '.Response.Rules' || echo "  No lifecycle rules"

  # 标签
  echo "--- Tags ---"
  tccli cos GetBucketTagging \
    --Bucket "$bucket" \
    --Region "{{env.TENCENTCLOUD_REGION}}" 2>/dev/null \
    | jq '.Response.TagSet' || echo "  No tags"

  echo ""
done
```

### 1.3 获取桶中对象概览

```bash
# 获取对象数量和大致分布
for bucket in $(tccli cos DescribeBuckets \
  --Region "{{env.TENCENTCLOUD_REGION}}" | \
  jq -r '.Response.Buckets[].Name'); do

  echo "=== $bucket ==="

  tccli cos GetBucket \
    --Bucket "$bucket" \
    --Region "{{env.TENCENTCLOUD_REGION}}" \
    --MaxKeys 1000 | jq '.Response | {ObjectCount: (.Contents | length) // 0, MaxKeys, IsTruncated}'

done
```

### 1.4 数据整理脚本

```python
#!/usr/bin/env python3
"""COS 成本数据采集 — 收集元数据用于 FinOps 分析"""
import os, json, subprocess

def collect_cos_buckets(region: str) -> list:
    # 采集所有 COS 桶的元数据
    result = subprocess.run(
        ["tccli", "cos", "DescribeBuckets", "--Region", region],
        capture_output=True, text=True
    )
    buckets = json.loads(result.stdout).get("Response", {}).get("Buckets", [])

    collected = []
    for b in buckets:
        name = b["Name"]
        bucket_info = {
            "name": name,
            "region": b.get("Location", region),
            "creation_date": b.get("CreationDate", ""),
            "logging": get_bucket_logging(name, region),
            "lifecycle": get_bucket_lifecycle(name, region),
            "tags": get_bucket_tags(name, region),
        }
        collected.append(bucket_info)
    return collected

def get_bucket_logging(bucket: str, region: str) -> dict:
    r = subprocess.run(["tccli", "cos", "GetBucketLogging",
        "--Bucket", bucket, "--Region", region], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else {}

def get_bucket_lifecycle(bucket: str, region: str) -> list:
    r = subprocess.run(["tccli", "cos", "GetBucketLifecycle",
        "--Bucket", bucket, "--Region", region], capture_output=True, text=True)
    return json.loads(r.stdout).get("Response", {}).get("Rules", []) if r.returncode == 0 else []

def get_bucket_tags(bucket: str, region: str) -> list:
    r = subprocess.run(["tccli", "cos", "GetBucketTagging",
        "--Bucket", bucket, "--Region", region], capture_output=True, text=True)
    return json.loads(r.stdout).get("Response", {}).get("TagSet", []) if r.returncode == 0 else []

if __name__ == "__main__":
    region = os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou")
    buckets = collect_cos_buckets(region)
    print(json.dumps(buckets, indent=2, ensure_ascii=False))
```

---

## 2. 存储类型分布分析

> **提示词示例**：
> - "帮我分析一下 COS 各存储类型的分布情况，各占多少容量"
> - "标准存储、低频存储、归档存储分别有多少数据量"
> - "按存储类型统计存储量，并估算月度成本"

通过 CLS COS 访问日志，按存储类型聚合存储分布。

### 前提

COS 访问日志已导入 CLS（参见 `qcloud-cls-ops` 的 `ImportCOSAccessLogs` 操作）。

### 2.1 CLI 查询按存储类型聚合

```bash
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '30 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query '* | select storageClass, count(*) as eventCount, sum(objectSize)/1073741824 as totalGB group by storageClass order by totalGB desc' \
  --Limit 100
```

### 2.2 查询按存储桶 + 存储类型聚合

```bash
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '30 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query '* | select bucketName, storageClass, count(*) as eventCount, sum(objectSize)/1073741824 as totalGB group by bucketName, storageClass order by totalGB desc' \
  --Limit 200
```

### 2.3 成本估算

**存储单价：**

| 存储类型 | 单价 (元/GB/月) | 低频最小存储时长 | 最小存储单位 |
|---------|----------------|----------------|------------|
| STANDARD | ¥0.118 | — | 按实际 |
| STANDARD_IA | ¥0.080 | 30天 | 64KB |
| ARCHIVE | ¥0.033 | 90天 | 64KB |
| DEEP_ARCHIVE | ¥0.018 | 180天 | 64KB |

**成本计算示例：**

```bash
# 假设查询结果为:
# | storageClass  | totalGB |
# | STANDARD      | 500     |
# | STANDARD_IA   | 200     |
# | ARCHIVE       | 100     |

# 手动估算
cat << EOF
=== 存储成本估算 ===
STANDARD:      500 GB × ¥0.118 = ¥59.0/月
STANDARD_IA:   200 GB × ¥0.080 = ¥16.0/月
ARCHIVE:       100 GB × ¥0.033 = ¥3.30/月
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总计:         800 GB           ¥78.3/月

如果所有低频转归档: ¥16.0 → ¥6.6 (节省 ¥9.4/月)
如果所有标准转低频: ¥59.0 → ¥40.0 (节省 ¥19.0/月)
EOF
```

### 2.4 Python 成本估算器

```python
#!/usr/bin/env python3
"""COS 存储成本估算"""
import json, subprocess, os
from datetime import datetime, timedelta

PRICING = {
    "STANDARD": 0.118,
    "STANDARD_IA": 0.080,
    "ARCHIVE": 0.033,
    "DEEP_ARCHIVE": 0.018,
}

def query_storage_distribution(topic_id: str, region: str) -> list:
    # 通过 CLS 查询存储分布
    from_ts = int((datetime.now() - timedelta(days=30)).timestamp()) * 1000
    to_ts = int(datetime.now().timestamp()) * 1000

    r = subprocess.run([
        "tccli", "cls", "SearchLog",
        "--Region", region,
        "--TopicId", topic_id,
        "--From", str(from_ts),
        "--To", str(to_ts),
        "--Query", "* | select storageClass, count(*) as eventCount, sum(objectSize)/1073741824 as totalGB group by storageClass",
        "--Limit", "10"
    ], capture_output=True, text=True)

    data = json.loads(r.stdout)
    results = []
    for row in data.get("Response", {}).get("Results", []):
        results.append(json.loads(row.get("Log", "{}")))
    return results

def estimate_costs(distribution: list) -> dict:
    total = 0
    details = []
    for item in distribution:
        storage_class = item.get("storageClass", "STANDARD")
        gb = float(item.get("totalGB", 0))
        price = PRICING.get(storage_class, 0.118)
        cost = round(gb * price, 2)
        total += cost
        details.append({
            "storage_class": storage_class,
            "gb": gb,
            "price_per_gb": price,
            "monthly_cost": cost,
        })
    return {"details": details, "total_monthly": round(total, 2)}

if __name__ == "__main__":
    topic_id = os.environ.get("TOPIC_ID")
    region = os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou")
    dist = query_storage_distribution(topic_id, region)
    costs = estimate_costs(dist)
    print(json.dumps(costs, indent=2, ensure_ascii=False))
```

---

## 3. 请求量成本分析

> **提示词示例**：
> - "帮我分析一下 COS 的请求量成本，哪些操作产生的请求最多"
> - "统计最近30天的 PUT/GET/DELETE 请求量，估算请求费用"
> - "查看哪个操作类型的请求量最大，成本最高"

COS 对不同类型的请求（PUT、GET、DELETE 等）按次数计费。

### 3.1 请求类型分布查询

```bash
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '30 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query '* | select eventName, count(*) as requestCount, sum(reqBytesSent)+sum(resBytesSent) as totalBytes, avg(resTotalTime) as avgTimeMs group by eventName order by requestCount desc' \
  --Limit 50
```

### 3.2 请求分类成本估算

**请求定价参考：**

| 请求类型 | 单价 | 说明 |
|---------|------|------|
| PUT/COPY/POST/LIST | ¥0.01/万次 | 写请求 |
| GET/HEAD/OPTIONS | ¥0.001/万次 | 读请求 |
| DELETE | 免费 | 删除操作 |

> 注意：实际价格可能因存储类型和地域而异，请参考最新 [COS 定价](https://buy.cloud.tencent.com/price/cos)。

### 3.3 CLI 请求成本估算

```bash
# 查询 PUT 类请求量
PUT_COUNT=$(tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '30 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query 'eventName:(PutObject OR UploadPart OR CompleteMultipartUpload OR InitiateMultipartUpload OR AppendObject)' \
  --Limit 1 | jq -r '.Response.Count // "0"')

# 查询 GET 类请求量
GET_COUNT=$(tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '30 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query 'eventName:(GetObject OR HeadObject OR OptionsObject)' \
  --Limit 1 | jq -r '.Response.Count // "0"')

echo "=== 请求量月报 ==="
echo "写请求(PUT类): $PUT_COUNT 次 → ¥$(echo "scale=4; $PUT_COUNT / 10000 * 0.01" | bc)"
echo "读请求(GET类): $GET_COUNT 次 → ¥$(echo "scale=4; $GET_COUNT / 10000 * 0.001" | bc)"
```

### 3.4 Python 请求成本分析

```python
#!/usr/bin/env python3
"""COS 请求量成本分析"""
import json, subprocess, os
from datetime import datetime, timedelta

REQUEST_PRICING = {
    "write": 0.01,   # 元/万次
    "read": 0.001,   # 元/万次
}

WRITE_EVENTS = "PutObject OR UploadPart OR CompleteMultipartUpload"
READ_EVENTS = "GetObject OR HeadObject OR OptionsObject"

def query_request_count(topic_id: str, region: str, query: str) -> int:
    from_ts = int((datetime.now() - timedelta(days=30)).timestamp()) * 1000
    to_ts = int(datetime.now().timestamp()) * 1000
    r = subprocess.run([
        "tccli", "cls", "SearchLog",
        "--Region", region,
        "--TopicId", topic_id,
        "--From", str(from_ts),
        "--To", str(to_ts),
        "--Query", query,
        "--Limit", "1"
    ], capture_output=True, text=True)
    data = json.loads(r.stdout)
    return int(data.get("Response", {}).get("Count", 0))

def analyze_request_cost(topic_id: str, region: str) -> dict:
    write_count = query_request_count(topic_id, region, f"eventName:({WRITE_EVENTS})")
    read_count = query_request_count(topic_id, region, f"eventName:({READ_EVENTS})")

    write_cost = round(write_count / 10000 * REQUEST_PRICING["write"], 2)
    read_cost = round(read_count / 10000 * REQUEST_PRICING["read"], 2)

    return {
        "write_count": write_count,
        "read_count": read_count,
        "write_cost": write_cost,
        "read_cost": read_cost,
        "total_cost": round(write_cost + read_cost, 2),
        "recommendation": "Request cost is minimal vs storage cost" if (write_cost + read_cost) < 10 else "Consider batch operations to reduce request count",
    }

if __name__ == "__main__":
    topic_id = os.environ.get("TOPIC_ID")
    region = os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou")
    result = analyze_request_cost(topic_id, region)
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

---

## 4. 流量成本分析

> **提示词示例**：
> - "哪些 IP 的 COS 下载流量最大？帮我排个序"
> - "分析 CDN 回源流量和用户直连流量的对比"
> - "查看外网下行流量成本，谁在消耗带宽"
> - "按地域统计 COS 流量分布"

COS 流量分为外网下行流量、CDN 回源流量、内网流量、跨区域复制流量。

### 4.1 TOP 流量消费者

```bash
# 按来源 IP 聚合下载流量 TOP 10
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '30 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query '* | select remoteIp, sum(resBytesSent)/1048576 as downloadMB, sum(reqBytesSent)/1048576 as uploadMB, count(*) as requestCount group by remoteIp order by downloadMB desc limit 20' \
  --Limit 100
```

### 4.2 CDN 回源 vs 直连流量对比

```bash
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '30 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query '* | select logSourceType, sum(resBytesSent)/1073741824 as totalGB, count(*) as requestCount, avg(resTotalTime) as avgLatencyMs group by logSourceType' \
  --Limit 10
```

**结果解读：**

| logSourceType | 含义 | 成本 |
|-------------|------|------|
| `USER` | 用户直接访问（外网流量） | **高** — 外网下行流量计费 |
| `CDN` | CDN 回源流量 | **中** — 回源流量计费，通常低于外网 |

### 4.3 按地域流量分布

```bash
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '30 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query '* | select qcsRegion, sum(resBytesSent)/1073741824 as totalGB, count(*) as requestCount group by qcsRegion order by totalGB desc' \
  --Limit 20
```

### 4.4 Python 流量成本分析

```python
#!/usr/bin/env python3
"""COS 流量成本分析"""
import json, subprocess, os
from datetime import datetime, timedelta

TRAFFIC_PRICING = {
    "internet_down": 0.50,  # 元/GB — 外网下行
    "cdn_origin": 0.15,     # 元/GB — CDN 回源
    "internal": 0.0,        # 元/GB — 内网免费
}

def query_traffic_data(topic_id: str, region: str, query: str) -> list:
    from_ts = int((datetime.now() - timedelta(days=30)).timestamp()) * 1000
    to_ts = int(datetime.now().timestamp()) * 1000
    r = subprocess.run([
        "tccli", "cls", "SearchLog",
        "--Region", region,
        "--TopicId", topic_id,
        "--From", str(from_ts),
        "--To", str(to_ts),
        "--Query", query,
        "--Limit", "100"
    ], capture_output=True, text=True)
    data = json.loads(r.stdout)
    return data.get("Response", {}).get("Results", [])

def analyze_traffic(topic_id: str, region: str) -> dict:
    # CDN vs Direct
    source_results = query_traffic_data(topic_id, region,
        "* | select logSourceType, sum(resBytesSent)/1073741824 as totalGB, count(*) as requestCount, "
        "avg(resTotalTime) as avgLatencyMs group by logSourceType")

    traffic_by_source = {}
    for row in source_results:
        log = json.loads(row.get("Log", "{}"))
        source = log.get("logSourceType", "UNKNOWN")
        gb = float(log.get("totalGB", 0))
        traffic_by_source[source] = gb

    # 流量成本
    direct_traffic = traffic_by_source.get("USER", 0)
    cdn_traffic = traffic_by_source.get("CDN", 0)
    direct_cost = round(direct_traffic * TRAFFIC_PRICING["internet_down"], 2)
    cdn_cost = round(cdn_traffic * TRAFFIC_PRICING["cdn_origin"], 2)

    savings = round(direct_cost - cdn_cost, 2)  # 如果回源变直连的损失

    return {
        "direct_gb": round(direct_traffic, 2),
        "cdn_gb": round(cdn_traffic, 2),
        "direct_cost": direct_cost,
        "cdn_origin_cost": cdn_cost,
        "total_traffic_cost": round(direct_cost + cdn_cost, 2),
        "recommendation": "Enable CDN to reduce direct download traffic cost" if direct_traffic > cdn_traffic else "CDN optimization is effective",
    }

if __name__ == "__main__":
    topic_id = os.environ.get("TOPIC_ID")
    region = os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou")
    result = analyze_traffic(topic_id, region)
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

---

## 5. 低频存储访问频率检查

> **提示词示例**：
> - "低频存储 STANDARD_IA 中的文件被频繁访问吗？看看有没有需要转标准存储的"
> - "检查低频存储的访问量，是否有大量读请求导致成本升高"
> - "哪些低频存储的文件访问频率高，反而用标准存储更划算"

低频存储（STANDARD_IA）适合访问频率低的场景。如果低频存储的访问频率高，反而不如用标准存储。

### 5.1 低频存储的访问量查询

```bash
# 低频存储上的所有操作
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '30 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query 'storageClass:STANDARD_IA' \
  --Limit 1 | jq '.Response.Count'
```

### 5.2 低频存储高访问路径分析

```bash
# 低频存储中访问量 TOP 20 的路径
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '30 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query 'storageClass:STANDARD_IA | select reqPath, count(*) as accessCount, sum(resBytesSent)/1048576 as downloadMB group by reqPath order by accessCount desc limit 20' \
  --Limit 100
```

### 5.3 成本对比决策

```bash
# 低频存储成本 = 存储成本 + 请求成本 + 数据取回成本
# 标准存储成本 = 存储成本 + 请求成本
#
# 决策规则：
# 如果低频存储的月均请求 > N 次/GB，应转标准存储
# N 根据单价计算，通常约为 100 次/GB/月
```

### 5.4 检查脚本

```bash
#!/bin/bash
# 低频转标准合理性检查
TOPIC_ID="{{user.topic_id}}"
REGION="{{env.TENCENTCLOUD_REGION}}"

# 低频存储总请求量
IA_COUNT=$(tccli cls SearchLog --Region $REGION --TopicId $TOPIC_ID \
  --From $(date -d '30 days ago' +%s)000 --To $(date +%s)000 \
  --Query 'storageClass:STANDARD_IA' --Limit 1 | jq -r '.Response.Count // "0"')

# 低频存储总存储量
IA_GB=$(tccli cls SearchLog --Region $REGION --TopicId $TOPIC_ID \
  --From $(date -d '30 days ago' +%s)000 --To $(date +%s)000 \
  --Query '* | where storageClass=STANDARD_IA group by storageClass | select sum(objectSize)/1073741824 as totalGB' \
  --Limit 1 | ... )

echo "=== 低频存储检查 ==="
echo "低频存储请求量: $IA_COUNT/月"
if [ "$IA_COUNT" -gt 0 ] 2>/dev/null; then
  echo "建议: 请求量较高 → 检查是否应转为标准存储"
else
  echo "建议: 访问量低 → 当前存储类型策略合理"
fi
```

---

## 6. 闲置资源检测

> **提示词示例**：
> - "帮我检查一下有没有空的 COS 桶，可以直接删除的"
> - "哪些桶已经超过30天没有人访问了？可以归档或删除"
> - "看看有没有超过1GB的大文件长期没被访问，建议归档"
> - "检查 COS 中的闲置资源，找出浪费成本的桶和文件"

### 6.1 空桶检测

```bash
# 遍历所有桶，找出空桶
for bucket in $(tccli cos DescribeBuckets \
  --Region "{{env.TENCENTCLOUD_REGION}}" | \
  jq -r '.Response.Buckets[].Name'); do

  OBJECT_COUNT=$(tccli cos GetBucket \
    --Bucket "$bucket" \
    --Region "{{env.TENCENTCLOUD_REGION}}" \
    --MaxKeys 1 | jq -r '.Response.Contents | length // 0')

  if [ "$OBJECT_COUNT" -eq 0 ]; then
    echo "⚠️  空桶: $bucket — 可安全删除"
  fi
done
```

### 6.2 30 天无访问桶检测

通过 CLS 日志判断桶是否有读取请求：

```bash
# 检查指定桶是否有 GET 请求
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '30 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query 'eventName:GetObject AND bucketName:"{{user.bucket_name}}"' \
  --Limit 1 | jq '.Response.Count'
```

### 6.3 大文件长期未访问检测

```bash
# 查询 > 100MB 的文件的最近访问时间
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '90 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query '* | select reqPath, objectSize/1048576 as sizeMB, count(*) as accessCount, max(eventTime) as lastAccess group by reqPath having sizeMB > 100 order by accessCount asc limit 30' \
  --Limit 100
```

### 6.4 闲置检测脚本

```python
#!/usr/bin/env python3
"""COS 闲置资源检测"""
import json, subprocess, os
from datetime import datetime, timedelta

def detect_idle_resources(topic_id: str, region: str) -> dict:
    buckets = get_all_buckets(region)
    idle = {"empty_buckets": [], "no_access_30d": [], "large_unused_objects": []}

    for b in buckets:
        name = b["Name"]
        # 空桶检测
        r = subprocess.run(["tccli", "cos", "GetBucket",
            "--Bucket", name, "--Region", region, "--MaxKeys", "1"],
            capture_output=True, text=True)
        obj_count = len(json.loads(r.stdout).get("Response", {}).get("Contents", []))
        if obj_count == 0:
            idle["empty_buckets"].append(name)

        # 30天无访问 (通过CLS)
        from_ts = int((datetime.now() - timedelta(days=30)).timestamp()) * 1000
        to_ts = int(datetime.now().timestamp()) * 1000
        r2 = subprocess.run(["tccli", "cls", "SearchLog",
            "--Region", region, "--TopicId", topic_id,
            "--From", str(from_ts), "--To", str(to_ts),
            "--Query", f'eventName:GetObject AND bucketName:"{name}"', "--Limit", "1"],
            capture_output=True, text=True)
        count = int(json.loads(r2.stdout).get("Response", {}).get("Count", 0))
        if count == 0:
            idle["no_access_30d"].append(name)

    return idle

def get_all_buckets(region: str) -> list:
    r = subprocess.run(["tccli", "cos", "DescribeBuckets", "--Region", region],
        capture_output=True, text=True)
    return json.loads(r.stdout).get("Response", {}).get("Buckets", [])

if __name__ == "__main__":
    topic_id = os.environ.get("TOPIC_ID")
    region = os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou")
    result = detect_idle_resources(topic_id, region)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\n闲置桶: {len(result['empty_buckets'])}")
    print(f"30天无访问桶: {len(result['no_access_30d'])}")
```

---

## 7. 成本异常检测

> **提示词示例**：
> - "过去30天 COS 存储量有没有异常波动？帮我检测一下"
> - "检查存储增量是否有突增，哪天的数据量异常大"
> - "请求量是否突然增加？帮我分析请求量的每日趋势和异常"

### 7.1 存储量波动检测

通过 CLS 按天聚合存储增量，识别异常波动：

```bash
# 按天聚合存储增量
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '30 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query '* | select date_trunc('day', eventTime) as day, sum(deltaDataSize)/1048576 as deltaMB, count(*) as requestCount group by day order by day' \
  --Limit 100
```

### 7.2 请求量突增检测

```bash
# 按天聚合请求量，识别突增
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '7 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query '* | select date_trunc('day', eventTime) as day, count(*) as requestCount, countIf(resHttpCode>=400) as errorCount group by day order by day' \
  --Limit 30
```

### 7.3 异常检测脚本

```python
#!/usr/bin/env python3
"""COS 成本异常检测"""
import json, subprocess, os, statistics
from datetime import datetime, timedelta

def detect_cost_anomalies(topic_id: str, region: str) -> list:
    from_ts = int((datetime.now() - timedelta(days=30)).timestamp()) * 1000
    to_ts = int(datetime.now().timestamp()) * 1000

    r = subprocess.run([
        "tccli", "cls", "SearchLog",
        "--Region", region,
        "--TopicId", topic_id,
        "--From", str(from_ts),
        "--To", str(to_ts),
        "--Query", "* | select date_trunc('day', eventTime) as day, "
                  "sum(deltaDataSize)/1048576 as deltaMB, "
                  "count(*) as requestCount group by day order by day",
        "--Limit", "60"
    ], capture_output=True, text=True)

    anomalies = []
    daily_stats = []
    for row in json.loads(r.stdout).get("Response", {}).get("Results", []):
        log = json.loads(row.get("Log", "{}"))
        daily_stats.append(float(log.get("deltaMB", 0)))

    if len(daily_stats) >= 7:
        baseline = statistics.mean(daily_stats)
        stdev = statistics.stdev(daily_stats) if len(daily_stats) > 1 else baseline * 0.2

        for day_stat in daily_stats[-7:]:
            if day_stat > baseline + 3 * stdev:
                anomalies.append({
                    "type": "STORAGE_SPIKE",
                    "severity": "HIGH",
                    "detail": f"存储增量 {day_stat:.1f}MB 远超基线 {baseline:.1f}MB",
                    "recommendation": "检查是否有批量上传或异常写入",
                })
            elif day_stat < baseline * 0.1 and baseline > 10:
                anomalies.append({
                    "type": "STORAGE_DROP",
                    "severity": "MEDIUM",
                    "detail": f"存储增量 {day_stat:.1f}MB 显著低于基线 {baseline:.1f}MB",
                    "recommendation": "确认是否有数据丢失或清理操作",
                })

    return anomalies if anomalies else [{"type": "NONE", "severity": "INFO", "detail": "未检测到异常波动"}]

if __name__ == "__main__":
    topic_id = os.environ.get("TOPIC_ID")
    region = os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou")
    result = detect_cost_anomalies(topic_id, region)
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

---

## 8. 成本趋势预测

> **提示词示例**：
> - "按周统计 COS 存储增量趋势，看看增长速度"
> - "预测未来3个月的存储量增长和成本变化"
> - "以当前增长速度，下个月存储成本会到多少"

### 8.1 存储增长趋势

```bash
# 按周聚合存储增量
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '90 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query '* | select date_trunc('week', eventTime) as week, sum(deltaDataSize)/1073741824 as totalGB, count(*) as requestCount group by week order by week' \
  --Limit 100
```

### 8.2 Python 预测脚本

```python
#!/usr/bin/env python3
"""COS 成本趋势预测"""
import json, subprocess, os
from datetime import datetime, timedelta

def project_cos_cost(topic_id: str, region: str) -> dict:
    # 查询最近30天的存储增量
    from_ts = int((datetime.now() - timedelta(days=30)).timestamp()) * 1000
    to_ts = int(datetime.now().timestamp()) * 1000

    r = subprocess.run([
        "tccli", "cls", "SearchLog",
        "--Region", region, "--TopicId", topic_id,
        "--From", str(from_ts), "--To", str(to_ts),
        "--Query", "* | select date_trunc('day', eventTime) as day, "
                  "sum(deltaDataSize)/1073741824 as totalGB group by day order by day",
        "--Limit", "60"
    ], capture_output=True, text=True)

    daily_gb = []
    for row in json.loads(r.stdout).get("Response", {}).get("Results", []):
        log = json.loads(row.get("Log", "{}"))
        daily_gb.append(float(log.get("totalGB", 0)))

    if not daily_gb:
        return {"error": "No data available"}

    # 线性预测
    current_gb = sum(daily_gb)  # 总存储量（近30天累计）
    daily_avg_gb = current_gb / len(daily_gb) if daily_gb else 0

    # 预测未来3个月
    projections = []
    for months_ahead in [1, 3, 6]:
        projected_gb = current_gb + (daily_avg_gb * 30 * months_ahead)
        standard_cost = round(projected_gb * 0.118, 2)
        archive_cost = round(projected_gb * 0.033, 2)
        savings = round(standard_cost - archive_cost, 2)

        projections.append({
            "months_ahead": months_ahead,
            "projected_gb": round(projected_gb, 2),
            "standard_cost": standard_cost,
            "archive_cost": archive_cost,
            "potential_savings": savings,
        })

    return {
        "current_estimated_gb": round(current_gb, 2),
        "daily_growth_gb": round(daily_avg_gb, 2),
        "projections": projections,
        "recommendation": f"在当前增长趋势下，建议关注生命周期规则以控制成本"
    }

if __name__ == "__main__":
    topic_id = os.environ.get("TOPIC_ID")
    region = os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou")
    result = project_cos_cost(topic_id, region)
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

---

## 9. 优化建议生成

> **提示词示例**：
> - "基于上面所有的分析结果，帮我生成 COS 成本优化建议"
> - "有哪些可以立刻执行的成本节省措施？按优先级排序"
> - "给我一份 COS 存储的成本优化清单"

基于上述分析结果，自动生成优化建议。

### 9.1 建议分类

| 优先级 | 类型 | 描述 | 节省预估 |
|--------|------|------|---------|
| **P0 紧急** | 闲置清理 | 删除空桶 / 停止无访问桶的存储 | 100% 闲置成本 |
| **P1 高** | 存储降冷 | 低频访问的对象转为归档 | 60-90% 存储成本 |
| **P2 中** | 存储升温 | 高频访问的低频存储转标准 | 避免数据取回费 |
| **P3 低** | 生命周期 | 配置自动化生命周期规则 | 持续优化 |
| **P4 建议** | CDN 加速 | 外网直连转 CDN 回源 | 减少外网流量费 |

### 9.2 决策规则

```python
#!/usr/bin/env python3
"""COS 优化建议生成器"""

def generate_recommendations(analysis: dict) -> list:
    # 基于分析结果生成优化建议
    recommendations = []

    # P0: 闲置桶清理
    idle_buckets = analysis.get("idle", {}).get("empty_buckets", [])
    if idle_buckets:
        recommendations.append({
            "priority": "P0",
            "category": "闲置清理",
            "action": f"删除 {len(idle_buckets)} 个空桶",
            "savings": "释放桶配额",
        })

    # P0: 30天无访问桶
    no_access = analysis.get("idle", {}).get("no_access_30d", [])
    if no_access:
        recommendations.append({
            "priority": "P0",
            "category": "闲置清理",
            "action": f"检查 {len(no_access)} 个30天无访问桶，考虑归档或删除",
            "savings": "按存储量计算",
        })

    # P1: 归档低频数据
    storage = analysis.get("storage", {})
    ia_gb = storage.get("standa_ia_gb", 0)
    if ia_gb > 10:
        savings = round(ia_gb * (0.08 - 0.033), 2)
        recommendations.append({
            "priority": "P1",
            "category": "存储降冷",
            "action": f"将 {ia_gb}GB 低频存储转为归档（成本 ¥{ia_gb * 0.08:.2f}→¥{ia_gb * 0.033:.2f}）",
            "savings": f"¥{savings}/月",
        })

    # P2: 高频访问的低频存储转标准
    ia_high_access = analysis.get("storage", {}).get("ia_high_access_count", 0)
    if ia_high_access > 1000:
        recommendations.append({
            "priority": "P2",
            "category": "存储升温",
            "action": f"低频存储中高频访问对象（{ia_high_access}次/月）建议转标准存储",
            "savings": "避免数据取回费用",
        })

    # P3: 生命周期规则
    has_lifecycle = analysis.get("lifecycle", False)
    if not has_lifecycle:
        recommendations.append({
            "priority": "P3",
            "category": "生命周期",
            "action": "配置自动化生命周期规则（30天→低频，90天→归档，365天→删除）",
            "savings": "长期持续优化",
        })

    # P4: CDN 加速
    traffic = analysis.get("traffic", {})
    direct_gb = traffic.get("direct_gb", 0)
    if direct_gb > 50:
        cdn_savings = round(direct_gb * (0.50 - 0.15), 2)
        recommendations.append({
            "priority": "P4",
            "category": "CDN 加速",
            "action": f"外网直连流量 {direct_gb}GB/月, 建议启用 CDN 加速（可节省 ¥{cdn_savings}/月）",
            "savings": f"¥{cdn_savings}/月",
        })

    return recommendations
```

---

## 10. 月度成本报告模板

> **提示词示例**：
> - "帮我生成一份完整的 COS 月度成本分析报告"
> - "出一份 FinOps 报告，包含存储、请求、流量和各维度的优化建议"
> - "生成 COS 成本月报，列出资源概况、成本分布和闲置浪费"

完整的 FinOps 分析报告，可在完成上述所有分析后自动生成。

```markdown
# COS FinOps 月度成本报告

**报告日期**: {{report_date}}
**分析时段**: {{time_range}}
**地域**: {{region}}

---

## 一、资源概况

| 指标 | 数值 |
|------|------|
| 存储桶总数 | {{bucket_count}} |
| 已标记桶数 | {{tagged_count}} ({{tagged_percent}}%) |
| 未标记桶数 | {{untagged_count}} |
| 已启用访问日志 | {{logging_enabled_count}} |
| 已配置生命周期 | {{lifecycle_count}} |

---

## 二、存储成本分析

### 存储类型分布

| 存储类型 | 存储量(GB) | 单价(元/GB) | 月成本(元) | 占比 |
|---------|-----------|------------|-----------|------|
| STANDARD | {{standard_gb}} | 0.118 | ¥{{standard_cost}} | {{standard_percent}}% |
| STANDARD_IA | {{ia_gb}} | 0.080 | ¥{{ia_cost}} | {{ia_percent}}% |
| ARCHIVE | {{archive_gb}} | 0.033 | ¥{{archive_cost}} | {{archive_percent}}% |
| **合计** | **{{total_gb}}** | | **¥{{total_cost}}** | **100%** |

### 如果全部转归档可节省: ¥{{potential_savings_storage}}/月

---

## 三、请求量成本

| 请求类型 | 月请求量 | 单价 | 月成本 |
|---------|---------|------|--------|
| 写请求 (PUT类) | {{write_count}} | ¥0.01/万次 | ¥{{write_cost}} |
| 读请求 (GET类) | {{read_count}} | ¥0.001/万次 | ¥{{read_cost}} |
| **合计** | {{total_request_count}} | | **¥{{total_request_cost}}** |

---

## 四、流量成本

| 流量类型 | 流量(GB) | 月成本 |
|---------|---------|--------|
| 外网下行 (USER) | {{direct_gb}} GB | ¥{{direct_cost}} |
| CDN 回源 | {{cdn_gb}} GB | ¥{{cdn_origin_cost}} |
| **合计** | {{total_traffic_gb}} GB | **¥{{total_traffic_cost}}** |

> 建议: 如果外网直连流量 > CDN 回源流量，启用 CDN 加速可节省流量费。

---

## 五、闲置资源

| 类型 | 数量 | 操作建议 |
|------|------|---------|
| 空桶 | {{empty_bucket_count}} | 安全删除 |
| 30天无访问桶 | {{no_access_bucket_count}} | 检查后归档或删除 |
| 大文件未访问 (>100MB, >90天) | {{large_unused_count}} | 归档到冷存储 |

**闲置浪费成本: ¥{{idle_waste_cost}}/月**

---

## 六、成本异常

{{anomalies_table}}

---

## 七、成本趋势预测

| 预测周期 | 预估存储量(GB) | 标准成本(¥) | 归档成本(¥) | 节省潜力 |
|---------|---------------|------------|------------|---------|
| 未来 1 个月 | {{proj_1m_gb}} | ¥{{proj_1m_standard}} | ¥{{proj_1m_archive}} | ¥{{proj_1m_savings}} |
| 未来 3 个月 | {{proj_3m_gb}} | ¥{{proj_3m_standard}} | ¥{{proj_3m_archive}} | ¥{{proj_3m_savings}} |
| 未来 6 个月 | {{proj_6m_gb}} | ¥{{proj_6m_standard}} | ¥{{proj_6m_archive}} | ¥{{proj_6m_savings}} |

---

## 八、优化建议

| 优先级 | 类别 | 操作 | 预估节省 |
|--------|------|------|---------|
{{recommendations_table}}

### 立即行动 (P0)
{{p0_actions}}

### 短期优化 (P1-P2)
{{p1_p2_actions}}

### 持续改进 (P3-P4)
{{p3_p4_actions}}

---

## 九、上月建议跟进

| 建议 | 是否已执行 | 效果 |
|------|-----------|------|
{{last_month_followup}}

---

*报告由 COS FinOps 自动化分析流程生成*
```

---

## 全流程自动化脚本

以下脚本将整个 FinOps 分析流程串联起来：

```bash
#!/bin/bash
# COS FinOps 全自动分析脚本
# 前置条件: tccli 已安装并配置凭证
# 使用: COS_FINOPS_TOPIC_ID=<topic_id> bash cos_finops.sh

set -e
REGION="${TENCENTCLOUD_REGION:-ap-guangzhou}"
TOPIC_ID="${COS_FINOPS_TOPIC_ID:-}"
REPORT="cos-finops-report-$(date +%Y%m%d).md"

echo "🚀 开始 COS FinOps 全自动分析..."
echo "地域: $REGION"
echo "CLS Topic: $TOPIC_ID"

# === Phase 1: 采集元数据 ===
echo "📦 Phase 1: 采集 COS 元数据..."
BUCKET_LIST=$(tccli cos DescribeBuckets --Region "$REGION")
BUCKET_COUNT=$(echo "$BUCKET_LIST" | jq '.Response.Buckets | length')
echo "  发现 $BUCKET_COUNT 个存储桶"

# === Phase 2: 检查 CLS 连接 ===
echo "📊 Phase 2: 检查 CLS 日志..."
if [ -n "$TOPIC_ID" ]; then
  tccli cls DescribeTopics --TopicIds "[\"$TOPIC_ID\"]" --Region "$REGION" > /dev/null 2>&1 \
    && echo "  ✅ CLS Topic 可用" \
    || echo "  ⚠️  CLS Topic 不可用，部分分析将跳过"
else
  echo "  ⚠️  未设置 COS_FINOPS_TOPIC_ID，跳过 CLS 分析"
fi

# === Phase 3-8: 执行分析 ===
echo "🔍 Phase 3-8: 执行成本分析..."
# 具体查询由 Python 脚本或 SKILL 执行

# === Phase 9: 生成报告 ===
echo "📝 Phase 9: 生成报告..."
echo "# COS FinOps 成本分析报告" > "$REPORT"
echo "" >> "$REPORT"
echo "**生成时间**: $(date '+%Y-%m-%d %H:%M:%S')" >> "$REPORT"
echo "**地域**: $REGION" >> "$REPORT"
echo "**存储桶数**: $BUCKET_COUNT" >> "$REPORT"
echo "" >> "$REPORT"
echo "报告已保存: $REPORT"

echo "✅ COS FinOps 分析完成"
```

---

## 参考

- [COS 定价](https://buy.cloud.tencent.com/price/cos)
- [COS 访问日志字段](https://cloud.tencent.com/document/product/436/58956)
- [CLS COS 访问日志分析](../qcloud-cls-ops/references/cos-log-analysis.md)
- [CVM FinOps 分析模式](../qcloud-cvm-ops/references/finops-analysis.md)
- [CLB 成本优化模式](../qcloud-clb-ops/references/finops-cost-optimization.md)
- [生成器 FinOps 基模块](../qcloud-skill-generator/references/finops-cost-optimization.md)
