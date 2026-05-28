# CKafka Core Concepts

Architecture, instance types, Kafka versions, limits, and resource relationships for Tencent Cloud CKafka (Message Queue).

---

## 1. Architecture Overview

Tencent Cloud CKafka is a fully managed Apache Kafka service offering high-throughput, low-latency message streaming with automatic scaling, monitoring, and security features.

### CKafka Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Region (ap-guangzhou)                             │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                    VPC (Virtual Private Cloud)                   ││
│  │                                                                  ││
│  │  ┌──────────────────┐      ┌──────────────────┐                  ││
│  │  │   Zone A         │      │   Zone B         │                  ││
│  │  │  ┌────────────┐  │      │  ┌────────────┐  │                  ││
│  │  │  │ Broker 1   │  │      │  │ Broker 2   │  │                  ││
│  │  │  │ (Leader)   │◄─┼──────┼─►│ (Follower) │  │                  ││
│  │  │  └────────────┘  │ sync │  └────────────┘  │                  ││
│  │  │  ┌────────────┐  │      │  ┌────────────┐  │                  ││
│  │  │  │ Broker 3   │  │      │  │ Broker 4   │  │                  ││
│  │  │  │ (ISR)      │  │      │  │ (ISR)      │  │                  ││
│  │  │  └────────────┘  │      │  └────────────┘  │                  ││
│  │  └──────────────────┘      └──────────────────┘                  ││
│  │                                                                  ││
│  │  ┌───────────────────────────────────────────────────────────┐   ││
│  │  │     Topic: order-events                                     │   ││
│  │  │     ├── Partition 0 (Leader: B1, Replicas: [B1, B2, B3])   │   ││
│  │  │     ├── Partition 1 (Leader: B2, Replicas: [B2, B3, B1])   │   ││
│  │  │     ├── Partition 2 (Leader: B3, Replicas: [B3, B1, B2])   │   ││
│  │  │     └── ...                                                │   ││
│  │  └───────────────────────────────────────────────────────────┘   ││
│  │                                                                  ││
│  │  ┌──────────────────┐  ┌─────────────────────────────────────┐  ││
│  │  │  SASL Auth       │  │  Cloud Monitor (Metrics/Alarms)     │  ││
│  │  │  - SCRAM-SHA-512 │  │  - Message throughput               │  ││
│  │  │  - ACL Rules     │  │  - Consumer lag                     │  ││
│  │  └──────────────────┘  └─────────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Description |
|-----------|-------------|
| **Broker** | Kafka server handling message storage and retrieval |
| **Topic** | Message category/feed (log abstraction) |
| **Partition** | Ordered, immutable message sequence (topic shard) |
| **Replica** | Copy of partition for fault tolerance |
| **Consumer Group** | Logical consumer unit with load balancing |
| **Offset** | Unique message identifier within partition |
| **ZooKeeper** | Cluster coordination and metadata management |

---

## 2. Core Concepts

### 2.1 Instance

A CKafka instance is a complete Kafka cluster with configurable brokers, topics, and partitions.

| Attribute | Description |
|-----------|-------------|
| **InstanceId** | Unique identifier (e.g., `ckafka-xxx`) |
| **InstanceName** | Human-readable name |
| **Version** | Kafka version (2.4.2, 2.8.1, 3.x) |
| **Type** | Standard or Professional |
| **Zone** | Physical availability zone |
| **Specs** | Bandwidth, disk size, partition limit |

### 2.2 Topic

Logical message channel with configurable partitions and retention.

| Property | Description | Default | Range |
|----------|-------------|---------|-------|
| **PartitionNum** | Number of partitions | 6 | 1-300 |
| **ReplicaNum** | Replication factor | 3 | 2-3 |
| **RetentionMs** | Message retention time | 1440min | 60000ms - unlimited |
| **CleanupPolicy** | Retention strategy | delete | delete/compact |
| **MinInsyncReplicas** | Min replicas for commit | 1 | 1-2 |

### 2.3 Partition

The unit of parallelism in Kafka.

```
Topic: order-events
├── Partition 0: messages [0, 1, 2, ..., n]
├── Partition 1: messages [0, 1, 2, ..., m]
├── Partition 2: messages [0, 1, 2, ..., k]
└── ...

Offset: Unique within partition (monotonically increasing)
```

**Key behaviors:**
- Each partition can have one leader broker
- Writes go to leader, replicas sync from leader
- Consumers read from assigned partitions
- More partitions = higher throughput (with trade-offs)

### 2.4 Consumer Group

Logical grouping of consumers with automatic partition assignment.

```
Consumer Group: order-processor
├── Consumer-1: assigned [Partition 0, Partition 1]
├── Consumer-2: assigned [Partition 2, Partition 3]
└── Consumer-3: assigned [Partition 4, Partition 5]

If Consumer-2 fails:
└── Rebalance: Partitions 2,3 reassigned to Consumer-1 or 3
```

**Group behaviors:**
- One partition consumed by one consumer at a time
- Rebalance on consumer join/leave/failure
- Offset committed per partition

### 2.5 Offset

Position tracking mechanism for consumers.

| Offset Type | Description |
|-------------|-------------|
| **Earliest** | Start from oldest message |
| **Latest** | Start from newest message |
| **Committed** | Last processed position (stored in __consumer_offsets) |
| **Current** | Next message to be fetched |

**Offset commit strategies:**
- Auto commit: Periodic automatic commits
- Manual commit: Application-controlled commits
- At-least-once: Commit after processing
- At-most-once: Commit before processing
- Exactly-once: Transactional commits

---

## 3. Kafka Versions

### 3.1 Version Comparison

| Feature | 2.4.2 | 2.8.1 | 3.x |
|---------|-------|-------|-----|
| **ZooKeeper Mode** | Required | Required | Optional (KRaft) |
| **KRaft Mode** | No | Preview | Supported |
| **Producer Idempotency** | Yes | Yes | Yes |
| **Exactly-Once Semantics** | Yes | Yes | Yes |
| **Incremental Alter Configs** | Yes | Yes | Yes |
| **Static Membership** | Yes | Yes | Yes |
| **MirrorMaker 2.0** | Yes | Yes | Yes |
| **Topic IDs** | No | Yes | Yes |
| **Log dirs reload** | No | No | Yes |
| **API Key Support** | No | No | Yes |

### 3.2 Version Selection Guide

| Use Case | Recommended Version |
|----------|---------------------|
| Legacy compatibility | 2.4.2 |
| Production stability | 2.8.1 |
| New features / KRaft | 3.x |
| High throughput | 2.8.1 or 3.x |

> **Note:** CKafka currently supports 2.4.2 and 2.8.1. Check documentation for 3.x availability.

---

## 4. Instance Types

### 4.1 Standard vs Professional

| Feature | Standard | Professional |
|---------|----------|--------------|
| **Target** | Dev/test, small workloads | Production, enterprise |
| **Max Bandwidth** | 400 Mbps | 800+ Mbps |
| **Max Partitions** | 150 | 300+ |
| **Max Topics** | 50 | 100+ |
| **SASL/SCRAM** | Yes | Yes |
| **ACL** | Basic | Advanced |
| **Cross-AZ** | Single AZ | Multi-AZ support |
| **Price** | Lower | Higher |

### 4.2 Billing Models

| Model | Description | Use Case |
|-------|-------------|----------|
| **Prepaid (Monthly/Yearly)** | Pay upfront, lower unit cost | Stable workloads |
| **Postpaid (Hourly)** | Pay per hour, flexible | Variable/dev workloads |

### 4.3 Specification Dimensions

```bash
# Query available specifications
tccli ckafka DescribeInstanceAttributes --InstanceId "ckafka-xxxxxx"
```

| Spec | Min | Max |
|------|-----|-----|
| **Bandwidth** | 40 Mbps | 3600 Mbps |
| **Disk Size** | 200 GB | 16000 GB |
| **Max Topics** | 25 | 500 |
| **Max Partitions** | 75 | 1500 |

---

## 5. Message Retention Strategies

### 5.1 Retention Policies

| Policy | Description | Use Case |
|--------|-------------|----------|
| **Time-based** | Retain messages for X hours | Event logs, audit trails |
| **Size-based** | Retain until disk limit | High volume streams |
| **Compaction** | Keep latest per key | State changes, configuration |

### 5.2 Configuration

```bash
# Time-based retention (default: 1440 min = 24 hours)
tccli ckafka ModifyTopicAttributes \
  --InstanceId "ckafka-xxxxxx" \
  --TopicName "logs-topic" \
  --RetentionMs 604800000  # 7 days

# Cleanup policy
tccli ckafka CreateTopic \
  --InstanceId "ckafka-xxxxxx" \
  --TopicName "config-topic" \
  --PartitionNum 6 \
  --ReplicaNum 3 \
  --CleanUpPolicy "compact"
```

### 5.3 Retention Best Practices

| Scenario | Retention | Rationale |
|----------|-----------|-----------|
| Application logs | 3-7 days | Debug, short-term analysis |
| Audit logs | 30-90 days | Compliance, forensics |
| Event sourcing | Forever (compaction) | Rebuild state |
| Metrics | 1-3 days | Real-time monitoring |
| Clickstream | 7-30 days | Analytics, ML training |

---

## 6. Billing and Quotas

### 6.1 Billing Components

| Component | Billing Unit |
|-----------|--------------|
| **Instance** | Per instance/hour or month |
| **Disk Storage** | Per GB/month |
| **Network Traffic** | Per GB (egress) |
| **API Calls** | Per million requests |

### 6.2 Quotas and Limits

| Limit | Standard | Professional |
|-------|----------|--------------|
| **Instances per account** | 10 | 50 |
| **Topics per instance** | 50 | 100+ |
| **Partitions per topic** | 50 | 100 |
| **Partitions per instance** | 150 | 300+ |
| **Message size** | 12 MB | 12 MB |
| **Connections per broker** | 2000 | 5000 |
| **Retention period** | 30 days | 90 days |

### 6.3 Check Quotas

```bash
# List instances to check count
tccli ckafka DescribeInstances --Region ap-guangzhou | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'Instance count: {d[\"Response\"][\"TotalCount\"]}')"
```

---

## 7. Instance States

| Status | Code | Meaning |
|--------|------|---------|
| Creating | 0 | Instance being provisioned |
| Running | 1 | Normal operation |
| Isolating | 2 | Instance being isolated |
| Isolated | 3 | Instance isolated (payment overdue) |
| Upgrading | 4 | Instance upgrading |
| Restarting | 5 | Instance restarting |
| Deleting | 6 | Instance being deleted |

---

## 8. Security Features

### 8.1 Authentication

| Method | Description |
|--------|-------------|
| **SASL/SCRAM-SHA-256** | Username/password auth |
| **SASL/SCRAM-SHA-512** | Enhanced password auth |
| **API Key** | Programmatic access (v3.x+) |

### 8.2 Authorization (ACL)

| Resource Type | Operations |
|---------------|------------|
| **Topic** | Read, Write, Describe |
| **Group** | Read, Describe |
| **Cluster** | Create, Alter |

### 8.3 Encryption

| Layer | Support |
|-------|---------|
| **In-transit** | SSL/TLS 1.2+ |
| **At-rest** | Disk encryption |

---

## 9. Resource Relationships

```
Account
 └── CKafka Instance (InstanceId: ckafka-xxx)
      ├── Topics
      │    ├── Partitions (with Replicas)
      │    ├── Producers
      │    └── Consumers
      ├── Consumer Groups
      │    ├── Group Members
      │    └── Partition Assignments
      ├── Users (SASL/SCRAM)
      │    ├── Username/Password
      │    └── ACL Bindings
      ├── ACL Rules
      │    ├── Resource (Topic/Group/Cluster)
      │    ├── Principal (User)
      │    └── Operation Permissions
      └── VPC Network
           ├── VPC
           ├── Subnet
           └── Security Group
```

### 9.1 Cross-Skill Dependencies

| Resource | CKafka Relationship | Skill |
|----------|--------------------|-------|
| VPC | CKafka instance must be in VPC | `qcloud-vpc-ops` |
| Subnet | CKafka must have subnet assignment | `qcloud-vpc-ops` |
| Security Group | Network access control | `qcloud-vpc-ops` |
| Cloud Monitor | Metrics and alarms | `qcloud-monitor-ops` |
| CVM | Application servers consuming/producing | `qcloud-cvm-ops` |

### 9.2 Cross-Skill Delegation

- **Network connectivity issues?** Check VPC/subnet via `qcloud-vpc-ops`
- **Consumer lag alerts?** Check CVM resources via `qcloud-cvm-ops`
- **Metrics and dashboards?** Delegate to `qcloud-monitor-ops`
- **SASL user management?** Use CKafka ACL and user APIs
