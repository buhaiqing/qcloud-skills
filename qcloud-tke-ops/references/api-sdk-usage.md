# TKE API & SDK Usage

## API Reference

**Base URL:** `https://tke.tencentcloudapi.com`
**API Version:** 2018-05-25
**API Product:** TKE
**Documentation:** https://cloud.tencent.com/document/api/457

## Operation Map

### Cluster Management

| API Method | Description | CLI Command | Required Params |
|------------|-------------|-------------|-----------------|
| CreateCluster | Create a TKE cluster | `tccli tke CreateCluster` | ClusterType, ClusterName, VpcId, SubnetId |
| DeleteCluster | Delete a TKE cluster | `tccli tke DeleteCluster` | ClusterId |
| DescribeClusters | Query cluster list | `tccli tke DescribeClusters` | Optional: ClusterId, Offset, Limit |
| ModifyCluster | Modify cluster properties | `tccli tke ModifyCluster` | ClusterId |
| DescribeClusterAttribute | Query cluster attributes | `tccli tke DescribeClusterAttribute` | ClusterId, Attribute |

### Node Pool Management

| API Method | Description | CLI Command | Required Params |
|------------|-------------|-------------|-----------------|
| CreateClusterAsGroup | Create a node pool | `tccli tke CreateClusterAsGroup` | ClusterId, NodePoolName, InstanceType |
| DeleteClusterAsGroups | Delete node pool(s) | `tccli tke DeleteClusterAsGroups` | ClusterId, NodePoolIds |
| DescribeClusterAsGroups | Query node pool list | `tccli tke DescribeClusterAsGroups` | ClusterId |
| ModifyClusterAsGroup | Modify node pool config | `tccli tke ModifyClusterAsGroup` | ClusterId, NodePoolId |
| DescribeClusterNodePoolDetail | Query node pool detail | `tccli tke DescribeClusterNodePoolDetail` | ClusterId, NodePoolId |

### Cluster Instances (Nodes)

| API Method | Description | CLI Command | Required Params |
|------------|-------------|-------------|-----------------|
| DescribeClusterInstances | Query cluster node list | `tccli tke DescribeClusterInstances` | ClusterId |
| DeleteClusterInstances | Delete cluster nodes | `tccli tke DeleteClusterInstances` | ClusterId, InstanceIds |

### Addon/Component Management

| API Method | Description | CLI Command | Required Params |
|------------|-------------|-------------|-----------------|
| InstallComponents | Install cluster addons | `tccli tke InstallComponents` | ClusterId, Components |
| SetAddonsRemainQuota | Set addon remain quota | `tccli tke SetAddonsRemainQuota` | ClusterId |
| DescribeClusterAttribute | Query addon status | `tccli tke DescribeClusterAttribute` | ClusterId, Attribute=ClusterLevel/Addons |

### Cluster Security

| API Method | Description | CLI Command | Required Params |
|------------|-------------|-------------|-----------------|
| DescribeClusterSecurity | Get kubeconfig/security info | `tccli tke DescribeClusterSecurity` | ClusterId |
| DescribeClusterEndpoints | Get cluster API endpoints | `tccli tke DescribeClusterEndpoints` | ClusterId |

### Quota and Pricing

| API Method | Description | CLI Command | Required Params |
|------------|-------------|-------------|-----------------|
| DescribeUserQuota | Query user quotas | `tccli tke DescribeUserQuota` | None |
| DescribeClusterEndpointsSpecs | Query endpoint specs | `tccli tke DescribeClusterEndpointsSpecs` | None |

## SDK Usage Examples

### Initialization

```python
from tencentcloud.common import credential
from tencentcloud.tke import tke_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = tke_client.TkeClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))
```

### CreateCluster Request Schema

```python
req = models.CreateClusterRequest()
req.ClusterType = "MANAGED_TKE"       # Required: MANAGED_TKE or INDEPENDENT
req.ClusterName = "my-cluster"       # Required: cluster name
req.ClusterOs = "tlinux3.1x86_64"    # Required: OS for master nodes
req.ClusterVersion = "1.28.3"        # Optional: K8s version
req.ClusterOsType = "CUSTOM"         # Optional: OS type
req.VpcId = "vpc-xxxxx"              # Required: VPC ID
req.SubnetId = "subnet-xxxxx"        # Required: Subnet ID
req.ContainerRuntime = "docker"      # Optional: container runtime
req.NodeNameMode = "mycluster-%i"    # Optional: node naming pattern
req.ClusterLevel = "L5"              # Optional: cluster tier
```

### DescribeClusters Response Schema

```json
{
  "Response": {
    "Clusters": [
      {
        "ClusterId": "cls-xxxxxxxx",
        "ClusterName": "my-cluster",
        "ClusterStatus": "Running",
        "ClusterType": "MANAGED_TKE",
        "ClusterVersion": "1.28.3",
        "TotalNodeNum": 3,
        "CreatedTime": "2026-01-15T10:00:00Z",
        "VpcId": "vpc-xxxxx",
        "SubnetIds": ["subnet-xxxxx"]
      }
    ],
    "TotalCount": 1,
    "RequestId": "abc-123-def"
  }
}
```

## Pagination Pattern

For Describe APIs that support pagination:

```bash
# Manual pagination loop
OFFSET=0
LIMIT=100
while true; do
  DATA=$(tccli tke DescribeClusters --Offset $OFFSET --Limit $LIMIT)
  ITEMS=$(echo "$DATA" | jq '.Response.Clusters | length')
  echo "$DATA" | jq '.Response.Clusters[]'
  [ "$ITEMS" -lt "$LIMIT" ] && break
  OFFSET=$((OFFSET + LIMIT))
done
```

```python
def describe_all_clusters(client):
    clusters = []
    offset = 0
    limit = 100
    while True:
        req = models.DescribeClustersRequest()
        req.Offset, req.Limit = offset, limit
        resp = client.DescribeClusters(req)
        clusters.extend(resp.Clusters)
        if len(resp.Clusters) < limit:
            break
        offset += limit
    return clusters
```

## Async Operation Pattern

Cluster creation and deletion are async. Always poll until terminal state:

```bash
poll_cluster_status() {
  CLUSTER_ID=$1
  TARGET_STATUS=$2
  MAX_WAIT=${3:-600}
  INTERVAL=${4:-10}

  for i in $(seq 1 $((MAX_WAIT / INTERVAL))); do
    STATUS=$(tccli tke DescribeClusters --ClusterId "$CLUSTER_ID" | jq -r '.Response.Clusters[0].ClusterStatus')
    if [ "$STATUS" = "$TARGET_STATUS" ]; then
      echo "Cluster reached $TARGET_STATUS"
      return 0
    fi
    sleep $INTERVAL
  done
  echo "Timeout waiting for $TARGET_STATUS (current: $STATUS)"
  return 1
}
```