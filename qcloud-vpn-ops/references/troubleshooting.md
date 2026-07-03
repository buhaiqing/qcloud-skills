# VPN Troubleshooting

## Symptom: Tunnel stays in `PENDING` (never reaches `AVAILABLE`)

| Cause | Fix |
|---|---|
| Peer device not yet configured with the Tencent side's public IP and PSK | Share `vgw.public_ip` and the PSK with the on-prem operator; have them complete the config. |
| IKE version mismatch | Confirm both sides use the same `IkeVersion` (e.g., IKEv2). |
| PSK mismatch (one side has a typo) | Re-set the PSK on both sides; rotate the secret if it has been compromised. |
| Local / remote CIDR mismatch (cloud sees `10.0.0.0/16`, peer sees `10.0.0.0/24`) | Re-confirm `LocalCidrBlocks` and `RemoteCidrBlocks` on both sides; recreate the tunnel if needed. |
| UDP 500 / 4500 blocked by the on-prem firewall | Have the on-prem operator open UDP 500 and UDP 4500; many corporate firewalls block them by default. |

## Symptom: Tunnel reaches `AVAILABLE` then drops to `DOWN`

| Cause | Fix |
|---|---|
| Re-key lifetime too aggressive for the peer | Increase `IKESaLifetimeSeconds` and `IpsecSaLifetimeSeconds` on both sides. |
| Peer device NAT-traversal misconfigured | Enable NAT-T (`EnableNatTraversal = True`) on both sides. |
| On-prem ISP dropped the keep-alive | Some ISPs idle-drop UDP flows. Configure DPD (Dead Peer Detection) with a short interval. |

## Symptom: `DeleteVpnConnection` returns `ResourceInUse`

| Cause | Fix |
|---|---|
| Health check still running | Wait 30 s and retry. |
| Route table still references the connection | Remove the route in the VPC route table (`qcloud-vpc-ops`), then retry. |

## Symptom: `DeleteVpnGateway` returns `ResourceInUse.VpnGateway`

| Cause | Fix |
|---|---|
| VPN Connections still attached | `DescribeVpnConnections` filtered by `VpnGatewayId`; `DeleteVpnConnection` for each, then retry. |
| SSL VPN Server still attached | `DescribeVpnGatewaySslServers`; `DeleteVpnGatewaySslServers` for each, then retry. |

## Symptom: SSL client cannot connect

| Cause | Fix |
|---|---|
| Cert expired | Re-issue with `CreateVpnGatewaySslClient`. |
| Wrong `RemoteAddress` on the SSL server | Confirm the SSL client's network matches `RemoteAddress` of the server. |
| On-prem firewall blocks the SSL port | Open the port (default UDP 1194) on the user's path. |

## Symptom: `CreateVpnConnection` returns `InvalidParameter.PreShareKeyFormat`

| Cause | Fix |
|---|---|
| PSK too short or too long | Regenerate a 16–32 char PSK and re-submit. |
| PSK contains unsupported characters | Stick to printable ASCII letters / digits / `-_.`. |
