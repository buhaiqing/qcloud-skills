# CLS COS Access Log Analysis Guide

> COS 访问日志分析能力由 `qcloud-cls-ops` 提供，通过 CLS 进行检索、审计和分析。

## 概述

COS 访问日志分析是 CLS（日志服务）的能力，COS 侧只需开启访问日志记录，将日志投递到目标桶，然后通过 CLS 的 COS 数据导入功能进行分析。

## 前置条件

| 条件 | 说明 | 操作方法 |
|------|------|---------|
| COS 源桶 | 需要分析访问日志的存储桶 | — |
| COS 目标桶 | 存放访问日志文件的存储桶 | 可与源桶相同或不同 |
| COS 访问日志已开启 | 源桶上启用了访问日志记录 | 见下方 CLI 命令 |

## 启用 COS 访问日志

```python
# 为源桶启用访问日志记录（投递到目标桶）。SDK-only — 无 `tccli cos` 服务。
from qcloud_cos import CosConfig, CosS3Client
import os

config = CosConfig(
    Region=os.environ.get("TENCENTCLOUD_REGION"),
    SecretId=os.environ.get("TENCENTCLOUD_SECRET_ID"),
    SecretKey=os.environ.get("TENCENTCLOUD_SECRET_KEY"),
)
client = CosS3Client(config)

# 启用日志
client.put_bucket_logging(
    Bucket="{{user.source_bucket}}",
    BucketLoggingStatus={
        "LoggingEnabled": {
            "TargetBucket": "{{user.target_bucket}}",
            "TargetPrefix": "cos-access-log/",
        }
    }
)

# 验证是否已启用
resp = client.get_bucket_logging(Bucket="{{user.source_bucket}}")
print(resp.get("LoggingEnabled"))
```

## 分析流程委托

当用户提出 COS 访问日志分析需求时，**委托给 `qcloud-cls-ops`**：

| 步骤 | 操作 | 负责 Skill |
|------|------|-----------|
| 1 | 确认 COS 桶存在、启用访问日志 | `qcloud-cos-ops`（当前 skill） |
| 2 | 导入 COS 日志到 CLS | `qcloud-cls-ops` — ImportCOSAccessLogs |
| 3 | 配置 CLS 索引 | `qcloud-cls-ops` — CreateIndex |
| 4 | 执行分析（审计/性能/安全/故障排查） | `qcloud-cls-ops` — COSAccessLogAnalysis |

## 参考链接

- [CLS COS 访问日志分析分析文档](../qcloud-cls-ops/references/cos-log-analysis.md)
- [COS 访问日志字段说明](https://cloud.tencent.com/document/product/436/58956)
- [CLS 数据导入 — CreateCosRecharge](https://cloud.tencent.com/document/product/614/78156)
