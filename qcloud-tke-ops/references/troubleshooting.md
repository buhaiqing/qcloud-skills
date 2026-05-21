# TKE Troubleshooting Guide

## Error Code Reference

| Code | Meaning | Retry? | Agent Action | UX Feedback |
|------|---------|--------|--------------|-------------|
| `InvalidParameter` | Parameter validation failed | No | Fix parameter against API spec | `[ERROR] InvalidParameter: Check CreateCluster API docs → Fix → Retry` |
| `InvalidParameterValue` | Parameter value out of valid range | No | Adjust value per API spec | `[ERROR] InvalidParameterValue: Use valid value → Check spec → Retry` |
| `MissingParameter` | Required parameter not provided | No | Add missing parameter | `[ERROR] MissingParameter: Add required parameter → Retry` |
| `ResourceNotFound` | Target resource does not exist | No | Verify resource ID; suggest DescribeList | `[ERROR] ResourceNotFound: Verify ID with Describe API → Retry` |
| `ResourceNotFound.ClusterNotFound` | TKE cluster not found | No | List clusters to find correct ID | `[ERROR] Cluster not found → Run DescribeClusters → Verify ID` |
| `ResourceInsufficient` | Cluster quota exceeded | No | HALT; request quota increase | `[ERROR] Quota exceeded → Contact support for increase` |
| `ResourceInUse` | Cluster name or CIDR already used | No | Use unique name or CIDR range | `[ERROR] Name/CIDR in use → Choose different value → Retry` |
| `ResourcePreRunning` | Cluster not yet ready for operations | Yes (3x, 30s) | Poll DescribeClusters; retry when Running | `⚠️ Cluster not ready → Polling status → Retrying in 30s` |
| `ResourcePreDeleting` | Cluster still being deleted | No | Wait for deletion to complete | `[ERROR] Cluster in deletion → Wait for completion` |
| `OperationConflict` | Concurrent operation on same cluster | Yes (3x, 30s) | Wait for conflicting op; poll; retry | `⚠️ Operation in progress → Waiting → Retrying in 30s` |
| `InvalidSecretKey` / `InvalidSecretId` | Credential invalid | No | HALT; fix environment variables | `[ERROR] Credential invalid → Verify TENCENTCLOUD_SECRET_ID/KEY` |
| `RequestLimitExceeded` | API rate limit exceeded | Yes (3x) | Exponential backoff: 1s, 2s, 4s | `⚠️ Rate limit → Retry in {backoff}s (Attempt {n}/3)` |
| `InternalError` | Server-side internal error | Yes (3x) | Retry; escalate with RequestId if persists | `[ERROR] InternalError → Retry → Escalate with RequestId` |
| `QuotaExceeded` | TKE quota limit hit | No | HALT; user requests increase | `[ERROR] Cluster quota hit → Request increase via console` |
| `AddonConflict` | Addon already installed or conflict | No | Check existing addons via DescribeClusterAttribute | `[ERROR] Addon conflict → Check existing addons → Resolve` |
| `NodePoolResourceNotEnough` | Instance type unavailable in zone | No | Suggest different instance type | `[ERROR] Instance type unavailable → Change type → Retry` |

## Diagnostic Procedures

### Procedure 1: Cluster Creation Failure

**Symptom**: CreateCluster returns error

**Steps**:
1. Validate VPC/Subnet: `tccli vpc DescribeVpcs --VpcId <vpc_id>`
2. Validate Security Group: `tccli vpc DescribeSecurityGroups --SecurityGroupIds <sg_id>`
3. Check quota: `tccli tke DescribeUserQuota`
4. Validate instance type availability: `tccli tke DescribeClusterAsGroupOption`
5. Verify CIDR range doesn't overlap with existing VPC resources

**Most Likely Causes**:
1. VPC or subnet doesn't exist in selected region
2. Security group not found or misconfigured
3. Cluster quota exceeded
4. IP range conflict with existing VPC

### Procedure 2: Cluster Status Unknown/Abnormal

**Symptom**: Cluster shows non-Running status

**Steps**:
1. Query cluster status: `tccli tke DescribeClusters --ClusterId <cluster_id>`
2. Check cluster events: `tccli tke DescribeClusterAttribute --ClusterId <cluster_id> --Attribute Events`
3. Verify node pool status: `tccli tke DescribeClusterAsGroups --ClusterId <cluster_id>`
4. Check individual node status: `tccli tke DescribeClusterInstances --ClusterId <cluster_id>`

**Decision Tree**:
- Status = `Creating` → Wait/poll until Running (max 600s)
- Status = `Abnormal` → Check cluster events for root cause
- Status = `Deleting` → Deletion in progress; do not retry

### Procedure 3: Node Pool Scaling Failure

**Symptom**: CreateClusterAsGroup or ModifyClusterAsGroup fails

**Steps**:
1. Check cluster is Running: `tccli tke DescribeClusters --ClusterId <cluster_id>`
2. Validate instance type available in zone
3. Check CVM quota: `tccli cvm DescribeInstancesQuota`
4. Verify subnet has available IP addresses
5. Check node pool error field in DescribeClusterAsGroups response

**Most Likely Causes**:
1. Cluster not in Running state
2. Instance type not available in target zone
3. CVM quota insufficient
4. Subnet IP pool exhausted

### Procedure 4: Addon Installation Failure

**Symptom**: InstallComponents returns error or addon stays Pending

**Steps**:
1. Check cluster version compatibility with addon version
2. Verify addon not already installed: `tccli tke DescribeClusterAttribute --ClusterId <cluster_id> --Attribute ClusterLevel/Addons`
3. Check addon quota: `tccli tke SetAddonsRemainQuota` or DescribeClusterAttribute
4. Verify node pool has sufficient resources for addon pods

## Multi-Round Diagnosis

### Round 1: Initial Assessment

```yaml
round_1:
  checks:
    - cluster_exists
    - cluster_status_running
    - credentials_valid
    - quota_available
    - vpc_subnet_available
  actions:
    - describe_cluster
    - test_api_call
    - check_quotas
  decision:
    - if all pass: proceed to Round 2
    - if any fail: fix issue and retry Round 1
```

### Round 2: Detailed Analysis

```yaml
round_2:
  checks:
    - node_pool_status
    - addon_status
    - cluster_events
    - node_instance_health
  actions:
    - describe_cluster_as_groups
    - describe_cluster_instances
    - describe_cluster_attribute
  decision:
    - if anomaly found: proceed to Round 3
    - if no anomaly: escalate
```

### Round 3: Root Cause Determination

```yaml
round_3:
  checks:
    - event_timeline_analysis
    - resource_dependency_chain
    - version_compatibility
  actions:
    - correlate cluster events with operations
    - trace VPC/CVM/CLB dependency chain
    - verify K8s version ↔ addon compatibility
  output:
    - root_cause_hypothesis
    - evidence_chain
    - resolution_recommendation
```

## Escalation Criteria

Escalate when:
- `InternalError` persists after 3 retries with different RequestIds
- Cluster stuck in non-terminal state for > 600s
- Multi-round diagnosis inconclusive
- Platform-level TKE service outage suspected

**Escalation Protocol**:
1. Collect last RequestId from API response
2. Document: cluster ID, region, operation attempted, error codes encountered, diagnosis steps taken
3. Contact Tencent Cloud support with: ClusterId, RequestId, Timestamp, Error messages

## Common Scenarios

### Scenario: kubeconfig Expired

**Problem**: kubectl cannot authenticate to cluster

**Resolution**:
1. Fetch new kubeconfig: `tccli tke DescribeClusterSecurity --ClusterId <cluster_id>`
2. Extract CA certificate, endpoint URL, and access token
3. Update `~/.kube/config` with new credentials
4. Note: Access tokens expire every 24 hours

### Scenario: Pod Stuck in Pending on Node

**Problem**: Pods not scheduling on cluster nodes

**Resolution**:
1. Check node status: `tccli tke DescribeClusterInstances --ClusterId <cluster_id>`
2. Verify node pool has capacity: `tccli tke DescribeClusterAsGroups --ClusterId <cluster_id>`
3. Check if node is `NotReady` — may need restart/replacement
4. Scale node pool if insufficient capacity: `tccli tke ModifyClusterAsGroup`