# CLI Usage Guide

## Command Map

| Operation | CLI Command | SDK Method |
|-----------|------------|------------|
| Create Mesh | `tccli tcm CreateMesh` | `CreateMesh` |
| List Meshes | `tccli tcm DescribeMeshList` | `DescribeMeshList` |
| Get Mesh Details | `tccli tcm DescribeMesh` | `DescribeMesh` |
| Delete Mesh | `tccli tcm DeleteMesh` | `DeleteMesh` |
| Link Clusters | `tccli tcm LinkClusterList` | `LinkClusterList` |
| Unlink Cluster | `tccli tcm UnlinkCluster` | `UnlinkCluster` |
| Modify Mesh | `tccli tcm ModifyMesh` | `ModifyMesh` |
| Configure Tracing | `tccli tcm ModifyTracingConfig` | `ModifyTracingConfig` |
| Configure Access Logs | `tccli tcm ModifyAccessLogConfig` | `ModifyAccessLogConfig` |
| Link Prometheus | `tccli tcm LinkPrometheus` | `LinkPrometheus` |
| Unlink Prometheus | `tccli tcm UnlinkPrometheus` | `UnlinkPrometheus` |

## Common Patterns

### List all meshes

```bash
tccli tcm DescribeMeshList --Region ap-guangzhou
```

### Get mesh details

```bash
tccli tcm DescribeMesh \
  --Region ap-guangzhou \
  --MeshId mesh-xxx
```

### Create mesh with tracing

```bash
tccli tcm CreateMesh \
  --Region ap-guangzhou \
  --MeshName "my-mesh" \
  --MeshVersion "1.18.1-istio" \
  --TracingConfig '{"Enable":true,"Sampling":1.0}'
```

### Link cluster to mesh

```bash
tccli tcm LinkClusterList \
  --Region ap-guangzhou \
  --MeshId mesh-xxx \
  --ClusterList '["cls-xxx"]'
```

### Unlink cluster

```bash
tccli tcm UnlinkCluster \
  --Region ap-guangzhou \
  --MeshId mesh-xxx \
  --ClusterId cls-xxx
```

### Delete mesh

```bash
tccli tcm DeleteMesh \
  --Region ap-guangzhou \
  --MeshId mesh-xxx
```

## Coverage Gap Table

| Feature | CLI Support | SDK Support | Notes |
|---------|-------------|-------------|-------|
| Mesh CRUD | ✅ | ✅ | Full support |
| Cluster linking | ✅ | ✅ | Full support |
| Tracing config | ✅ | ✅ | Full support |
| Access logs | ✅ | ✅ | Full support |
| Prometheus integration | ✅ | ✅ | Full support |
| Istio CRD management | ❌ | ⚠️ | Use kubectl |
| Sidecar injection | ❌ | ❌ | Use kubectl |

Note: Istio CRDs (VirtualService, DestinationRule, etc.) must be managed via `kubectl` after mesh creation.
