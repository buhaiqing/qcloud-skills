# ES CLI Usage Guide

Detailed `tccli es` command reference for Elasticsearch Service operations.

---

## 1. CLI Overview

### Installation

```bash
pip install tccli
```

### Verify

```bash
tccli version
tccli es help
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

`tccli es` uses JSON string parameters for complex arguments:

```bash
# InstanceId as JSON array
tccli es DescribeInstances --InstanceIds '["es-xxxxxx"]'

# HealthStatus filter
tccli es DescribeInstances --HealthStatus "[0]"

# Multiple values
tccli es RestartNodes --NodeNames '["node1","node2"]'
```

### Output Validation

All tccli commands return JSON. Use `jq` or `python3 -c` to parse:

```bash
# Get instance count
tccli es DescribeInstances | jq '.Response.TotalCount'

# Get specific field
tccli es DescribeInstances | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['Response']['InstanceList'][0]['InstanceId'])"
```

---

## 3. Instance Operations

### 3.1 CreateInstance

```bash
# Minimal create
tccli es CreateInstance \
  --Region ap-guangzhou \
  --Zone ap-guangzhou-3 \
  --NodeType "ES.S1.MEDIUM4" \
  --NodeNum 3 \
  --DiskSize 200 \
  --DiskType "CLOUD_SSD" \
  --EsVersion "7.14.2" \
  --VpcId "vpc-xxxxxx" \
  --SubnetId "subnet-xxxxxx" \
  --Password "YourPassword123" \
  --InstanceName "my-es-cluster"

# With dedicated master nodes
tccli es CreateInstance \
  --Region ap-guangzhou \
  --Zone ap-guangzhou-3 \
  --NodeType "ES.S1.LARGE8" \
  --NodeNum 5 \
  --DiskSize 500 \
  --DiskType "CLOUD_SSD" \
  --EsVersion "7.14.2" \
  --VpcId "vpc-xxxxxx" \
  --SubnetId "subnet-xxxxxx" \
  --Password "YourPassword123" \
  --InstanceName "production-cluster" \
  --EnableDedicatedMaster true \
  --MasterNodeNum 3 \
  --MasterNodeType "ES.S1.MEDIUM4" \
  --MasterNodeDiskSize 50

# With Kibana public access disabled
tccli es CreateInstance \
  --Region ap-guangzhou \
  --Zone ap-guangzhou-3 \
  --NodeType "ES.S1.MEDIUM4" \
  --NodeNum 3 \
  --DiskSize 200 \
  --DiskType "CLOUD_SSD" \
  --EsVersion "7.14.2" \
  --VpcId "vpc-xxxxxx" \
  --SubnetId "subnet-xxxxxx" \
  --Password "YourPassword123" \
  --BasicSecurityType 1

# Response
# { "Response": { "InstanceId": "es-xxxxxx", "DealName": "20260521xxxx", "RequestId": "..." } }
```

### 3.2 DescribeInstances

```bash
# List all clusters
tccli es DescribeInstances --Region ap-guangzhou --Offset 0 --Limit 20

# Filter by instance IDs
tccli es DescribeInstances --InstanceIds '["es-xxxxxx"]'

# Filter by health status (green)
tccli es DescribeInstances --HealthStatus "[0]"

# Filter by cluster status (normal)
tccli es DescribeInstances --Status '["1"]'

# Response
# {
#   "Response": {
#     "TotalCount": 5,
#     "InstanceList": [
#       {
#         "InstanceId": "es-xxxxxx",
#         "InstanceName": "production-cluster",
#         "HealthStatus": 0,
#         "Status": 1,
#         "EsVersion": "7.14.2",
#         "NodeType": "ES.S1.LARGE8",
#         "NodeNum": 5,
#         "DiskSize": 500,
#         "EsDomain": "es-xxxxxx.ap-guangzhou.es.tencentcloud.com",
#         "KibanaUrl": "https://es-xxxxxx.ap-guangzhou.es.tencentcloud.com:5601",
#         "Zone": "ap-guangzhou-3",
#         "CreateTime": "2026-05-21T10:00:00+08:00"
#       }
#     ],
#     "RequestId": "..."
#   }
# }
```

### 3.3 UpdateInstance

```bash
# Scale node type and count
tccli es UpdateInstance \
  --InstanceId "es-xxxxxx" \
  --NodeType "ES.S1.LARGE8" \
  --NodeNum 5 \
  --DiskSize 500

# Scale with COS backup before operation
tccli es UpdateInstance \
  --InstanceId "es-xxxxxx" \
  --NodeType "ES.S1.2XLARGE16" \
  --NodeNum 10 \
  --CosBackup true

# Response
# { "Response": { "RequestId": "..." } }
```

### 3.4 DeleteInstance

```bash
tccli es DeleteInstance --InstanceId "es-xxxxxx"

# Response
# { "Response": { "RequestId": "..." } }
```

### 3.5 RestartInstance

```bash
# Restart entire cluster
tccli es RestartInstance --InstanceId "es-xxxxxx"

# Restart specific nodes
tccli es RestartNodes --InstanceId "es-xxxxxx" --NodeNames '["es-xxxxxx_node1","es-xxxxxx_node2"]'

# Restart Kibana
tccli es RestartKibana --InstanceId "es-xxxxxx"
```

### 3.6 UpgradeInstance

```bash
# Upgrade ES version (e.g., 7.10 → 7.14)
tccli es UpgradeInstance \
  --InstanceId "es-xxxxxx" \
  --EsVersion "7.14.2" \
  --CheckOnly false

# Check version upgrade feasibility only
tccli es UpgradeInstance \
  --InstanceId "es-xxxxxx" \
  --EsVersion "7.14.2" \
  --CheckOnly true

# Upgrade license (node type/count/disk)
tccli es UpgradeLicense \
  --InstanceId "es-xxxxxx" \
  --NodeType "ES.S1.LARGE8" \
  --NodeNum 5 \
  --DiskSize 500
```

---

## 4. Index Operations

### 4.1 CreateIndex

```bash
# Create a simple index
tccli es CreateIndex \
  --InstanceId "es-xxxxxx" \
  --IndexName "my-index" \
  --IndexType "normal"

# Create index with mapping and settings
tccli es CreateIndex \
  --InstanceId "es-xxxxxx" \
  --IndexName "my-index" \
  --IndexType "normal" \
  --IndexMetaJson '{"settings":{"number_of_shards":5,"number_of_replicas":1},"mappings":{"properties":{"title":{"type":"text"},"price":{"type":"float"}}}}'

# Response
# { "Response": { "IndexName": "my-index", "RequestId": "..." } }
```

### 4.2 DescribeIndexList

```bash
tccli es DescribeIndexList --InstanceId "es-xxxxxx" --Offset 0 --Limit 20

# Response
# {
#   "Response": {
#     "IndexMetaFields": [
#       {
#         "IndexName": "my-index",
#         "IndexType": "normal",
#         "IndexCreateTime": "2026-05-21 10:00:00",
#         "IndexSize": 1024,
#         "IndexDocNum": 10000
#       }
#     ],
#     "TotalCount": 3,
#     "RequestId": "..."
#   }
# }
```

### 4.3 DescribeIndexMeta

```bash
tccli es DescribeIndexMeta --InstanceId "es-xxxxxx" --IndexName "my-index"
```

### 4.4 UpdateIndex

```bash
tccli es UpdateIndex --InstanceId "es-xxxxxx" --IndexName "my-index"
```

### 4.5 DeleteIndex

```bash
tccli es DeleteIndex --InstanceId "es-xxxxxx" --IndexName "my-index"
# Response: { "Response": { "RequestId": "..." } }
```

---

## 5. Snapshot Operations

### 5.1 CreateClusterSnapshot

```bash
tccli es CreateClusterSnapshot \
  --InstanceId "es-xxxxxx" \
  --SnapshotName "manual-backup-20260521"

# Response
# { "Response": { "SnapshotId": "snap-xxxxxx", "RequestId": "..." } }
```

### 5.2 DescribeClusterSnapshot

```bash
tccli es DescribeClusterSnapshot --InstanceId "es-xxxxxx"

# Response
# {
#   "Response": {
#     "ClusterSnapshotSet": [
#       {
#         "SnapshotId": "snap-xxxxxx",
#         "SnapshotName": "manual-backup-20260521",
#         "Status": 1,
#         "SnapshotCreateTime": "2026-05-21 10:00:00"
#       }
#     ],
#     "RequestId": "..."
#   }
# }
```

### 5.3 DeleteClusterSnapshot

```bash
tccli es DeleteClusterSnapshot --InstanceId "es-xxxxxx" --SnapshotId "snap-xxxxxx"
```

### 5.4 RestoreClusterSnapshot

```bash
tccli es RestoreClusterSnapshot \
  --InstanceId "es-xxxxxx" \
  --SnapshotId "snap-xxxxxx"

# Response
# { "Response": { "RequestId": "..." } }
```

---

## 6. Plugin and Dictionary Operations

### 6.1 UpdatePlugins

```bash
# Install plugins
tccli es UpdatePlugins \
  --InstanceId "es-xxxxxx" \
  --InstallPluginList '["analysis-ik","analysis-pinyin"]'

# Remove plugins
tccli es UpdatePlugins \
  --InstanceId "es-xxxxxx" \
  --RemovePluginList '["analysis-ik"]'

# Install and remove simultaneously
tccli es UpdatePlugins \
  --InstanceId "es-xxxxxx" \
  --InstallPluginList '["analysis-ik"]' \
  --RemovePluginList '["old-plugin"]'
```

### 6.2 UpdateDictionaries

```bash
# Update IK main dictionaries (COS file URLs)
tccli es UpdateDictionaries \
  --InstanceId "es-xxxxxx" \
  --IkMainDicts '["https://cos-bucket.cos.ap-guangzhou.myqcloud.com/dict/main.dic"]'

# Update IK stopwords
tccli es UpdateDictionaries \
  --InstanceId "es-xxxxxx" \
  --IkStopwords '["https://cos-bucket.cos.ap-guangzhou.myqcloud.com/dict/stopword.dic"]'

# Update Jieba dictionaries
tccli es UpdateDictionaries \
  --InstanceId "es-xxxxxx" \
  --JiebaDicts '["https://cos-bucket.cos.ap-guangzhou.myqcloud.com/dict/jieba.dic"]'
```

---

## 7. Diagnostics

### 7.1 DiagnoseInstance

```bash
# Trigger diagnostics
tccli es DiagnoseInstance --InstanceId "es-xxxxxx"
# Response: { "Response": { "RequestId": "..." } }

# Check diagnosis result
tccli es DescribeDiagnose --InstanceId "es-xxxxxx"
```

---

## 8. Logs and Operations

### 8.1 DescribeInstanceLogs

```bash
# Get cluster logs
tccli es DescribeInstanceLogs --InstanceId "es-xxxxxx" --LogType 1

# Log types: 1=ES logs, 2=Search slow logs, 3=Indexing slow logs
tccli es DescribeInstanceLogs --InstanceId "es-xxxxxx" --LogType 2 --Offset 0 --Limit 10
```

### 8.2 DescribeInstanceOperations

```bash
# Get recent cluster operations
tccli es DescribeInstanceOperations \
  --InstanceId "es-xxxxxx" \
  --Offset 0 \
  --Limit 20

# Response
# {
#   "Response": {
#     "Operations": [
#       {
#         "Id": 12345,
#         "StartTime": "2026-05-21 10:00:00",
#         "Type": "CreateInstance",
#         "Status": 2,
#         "Result": "Success"
#       }
#     ],
#     "TotalCount": 10,
#     "RequestId": "..."
#   }
# }
```

---

## 9. Views

```bash
# Get dashboard/project views
tccli es DescribeViews --InstanceId "es-xxxxxx"
```

---

## 10. CLI Coverage Gap Table

Most ES operations are supported by `tccli es`. The following operations may require SDK fallback:

| Operation | CLI Support | SDK Fallback Needed? | Reason |
|-----------|-------------|---------------------|--------|
| CreateInstance | ✅ Full | No | — |
| DescribeInstances | ✅ Full | No | — |
| UpdateInstance | ✅ Full | No | — |
| DeleteInstance | ✅ Full | No | — |
| UpgradeInstance | ✅ Full | No | — |
| UpgradeLicense | ✅ Full | No | — |
| RestartInstance | ✅ Full | No | — |
| RestartNodes | ✅ Full | No | — |
| RestartKibana | ✅ Full | No | — |
| CreateIndex | ✅ Full | No | — |
| DescribeIndexList | ✅ Full | No | — |
| DescribeIndexMeta | ✅ Full | No | — |
| UpdateIndex | ✅ Full | No | — |
| DeleteIndex | ✅ Full | No | — |
| CreateClusterSnapshot | ✅ Full | No | — |
| DescribeClusterSnapshot | ✅ Full | No | — |
| DeleteClusterSnapshot | ✅ Full | No | — |
| RestoreClusterSnapshot | ✅ Full | No | — |
| UpdatePlugins | ✅ Full | No | — |
| UpdateDictionaries | ✅ Full | No | — |
| DiagnoseInstance | ✅ Full | No | — |
| DescribeDiagnose | ✅ Full | No | — |
| DescribeInstanceLogs | ✅ Full | No | — |
| DescribeInstanceOperations | ✅ Full | No | — |
| DescribeViews | ✅ Full | No | — |
