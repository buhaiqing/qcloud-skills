# Service Mesh Troubleshooting

## Mesh Creation Issues

### Symptom: Mesh creation fails

| Check | Command |
|-------|---------|
| Verify region support | Check TCM availability in region |
| Check quota | `tccli tcm DescribeMeshList | wc -l` |
| Validate mesh name | Ensure unique, valid format |

### Symptom: Cluster fails to link

| Check | Command |
|-------|---------|
| Cluster status | `tccli tke DescribeClusters` |
| Cluster region | Must match mesh region |
| Network connectivity | VPC peering if different VPCs |

## Sidecar Injection Issues

### Symptom: Sidecar not injected

1. **Check namespace label:**
   ```bash
   kubectl get namespace <namespace> -o jsonpath='{.metadata.labels.istio-injection}'
   ```

2. **Check pod annotations:**
   ```bash
   kubectl get pod <pod> -o jsonpath='{.metadata.annotations.sidecar\.istio\.io/inject}'
   ```

3. **Restart deployment:**
   ```bash
   kubectl rollout restart deployment/<name> -n <namespace>
   ```

### Symptom: Sidecar proxy errors

```bash
# Check proxy logs
kubectl logs <pod> -c istio-proxy -n <namespace>

# Check proxy config
istioctl proxy-config cluster <pod>.<namespace>
```

## Traffic Management Issues

### Symptom: Traffic not routing correctly

1. **Verify VirtualService exists:**
   ```bash
   kubectl get virtualservice -n <namespace>
   ```

2. **Check DestinationRule:**
   ```bash
   kubectl get destinationrule -n <namespace>
   ```

3. **Test with curl:**
   ```bash
   kubectl exec -it <source-pod> -c istio-proxy -- curl -v http://<destination>
   ```

## mTLS Issues

### Symptom: Service communication fails with mTLS enabled

1. **Check mTLS mode:**
   ```bash
   kubectl get peerauthentication -n <namespace>
   ```

2. **Verify certificates:**
   ```bash
   istioctl authn tls-check <pod>.<namespace>
   ```

3. **Check permissive vs strict:**
   - Permissive allows both plaintext and TLS
   - Strict requires mTLS for all traffic

## Observability Issues

### Symptom: No tracing data

| Check | Action |
|-------|--------|
| Tracing enabled | `tccli tcm DescribeMesh --MeshId <id>` |
| Sampling rate | Should be > 0 |
| Tracing backend | Verify Jaeger/Zipkin endpoint |

### Symptom: No metrics in TCM console

1. **Check Prometheus linkage:**
   ```bash
   tccli tcm DescribeMesh --MeshId <id>
   ```

2. **Verify prometheus config:**
   - Ensure Prometheus is linked to mesh
   - Check scrape configurations

## Common Error Codes

| Error Code | Likely Cause | Solution |
|------------|--------------|----------|
| `MeshNotFound` | Invalid mesh ID | Verify mesh exists |
| `ClusterNotFound` | Invalid cluster ID | Verify cluster exists |
| `ClusterAlreadyLinked` | Duplicate link request | Check linked clusters |
| `ClusterStatusNotRunning` | Cluster not ready | Wait for cluster |
| `MeshHasLinkedClusters` | Delete blocked | Unlink clusters first |
| `QuotaExceeded` | Mesh limit reached | Request quota increase |

## Debug Commands

```bash
# List all meshes
tccli tcm DescribeMeshList

# Get mesh details
tccli tcm DescribeMesh --MeshId mesh-xxx

# Check linked clusters
tccli tcm DescribeMesh --MeshId mesh-xxx --output json | jq '.Mesh.LinkedClusterSet'

# Verify istiod status
kubectl get pods -n istio-system

# Check Sidecar sync status
istioctl proxy-status
```
