# TKE SecOps Security Operations Module

Security operations patterns for Tencent Cloud TKE (Kubernetes Engine).

---

## 1. Security Audit Logs

### CAM Audit Log Query

```python
from tencentcloud.cloudaudit import cloudaudit_client, models

def query_tke_audit_logs(start_time: str, end_time: str) -> list:
    client = cloudaudit_client.CloudauditClient(cred, region)

    request = models.LookUpEventsRequest()
    request.StartTime = start_time
    request.EndTime = end_time
    request.MaxResults = 100

    response = client.LookUpEvents(request)

    tke_events = [
        {
            'event_id': e.EventId,
            'action': e.EventName,
            'resource': e.Resources[0].ResourceName,
            'user': e.Username,
            'time': e.EventTime,
            'result': e.ErrorCode
        }
        for e in response.Events
        if 'cluster' in e.Resources[0].ResourceName.lower()
        or 'tke' in e.Resources[0].ResourceName.lower()
    ]

    return tke_events
```

### High-Risk TKE Actions

| Action | Risk Level | Monitor |
|--------|------------|---------|
| DeleteCluster | Critical | Alert before deletion, workload loss |
| DeleteNodePool | High | Alert, node drain warning |
| ScaleInCluster | High | Alert, pod eviction |
| UpdateClusterKubeconfig | High | Alert, credential change |
| ModifyClusterAttribute | High | Alert on cluster config change |
| CreateCluster | Medium | Track new deployments |

### Kubeconfig Audit

```bash
# Audit kubeconfig usage — check for suspicious access patterns
tccli tke DescribeClusterSecurityAttribute --ClusterId cls-xxxx

# Review who fetched kubeconfig (via CAM audit logs)
# Look for: UpdateClusterKubeconfig, CreateClusterKubeconfig
```

---

## 2. Credential Rotation Strategy

### Rotation Schedule

| Credential | Rotation Frequency | Method |
|------------|-------------------|--------|
| Cluster Kubeconfig | 90 days | UpdateClusterKubeconfig |
| TENCENTCLOUD API Key | 90 days | CAM console rotation |
| Image Pull Secrets (TCR) | 180 days | UpdateClusterCredential |

### Kubeconfig Rotation Process

```yaml
kubeconfig_rotation:
  process:
    step_1: "Generate new kubeconfig: UpdateClusterKubeconfig"
    step_2: "Distribute to CI/CD systems and developers"
    step_3: "Verify kubectl access with new kubeconfig"
    step_4: "Monitor for access anomalies"
    step_5: "Revoke old kubeconfig after grace period (24h)"

  safety:
    - Never revoke old kubeconfig before verifying new one works
    - Keep old kubeconfig for rollback (24 hours)
    - Use CAM least-privilege service accounts in cluster
```

---

## 3. RBAC Security

### RBAC Security Checklist

| Check | Rule | Status |
|-------|------|--------|
| CAM least privilege | Use specific roles, not QcloudCOSAccessForTKERole | Review |
| Node RBAC | Nodes use node authorizer, not high-privilege | Review |
| Workload RBAC | ServiceAccounts with minimal permissions | Review |
| NetworkPolicy | Enabled and applied | Review |
| No privileged containers | Privileged=false in PodSecurityPolicy | Review |

### RBAC Audit

```bash
# Check cluster RBAC settings
tccli tke DescribeClusters --Region ap-guangzhou

# Verify node pools are not using overly permissive roles
tccli tke DescribeNodePools --ClusterId cls-xxxx
```

---

## 4. Network Security

### Network Security Checklist

| Check | Rule | Status |
|-------|------|--------|
| Cluster in VPC | Private network isolation | Review |
| Public endpoint disabled | EnablePrivateAccess=true, DisablePublicNetwork=true | Review |
| Node in private subnet | No direct node public IPs | Review |
| NetworkPolicy enabled | Restrict pod-to-pod traffic | Review |
| SecurityGroup configured | Restrict node port exposure | Review |

---

## 5. High-Risk Operations

### DeleteCluster — Safety Gate

1. **MUST** warn: all workloads, services, and data in the cluster will be terminated
2. **MUST** list all node pools and workloads
3. **MUST** verify: backup of persistent data (PVC snapshots)
4. **MUST** confirm: user input `CONFIRM DELETE {{cluster_id}}`

### DeleteNodePool — Safety Gate

1. **MUST** warn: all nodes in the pool will be terminated
2. **MUST** check: PodDisruptionBudgets are satisfied
3. **MUST** verify: workloads can be rescheduled to other pools
4. **MUST** confirm: drain completed before deletion

### ScaleInCluster — Safety Gate

1. **MUST** verify: no pods with PDB blocking eviction
2. **MUST** warn: nodes will be cordoned and drained
3. **MUST** check: cluster has sufficient capacity remaining

### UpdateClusterKubeconfig — Safety Gate

1. **MUST** warn: existing kubeconfig will become invalid
2. **MUST** verify: new kubeconfig works before distribution
3. **MUST** provide: rollout plan for all consumers

---

## 6. Compliance Checklist

### TKE Security Compliance

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | Cluster in VPC (private) | ✓/✗ | |
| 2 | Public endpoint disabled | ✓/✗ | |
| 3 | RBAC with least privilege | ✓/✗ | |
| 4 | NetworkPolicy enabled | ✓/✗ | |
| 5 | No privileged containers | ✓/✗ | |
| 6 | Kubeconfig rotated < 90 days | ✓/✗ | |
| 7 | CloudAudit enabled for TKE | ✓/✗ | |
| 8 | SecurityGroup properly restricted | ✓/✗ | |
| 9 | Pod Security Standards enforced | ✓/✗ | |

---

## 7. Emergency Contacts

- On-call SRE: [Contact info]
- Security team: [Contact info]
- Cloud Support: [ Tencent Cloud support ticket ]

---

## References

- [TKE API Documentation](https://cloud.tencent.com/document/api/457)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Tencent Cloud CAM Policy Guide](https://cloud.tencent.com/document/product/598)
