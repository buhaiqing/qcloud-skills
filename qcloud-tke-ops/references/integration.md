# TKE Integration Guide

## SDK Setup

### Installation

```bash
# Full TKE SDK
pip install tencentcloud-sdk-python-tke

# Or install full SDK
pip install tencentcloud-sdk-python
```

### Python SDK Usage

```python
from tencentcloud.common import credential
from tencentcloud.tke import tke_client, models
import os

# Initialize
cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = tke_client.TkeClient(
    cred,
    os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou")
)

# Example: List clusters
req = models.DescribeClustersRequest()
req.Offset = 0
req.Limit = 100
resp = client.DescribeClusters(req)
for cluster in resp.Clusters:
    print(f"Cluster: {cluster.ClusterName} [{cluster.ClusterId}] - {cluster.ClusterStatus}")
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TENCENTCLOUD_SECRET_ID` | API Secret ID | Yes |
| `TENCENTCLOUD_SECRET_KEY` | API Secret Key | Yes |
| `TENCENTCLOUD_REGION` | Default region code | Yes |
| `TENCENTCLOUD_TOKEN` | Session token (temporary credentials) | Optional |

### CLI Configuration

```bash
# Install
pip install tccli

# Configure
tccli configure
# Enter: SecretId, SecretKey, Region, output format (json)

# Verify
tccli tke DescribeClusters --Region ap-guangzhou --Offset 0 --Limit 1
```

## Cross-Skill Delegation Matrix

| TKE Needs | From Skill | What to Delegate |
|-----------|------------|------------------|
| VPC/Subnet creation | `qcloud-vpc-ops` | Create VPC, subnet, security group before CreateCluster |
| CLB for Service LoadBalancer | `qcloud-clb-ops` | Configure CLB listener, health check, backend |
| CVM worker node management | `qcloud-cvm-ops` | SSH access, disk management, OS-level debugging |
| Container image storage (COS) | `qcloud-cos-ops` | COS bucket for legacy image registry |
| Container registry (TCR) | `qcloud-tcr-ops` | Modern registry, image pull credentials |
| Metrics and alerting | `qcloud-monitor-ops` | Monitor data, alert rules, dashboards |
| CAM permissions | `qcloud-cam-ops` | IAM policies for TKE operations |

## Delegation Workflow Example

```
User: "Create a TKE cluster in a new VPC"

1. → qcloud-vpc-ops: Create VPC (cidr: 10.0.0.0/16)
2. → qcloud-vpc-ops: Create subnet (cidr: 10.0.1.0/24) in zone
3. → qcloud-vpc-ops: Create security group (allow 22, 443, 6443)
4. → qcloud-tke-ops: CreateCluster with VPC/Subnet/SG
5. → qcloud-tke-ops: Poll until cluster Running
6. → qcloud-tke-ops: CreateClusterAsGroup (node pool)
7. → qcloud-tke-ops: InstallComponents (metrics-server, coredns)
```

## CI/CD Integration

### TKE in CI/CD Pipeline

```yaml
# Example CI/CD steps for TKE deployment
steps:
  - name: Update kubeconfig
    run: tccli tke DescribeClusterSecurity --ClusterId $CLUSTER_ID > kubeconfig.json

  - name: Deploy application
    run: |
      kubectl --kubeconfig kubeconfig apply -f deployment.yaml
      kubectl --kubeconfig kubeconfig rollout status deployment/app
```

### Infrastructure as Code (Terraform)

```hcl
resource "tencentcloud_tke_cluster" "main" {
  cluster_name       = "my-tke-cluster"
  cluster_os         = "tlinux3.1x86_64"
  cluster_type       = "MANAGED_TKE"
  cluster_version    = "1.28.3"
  vpc_id             = tencentcloud_vpc.main.id
  subnet_id          = tencentcloud_subnet.main.id
  cluster_max_pod_num = 256
  cluster_level      = "L5"
}

resource "tencentcloud_tke_cluster_as_group" "np1" {
  cluster_id     = tencentcloud_tke_cluster.main.id
  node_pool_name = "default-pool"
  instance_type  = "SA5.MEDIUM8"
  vpc_id         = tencentcloud_vpc.main.id
  subnet_id      = tencentcloud_subnet.main.id
  max_size       = 10
  min_size       = 1
  desired_size   = 3
}
```

## kubectl Integration

```bash
# Get kubeconfig from TKE
tccli tke DescribeClusterSecurity --ClusterId "cls-xxxxx" \
  | jq '.Response | {
      "apiVersion": "v1",
      "kind": "Config",
      "clusters": [{
        "name": "TKE",
        "cluster": { "server": (.AccessInfo.EndPointPublic) }
      }],
      "users": [{
        "name": "TKE",
        "user": { "token": (.AccessInfo.AccessToken) }
      }],
      "contexts": [{ "context": { "cluster": "TKE", "user": "TKE" }, "name": "tke" }],
      "current-context": "tke"
    }' > ~/.kube/config

# Verify
kubectl get nodes
```

## Automation Patterns

### Recurring Node Pool Inspection

```bash
#!/bin/bash
# Daily node pool health check script
for CLUSTER in $(tccli tke DescribeClusters --Region ap-guangzhou | jq -r '.Response.Clusters[].ClusterId'); do
  echo "=== Cluster: $CLUSTER ==="
  tccli tke DescribeClusterAsGroups --ClusterId "$CLUSTER" | jq '.Response.NodePoolSet[] | {
    node_pool: .NodePoolId,
    name: .Name,
    status: .Status,
    nodes: .TotalNodeCount,
    desired: .DesiredNodeCount
  }'
done
```

### Automated Cluster Backup

```bash
#!/bin/bash
# Export cluster YAML before maintenance
cluster_id="$1"
kubectl get all --all-namespaces -o yaml > "backup-${cluster_id}-$(date +%Y%m%d).yaml"
kubectl get pv,pvc,ingress,configmap,secret --all-namespaces -o yaml \
  >> "backup-${cluster_id}-$(date +%Y%m%d).yaml"
```