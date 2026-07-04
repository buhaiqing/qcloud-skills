# CKafka Topic API

> CKafka topic operations.

## API Reference

| API | Description | CLI Example |
|-----|-------------|-------------|
| DescribeTopics | Query topic list | `tccli ckafka DescribeTopics` |
| CreateTopic | Create topic | `tccli ckafka CreateTopic` |
| DeleteTopic | Delete topic | `tccli ckafka DeleteTopic` |
| ModifyTopicAttributes | Modify topic attributes | `tccli ckafka ModifyTopicAttributes` |
| CreatePartition | Add partitions to topic | `tccli ckafka CreatePartition` |

## Topic Creation Example

```bash
tccli ckafka CreateTopic --InstanceId ckafka-xxx --TopicName my-topic --PartitionNum 6 --ReplicaNum 3
```

## Partition Strategy

- More partitions = higher throughput (consumer parallelism)
- Replicas provide fault tolerance (use 3 replicas for production)
- Retention period configurable per topic

## See also
- [Core Concepts](core-concepts.md)
- [API Instance](api-instance.md)
