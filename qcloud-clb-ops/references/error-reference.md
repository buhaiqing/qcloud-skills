# CLB Error Code Reference

Product-specific error codes for the CLB (Cloud Load Balancer) API. Recovery notes assume the
[Failure Recovery](../SKILL.md#failure-recovery) loop in SKILL.md (HALT vs retry per error class).

## Parameter Validation Errors

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter.LBIdNotFound` | LoadBalancer ID invalid | Verify LB ID; suggest `DescribeLoadBalancers` |
| `InvalidParameter.ListenerIdNotFound` | Listener ID invalid | Verify listener ID |
| `InvalidParameter.LocationNotFound` | Forwarding rule not found | Verify rule location/URL |
| `InvalidParameter.PortCheckFailed` | Port conflict or invalid | Use different port |
| `InvalidParameter.ProtocolCheckFailed` | Protocol mismatch | Check protocol support per CLB type |
| `InvalidParameter.RegionNotFound` | Region invalid | Verify region is correct |
| `InvalidParameter.FormatError` | Parameter format error | Check parameter format per API spec |
| `InvalidParameter.InvalidFilter` | Query filter error | Fix filter parameter structure |
| `InvalidParameter.RewriteAlreadyExist` | Rewrite rule already exists | Use different source URL |
| `InvalidParameter.SomeRewriteNotFound` | Some rewrite rules not found | Verify rewrite rule IDs |
| `InvalidParameter.ClientTokenLimitExceeded` | ClientToken expired | Generate new ClientToken |
| `InvalidParameterValue.Duplicate` | Duplicate parameter value | Use unique values |
| `InvalidParameterValue.InvalidFilter` | Filter input error | Fix filter name/values |
| `InvalidParameterValue.Length` | Parameter length error | Shorten parameter value |
| `InvalidParameterValue.Range` | Parameter range error | Adjust value to valid range |

## CLB Status & Operation Errors

| Code | Description | Recovery |
|------|-------------|----------|
| `FailedOperation.InvalidLBStatus` | LB status abnormal | Wait for LB to stabilize; check `DescribeLoadBalancers` |
| `FailedOperation.ResourceInOperating` | Resource being operated | Wait 30s; retry |
| `FailedOperation.ResourceInCloning` | Resource being cloned | Wait for clone to complete |
| `FailedOperation.NoListenerInLB` | No listener for operation | Create listener first |
| `FailedOperation.EipTrafficCheckRisk` | EIP bandwidth exceeds threshold | Disable anti-misoperation in EIP console |
| `FailedOperation.FrequencyCheckRisk` | Delete frequency too high | Slow down delete rate |
| `FailedOperation.TargetNumCheckRisk` | Rule count risk too high | Pass `ForceDelete=true` |
| `FailedOperation.TrafficCheckRisk` | Traffic check high risk | Confirm force delete with `ForceDelete=true` |

## Auth & Resource Errors

| Code | Description | Recovery |
|------|-------------|----------|
| `AuthFailure` | CAM signature/auth error | Check CAM policies for CLB |
| `OperationDenied` | Operation denied | Check account permissions |
| `ResourcesSoldOut` | Resources sold out | Try different region or specification |
| `InternalError` | Internal server error | Transient — retry; escalate if persists |
