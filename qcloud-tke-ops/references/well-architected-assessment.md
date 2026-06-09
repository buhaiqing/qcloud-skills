# TKE Well-Architected Assessment

## Reliability (可靠性)

| Requirement | Status | Documentation |
|-------------|--------|---------------|
| Multi-AZ node pools | ✓ | Create node pools in different availability zones within a region |
| Backup operations | ✓ | Export cluster YAML (`kubectl get all --all-namespaces -o yaml`) before any destructive operation |
| Recovery runbook | ✓ | Restore from backup: `kubectl apply -f backup.yaml` |
| Safety gates | ✓ | All destructive ops (DeleteCluster) require explicit confirmation with cluster ID |
| Auto-repair | ✓ | TKE managed clusters support node auto-repair; node pools detect and replace unhealthy nodes |
| DR runbook | ✓ | Document cross-region cluster deployment with Velero for stateful workloads |

### Multi-AZ Deployment Recommendation

Deploy node pools across multiple availability zones for high availability:

```bash
# Node pool in zone 3 (ap-guangzhou-3)
tccli tke CreateClusterAsGroup --ClusterId "cls-xxx" --NodePoolName "pool-zone3" \
  --SubnetId "subnet-az3" --VpcId "vpc-xxx" --MaxNum 10 --MinNum 2

# Node pool in zone 4 (ap-guangzhou-4)
tccli tke CreateClusterAsGroup --ClusterId "cls-xxx" --NodePoolName "pool-zone4" \
  --SubnetId "subnet-az4" --VpcId "vpc-xxx" --MaxNum 10 --MinNum 2
```

Use pod anti-affinity and topology spread constraints in Kubernetes manifests to distribute workloads.

## Security (安全性)

| Requirement | Status | Documentation |
|-------------|--------|---------------|
| Minimum CAM permissions | ✓ | See CAM Policy below |
| Credential masking | ✓ | Enforced in all execution paths |
| Network isolation | ✓ | VPC isolation + security group rules per cluster |
| RBAC | ✓ | Kubernetes RBAC integrated with Tencent Cloud CAM |
| Encryption | ✓ | Support for TLS between API server and kubelet |

### CAM Policy Example

```json
{
  "version": "2.0",
  "statement": [
    {
      "action": [
        "tke:Describe*",
        "tke:Get*"
      ],
      "effect": "allow",
      "resource": "*"
    },
    {
      "action": [
        "tke:CreateCluster",
        "tke:CreateClusterAsGroup",
        "tke:ModifyClusterAsGroup",
        "tke:InstallComponents"
      ],
      "effect": "allow",
      "resource": "*"
    },
    {
      "action": [
        "tke:DeleteCluster",
        "tke:DeleteClusterAsGroups"
      ],
      "effect": "allow",
      "resource": "*"
    }
  ]
}
```

## Cost (成本)

| Requirement | Status | Documentation |
|-------------|--------|---------------|
| Billing models | ✓ | Managed cluster control plane is free; CVM nodes billed per instance type |
| Idle detection | ✓ | Detect clusters with 0 node pools or empty clusters running > 7 days |
| Right-sizing | ✓ | Recommend resizing node pools based on actual pod resource usage |

### Idle Cluster Detection

| Pattern | Detection | Recommendation |
|---------|-----------|----------------|
| No node pools | `DescribeClusterAsGroups` returns empty list | Delete cluster if unintentional |
| No running pods | All cluster nodes have 0 Running pods for 7+ days | Scale down node pool or delete cluster |
| Cluster status Abnormal | `ClusterStatus == "Abnormal"` for 24+ hours | Investigate or delete |

### Cost Optimization

| Action | Savings |
|--------|---------|
| Use prepaid nodes for baseline capacity | 30-50% vs pay-as-you-go |
| Use auto-scaling pool for burst workloads | Pay only for actual usage |
| Right-size node instance types | Match CPU/memory to actual workload needs |
| Delete unused clusters | Eliminate idle node costs entirely |

## Efficiency (效率)

| Requirement | Status | Documentation |
|-------------|--------|---------------|
| Batch operations | ✓ | `DeleteClusterAsGroups` supports batch node pool deletion |
| Automation support | ✓ | Full CLI + SDK for CI/CD, Terraform, and scripting |
| API optimization | ✓ | Paginated Describe APIs with appropriate Limit values |
| Node provisioning | ✓ | Concurrent node creation; use larger node counts per batch |

### Batch Cluster Operations

```bash
# Batch describe clusters with jq filter
tccli tke DescribeClusters --Region ap-guangzhou --Limit 100 \
  | jq '[.Response.Clusters[] | {id: .ClusterId, name: .ClusterName, status: .ClusterStatus, nodes: .TotalNodeNum}]'
```

### Automation: Cluster + Node Pool in One Flow

```bash
# Automated cluster provisioning
CLUSTER_ID=$(tccli tke CreateCluster --ClusterType MANAGED_TKE \
  --ClusterName "$CLUSTER_NAME" --ClusterOs "tlinux3.1x86_64" \
  --ClusterVersion "1.28.3" --VpcId "$VPC_ID" --SubnetId "$SUBNET_ID" \
  | jq -r '.Response.ClusterId')

# Wait for cluster ready
for i in $(seq 1 60); do
  STATUS=$(tccli tke DescribeClusters --ClusterId "$CLUSTER_ID" | jq -r '.Response.Clusters[0].ClusterStatus')
  [ "$STATUS" = "Running" ] && break
  sleep 10
done

# Create node pool
tccli tke CreateClusterAsGroup --ClusterId "$CLUSTER_ID" \
  --NodePoolName "default" --InstanceType "SA5.MEDIUM8" \
  --SubnetId "$SUBNET_ID" --VpcId "$VPC_ID" --MaxNum 10 --MinNum 2
```

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-tke-ops` |
| `product` | `tke` |
| Finding `id` pattern | `tke-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

### Pillar → checklist map

| `pillars` key | Checklist source in this document |
|---------------|-------------------------------------|
| `reliability` | Reliability / HA sections |
| `security` | Security sections |
| `cost` | Cost sections |
| `efficiency` | Efficiency sections |

### Populate rules

1. Include only pillar keys requested by orchestrator `{{user.pillars}}` (`all` = four keys).
2. `score = round(passed / applicable × 100)`; use `status=not_assessed` when data missing (omit score or null).
3. Each failed/warn checklist item → one `findings[]` entry with all six finding fields (§2.1 in schema).
4. `recommendations[]`: top 1–5 actions with `priority`, `pillar`, `action`, `effort` (§2.2 in schema).
5. `partial=true` when any pillar is `not_assessed`; top-level `status=PARTIAL`.
6. `trace.commands`: every read API call; mask credentials. `errors[]` on API failure (§3 in schema).
7. Local “Score Calculation” sections are for manual review only — **worker mode must emit this JSON**.

### Example `{{output.product_assessment}}`

```json
{
  "skill_id": "qcloud-tke-ops",
  "product": "tke",
  "region": "ap-guangzhou",
  "scope": "account-wide",
  "assessment_date": "2026-06-09T10:00:00+08:00",
  "status": "OK",
  "partial": false,
  "resource_count": 3,
  "pillars": {
    "reliability": {
      "score": 75,
      "status": "assessed",
      "findings": [
        {
          "id": "tke-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Worker nodes in single zone",
          "evidence": "All nodes in one zone",
          "recommendation": "Use multi-AZ node pool or spread across zones",
          "effort": "medium"
        }
      ]
    },
    "security": {
      "score": 88,
      "status": "assessed",
      "findings": []
    },
    "cost": {
      "score": 72,
      "status": "assessed",
      "findings": []
    },
    "efficiency": {
      "score": 70,
      "status": "assessed",
      "findings": []
    }
  },
  "recommendations": [
    {
      "priority": "High",
      "pillar": "reliability",
      "action": "Use multi-AZ node pool or spread across zones",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [
      "tccli tke DescribeClusters --Region ap-guangzhou (SecretKey=<masked>)"
    ],
    "request_ids": [
      "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    ]
  },
  "errors": []
}
```
