# qcloud-skills

[English](README.md) | 中文

腾讯云 Agent Skill 集合，遵循 [Agent Skill OpenSpec](https://agentskills.io/specification) 规范，为 AI Agent（如 Claude Code、Cursor、Harness AI Agent 等）提供腾讯云产品运维 runbook。

这些 skill 是给 Agent 读取的指令文档，不是可执行程序。实际云资源操作在运行时通过 `tccli`（主路径）或 `tencentcloud-sdk-python`（备用路径）完成。

## 仓库结构

```text
qcloud-skills/
├── qcloud-*-ops/                   # 产品级运维技能目录（SKILL.md + assets/ + references/）
├── qcloud-aiops-diagnosis/         # AIOps 智能诊断（跨产品）
├── qcloud-proactive-inspection/    # 主动巡检（跨产品）
├── qcloud-well-architected-review/ # 卓越架构审查（跨产品编排）
├── qcloud-skill-generator/         # 技能生成器（元技能，非运行时运维 skill）
├── scripts/                        # 共享校验、GCL、CI/本地验证脚本
│   └── fixtures/                   # CI/local smoke 用固定输入 fixture
├── docs/                           # GCL、Reflexion、failure-pattern 等跨技能规范
├── .github/workflows/              # GitHub Actions 质量门禁
├── ruff.toml                       # Python lint 配置（Ruff 0.11.8 / py311）
├── README.md
├── README_CN.md
└── LICENSE
```

Canonical 技能清单以仓库中的 `qcloud-*` 目录和 `AGENTS.md` 为准。

## 技能清单

### 产品级技能

| Skill | 产品 / 范围 | 主要能力 |
|---|---|---|
| `qcloud-cvm-ops` | 云服务器 CVM | 实例生命周期、CBS/快照/镜像、SSH 密钥、安全组、性能调优、故障诊断 |
| `qcloud-cdb-ops` | 云数据库 MySQL | 实例生命周期、备份恢复、账户与参数、SSL、慢查询、错误日志 |
| `qcloud-clb-ops` | 负载均衡 CLB | 负载均衡实例、监听器、后端绑定、健康检查、证书与跨地域绑定 |
| `qcloud-cos-ops` | 对象存储 COS | 存储桶与对象生命周期、存储分级、ACL/Bucket Policy、版本控制、静态网站 |
| `qcloud-es-ops` | Elasticsearch Service | 集群生命周期、索引、快照恢复、插件词典、集群诊断 |
| `qcloud-redis-ops` | 云缓存 Redis | 实例生命周期、备份恢复、参数、账号、网络诊断、性能调优 |
| `qcloud-monitor-ops` | 云监控 / 可观测 | 告警策略、指标查询、告警历史、通知模板、GCL 质量 dashboard |
| `qcloud-tke-ops` | 容器服务 TKE | 集群、节点池、Addon、安全配置、Kubernetes 诊断 |
| `qcloud-vpc-ops` | 私有网络 VPC | VPC、子网、路由、CIDR 规划、NAT、VPN、对等连接、安全组/ACL |
| `qcloud-cam-ops` | 访问管理 CAM | 策略、用户/组/角色、密钥轮换、SAML/OIDC、权限审计 |
| `qcloud-cdn-ops` | 内容分发 CDN | 域名管理、刷新预热、HTTPS 证书、源站、流量监控、防盗链、日志分析 |
| `qcloud-cbs-ops` | 云硬盘 CBS | 云硬盘生命周期、挂载卸载、扩容、快照、自动快照策略 |
| `qcloud-cls-ops` | 日志服务 CLS | 日志集/主题、索引、采集配置、日志查询、下载与投递 |
| `qcloud-ckafka-ops` | 消息队列 CKafka | 实例、Topic、分区、消费组、ACL、消息生产消费 |
| `qcloud-scf-ops` | 云函数 SCF | 函数、命名空间、触发器、版本别名、日志与诊断 |
| `qcloud-mongodb-ops` | MongoDB | 副本集/分片集群、备份恢复、FlashBack、账号参数、审计、TDE |
| `qcloud-postgres-ops` | PostgreSQL | 实例、库表、备份恢复、参数、账号、安全与诊断 |
| `qcloud-ssl-ops` | SSL 证书 | 证书查询、部署、续期、删除保护与证书关联检查 |
| `qcloud-agsx-ops` | Agent Runtime / AGSX | SDK-only 能力，Agent pool 和运行时资源运维 |
| `qcloud-finops-ops` | FinOps | 成本分析、账单查询、异常检测、优化建议；不自动执行计费变更 |

### 跨产品与元技能

| Skill | 类型 | 主要能力 |
|---|---|---|
| `qcloud-aiops-diagnosis` | 跨产品诊断 | 多指标关联、日志模式识别、告警风暴处理、诊断决策树 |
| `qcloud-proactive-inspection` | 跨产品巡检 | 发现 → 采集 → 检测 → 诊断 → 报告的五步闭环巡检 |
| `qcloud-well-architected-review` | 跨产品架构审查 | 可靠性、安全、成本、效率四支柱评估；编排产品 worker |
| `qcloud-skill-generator` | 元技能 | 生成/更新其他 skill，执行模板、治理、自检与对抗审查流程 |

## 公共设计模式

- **双路径执行模型**：`tccli` 是主路径，`tencentcloud-sdk-python` 是备用路径。
- **前置检查 → 执行 → 验证 → 恢复**：所有操作 runbook 都遵循四步结构。
- **五大核心标准**：清晰边界、结构化 I/O、明确操作步骤、完整失败策略、绝对单一职责。
- **跨技能委派**：例如 CVM 可委派 VPC/CLB/COS，Monitor 可委派 CVM/CLB/VPC；架构评估和主动巡检由对应跨产品 skill 编排。
- **运行时质量门禁（GCL）**：高风险操作通过 Generator-Critic-Loop 进行 trace、评分、重试和安全中止。
- **轻量 Reflexion**：可复用失败模式保存在 `docs/failure-patterns.md`，用于跨会话预防重复错误。

## 本地校验

提交或交接前，优先运行与 CI 质量门禁对齐的一键校验：

```bash
python3 scripts/validate_local.py
```

查看脚本将执行的具体命令：

```bash
python3 scripts/validate_local.py --list
```

其中包含：

- Ruff lint（固定 `0.11.8`，配置见 `ruff.toml`）
- `SKILL.md` frontmatter 校验
- Well-Architected Worker Output Contract 示例 JSON 校验
- Markdown 本地链接与仓库路径校验
- GCL smoke + trace aggregate
- 脚本单测
- 使用固定健康 fixture 的 GCL alarm wire plan
- GCL Tier-A conformance

GCL alarm plan 使用 `scripts/fixtures/gcl-quality-summary-healthy.json`，避免被本地或 CI 的历史 `audit-results/` trace 污染。GCL smoke 使用 `--structural-critic-only`，仅用于 CI/local 结构冒烟，不可作为生产质量通过。

GitHub Actions workflow `.github/workflows/validate-skills.yml` 会在每个 PR 上运行同一套质量门禁。

## 快速开始

1. 安装前置工具：
   - [tccli](https://cloud.tencent.com/document/product/440)
   - Python 3.11（CI 基准；运行 skill 的最低要求为 Python 3.8+）
   - Ruff 0.11.8（用于本地 lint）
2. 配置腾讯云凭据：

```bash
export TENCENTCLOUD_SECRET_ID=your_secret_id
export TENCENTCLOUD_SECRET_KEY=your_secret_key
export TENCENTCLOUD_REGION=ap-guangzhou
```

3. 在支持 Agent Skill 的 AI Agent 中引用对应 skill 的 `SKILL.md`。
4. 对高风险云操作，按对应 skill 的 GCL/确认/回滚要求执行，不要绕过安全门禁。

## 关键文档

| 文档 | 说明 |
|---|---|
| `AGENTS.md` | 仓库级 Agent 指引、质量门禁、文件放置规则 |
| `docs/gcl-spec.md` | Generator-Critic-Loop 运行时质量门规范 |
| `docs/reflexion-memory.md` | Reflexion 失败模式记忆规则 |
| `docs/failure-patterns.md` | 可复用失败模式存储 |
| `qcloud-skill-generator/SKILL.md` | 元技能工作流、生成规则与自检要求 |

## 许可证

MIT License — 详见 [LICENSE](LICENSE)。
