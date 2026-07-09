# Direct Connect Troubleshooting

## Connectivity Diagnosis

1. **Check physical layer**: Verify fiber connection status with access point
2. **Check DC status**: Ensure `State = AVAILABLE`
3. **Check tunnel status**: Verify tunnel is `AVAILABLE`
4. **Check BGP session**: For BGP tunnels, verify peering is established
5. **Check routing**: Verify route propagation to/from VPC

## Common Issues

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| DC stuck in PENDING | Physical connection not completed | Coordinate with Tencent Cloud/facility |
| Tunnel not establishing | BGP config mismatch | Check AS numbers, peer IPs, auth |
| No route propagation | Route table not associated | Associate DC gateway with VPC route table |
| Intermittent connectivity | Physical line issues | Contact carrier/Tencent Cloud |
| High latency | Suboptimal routing | Check route tables, consider CCN |
| BGP session down | Authentication failure | Verify MD5 password matches |

## Error Code Quick Reference

| Error Code | Meaning | Action |
|------------|---------|--------|
| `InvalidParameter` | Parameter validation failed | Check request parameters |
| `ResourceNotFound` | Resource doesn't exist | Verify resource ID |
| `ResourceQuotaExceeded` | Quota limit reached | Request quota increase |
| `OperationDenied` | Operation not allowed | Check permissions or state |

## Debug Steps

1. **Verify DC status**:
   ```bash
   tccli dc DescribeDirectConnects \
     --Filters "Name=direct-connect-id,Values=dc-xxx"
   ```

2. **Check tunnel health**:
   ```bash
   tccli dc DescribeDirectConnectTunnels \
     --Filters "Name=direct-connect-id,Values=dc-xxx"
   ```

3. **Verify BGP status** (for BGP tunnels):
   ```bash
   # Check BGP session state in tunnel details
   tccli dc DescribeDirectConnectTunnelExtra \
     --DirectConnectTunnelId dct-xxx
   ```

4. **Test connectivity**:
   ```bash
   # From on-premise, ping VPC CIDR
   ping <vpc-cidr-gateway-ip>
   ```

5. **Check route tables**:
   ```bash
   tccli vpc DescribeRouteTables \
     --Filters "Name=route-table-id,Values=rtb-xxx"
   ```

## Failover Failure Patterns & Recovery

| Symptom | Likely Cause | Recovery |
|---------|-------------|----------|
| Automatic failover did not trigger | BFD/NQA not enabled on tunnel | Enable via `ModifyDirectConnectTunnelExtra --BfdEnable 1 --NqaEnable 1`; verify with `DescribeDirectConnectTunnelExtra` |
| Backup tunnel unhealthy at switch time | Backup provisioning incomplete | Wait for `State=AVAILABLE` before `FailoverSwitch`; never withdraw primary first |
| Full outage after manual switch | Primary withdrawn, backup not carrying traffic | Restore primary routes (`ImportDirectRoute true`); verify BGP session on backup |
| Health check flapping | Probe interval too aggressive | Increase `ProbeInterval` / `ProbeThreshold` in `BfdInfo`/`NqaInfo` |
| Cloud attach not routing | CCN not attached / routes not propagated | Delegate to `qcloud-ccn-ops`: verify `AttachCcnInstances` and route tables |
