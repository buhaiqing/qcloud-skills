# qcloud-skills

English | [中文](README_CN.md)

Tencent Cloud Agent Skill collection following the [Agent Skill OpenSpec](https://agentskills.io/specification). It provides operational runbooks for AI agents such as Claude Code, Cursor, Harness AI Agent, and other OpenSpec-compatible agents.

These skills are instruction documents for agents, not executable programs. Live cloud operations are executed at runtime through `tccli` as the primary path or `tencentcloud-sdk-python` as the fallback path.

## Repository layout

```text
qcloud-skills/
├── qcloud-*-ops/                   # Product-scoped ops skills (SKILL.md + assets/ + references/)
├── qcloud-aiops-diagnosis/         # Cross-product AIOps diagnosis
├── qcloud-proactive-inspection/    # Cross-product proactive inspection
├── qcloud-well-architected-review/ # Cross-product Well-Architected review orchestrator
├── qcloud-skill-generator/         # Meta-skill for generating/updating skills; not a runtime ops skill
├── scripts/                        # Shared validation, GCL, CI, and local verification scripts
│   └── fixtures/                   # Fixed inputs for CI/local smoke checks
├── docs/                           # GCL, Reflexion, failure-pattern, and cross-skill specifications
├── .github/workflows/              # GitHub Actions quality gates
├── ruff.toml                       # Python lint configuration (Ruff 0.11.8 / py311)
├── README.md
├── README_CN.md
└── LICENSE
```

The canonical skill inventory is the set of `qcloud-*` directories in this repository plus the governance notes in `AGENTS.md`.

## Skill inventory

### Product-scoped skills

| Skill | Product / scope | Main capabilities |
|---|---|---|
| `qcloud-cvm-ops` | Cloud Virtual Machine (CVM) | Instance lifecycle, CBS/snapshots/images, SSH keys, security groups, performance tuning, troubleshooting |
| `qcloud-cdb-ops` | TencentDB for MySQL | Instance lifecycle, backup/restore, accounts and parameters, SSL, slow query analysis, error logs |
| `qcloud-clb-ops` | Cloud Load Balancer (CLB) | Load balancers, listeners, backend binding, health checks, certificates, cross-region binding |
| `qcloud-cos-ops` | Cloud Object Storage (COS) | Bucket/object lifecycle, storage classes, ACL/Bucket Policy, versioning, static website hosting |
| `qcloud-es-ops` | Elasticsearch Service | Cluster lifecycle, indices, snapshot restore, plugins/dictionaries, cluster diagnosis |
| `qcloud-redis-ops` | TencentDB for Redis | Instance lifecycle, backup/restore, parameters, accounts, network diagnosis, performance tuning |
| `qcloud-monitor-ops` | Cloud Monitor / Observability | Alarm policies, metric queries, alarm history, notification templates, GCL quality dashboard |
| `qcloud-tke-ops` | Tencent Kubernetes Engine (TKE) | Clusters, node pools, addons, security configuration, Kubernetes diagnosis |
| `qcloud-vpc-ops` | Virtual Private Cloud (VPC) | VPCs, subnets, routes, CIDR planning, NAT, VPN, peering, security groups/network ACLs |
| `qcloud-cam-ops` | Cloud Access Management (CAM) | Policies, users/groups/roles, access-key rotation, SAML/OIDC, permission audit |
| `qcloud-cdn-ops` | Content Delivery Network (CDN) | Domain management, purge/prefetch, HTTPS certificates, origins, traffic monitoring, hotlink protection, log analysis |
| `qcloud-cbs-ops` | Cloud Block Storage (CBS) | Disk lifecycle, attach/detach, expansion, snapshots, scheduled snapshot policies |
| `qcloud-cls-ops` | Cloud Log Service (CLS) | Logsets/topics, indexes, collection rules, log query, download, shipping |
| `qcloud-ckafka-ops` | CKafka | Instances, topics, partitions, consumer groups, ACLs, message production/consumption |
| `qcloud-scf-ops` | Serverless Cloud Function (SCF) | Functions, namespaces, triggers, versions/aliases, logs, diagnosis |
| `qcloud-mongodb-ops` | TencentDB for MongoDB | Replica sets/sharded clusters, backup/restore, FlashBack, accounts/parameters, audit, TDE |
| `qcloud-postgres-ops` | TencentDB for PostgreSQL | Instances, databases/tables, backup/restore, parameters, accounts, security, diagnosis |
| `qcloud-ssl-ops` | SSL certificates | Certificate query, deployment, renewal, delete protection, association checks |
| `qcloud-agsx-ops` | Agent runtime / AGSX | SDK-only operations for agent pools and runtime resources |
| `qcloud-finops-ops` | FinOps | Cost analysis, billing queries, anomaly detection, optimization recommendations; no automatic billing changes |
| `qcloud-ccn-ops` | Cloud Connect Network (CCN) | CCN instances, VPC/DC/VPN attachments, route learning/propagation, bandwidth limits, cross-region/cross-account networking |
| `qcloud-cicd-ops` | CI/CD & DevOps | Pipelines, code repositories, artifact repos, automated deployments; SDK-only operations |
| `qcloud-dc-ops` | Direct Connect (DC) | Physical dedicated lines, direct connect tunnels, direct connect gateways, BGP routing |
| `qcloud-migration-ops` | Cloud migration | Host migration (CVM online/offline), database migration (DTS), storage migration, migration assessment |
| `qcloud-service-mesh-ops` | Service Mesh (TCM) | Istio-based service mesh, sidecar injection, traffic governance, canary deployments, mTLS, distributed tracing |
| `qcloud-tcop-ops` | Optimization Platform (TCOP) | Cost optimization, resource optimization (right-sizing/idle), architecture review, savings plan/RI coverage, optimization reports |

### Cross-product and meta skills

| Skill | Type | Main capabilities |
|---|---|---|
| `qcloud-aiops-diagnosis` | Cross-product diagnosis | Multi-metric correlation, log pattern recognition, alarm storm handling, diagnostic decision trees |
| `qcloud-proactive-inspection` | Cross-product inspection | Five-step loop: discovery → collection → detection → diagnosis → report |
| `qcloud-well-architected-review` | Cross-product architecture review | Reliability, security, cost, and efficiency assessment; orchestrates product workers |
| `qcloud-skill-generator` | Meta-skill | Generates/updates other skills and enforces templates, governance, self-review, and adversarial review |

## Shared design patterns

- **Dual-path execution model**: `tccli` is the primary path; `tencentcloud-sdk-python` is the fallback path.
- **Pre-check → Execute → Verify → Recover**: every operation runbook follows this four-step structure.
- **Five Core Standards**: clear boundaries, structured I/O, explicit actionable steps, complete failure strategies, and absolute single responsibility.
- **Cross-skill delegation**: for example, CVM may delegate to VPC/CLB/COS, and Monitor may delegate to CVM/CLB/VPC. Architecture review and proactive inspection are orchestrated by their cross-product skills.
- **Runtime quality gates (GCL)**: high-risk operations are guarded by Generator-Critic-Loop traces, scoring, retry decisions, and safety aborts.
- **Lightweight Reflexion**: reusable failure patterns are stored in `docs/failure-patterns.md` to prevent repeated mistakes across sessions.

## Local validation

Before opening a pull request or handing off work, run the one-command local validation suite aligned with CI:

```bash
python3 scripts/validate_local.py
```

To inspect the exact commands without running them:

```bash
python3 scripts/validate_local.py --list
```

The suite includes:

- Ruff linting pinned to `0.11.8` via `ruff.toml`
- `SKILL.md` frontmatter validation
- Well-Architected Worker Output Contract example JSON validation
- Markdown local link and repository path validation
- GCL smoke + trace aggregation
- Script unit tests
- GCL alarm wire plan using a fixed healthy fixture
- GCL Tier-A conformance

The GCL alarm plan uses `scripts/fixtures/gcl-quality-summary-healthy.json` so local or CI history under `audit-results/` cannot affect build-time regression checks. The GCL smoke step uses `--structural-critic-only` for CI/local structural smoke checks only; it must not be used as a production quality pass.

The GitHub Actions workflow `.github/workflows/validate-skills.yml` runs the same quality gates on every pull request.

## Quick start

1. Install prerequisites:
   - [tccli](https://cloud.tencent.com/document/product/440)
   - Python 3.11 for CI parity; runtime skills require at least Python 3.8+
   - Ruff 0.11.8 for local linting
2. Configure Tencent Cloud credentials:

```bash
export TENCENTCLOUD_SECRET_ID=your_secret_id
export TENCENTCLOUD_SECRET_KEY=your_secret_key
export TENCENTCLOUD_REGION=ap-guangzhou
```

3. Reference the relevant skill's `SKILL.md` from an Agent Skill-compatible AI agent.
4. For high-risk cloud operations, follow the skill-specific GCL, confirmation, and rollback requirements. Do not bypass safety gates.

## Key documents

| Document | Description |
|---|---|
| `AGENTS.md` | Repository-level agent guidance, quality gates, and asset placement rules |
| `docs/gcl-spec.md` | Generator-Critic-Loop runtime quality gate specification |
| `docs/reflexion-memory.md` | Reflexion failure-memory governance |
| `docs/failure-patterns.md` | Reusable failure-pattern store |
| `qcloud-skill-generator/SKILL.md` | Meta-skill workflow, generation rules, and self-review requirements |
| `manual/trajectory-evaluation-metrics.md` | Trajectory evaluation metrics system — 57 indicators across 10 dimensions (output quality, convergence, safety, self-evolution, anomaly, collaboration, observability, cost, robustness, explainability) with coverage map and priority roadmap |

## License

MIT License — see [LICENSE](LICENSE).
