# Cloud Resource Skills Inventory

**Document Version:** 1.0  
**Last Updated:** 2026-05-27  
**Purpose:** Comprehensive mapping of Alibaba Cloud resource analysis skills to their underlying MCP tools

---

## Section 1: Existing Alibaba Cloud Resource Skills

This section documents the 6 existing Alibaba Cloud resource analysis skills, their mapped tools, status, and primary use cases.

### 1.1 Individual Resource Skills

| Skill Name | Resource Type | Primary Tool | Status | Key Use Cases |
|:-----------|:--------------|:-------------|:-------|:--------------|
| `ecs-analysis-aliyun` | ECS (Elastic Compute Service) | `get_ali_ecs_info` | ✅ Active | • Instance inventory and resource盘点<br>• Performance analysis and optimization<br>• Cost assessment and right-sizing recommendations<br>• Expiration tracking and capacity planning |
| `elasticsearch-analysis-aliyun` | Elasticsearch | `get_ali_elasticsearch_info_metrics` | ✅ Active | • Cluster performance analysis<br>• Storage optimization<br>• Shard distribution and balancing<br>• Resource utilization assessment |
| `mongodb-analysis-aliyun` | MongoDB | `get_ali_mongodb_info_metrics` | ✅ Active | • Instance performance metrics analysis<br>• Storage usage optimization<br>• Connection bottleneck identification<br>• Resource capacity planning |
| `redis-analysis-aliyun` | Redis | `get_ali_redis_info_metrics` | ✅ Active | • Memory usage analysis and optimization<br>• Performance bottleneck identification<br>• Connection pool monitoring<br>• Resource utilization assessment |

### 1.2 Composite Resource Skills

| Skill Name | Resource Type | Primary Tools | Status | Key Use Cases |
|:-----------|:--------------|:--------------|:-------|:--------------|
| `crm-cruise-aliyun` | Multi-Resource (CRM) | Multiple tools including:<br>• `get_ali_rds_mysql_info_metrics`<br>• `get_ali_redis_info_metrics`<br>• `get_ali_ecs_info`<br>• `get_k8s_core_metrics`<br>• `get_ka_project_summary` | ✅ Active | • Comprehensive CRM system health check<br>• Multi-resource correlation analysis<br>• Performance bottleneck identification across stack<br>• Proactive monitoring and alerting |
| `erp-cruise-aliyun` | Multi-Resource (ERP) | Multiple tools including:<br>• `get_ali_rds_mysql_info_metrics`<br>• `get_ali_redis_info_metrics`<br>• `get_ali_ecs_info`<br>• `get_ka_erp_*` JVM analysis tools<br>• `get_k8s_*` cluster metrics | ✅ Active | • End-to-end ERP system performance analysis<br>• JVM-specific diagnostics (GC, threads, heap)<br>• Container restart analysis<br>• Multi-layer infrastructure assessment |

### 1.3 Existing Skills Summary Statistics

| Category | Count | Percentage |
|:---------|------:|-----------:|
| Individual Resource Skills | 4 | 66.7% |
| Composite/Multi-Resource Skills | 2 | 33.3% |
| **Total Existing Skills** | **6** | **100%** |

---

## Section 2: Unmapped Alibaba Cloud Tools

This section lists the 7 Alibaba Cloud MCP tools that currently do **not** have dedicated skills mapped to them. These represent opportunities for skill development.

### 2.1 Unmapped Tools Detail

| # | Tool Name | Resource Type | Function Description | Business Importance |
|:-:|:----------|:--------------|:---------------------|:--------------------|
| 1 | `get_ali_slb_info_metrics` | SLB (Server Load Balancer) | Retrieves core metrics for SLB instances including upstream 4xx/5xx status codes, active connections, and dropped connections. Supports resource usage analysis and identifies potential load balancing issues. | **High** - Critical for traffic routing health and availability monitoring |
| 2 | `get_ali_rds_mysql_info` | RDS MySQL | Fetches RDS MySQL instance metadata including instance IDs, names, specifications, and expiration dates. Provides foundational inventory data without performance metrics. | **Medium** - Important for asset management and lifecycle tracking |
| 3 | `get_ali_rds_mysql_info_metrics` | RDS MySQL | Retrieves comprehensive performance metrics for RDS MySQL instances including CPU, memory, IOPS, and storage utilization. Enables deep performance analysis. | **High** - Essential for database performance optimization and capacity planning |
| 4 | `get_ali_rds_pg_info_metrics` | RDS PostgreSQL | Fetches performance metrics for RDS PostgreSQL instances similar to MySQL metrics. Supports PostgreSQL-specific performance analysis and optimization. | **Medium** - Important for PostgreSQL-based workloads |
| 5 | `get_ali_polar_mysql_info_metrics` | PolarDB MySQL | Retrieves metrics for Alibaba Cloud's PolarDB MySQL-compatible distributed database. Supports enterprise-grade distributed database analysis. | **High** - Critical for high-performance, scalable database workloads |
| 6 | `get_ali_alarm_rules` | CloudMonitor | Lists alarm rules configured for specified Alibaba Cloud accounts and resources. Enables configuration audit and alerting strategy review. | **Medium** - Important for monitoring coverage validation |
| 7 | `get_ali_alerts` | CloudMonitor | Retrieves historical alarm information and frequency statistics for resources. Supports incident analysis and alerting effectiveness assessment. | **Medium** - Valuable for operational review and incident post-mortems |

### 2.2 Unmapped Tools by Resource Category

| Category | Tools | Count |
|:---------|:------|------:|
| **Database & Storage** | `get_ali_rds_mysql_info`<br>`get_ali_rds_mysql_info_metrics`<br>`get_ali_rds_pg_info_metrics`<br>`get_ali_polar_mysql_info_metrics` | 4 |
| **Network & Load Balancing** | `get_ali_slb_info_metrics` | 1 |
| **Monitoring & Alerting** | `get_ali_alarm_rules`<br>`get_ali_alerts` | 2 |
| **Total Unmapped** | | **7** |

### 2.3 Business Importance Distribution

| Importance Level | Count | Tools |
|:-----------------|------:|:------|
| **High** | 3 | `get_ali_slb_info_metrics`, `get_ali_rds_mysql_info_metrics`, `get_ali_polar_mysql_info_metrics` |
| **Medium** | 4 | `get_ali_rds_mysql_info`, `get_ali_rds_pg_info_metrics`, `get_ali_alarm_rules`, `get_ali_alerts` |
| **Low** | 0 | - |

---

## Section 3: Gap Summary Matrix

This matrix provides a comprehensive view of the current coverage landscape, highlighting gaps and opportunities.

### 3.1 Complete Tool-to-Skill Mapping Matrix

| Resource Category | Tool Name | Has Skill? | Skill Name (if exists) | Gap Type |
|:------------------|:----------|:----------:|:-----------------------|:---------|
| **Compute** | `get_ali_ecs_info` | ✅ | `ecs-analysis-aliyun` | Covered |
| **Database - MySQL** | `get_ali_rds_mysql_info` | ❌ | - | **Gap** |
| **Database - MySQL** | `get_ali_rds_mysql_info_metrics` | ⚠️ | Used in composite skills only | **Partial Gap** |
| **Database - PostgreSQL** | `get_ali_rds_pg_info_metrics` | ❌ | - | **Gap** |
| **Database - PolarDB** | `get_ali_polar_mysql_info_metrics` | ❌ | - | **Gap** |
| **Search & Analytics** | `get_ali_elasticsearch_info_metrics` | ✅ | `elasticsearch-analysis-aliyun` | Covered |
| **NoSQL** | `get_ali_mongodb_info_metrics` | ✅ | `mongodb-analysis-aliyun` | Covered |
| **Cache** | `get_ali_redis_info_metrics` | ✅ | `redis-analysis-aliyun` | Covered |
| **Load Balancer** | `get_ali_slb_info_metrics` | ❌ | - | **Gap** |
| **Monitoring** | `get_ali_alarm_rules` | ❌ | - | **Gap** |
| **Monitoring** | `get_ali_alerts` | ❌ | - | **Gap** |

### 3.2 Coverage Summary by Resource Type

| Resource Domain | Total Tools | Covered | Partial | Uncovered | Coverage Rate |
|:----------------|------------:|--------:|--------:|----------:|--------------:|
| Compute (ECS) | 1 | 1 | 0 | 0 | 100% ✅ |
| Database (All) | 4 | 0 | 1 | 3 | 25% ⚠️ |
| ├─ MySQL | 2 | 0 | 1 | 1 | 25% ⚠️ |
| ├─ PostgreSQL | 1 | 0 | 0 | 1 | 0% ❌ |
| └─ PolarDB | 1 | 0 | 0 | 1 | 0% ❌ |
| Search (ES) | 1 | 1 | 0 | 0 | 100% ✅ |
| NoSQL (MongoDB) | 1 | 1 | 0 | 0 | 100% ✅ |
| Cache (Redis) | 1 | 1 | 0 | 0 | 100% ✅ |
| Network (SLB) | 1 | 0 | 0 | 1 | 0% ❌ |
| Monitoring | 2 | 0 | 0 | 2 | 0% ❌ |
| **TOTAL** | **11** | **4** | **1** | **6** | **36.4%** |

### 3.3 Priority Recommendations for Skill Development

| Priority | Tool(s) | Recommended Skill Name | Justification |
|:---------|:--------|:-----------------------|:--------------|
| **P0 - Critical** | `get_ali_rds_mysql_info_metrics` | `mysql-analysis-aliyun` | Most widely used database; already partially used in composite skills; high business impact |
| **P0 - Critical** | `get_ali_slb_info_metrics` | `slb-analysis-aliyun` | Critical network infrastructure component; no coverage currently |
| **P1 - High** | `get_ali_polar_mysql_info_metrics` | `polar-mysql-analysis-aliyun` | Enterprise-grade database solution; growing adoption |
| **P1 - High** | `get_ali_rds_pg_info_metrics` | `pg-analysis-aliyun` | Important for PostgreSQL workloads; similar pattern to MySQL |
| **P2 - Medium** | `get_ali_alarm_rules`<br>`get_ali_alerts` | `aliyun-monitoring-analysis` | Monitoring infrastructure; could be combined into single skill |
| **P2 - Medium** | `get_ali_rds_mysql_info` | Include in `mysql-analysis-aliyun` | Metadata tool; should be included in primary MySQL skill |

### 3.4 Gap Impact Analysis

| Impact Area | Current State | Risk Level | Recommended Action |
|:------------|:--------------|:-----------|:-------------------|
| **Database Coverage** | Only composite skills cover MySQL; no standalone DB skills | 🔴 High | Develop dedicated `mysql-analysis-aliyun` and `polar-mysql-analysis-aliyun` skills |
| **Network Visibility** | No SLB analysis capability | 🔴 High | Create `slb-analysis-aliyun` skill |
| **Observability** | No monitoring/alerting analysis | 🟡 Medium | Develop unified monitoring analysis skill |
| **Multi-DB Support** | No PostgreSQL support | 🟡 Medium | Create `pg-analysis-aliyun` skill |

---

## Appendix A: Tool Reference

### A.1 Tool Signature Quick Reference

```yaml
# Compute
tools.get_ali_ecs_info:
  params: { project, profile, start_time?, end_time? }
  returns: ECSInstanceInfo[]

# Database
tools.get_ali_rds_mysql_info:
  params: { project, profile?, product?, start_time?, end_time? }
  returns: RDSMySQLInstanceInfo[]

tools.get_ali_rds_mysql_info_metrics:
  params: { project, profile?, start_time?, end_time? }
  returns: RDSMySQLMetrics[]

tools.get_ali_rds_pg_info_metrics:
  params: { project, profile?, start_time?, end_time? }
  returns: RDSPostgreSQLMetrics[]

tools.get_ali_polar_mysql_info_metrics:
  params: { project, profile?, product?, start_time?, end_time? }
  returns: PolarDBMySQLMetrics[]

# Search & NoSQL
tools.get_ali_elasticsearch_info_metrics:
  params: { project, profile, start_time?, end_time? }
  returns: ElasticsearchMetrics[]

tools.get_ali_mongodb_info_metrics:
  params: { project, profile, start_time?, end_time? }
  returns: MongoDBMetrics[]

tools.get_ali_redis_info_metrics:
  params: { project, profile?, product?, start_time?, end_time? }
  returns: RedisMetrics[]

# Network
tools.get_ali_slb_info_metrics:
  params: { project, profile, product?, start_time?, end_time? }
  returns: SLBMetrics[]

# Monitoring
tools.get_ali_alarm_rules:
  params: { account, resource_id, start_time?, end_time? }
  returns: AlarmRule[]

tools.get_ali_alerts:
  params: { account, resource_id, start_time?, end_time? }
  returns: AlertHistory[]
```

---

## Document Metadata

| Property | Value |
|:---------|:------|
| **Document Type** | Inventory & Gap Analysis |
| **Scope** | Alibaba Cloud Resource Skills |
| **Tools Analyzed** | 11 |
| **Skills Mapped** | 6 |
| **Gaps Identified** | 6 tools without dedicated skills |
| **Next Review Date** | 2026-06-27 |
