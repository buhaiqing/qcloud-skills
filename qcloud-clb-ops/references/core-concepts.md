# CLB Core Concepts

## Overview

CLB (Cloud Load Balancer, 负载均衡) provides traffic distribution across multiple backend servers, eliminating single points of failure and improving service availability.

## Instance Types

| Type | Description | Use Case |
|------|-------------|----------|
| **公网型 (OPEN)** | Public network load balancer with public IP | Web services, public APIs |
| **内网型 (Internal)** | Internal network load balancer with private IP | Internal services, microservices |

## Architecture Components

### LoadBalancer (实例)
- Primary resource containing configuration
- Bound to VPC and subnet
- Has VIP (virtual IP) for traffic ingress

### Listener (监听器)
- Defines protocol and port for traffic handling
- Protocols: TCP, UDP, HTTP, HTTPS, TCP SSL
- Each LB can have multiple listeners

### Backend Server / Target (后端服务器)
- CVM instances or ENIs receiving traffic
- Bound to listeners via port and weight
- Health check determines traffic routing

### Target Group (目标组)
- Logical grouping of backend servers
- Enables flexible management and scaling

## Protocol Comparison

| Protocol | Layer | Features | Best For |
|----------|-------|----------|----------|
| **TCP** | Layer 4 | High performance, health check | Games, database, non-HTTP |
| **UDP** | Layer 4 | UDP traffic, QUIC support | VoIP, video streaming |
| **HTTP** | Layer 7 | URL routing, header manipulation | Web applications, APIs |
| **HTTPS** | Layer 7 | SSL/TLS termination | Secure web services |
| **TCP SSL** | Layer 4+7 | SSL passthrough | End-to-end encryption |

## Health Check

| Protocol | Check Method | Parameters |
|----------|--------------|------------|
| TCP | TCP connect | Timeout: 2s, Interval: 5s |
| UDP | UDP packet + response | Custom check domain |
| HTTP | HTTP GET | Path, domain, status code |
| HTTPS | HTTPS GET | SSL certificate validation |

## Limits and Quotas

| Resource | Default Limit |
|----------|---------------|
| LoadBalancer instances per region | 50 |
| Listeners per LB | 50 |
| Backend servers per listener | 100 |
| Target groups per region | 50 |

## Region and Zone Support

CLB supports:
- Cross-zone binding: Backend servers across zones
- Cross-region binding: Anycast CLB for global access
- IPv6 support: IPv6-only or dual-stack

## Common Patterns

### High Availability
- Multi-zone backend deployment
- Multiple CLB instances for redundancy
- Health check with auto-recovery

### SSL Termination
- HTTPS listener with SSL certificate
- Backend uses HTTP (internal network)
- Offload encryption at CLB layer

### Session Persistence
- Layer 4: Source IP hash
- Layer 7: Cookie-based persistence
- Application-controlled via headers

## Integration Points

- **VPC**: Required network context
- **CVM**: Backend server instances
- **Security Groups**: Traffic filtering
- **SSL Certificates**: HTTPS listener requirement
- **CAM**: Permission control

## Dependency Graph

```
LoadBalancer
├── VPC (required)
│   └── Subnet (required)
├── Security Group (optional)
├── Listener(s)
│   ├── Protocol/Port
│   ├── SSL Certificate (HTTPS)
│   └── Backend Servers/Targets
│       ├── CVM Instance (delegate to qcloud-cvm-ops)
│       ├── Port/Weight
│       └── Health Check
└── Target Groups (optional)
```