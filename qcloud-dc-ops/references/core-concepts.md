# Direct Connect Core Concepts

## Architecture

Tencent Cloud Direct Connect (DC) establishes dedicated network connections:

- **Physical Dedicated Line**: Physical fiber connection from customer DC to Tencent Cloud access point
- **Direct Connect Tunnel**: Logical tunnel over the physical line (BGP or static routing)
- **Direct Connect Gateway**: VPC-side gateway for DC connectivity
- **Access Point**: Tencent Cloud facility for physical connection

## Connection Models

### Model 1: Dedicated Physical Line
```
Customer DC → Physical Fiber → Tencent Access Point → DC Gateway → VPC
```

### Model 2: Shared Partner Line
```
Customer DC → Partner Network → Tencent Access Point → DC Gateway → VPC
```

## Resource Hierarchy

1. **Direct Connect** (物理专线)
   - Physical connection resource
   - Bandwidth: 1Gbps - 100Gbps
   - State: PENDING → AVAILABLE → DELETING

2. **Direct Connect Tunnel** (专用通道)
   - Logical tunnel over physical line
   - Routing: BGP or Static
   - State: PENDING → AVAILABLE

3. **Direct Connect Gateway** (专线网关)
   - VPC attachment point
   - Types: Standard, NAT

## Resource Limits

| Resource | Default Limit |
|----------|--------------|
| Direct Connects per account | 10 |
| Tunnels per DC | 10 |
| Gateways per VPC | 5 |
| Bandwidth options | 1G/10G/100Gbps |

## Delegation

- VPN backup → `qcloud-vpn-ops`
- CCN cloud networking → `qcloud-ccn-ops`
- VPC configuration → `qcloud-vpc-ops`
- Cross-region peering → `qcloud-ccn-ops`

## Security Best Practices

1. **Physical Security**: Use partner facilities if direct access unavailable
2. **Redundancy**: Deploy dual DC connections for high availability
3. **Encryption**: Use MACsec for Layer 2 encryption (if supported)
4. **Access Control**: Restrict DC modification permissions via CAM
