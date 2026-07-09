# VPN Core Concepts

## What is Tencent Cloud VPN

Tencent Cloud VPN provides encrypted hybrid cloud connectivity. Two flavors:

- **IPSec VPN** — site-to-site encrypted tunnel between a Tencent VPC and an on-prem / remote network. Always-on, used for steady hybrid cloud traffic.
- **SSL VPN** — remote-access VPN. Individual users (telecommuters, O&M engineers) connect to a VPC using an SSL VPN client.

## Components

| Component | Description | Scope |
|---|---|---|
| **VPN Gateway** | The cloud-side endpoint, lives inside a VPC. Charges an hourly fee plus bandwidth. | Per VPC |
| **IPSec VPN Connection** (a.k.a. VPN Tunnel) | The encrypted tunnel between a VPN Gateway and a Customer Gateway. | Per peer device |
| **Customer Gateway** | The **logical** representation of the on-prem / peer device. Needs only the peer's public IP and a name. | Per peer device |
| **SSL VPN Server** | A server that runs on a VPN Gateway and listens for SSL VPN client connections. | Per remote-access scenario |
| **SSL VPN Client** | A cert + profile issued by an SSL VPN Server. One per remote user. | Per user |

```
                 ┌──────────────────────────────────┐
                 │       Tencent Cloud VPC          │
                 │                                  │
                 │  ┌────────────┐                  │
                 │  │ VPN        │                  │
                 │  │ Gateway    │                  │
                 │  └─────┬──────┘                  │
                 │        │                         │
                 │  ┌─────▼──────┐  ┌────────────┐   │
                 │  │ IPSec      │  │ SSL VPN    │   │
                 │  │ Tunnel     │  │ Server     │   │
                 │  └─────┬──────┘  └─────┬──────┘   │
                 └────────│───────────────│──────────┘
                          │               │
                  ════════│═══════════════│═════════ encrypted
                          │               │
                  ┌───────▼─────┐    ┌────▼───────┐
                  │ On-prem     │    │ Remote     │
                  │ firewall    │    │ user       │
                  │ (Customer   │    │ (SSL VPN   │
                  │  Gateway)   │    │  client)   │
                  └─────────────┘    └────────────┘
```

## Crypto Policy

The IKE / IPSec policy (encryption algo, integrity, DH group, lifetime) must match on both sides of the tunnel. The most common cause of a tunnel staying in `DOWN` state is policy mismatch — the cloud side and the on-prem device are configured with different IKE versions, different encryption algorithms, or different PSKs.

### IKE Policy Parameters

| Parameter | Recommended | Acceptable | Legacy (avoid) |
|-----------|-------------|------------|----------------|
| IKE Version | IKEv2 | IKEv1 (interoperability) | — |
| Encryption | AES-256 | AES-128 | 3DES |
| Authentication | SHA-256 | SHA1 | MD5 |
| DH Group | GROUP14 (2048-bit) | GROUP2, GROUP5 | GROUP1 |
| Lifetime (IKE SA) | 86400s (24h) | 28800s–86400s | <28800s |

### IPSec Policy Parameters

| Parameter | Recommended | Acceptable | Notes |
|-----------|-------------|------------|-------|
| Encryption | AES-256 | AES-128 | Match IKE encryption |
| Authentication | SHA-256 | SHA1 | Match IKE authentication |
| PFS (Perfect Forward Secrecy) | Enabled (DH Group 14) | Disabled | Recommended for high-security |
| Lifetime (IPSec SA) | 3600s (1h) | 1800s–3600s | Shorter = more re-key overhead |

### Pre-Shared Key (PSK) Requirements

| Requirement | Value |
|-------------|-------|
| Length | 16–32 characters |
| Characters | Printable ASCII (letters, digits, `-_.`) |
| Rotation | Every 90 days (recommended) |
| Storage | NEVER log, echo, or commit to version control |

> **Security best practices**: See [secops-security-operations.md](secops-security-operations.md) for the complete security checklist.

## Tunnel State Machine

```
PENDING ─────► AVAILABLE ◄────► DOWN (transient, e.g. re-key)
                  │
                  └──────► DELETING ──► DELETED
```

A `DOWN` for > 5 minutes is alertable — see [troubleshooting.md](troubleshooting.md).

## Pricing

| Cost item | Notes |
|---|---|
| VPN Gateway hourly fee | Charged per gateway, per hour, by bandwidth tier |
| Inter-region traffic | Outbound traffic is billed; inbound is free |
| SSL VPN | No extra fee beyond the gateway's hourly fee |

> Use the billing console for the latest unit prices; the agent should never hardcode prices.

## Quotas

| Resource | Adjustable |
|---|---|
| VPN Gateways per VPC | Yes |
| IPSec Connections per Gateway | Yes |
| SSL VPN Servers per Gateway | Yes |
| SSL VPN Clients per Server | Yes |

## References

- [VPN Documentation](https://cloud.tencent.com/document/product/554)
- [IPSec VPN Limits](https://cloud.tencent.com/document/product/554/19288)
- [SSL VPN Documentation](https://cloud.tencent.com/document/product/554/34952)
