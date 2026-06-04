# TCR (Tencent Container Registry) Integration

> [仅在用户提到使用 TCR 或容器镜像仓库时加载]

## Prerequisites

- TKE cluster is Running
- TCR instance exists (use TCR console or `tccli tcr` for management)
- User has TCR credentials (username + password)

## Associate TCR with Cluster

```bash
tccli tke EnableClusterAudit \
  --ClusterId "{{output.cluster_id}}" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

## Configure Image Pull Secret

```bash
# Fetch kubeconfig
tccli tke DescribeClusterSecurity \
  --ClusterId "{{output.cluster_id}}" \
  --Region {{env.TENCENTCLOUD_REGION}} > /tmp/kubeconfig.yaml

# Set image pull secret
kubectl --kubeconfig=/tmp/kubeconfig.yaml create secret docker-registry tcr-secret \
  --docker-server={{user.tcr_registry}} \
  --docker-username={{user.tcr_username}} \
  --docker-password={{user.tcr_password}} \
  --docker-email={{user.email}}
```

**Note:** For full TCR operations, use `qcloud-tcr-ops` skill (not yet implemented — use TCR console or SDK directly).