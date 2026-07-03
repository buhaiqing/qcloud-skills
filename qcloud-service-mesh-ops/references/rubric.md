# GCL Scoring Rubric — Service Mesh

## C1: Security (Security)

| Check | Weight | Pass Criteria |
|-------|--------|---------------|
| No credential exposure | Critical | No SecretKey in any output |
| mTLS configuration | High | Strict mode for production |
| Authorization policies | High | Policies defined for sensitive services |
| Egress control | Medium | Egress gateway configured |

## C2: Reliability (可靠性)

| Check | Weight | Pass Criteria |
|-------|--------|---------------|
| Multi-cluster setup | High | Mesh spans ≥2 clusters |
| Circuit breaker | High | Outlier detection enabled |
| Health checks | Medium | Active health checks configured |
| Retry policies | Medium | Appropriate retry configuration |

## C3: API Correctness (API 正确性)

| Check | Weight | Pass Criteria |
|-------|--------|---------------|
| Valid mesh ID | Critical | Mesh exists and is active |
| Valid cluster ID | Critical | Cluster exists and is linked |
| Correct API version | High | Using supported MeshVersion |
| Parameter validation | High | All parameters validated |

## C4: Safety Gates (安全门)

| Check | Weight | Pass Criteria |
|-------|--------|---------------|
| Delete confirmation | Critical | User confirmed deletion |
| Dependency check | High | Clusters unlinked before delete |
| Resource cleanup | Medium | Mesh resources removed |
| Rollback plan | Medium | Rollback steps documented |

## C5: UX (用户体验)

| Check | Weight | Pass Criteria |
|-------|--------|---------------|
| Clear error messages | High | Errors are actionable |
| Progress indication | Medium | Long operations show progress |
| Output formatting | Medium | JSON paths documented |
| Help text | Low | Contextual help available |

## C6: Token Efficiency (Token 效率)

| Check | Weight | Pass Criteria |
|-------|--------|---------------|
| No hardcoded versions | Medium | Query API for versions |
| Compact tables | Low | Tables ≤3 columns |
| No duplicate content | Medium | No duplicated flows |

## Scoring

- Critical: Must pass, blocking if failed
- High: Should pass, warning if failed
- Medium/Low: Nice to have, note if failed

## Product-Specific Safety Rules

1. **DeleteMesh HALT conditions**:
   - Cluster still linked → MUST unlink first
   - Active traffic → MUST warn user
   - No confirmation → MUST not proceed

2. **UnlinkCluster HALT conditions**:
   - Traffic flowing through mesh → MUST warn
   - No alternative routing → MUST recommend

3. **ModifyMesh restrictions**:
   - Cannot downgrade MeshVersion
   - Cannot change mesh name
