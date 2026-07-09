# TDMQ CLI Usage

Verified `tccli tdmq` commands (API version 2020-02-17).

## Cluster

```bash
# List RocketMQ clusters
tccli tdmq DescribeRocketMQClusters --Region "{{env.TENCENTCLOUD_REGION}}"

# Create cluster
tccli tdmq CreateRocketMQCluster --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ClusterName "my-cluster" --Remark "prod"

# Delete cluster
tccli tdmq DeleteRocketMQCluster --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ClusterId "rocketmq-xxx"
```

## Namespace / Topic / Group

```bash
tccli tdmq CreateRocketMQNamespace --ClusterId "rocketmq-xxx" --NamespaceName "ns-prod"
tccli tdmq CreateRocketMQTopic --ClusterId "rocketmq-xxx" --Namespace "ns-prod" --Topic "orders"
tccli tdmq CreateRocketMQGroup --ClusterId "rocketmq-xxx" --Namespace "ns-prod" --Group "order-consumer"
tccli tdmq DeleteRocketMQTopic --ClusterId "rocketmq-xxx" --Namespace "ns-prod" --Topic "orders"
```

## Messages

```bash
tccli tdmq SendRocketMQMessage --ClusterId "rocketmq-xxx" --Namespace "ns-prod" \
  --Topic "orders" --Body "hello"
tccli tdmq ReceiveMessage --ClusterId "rocketmq-xxx" --Namespace "ns-prod" \
  --Topic "orders" --Group "order-consumer"
tccli tdmq ResetRocketMQConsumerOffSet --ClusterId "rocketmq-xxx" --Namespace "ns-prod" \
  --Topic "orders" --Group "order-consumer" --ResetTimestamp "2026-07-09T10:00:00+08:00"
```

## CMQ

```bash
tccli tdmq RewindCmqQueue --QueueName "my-queue" --StartConsumeTime "2026-07-09T10:00:00+08:00"
```

> All commands use `--Region` from `{{env.TENCENTCLOUD_REGION}}`. Output is JSON by default.
