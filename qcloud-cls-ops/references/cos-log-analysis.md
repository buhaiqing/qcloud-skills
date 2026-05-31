# CLS COS Access Log Analysis

> 使用 CLS 对 COS（对象存储）访问日志进行检索、分析和审计。

## 数据流架构

```
COS 源存储桶
  │ 启用访问日志记录（PutBucketLogging）
  ▼
COS 目标存储桶（存放原始访问日志文件）
  │ CreateCosRecharge（CLS COS 导入任务）
  ▼
CLS 日志主题（结构化后的 COS 访问日志）
  │ CreateIndex（配置 Key-Value 索引）
  ▼
CLS 检索分析（SearchLog + SQL 分析）
  │
  ├── 故障排查：对象无法访问、权限拒绝
  ├── 安全审计：异常 IP、越权操作
  ├── 性能分析：慢请求、高耗时操作
  └── 成本分析：存储类型分布、流量统计
```

---

## 前置条件

| 条件 | 检查方法 | 说明 |
|------|---------|------|
| COS 访问日志已开启 | `tccli cos GetBucketLogging --Bucket {{user.bucket_name}}` | 需在源桶上启用日志投递 |
| COS 目标桶存在 | 委托 `qcloud-cos-ops` | 日志写入的目标桶 |
| CLS 日志主题已创建 | `tccli cls DescribeTopics` | 数据将导入到该主题 |
| CLS 凭证已配置 | `TENCENTCLOUD_SECRET_ID/KEY` | 必须拥有 CLS 写权限 |

### 启用 COS 访问日志

```bash
# 通过 COS CLI 启用访问日志（需要委托 qcloud-cos-ops）
tccli cos PutBucketLogging \
  --Bucket "{{user.source_bucket}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --BucketLoggingStatus '{
    "TargetBucket": "{{user.target_bucket}}",
    "TargetPrefix": "cos-access-log/"
  }'

# 验证是否已启用
tccli cos GetBucketLogging \
  --Bucket "{{user.source_bucket}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}"
```

---

## COS 访问日志字段（30个）

> 这些字段是 COS 访问日志被导入 CLS 后，CLS 自动解析出的结构化字段。

### 请求基础信息

| # | 字段名 | 类型 | 含义 | 示例值 |
|---|--------|------|------|--------|
| 1 | `eventVersion` | text | 日志版本 | `1.0` |
| 4 | `eventTime` | text | 事件时间（UTC 0 时区） | `2018-12-01T11:02:33Z` |
| 5 | `eventSource` | text | 访问域名 | `examplebucket-1250000000.cos.ap-guangzhou.myqcloud.com` |
| 30 | `requestUri` | text | 请求 URI | `GET /folder/file.txt HTTP/1.1` |
| 12 | `reqPath` | text | 请求文件路径 | `/folder/text.txt` |
| 13 | `reqMethod` | text | 请求方法（小写） | `put`、`get`、`delete`、`post`、`head` |
| 14 | `userAgent` | text | 用户 UA | `cos-go-sdk-v5.2.9` |
| 25 | `requestId` | text | 请求 ID | `NWQ1ZjY4MTBfMjZiMjU4NjRfOWI1N180NDBiYTY=` |
| 29 | `referer` | text | HTTP referer | `*.example.com` |

### 桶和对象信息

| # | 字段名 | 类型 | 含义 | 示例值 |
|---|--------|------|------|--------|
| 2 | `bucketName` | text | 存储桶名称 | `examplebucket-1250000000` |
| 3 | `qcsRegion` | text | 请求地域 | `ap-beijing` |
| 22 | `accountId` | text | 桶所有者 ID | `100000000001` |
| 21 | `storageClass` | text | 存储类型 | `STANDARD`、`STANDARD_IA`、`ARCHIVE` |
| 26 | `objectSize` | long | 对象大小（Bytes） | `808` |
| 27 | `versionId` | text | 对象版本 ID | 随机字符串 |
| 28 | `targetStorageClass` | text | 目标存储类型（复制操作） | `STANDARD`、`STANDARD_IA` |

### 操作和事件

| # | 字段名 | 类型 | 含义 | 示例值 |
|---|--------|------|------|--------|
| 6 | `eventName` | text | 事件名称（操作类型） | `PutObject`、`DeleteObject`、`UploadPart`、`GetObject` |
| 20 | `logSourceType` | text | 日志源类型 | `USER`（用户请求）、`CDN`（CDN 回源） |

**常见 eventName 枚举：**

| 操作类型 | eventName | 说明 |
|---------|-----------|------|
| 上传 | `PutObject`、`AppendObject`、`UploadPart`、`CompleteMultipartUpload` | 对象上传/追加 |
| 下载 | `GetObject`、`HeadObject`、`OptionsObject` | 对象读取 |
| 删除 | `DeleteObject`、`DeleteObjects` | 对象删除 |
| 复制 | `PutObjectCopy`、`UploadPartCopy` | 跨桶/同桶复制 |
| 创建 | `PutBucket`、`InitiateMultipartUpload` | 存储桶/分块创建 |
| 权限 | `PutBucketACL`、`GetBucketACL`、`PutBucketPolicy` | 权限变更 |
| 生命周期 | `AbortMultipartUpload`、`PostObjectRestore` | 生命周期管理 |

### 请求来源

| # | 字段名 | 类型 | 含义 | 示例值 |
|---|--------|------|------|--------|
| 7 | `remoteIp` | text | 来源 IP | `192.168.0.1` |
| 8 | `userSecretKeyId` | text | 访问 KeyId（部分掩码） | `AKID****` |
| 24 | `requester` | text | 访问者身份 | `100000000001:12345`（主账号ID:子账号ID），匿名访问为 `-` |

### 请求数据量

| # | 字段名 | 类型 | 含义 | 示例值 |
|---|--------|------|------|--------|
| 10 | `reqBytesSent` | long | 请求字节数 | `83886080` |
| 11 | `deltaDataSize` | long | 存储量改变（Bytes） | `808` |
| 18 | `resBytesSent` | long | 返回字节数 | `197` |

### 响应状态和性能

| # | 字段名 | 类型 | 含义 | 示例值 |
|---|--------|------|------|--------|
| 15 | `resHttpCode` | long | HTTP 返回码 | `200`、`403`、`404`、`500` |
| 16 | `resErrorCode` | text | 错误码 | `NoSuchKey`、`AccessDenied`、`InternalError` |
| 17 | `resErrorMsg` | text | 错误信息 | `The specified key does not exist.` |
| 19 | `resTotalTime` | long | 请求总耗时（毫秒） | `4295` |
| 23 | `resTurnAroundTime` | long | 服务端耗时（毫秒） | `4295` |

### 保留字段

| # | 字段名 | 类型 | 含义 | 示例值 |
|---|--------|------|------|--------|
| 9 | `reservedField` | text | 保留字段 | `-` |

---

## 索引配置模板

导入 COS 日志后，需要对日志主题配置索引才能进行检索。

### 完整 Key-Value 索引配置

```json
{
  "FullText": {
    "CaseSensitive": false,
    "Tokenizer": "@&?|#()='\"/:;,\\[\\]{} \t\n",
    "ContainZH": true
  },
  "KeyValue": {
    "CaseSensitive": false,
    "KeyValues": [
      {"Key": "eventVersion",     "Value": {"Type": "text"}},
      {"Key": "bucketName",       "Value": {"Type": "text"}},
      {"Key": "qcsRegion",        "Value": {"Type": "text"}},
      {"Key": "eventTime",        "Value": {"Type": "text"}},
      {"Key": "eventSource",      "Value": {"Type": "text"}},
      {"Key": "eventName",        "Value": {"Type": "text"}},
      {"Key": "remoteIp",         "Value": {"Type": "text"}},
      {"Key": "userSecretKeyId",  "Value": {"Type": "text"}},
      {"Key": "reqPath",          "Value": {"Type": "text"}},
      {"Key": "reqMethod",        "Value": {"Type": "text"}},
      {"Key": "userAgent",        "Value": {"Type": "text"}},
      {"Key": "resHttpCode",      "Value": {"Type": "long"}},
      {"Key": "resErrorCode",     "Value": {"Type": "text"}},
      {"Key": "resErrorMsg",      "Value": {"Type": "text"}},
      {"Key": "resTotalTime",     "Value": {"Type": "long"}},
      {"Key": "resTurnAroundTime","Value": {"Type": "long"}},
      {"Key": "reqBytesSent",     "Value": {"Type": "long"}},
      {"Key": "resBytesSent",     "Value": {"Type": "long"}},
      {"Key": "deltaDataSize",    "Value": {"Type": "long"}},
      {"Key": "objectSize",       "Value": {"Type": "long"}},
      {"Key": "logSourceType",    "Value": {"Type": "text"}},
      {"Key": "storageClass",     "Value": {"Type": "text"}},
      {"Key": "accountId",        "Value": {"Type": "text"}},
      {"Key": "requester",        "Value": {"Type": "text"}},
      {"Key": "requestId",        "Value": {"Type": "text"}},
      {"Key": "versionId",        "Value": {"Type": "text"}},
      {"Key": "targetStorageClass","Value": {"Type": "text"}},
      {"Key": "referer",          "Value": {"Type": "text"}},
      {"Key": "requestUri",       "Value": {"Type": "text"}},
      {"Key": "reservedField",    "Value": {"Type": "text"}}
    ]
  }
}
```

### CLI 创建索引

```bash
tccli cls CreateIndex \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --Rule '{
    "FullText": {"CaseSensitive": false, "Tokenizer": "@&?|#()='\''\"/:;,\\[\\]{} \t\n", "ContainZH": true},
    "KeyValue": {
      "CaseSensitive": false,
      "KeyValues": [
        {"Key": "eventName",     "Value": {"Type": "text"}},
        {"Key": "remoteIp",      "Value": {"Type": "text"}},
        {"Key": "reqPath",       "Value": {"Type": "text"}},
        {"Key": "reqMethod",     "Value": {"Type": "text"}},
        {"Key": "resHttpCode",   "Value": {"Type": "long"}},
        {"Key": "resErrorCode",  "Value": {"Type": "text"}},
        {"Key": "resTotalTime",  "Value": {"Type": "long"}},
        {"Key": "requester",     "Value": {"Type": "text"}},
        {"Key": "storageClass",  "Value": {"Type": "text"}},
        {"Key": "objectSize",    "Value": {"Type": "long"}},
        {"Key": "logSourceType", "Value": {"Type": "text"}},
        {"Key": "userAgent",     "Value": {"Type": "text"}},
        {"Key": "referer",       "Value": {"Type": "text"}},
        {"Key": "eventTime",     "Value": {"Type": "text"}},
        {"Key": "bucketName",    "Value": {"Type": "text"}},
        {"Key": "deltaDataSize", "Value": {"Type": "long"}},
        {"Key": "resTurnAroundTime", "Value": {"Type": "long"}},
        {"Key": "accountId",     "Value": {"Type": "text"}}
      ]
    }
  }' \
  --Status true
```

> **提示**: 对于频繁查询的字段才需要加入 Key-Value 索引。以上 18 个字段覆盖了 95% 以上的分析场景。

---

## 分析场景与查询示例

### 场景一：对象访问故障排查

> 用户反馈文件无法访问，需要定位原因。

#### 提示词示例

```
请帮我排查 COS 存储桶 {{user.bucket_name}} 中 /path/to/file.txt 无法访问的原因。
```

#### 分析流程

**Step 1 — 按文件路径检索所有相关请求**

```
reqPath:/path/to/file.txt
```

```bash
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '7 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query 'reqPath:/path/to/file.txt' \
  --Limit 100
```

**Step 2 — 按 HTTP 状态码聚合**

```
reqPath:/path/to/file.txt | select resHttpCode, count(*) as count group by resHttpCode order by count desc
```

**预期结果解读：**

| resHttpCode | 含义 | 常见原因 |
|-------------|------|---------|
| `403` | 权限拒绝 | AccessDenied — 无读取权限 |
| `404` | 不存在 | NoSuchKey — 文件已被删除或路径错误 |
| `200` | 成功 | 文件正常可访问 |
| `204` | 无内容 | DeleteObject 成功（已被删除） |

**Step 3 — 下钻分析失败请求详情**

```
resHttpCode:403 AND reqPath:/path/to/file.txt
```

```bash
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '7 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query 'resHttpCode:403 AND reqPath:/path/to/file.txt' \
  --Limit 50
```

**Step 4 — 检查是谁删除了文件**

```
eventName:DeleteObject AND reqPath:/path/to/file.txt
```

```bash
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '30 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query 'eventName:DeleteObject AND reqPath:/path/to/file.txt' \
  --Limit 20
```

**关注字段：** `requester`（谁删的）、`eventTime`（何时删的）、`remoteIp`（从哪删的）

#### 完整排查提示词模板

```
排查 COS 文件 {{reqPath}} 的访问问题：

1. 按 reqPath 检索最近7天的所有请求，关注 resHttpCode 分布
2. 如果有 403，查看 resErrorCode 和 requester，判断是权限问题还是匿名访问
3. 如果有 404，查看最近30天的 DeleteObject 事件，定位谁删除了文件
4. 如果之前可访问后来不行，以 eventTime 为分界对比前后状态
```

---

### 场景二：安全审计 — 异常访问检测

> 发现可疑 IP 或异常访问模式，需要追溯。

#### 提示词示例

```
请分析 COS 存储桶 {{user.bucket_name}} 最近24小时的异常访问情况，识别可疑的 IP 和操作。
```

#### 查询模板

**查询 1：按 IP 聚合请求量，识别高频访问者**

```
bucketName:"{{user.bucket_name}}" | select remoteIp, count(*) as reqCount, countIf(resHttpCode>=400) as errorCount group by remoteIp order by reqCount desc limit 20
```

**查询 2：识别异常 IP 的详细操作记录**

```
remoteIp:{{user.suspicious_ip}} AND bucketName:"{{user.bucket_name}}"
```

**查询 3：识别越权操作（403 请求最多的 IP）**

```
resHttpCode:403 AND bucketName:"{{user.bucket_name}}" | select remoteIp, count(*) as count group by remoteIp order by count desc limit 10
```

**查询 4：批量删除/枚举操作检测**

```
eventName:DeleteObjects AND bucketName:"{{user.bucket_name}}"
```

**查询 5：识别来自非预期地域的访问**

```
qcsRegion:("ap-hongkong" OR "na-ashburn" OR "eu-frankfurt") AND bucketName:"{{user.bucket_name}}" | select remoteIp, qcsRegion, eventName, requester, count(*) as count group by remoteIp, qcsRegion, eventName, requester
```

**查询 6：匿名访问检测（requester 为 `-`）**

```
requester:"-" AND bucketName:"{{user.bucket_name}}"
```

#### 完整安全审计提示词模板

```
审计 COS 存储桶 {{user.bucket_name}} 的安全状况：

1. 统计最近24小时各IP的访问量和错误率，排序取前20
   → bucketName:"{{user.bucket_name}}" | select remoteIp, count(*) as reqCount, countIf(resHttpCode>=400) as errorCount group by remoteIp order by reqCount desc limit 20

2. 检查是否有匿名访问（requester为"-"）
   → requester:"-" AND bucketName:"{{user.bucket_name}}"

3. 检查是否有来自海外地域的访问
   → qcsRegion:("ap-hongkong" OR "na-ashburn" OR "eu-frankfurt") AND bucketName:"{{user.bucket_name}}"

4. 检查是否有批量删除操作
   → eventName:DeleteObjects AND bucketName:"{{user.bucket_name}}"

5. 对于每个异常 IP，获取其详细操作记录
   → remoteIp:{{suspicious_ip}} AND bucketName:"{{user.bucket_name}}" | select eventTime, eventName, reqPath, resHttpCode, resErrorCode order by eventTime asc
```

---

### 场景三：性能分析 — 识别慢请求

> 用户反馈 COS 请求响应慢，需要定位瓶颈。

#### 提示词示例

```
请分析 COS 存储桶 {{user.bucket_name}} 最近1小时的请求性能，找出最慢的操作。
```

#### 查询模板

**查询 1：最慢的 TOP 20 请求**

```
bucketName:"{{user.bucket_name}}" | select eventTime, reqMethod, reqPath, objectSize, resTotalTime, resTurnAroundTime, remoteIp order by resTotalTime desc limit 20
```

**查询 2：按操作类型聚合平均耗时**

```
bucketName:"{{user.bucket_name}}" | select eventName, count(*) as count, avg(resTotalTime) as avgTime, max(resTotalTime) as maxTime, sum(resBytesSent) as totalBytes group by eventName order by avgTime desc
```

**查询 3：大文件上传性能分析**

```
eventName:PutObject AND bucketName:"{{user.bucket_name}}" AND objectSize:>104857600 | select eventTime, remoteIp, objectSize/1048576 as sizeMB, resTotalTime, reqBytesSent/1048576 as uploadMB group by eventTime, remoteIp, sizeMB, resTotalTime, uploadMB order by resTotalTime desc
```

> 说明：筛选出上传大于 100MB 文件的请求，分析上传耗时

**查询 4：分块上传性能分析**

```
eventName:(UploadPart OR CompleteMultipartUpload) AND bucketName:"{{user.bucket_name}}" | select eventName, count(*) as count, avg(resTotalTime) as avgTime, sum(reqBytesSent)/1048576 as totalUploadMB group by eventName
```

**查询 5：CDN 回源 vs 用户直连延迟对比**

```
bucketName:"{{user.bucket_name}}" | select logSourceType, avg(resTotalTime) as avgLatency, count(*) as count group by logSourceType
```

#### 完整性能分析提示词模板

```
分析 COS 存储桶 {{user.bucket_name}} 的请求性能：

1. 整体性能概览 — 按 eventName 统计平均耗时和请求量
   → bucketName:"{{user.bucket_name}}" | select eventName, count(*) as count, avg(resTotalTime) as avgTime, max(resTotalTime) as maxTime group by eventName order by avgTime desc

2. 识别最慢的 TOP 20 请求，关注大文件和高耗时
   → bucketName:"{{user.bucket_name}}" | select eventTime, reqMethod, reqPath, objectSize/1048576 as sizeMB, resTotalTime order by resTotalTime desc limit 20

3. 对比 CDN 回源和用户直连的性能差异
   → logSourceType:CDN AND bucketName:"{{user.bucket_name}}" | select avg(resTotalTime) as avgCDN, count(*) as cdnCount
   → logSourceType:USER AND bucketName:"{{user.bucket_name}}" | select avg(resTotalTime) as avgDirect, count(*) as directCount

4. 检查服务端耗时 vs 网络耗时
   → bucketName:"{{user.bucket_name}}" | select avg(resTotalTime) as avgTotal, avg(resTurnAroundTime) as avgServer, avg(resTotalTime - resTurnAroundTime) as avgNetwork
```

---

### 场景四：成本分析 — 存储与流量洞察

> 需要了解 COS 存储使用情况和流量分布。

#### 提示词示例

```
请分析 COS 存储桶 {{user.bucket_name}} 的存储类型分布和流量情况。
```

#### 查询模板

**查询 1：存储类型分布**

```
bucketName:"{{user.bucket_name}}" AND eventName:PutObject | select storageClass, count(*) as count, sum(objectSize)/1073741824 as totalGB group by storageClass
```

**查询 2：请求流量 TOP 10 操作**

```
bucketName:"{{user.bucket_name}}" | select eventName, count(*) as count, sum(reqBytesSent)+sum(resBytesSent) as totalBytes group by eventName order by totalBytes desc limit 10
```

**查询 3：按来源 IP 统计流量**

```
bucketName:"{{user.bucket_name}}" | select remoteIp, sum(resBytesSent)/1048576 as downloadMB, sum(reqBytesSent)/1048576 as uploadMB, count(*) as count group by remoteIp order by downloadMB desc limit 10
```

**查询 4：存储量变化追踪（按天聚合）**

```
bucketName:"{{user.bucket_name}}" | select date_trunc('day', eventTime) as day, sum(deltaDataSize)/1048576 as deltaMB, count(*) as count group by day order by day
```

**查询 5：低频/归档存储的访问频率分析**

```
storageClass:(STANDARD_IA OR ARCHIVE) AND bucketName:"{{user.bucket_name}}" | select storageClass, eventName, count(*) as count, avg(resTotalTime) as avgTime group by storageClass, eventName order by storageClass, count desc
```

> 场景：如果低频存储的访问频率很高，实际上用标准存储更划算

#### 完整成本分析提示词模板

```
分析 COS 存储桶 {{user.bucket_name}} 的成本构成：

1. 存储类型分布 — 了解各类存储的用量
   → eventName:PutObject AND bucketName:"{{user.bucket_name}}" | select storageClass, count(*) as count, sum(objectSize)/1073741824 as totalGB group by storageClass

2. 流量 TOP 消费者 — 从哪些 IP 产生的流量最大
   → bucketName:"{{user.bucket_name}}" | select remoteIp, sum(resBytesSent)/1048576 as downloadMB, count(*) as count group by remoteIp order by downloadMB desc limit 10

3. 低频存储的访问频率 — 判断是否需要降冷
   → storageClass:STANDARD_IA AND bucketName:"{{user.bucket_name}}" | select eventName, count(*) as count, count(distinct remoteIp) as uniqueIPs group by eventName

4. 日存储增量趋势 — 判断存储增长是否正常
   → bucketName:"{{user.bucket_name}}" AND deltaDataSize:>0 | select date_trunc('day', eventTime) as day, sum(deltaDataSize)/1048576 as deltaMB group by day order by day
```

---

### 场景五：操作审计 — 谁做了什么

> 需要追溯特定时间段内谁对 COS 执行了什么操作。

#### 提示词示例

```
请查询 COS 存储桶 {{user.bucket_name}} 中最近7天所有的 DeleteObject 操作，列出操作者和操作详情。
```

#### 查询模板

**查询 1：删除操作审计**

```
eventName:(DeleteObject OR DeleteObjects) AND bucketName:"{{user.bucket_name}}" | select eventTime, requester, remoteIp, reqPath, userAgent order by eventTime desc
```

**查询 2：权限变更审计**

```
eventName:(PutBucketACL OR PutBucketPolicy OR PutBucketCORS) AND bucketName:"{{user.bucket_name}}" | select eventTime, requester, remoteIp, eventName, reqPath order by eventTime desc
```

**查询 3：特定用户的操作历史**

```
requester:{{user.requester_id}} AND bucketName:"{{user.bucket_name}}" | select eventTime, eventName, reqPath, resHttpCode, remoteIp order by eventTime desc limit 100
```

**查询 4：特定时间段的所有写操作**

```
eventName:(PutObject OR AppendObject OR UploadPart OR CompleteMultipartUpload) AND bucketName:"{{user.bucket_name}}" AND eventTime:[{{user.start_time}} TO {{user.end_time}}] | select eventTime, requester, remoteIp, reqPath, objectSize/1048576 as sizeMB order by eventTime desc
```

#### 完整审计提示词模板

```
审计 COS 存储桶 {{user.bucket_name}} 的用户操作：

1. 所有删除操作 — 关注删除者和删除时间
   → eventName:(DeleteObject OR DeleteObjects) AND bucketName:"{{user.bucket_name}}" | select eventTime, requester, remoteIp, reqPath, userAgent order by eventTime desc

2. 所有权限变更操作 — ACL和策略修改
   → eventName:(PutBucketACL OR PutBucketPolicy) AND bucketName:"{{user.bucket_name}}" | select eventTime, requester, remoteIp, eventName, reqPath order by eventTime desc

3. 指定用户 {{user.requester_id}} 的完整操作历史
   → requester:{{user.requester_id}} AND bucketName:"{{user.bucket_name}}" | select eventTime, eventName, reqPath, resHttpCode, remoteIp order by eventTime desc limit 100
```

---

### 场景六：自定义灵活查询

#### 提示词示例

```
请统计 COS 存储桶 {{user.bucket_name}} 中各个操作类型的请求量分布。
```

#### 通用聚合查询

| 分析维度 | 查询语句 | 用途 |
|---------|---------|------|
| 按操作类型聚合 | `bucketName:"{{bucket}}" \| select eventName, count(*) as count group by eventName order by count desc` | 了解操作分布 |
| 按状态码聚合 | `bucketName:"{{bucket}}" \| select resHttpCode, count(*) as count group by resHttpCode order by count desc` | 错误率监控 |
| 按小时聚合 | `bucketName:"{{bucket}}" \| select date_trunc('hour', eventTime) as hour, count(*) as count group by hour order by hour` | 访问趋势 |
| 按 IP 聚合 | `bucketName:"{{bucket}}" \| select remoteIp, count(*) as count group by remoteIp order by count desc limit 20` | 热点 IP |
| 错误码详情 | `resHttpCode:>=400 AND bucketName:"{{bucket}}" \| select resErrorCode, resErrorMsg, count(*) as count group by resErrorCode, resErrorMsg order by count desc` | 错误根因 |
| 大文件下载 | `eventName:GetObject AND objectSize:>104857600 AND bucketName:"{{bucket}}" \| select reqPath, objectSize/1048576 as sizeMB, remoteIp, eventTime order by objectSize desc` | 大文件追踪 |

---

## 预置仪表盘

CLS 控制台提供 **"COS 访问日志分析"** 预置仪表盘，开箱即用：

| 仪表盘模块 | 展示内容 | 对应场景 |
|-----------|---------|---------|
| 请求总览 | 总请求量、流量、错误率趋势图 | 全局监控 |
| 操作 TOP N | 最频繁的操作和文件路径 | 使用热度 |
| 错误分析 | HTTP 错误码分布和错误趋势 | 故障发现 |
| 访问来源 | 按 IP 和地域分布的访问来源 | 安全审计 |
| 性能分析 | 平均响应时间和慢请求分布 | 性能监控 |

**创建仪表盘（CLI）：**

```bash
# 查看预置仪表盘列表
tccli cls DescribeDashboards \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}"

# 仪表盘操作通常通过控制台完成
# 在 CLS 控制台 → 日志主题 → 仪表盘 → 选择 "COS 访问日志分析"
```

---

## 最佳实践

### 字段选择索引策略

| 优先级 | 字段 | 理由 |
|--------|------|------|
| **必索引** | `eventName`, `remoteIp`, `reqPath`, `resHttpCode`, `resErrorCode`, `requester` | 几乎所有分析场景都需要 |
| **推荐索引** | `resTotalTime`, `bucketName`, `storageClass`, `eventTime`, `reqMethod`, `logSourceType` | 性能和成本分析 |
| **按需索引** | `objectSize`, `userAgent`, `referer`, `deltaDataSize`, `qcsRegion` | 特定场景需要 |
| **可不索引** | `requestUri`, `versionId`, `accountId`, `reservedField` | 极少使用 |

### 查询优化建议

1. **缩小时间范围**: 先聚合统计，再下钻详情
2. **善用字段过滤**: `bucketName:"xxx" AND eventName:"DeleteObject"` 比全文搜索快10倍+
3. **避免前缀通配符**: `\*Path:/file.txt` 比 `reqPath:\*/file.txt` 快得多
4. **分步分析**: 先概览 → 再聚合 → 最后看详情，避免一次拉取大量数据
5. **导出大量数据**: 使用 `CreateExport` 而非 `SearchLog` 拉取超大数据集

### 常见错误码速查

| resHttpCode | resErrorCode | 含义 | 排查方向 |
|-------------|-------------|------|---------|
| 403 | `AccessDenied` | 权限拒绝 | 检查 Bucket Policy、ACL、子账号权限 |
| 403 | `SignatureDoesNotMatch` | 签名错误 | 检查 SecretId/Key 是否正确 |
| 404 | `NoSuchBucket` | 桶不存在 | 检查桶名和地域 |
| 404 | `NoSuchKey` | 文件不存在 | 文件已被删除或路径错误 |
| 405 | `MethodNotAllowed` | 方法不允许 | CORS 配置或 CDN 回源异常 |
| 409 | `BucketAlreadyExists` | 桶已存在 | 创建桶时名称被占用 |
| 500 | `InternalError` | 服务端内部错误 | 重试或提工单 |
| 503 | `ServiceUnavailable` | 服务暂时不可用 | 等待后重试 |

---

## 参考链接

- [CLS COS 访问日志分析](https://cloud.tencent.com/document/product/614/61406) — 官方文档
- [COS 访问日志字段](https://cloud.tencent.com/document/product/436/58956) — 字段详细说明
- [CLS 检索语法](https://cloud.tencent.com/document/product/614/47044) — 查询语法参考
- [CLS SQL 分析](https://cloud.tencent.com/document/product/614/58981) — SQL 分析功能
- [CreateCosRecharge API](https://cloud.tencent.com/document/product/614/78156) — COS 数据导入 API
