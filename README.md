# qcloud-skills

腾讯云 Agent Skill 集合 — 遵循 [Agent Skill OpenSpec](https://agentskills.io/specification) 规范，为 AI Agent（如 Claude Code、Cursor、Harness AI Agent 等）提供腾讯云各类产品的运维操作能力。

## 仓库结构

```
qcloud-skills/
├── qcloud-cdb-ops/            # 云数据库 MySQL 运维技能
├── qcloud-clb-ops/            # 负载均衡运维技能
├── qcloud-cos-ops/            # 对象存储运维技能
├── qcloud-cvm-ops/            # 云服务器运维技能
├── qcloud-es-ops/             # Elasticsearch 服务运维技能
├── qcloud-monitor-ops/        # 云监控运维技能
├── qcloud-redis-ops/          # 云缓存 Redis 运维技能
├── qcloud-skill-generator/    # 技能生成器（元技能）
├── qcloud-tke-ops/            # 容器服务 TKE 运维技能
├── qcloud-vpc-ops/            # 虚拟私有云运维技能
├── qcloud-cam-ops/            # 访问管理 CAM 运维技能
├── qcloud-cdn-ops/            # 内容分发 CDN 运维技能
├── qcloud-cbs-ops/            # 云硬盘 CBS 运维技能
├── qcloud-cls-ops/            # 日志服务 CLS 运维技能
├── qcloud-ckafka-ops/         # 消息队列 CKafka 运维技能
├── qcloud-scf-ops/            # 云函数 SCF 运维技能
├── qcloud-aioops-diagnosis/   # AIOps 智能诊断（跨产品）
├── qcloud-proactive-inspection/ # 主动巡检（跨产品）
├── qcloud-well-architected-review/ # 卓越架构审查（跨产品）
├── README.md
└── LICENSE
```

## 技能概览

### qcloud-cvm-ops — 云服务器运维

管理腾讯云 CVM（Cloud Virtual Machine）实例的完整生命周期，包括创建/查询/启动/停止/重启/销毁实例，CBS 云硬盘管理、快照与镜像、SSH 密钥、安全组配置、性能调优及故障诊断等。

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 核心技能文档（29 KB） |
| `assets/eval_queries.json` | 评估查询集（含 intent 分类） |
| `assets/example-config.yaml` | 10 个场景示例配置 |
| `references/core-concepts.md` | 核心概念 |
| `references/cli-usage.md` | CLI 使用指南 |
| `references/api-sdk-usage.md` | Python SDK 使用指南 |
| `references/troubleshooting.md` | 故障排查 |
| `references/monitoring.md` | 监控配置 |
| `references/integration.md` | 集成指南 |
| `references/finops-analysis.md` | 成本分析 |
| `references/secops-checklist.md` | 安全清单 |
| `references/well-architected-assessment.md` | 卓越架构评估 |
| `references/aiops-diagnosis.md` | AIOps 诊断 |
| `references/proactive-inspection.md` | 主动巡检 |
| `references/audit-rules.md` | 审计规则 |

### qcloud-clb-ops — 负载均衡运维

管理腾讯云 CLB（Cloud Load Balancer）负载均衡实例的 CRUD、监听器配置（TCP/UDP/HTTP/HTTPS）、后端服务器绑定与健康检查、目标组管理、SSL 证书配置、跨地域绑定等。

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 核心技能文档（24 KB） |
| `assets/eval_queries.json` | 评估查询集（20 条查询） |
| `assets/example-config.yaml` | 示例配置 |
| `references/core-concepts.md` | 核心概念 |
| `references/cli-usage.md` | CLI 使用指南 |
| `references/api-sdk-usage.md` | Python SDK 使用指南 |
| `references/troubleshooting.md` | 故障排查 |
| `references/monitoring.md` | 监控配置 |
| `references/integration.md` | 集成指南 |
| `references/finops-cost-optimization.md` | 成本优化 |
| `references/secops-security-operations.md` | 安全运维 |
| `references/well-architected-assessment.md` | 卓越架构评估 |
| `references/aiops-best-practices.md` | AIOps 最佳实践 |

### qcloud-cbs-ops — 云硬盘运维

管理腾讯云 CBS（Cloud Block Storage）云硬盘生命周期，包括创建/删除云硬盘、挂载/卸载到CVM实例、磁盘扩容、快照管理（创建/回滚/删除）、自动快照策略配置等。

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 核心技能文档（28 KB） |
| `assets/eval_queries.json` | 评估查询集 |
| `references/core-concepts.md` | 核心概念（磁盘类型、状态机、性能指标） |
| `references/cli-usage.md` | CLI 使用指南 |
| `references/troubleshooting.md` | 故障排查 |

### qcloud-cls-ops — 日志服务运维

管理腾讯云 CLS（Cloud Log Service）日志服务，包括日志集和日志主题管理、日志索引配置、日志采集配置（机器组+采集规则）、日志查询与分析、下载和投递等。

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 核心技能文档（28 KB） |
| `assets/eval_queries.json` | 评估查询集 |
| `references/core-concepts.md` | 核心概念（日志集/主题/索引/采集） |
| `references/cli-usage.md` | CLI 使用指南 |
| `references/troubleshooting.md` | 故障排查 |

### qcloud-ckafka-ops — 消息队列运维

管理腾讯云 CKafka（Cloud Kafka Service）消息队列实例，包括实例创建/销毁、Topic管理、分区配置、消费者组管理、ACL规则配置、消息生产和消费等。

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 核心技能文档（24 KB） |
| `assets/eval_queries.json` | 评估查询集 |
| `references/core-concepts.md` | 核心概念（Broker/Topic/Partition/ConsumerGroup） |
| `references/cli-usage.md` | CLI 使用指南 |
| `references/troubleshooting.md` | 故障排查 |

### qcloud-vpc-ops — 虚拟私有云运维

管理腾讯云 VPC（Virtual Private Cloud）网络、子网、路由表的 CRUD、CIDR 规划、NAT 网关、VPN、对等连接、专线接入、网络安全组与网络 ACL 等。

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 核心技能文档（15.6 KB） |
| `assets/eval_queries.json` | 评估查询集 |
| `assets/example-config.yaml` | 示例配置 |
| `references/core-concepts.md` | 核心概念 |
| `references/cli-usage.md` | CLI 使用指南 |
| `references/api-sdk-usage.md` | Python SDK 使用指南 |
| `references/troubleshooting.md` | 故障排查 |
| `references/integration.md` | 集成指南 |
| `references/finops-cost-optimization.md` | 成本优化 |
| `references/secops-security-operations.md` | 安全运维 |
| `references/well-architected-assessment.md` | 卓越架构评估 |
| `references/aiops-best-practices.md` | AIOps 最佳实践 |

### qcloud-cos-ops — 对象存储运维

管理腾讯云 COS（Cloud Object Storage）存储桶生命周期、对象上传/下载/删除、存储分级（STANDARD/STANDARD_IA/ARCHIVE）、访问控制（ACL/Bucket Policy）、版本控制、静态网站托管等。

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 核心技能文档（9.8 KB） |
| `assets/eval_queries.json` | 评估查询集（10+10 正反例） |
| `assets/example-config.yaml` | 示例配置 |
| `references/core-concepts.md` | 核心概念 |
| `references/cli-usage.md` | CLI 使用指南 |
| `references/api-sdk-usage.md` | Python SDK 使用指南 |
| `references/troubleshooting.md` | 故障排查 |
| `references/integration.md` | 集成指南 |
| `references/finops-cost-optimization.md` | 成本优化 |
| `references/secops-security-operations.md` | 安全运维 |
| `references/well-architected-assessment.md` | 卓越架构评估 |
| `references/aiops-best-practices.md` | AIOps 最佳实践 |

### qcloud-cdb-ops — 云数据库 MySQL 运维

管理腾讯云 CDB（TencentDB for MySQL）实例的完整生命周期，包括创建/查询/升级/重启/隔离/销毁实例，备份与克隆恢复、账户管理、参数配置、SSL 加密、慢查询分析、错误日志排查等。

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 核心技能文档（24 KB） |
| `assets/eval_queries.json` | 评估查询集（20 条查询） |
| `assets/example-config.yaml` | 示例配置 |
| `references/core-concepts.md` | 核心概念（MySQL 版本、实例规格、存储引擎） |
| `references/cli-usage.md` | CLI 使用指南（tccli cdb 命令全表） |
| `references/api-sdk-usage.md` | Python SDK 使用指南（操作映射与示例） |
| `references/troubleshooting.md` | 故障排查（18+ 错误码诊断） |
| `references/monitoring.md` | 监控配置（QCE/CDB 指标与告警规则） |
| `references/integration.md` | 集成指南（Cloud Shell、CI/CD、委派模式） |
| `references/well-architected-assessment.md` | 卓越架构评估（4 支柱检查清单） |

### qcloud-es-ops — Elasticsearch 服务运维

管理腾讯云 ES（Elasticsearch Service）集群的完整生命周期，包括创建/查询/更新/删除集群，索引管理（创建/查询/更新/删除），快照备份与恢复，插件与词典管理，集群诊断与健康检查等。

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 核心技能文档（28 KB） |
| `assets/eval_queries.json` | 评估查询集（20 条查询） |
| `assets/example-config.yaml` | 示例配置 |
| `references/core-concepts.md` | 核心概念（节点类型、磁盘类型、架构） |
| `references/cli-usage.md` | CLI 使用指南（tccli es 命令全表） |
| `references/api-sdk-usage.md` | Python SDK 使用指南（操作映射与示例） |
| `references/troubleshooting.md` | 故障排查（16+ 错误码诊断） |
| `references/monitoring.md` | 监控配置（QCE/ES 指标与告警规则） |
| `references/integration.md` | 集成指南（Cloud Shell、CI/CD、委派模式） |
| `references/well-architected-assessment.md` | 卓越架构评估（4 支柱检查清单） |

### qcloud-monitor-ops — 云监控运维

管理腾讯云 TCOP（腾讯云可观测平台）告警策略 CRUD、指标查询（GetMonitorData）、告警历史、通知模板、仪表盘、事件监控、AIOps 主动巡检等。

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 核心技能文档（20 KB） |
| `assets/eval_queries.json` | 评估查询集 |
| `assets/example-config.yaml` | 示例配置 |
| `references/core-concepts.md` | 核心概念 |
| `references/cli-usage.md` | CLI 使用指南 |
| `references/api-sdk-usage.md` | Python SDK 使用指南 |
| `references/troubleshooting.md` | 故障排查 |
| `references/integration.md` | 集成指南 |
| `references/finops-cost-optimization.md` | 成本优化 |
| `references/secops-security-operations.md` | 安全运维 |
| `references/well-architected-assessment.md` | 卓越架构评估 |
| `references/aiops-best-practices.md` | AIOps 最佳实践 |

### qcloud-redis-ops — 云缓存 Redis 运维

管理腾讯云 Redis（云缓存）实例的完整生命周期，包括创建/查询/升级/续费/隔离/销毁实例，备份恢复、参数配置、账号管理、网络诊断、性能调优、规格升级、自动备份配置等。

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 核心技能文档 |
| `assets/eval_queries.json` | 评估查询集 |
| `assets/example-config.yaml` | 示例配置 |
| `references/core-concepts.md` | 核心概念 |
| `references/cli-usage.md` | CLI 使用指南 |
| `references/api-sdk-usage.md` | Python SDK 使用指南 |
| `references/troubleshooting.md` | 故障排查 |
| `references/monitoring.md` | 监控配置 |
| `references/integration.md` | 集成指南 |
| `references/well-architected-assessment.md` | 卓越架构评估 |
| `references/enhanced-self-healing-framework.md` | 自愈框架 |

### qcloud-tke-ops — 容器服务 TKE 运维

管理腾讯云 TKE（Tencent Kubernetes Engine）集群的完整生命周期，包括集群创建/查询/删除、节点池管理、Addon 安装、集群安全配置、Kubernetes 诊断、集群实例管理等。

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 核心技能文档 |
| `assets/eval_queries.json` | 评估查询集 |
| `assets/example-config.yaml` | 示例配置 |
| `references/core-concepts.md` | 核心概念 |
| `references/cli-usage.md` | CLI 使用指南 |
| `references/api-sdk-usage.md` | Python SDK 使用指南 |
| `references/troubleshooting.md` | 故障排查 |
| `references/monitoring.md` | 监控配置 |
| `references/integration.md` | 集成指南 |
| `references/well-architected-assessment.md` | 卓越架构评估 |
| `references/enhanced-self-healing-framework.md` | 自愈框架 |
### qcloud-skill-generator — 技能生成器

**元技能（Meta-Skill）**，用于生成或更新其他 `qcloud-[product]-ops` 技能。本身不执行云资源操作，而是根据腾讯云 API 规范生成 AI Agent 可读的运维剧本（runbook），包含完整的生成工作流、模板、提示词库和审查指南。

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 核心元技能文档（33.7 KB） |
| `assets/eval_queries.json` | 评估查询集 |
| `assets/example-config.yaml` | 示例配置 |
| `references/qcloud-skill-template.md` | 技能生成模板（27.3 KB） |
| `references/prompt-library.md` | 提示词库 |
| `references/user-experience-spec.md` | 用户体验规范 |
| `references/execution-environment.md` | 执行环境设置 |
| `references/cli-behavior.md` | CLI 行为参考 |
| `references/enhanced-self-healing-framework.md` | 自愈框架 |
| `references/governance-and-adversarial-review.md` | 治理与对抗审查 |
| `references/optimization-analysis.md` | 三维优化框架 |
| `references/aiops-best-practices.md` | AIOps 最佳实践 |
| `references/aiops-log-intelligence.md` | AIOps 日志智能 |
| `references/finops-cost-optimization.md` | FinOps 成本优化 |
| `references/secops-security-operations.md` | SecOps 安全运维 |
| `references/troubleshooting.md` | 故障排查模板 |
| `references/well-architected-assessment.md` | 卓越架构评估 |
| `templates/proactive-inspection.md` | 主动巡检模板（25.8 KB） |

### qcloud-cam-ops — 访问管理 CAM 运维

管理腾讯云 CAM（Cloud Access Management）策略的完整生命周期，包括策略 CRUD、用户/组/角色管理、API 密钥轮换、SAML/OIDC 配置、权限审计和最小权限检查等。

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 核心技能文档 |
| `assets/eval_queries.json` | 评估查询集 |
| `assets/example-config.yaml` | 示例配置 |
| `references/core-concepts.md` | 核心概念 |
| `references/cli-usage.md` | CLI 使用指南 |
| `references/api-sdk-usage.md` | Python SDK 使用指南 |
| `references/troubleshooting.md` | 故障排查 |
| `references/well-architected-assessment.md` | 卓越架构评估 |

### qcloud-cdn-ops — 内容分发 CDN 运维

管理腾讯云 CDN（Content Delivery Network）加速域名的完整生命周期，包括域名管理、缓存刷新/预热、HTTPS 证书配置、源站管理、流量监控、防盗链和日志分析等。

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 核心技能文档 |
| `assets/eval_queries.json` | 评估查询集 |
| `assets/example-config.yaml` | 示例配置 |
| `references/core-concepts.md` | 核心概念 |
| `references/cli-usage.md` | CLI 使用指南 |
| `references/api-sdk-usage.md` | Python SDK 使用指南 |
| `references/troubleshooting.md` | 故障排查 |
| `references/monitoring.md` | 监控配置 |
| `references/well-architected-assessment.md` | 卓越架构评估 |
| `references/finops-cost-optimization.md` | 成本优化 |
| `references/secops-security-operations.md` | 安全运维 |
| `references/integration.md` | 集成指南 |

### qcloud-well-architected-review — 卓越架构审查（跨产品）

对腾讯云资源进行四支柱（可靠性/安全性/成本/效率）架构评估，支持单资源审查和全站架构审计，可作为各产品运维技能的委派目标。

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 核心技能文档 |
| `references/reliability-pillar.md` | 可靠性支柱：备份/恢复/多可用区 |
| `references/security-pillar.md` | 安全性支柱：CAM/凭证/加密 |
| `references/cost-pillar.md` | 成本支柱：计费/闲置检测/升配降配 |
| `references/efficiency-pillar.md` | 效率支柱：批量操作/自动化/API优化 |
| `assets/eval_queries.json` | 评估查询集 |
| `assets/example-config.yaml` | 示例配置 |

### qcloud-aioops-diagnosis — AIOps 智能诊断（跨产品）

三维优化框架（故障诊断→根因定位→快速恢复）的智能诊断引擎，支持多指标关联分析、日志模式识别、告警风暴处理和诊断决策树。

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 核心技能文档 |
| `references/diagnosis-framework.md` | 三维优化框架 |
| `references/log-intelligence.md` | 日志模式识别 |
| `references/diagnostic-workflows.md` | 诊断决策树 |
| `references/alarm-handling.md` | 告警风暴处理 |
| `references/delegation-matrix.md` | 委派路由 |
| `assets/eval_queries.json` | 评估查询集 |
| `assets/example-config.yaml` | 示例配置 |

### qcloud-proactive-inspection — 主动巡检（跨产品）

五步闭环巡检流程（发现→采集→检测→诊断→报告），支持多产品资源巡检、可配置阈值、统计异常检测和结构化报告生成。

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 核心技能文档 |
| `references/discovery.md` | 资源发现模式 |
| `references/collection.md` | 指标采集方法 |
| `references/detection.md` | 异常检测规则 |
| `references/diagnosis.md` | 根因分析工作流 |
| `references/reporting.md` | 报告生成模板 |
| `assets/eval_queries.json` | 评估查询集 |
| `assets/example-config.yaml` | 示例配置 |

## 公共设计模式

所有技能共享以下设计原则：

- **双路径执行模型** — 主路径为 `tccli` CLI，备用路径为 `tencentcloud-sdk-python` Python SDK
- **五大核心标准** — 清晰边界、结构化 I/O、明确操作步骤、完整的失败策略、绝对单一职责
- **卓越架构集成** — 将操作映射到可靠性、安全性、成本、效率四大支柱
- **前置检查 → 执行 → 验证 → 恢复** 四步执行流程
- **技能间委派** — CVM 可委派 VPC/CLB/COS，Monitor 可委派 CVM/CLB/VPC，CDB/ES 可委派 VPC/Monitor/COS 等

## 快速开始

1. 确保已安装 [tccli](https://cloud.tencent.com/document/product/440) 和 Python 3.8+
2. 配置腾讯云凭据：
   ```bash
   export TENCENTCLOUD_SECRET_ID=your_secret_id
   export TENCENTCLOUD_SECRET_KEY=your_secret_key
   export TENCENTCLOUD_REGION=ap-guangzhou
   ```
3. 在支持 Agent Skill 的 AI Agent 中引用对应技能的 `SKILL.md` 文件

## 许可证

MIT License — 详见 [LICENSE](LICENSE) 文件。
