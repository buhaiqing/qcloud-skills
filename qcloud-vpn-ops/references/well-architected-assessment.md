# VPN Well-Architected Assessment

Read-only assessment for the VPN worker when invoked by `qcloud-well-architected-review`. Return shape matches [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md) with `product: vpn`.

## Pillar Coverage

| Pillar | What to inspect for VPN |
|---|---|
| **可靠性 (Reliability)** | Active-active or dual-tunnel setup for critical hybrid cloud links; no single-tunnel SPOF; SSL client certs within validity |
| **安全性 (Security)** | IKEv2 preferred; AES-256 + SHA-256 minimum; PSK length 16–32 chars; SSL certs not expired; no SSL clients issued to departed users |
| **成本 (Cost)** | VPN Gateway bandwidth tier matched to actual usage (via `qcloud-finops-ops`); no idle gateways with no connections |
| **效率 (Efficiency)** | Tunnels consolidated per Customer Gateway (one tunnel per peer, not many); SSL client count matches active users |

## Worker Output Contract (excerpt)

The worker MUST return `{{output.product_assessment}}` with `product: vpn`, `scope: single-resource | account-wide`, plus the canonical four-pillar `findings[]` and `summary`.

## Example `{{output.product_assessment}}`

```json
{
  "skill_id": "qcloud-vpn-ops",
  "product": "vpn",
  "region": "ap-guangzhou",
  "scope": "account-wide",
  "assessment_date": "2026-07-03T10:00:00+08:00",
  "status": "OK",
  "partial": false,
  "resource_count": 2,
  "pillars": {
    "reliability": {
      "score": 65,
      "status": "assessed",
      "findings": [
        {
          "id": "vpn-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Single-tunnel SPOF for production hybrid cloud link",
          "evidence": "Only one IPSec connection on vpn-gateway-prod-1; no active-active / dual-tunnel partner",
          "recommendation": "Add a second tunnel to the same peer on a second VPN gateway for active-active failover",
          "effort": "major"
        }
      ]
    },
    "security": {
      "score": 78,
      "status": "assessed",
      "findings": [
        {
          "id": "vpn-sec-001",
          "severity": "Medium",
          "confidence": "HIGH",
          "title": "IKEv1 in use on a legacy tunnel",
          "evidence": "vpnx-legacy uses IkeVersion=IKEV1; IKEv2 is the current minimum",
          "recommendation": "Recreate the connection with IKEv2 and re-coordinate with the on-prem operator",
          "effort": "medium"
        }
      ]
    },
    "cost": {
      "score": 80,
      "status": "assessed",
      "findings": []
    },
    "efficiency": {
      "score": 85,
      "status": "assessed",
      "findings": []
    }
  },
  "recommendations": [
    {
      "priority": 1,
      "pillar": "reliability",
      "action": "Add an active-active partner tunnel for vpn-gateway-prod-1",
      "effort": "major"
    },
    {
      "priority": 2,
      "pillar": "security",
      "action": "Recreate vpnx-legacy with IKEv2",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [
      "tccli vpc DescribeVpnGateways --Region ap-guangzhou",
      "tccli vpc DescribeVpnConnections --Region ap-guangzhou",
      "tccli vpc DescribeCustomerGateways --Region ap-guangzhou",
      "tccli vpc DescribeVpnGatewaySslClients --Region ap-guangzhou"
    ]
  },
  "errors": []
}
```
