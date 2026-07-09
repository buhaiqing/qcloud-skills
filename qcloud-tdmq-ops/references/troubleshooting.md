# TDMQ Troubleshooting

## Common Issues

### Cluster Creation Failed

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| `InvalidParameter.ClusterNameExists` | Name collision | Use a unique cluster name |
| `ResourceInsufficient` | Quota exceeded | Request quota increase in console |
| Region not supported | Wrong region | Use a TDMQ-supported region |

### Topic Issues

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| `ResourceNotFound.Namespace` | Namespace missing | Create namespace first |
| `InvalidParameter.TopicExists` | Duplicate topic | Reuse existing or rename |
| Message not consumed | Consumer group offset stuck | Reset offset via `ResetRocketMQConsumerOffSet` |

### Message Consumption

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| Messages in DLQ | Consumer exception > retry limit | Inspect DLQ; fix consumer; reprocess |
| Offset drift | Concurrent reset | Coordinate reset with all consumers |
| Lag growing | Consumer slow | Scale consumers; increase concurrency |

### CMQ Rewind

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| Rewind no effect | Timestamp before retention | Use timestamp within message retention window |
| Partial replay | Some messages expired | Accept partial; verify with `DescribeMsg` |

## Debug Steps

```bash
# Verify cluster status
tccli tdmq DescribeRocketMQCluster --ClusterId "rocketmq-xxx"

# List topics in namespace
tccli tdmq DescribeRocketMQTopics --ClusterId "rocketmq-xxx" --Namespace "ns-prod"

# Check consumer connection
tccli tdmq DescribeRocketMQConsumerConnections --ClusterId "rocketmq-xxx" \
  --Namespace "ns-prod" --Group "order-consumer"

# Check DLQ messages
tccli tdmq DescribeRocketMQTopicMsgs --ClusterId "rocketmq-xxx" \
  --Namespace "ns-prod" --Topic "orders" --MsgType DLQ
```
