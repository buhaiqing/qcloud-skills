# VPN AIOps Best Practices

> VPN intelligent operations and anomaly detection patterns.

## Monitoring Integration

VPN monitoring relies on Tencent Cloud Monitor (QCloud Monitor). Use `qcloud-monitor-ops` for alarm configuration and metric queries.

### Key Metrics

| Metric | Namespace | Dimension | Description | Alarm Threshold |
|--------|-----------|-----------|-------------|-----------------|
| `VpnTunnelState` | `QCE/VPC` | `VpnConnectionId` | Tunnel state (1=up, 0=down) | State=0 for >5 min |
| `VpnTunnelInBandwidth` | `QCE/VPC` | `VpnConnectionId` | Inbound bandwidth (Mbps) | Anomaly detection |
| `VpnTunnelOutBandwidth` | `QCE/VPC` | `VpnConnectionId` | Outbound bandwidth (Mbps) | Anomaly detection |
| `VpnTunnelInPkg` | `QCE/VPC` | `VpnConnectionId` | Inbound packets/s | Packet loss detection |
| `VpnTunnelOutPkg` | `QCE/VPC` | `VpnConnectionId` | Outbound packets/s | Packet loss detection |
| `VpnTunnelDropPkg` | `QCE/VPC` | `VpnConnectionId` | Dropped packets/s | >0 indicates issue |

### Query Metrics via CLI

```bash
# Get tunnel state for the last hour
tccli monitor GetMonitorData \
  --Namespace QCE/VPC \
  --MetricName VpnTunnelState \
  --Dimensions '[{"Name":"VpnConnectionId","Value":"vpnx-xxx"}]' \
  --Period 60 \
  --StartTime "$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### Query via SDK

```python
from tencentcloud.monitor.v20180724 import models as monitor_models

monitor_client = monitor_client.MonitorClient(cred, region)

req = monitor_models.GetMonitorDataRequest()
req.Namespace = "QCE/VPC"
req.MetricName = "VpnTunnelState"
req.Dimensions = [{"Name": "VpnConnectionId", "Value": "vpnx-xxx"}]
req.Period = 60
req.StartTime = "2026-07-09T10:00:00Z"
req.EndTime = "2026-07-09T11:00:00Z"

resp = monitor_client.GetMonitorData(req)
for point in resp.DataPoints:
    print(f"Timestamp: {point.Timestamps}, Value: {point.Values}")
```

## Anomaly Detection Patterns

### 1. Tunnel Flapping Detection

Tunnel that transitions between AVAILABLE and DOWN more than N times in a time window indicates unstable peer or network.

```bash
# Check tunnel state history (requires CloudAudit or CLS integration)
# This is a conceptual pattern — actual implementation depends on log retention
tccli cls GetLogList \
  --TopicId "xxx" \
  --Query 'VpnConnectionId:vpnx-xxx AND (State:AVAILABLE OR State:DOWN)' \
  --FromTime "$(date -d '1 hour ago' +%s)" \
  --ToTime "$(date +%s)"
```

### 2. Bandwidth Saturation Detection

Alert when bandwidth usage exceeds 80% of gateway capacity.

```bash
# Get bandwidth utilization
tccli monitor GetMonitorData \
  --Namespace QCE/VPC \
  --MetricName VpnTunnelOutBandwidth \
  --Dimensions '[{"Name":"VpnConnectionId","Value":"vpnx-xxx"}]' \
  --Period 300 \
  --StartTime "$(date -u -d '5 min ago' +%Y-%m-%dT%H:%M:%SZ)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%SZ)" | \
  jq '.DataPoints[0].Values[] | select(. > 80)'
```

### 3. Packet Loss Detection

Dropped packets indicate MTU mismatch, firewall filtering, or peer device issues.

```bash
tccli monitor GetMonitorData \
  --Namespace QCE/VPC \
  --MetricName VpnTunnelDropPkg \
  --Dimensions '[{"Name":"VpnConnectionId","Value":"vpnx-xxx"}]' \
  --Period 60 \
  --StartTime "$(date -u -d '10 min ago' +%Y-%m-%dT%H:%M:%SZ)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

## Auto-Healing Patterns

### Pattern 1: Tunnel Auto-Recovery

When tunnel state is DOWN for >5 min:

1. **Diagnose**: Check peer device reachability, PSK validity, crypto policy match
2. **Notify**: Alert on-call via `qcloud-monitor-ops` alarm callback
3. **Recover**: If peer-side issue confirmed, wait for peer fix; if cloud-side issue, recreate tunnel with correct parameters

```bash
# Check if peer IP is reachable (run from VPC)
ping -c 3 {{user.peer_public_ip}}

# Verify tunnel configuration
tccli vpc DescribeVpnConnections \
  --VpnConnectionIds "[\"vpnx-xxx\"]" | \
  jq '.Response.VpnConnectionSet[0] | {State, LocalCidrBlocks, RemoteCidrBlocks}'
```

### Pattern 2: Gateway Bandwidth Auto-Scaling

For VPN gateways with predictable traffic patterns:

```bash
# Analyze peak traffic hours
tccli monitor GetMonitorData \
  --Namespace QCE/VPC \
  --MetricName VpnTunnelOutBandwidth \
  --Dimensions '[{"Name":"VpnGatewayId","Value":"vpngw-xxx"}]' \
  --Period 3600 \
  --StartTime "$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Upgrade bandwidth before peak (manual or via scheduled task)
tccli vpc ModifyVpnGatewayAttribute \
  --VpnGatewayId "vpngw-xxx" \
  --Bandwidth 200
```

## Integration with `qcloud-monitor-ops`

### Create Alarm Policy for VPN Tunnel Down

```bash
# Delegate to qcloud-monitor-ops for alarm creation
# The following is the policy structure to pass

POLICY='{
  "PolicyName": "VPN-Tunnel-Down",
  "Module": "monitor",
  "Namespace": "QCE/VPC",
  "MetricName": "VpnTunnelState",
  "Condition": {
    "CalcType": 1,
    "CalcValue": 0,
    "ContinueTime": 300
  },
  "AlarmReceivers": {
    "ReceiverType": "USER",
    "ReceiverIdList": ["user-xxx"]
  }
}'

# Use qcloud-monitor-ops skill to create this policy
```

### Create Alarm Policy for Bandwidth Saturation

```bash
POLICY='{
  "PolicyName": "VPN-Bandwidth-Saturation",
  "Module": "monitor",
  "Namespace": "QCE/VPC",
  "MetricName": "VpnTunnelOutBandwidth",
  "Condition": {
    "CalcType": 2,
    "CalcValue": 80,
    "ContinueTime": 300
  }
}'
```

## Predictive Maintenance

### PSK Rotation Schedule

Track PSK age and trigger rotation alerts:

```bash
# Query tunnel creation time
tccli vpc DescribeVpnConnections \
  --VpnConnectionIds "[\"vpnx-xxx\"]" | \
  jq -r '.Response.VpnConnectionSet[0].CreatedTime'

# If CreatedTime > 90 days, trigger PSK rotation workflow
```

### SSL Client Cert Expiry Detection

```bash
# Query SSL client cert validity
tccli vpc DescribeVpnGatewaySslClients \
  --Filters "Name=ssl-vpn-server-id,Values=sslvpns-xxx" | \
  jq '.Response.SslVpnClientSet[] | {SslVpnClientId, SslVpnClientName, CreatedTime}'
```

## See also
- [Core Concepts](core-concepts.md)
- [Troubleshooting](troubleshooting.md)
- [qcloud-monitor-ops](../../qcloud-monitor-ops/SKILL.md) — Alarm policy creation and metric queries
- [qcloud-aiops-diagnosis](../../qcloud-aiops-diagnosis/SKILL.md) — Cross-product anomaly diagnosis
