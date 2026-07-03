# Migration Core Concepts

## Migration Types

Tencent Cloud MSP supports three primary migration types:

### 1. Host Migration (主机迁移)

Migrate physical or virtual servers to Tencent Cloud CVM.

- **Online Migration**: Agent-based live migration with minimal downtime
- **Offline Migration**: Image-based migration for cold workloads
- **Supported Sources**: VMware, Hyper-V, Physical servers, Other cloud platforms

### 2. Database Migration (数据库迁移)

Migrate databases using Data Transmission Service (DTS).

- **Full Migration**: One-time data migration
- **Incremental Sync**: Ongoing replication with minimal downtime
- **Supported Databases**: MySQL, PostgreSQL, MongoDB, Redis, SQL Server

### 3. Storage Migration (存储迁移)

Migrate object storage and file systems to COS.

- **COS Migration Tool**: Client-side migration tool
- **Offline Migration**: Physical device shipping for large datasets
- **Supported Sources**: AWS S3, Alibaba OSS, On-premise NAS/SAN

## Migration Lifecycle

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Assessment │ → │   Planning  │ → │ Preparation │ → │  Execution  │ → │ Validation  │
└─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
```

### Phase 1: Assessment

- Inventory source resources
- Dependency mapping
- Migration complexity analysis
- Cost estimation

### Phase 2: Planning

- Migration strategy selection
- Timeline and milestone definition
- Risk assessment and mitigation
- Rollback plan preparation

### Phase 3: Preparation

- Target infrastructure provisioning
- Network connectivity establishment
- Security configuration
- Migration tool setup

### Phase 4: Execution

- Data migration / synchronization
- Application migration
- Testing and validation
- Cutover or switchover

### Phase 5: Validation

- Data consistency checks
- Application functionality tests
- Performance validation
- Monitoring setup

## Delegation

- Target infrastructure → `qcloud-cvm-ops`, `qcloud-vpc-ops`, `qcloud-cdb-ops`
- Post-migration validation → Product-specific ops skills
- Application deployment → `qcloud-cicd-ops`
- Monitoring → `qcloud-monitor-ops`

## Security Best Practices

1. **Encryption**: Enable TLS for data in transit
2. **Credential Management**: Use temporary credentials where possible
3. **Network Security**: Use VPN or专线 for private connectivity
4. **Data Sanitization**: Remove sensitive data from test migrations
