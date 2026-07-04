# CLS Integration

> CLS integration with other Tencent Cloud services.

## COS Integration

Ship logs from COS buckets to CLS via log ingestion:
1. Create a logset and topic in CLS
2. Create a machine group or use API to push logs
3. Configure log shipping from COS bucket to CLS topic

## SCF Integration

SCF functions can push logs to CLS using the CLS SDK:

```python
import cls
from tencentcloud.cls.v20201016 importClsClient

client = cls.Client(...)
client.put_log([...])
```

## CVM Integration

Install CLS agent (LogListener) on CVM instances to collect system and application logs.

## See also
- [Core Concepts](core-concepts.md)
- [CLI Usage](cli-usage.md)
- [Query Language](query-language.md)
