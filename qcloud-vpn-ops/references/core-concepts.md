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

| Field | Typical value |
|---|---|
| IKE version | IKEv2 (preferred) / IKEv1 |
| Encryption | AES-256 / AES-128 |
| Integrity | SHA1 / SHA-256 |
| DH group | GROUP2 / GROUP14 / GROUP5 |
| Lifetime | 86400 s (IKE) / 3600 s (IPSec) |
| Pre-shared key | 16–32 chars, both sides must match |

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
