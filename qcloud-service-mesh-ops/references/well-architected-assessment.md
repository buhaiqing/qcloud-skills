# Well-Architected Assessment — Service Mesh

## Reliability

- **Multi-cluster mesh**: Deploy mesh across multiple clusters for HA
- **Circuit breaker**: Configure outlier detection to prevent cascade failures
- **Retry policies**: Set appropriate retry counts and timeouts
- **Health checks**: Enable active health checks for upstream services

## Security

- **mTLS encryption**: Enable strict mTLS for production workloads
- **Authorization policies**: Define fine-grained access control
- **Cert rotation**: Automatic certificate rotation (default 24h)
- **Egress control**: Restrict external access via egress gateways

## Cost

- **Sidecar resource optimization**: Tune CPU/memory requests
- **Selective injection**: Only inject Sidecars where needed
- **Log sampling**: Reduce log volume with appropriate sampling
- **Prometheus retention**: Adjust metrics retention period

## Efficiency

- **Connection pooling**: Optimize connection reuse
- **Locality-based routing**: Route to nearest endpoints
- **Cache warming**: Pre-warm caches before traffic shift
- **Request hedging**: Send multiple requests, use fastest response

## Assessment Checklist

| Pillar | Check | Weight |
|--------|-------|--------|
| Reliability | Multi-cluster configuration | High |
| Reliability | Circuit breaker configured | High |
| Security | Strict mTLS enabled | Critical |
| Security | Authorization policies defined | High |
| Cost | Sidecar resources optimized | Medium |
| Cost | Selective injection used | Medium |
| Efficiency | Connection pooling enabled | Medium |
| Efficiency | Locality routing configured | Low |
