# TDMQ Well-Architected Assessment

## 可靠性 (Reliability)

| Check | Recommendation |
|-------|----------------|
| Multi-AZ deployment | Use Pro/cluster instances with cross-AZ replication |
| Message durability | Enable sync flush for critical topics |
| DLQ handling | Monitor DLQ depth; alert on threshold breach |
| Offset management | Document reset procedure; coordinate with consumers |

## 安全性 (Security)

| Check | Recommendation |
|-------|----------------|
| Namespace isolation | Separate namespaces per environment/team |
| Access control | Use namespace roles; least privilege |
| Credential masking | Never log `TENCENTCLOUD_SECRET_KEY` |
| Network | Use VPC private access for sensitive workloads |

## 成本 (Cost)

| Check | Recommendation |
|-------|----------------|
| Cluster spec | Right-size by throughput; avoid over-provisioning |
| Billing model | Compare pay-as-you-go vs monthly subscription |
| Retention | Set topic retention to minimum required |

## 效率 (Efficiency)

| Check | Recommendation |
|-------|----------------|
| Batch send | Use `SendBatchMessages` for high throughput |
| Consumer tuning | Match consumer count to partition/topic concurrency |
| Partition strategy | Even partition distribution avoids hot topics |
