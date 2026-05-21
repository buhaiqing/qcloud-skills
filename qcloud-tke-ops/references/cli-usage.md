# TKE CLI Usage Reference

## Overview

The `tccli tke` command group provides CLI access to Tencent Kubernetes Engine operations. This document maps CLI commands to TKE API methods and identifies coverage gaps.

## CLI Command Map

### Cluster Operations

| CLI Command | API Method | Description | Supports |
|-------------|------------|-------------|----------|
| `tccli tke CreateCluster` | CreateCluster | Create a managed or independent cluster | Cluster type, OS, version, VPC |
| `tccli tke DeleteCluster` | DeleteCluster | Delete a cluster | Sync/async delete mode |
| `tccli tke DescribeClusters` | DescribeClusters | Query cluster list/details | Pagination, filters |
| `tccli tke ModifyCluster` | ModifyCluster | Modify cluster attributes | Name, description, version |
| `tccli tke DescribeClusterAttribute` | DescribeClusterAttribute | Query cluster attributes | Addons, security |

### Node Pool Operations

| CLI Command | API Method | Description | Supports |
|-------------|------------|-------------|----------|
| `tccli tke CreateClusterAsGroup` | CreateClusterAsGroup | Create a node pool | Auto-scaling, OS, instance type |
| `tccli tke DeleteClusterAsGroups` | DeleteClusterAsGroups | Delete node pool(s) | Batch delete |
| `tccli tke DescribeClusterAsGroups` | DescribeClusterAsGroups | Query node pool list | Pagination, cluster filter |
| `tccli tke ModifyClusterAsGroup` | ModifyClusterAsGroup | Modify node pool config | Scale, rename |
| `tccli tke DescribeClusterNodePoolDetail` | DescribeClusterNodePoolDetail | Get node pool detail | Nodes, labels, taints |

### Node/Instance Operations

| CLI Command | API Method | Description | Supports |
|-------------|------------|-------------|----------|
| `tccli tke DescribeClusterInstances` | DescribeClusterInstances | List cluster node instances | Node status, IP, hostname |
| `tccli tke DeleteClusterInstances` | DeleteClusterInstances | Remove nodes from cluster | Batch delete |

### Addon Operations

| CLI Command | API Method | Description | Supports |
|-------------|------------|-------------|----------|
| `tccli tke InstallComponents` | InstallComponents | Install cluster addons | Addon name, version |
| `tccli tke SetAddonsRemainQuota` | SetAddonsRemainQuota | Set addon quota | Addon count limit |

### Security Operations

| CLI Command | API Method | Description | Supports |
|-------------|------------|-------------|----------|
| `tccli tke DescribeClusterSecurity` | DescribeClusterSecurity | Get kubeconfig/security | JKS, CA cert, endpoint |
| `tccli tke DescribeClusterEndpoints` | DescribeClusterEndpoints | Get API server endpoints | Internal/public endpoints |

### Quota Operations

| CLI Command | API Method | Description | Supports |
|-------------|------------|-------------|----------|
| `tccli tke DescribeUserQuota` | DescribeUserQuota | Query user quota | Cluster quota |
| `tccli tke DescribeClusterEndpointsSpecs` | DescribeClusterEndpointsSpecs | Endpoint specifications | Pricing tiers |

## Coverage Gap Analysis

CLI covers the majority of TKE API operations. Gaps or partial coverage:

| API Method (API spec) | CLI Coverage | Gap Description |
|----------------------|--------------|-----------------|
| CreateCluster | ✓ Full | All params exposed via CLI |
| DeleteCluster | ✓ Full | All params exposed via CLI |
| ModifyCluster | Partial | Some advanced params may need SDK |
| InstallComponents | ✓ Full | All params exposed via CLI |
| DescribeClusterAttribute | ✓ Full | All params exposed via CLI |
| Advanced node pool scheduling | Partial | Complex scheduling policies may require SDK |

## CLI Invocation Patterns

### Basic Usage

```bash
# List all clusters in region
tccli tke DescribeClusters --Region ap-guangzhou

# Get specific cluster detail
tccli tke DescribeClusters --Region ap-guangzhou --ClusterId "cls-xxxxxxxx"

# Extract just the cluster status
tccli tke DescribeClusters --Region ap-guangzhou --ClusterId "cls-xxxxxxxx" | jq -r '.Response.Clusters[0].ClusterStatus'
```

### JSON Output (Default)

CLI outputs JSON by default. Parse with jq:

```bash
# List clusters with name and status
tccli tke DescribeClusters --Region ap-guangzhou | jq -r '.Response.Clusters[] | "\(.ClusterName) \(.ClusterStatus)"'

# Count total clusters
tccli tke DescribeClusters --Region ap-guangzhou | jq '.Response.TotalCount'
```

### Help System

```bash
# List all TKE CLI actions
tccli tke help

# Get help for specific action
tccli tke help CreateCluster

# Get parameter help
tccli tke help CreateCluster --param ClusterType
```

### Batch Operations

```bash
# Delete multiple clusters
for CLUS_ID in "cls-111" "cls-222"; do
  echo "Deleting $CLUS_ID..."
  tccli tke DeleteCluster --ClusterId "$CLUS_ID" --Region ap-guangzhou
done
```