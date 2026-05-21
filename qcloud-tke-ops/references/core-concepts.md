# TKE Core Concepts

## Architecture Overview

Tencent Kubernetes Engine (TKE) provides managed Kubernetes clusters with two deployment modes:

### Cluster Types

| Type | Description | Management Scope |
|------|-------------|------------------|
| **MANAGED_TKE** (托管集群) | Tencent Cloud manages the control plane (API server, etcd, scheduler, controller-manager) | User manages node pools and workloads only |
| **INDEPENDENT** (独立集群) | User provisions and manages the full control plane on CVM instances | Full user control, higher operational overhead |

### Resource Hierarchy

```
Account
└── TKE Cluster (cls-xxx)
    ├── Node Pool (np-xxx)
    │   ├── Node 1 (CVM instance)
    │   ├── Node 2 (CVM instance)
    │   └── Node N (CVM instance)
    ├── Addons (metrics-server, coredns, csi, etc.)
    ├── Namespace(s)
    │   ├── Pod(s)
    │   ├── Service(s)
    │   └── Deployment(s)
    └── Storage (CBS via CSI)
```

### Networking Models

| Network Plugin | Description | Max Pods/Node | Use Case |
|----------------|-------------|---------------|----------|
| **VPC-CNI** | Native VPC networking, each pod gets a VPC IP | 256 (by VPC subnet size) | Large clusters, performance-critical workloads |
| **Global Routing** (GR) | Overlay network, pod IPs are managed independently | 256 | Default mode, simpler IP management |
| **Cilium** | eBPF-based networking with advanced policies | 256+ | Advanced network policy requirements |

### Key Dependencies

TKE depends on other Tencent Cloud services:

| Dependency | Purpose | Delegate Skill |
|------------|---------|----------------|
| **VPC** (Virtual Private Cloud) | Cluster networking, subnet for nodes/pods | `qcloud-vpc-ops` |
| **CVM** (Cloud Virtual Machine) | Worker node instances | `qcloud-cvm-ops` |
| **CLB** (Cloud Load Balancer) | LoadBalancer-type Services | `qcloud-clb-ops` |
| **CBS** (Cloud Block Storage) | PV storage for stateful workloads | `qcloud-cvm-ops` (CBS scope) |
| **COS** (Cloud Object Storage) | Container image storage (legacy) or artifacts | `qcloud-cos-ops` |
| **TCR** (Container Registry) | Modern container image registry | `qcloud-tcr-ops` (when present) |
| **Monitor** | Cluster metrics, node metrics, alerting | `qcloud-monitor-ops` |

## Limits and Quotas

| Resource | Default Limit | Notes |
|----------|---------------|-------|
| Clusters per account | 50 | Can request quota increase |
| Node pools per cluster | 50 | |
| Nodes per cluster | 500 | For large clusters, contact support |
| Pods per node (VPC-CNI) | 256 | Limited by subnet IP range |
| Pods per node (GR) | 256 | |
| Addons per cluster | 20 | |
| Clusters per region | Varies | Check DescribeUserQuota |

## Supported Regions

| Region | Code | TKE Available |
|--------|------|---------------|
| Guangzhou | `ap-guangzhou` | ✓ |
| Shanghai | `ap-shanghai` | ✓ |
| Beijing | `ap-beijing` | ✓ |
| Chengdu | `ap-chengdu` | ✓ |
| Chongqing | `ap-chongqing` | ✓ |
| Nanjing | `ap-nanjing` | ✓ |
| Hong Kong | `ap-hongkong` | ✓ |
| Singapore | `ap-singapore` | ✓ |
| Tokyo | `ap-tokyo` | ✓ |
| Seoul | `ap-seoul` | ✓ |
| Frankfurt | `eu-frankfurt` | ✓ |
| Virginia | `na-ashburn` | ✓ |

## Node OS Options

| OS | Identifier | Notes |
|----|------------|-------|
| Tlinux 3.1 | `tlinux3.1x86_64` | Recommended, TKE-optimized |
| Ubuntu 22.04 | `ubuntu22.04x86_64` | Standard Ubuntu |
| CentOS 7.9 | `centos7.9x86_64` | Legacy support |

## Cluster Lifecycle States

| State | Meaning |
|-------|---------|
| `Creating` | Cluster is being provisioned |
| `Running` | Cluster is operational |
| `Abnormal` | Cluster has issues (check node health, control plane) |
| `Updating` | Cluster version or configuration update in progress |
| `Scaling` | Node pool is scaling up or down |
| `Aborting` | Cluster deletion in progress |
| `Deleting` | Cluster deletion in progress |

## Node Pool Auto-Scaling

Node pools support horizontal auto-scaling based on pod pending events or custom metrics:

| Setting | Description |
|---------|-------------|
| `MinNum` | Minimum nodes in pool |
| `MaxNum` | Maximum nodes in pool |
| `DesiredPodNum` | Target pod count (when using custom HPA) |
| `EnableAutoscale` | Enable/disable auto-scaling |

## Kubernetes Version Support

| K8s Version | TKE Support | Notes |
|-------------|-------------|-------|
| 1.32 | Latest | Recommended for new clusters |
| 1.30 | Stable | Widely used |
| 1.28 | LTS | End of approaching support |
| 1.26 | Maintenance | Plan upgrade |

> Check official TKE documentation for current supported versions.

## Cost Model

| Billing Mode | Description |
|--------------|-------------|
| Pay-as-you-go (按量计费) | Hourly billing for nodes, per-second for cluster control plane (free for managed) |
| Prepaid (包年包月) | Monthly/annual commitment for node instances, discounted rates |

> Managed cluster control plane is **free**; only worker node CVM costs are charged.