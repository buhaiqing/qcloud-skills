# Integration Guide

## SDK Setup

```bash
pip install tencentcloud-sdk-python
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TENCENTCLOUD_SECRET_ID` | Yes | API Secret ID |
| `TENCENTCLOUD_SECRET_KEY` | Yes | API Secret Key |
| `TENCENTCLOUD_REGION` | Yes | Region (e.g., ap-guangzhou) |

## Cross-Skill Delegation

| Scenario | Delegate To |
|----------|------------|
| TKE cluster creation/management | `qcloud-tke-ops` |
| K8s node operations | `qcloud-tke-ops` |
| Container registry (TCR) | `qcloud-tke-ops` |
| Monitoring and alerting | `qcloud-monitor-ops` |
| Log aggregation (CLS) | `qcloud-cls-ops` |
| VPC/network policies | `qcloud-vpc-ops` |

## Service Mesh + TKE Integration

### Typical Workflow

1. **Create TKE cluster** (via `qcloud-tke-ops`)
2. **Create TCM mesh** (this skill)
3. **Link cluster to mesh** (this skill)
4. **Deploy applications** (via `qcloud-tke-ops` kubectl)
5. **Configure traffic rules** (kubectl apply Istio CRDs)

### kubectl Integration

After mesh setup, use kubectl for Istio resource management:

```bash
# Apply VirtualService
kubectl apply -f virtualservice.yaml

# Apply DestinationRule
kubectl apply -f destinationrule.yaml

# Check Sidecar injection
kubectl get pods -n default -o jsonpath='{.items[*].spec.containers[*].name}'
```

## Prometheus Integration

Link existing Prometheus instance to mesh for metrics:

```bash
tccli tcm LinkPrometheus \
  --MeshId mesh-xxx \
  --PrometheusId prom-xxx
```

## Distributed Tracing Integration

Configure tracing backends:

```bash
# Jaeger
tccli tcm ModifyTracingConfig \
  --MeshId mesh-xxx \
  --TracingConfig '{"Enable":true,"Sampling":1.0,"Backend":"jaeger","Address":"jaeger:9411"}'
```

## Best Practices

1. **Namespace isolation**: Use separate namespaces for different environments
2. **Gradual Sidecar rollout**: Start with permissive mTLS, then move to strict
3. **Circuit breakers**: Configure outlier detection for resilience
4. **Resource limits**: Set CPU/memory limits on Sidecar proxies
