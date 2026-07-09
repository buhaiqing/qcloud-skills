# TDMQ Core Concepts

## Supported Protocols

| Protocol | Use Case | Key Resources |
|----------|----------|---------------|
| **RocketMQ** | Ordered messaging, transaction messages, delay messages | Cluster, Namespace, Topic, Group |
| **Pulsar** | Multi-tenancy, unified messaging | Environment, Tenant, Topic, Subscription |
| **RabbitMQ** | AMQP protocol compatibility | VipInstance, VirtualHost, Exchange, Queue, Binding, User |
| **CMQ** | Simple queue service | Queue, Topic, Subscription |
| **Pulsar Pro** | Enterprise Pulsar | ProInstance |

## RocketMQ Resource Hierarchy

```
Cluster
  └── Namespace (logical isolation unit)
        └── Topic (message category)
        └── Group (consumer group)
```

## Message Lifecycle

1. Producer sends message to Topic
2. Broker persists (sync/async flush)
3. Consumer (Group) pulls/subscribes
4. Offset tracked per Group per Topic
5. Dead-letter queue captures failed consumption after retry limit

## Dead-Letter Queue (DLQ)

Messages that fail consumption N times are routed to DLQ. Inspect via
`DescribeRocketMQTopicMsgs` with `MsgType=DLQ`.

## Offset & Rewind

- Consumer offset = position of next message to consume
- `ResetRocketMQConsumerOffSet` repositions by timestamp
- `RewindCmqQueue` replays CMQ messages from a timestamp
