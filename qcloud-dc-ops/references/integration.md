# Integration Guide

## SDK Setup

```bash
pip install tencentcloud-sdk-python
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TENCENTCLOUD_SECRET_ID` | Yes | API Secret ID |
| `TENCENTCLOUD_SECRET_KEY` | Yes | API Secret Key |
| `TENCENTCLOUD_REGION` | Yes | Region (e.g., ap-guangzhou) |

## Cross-Skill Delegation

| Scenario | Delegate To |
|----------|------------|
| VPN backup configuration | `qcloud-vpn-ops` |
| CCN cloud networking | `qcloud-ccn-ops` |
| VPC route table config | `qcloud-vpc-ops` |
| Cross-region peering | `qcloud-ccn-ops` |
| Monitor DC metrics | `qcloud-monitor-ops` |

## Hybrid Cloud Integration Example

```python
#!/usr/bin/env python3
"""
Example: Hybrid cloud setup with DC + VPN backup
"""
import os
from tencentcloud.common import credential

# 1. Create DC connection (this skill)
# - CreateDirectConnect
# - CreateDirectConnectTunnel
# - CreateDirectConnectGateway

# 2. Configure VPN backup (delegate to qcloud-vpn-ops)
# - CreateVpnGateway
# - CreateVpnConnection

# 3. Configure VPC routing (delegate to qcloud-vpc-ops)
# - Configure route tables with DC as primary, VPN as backup
```

## Best Practices

1. **High Availability**: Always deploy dual DC connections
2. **Monitoring**: Integrate with `qcloud-monitor-ops` for alerting
3. **Documentation**: Maintain accurate network topology diagrams
4. **Testing**: Regular failover testing to verify backup paths
