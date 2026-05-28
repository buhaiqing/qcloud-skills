# CKafka CLI Usage Guide

Detailed `tccli ckafka` command reference for Tencent Cloud CKafka (Message Queue) operations.

---

## 1. CLI Overview

### Installation

```bash
pip install tccli
```

### Verify

```bash
tccli version
tccli ckafka help
```

### Credential Setup

```bash
export TENCENTCLOUD_SECRET_ID="AKIDxxxx"
export TENCENTCLOUD_SECRET_KEY="xxxxx"
export TENCENTCLOUD_REGION="ap-guangzhou"
```

---

## 2. Common Patterns

### JSON Parameter Convention

`tccli ckafka` uses JSON string parameters for complex arguments:

```bash
# InstanceId list as JSON array
tccli ckafka DescribeInstances --InstanceIdList '["ckafka-xxx"]' --Region ap-guangzhou

# Filter parameters as JSON object
tccli ckafka DescribeTopic --InstanceId "ckafka-xxx" --SearchWord "test-topic"

# Batch operations with JSON arrays
tccli ckafka DeleteTopic \
  --InstanceId "ckafka-xxx" \
  --TopicNameList '["topic1", "topic2"]'

# ACL rule configuration
tccli ckafka CreateAclRule \
  --InstanceId "ckafka-xxx" \
  --ResourceType 2 \
  --ResourceName "test-topic" \
  --Principal '{
      "PrincipalType": "PrincipalTypeUser",
      "PrincipalName": "user1",
      "Host": "*"
    }' \
  --OperationList '[{"OperationType": "Read", "PermissionType": "Allow"}]'

# Partition reassignment
tccli ckafka ModifyPartitionReassign \
  --InstanceId "ckafka-xxx" \
  --TopicName "test-topic" \
  --ReassignList '[{"Partition": 0, "Replicas": [1001, 1002]}]'
```

---

## 3. Instance Operations

### 3.1 DescribeInstances

```bash
# List all instances
tccli ckafka DescribeInstances --Region ap-guangzhou --Offset 0 --Limit 20

# Filter by instance ID
tccli ckafka DescribeInstances --InstanceIdList '["ckafka-xxxxxx"]' --Region ap-guangzhou

# Filter by instance name
tccli ckafka DescribeInstances --SearchWord "production" --Region ap-guangzhou

# Filter by status
tccli ckafka DescribeInstances --Status '[1]' --Region ap-guangzhou

# Response
# {
#   "Response": {
#     "InstanceList": [
#       {
#         "InstanceId": "ckafka-xxxxxx",
#         "InstanceName": "production-kafka",
#         "Status": 1,
#         "Version": "2.8.1",
#         "InstanceType": "profession",
#         "ZoneId": 100003,
#         "VpcId": "vpc-xxxxxx",
#         "SubnetId": "subnet-xxxxxx",
#         "MsgRetentionTime": 1440,
#         "MaxTopicNumber": 100,
#         "MaxPartitionNumber": 300,
#         "CreateTime": 1716192000
#       }
#     ],
#     "TotalCount": 3,
#     "RequestId": "..."
#   }
# }
```

### 3.2 CreateInstancePost

```bash
# Minimal create (prepaid)
tccli ckafka CreateInstancePost \
  --Region ap-guangzhou \
  --InstanceName "test-kafka" \
  --ZoneId 100003 \
  --VpcId "vpc-xxxxxx" \
  --SubnetId "subnet-xxxxxx" \
  --InstanceVersion "2.8.1" \
  --InstanceType "profession" \
  --MsgRetentionTime 1440 \
  --RenewFlag 1 \
  --TimeSpan 1 \
  --TimeUnit "m"

# With specifications
tccli ckafka CreateInstancePost \
  --Region ap-guangzhou \
  --InstanceName "production-kafka" \
  --ZoneId 100003 \
  --VpcId "vpc-xxxxxx" \
  --SubnetId "subnet-xxxxxx" \
  --InstanceVersion "2.8.1" \
  --InstanceType "profession" \
  --MsgRetentionTime 1440 \
  --MaxTopicNumber 100 \
  --MaxPartitionNumber 300 \
  --Bandwidth 400 \
  --DiskSize 2000 \
  --RenewFlag 1 \
  --TimeSpan 12 \
  --TimeUnit "m"

# Response
# { "Response": { "Result": { "DealId": "20260521xxxx", "InstanceId": "ckafka-xxxxxx" }, "RequestId": "..." } }
```

### 3.3 CreateInstancePre

```bash
# Hourly billing (postpaid)
tccli ckafka CreateInstancePre \
  --Region ap-guangzhou \
  --InstanceName "dev-kafka" \
  --ZoneId 100003 \
  --VpcId "vpc-xxxxxx" \
  --SubnetId "subnet-xxxxxx" \
  --InstanceVersion "2.8.1" \
  --InstanceType "profession" \
  --MsgRetentionTime 1440 \
  --MaxTopicNumber 50 \
  --MaxPartitionNumber 150
```

### 3.4 ModifyInstancePre

```bash
# Upgrade instance specifications
tccli ckafka ModifyInstancePre \
  --InstanceId "ckafka-xxxxxx" \
  --DiskSize 3000 \
  --Bandwidth 800

# Response
# { "Response": { "Result": { "DealId": "20260521xxxx" }, "RequestId": "..." } }
```

### 3.5 RenewCkafkaInstance

```bash
# Renew instance
tccli ckafka RenewCkafkaInstance \
  --InstanceId "ckafka-xxxxxx" \
  --TimeSpan 6 \
  --TimeUnit "m"

# Response
# { "Response": { "Result": { "DealId": "20260521xxxx" }, "RequestId": "..." } }
```

### 3.6 DeleteInstancePre

```bash
# Delete prepaid instance
tccli ckafka DeleteInstancePre \
  --InstanceId "ckafka-xxxxxx"

# Response
# { "Response": { "Result": { "ReturnCode": "0", "ReturnMessage": "success" }, "RequestId": "..." } }
```

### 3.7 RestartInstance

```bash
# Restart instance
tccli ckafka RestartInstance --InstanceId "ckafka-xxxxxx"

# Response
# { "Response": { "Result": true, "RequestId": "..." } }
```

### 3.8 ModifyInstanceAttributes

```bash
# Rename instance
tccli ckafka ModifyInstanceAttributes \
  --InstanceId "ckafka-xxxxxx" \
  --InstanceName "new-kafka-name"

# Modify message retention
tccli ckafka ModifyInstanceAttributes \
  --InstanceId "ckafka-xxxxxx" \
  --MsgRetentionTime 2880

# Enable public access
tccli ckafka ModifyInstanceAttributes \
  --InstanceId "ckafka-xxxxxx" \
  --EnablePublicAccess 1

# Response
# { "Response": { "Result": { "ReturnCode": "0" }, "RequestId": "..." } }
```

---

## 4. Topic Operations

### 4.1 CreateTopic

```bash
# Create topic
tccli ckafka CreateTopic \
  --InstanceId "ckafka-xxxxxx" \
  --TopicName "test-topic" \
  --PartitionNum 6 \
  --ReplicaNum 3 \
  --EnableWhiteList 0

# With whitelist
tccli ckafka CreateTopic \
  --InstanceId "ckafka-xxxxxx" \
  --TopicName "secure-topic" \
  --PartitionNum 6 \
  --ReplicaNum 3 \
  --EnableWhiteList 1 \
  --IpWhiteList '["10.0.0.0/8", "192.168.0.0/16"]'

# With retention and cleanup policy
tccli ckafka CreateTopic \
  --InstanceId "ckafka-xxxxxx" \
  --TopicName "log-topic" \
  --PartitionNum 12 \
  --ReplicaNum 3 \
  --RetentionMs 604800000 \
  --CleanUpPolicy "delete"

# Response
# { "Response": { "Result": { "ReturnCode": "0", "ReturnMessage": "success" }, "RequestId": "..." } }
```

### 4.2 DescribeTopic

```bash
# List all topics
tccli ckafka DescribeTopic \
  --InstanceId "ckafka-xxxxxx" \
  --Offset 0 \
  --Limit 50

# Search topic by name
tccli ckafka DescribeTopic \
  --InstanceId "ckafka-xxxxxx" \
  --SearchWord "test" \
  --Offset 0 \
  --Limit 20

# Response
# {
#   "Response": {
#     "Result": {
#       "TopicList": [
#         {
#           "TopicId": "topic-xxxxxx",
#           "TopicName": "test-topic",
#           "PartitionNum": 6,
#           "ReplicaNum": 3,
#           "Note": "Test topic",
#           "CreateTime": "2026-05-21 10:00:00",
#           "EnableWhiteList": 0,
#           "RetentionMsConfig": 604800000
#         }
#       ],
#       "TotalCount": 5
#     },
#     "RequestId": "..."
#   }
# }
```

### 4.3 DescribeTopicAttributes

```bash
# Get detailed topic info
tccli ckafka DescribeTopicAttributes \
  --InstanceId "ckafka-xxxxxx" \
  --TopicName "test-topic"

# Response
# {
#   "Response": {
#     "Result": {
#       "TopicId": "topic-xxxxxx",
#       "TopicName": "test-topic",
#       "PartitionNum": 6,
#       "ReplicaNum": 3,
#       "Note": "Test topic",
#       "CreateTime": 1716192000,
#       "EnableWhiteList": 0,
#       "IpWhiteList": [],
#       "Config": {
#         "RetentionMs": 604800000,
#         "MinInsyncReplicas": 1,
#         "CleanupPolicy": "delete"
#       },
#       "Partitions": [
#         { "Partition": 0, "Leader": 1001, "Replicas": [1001, 1002, 1003], "Isr": [1001, 1002, 1003] }
#       ]
#     },
#     "RequestId": "..."
#   }
# }
```

### 4.4 ModifyTopicAttributes

```bash
# Update topic configuration
tccli ckafka ModifyTopicAttributes \
  --InstanceId "ckafka-xxxxxx" \
  --TopicName "test-topic" \
  --Note "Updated description"

# Change retention time
tccli ckafka ModifyTopicAttributes \
  --InstanceId "ckafka-xxxxxx" \
  --TopicName "log-topic" \
  --RetentionMs 86400000

# Update whitelist
tccli ckafka ModifyTopicAttributes \
  --InstanceId "ckafka-xxxxxx" \
  --TopicName "secure-topic" \
  --EnableWhiteList 1 \
  --IpWhiteList '["10.0.1.0/24", "172.16.0.0/16"]'

# Response
# { "Response": { "Result": { "ReturnCode": "0", "ReturnMessage": "success" }, "RequestId": "..." } }
```

### 4.5 DeleteTopic

```bash
# Delete single topic
tccli ckafka DeleteTopic \
  --InstanceId "ckafka-xxxxxx" \
  --TopicName "test-topic"

# Delete multiple topics
tccli ckafka DeleteTopic \
  --InstanceId "ckafka-xxxxxx" \
  --TopicNameList '["topic1", "topic2", "topic3"]'

# Response
# { "Response": { "Result": { "ReturnCode": "0", "ReturnMessage": "success" }, "RequestId": "..." } }
```

### 4.6 ModifyPartitionNum

```bash
# Increase partition count (cannot decrease)
tccli ckafka ModifyPartitionNum \
  --InstanceId "ckafka-xxxxxx" \
  --TopicName "test-topic" \
  --PartitionNum 12

# Response
# { "Response": { "Result": { "ReturnCode": "0", "ReturnMessage": "success" }, "RequestId": "..." } }
```

---

## 5. Consumer Group Operations

### 5.1 DescribeGroup

```bash
# List consumer groups
tccli ckafka DescribeGroup \
  --InstanceId "ckafka-xxxxxx" \
  --GroupName "consumer-group-1" \
  --Offset 0 \
  --Limit 50

# Search consumer groups
tccli ckafka DescribeGroup \
  --InstanceId "ckafka-xxxxxx" \
  --SearchWord "consumer" \
  --Offset 0 \
  --Limit 20

# Response
# {
#   "Response": {
#     "Result": {
#       "GroupList": [
#         {
#           "Group": "consumer-group-1",
#           "Protocol": "consumer",
#           "ProtocolType": "consumer",
#           "MemberCount": 3,
#           "TopicList": ["test-topic", "log-topic"]
#         }
#       ],
#       "TotalCount": 5
#     },
#     "RequestId": "..."
#   }
# }
```

### 5.2 DescribeGroupOffsets

```bash
# Get consumer group offsets
tccli ckafka DescribeGroupOffsets \
  --InstanceId "ckafka-xxxxxx" \
  --Group "consumer-group-1"

# Response
# {
#   "Response": {
#     "Result": {
#       "TopicList": [
#         {
#           "Topic": "test-topic",
#           "Partitions": [
#             { "Partition": 0, "Offset": 12345, "Metadata": "" },
#             { "Partition": 1, "Offset": 67890, "Metadata": "" }
#           ]
#         }
#       ]
#     },
#     "RequestId": "..."
#   }
# }
```

### 5.3 DescribeGroupInfo

```bash
# Get detailed consumer group info
tccli ckafka DescribeGroupInfo \
  --InstanceId "ckafka-xxxxxx" \
  --GroupName "consumer-group-1"

# Response
# {
#   "Response": {
#     "Result": {
#       "Group": "consumer-group-1",
#       "Protocol": "consumer",
#       "ProtocolType": "consumer",
#       "Members": [
#         {
#           "MemberId": "consumer-1-xxx",
#           "ClientId": "consumer-1",
#           "ClientHost": "/10.0.0.1",
#           "MemberAssignment": { "test-topic": [0, 1, 2] }
#         }
#       ],
#       "PartitionAssignment": [
#         { "Topic": "test-topic", "Partition": 0, "Consumer": "consumer-1" }
#       ]
#     },
#     "RequestId": "..."
#   }
# }
```

### 5.4 DeleteGroup

```bash
# Delete consumer group
tccli ckafka DeleteGroup \
  --InstanceId "ckafka-xxxxxx" \
  --GroupName "consumer-group-1"

# Response
# { "Response": { "Result": { "ReturnCode": "0", "ReturnMessage": "success" }, "RequestId": "..." } }
```

---

## 6. ACL Operations

### 6.1 CreateAclRule

```bash
# Create ACL rule for topic
tccli ckafka CreateAclRule \
  --InstanceId "ckafka-xxxxxx" \
  --ResourceType 2 \
  --ResourceName "test-topic" \
  --Principal '{
      "PrincipalType": "PrincipalTypeUser",
      "PrincipalName": "user1",
      "Host": "*"
    }' \
  --OperationList '[{"OperationType": "Read", "PermissionType": "Allow"}]'

# Create ACL rule for group
tccli ckafka CreateAclRule \
  --InstanceId "ckafka-xxxxxx" \
  --ResourceType 3 \
  --ResourceName "consumer-group-1" \
  --Principal '{
      "PrincipalType": "PrincipalTypeUser",
      "PrincipalName": "user1",
      "Host": "10.0.%"
    }' \
  --OperationList '[
      {"OperationType": "Read", "PermissionType": "Allow"},
      {"OperationType": "Write", "PermissionType": "Allow"}
    ]'

# Resource Types: 2=Topic, 3=Group, 4=Cluster

# Response
# { "Response": { "Result": 1, "RequestId": "..." } }
```

### 6.2 DescribeAclRule

```bash
# List ACL rules
tccli ckafka DescribeAclRule \
  --InstanceId "ckafka-xxxxxx" \
  --ResourceType 2 \
  --ResourceName "test-topic" \
  --Offset 0 \
  --Limit 50

# Response
# {
#   "Response": {
#     "Result": {
#       "AclRuleList": [
#         {
#           "RuleName": "acl-xxxxxx",
#           "InstanceId": "ckafka-xxxxxx",
#           "ResourceType": 2,
#           "ResourceName": "test-topic",
#           "Principal": { "PrincipalType": "PrincipalTypeUser", "PrincipalName": "user1", "Host": "*" },
#           "Operation": { "OperationType": "Read", "PermissionType": "Allow" },
#           "CreateTime": 1716192000
#         }
#       ],
#       "TotalCount": 3
#     },
#     "RequestId": "..."
#   }
# }
```

### 6.3 DeleteAclRule

```bash
# Delete ACL rule
tccli ckafka DeleteAclRule \
  --InstanceId "ckafka-xxxxxx" \
  --RuleName "acl-xxxxxx"

# Response
# { "Response": { "Result": true, "RequestId": "..." } }
```

### 6.4 ModifyAclRule

```bash
# Update ACL rule
tccli ckafka ModifyAclRule \
  --InstanceId "ckafka-xxxxxx" \
  --RuleName "acl-xxxxxx" \
  --OperationList '[{"OperationType": "Read", "PermissionType": "Deny"}]'

# Response
# { "Response": { "Result": true, "RequestId": "..." } }
```

---

## 7. User Operations

### 7.1 CreateUser

```bash
# Create SASL/SCRAM user
tccli ckafka CreateUser \
  --InstanceId "ckafka-xxxxxx" \
  --Name "app-user" \
  --Password "SecurePassword123!"

# Response
# { "Response": { "Result": { "ReturnCode": "0", "ReturnMessage": "success" }, "RequestId": "..." } }
```

### 7.2 DescribeUser

```bash
# List users
tccli ckafka DescribeUser \
  --InstanceId "ckafka-xxxxxx" \
  --Offset 0 \
  --Limit 50

# Response
# {
#   "Response": {
#     "Result": {
#       "Users": [
#         {
#           "Name": "app-user",
#           "CreateTime": 1716192000,
#           "UpdateTime": 1716192000
#         }
#       ],
#       "TotalCount": 2
#     },
#     "RequestId": "..."
#   }
# }
```

### 7.3 ModifyUser

```bash
# Change user password
tccli ckafka ModifyUser \
  --InstanceId "ckafka-xxxxxx" \
  --Name "app-user" \
  --Password "NewPassword456!"

# Response
# { "Response": { "Result": { "ReturnCode": "0", "ReturnMessage": "success" }, "RequestId": "..." } }
```

### 7.4 DeleteUser

```bash
# Delete user
tccli ckafka DeleteUser \
  --InstanceId "ckafka-xxxxxx" \
  --Name "app-user"

# Response
# { "Response": { "Result": { "ReturnCode": "0", "ReturnMessage": "success" }, "RequestId": "..." } }
```

---

## 8. Advanced Operations

### 8.1 ModifyPartitionReassign

```bash
# Reassign partitions to different brokers
tccli ckafka ModifyPartitionReassign \
  --InstanceId "ckafka-xxxxxx" \
  --TopicName "test-topic" \
  --ReassignList '[
      {"Partition": 0, "Replicas": [1001, 1002]},
      {"Partition": 1, "Replicas": [1002, 1003]},
      {"Partition": 2, "Replicas": [1003, 1001]}
    ]'

# Response
# { "Response": { "Result": { "ReturnCode": "0", "ReturnMessage": "success" }, "RequestId": "..." } }
```

### 8.2 DescribeTaskStatus

```bash
# Check async task status
tccli ckafka DescribeTaskStatus \
  --InstanceId "ckafka-xxxxxx" \
  --FlowId 12345

# Response
# {
#   "Response": {
#     "Result": {
#       "FlowId": 12345,
#       "Status": 2,
#       "StatusDesc": "Success"
#     },
#     "RequestId": "..."
#   }
# }
# Status: 0=Init, 1=Running, 2=Success, 3=Failed
```

### 8.3 SendMessage (Test)

```bash
# Send test message
tccli ckafka SendMessage \
  --InstanceId "ckafka-xxxxxx" \
  --Topic "test-topic" \
  --Partition 0 \
  --Message "Test message content"

# Response
# { "Response": { "Result": { "Partition": 0, "Offset": 12345 }, "RequestId": "..." } }
```

---

## 9. Monitoring Operations

```bash
# Get CKafka metrics via monitor API
tccli monitor GetMonitorData \
  --Namespace QCE/CKAFKA \
  --MetricName InstanceMessagesIn \
  --Dimensions '[{"Name":"InstanceId","Value":"ckafka-xxxxxx"}]' \
  --StartTime 2026-05-20T00:00:00+08:00 \
  --EndTime 2026-05-21T00:00:00+08:00 \
  --Period 300

# Available metrics:
# - InstanceMessagesIn: Messages received per second
# - InstanceMessagesOut: Messages sent per second
# - InstanceBytesIn: Bytes received per second
# - InstanceBytesOut: Bytes sent per second
# - InstanceCpuUsage: CPU usage percentage
# - InstanceMemoryUsage: Memory usage percentage
# - InstanceDiskUsage: Disk usage percentage
```

---

## 10. CLI Coverage Gap Table

Most CKafka operations are supported by `tccli ckafka`. The following operations may require SDK fallback:

| Operation | CLI Support | SDK Fallback Needed? |
|-----------|-------------|---------------------|
| DescribeInstances | ✅ Full | No |
| CreateInstancePost | ✅ Full | No |
| CreateInstancePre | ✅ Full | No |
| ModifyInstancePre | ✅ Full | No |
| DeleteInstancePre | ✅ Full | No |
| RestartInstance | ✅ Full | No |
| ModifyInstanceAttributes | ✅ Full | No |
| RenewCkafkaInstance | ✅ Full | No |
| CreateTopic | ✅ Full | No |
| DescribeTopic | ✅ Full | No |
| DescribeTopicAttributes | ✅ Full | No |
| ModifyTopicAttributes | ✅ Full | No |
| DeleteTopic | ✅ Full | No |
| ModifyPartitionNum | ✅ Full | No |
| DescribeGroup | ✅ Full | No |
| DescribeGroupOffsets | ✅ Full | No |
| DescribeGroupInfo | ✅ Full | No |
| DeleteGroup | ✅ Full | No |
| CreateAclRule | ✅ Full | No |
| DescribeAclRule | ✅ Full | No |
| ModifyAclRule | ✅ Full | No |
| DeleteAclRule | ✅ Full | No |
| CreateUser | ✅ Full | No |
| DescribeUser | ✅ Full | No |
| ModifyUser | ✅ Full | No |
| DeleteUser | ✅ Full | No |
| ModifyPartitionReassign | ✅ Full | No |
| DescribeTaskStatus | ✅ Full | No |
| SendMessage | ✅ Full | No |
