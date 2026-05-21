# VPC Core Concepts

## Architecture Overview

Tencent Cloud VPC (Virtual Private Cloud) provides an isolated virtual network environment where you can launch Tencent Cloud resources (CVM instances, CLB, databases) in a defined network topology.

### Key Components

| Component | Function | Limits |
|-----------|----------|--------|
| **VPC** | Isolated network container | 5 per region (default quota) |
| **Subnet** | Network segment within VPC | 100 per VPC |
| **Route Table** | Traffic routing rules | 50 per VPC |
| **Network ACL** | Subnet-level firewall | Default ACL per VPC |
| **Security Group** | Instance-level firewall | 50 per region |
| **NAT Gateway** | Outbound internet access | 1 per VPC (default) |
| **VPN Gateway** | Hybrid cloud connection | 1 per VPC |
| **Direct Connect** | Dedicated line connection | Per subscription |

## CIDR Planning

### Recommended CIDR Ranges

| Network Type | Recommended CIDR | Example |
|--------------|------------------|---------|
| Development | `10.0.0.0/16` - `10.255.0.0/16` | 65,536 IPs |
| Production | `172.16.0.0/16` - `172.31.0.0/16` | 65,536 IPs |
| Large Scale | `192.168.0.0/16` | 65,536 IPs |

### Subnet CIDR Subdivision

| Subnet Purpose | CIDR Example | IP Count |
|----------------|--------------|----------|
| Web tier | `10.0.1.0/24` | 256 IPs |
| App tier | `10.0.2.0/24` | 256 IPs |
| Database | `10.0.3.0/24` | 256 IPs |
| Management | `10.0.100.0/24` | 256 IPs |

### CIDR Allocation Best Practices

1. Reserve first 10% of CIDR for infrastructure
2. Allocate subnet CIDRs in multiples of `/24`
3. Leave gaps for future expansion
4. Avoid overlapping with on-premise networks

## Region and Zone Coverage

### Supported Regions

| Region | Code | Zones |
|--------|------|-------|
| 广州 | `ap-guangzhou` | 1, 2, 3, 4, 6, 7 |
| 上海 | `ap-shanghai` | 1, 2, 3, 4, 5 |
| 北京 | `ap-beijing` | 1, 2, 3, 4, 5, 6, 7, 8 |
| 成都 | `ap-chengdu` | 1, 2 |
| 重庆 | `ap-chongqing` | 1 |
| 深圳 | `ap-shenzhen-fsi` | 1, 2, 3, 4 |
| 南京 | `ap-nanjing` | 1, 2 |
| 香港 | `ap-hongkong` | 1, 2, 3 |
| 新加坡 | `ap-singapore` | 1, 2, 3 |
| 东京 | `ap-tokyo` | 1, 2 |
| 雅加达 | `ap-jakarta` | 1, 2 |

### Multi-AZ Subnet Strategy

```
VPC (10.0.0.0/16)
├── Subnet-Web-AZ1 (10.0.1.0/24) - ap-guangzhou-1
├── Subnet-Web-AZ2 (10.0.2.0/24) - ap-guangzhou-2
├── Subnet-App-AZ1 (10.0.3.0/24) - ap-guangzhou-1
├── Subnet-App-AZ2 (10.0.4.0/24) - ap-guangzhou-2
├── Subnet-DB-AZ1 (10.0.5.0/24) - ap-guangzhou-1
├── Subnet-DB-AZ2 (10.0.6.0/24) - ap-guangzhou-2
```

## Resource Relationships

### Dependency Graph

```
VPC
  ├── Subnet (requires: VPC, Zone)
  │     ├── CVM Instance (requires: Subnet)
  │     ├── CLB (requires: Subnet)
  │     ├── MySQL (requires: Subnet)
  │     └── Redis (requires: Subnet)
  ├── Route Table (requires: VPC)
  │     └── Routes (requires: Route Table, NextHop)
  ├── Network ACL (requires: VPC)
  │     └── Subnet Association (requires: ACL, Subnet)
  ├── Security Group (standalone)
  │     └── CVM Association (requires: SG, CVM)
  ├── NAT Gateway (requires: VPC, Subnet, EIP)
  ├── VPN Gateway (requires: VPC)
  │     ├── VPN Connection (requires: VPN Gateway, CGW)
  │     └── Customer Gateway (standalone)
  ├── Peering Connection (requires: VPC, Peer VPC)
  └── Direct Connect Gateway (requires: VPC)
```

### Resource Lifecycle Sequence

1. **Create VPC** → defines network boundary
2. **Create Subnets** → divide into zones/segments
3. **Create Route Tables** → define routing rules
4. **Create Network ACLs** → subnet-level firewall
5. **Create Security Groups** → instance-level firewall
6. **Launch CVM/CLB/DB** → deploy compute resources
7. **Configure NAT/VPN** → enable connectivity

## Quotas and Limits

### Default Quotas

| Resource | Default Limit | Adjustable |
|----------|---------------|------------|
| VPCs per region | 5 | Yes (max 20) |
| Subnets per VPC | 100 | Yes |
| Route tables per VPC | 50 | Yes |
| Network ACLs per VPC | 50 | Yes |
| Security groups per region | 50 | Yes |
| NAT gateways per VPC | 1 | Yes |
| VPN gateways per VPC | 1 | Yes |
| Peering connections per VPC | 10 | Yes |

### IP Address Limits

| Resource | Limit |
|----------|-------|
| Minimum subnet CIDR | `/28` (16 IPs) |
| Maximum subnet CIDR | `/16` (65,536 IPs) |
| VPC CIDR range | `/16` to `/28` |
| Reserved IPs per subnet | First 4 IPs |

## Connectivity Options

### Internet Access Methods

| Method | Use Case | Cost |
|--------|----------|------|
| **EIP + CVM** | Direct public IP on instance | EIP hourly fee |
| **NAT Gateway** | Shared outbound for subnet | NAT gateway fee + bandwidth |
| **CLB** | Inbound traffic distribution | CLB instance fee |

### Hybrid Cloud Connectivity

| Method | Bandwidth | Latency | Cost |
|--------|-----------|---------|------|
| **VPN Gateway** | 100Mbps default | Higher | VPN gateway fee |
| **Direct Connect** | Up to 10Gbps | Lowest | Dedicated line fee |
| **CCN (Cloud Connect Network)** | Flexible | Medium | CCN fee |

### VPC Peering

| Scenario | Configuration |
|----------|---------------|
| Cross-region peering | Requires CCN |
| Same-region peering | Direct peering connection |
| Cross-account peering | Requires account approval |

## Security Model

### Network ACL vs Security Group

| Feature | Network ACL | Security Group |
|---------|-------------|----------------|
| Level | Subnet | Instance |
| Stateful | No (separate inbound/outbound) | Yes |
| Rule priority | Low to high number | All rules evaluated |
| Default behavior | Deny all inbound, Allow all outbound | Allow all outbound, Deny inbound |

### Recommended ACL Rules

**Production Web Tier ACL:**
```
Inbound:
- Allow HTTP (80) from 0.0.0.0/0
- Allow HTTPS (443) from 0.0.0.0/0
- Allow SSH (22) from management subnet
- Deny all else

Outbound:
- Allow HTTP/HTTPS to app tier
- Allow DNS (53) to 0.0.0.0/0
- Allow all else
```

## Monitoring and Observability

### Flow Logs

- Capture VPC traffic metadata
- Store in COS bucket
- Enable per VPC/Subnet level
- Cost: storage + processing fee

### Key Metrics

| Metric | Alert Threshold |
|--------|-----------------|
| VPC bandwidth | >80% of limit |
| NAT gateway connections | >1000 concurrent |
| VPN tunnel status | Down for >5min |

## Design Patterns

### Three-Tier Architecture

```
Internet → CLB → Web Tier (Subnet-AZ1, AZ2)
                    ↓
               App Tier (Subnet-AZ1, AZ2)
                    ↓
               DB Tier (Subnet-AZ1, AZ2, Multi-AZ DB)
```

### Microservices Network

```
VPC
├── Service Mesh Subnet (10.0.0.0/20)
├── API Gateway Subnet (10.0.16.0/24)
├── Service A Subnet (10.0.32.0/24)
├── Service B Subnet (10.0.48.0/24)
├── Shared DB Subnet (10.0.64.0/24)
├── Monitoring Subnet (10.0.80.0/24)
```

## References

- [VPC Documentation](https://cloud.tencent.com/document/product/215)
- [CIDR Planning Guide](https://cloud.tencent.com/document/product/215/32801)
- [VPC Limits](https://cloud.tencent.com/document/product/215/537)