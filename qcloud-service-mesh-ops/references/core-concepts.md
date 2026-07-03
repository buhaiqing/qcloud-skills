# Service Mesh Core Concepts

## Architecture

Tencent Cloud Mesh (TCM) is built on Istio, providing a unified way to connect, secure, and observe microservices.

### Components

| Component | Function |
|-----------|----------|
| **Control Plane** | Manages and configures Sidecar proxies |
| **Data Plane** | Sidecar proxies (Envoy) handling service traffic |
| **Istiod** | Core control plane component (pilot, citadel, galley) |

### Mesh vs K8s Relationship

- TCM **requires** an underlying TKE (Tencent Kubernetes Engine) cluster
- One mesh can span **multiple clusters** (multi-cluster mesh)
- Sidecar injection happens at the **namespace level**

## Sidecar Injection

### Automatic Injection

Label namespace to enable automatic Sidecar injection:

```bash
kubectl label namespace <namespace> istio-injection=enabled
```

All new pods in the namespace will get an `istio-proxy` Sidecar container.

### Selective Injection

Use pod annotations for fine-grained control:

```yaml
annotations:
  sidecar.istio.io/inject: "true"  # or "false"
```

## Traffic Governance

### VirtualService

Defines traffic routing rules:

- Weight-based routing (canary deployment)
- Header-based routing (A/B testing)
- Fault injection (chaos engineering)

### DestinationRule

Defines policies applied to traffic after routing:

- Load balancing settings
- Connection pool settings
- Outlier detection (circuit breaker)
- mTLS settings

### Gateway

Manages inbound traffic from outside the mesh:

- Ingress gateway for external access
- Egress gateway for controlled external access

## Security

### mTLS (Mutual TLS)

Automatically encrypts service-to-service communication:

- **Permissive mode**: Allows both plaintext and TLS (migration mode)
- **Strict mode**: Requires mTLS for all mesh traffic

### Authorization Policy

Controls access between services:

```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: service-policy
spec:
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/frontend"]
```

## Observability

### Distributed Tracing

TCM supports:
- **Jaeger**: Open source tracing system
- **Zipkin**: Alternative tracing backend
- **SkyWalking**: APM tool with tracing

### Metrics

- **Envoy metrics**: Request rate, latency, error rate
- **Service metrics**: Golden signals (RED metrics)
- **Control plane metrics**: Istiod health

### Logging

Access logs can be exported to CLS (Cloud Log Service) for analysis.

## Delegation

- K8s cluster management → `qcloud-tke-ops`
- Monitoring and alerting → `qcloud-monitor-ops`
- Log aggregation → `qcloud-cls-ops`
- VPC/network policies → `qcloud-vpc-ops`
