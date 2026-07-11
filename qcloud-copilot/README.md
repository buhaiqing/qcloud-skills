---
name: qcloud-copilot
description: |
  AIOps Copilot — Tencent Cloud 的 NL→Orchestration 编排引擎（Level 3）。
  接受自然语言运维意图，解析 + 分类 + 编排 + 安全门控 + 跨 Skill Blackboard 协作，
  生成结构化执行计划并自动落盘双份巡检报告（详版 / 简版）。
license: MIT
---

# AIOps Copilot（qcloud-copilot）

`qcloud-copilot` 是 Tencent Cloud Skills Farm 的**编排层 Skill**，位于所有 `qcloud-*-ops` 产品
Skill 之上。它把用户的自然语言请求转换为**结构化执行计划**，按 `parallel_group` 与
`depends_on` 调度到底层 Skill，并通过 **Blackboard** 实现跨 Skill 上下文传递与证据链沉淀。

| 维度 | 摘要 |
|------|------|
| 目标 | "把一句话运维意图变成可追溯的巡检/变更报告" |
| Level | Gartner L3 — 工作流协作（Blackboard + Plan/Dispatcher） |
| 上游 | 用户 NL / Agent 内调 / 结构化 `ExecutionPlan` JSON |
| 下游 | `qcloud-proactive-inspection`、`qcloud-monitor-ops`、`qcloud-vpc-ops` 等 24 个产品 Skill |
| 默认受众 | 详版（运维工程师）+ 简版（管理层） |
| 状态机 | `IDLE → PARSING → CLASSIFYING → L0 → PLANNING → L1 → EXECUTING → L2 → REPORTING → L3 → COMPLETED` |

> **ADR**: [`docs/architecture/2026-07-11-llm-native-agent-inband-adr.md`](../../docs/architecture/2026-07-11-llm-native-agent-inband-adr.md)
> **开发计划**: [`docs/superpowers/plans/2026-07-11-llm-native-agent-inband.md`](../../docs/superpowers/plans/2026-07-11-llm-native-agent-inband.md)
> **入口 SKILL**: [SKILL.md](./SKILL.md)（编排契约与触发规则）

---

## 目录

1. [核心价值](#核心价值)
2. [适用场景](#适用场景)
3. [快速开始](#快速开始)
4. [整体架构](#整体架构)
5. [核心模块](#核心模块)
6. [CLI 用法](#cli-用法)
7. [执行流程与生命周期](#执行流程与生命周期)
8. [四层安全门](#四层安全门)
9. [Blackboard — 跨 Skill 上下文总线](#blackboard--跨-skill-上下文总线)
10. [证据链 evidence_chain](#证据链-evidence_chain)
11. [巡检策略 inspection_strategy](#巡检策略-inspection_strategy)
12. [输出与报告](#输出与报告)
13. [环境变量与配置](#环境变量与配置)
14. [LLM-native 巡检路径](#llm-native-巡检路径)
15. [Agent Runtime 无关性](#agent-runtime-无关性)
16. [测试](#测试)
17. [故障排除](#故障排除)
18. [参见](#参见)

---

## 核心价值

- **意图即接口**：用户写"朔州天源 VPC 风险巡检和告警汇总报告"，Copilot 解析意图、查别名表、生成 4 步风险计划、自动路由到 `qcloud-vpc-ops` + `qcloud-proactive-inspection` + `qcloud-monitor-ops`，最后合成双份报告落盘。
- **结构化 handoff**：跨 Skill 上下文走 **Blackboard（schema 1.1）+ evidence_chain**，不走 SKILL.md prose 手工拼接；同一 `session_id` 的多次调用串成可审计链。
- **Topology-first**：策略决策依据客户**实际拓扑**（EIP/CLB/VM/RDS/Redis 计数），非固定跑完全部 analyzer；零资源的服务写入 `skipped_analyzers`（不是漏检）。
- **四层安全门**：L0/L1/L2/L3 分别拦截格式、计划、变更、报告；任一失败立即 `ABORT`，不留 partial result。
- **H 幻觉检测 + Reflexion 反思**：`check_h()` 在执行前拦截未知 skill/operation；`write_reflexion()` 在失败后写入 `docs/failure-patterns.md`，跨 session 学习。
- **Agent Runtime 无关**：同一套 prompt + 同一 `session_id` 在 Cursor / OpenCode / Claude Code 上产出结构等价的证据链与报告。

---

## 适用场景

**SHOULD Use**（应使用本 Skill）：

| 场景 | 例子 |
|------|------|
| 跨产品 NL 查询 | "巡检济南银座全部资源" |
| 模糊 NL 意图（Type C 用户） | "最近系统有没有问题" |
| 多步编排（黑板协作） | "朔州天源 VPC 风险巡检和告警汇总报告" |
| 会话上下文继承 | "那北京的呢"（基于上一轮） |
| 已知结构的可重复巡检 | 4 步风险计划（vpc-0 → cruise-1 + alert-2 → report-3） |
| Agent 内调策略写回 | Cursor Agent 产出 inspection_strategy JSON → `copilot strategy apply` |

**SHOULD NOT Use**（不应使用本 Skill）：

| 反例 | 原因 |
|------|------|
| 单产品直接 CRUD | 直接调用 `qcloud-cvm-ops` 等产品 Skill 即可 |
| 实时流式响应 | 产品 Skill 处理 |
| 非 Tencent Cloud 操作 | 不在编排范围 |
| 不带白名单 operation 的破坏性变更 | `SkillDispatcher` 会拒派 |

---

## 快速开始

### 1. 前置环境

按仓库根 `AGENTS.md` 完成：

```bash
# Python 3.10 venv（tcm 兼容；本 skill 走 tccli + Tencent SDK）
uv venv --python 3.10 && source .venv/bin/activate
uv pip install tccli

# 凭证（CLI 必须用 INI，SDK 用 env）
cp .env.example .env
$EDITOR .env  # 填入 TENCENTCLOUD_SECRET_ID / TENCENTCLOUD_SECRET_KEY / COPILOT_* 等

# 验证 tccli 在 PATH 中
which tccli
tccli --version
```

### 2. 一行自然语言巡检

```bash
source .venv/bin/activate
export PYTHONPATH=qcloud-copilot

# NL 模式（自动解析意图、生成计划）
python -m copilot ask "朔州天源 VPC 风险巡检和告警汇总报告" \
  --session ses-001 --format detailed --reviewed

# 输出：终端打印报告 + 自动落盘两份 Markdown
#   .runtime/copilot/reports/朔州天源/final-report.md
#   .runtime/copilot/reports/朔州天源/summary-report.md
```

### 3. 结构化计划模式

```bash
python -m copilot plan \
  --plan qcloud-copilot/tests/fixtures/plan-vpc-cruise-alert-report.json \
  --session ses-abc123 --reviewed
```

### 4. 管理会话 / 健康指标

```bash
python -m copilot sessions list
python -m copilot sessions show ses-001
python -m copilot health report --days 7
python -m copilot health top-errors --limit 5
```

---

## 整体架构

```
┌──────────────────────────────────────────────────────────────────┐
│                      CLI（copilot/cli.py）                       │
│  ask / run / plan / sessions / health / strategy apply           │
└────────────────────┬─────────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────┐
│                  CopilotEngine（engine.py）                     │
│  ask(query) → Report    run_plan(plan) → Report                  │
│                                                                  │
│  State: IDLE→PARSING→CLASSIFYING→L0→PLANNING→L1→                │
│        EXECUTING→L2→REPORTING→L3→COMPLETED                       │
└──────┬─────────┬─────────┬─────────┬─────────┬─────────────────┘
       │         │         │         │         │
       ▼         ▼         ▼         ▼         ▼
   parser  classifier  plan_gen  L0/L1/L2/L3  dispatcher
   (parse) (classify)  (generate) (gate)       (topo DAG exec)
                                                    │
                              ┌─────────────────────┼─────────────────────┐
                              ▼                     ▼                     ▼
                       SkillDispatcher        CruiseRunner       AlertIntelRunner
                          (skill_call)        (cruise_run)        (alert_analyze)
                              │                     │                     │
                              ▼                     ▼                     ▼
                          tccli              proactive-inspection 脚本       monitor GetMonitorData
                       (read-only)          (sniff + analyze)              (tccli)
                              │
                              ▼
                       ┌──────────────────────────────────────────┐
                       │ Blackboard（.runtime/blackboard/*.json） │
                       │   shared_context.contributions.*          │
                       │   shared_context.evidence_chain.*         │
                       │   plan / status / schema_version          │
                       └──────────────────────────────────────────┘
                                       │
                                       ▼
                       ┌──────────────────────────────────────────┐
                       │  Report Synthesizer（report_gen.py）    │
                       │  → detailed + summary Markdown            │
                       │  → .runtime/copilot/reports/<customer>/   │
                       └──────────────────────────────────────────┘
```

详见 [references/architecture.md](./references/architecture.md)。

---

## 核心模块

`qcloud-copilot/copilot/` 下的核心文件：

| 模块 | 职责 | 关键导出 |
|------|------|---------|
| `models.py` | 全部 dataclass + `IntentType` 枚举 | `ParsedRequest`, `ClassifiedIntent`, `PlanStep`, `ExecutionPlan`, `StepResult`, `ExecutionResult`, `Report`, `SessionState`, `DEFAULT_DISPATCH_CONFIG` |
| `parser.py` | NL 归一化、实体抽取、置信度打分 | `parse(raw) -> ParsedRequest` |
| `classifier.py` | 意图分类 + 目标资源识别 | `classify(request) -> ClassifiedIntent` |
| `plan_gen.py` | 按 `IntentType` 模板化生成 `ExecutionPlan`；特例：VPC + 风险 + 告警 → 4 步风险计划 | `generate(intent, context) -> ExecutionPlan` |
| `plan_schema.py` | JSON 计划文件加载、依赖校验、Blackboard 路径解析 | `load_plan_file`, `validate_execution_plan`, `resolve_blackboard_paths` |
| `engine.py` | 顶层编排器（状态机 + 报告落盘 + L3 门禁） | `CopilotEngine.ask`, `CopilotEngine.run_plan` |
| `dispatcher.py` | 拓扑 DAG 执行器、并行 group、step timeout 300s | `PlanDispatcher.execute` |
| `report_gen.py` | 双模板合成（详版/简版）、Markdown 落盘 | `synthesize`, `synthesize_from_blackboard`, `save_report_markdown`, `render_markdown` |
| `blackboard.py` | Session-scoped Blackboard 客户端；fcntl 文件锁；schema 校验 | `BlackboardClient`, `validate_blackboard`, `empty_board`, `load_schema` |
| `strategy.py` | Inspection strategy 加载/校验/写回 Blackboard evidence_chain | `apply_strategy`, `load_strategy_file`, `validate_strategy` |
| `evidence.py` | 证据链构造（strategy / plan / process / results 四段） | `build_evidence_chain`, `load_sniff_for_session` |
| `topology_reasoner.py` | 拓扑驱动的优先级链生成（heuristic_v1） | `reason_inspection_strategy` |
| `llm_reasoner.py` | CI 模式外部 LLM 策略生成（OpenAI 兼容接口） | `reason_inspection_strategy_llm`, `LlmConfig` |
| `mode_resolver.py` | delivery / ci / fallback 模式决策；trigger word 匹配 | `resolve_inspection_mode`, `strip_ci_trigger_words` |
| `context_manager.py` | 别名表（客户/区域 → tag key / region） | `ContextManager`, `CUSTOMER_ALIASES`, `REGION_ALIASES` |
| `env_loader.py` | 自动加载 `.env` 中 `COPILOT_*` / `TENCENTCLOUD_*`（shell env 优先） | `ensure_runtime_env`, `load_project_dotenv` |
| `session.py` | 跨 session 对话历史（Memor 持久化） | `SessionManager` |
| `cli.py` | Typer CLI 入口；子命令 `ask/run/plan/sessions/health/strategy apply` | `app` |
| `safety/l0.py` | 结构性校验（skill/resource/region 合法性） | `check_l0` |
| `safety/l1.py` | 语义校验（step ≤ 10、无重复 step id） | `check_l1`, `MAX_STEP_BUDGET=10` |
| `safety/l2.py` | 破坏性操作二次确认 | `check_l2`, `requires_confirmation` |
| `safety/l3.py` | CRITICAL 报告人工门 | `check_l3` |
| `quality/audit.py` | 步级 trace JSON 落盘 | `audit_trace` |
| `quality/health.py` | 技能健康指标 JSONL 写入 | `record_health` |
| `quality/hallucination.py` | H 幻觉检测（skill / operation 白名单） | `check_h`, `KNOWN_OPERATIONS` |
| `quality/reflexion.py` | 失败模式写入（scratch → 聚合到 `docs/failure-patterns.md`） | `write_reflexion`, `aggregate_scratch` |
| `integration/skills.py` | Skill 分发器：tccli-first 派发、白名单 operation | `SkillDispatcher`, `KNOWN_SKILLS`, `SAFE_OPERATIONS`, `SKILL_PARAM_MAPPING`, `OPERATION_ALIAS` |
| `integration/cruise.py` | `cruise_sniff` + `cruise_analyze` 脚本调用、contribution 写回 | `CruiseRunner` |
| `integration/alert_intel.py` | 告警历史分析 + contribution 写回 + 待委派动作 | `AlertIntelRunner` |
| `integration/gcl.py` | GCL Runner 薄适配器（subprocess 包装） | `run_gcl` |
| `integration/memor.py` | SessionManager 重导出 | `SessionManager` |

---

## CLI 用法

### `ask` — 自然语言问询

```bash
python -m copilot ask "<NL query>" [OPTIONS]

Arguments:
  QUERY  自然语言 AIOps 请求

Options:
  -s, --session TEXT         会话 ID（用于多轮继承）
  --format [detailed|summary|auto]   输出受众（auto=按意图决策）
  --confirm                  L2 破坏性操作确认（危险操作门禁 bypass）
  --reviewed                 L3 CRITICAL findings 人工复核门禁 bypass
  --inspection-mode [delivery|ci]    强制巡检模式（覆盖 env / 关键词）
```

### `run` — 一次性查询（无 session）

```bash
python -m copilot run "<NL query>" --output markdown|json
```

### `plan` — 结构化多步计划

```bash
python -m copilot plan --plan <path.json> --session <id> [OPTIONS]

Options:
  --plan PATH           计划 JSON 文件路径（fixtures/plan-*.json）
  -s, --session TEXT    Blackboard session ID（必填）
  --format [detailed|summary]   输出受众
  --dry-run             仅打印步骤顺序 + blackboard read/write 路径
  --reviewed            L3 门禁 bypass
```

### `strategy apply` — Agent 内调策略写回

```bash
python -m copilot strategy apply \
  --session <id> \
  --file strategy-<id>.json \
  --decision-maker agent_session_v1|topology_reasoner_v1|llm_reasoner_v1
```

将 Agent 产出的 inspection strategy 校验后落盘 `strategy-<id>.json` 并合并进 Blackboard
`evidence_chain.strategy`。

### `sessions` — 会话管理

```bash
python -m copilot sessions list
python -m copilot sessions show <session_id>
python -m copilot sessions delete <session_id>
```

### `health` — 健康指标

```bash
python -m copilot health report --days 7
python -m copilot health top-errors --limit 5
python -m copilot health sweep --dry-run    # 90 天保留期清理预览
python -m copilot health sweep              # 实际清理
```

读 `.runtime/health/skill-metrics.jsonl`（append-only JSONL），符合
`AGENTS.md §16` 的 Per-Skill Health Metrics 规范。

---

## 执行流程与生命周期

`CopilotEngine.ask(query, session_id, audience, l2_confirmed, l3_reviewed, inspection_mode)` 的完整数据流：

```
1. ensure_runtime_env()             加载 .env（COPILOT_* / TENCENTCLOUD_*）
2. resolve_inspection_mode(...)     delivery / ci / fallback 决策
3. SessionManager.init_blackboard   创建/恢复 .runtime/blackboard/<id>.json
4. parse(query)                     → ParsedRequest（含 entities + confidence）
5. classify(parsed)                 → ClassifiedIntent（primary + targets）
6. check_l0(parsed, intent)         结构性校验；失败 → error report
7. gen_plan(intent, context)        → ExecutionPlan（含 depends_on / parallel_group）
8. check_l1(plan)                   语义校验（step ≤ 10，无重 ID）
9. check_l2(plan, confirmed)        破坏性操作二次确认
10. PlanDispatcher.execute          拓扑 DAG + 并行 group + step timeout 300s
    ├─ skill_call      → H gate → SkillDispatcher.execute → tccli
    ├─ cruise_run      → CruiseRunner（sniff + analyze + 写 contribution）
    ├─ alert_analyze   → AlertIntelRunner（Cloud Monitor tccli + 写 contribution）
    ├─ synthesize_report → synthesize_from_blackboard
    └─ report          → 占位步骤
11. _build_final_report             聚合 contributions + 构建 evidence_chain
12. check_l3(result, reviewed)      CRITICAL findings 人工门禁
13. _deliver_report                 save_report_markdown × 2（详版 + 简版）
14. record_health(skill, op, ...)   → .runtime/health/skill-metrics.jsonl
15. SessionManager.append_history   → ~/.omo/memor/copilot/sessions/<id>.json
```

每一步的执行事件由 `audit_trace` 落盘到 `.runtime/gcl/copilot/audit/<id>/step-<id>-<ts>.json`。

---

## 四层安全门

Copilot 强制按 **L0 → L1 → L2 → L3** 顺序检查，任一失败立即终止，**不留 partial result**。
对齐 `AGENTS.md §3` "Safety = 0 → ABORT immediately"。

| Gate | 检查点 | 触发条件 | 失败处理 |
|------|--------|---------|---------|
| **L0** | `check_l0()` 在 Classify 之后 | 未知 skill / 资源 ID 格式不匹配 `^(vm\|redis\|mysql\|...\|cd\|jcq)-\w+$` / 未知 region | `_error_report(L0 gate failed)` |
| **L1** | `check_l1()` 在 Plan 之后 | `len(steps) > 10` 或重复 step id | `_error_report(L1 gate failed)` |
| **L2** | `check_l2()` 在 Plan 之后（执行前） | 任一 `step.destructive == True` 且未传 `--confirm` | `_error_report(L2 gate failed)` |
| **L3** | `check_l3()` 在执行后、报告输出前 | `result.status == "awaiting_confirmation"` 或 `ReportSection.severity == "critical"` 且未传 `--reviewed` | `exec_result.status = "aborted"` + `_error_report(L3 gate failed)` |

H 幻觉检测（`check_h`）作为软门，在 `PlanDispatcher._execute_step()` 执行 `skill_call` 前
强制通过；拦截未知 skill 名称 + 未知 operation。

| H 检查 | 来源 |
|--------|------|
| 未知 skill 名称 | `KNOWN_SKILLS`（24 个产品 Skill） |
| 未知 operation | `KNOWN_OPERATIONS`（按 skill 分组的合法 operation 集合） |

---

## Blackboard — 跨 Skill 上下文总线

**Blackboard** 是 Level 3 跨 Skill 结构化 handoff 的核心。约定详见 `AGENTS.md §17.2`。

| 项 | 约定 |
|----|------|
| Schema | `.runtime/blackboard/schema.json`（Draft-07，enum schema_version ∈ {1.0, 1.1}） |
| Session 实例 | `.runtime/blackboard/{session_id}.json`（gitignore） |
| Fixtures | `.runtime/blackboard/fixtures/*.json`（**入库**，供 `jsonschema` CI 校验） |
| 客户端 | `BlackboardClient(board_dir)` |
| 写锁 | `fcntl.flock(LOCK_EX)`（session 级 lock file） |
| 写合并 | `_merge_contribution()`：findings 去重 by id，topology_hints 集合并，metadata 深合并 |

### 核心字段（`shared_context`）

| 字段 | 类型 | 用途 |
|------|------|------|
| `contributions.<skill>` | `object` | 每个 Skill 的 verdict / findings / topology_hints / metadata |
| `evidence_chain` | `object` | 完整证据链（见下） |
| `pending_actions` | `array` | 待委派变更（只读巡检不写） |

### 主要 API

```python
from copilot.blackboard import BlackboardClient

bb = BlackboardClient()
board = bb.get_or_create(session_id, user_request)

# 写入 Skill 贡献
bb.write_contribution(session_id, "qcloud-proactive-inspection", {
    "version": "3.1.0",
    "verdict": "CRITICAL",
    "findings": [{"id": "...", "severity": "P0", "summary": "...", "resource_id": "..."}],
    "topology_hints": ["i-abc", "lb-xyz"],
    "metadata": {"sniff_path": "...", "report_path": "..."},
})

# 读取
contributions = bb.read_contributions(session_id)
hints = bb.read_topology_hints(session_id)

# 写证据链
bb.write_evidence_chain(session_id, evidence_chain_dict)
```

---

## 证据链 evidence_chain

`evidence_chain` 是 Level 3 关键交付物：把"**为什么这么巡检 → 计划是什么 → 怎么跑的 → 结果怎么样**"
完整沉淀到 Blackboard，并同源渲染到报告的「巡检证据链」节。

由 `copilot/evidence.py:build_evidence_chain()` 构造，包含四段：

| 段 | 来源 | 字段 |
|----|------|------|
| `strategy` | `topology_reasoner.reason_inspection_strategy()` 或 Agent 写回的 inspection_strategy | `decision_maker`, `priority_chain`, `topology_summary`, `analysis_depth`, `selected_analyzers`, `skipped_analyzers`, `agent_rationale` |
| `plan` | `ExecutionPlan` 快照 | `plan_id`, `safety_level`, `primary_intent`, `secondary_intents`, `context`, `steps[]`（id/type/skill/operation/depends_on/parallel_group） |
| `process` | 逐步执行事件 | `ts`, `step_id`, `phase`（perceive/reason/aggregate/execute）, `actor`, `status`, `duration_ms`, `error?`, `artifact?`, `verdict?` |
| `results` | Blackboard contributions + artifact 索引 | `overall_verdict`, `contributions`（每 skill 的 verdict/findings_count/topology_hints_count）, `artifact_index`（sniff_topology / cruise_analysis / analyzer_run） |

详见 [references/architecture.md](./references/architecture.md) 与
`docs/architecture/2026-07-11-llm-native-agent-inband-adr.md`。

---

## 巡检策略 inspection_strategy

**schema_version 1.2**（位于 `evidence_chain.strategy`，与 Blackboard schema 1.1 解耦）。

### 三种 decision_maker

| `decision_maker` | 路径 | 触发条件 |
|------------------|------|---------|
| `agent_session_v1` | Agent 内调（生产主路径） | Agent 写入 `.runtime/blackboard/strategy-<id>.json` 后 `copilot strategy apply` |
| `topology_reasoner_v1` | 拓扑启发式 | 默认 fallback；无 LLM 凭据或 LLM 调用失败 |
| `llm_reasoner_v1` | 外部 LLM API | `COPILOT_LLM_REASONING=1` + `COPILOT_LLM_API_KEY` 已配置 + 用户触发 CI 模式 |

### 关键字段

```json
{
  "strategy_schema": "1.2",
  "mode": "topology_first",
  "execution_path": "agent_inband_selective",
  "decision_maker": "agent_session_v1",
  "llm_native_target": true,
  "customer": "朔州天源",
  "region": "ap-guangzhou",
  "user_request": "朔州天源 VPC 风险巡检和告警汇总报告",
  "topology_summary": {"vms": 4, "lbs": 1, "eips": 2, "rds": 2, "redis": 0, "vpcs": 1},
  "agent_rationale": "用户关注 VPC 风险；拓扑有 CLB+EIP 公网入口，优先深查 CLB 后端 VM 磁盘加密；无 Redis。",
  "selected_analyzers": ["eip", "clb", "vm", "rds_mysql"],
  "skipped_analyzers": [{"service": "redis", "reason": "topology_count=0"}],
  "analysis_depth": {"clb": "deep", "vm": "deep", "eip": "normal", "rds_mysql": "normal"},
  "early_stop": false,
  "priority_chain": [
    {"layer": "公网入口", "resource_count": 3, "analysis_depth": "deep", "rationale": "...", "sample_resource_ids": ["eip-xxx", "lb-xxx"]}
  ]
}
```

合法 analyzer 名（11 个）：`vm`, `clb`, `eip`, `redis`, `rds_mysql`, `rds_postgresql`,
`mongodb`, `elasticsearch`, `nat`, `k8s`, `security_group`。

Agent 内调 Prompt 全文：[references/agent-inspection-prompt.md](./references/agent-inspection-prompt.md)。

---

## 输出与报告

每次巡检（且 Blackboard 有 contributions）**自动落盘两份报告**，目录结构：

```
.runtime/copilot/reports/<customer>/
├── final-report.md      # 详版（运维工程师）
└── summary-report.md    # 简版（管理层）
```

终端按 `--format` 输出其中一份；文件全部落盘（不受 `--format` 影响）。

### 详版结构（结论先行）

1. **巡检结论**（Top 3 findings + 健康度评分）
2. **拓扑资源巡检覆盖**（analyzer_runs 表格：service / 拓扑数 / 已分析 / findings / 状态）
3. **巡检证据链**（evidence_chain 四段同源渲染）
4. **Skill 调用链**（L1/L2 调用时序）
5. **需处理项**（按 P0/P1/P2 分组）
6. **问题分析**（按 service 分组的根因讨论）
7. **推荐方案**（修复建议 + 委派哪个产品 Skill）
8. **自动化路径**（如何脚本化此巡检）
9. **附录**：巡检过程 / 环境参考

### 简版结构

1. **巡检结论**（一段话）
2. **拓扑覆盖摘要**（一行表格）
3. **证据链摘要**（decision_maker + verdict 摘要）
4. **需处理项**（P0/P1/P2 列表）
5. **下一步行动**（3-5 条 bullet）

### 到期晋升规则

30 天内到期的资源 → P1；60 天内到期的资源 → P2；纳入需处理项。

---

## 环境变量与配置

`copilot/env_loader.py:ensure_runtime_env()` 在 CLI 启动时自动加载 `.env` 中以 `COPILOT_` / `TENCENTCLOUD_` 开头的键，**shell 环境优先**（`os.environ.setdefault`）。

| 变量 | 默认 | 用途 |
|------|------|------|
| `COPILOT_CUSTOMER_TAG_KEY` | `客户` | 资源上识别客户的 tag key；CI 模式下未设置会发软警告 |
| `COPILOT_INSPECTION_MODE` | `auto` | `auto` / `delivery` / `ci` |
| `COPILOT_LLM_REASONING` | `0` | `1` 允许 CI 模式调用外部 LLM；`0` 降级到 `topology_reasoner_v1` |
| `COPILOT_CI_TRIGGER_WORDS` | 空 | 逗号分隔，追加 CI 触发词 |
| `COPILOT_LLM_API_KEY` | 空 | OpenAI 兼容接口的 API key |
| `COPILOT_LLM_BASE_URL` | `https://api.openai.com/v1` | 兼容国内模型（DashScope / DeepSeek / Moonshot） |
| `COPILOT_LLM_MODEL` | `gpt-4o-mini` | 模型名 |
| `COPILOT_LLM_TIMEOUT` | `300` | HTTP 读超时（秒） |
| `TENCENTCLOUD_SECRET_ID` / `TENCENTCLOUD_SECRET_KEY` | — | Tencent Cloud 凭证（tccli / SDK 用） |
| `TENCENTCLOUD_DOTENV_PATH` / `COPILOT_DOTENV_PATH` | — | 显式指定 .env 路径 |
| `TENCENTCLOUD_REGION` | `ap-guangzhou` | 默认 region |

完整配置样例见仓库根 `.env.example`。

---

## LLM-native 巡检路径

> **核心原则**：客户拓扑不同 → 分析优先级应动态决策，而非固定跑完全部 analyzer 脚本。

| 层级 | 当前实现 | 生产目标 |
|------|---------|---------|
| 策略决策 | `topology_reasoner.py` 启发式（`decision_maker: topology_reasoner_v1`） | Agent 内调读取 sniff JSON + 用户意图 → 自主决定深挖链 |
| 指标采集 | proactive-inspection analyzer 脚本（**fallback**） | Agent 按需拉取 + 子任务并行 |
| 根因关联 | 报告层规则聚合 | 主 Agent 持拓扑上下文推理 |
| 变更执行 | 委托产品 Skill + L2 门禁 | 不变（human-in-the-loop） |

### 三种 decision_maker 触发逻辑

```
CLI --inspection-mode  >  COPILOT_INSPECTION_MODE env  >  CI 触发词（"ci 模式" / "夜间巡检" / "weekly-cruise"…）  >  default=delivery
            │                          │                                       │
            └──────────── ┌────────────┘                                       │
                          ▼                                                    │
                   mode = delivery|ci|auto                                     │
                          │                                                    │
                          ▼                                                    ▼
                  COPILOT_LLM_REASONING=1 ?  :  fallback → topology_reasoner_v1
                          │
                          ▼
                  llm_reasoner_v1（外部 OpenAI 兼容 API）
```

详见 `copilot/mode_resolver.py:resolve_inspection_mode()` 与
`copilot/llm_reasoner.py:reason_inspection_strategy_llm()`。

---

## Agent Runtime 无关性

**Agent 内调是模式，不是产品。** 以下运行时均可复用同一套巡检契约：

| 运行时 | 状态 |
|--------|------|
| Cursor | 当前主要交互环境 |
| OpenCode | 换 Agent 后同样适用 |
| Claude Code / 其他 | 只要能加载 Skill + 执行 Shell |

### 可移植接头

| 接头 | 约定 |
|------|------|
| Skill 入口 | `qcloud-copilot/SKILL.md` + `qcloud-proactive-inspection/SKILL.md` |
| 仓库规范 | 根目录 `AGENTS.md` |
| NL 触发 | `python -m copilot ask "{客户} VPC 风险巡检和告警汇总报告" --session <id> --reviewed` |
| 结构化 handoff | Blackboard `schema_version` 1.1 + `evidence_chain` |
| 报告落盘 | `.runtime/copilot/reports/{customer}/final-report.md` + `summary-report.md` |
| 预检 | Python 3.10 `.venv`、`tccli` 在 PATH、`.env` 填齐凭证 |

**各 Agent 需自行配置**（非契约一部分）：Skill 发现插件、MCP 工具、子 Agent 并行机制。

换平台后：同一提示词 + 同一 `session_id` → 结构等价的证据链与报告。

详见 [`docs/architecture/2026-07-11-llm-native-agent-inband-adr.md`](../../docs/architecture/2026-07-11-llm-native-agent-inband-adr.md)。

---

## 测试

`qcloud-copilot/tests/` 下 42 个 `test_*.py` 文件覆盖：blackboard schema / 调度器 / 引擎 / 报告合成 / 上下文管理器 / 客户 tag key / 证据链 / env loader / LLM reasoner / 模式解析器 / 策略应用 / LC 系列 / L3 E2E 等。

```bash
# 全量
PYTHONPATH=qcloud-copilot pytest qcloud-copilot/tests/ -v

# 关键子集
PYTHONPATH=qcloud-copilot pytest qcloud-copilot/tests/test_blackboard_schema.py \
  qcloud-copilot/tests/test_engine.py \
  qcloud-copilot/tests/test_dispatcher.py \
  qcloud-copilot/tests/test_evidence_chain.py \
  qcloud-copilot/tests/test_strategy_apply.py \
  qcloud-copilot/tests/test_lc5_integration.py -v

# L3 端到端（需要真实 .env / Tencent Cloud 凭证）
PYTHONPATH=qcloud-copilot pytest qcloud-copilot/tests/test_l3_e2e_blackboard.py \
  qcloud-copilot/tests/test_l3_e2e_plan.py -v
```

L3 端到端测试需要真实 Tencent Cloud 凭证；其余可在沙盒中跑通。

---

## 故障排除

### `command not found: tccli`

```bash
which tccli   # 必须输出 PATH 中的 tccli
source .venv/bin/activate
uv pip install --no-cache tccli
```

### L0 失败：`Unknown skill: ...`

检查拼写是否在 `KNOWN_SKILLS`（24 个产品 Skill）中。详见 `copilot/integration/skills.py:KNOWN_SKILLS`。

### L2 失败：`Destructive operation requires user confirmation`

带 `--confirm` 标志（**仅在你已确认目标与影响后**），例如：
```bash
python -m copilot ask "停止 ins-abc" --session ses-001 --confirm
```

### L3 失败：`CRITICAL findings require human review`

带 `--reviewed` 标志，表示你已阅读 CRITICAL findings 并确认发布。

### `Blackboard not found`

session 还没创建；先 `init_blackboard()` 或调用 `get_or_create()`。`.runtime/blackboard/*.lock` 残留文件可安全删除。

### `H gate failed: Unknown operation 'X' for skill qcloud-...`

operation 不在 `KNOWN_OPERATIONS` 白名单（按 skill 分组）。要么换合法 operation，要么扩展白名单（编辑 `copilot/quality/hallucination.py`）。

### `cruise_sniff timed out after 120s` / `cruise_analyze timed out after 300s`

- 嗅探超时 → 检查 `.env` 凭证 + 网络
- 分析超时 → 客户资源量大；可拆 plan 或缩 `--hours`

### `Schema validation failed: ...`

Blackboard 文件被手动改坏了；删除 `.runtime/blackboard/<id>.json` 重跑会自动重建（注意 loss of session context）。

### 报告未自动落盘

只有当 Blackboard 有 `contributions` 时才双份落盘；纯 inspect / describe 单步操作只会生成单份终端输出。

---

## 参见

- **入口 SKILL**: [SKILL.md](./SKILL.md) — 触发条件、变量约定、执行流、Cross-Skill 委托表
- **架构参考**: [references/architecture.md](./references/architecture.md)
- **核心概念**: [references/core-concepts.md](./references/core-concepts.md)
- **集成模式**: [references/integration.md](./references/integration.md)
- **GCL Rubric**: [references/rubric.md](./references/rubric.md)（8 维度，D4 hard gate）
- **Prompt 模板**: [references/prompt-templates.md](./references/prompt-templates.md)
- **Agent 内调 Prompt**: [references/agent-inspection-prompt.md](./references/agent-inspection-prompt.md)
- **ADR**: [docs/architecture/2026-07-11-llm-native-agent-inband-adr.md](../../docs/architecture/2026-07-11-llm-native-agent-inband-adr.md)
- **开发计划**: [docs/superpowers/plans/2026-07-11-llm-native-agent-inband.md](../../docs/superpowers/plans/2026-07-11-llm-native-agent-inband.md)
- **Level 3 协议**: 根 `AGENTS.md §17`（Blackboard / Plan / Dispatcher 约束）
- **Blackboard Schema**: `.runtime/blackboard/schema.json`（Draft-07）
- **Strategy Fixtures**: `.runtime/blackboard/fixtures/strategy-agent-session.json`
