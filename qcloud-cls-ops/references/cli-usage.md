# CLS CLI Usage

## tccli cls Commands Overview

| Category | CLI Command | API Action | Description |
|----------|-------------|------------|-------------|
| **Logset** | `tccli cls CreateLogset` | CreateLogset | 创建日志集 |
| | `tccli cls DeleteLogset` | DeleteLogset | 删除日志集 |
| | `tccli cls ModifyLogset` | ModifyLogset | 修改日志集 |
| | `tccli cls DescribeLogsets` | DescribeLogsets | 获取日志集列表 |
| **Topic** | `tccli cls CreateTopic` | CreateTopic | 创建日志主题 |
| | `tccli cls DeleteTopic` | DeleteTopic | 删除日志主题 |
| | `tccli cls ModifyTopic` | ModifyTopic | 修改日志主题 |
| | `tccli cls DescribeTopics` | DescribeTopics | 获取日志主题列表 |
| **Index** | `tccli cls CreateIndex` | CreateIndex | 创建索引规则 |
| | `tccli cls DeleteIndex` | DeleteIndex | 删除索引规则 |
| | `tccli cls ModifyIndex` | ModifyIndex | 修改索引规则 |
| | `tccli cls DescribeIndex` | DescribeIndex | 获取索引规则 |
| **Search** | `tccli cls SearchLog` | SearchLog | 检索日志 |
| | `tccli cls GetAlarmLog` | GetAlarmLog | 获取告警历史 |
| **Config** | `tccli cls CreateConfig` | CreateConfig | 创建采集配置 |
| | `tccli cls DeleteConfig` | DeleteConfig | 删除采集配置 |
| | `tccli cls ModifyConfig` | ModifyConfig | 修改采集配置 |
| | `tccli cls DescribeConfigs` | DescribeConfigs | 获取采集配置列表 |
| **MachineGroup** | `tccli cls CreateMachineGroup` | CreateMachineGroup | 创建机器组 |
| | `tccli cls DeleteMachineGroup` | DeleteMachineGroup | 删除机器组 |
| | `tccli cls DescribeMachineGroups` | DescribeMachineGroups | 获取机器组列表 |
| | `tccli cls ModifyMachineGroup` | ModifyMachineGroup | 修改机器组 |

## Logset Operations

### Create Logset

```bash
tccli cls CreateLogset \
  --Region ap-guangzhou \
  --LogsetName "my-logset" \
  --Tags '[{"Key":"env","Value":"prod"}]'
```

**Output:**
```json
{
  "Response": {
    "LogsetId": "5f3c2a1b-8d4e-4f6a-9c2b-1a3b4c5d6e7f",
    "RequestId": "abc123-def456"
  }
}
```

### List Logsets

```bash
tccli cls DescribeLogsets \
  --Region ap-guangzhou \
  --Offset 0 \
  --Limit 20
```

**Output:**
```json
{
  "Response": {
    "Logsets": [
      {
        "LogsetId": "5f3c2a1b-8d4e-4f6a-9c2b-1a3b4c5d6e7f",
        "LogsetName": "my-logset",
        "CreateTime": "2026-05-20T10:00:00+08:00",
        "TopicCount": 3
      }
    ],
    "TotalCount": 1,
    "RequestId": "xyz789"
  }
}
```

### Modify Logset

```bash
tccli cls ModifyLogset \
  --Region ap-guangzhou \
  --LogsetId "5f3c2a1b-8d4e-4f6a-9c2b-1a3b4c5d6e7f" \
  --LogsetName "production-logs"
```

### Delete Logset

```bash
tccli cls DeleteLogset \
  --Region ap-guangzhou \
  --LogsetId "5f3c2a1b-8d4e-4f6a-9c2b-1a3b4c5d6e7f"
```

**Safety Check:**
```bash
# Check if logset has topics
TOPICS=$(tccli cls DescribeTopics --LogsetId "$LOGSET_ID" | jq '.Response.Topics | length')
if [ "$TOPICS" -gt 0 ]; then
  echo "Logset contains $TOPICS topics - delete topics first"
  exit 1
fi
```

## Topic Operations

### Create Topic

```bash
tccli cls CreateTopic \
  --Region ap-guangzhou \
  --LogsetId "5f3c2a1b-8d4e-4f6a-9c2b-1a3b4c5d6e7f" \
  --TopicName "nginx-access" \
  --PartitionCount 1 \
  --Tags '[{"Key":"service","Value":"nginx"}]'
```

**Output:**
```json
{
  "Response": {
    "TopicId": "topic-12345678-abcd-efgh",
    "RequestId": "req-abc123"
  }
}
```

### List Topics

```bash
tccli cls DescribeTopics \
  --Region ap-guangzhou \
  --LogsetId "5f3c2a1b-8d4e-4f6a-9c2b-1a3b4c5d6e7f"
```

### Modify Topic

```bash
tccli cls ModifyTopic \
  --Region ap-guangzhou \
  --TopicId "topic-12345678-abcd-efgh" \
  --TopicName "nginx-access-updated" \
  --PartitionCount 2
```

### Delete Topic

```bash
tccli cls DeleteTopic \
  --Region ap-guangzhou \
  --TopicId "topic-12345678-abcd-efgh"
```

## Index Operations

### Create Full-Text Index

```bash
tccli cls CreateIndex \
  --Region ap-guangzhou \
  --TopicId "topic-12345678-abcd-efgh" \
  --Rule '{
    "FullText": {
      "CaseSensitive": false,
      "Tokenizer": "@&?|#()='\''<>/:\", \"
      "ContainZH": true
    }
  }'
```

### Create Key-Value Index

```bash
tccli cls CreateIndex \
  --Region ap-guangzhou \
  --TopicId "topic-12345678-abcd-efgh" \
  --Rule '{
    "KeyValue": {
      "CaseSensitive": false,
      "KeyValues": [
        {
          "Key": "level",
          "Value": {
            "Type": "text",
            "Tokenizer": " "
          }
        },
        {
          "Key": "status_code",
          "Value": {
            "Type": "long"
          }
        },
        {
          "Key": "timestamp",
          "Value": {
            "Type": "text",
            "Tokenizer": " "
          }
        }
      ]
    }
  }'
```

### Describe Index

```bash
tccli cls DescribeIndex \
  --Region ap-guangzhou \
  --TopicId "topic-12345678-abcd-efgh"
```

### Modify Index

```bash
tccli cls ModifyIndex \
  --Region ap-guangzhou \
  --TopicId "topic-12345678-abcd-efgh" \
  --Rule '{
    "FullText": {
      "CaseSensitive": true,
      "Tokenizer": "@&?|#()='\''<>/:\", \"
      "ContainZH": true
    },
    "KeyValue": {
      "CaseSensitive": false,
      "KeyValues": [
        {
          "Key": "level",
          "Value": {
            "Type": "text"
          }
        }
      ]
    }
  }'
```

## Search Operations

### Search Logs

```bash
tccli cls SearchLog \
  --Region ap-guangzhou \
  --TopicId "topic-12345678-abcd-efgh" \
  --From 1716192000000 \
  --To 1716278400000 \
  --Query 'level:error AND status_code:500' \
  --Limit 100
```

**Output:**
```json
{
  "Response": {
    "Results": [
      {
        "Time": 1716195600000,
        "TopicId": "topic-12345678-abcd-efgh",
        "Source": "172.16.0.1",
        "FileName": "/var/log/nginx/access.log",
        "PkgId": "pkg-abc123",
        "PkgLogId": "log-xyz789",
        "Log": "{\"level\":\"error\",\"status_code\":500,\"message\":\"Internal Server Error\"}"
      }
    ],
    "RequestId": "req-search123"
  }
}
```

### Search with Context

```bash
tccli cls SearchLog \
  --Region ap-guangzhou \
  --TopicId "topic-12345678-abcd-efgh" \
  --From 1716192000000 \
  --To 1716278400000 \
  --Query 'request_id:abc123' \
  --Context "on" \
  --Limit 20 \
  --Sort asc
```

### Histogram Query

```bash
tccli cls SearchLog \
  --Region ap-guangzhou \
  --TopicId "topic-12345678-abcd-efgh" \
  --From 1716192000000 \
  --To 1716278400000 \
  --Query '*' \
  --Interval 3600 \
  --Limit 0
```

## Collection Configuration

### Create Config (LogListener)

```bash
tccli cls CreateConfig \
  --Region ap-guangzhou \
  --Name "nginx-config" \
  --Output "topic-12345678-abcd-efgh" \
  --Path '/var/log/nginx/*.log' \
  --LogType "json_log" \
  --ExtractRule '{
    "TimeKey": "timestamp",
    "TimeFormat": "%Y-%m-%d %H:%M:%S",
    "Delimiter": "",
    "LogRegex": "",
    "Keys": ["timestamp", "level", "message"],
    "FilterKeyRegex": []
  }' \
  --ExcludePaths '[{"Type":"Path","Value":"/var/log/nginx/error.log"}]'
```

### Create Config for CSV Log

```bash
tccli cls CreateConfig \
  --Region ap-guangzhou \
  --Name "app-csv-config" \
  --Output "topic-12345678-abcd-efgh" \
  --Path '/var/log/app/*.csv' \
  --LogType "delimiter_log" \
  --ExtractRule '{
    "TimeKey": "_timestamp_",
    "TimeFormat": "%Y-%m-%d %H:%M:%S",
    "Delimiter": ",",
    "Keys": ["timestamp", "level", "module", "message"]
  }'
```

### List Configs

```bash
tccli cls DescribeConfigs \
  --Region ap-guangzhou \
  --Filters '[{"Key":"output","Value":"topic-12345678-abcd-efgh"}]'
```

## Machine Group Operations

### Create Machine Group

```bash
tccli cls CreateMachineGroup \
  --Region ap-guangzhou \
  --GroupName "web-servers" \
  --MachineGroupType '{
    "Type": "ip",
    "Values": ["172.16.0.1", "172.16.0.2", "172.16.0.3"]
  }' \
  --Tags '[{"Key":"env","Value":"production"}]'
```

**Auto-scaling Machine Group (Label-based):**
```bash
tccli cls CreateMachineGroup \
  --Region ap-guangzhou \
  --GroupName "k8s-nodes" \
  --MachineGroupType '{
    "Type": "label",
    "Values": ["app=nginx"]
  }'
```

### Apply Config to Machine Group

```bash
tccli cls ApplyConfigToMachineGroup \
  --Region ap-guangzhou \
  --ConfigId "config-abc123" \
  --GroupId "group-xyz789"
```

### List Machine Groups

```bash
tccli cls DescribeMachineGroups \
  --Region ap-guangzhou \
  --Filters '[{"Key":"groupName","Value":"web-servers"}]'
```

## jq Parsing Patterns

```bash
# Get logset ID
LOGSET_ID=$(tccli cls CreateLogset --Region ap-guangzhou --LogsetName "test" | jq -r '.Response.LogsetId')

# Get topic count
TOPIC_COUNT=$(tccli cls DescribeLogsets --Region ap-guangzhou | jq -r '.Response.Logsets[0].TopicCount')

# Get topic IDs
TOPIC_IDS=$(tccli cls DescribeTopics --Region ap-guangzhou --LogsetId "$LOGSET_ID" | jq -r '.Response.Topics[].TopicId')

# Count error logs
ERROR_COUNT=$(tccli cls SearchLog --Region ap-guangzhou --TopicId "$TOPIC_ID" --From 1716192000000 --To 1716278400000 --Query 'level:error' --Limit 1 | jq -r '.Response.Results | length')

# Get machine group IPs
IPS=$(tccli cls DescribeMachineGroups --Region ap-guangzhou | jq -r '.Response.MachineGroups[0].MachineGroupType.Values[]')
```

## CLI Coverage Analysis

| Operation | tccli | SDK Required | Notes |
|-----------|-------|--------------|-------|
| CreateLogset | ✓ | No | — |
| DeleteLogset | ✓ | No | Check empty first |
| ModifyLogset | ✓ | No | — |
| DescribeLogsets | ✓ | No | Pagination supported |
| CreateTopic | ✓ | No | — |
| DeleteTopic | ✓ | No | — |
| ModifyTopic | ✓ | No | — |
| DescribeTopics | ✓ | No | — |
| CreateIndex | ✓ | No | JSON rule required |
| DeleteIndex | ✓ | No | — |
| ModifyIndex | ✓ | No | — |
| DescribeIndex | ✓ | No | — |
| SearchLog | ✓ | No | Time in milliseconds |
| CreateConfig | ✓ | No | Complex extract rules |
| DeleteConfig | ✓ | No | — |
| ModifyConfig | ✓ | No | — |
| DescribeConfigs | ✓ | No | — |
| CreateMachineGroup | ✓ | No | IP or label based |
| DeleteMachineGroup | ✓ | No | — |
| DescribeMachineGroups | ✓ | No | — |
| ApplyConfigToMachineGroup | ✓ | No | — |
| UploadLog | — | Yes | SDK/API only |
| GetAlarmLog | ✓ | No | — |
| CreateAlarm | ✓ | No | — |
| ModifyAlarm | ✓ | No | — |
| DeleteAlarm | ✓ | No | — |
| DescribeAlarms | ✓ | No | — |

**Note:** Log upload requires SDK (Python/Go/Java) or API call with signature.

## Pagination

```bash
# Paginate through logsets
OFFSET=0
LIMIT=20
while true; do
  RESULT=$(tccli cls DescribeLogsets --Region ap-guangzhou --Offset $OFFSET --Limit $LIMIT)
  LOGSETS=$(echo "$RESULT" | jq -r '.Response.Logsets')
  COUNT=$(echo "$LOGSETS" | jq 'length')
  
  if [ "$COUNT" -eq 0 ]; then
    break
  fi
  
  echo "$LOGSETS" | jq -r '.[].LogsetName'
  OFFSET=$((OFFSET + LIMIT))
done
```

## References

- [CLS API Documentation](https://cloud.tencent.com/document/product/614/12445)
- [CLS CLI Documentation](https://cloud.tencent.com/document/product/614/42884)
- [Search Syntax](https://cloud.tencent.com/document/product/614/47044)
