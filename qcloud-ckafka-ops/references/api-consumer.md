# CKafka Consumer Group API

> CKafka consumer group operations.

## API Reference

| API | Description | CLI Example |
|-----|-------------|-------------|
| DescribeConsumerGroups | Query consumer group list | `tccli ckafka DescribeConsumerGroups` |
| ModifyConsumerGroupOffsets | Modify consumer offsets | `tccli ckafka ModifyConsumerGroupOffsets` |
| DeleteConsumerGroup | Delete consumer group | `tccli ckafka DeleteConsumerGroup` |

## Consumer Group Operations

### List Consumer Groups
```bash
tccli ckafka DescribeConsumerGroups --InstanceId ckafka-xxx
```

### Reset Consumer Offsets
```bash
tccli ckafka ModifyConsumerGroupOffsets --InstanceId ckafka-xxx --GroupName my-group --TopicName my-topic --PartitionOffsets '[{"Partition":0,"Offset":100}]'
```

## Monitoring Consumer Lag

Consumer lag indicates how far behind consumers are from producers. Monitor via:
- Cloud Monitor: `CkafkaConsumerLag` metric
- High lag = consumers cannot keep up with message rate

## See also
- [Core Concepts](core-concepts.md)
- [API Topic](api-topic.md)
