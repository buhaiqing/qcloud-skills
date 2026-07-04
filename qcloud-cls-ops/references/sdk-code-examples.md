# CLS SDK Code Examples

> Extracted from SKILL.md for token efficiency. Each example is operation-specific; see [sdk-templates.md](sdk-templates.md) for common init/poll/error boilerplate.

## CreateLogset

```python
req = models.CreateLogsetRequest()
req.LogsetName = os.environ.get("LOGSET_NAME", "default-logset")
req.ClientToken = str(int(time.time() * 1000000))
resp = client.CreateLogset(req)
result = json.loads(resp.to_json_string())
print(json.dumps(result, indent=2))
print(f"\nLogsetId: {result['Response']['LogsetId']}")
```

## CreateTopic

```python
req = models.CreateTopicRequest()
req.LogsetId = os.environ.get("LOGSET_ID")
req.TopicName = os.environ.get("TOPIC_NAME", "default-topic")
req.PartitionCount = int(os.environ.get("PARTITION_COUNT", "1"))
req.AutoSplit = True
req.MaxSplitPartitions = 50
resp = client.CreateTopic(req)
result = json.loads(resp.to_json_string())
print(json.dumps(result, indent=2))
print(f"\nTopicId: {result['Response']['TopicId']}")
```

## CreateIndex

```python
req = models.CreateIndexRequest()
req.TopicId = os.environ.get("TOPIC_ID")
rule = {
    "FullText": {"CaseSensitive": False, "Tokenizer": "@&()='%$"},
    "KeyValue": {
        "CaseSensitive": False,
        "KeyValues": [
            {"Key": "level", "Value": {"Type": "text", "Tokenizer": " "}},
            {"Key": "timestamp", "Value": {"Type": "long"}},
            {"Key": "message", "Value": {"Type": "text", "Tokenizer": "@&()='%$"}}
        ]
    }
}
req.Rule = json.dumps(rule)
req.Status = True
resp = client.CreateIndex(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## SearchLog

```python
req = models.SearchLogRequest()
req.TopicId = os.environ.get("TOPIC_ID")
req.From = int(time.time()) - 3600
req.To = int(time.time())
req.Query = os.environ.get("SEARCH_QUERY", "*")
req.Limit = int(os.environ.get("LIMIT", "100"))
resp = client.SearchLog(req)
result = json.loads(resp.to_json_string())
print(f"Total: {result['Response'].get('Count', 0)} logs")
for log in result['Response'].get('Results', []):
    print(f"  [{log.get('Timestamp')}] {log.get('Content', '')[:200]}")
```

## CreateMachineGroup

```python
req = models.CreateMachineGroupRequest()
req.GroupName = os.environ.get("GROUP_NAME", "default-group")
machine_group_type = {
    "Type": "ip",
    "Values": os.environ.get("CVM_IPS", "10.0.1.10").split(",")
}
req.MachineGroupType = json.dumps(machine_group_type)
resp = client.CreateMachineGroup(req)
result = json.loads(resp.to_json_string())
print(json.dumps(result, indent=2))
print(f"\nGroupId: {result['Response'].get('GroupId', 'N/A')}")
```

## CreateConfig

```python
req = models.CreateConfigRequest()
req.Name = os.environ.get("CONFIG_NAME", "default-config")
req.TopicId = os.environ.get("TOPIC_ID")
req.Output = json.dumps({"TopicId": os.environ.get("TOPIC_ID")})
input_config = {
    "Content": {
        "Type": "container_stdout",
        "ContainerStdout": {
            "Namespace": "default",
            "IncludeLabels": {"app": "myapp"}
        }
    }
}
req.Input = json.dumps(input_config)
req.MachineGroupIds = [os.environ.get("MACHINE_GROUP_ID", "")]
resp = client.CreateConfig(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

## CreateCosRecharge

```python
req = models.CreateCosRechargeRequest()
req.TopicId = os.environ.get("TOPIC_ID")
req.Bucket = os.environ.get("COS_BUCKET")
req.BucketRegion = os.environ.get("COS_REGION", os.environ.get("TENCENTCLOUD_REGION"))
req.LogType = os.environ.get("LOG_TYPE", "minimalist_log")
req.Prefix = os.environ.get("COS_PREFIX", "")
req.TaskName = os.environ.get("TASK_NAME", "cos-log-import")
req.Enable = 1
resp = client.CreateCosRecharge(req)
result = json.loads(resp.to_json_string())
recharge_id = result.get('Response', {}).get('TaskId') or result.get('Response', {}).get('RechargeId')
print(f"\n✅ COS import task created: {recharge_id}")
```