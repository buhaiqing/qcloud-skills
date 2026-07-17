---
name: qcloud-copilot
description: >-
  Natural-language AIOps orchestration for Tencent Cloud. Accepts NL requests,
  converts to structured execution plans, routes to qcloud-*-ops skills and
  qcloud-proactive-inspection, returns dual-audience inspection reports via
  Blackboard-backed multi-step workflows.
license: MIT
compatibility: >-
  Python 3.8+, tccli (primary CLI), valid TENCENTCLOUD_* credentials,
  optional OpenAI-compatible LLM for CI inspection strategy mode.
metadata:
  author: qcloud
  version: "1.0.0"
  last_updated: "2026-07-11"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  cli_applicability: cli-first
  cli_support_evidence: >-
    Orchestration layer; delegates execution to product skills via tccli
    (SkillDispatcher) and qcloud-proactive-inspection scripts.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
    - COPILOT_CUSTOMER_TAG_KEY
  related_skills:
    - qcloud-proactive-inspection
    - qcloud-aiops-diagnosis
    - qcloud-monitor-ops
    - qcloud-vpc-ops
---

## Trigger & Scope

### SHOULD Use

| Scenario | Example | Delegation |
|----------|---------|------------|
| NL query spanning multiple Tencent Cloud products | "巡检示例客户全部资源" | → `qcloud-proactive-inspection` |
| Conversational follow-up with context inheritance | "那北京的呢" (after prior query) | → self (SessionManager) |
| Unknown intent requiring clarification | "帮我看看这个" (vague) | → ask user via `ask_user` step |
| Destructive mutation with confirmation | "停止 ins-abc" | → product skill + L2 gate |

### SHOULD NOT Use

- Direct CRUD on a single known product → delegate directly to product skill
- Real-time streaming responses → product skill handles
- Non-Tencent Cloud operations → not in scope

## Variable Convention

| Type | Syntax | Resolved From |
|------|---------|----------------|
| Runtime | `{{env.*}}` | Agent environment |
| User input | `{{user.*}}` | First-turn NL query |
| Output | `{{output.*}}` | Skill execution result |
| Context | `{{ctx.*}}` | SessionManager history |

## Execution Flow

```
ask/run CLI
    │
    ▼
CopilotEngine.ask(query)
    │
    ├─ Parser.parse()          → ParsedRequest
    ├─ Classifier.classify()   → ClassifiedIntent
    ├─ PlanGen.generate()      → ExecutionPlan
    ├─ Safety L0 (structural)  ← check_l0()
    ├─ Safety L1 (semantic)    ← check_l1()
    ├─ PlanDispatcher.execute() → [StepResult]   # Phase 2: serial multi-step
    │       ├─ SkillDispatcher (skill_call)
    │       ├─ CruiseRunner (cruise_run)
    │       ├─ AlertIntelRunner (alert_analyze)
    │       └─ synthesize_report (blackboard aggregation)
    ├─ Safety L2 (destructive) ← check_l2(confirmed=...)
    ├─ Safety L3 (report)      ← check_l3(reviewed=...)
    └─ ReportGen.synthesize()  → Report → save_report_markdown()
```

### Multi-Step Plan Mode (Level 3 Phase 2)

Load a structured `ExecutionPlan` JSON instead of NL plan generation:

```bash
python -m copilot plan \
  --plan qcloud-copilot/tests/fixtures/plan-vpc-cruise-alert-report.json \
  --session ses-abc123
```

| Flag | Purpose |
|------|---------|
| `--plan <path.json>` | Execute fixture/file plan (skips NL `plan_gen`) |
| `--dry-run` | Print step order + blackboard read/write paths only |
| `--session` | Bind blackboard session (required) |
| `--reviewed` | Bypass L3 gate after CRITICAL findings |

**Standard 4-step risk plan** (NL trigger: VPC + 风险/巡检 + 告警, or `REPORT` + secondary `CRUISE`):

```
vpc-0 (describe-vpcs) → cruise-1 + alert-2 → report-3 (synthesize_report)
```

Phase 2 executes steps **serially** by `depends_on` + `parallel_group` order when `max_parallel_groups=1`.

**Phase 3 (parallel)**: when `dispatch_config.max_parallel_groups > 1`, steps in the same `parallel_group` run concurrently via `ThreadPoolExecutor`; groups execute in order (0 → 1 → 2). Blackboard writes use `fcntl.flock` merge-write.

**V4 human gate**: any contribution `verdict == CRITICAL` → `ExecutionResult.status = awaiting_confirmation`; CLI requires `--reviewed` to deliver.

## Cross-Skill Delegation

| Intent | Primary Skill | Fallback |
|--------|--------------|----------|
| `diagnose` | `qcloud-monitor-ops` + `qcloud-cvm-ops` | parallel |
| `inspect` | per target → `qcloud-{target}-ops` | — |
| `cruise` | `qcloud-proactive-inspection` | parallel inspect |
| `act` | per target → `qcloud-{target}-ops` | GCL runner |
| `report` | self (report_gen) | — |

## Safety Gates

- **L0** (structural): skill name validity, resource ID format, region validity
- **L1** (semantic): step budget ≤ 10, no duplicate step IDs
- **L2** (destructive): user confirmation required for `destructive=True` steps
- **L3** (report): critical findings require human review before output

## Output

每次巡检**自动落盘两份报告**（同目录、按客户覆盖）：

| 受众 | 路径 | 内容 |
|------|------|------|
| 运维工程师 | `.runtime/copilot/reports/{customer}/final-report.md` | 结论先行 + 按优先级处理项 + 根因分析 + 附录（编排/Skill链） |
| 管理层 | `.runtime/copilot/reports/{customer}/summary-report.md` | 结论 + 处理项 + 下一步行动（无技术附录） |

**详版结构（结论先行）**：巡检结论 → 拓扑资源巡检覆盖 → **巡检证据链** → Skill 调用链 → 需处理项（P0/P1/P2）→ 问题分析 → 推荐方案 → 自动化路径 → 附录：巡检过程 → 环境参考

**简报结构**：巡检结论 → 拓扑覆盖摘要 → **证据链摘要** → 需处理项 → 下一步行动

到期规则：30 天内到期自动升级为 P1 纳入需处理项；60 天内为 P2。

```bash
# NL 巡检 — 两份报告均自动写入
python -m copilot ask "朔州天源 VPC 风险巡检和告警汇总报告" \
  --session ses-001 --format detailed --reviewed

# 终端输出管理层简报（文件仍双份落盘）
python -m copilot ask "..." --session ses-001 --format summary --reviewed
```

Related runtime artifacts (not the Copilot summary `.md`):

| Artifact | Path |
|----------|------|
| Blackboard | `.runtime/blackboard/{session_id}.json` |
| **Evidence chain** | `shared_context.evidence_chain`（策略/计划/过程/结果/产物索引） |
| proactive-inspection JSON | `.runtime/proactive-inspection/cruise-{customer}-*.json` |
| Session history | `~/.omo/memor/copilot/sessions/{session_id}.json` |

## Blackboard Integration

跨 Skill 结构化 handoff 走 Blackboard schema（`schema_version` **1.1**）。

| 字段 | 路径 | 说明 |
|------|------|------|
| contributions | `shared_context.contributions.<skill>` | 各 Skill verdict / findings / topology_hints |
| **evidence_chain** | `shared_context.evidence_chain` | **完整证据链**（见下表） |
| pending_actions | `shared_context.pending_actions` | 待委派变更（只读巡检不写） |

**evidence_chain 四段结构**（`copilot/evidence.py` 写入，报告「巡检证据链」节同源渲染）：

| 段 | 内容 |
|----|------|
| `strategy` | 拓扑驱动巡检策略：`priority_chain`、决策器 `topology_reasoner_v1`、`llm_native_target` |
| `plan` | ExecutionPlan 快照（步骤 id / skill / operation） |
| `process` | 逐步执行事件（phase / actor / status / artifact） |
| `results` | contributions 汇聚 + `artifact_index`（sniff/cruise JSON 路径） |

## LLM-native 巡检路径（生产目标）

> **原则**：客户拓扑不同 → 分析优先级应动态决策，而非固定跑完全部 analyzer 脚本。

| 层级 | 当前实现 | 生产路径 |
|------|----------|----------|
| 策略决策 | `topology_reasoner.py` 启发式（`decision_maker: topology_reasoner_v1`） | LLM 读拓扑 JSON + 用户意图 → 自主决定深挖链 |
| 指标采集 | proactive-inspection analyzer 脚本（**fallback**） | LLM 按需拉取 + 子任务并行 |
| 根因关联 | 报告层规则聚合 | 主 Agent 持拓扑上下文推理 |
| 变更执行 | 委托产品 Skill + L2 Gate | 不变（human-in-the-loop） |

环境变量 `COPILOT_LLM_REASONING=1` 启用 CI 外部 LLM 策略；配合 `COPILOT_LLM_API_KEY`、`COPILOT_LLM_MODEL`、`COPILOT_LLM_BASE_URL`（OpenAI 兼容入口，支持国内模型）。**默认主路径为 Agent 内调**，未启用时使用拓扑启发式 + 脚本 fallback，证据链仍完整写入 Blackboard。

## Agent Runtime 无关性（Portable Contract）

> **ADR**: [`docs/architecture/2026-07-11-llm-native-agent-inband-adr.md`](../../docs/architecture/2026-07-11-llm-native-agent-inband-adr.md)  
> **ADR** = Architecture Decision Record（架构决策记录）；[术语表](../../docs/architecture/2026-07-11-llm-native-agent-inband-adr.md#附录术语表-glossary)；[开发计划](../../docs/superpowers/plans/2026-07-11-llm-native-agent-inband.md)

**Agent 内调是模式，不是产品。** 以下运行时均可复用同一套巡检契约：

| 运行时 | 说明 |
|--------|------|
| Cursor | 当前主要交互环境 |
| OpenCode | 换 Agent 后同样适用 |
| Claude Code / 其他 | 只要能加载 Skill + 执行 Shell |

**可移植接头**（与 Agent 品牌无关）：

| 接头 | 约定 |
|------|------|
| Skill 入口 | 本文件 + `qcloud-proactive-inspection/SKILL.md` |
| 仓库规范 | 根目录 `AGENTS.md` |
| NL 触发 | `python -m copilot ask "{客户} VPC 风险巡检和告警汇总报告" --session <id> --reviewed` |
| 结构化 handoff | Blackboard `schema_version` 1.1 + `evidence_chain` |
| 报告落盘 | `.runtime/copilot/reports/{customer}/final-report.md` + `summary-report.md` |
| 预检 | Python 3.10+ `.venv`、`tccli` 在 PATH、`.env` 填齐凭证 |

**各 Agent 需自行配置**（非契约一部分）：Skill 发现插件、MCP 工具、子 Agent 并行机制。

换平台后：同一提示词 + 同一 `session_id` → 结构等价的证据链与报告。

## Architecture Decisions（2026-07-11）

| 决策 | 内容 |
|------|------|
| **LLM-native > 脚本** | 生产由 Agent/LLM 按拓扑动态决策；analyzer 脚本为 fallback |
| **Agent 内调为主** | 策略推理在会话 Agent 中完成，优于外部 LLM API 默认路径 |
| **证据链进 Blackboard** | 策略 / 计划 / 过程 / 结果四段，报告「巡检证据链」同源 |
| **拓扑驱动** | 客户实际部署结构决定 `priority_chain`，非固定全量 analyzer |
| **双层巡检** | L1 Copilot 编排；L2 proactive-inspection 内部分析（非每资源调产品 Skill） |
| **只读 + 人工门** | 巡检不变更；CRITICAL 须 `--reviewed`；修复委派产品 Skill |

## Agent-Driven Inspection Flow（LC-1 契约）

> Prompt 全文：[references/agent-inspection-prompt.md](references/agent-inspection-prompt.md)  
> Strategy schema 1.2 样例：`.runtime/blackboard/fixtures/strategy-agent-session.json`

```
用户 NL 请求
  → Agent 读本 SKILL + agent-inspection-prompt.md
  → Pre-flight（venv / tccli / 凭证）
  → python -m copilot ask "{客户} VPC 风险巡检和告警汇总报告" --session <id> --reviewed
  → 读 sniff JSON（metadata.sniff_path 或 .runtime/proactive-inspection/sniff-*.json）
  → Agent 产出 strategy JSON（decision_maker: agent_session_v1）
  → python -m copilot strategy apply --session <id> --file strategy-{session_id}.json
  → L2 proactive-inspection 按 selected_analyzers 选择性分析（LC-2）
  → final-report.md + summary-report.md（含巡检证据链）
```

| 步骤 | Agent 动作 | 禁止 |
|------|------------|------|
| 策略 | 拓扑 + 意图 → JSON 1.2 | 未读 sniff 全量 analyzer |
| 编排 | 触发 Copilot plan / ask | 直接变更资源 |
| 证据 | 确保 Blackboard evidence_chain 四段齐全 | 仅自然语言无 JSON |
| 定位 | 代码理解前先 `codegraph_explore`（查询优先） | 对本仓库已索引代码起 `explore` 子 agent / grep-read 循环做地图 |
| 同步 | 改 `.py` 后 `codegraph sync` | 用过时索引定位代码 |

> 查询优先 + 改后同步 的硬规则见根 `AGENTS.md §CodeGraph — code intelligence (MANDATORY)`。

## Quality Gate (GCL)

GCL is **recommended** for `act` intent operations. The Copilot engine delegates
destructive operations to product skills which apply their own GCL safety gates.

## Changelog

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.7.0 | 2026-07-11 | LC-3：`copilot strategy apply`、Agent 策略写回 evidence_chain、巡检剧本 |
| 1.6.0 | 2026-07-11 | LC-1：Agent-Driven Inspection Flow + `references/agent-inspection-prompt.md` |
| 1.5.1 | 2026-07-11 | ADR 文档化：Agent Runtime 无关性、Agent 内调主路径、架构决策表；链至 `docs/architecture/2026-07-11-llm-native-agent-inband-adr.md` |
| 1.5.0 | 2026-07-11 | Blackboard evidence_chain（schema 1.1）、报告「巡检证据链」节、topology_reasoner_v1、双报告 v1.4 增强 |
| 1.4.0 | 2026-07-11 | 双报告落盘、结论先行、到期晋升 P1/P2、拓扑资源覆盖表、L1/L2 Skill 调用链 |
