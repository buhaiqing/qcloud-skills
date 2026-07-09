# TDMQ Integration

## Delegation Map

| Scenario | Delegate To |
|----------|-------------|
| Kafka topic/cluster ops | `qcloud-ckafka-ops` |
| Underlying CVM for self-built MQ | `qcloud-cvm-ops` |
| VPC/networking for private access | `qcloud-vpc-ops` |
| CAM policy for TDMQ roles | `qcloud-cam-ops` |
| Cost analysis of messaging spend | `qcloud-finops-ops` |

## Cross-Skill Handoff

When a migration from self-built RocketMQ to TDMQ is requested, coordinate with
`qcloud-migration-ops` for the cutover plan. TDMQ owns the target cluster lifecycle;
migration-ops owns the cutover orchestration.

## Monitoring

For message lag / DLQ alerts, integrate with `qcloud-monitor-ops` to push metrics to
Cloud Monitor. TDMQ emits namespace/topic-level metrics consumable via monitor APIs.
