# Well-Architected Assessment Checklist

## Operational Excellence

- [ ] Sandbox tools defined as code (Terraform/Pulumi) or via repeatable scripts
- [ ] Image prewarming configured for production tools (WarmCount >= 3)
- [ ] CLS logging enabled on all production tools
- [ ] Audit logs reviewed weekly via CloudAudit console
- [ ] Runbooks documented for: tool deletion, key rotation, quota exhaustion

## Security

- [ ] API keys scoped via CAM policies (least privilege)
- [ ] Keys rotated quarterly via CreateAPIKey + DeleteAPIKey workflow
- [ ] SecretId/SecretKey stored in secrets manager (not in code)
- [ ] E2B_API_KEY masked in all logs (first 4 + last 4)
- [ ] Sandbox tools use isolated VPC if accessing internal services
- [ ] No long-lived keys in client-side code (use STS tokens where possible)

## Reliability

- [ ] Multi-region failover plan documented
- [ ] Exponential backoff on RequestLimitExceeded
- [ ] Instance health checked via DescribeSandboxInstanceList before use
- [ ] Quota monitoring at 80% threshold
- [ ] Graceful degradation if sandbox unavailable (fallback to local exec)

## Performance Efficiency

- [ ] Tool specs right-sized via CloudMonitor MemoryUtilization/CpuUtilization
- [ ] Image prewarming reduces cold-start to under 200ms P95
- [ ] Connection pooling for client SDK (reuse Sandbox objects within session)
- [ ] Batch instance creation where possible

## Cost Optimization

- [ ] Idle instances terminated within 5 minutes (not waiting for 24h auto-cleanup)
- [ ] Tool specs (CPU/Memory) reduced if utilization < 30% sustained
- [ ] Sandbox-hours tracked monthly per team/project tag
- [ ] CreatePreCacheImageTask WarmCount tuned to actual demand (not over-provisioned)
- [ ] Dev/test environments use smaller specs than prod

## Scoring

For each pillar, score 0-3 (0=missing, 1=partial, 2=mostly, 3=fully). Total / 75 = maturity %.

| Pillar | Score |
|---|---|
| Operational Excellence | __/15 |
| Security | __/18 |
| Reliability | __/15 |
| Performance | __/12 |
| Cost | __/15 |
| **Total** | **__/75** |
