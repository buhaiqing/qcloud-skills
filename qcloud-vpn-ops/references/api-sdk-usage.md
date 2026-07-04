# VPN API & SDK Usage

> VPN API and SDK reference.

## SDK Installation

```bash
pip install tencentcloud-sdk-python-vpc
```

Note: All VPN APIs are under the `vpc` product namespace.

## API Reference

| API | Description | CLI Example |
|-----|-------------|-------------|
| DescribeVpnConnections | Query VPN tunnel list | `tccli vpc DescribeVpnConnections` |
| CreateVpnConnection | Create VPN tunnel | `tccli vpc CreateVpnConnection` |
| DeleteVpnConnection | Delete VPN tunnel | `tccli vpc DeleteVpnConnection` |
| DescribeVpnGateways | Query VPN Gateway list | `tccli vpc DescribeVpnGateways` |
| DescribeCustomerGateways | Query Customer Gateway list | `tccli vpc DescribeCustomerGateways` |

## SDK Code Example

```python
from tencentcloud.vpc.v20170312 import VpcClient
from tencentcloud.vpc.v20170312.models import DescribeVpnConnectionsRequest

client = VpcClient(cred, region, profile)
req = DescribeVpnConnectionsRequest()
req.VpnGatewayIds = ["vpngw-12345678"]
resp = client.DescribeVpnConnections(req)
print(resp.VpnConnectionSet)
```

## See also
- [Core Concepts](core-concepts.md)
- [CLI Usage](cli-usage.md)
