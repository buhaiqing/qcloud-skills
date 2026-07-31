# Phase 1: L3 Adaptive Orchestration 补齐 — 设计文档

> **Status**: Accepted
> **Date**: 2026-08-01
> **Author**: bohaiqing
> **ADR**: ADR-0004

## 背景

qcloud-skills 在 Gartner Agentic AI 成熟度模型中处于 L2+。四个核心 L3 能力缺失：

1. GCL Critic 无法自主运行（需外部 JSON 输入）
2. Skill 注册表硬编码（新增 skill 需改 4 处代码）
3. 错误升级链是文档而非运行时机制
4. 观测面三套独立（GCL trace / Copilot health / Evidence audit）

## 架构总览

```
用户请求
  │
  ▼
┌─────────────────────────────────────────────┐
│ Copilot Engine (classify → plan → dispatch) │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │ SkillRegistry (1.2)                  │   │
│  │  动态发现 → 路由 → delegate-to 图    │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  ┌──────────────────┐ ┌──────────────────┐  │
│  │ ErrorEscalator   │ │ SkillDispatcher  │  │
│  │ (1.3)            │ │                  │  │
│  │ HALT/RETRY/      │ │ tccli 执行       │  │
│  │ DELEGATE/FIX     │ │                  │  │
│  └────────┬─────────┘ └────────┬─────────┘  │
│           │                    │             │
│           ▼                    ▼             │
│  ┌──────────────────────────────────────┐   │
│  │ GCL Runner (1.1)                     │   │
│  │  Generator → LLM Critic → Decide     │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │ Unified Observability (1.4)          │   │
│  │  TraceSpan → GCL trace + Step span   │   │
│  │  + Evidence audit                    │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

---

## 1.1 内建 LLM Critic

### 1.1.1 现状

`gcl_runner.py` 的 Critic 有两种模式：

- **Structural Critic** (`structural_critic()`): 纯规则，检查 exit code / credential leak / RequestId / ClientToken。标记为 "CI/dry-run only"。
- **External Critic** (`--critic-json` / `--critic-stdin`): 读取外部 JSON 文件，期望包含 5 维度评分。

`decide()` 函数只消费 `scores` dict，不关心 Critic 来源——这是注入 LLM Critic 的关键 seam。

### 1.1.2 设计

新增 `llm_critic()` 函数，签名：

```python
def llm_critic(
    generator: dict[str, Any],
    skill: str,
    rubric_text: str,
    prompt_template: str,
    llm_config: dict[str, Any],
) -> dict[str, Any]
```

**内部流程**：

```
1. 加载 rubric.md (skill-specific) + gcl-prompt-backbone.md §2 (generic)
2. 替换占位符: {{skill_id}}, {{output.rubric}}, {{output.generator_output}}, {{output.trace}}
3. 调用 OpenAI-compatible API (chat completion)
4. 解析 JSON 响应 → validate_critic_payload()
5. 失败时: retry once → fallback to structural_critic()
```

**CLI 参数**：

```
--llm-critic           启用内建 LLM Critic
--llm-model MODEL      模型名 (默认从 GCL_LLM_MODEL 环境变量)
--llm-base-url URL     API 地址 (默认从 GCL_LLM_BASE_URL 环境变量)
```

**环境变量** (`.env.example`)：

```bash
GCL_LLM_API_KEY=sk-xxx
GCL_LLM_BASE_URL=https://api.openai.com/v1
GCL_LLM_MODEL=gpt-4o-mini
GCL_LLM_TIMEOUT=120
```

**Critic 输出合约**（与现有 `validate_critic_payload()` 兼容）：

```python
{
    "scores": {"correctness": 0|0.5|1, "safety": 0|1, "idempotency": 0|0.5|1,
               "traceability": 0|0.5|1, "spec_compliance": 0|0.5|1},
    "suggestions": ["...", "..."],
    "blocking": bool,
    "_mode": "llm-builtin"  # 区分于 "structural-only" 和外部 JSON
}
```

### 1.1.3 文件变更

| 文件 | 变更 | 行数估计 |
|------|------|:------:|
| `scripts/gcl_runner.py` | 新增 `llm_critic()` + `_build_llm_config()` | +80 |
| `scripts/gcl_runner.py` | `cmd_run()` 增加 `--llm-critic` 分支 | ±5 |
| `scripts/gcl_runner.py` | 新增 `--llm-critic` / `--llm-model` / `--llm-base-url` CLI 参数 | +15 |
| `.env.example` | 新增 `GCL_LLM_*` 环境变量块 | +6 |
| `scripts/gcl_runner_test.py` | 新增 `llm_critic()` 测试 (mock LLM) | +40 |

### 1.1.4 向后兼容

- `--critic-json` / `--critic-stdin` 模式完全不变
- `--structural-critic-only` 模式完全不变
- 不传任何 LLM 参数时行为与当前一致
- `decide()` 和 trace schema 不受影响（`_mode` 字段仅标记）

### 1.1.5 验收标准

- [ ] `gcl_runner run --llm-critic --skill qcloud-cvm-ops --command "tccli cvm DescribeInstances"` 完整执行 Generate → LLM Critique → Decide 闭环
- [ ] LLM API 超时时 fallback 到 structural critic
- [ ] LLM 返回 malformed JSON 时 fallback 到 structural critic
- [ ] `--critic-json` 模式行为不变（回归测试）
- [ ] 5 维度评分通过 `validate_critic_payload()` 验证

---

## 1.2 动态 Skill 注册与路由

### 1.2.1 现状

**四份硬编码注册表**：

| 注册表 | 文件 | 行 | 内容 |
|--------|------|:--:|------|
| `KNOWN_SKILLS` | `copilot/integration/skills.py` | 8-32 | 23 个 skill 名的 set |
| `SKILL_TO_PRODUCT` | 同上 | 35-58 | skill → tccli product 映射 |
| `OPERATION_ALIAS` | 同上 | 92-107 | (skill, op) → canonical op 映射 |
| `SKILL_PARAM_MAPPING` | 同上 | 109-119 | (skill, op) → 资源 ID flag 映射 |

**两套独立路由**：Copilot 用硬编码，Harness 用 `build_skill_registry.py` 扫描输出。两者不互通。

### 1.2.2 设计

**核心类**：`scripts/skill_registry.py::SkillRegistry`

```python
@dataclass
class SkillEntry:
    name: str                           # "qcloud-cvm-ops"
    path: Path                          # 文件系统路径
    cli_applicability: str              # "dual-path" | "cli-first" | ...
    description: str
    intent_keywords: list[str]          # 路由关键词
    delegate_to: list[dict]             # 结构化委托声明
    product_name: str                   # tccli product: "cvm"
    operation_aliases: dict[str, str]   # op 别名 → 规范名
    param_mapping: dict[str, str]       # op → 资源 ID CLI flag
    version: str
    last_updated: str

class SkillRegistry:
    skills: dict[str, SkillEntry]
    _keyword_index: dict[str, set[str]]     # token → {skill_names}
    _delegate_graph: dict[str, set[str]]    # skill → {dependencies}

    @classmethod
    def from_skill_dirs(cls, root: Path) -> SkillRegistry: ...
    def discover(self) -> list[str]: ...
    def validate(self, skill_name: str) -> bool: ...
    def route(self, query: str) -> tuple[str, float]: ...
    def get_product(self, skill_name: str) -> str: ...
    def resolve_operation(self, skill_name: str, operation: str) -> str: ...
    def resolve_param(self, skill_name: str, operation: str) -> str | None: ...
    def get_dependencies(self, skill_name: str) -> set[str]: ...
    def get_dependents(self, skill_name: str) -> set[str]: ...
    def topological_order(self) -> list[str]: ...
```

**标准化 `delegate_to` YAML 字段**（替代 prose "delegate to:" 标记）：

```yaml
delegate_to:
  - skill: qcloud-vpc-ops
    reason: "VPC/Subnet must exist before CreateDBInstance"
    trigger: "pre-flight"
  - skill: qcloud-monitor-ops
    reason: "Dashboard and alarm configuration"
    trigger: "on-demand"
```

### 1.2.3 文件变更

| 文件 | 变更 | 行数估计 |
|------|------|:------:|
| `scripts/skill_registry.py` | 新文件: SkillEntry + SkillRegistry | +200 |
| `scripts/build_skill_registry.py` | 重构: 使用 SkillRegistry 作为核心 | ±50 |
| `qcloud-copilot/copilot/integration/skills.py` | 重构: SkillDispatcher 接受 SkillRegistry 参数 | ±30 |
| `qcloud-copilot/copilot/engine.py` | 加载 SkillRegistry 传入 SkillDispatcher | ±10 |
| 30 个 SKILL.md | 新增 `delegate_to` + `product_name` + `operation_aliases` + `param_mapping` YAML 字段 | 每个 ±15 |
| `scripts/cross_skill_impact.py` | 优先读 `delegate_to`，fallback 到 `related_skills` | ±20 |
| `scripts/harness_router.py` | 使用 SkillRegistry 替代直接读 JSON | ±15 |

### 1.2.4 迁移策略

| 阶段 | 内容 | 向后兼容 |
|:----:|------|:--------:|
| 1 | SkillRegistry 新增，`build_skill_registry.py` 双输出 (registry JSON + 兼容旧格式) | ✅ |
| 2 | Copilot `SkillDispatcher` 接受可选 `SkillRegistry` 参数，默认用硬编码 | ✅ |
| 3 | 30 个 SKILL.md 批量添加 YAML 字段（脚本化） | ✅ |
| 4 | CI 验证 SkillRegistry 与硬编码注册表一致 | ✅ |
| 5 | 移除硬编码注册表 | ❌ (breaking, 最终阶段) |

### 1.2.5 验收标准

- [ ] `SkillRegistry.from_skill_dirs()` 扫描到全部 30 个 skill
- [ ] `SkillRegistry.validate("qcloud-cvm-ops")` → True, `validate("nonexistent")` → False
- [ ] `SkillRegistry.route("describe my cvm instances")` → `("qcloud-cvm-ops", confidence>0)`
- [ ] `SkillRegistry.get_product("qcloud-cvm-ops")` → `"cvm"`
- [ ] `SkillRegistry.get_dependencies("qcloud-cdb-ops")` → `{"qcloud-vpc-ops", "qcloud-cam-ops"}`
- [ ] CI: `SkillRegistry` 输出与硬编码 `KNOWN_SKILLS` 一致

---

## 1.3 运行时错误升级链

### 1.3.1 现状

- SKILL.md 中的错误表格式不一致（2-5 列，HALT/RETRY 嵌在自由文本中）
- `dispatcher.py` 不解析错误码，所有失败统一处理
- `tcloud_error_codes.py` 仅有 9 个顶级错误码，无产品子码、无 action/retry/delegate 字段
- 跨 skill 委托指令是 prose（"Delegate to qcloud-vpc-ops"），未运行时执行

### 1.3.2 设计

**标准化错误表格式**（6 列，所有 SKILL.md 统一）：

```
| Error Code | Action | Max Retries | Backoff | Delegate To | Recovery Hint |
|------------|--------|-------------|---------|-------------|---------------|
| `InvalidVpc.NotFound` | HALT | 0 | — | qcloud-vpc-ops | Verify VPC exists |
| `RequestLimitExceeded` | RETRY | 3 | exponential | — | Back off and retry |
| `InternalError` | RETRY | 3 | 2s,4s,8s | — | Escalate with RequestId |
| `InvalidParameter.ImageIdMalformed` | FIX | 1 | — | — | Use DescribeImages |
```

**Action 枚举**：`HALT | RETRY | FIX | DELEGATE`

**ErrorEscalator 类** (`scripts/error_escalator.py`)：

```python
@dataclass
class ErrorRule:
    code: str
    product: str
    action: Action          # HALT | RETRY | FIX | DELEGATE
    max_retries: int = 0
    backoff_seconds: list[int] = field(default_factory=list)
    backoff_strategy: str = "fixed"
    delegate_to: str | None = None
    recovery_hint: str = ""

class ErrorEscalator:
    def load_from_skill(self, skill_dir: Path) -> None: ...
    def load_all_skills(self, repo_root: Path) -> None: ...
    def resolve(self, error_code: str, product: str) -> ErrorRule: ...
    def execute(self, error_code: str, product: str, step_fn, step_args) -> dict: ...
```

**dispatcher.py 集成**：

```python
# 当前: 所有失败统一处理
if result.status == "failure":
    write_reflexion(category="engine_step", ...)

# 改进: 错误码解析 + 分级处理
error_code = extract_error_code(result)
rule = escalator.resolve(error_code, step.skill)
if rule.action == Action.DELEGATE:
    step.skill = rule.delegate_to
    result = retry_step(step)  # 委托到新 skill
elif rule.action == Action.RETRY:
    result = retry_with_backoff(step, rule)
elif rule.action == Action.HALT:
    return result  # 立即停止
```

### 1.3.3 文件变更

| 文件 | 变更 | 行数估计 |
|------|------|:------:|
| `scripts/error_escalator.py` | 新文件: ErrorRule + ErrorEscalator | +180 |
| `scripts/tcloud_error_codes.py` | 扩展: 新增产品级子错误码 + action/retry/delegate 字段 | +50 |
| `qcloud-copilot/copilot/dispatcher.py` | `_execute_step` 集成 ErrorEscalator | +40 |
| `qcloud-copilot/copilot/models.py` | StepResult 新增 `error_code`, `retry_count`, `delegate_to` | +10 |
| `scripts/error_table_parser.py` | 新文件: 解析新旧两种错误表格式 | +60 |
| 30 个 SKILL.md | 错误表标准化为 6 列格式 | 每个 ±20 |
| `scripts/validate_error_tables.py` | 新文件: CI 校验 | +50 |

### 1.3.4 验收标准

- [ ] `ErrorEscalator.resolve("InvalidVpc.NotFound", "cvm")` → `Action.HALT, delegate_to=qcloud-vpc-ops`
- [ ] `ErrorEscalator.resolve("RequestLimitExceeded", "cvm")` → `Action.RETRY, max_retries=3, backoff=exponential`
- [ ] CVM CreateInstances 遇到 `InvalidVpc.NotFound` → 自动委托 VPC skill → VPC 创建成功 → CVM 重试成功
- [ ] `ErrorEscalator.resolve("UnknownError", "cvm")` → `Action.HALT` (safe default)
- [ ] dispatcher 遇到 HALT 级别错误立即停止执行计划
- [ ] `validate_error_tables.py` 通过所有 30 个 skill

---

## 1.4 统一观测面

### 1.4.1 现状

三套独立系统：

| 系统 | Schema | 文件位置 | 缺陷 |
|------|--------|----------|------|
| GCL Trace | `iterations[].critic.scores` + `final.status` | `audit-results/gcl-trace-*.json` | 仅覆盖 GCL 执行，不覆盖 Copilot step |
| Copilot Health | `skill`, `duration_ms`, `status`, `error_code` (hardcoded None) | `.runtime/health/skill-metrics.jsonl` | 只写不读，无聚合查询 |
| Evidence Audit | `run_id`, `skill`, `command`, `destructive`, `token_bound` | `audit-results/evidence-*.json` | 仅记录是否执行，不记录执行质量 |

已有 OBS-1 spec 定义了 `Observation` / `UsageEvent` / `Metric` dataclass，但尚未与 GCL trace 打通。

### 1.4.2 设计

**不新建系统**，而是扩展现有 OBS-1 的 `Observation` dataclass，增加跨 skill 调用链支持。

**核心 schema 扩展**：

```python
@dataclass
class TraceSpan:
    """统一追踪 span，跨 GCL trace + Copilot step + Evidence audit"""
    span_id: str                          # UUID
    trace_id: str                         # 一次用户请求的全局 ID
    parent_span_id: str | None            # 跨 skill 委托链
    run_id: str                           # 对应 GCL trace 的 run_id
    skill: str                            # "qcloud-cvm-ops"
    operation: str                        # "DescribeInstances"
    step_id: str | None                   # Copilot plan step id
    start_time: str                       # ISO 8601
    end_time: str                         # ISO 8601
    duration_ms: int
    status: str                           # "success" | "failure" | "halted" | "delegated"
    error_code: str | None                # 来自 ErrorEscalator
    gcl_scores: dict[str, float] | None   # 仅 GCL-gated 操作有
    evidence: EvidenceRecord | None       # 破坏性操作的审计记录
    metadata: dict[str, Any]              # 扩展字段
```

**跨 skill 调用链示例**：

```
trace_id: "abc-123"
├── span_id: "s1" (Copilot: plan execution)
│   ├── span_id: "s2", parent: "s1" (CVM: RunInstances)
│   │   ├── gcl_scores: {correctness: 1, safety: 1, ...}
│   │   └── error_code: "InvalidVpc.NotFound"
│   ├── span_id: "s3", parent: "s1" (ErrorEscalator: DELEGATE → VPC)
│   │   └── delegate_to: "qcloud-vpc-ops"
│   ├── span_id: "s4", parent: "s1" (VPC: CreateVpc)
│   │   └── gcl_scores: {correctness: 1, safety: 1, ...}
│   └── span_id: "s5", parent: "s1" (CVM: RunInstances retry)
│       └── gcl_scores: {correctness: 1, safety: 1, ...}
```

**持久化**：

| 存储 | 格式 | 用途 |
|------|------|------|
| `.runtime/traces/{run_id}/spans.jsonl` | 每个 span 一行 JSON | 实时写入 |
| `.runtime/traces/{run_id}/_summary.json` | run 级别汇总 | 快速查询 |
| `audit-results/gcl-trace-*.json` | 保持现有格式（GCL 兼容） | 向后兼容 |

**gcl_trace_aggregate.py 扩展**：

新增 `--cross-skill` 模式，读取 spans.jsonl 构建调用链 DAG：

```bash
python3 scripts/gcl_trace_aggregate.py --cross-skill --run-id abc-123
# 输出: CVM(失败) → VPC(成功) → CVM(重试成功), 总耗时 12.3s
```

### 1.4.3 文件变更

| 文件 | 变更 | 行数估计 |
|------|------|:------:|
| `qcloud-copilot/copilot/observ.py` | 扩展: 新增 `TraceSpan` dataclass + `emit_span()` | +40 |
| `scripts/gcl_runner.py` | `persist_trace()` 同时写入 spans.jsonl | +15 |
| `qcloud-copilot/copilot/dispatcher.py` | 每个 step 开始/结束 emit span | +20 |
| `scripts/gcl_trace_aggregate.py` | 新增 `--cross-skill` 模式 | +60 |
| `scripts/evidence_kernel.py` | `post_record()` 关联 span_id | +10 |

### 1.4.4 向后兼容

- GCL trace JSON (`audit-results/gcl-trace-*.json`) 保持现有格式不变
- Evidence audit JSON (`audit-results/evidence-*.json`) 保持现有格式不变
- `gcl_trace_aggregate.py` 默认行为不变（不加 `--cross-skill` 时）

### 1.4.5 验收标准

- [ ] 一次 "诊断 CVM 高 CPU → 发现 VPC 问题 → 修复 VPC → 验证 CVM" 生成完整的 parent-child span 链
- [ ] `gcl_trace_aggregate.py --cross-skill --run-id xxx` 输出调用链拓扑
- [ ] 跨 skill 委托在 span 中正确标记（parent_span_id 非空）
- [ ] Evidence record 与 span 通过 run_id 关联
- [ ] GCL trace JSON 格式不受影响（回归测试）

---

## 自验证 (Self-Verify)

```python
# 1.2: SkillRegistry 完整性
reg = SkillRegistry.from_skill_dirs(Path("."))
assert len(reg.discover()) == 34
assert reg.validate("qcloud-cvm-ops")
assert not reg.validate("nonexistent")

# 1.3: ErrorEscalator 安全默认值
esc = ErrorEscalator()
rule = esc.resolve("UnknownCode.XYZ", "unknown_product")
assert rule.action == Action.HALT  # 未知错误必须 HALT

# 1.1: LLM Critic 输出合约
scores = llm_critic(generator, skill, rubric, template, config)
errors = validate_critic_payload({"scores": scores, "suggestions": [], "blocking": False})
assert not errors

# 1.4: 跨 skill span 链完整性
spans = load_spans(run_id)
assert all(s.trace_id == spans[0].trace_id for s in spans)
assert any(s.parent_span_id is not None for s in spans)  # 至少有一次委托
```

---

## 文件清单

| 文件 | 操作 | 说明 |
|------|:----:|------|
| `scripts/gcl_runner.py` | 修改 | +llm_critic() |
| `scripts/skill_registry.py` | 新增 | SkillRegistry |
| `scripts/build_skill_registry.py` | 修改 | 重构为 SkillRegistry |
| `scripts/error_escalator.py` | 新增 | ErrorEscalator |
| `scripts/error_table_parser.py` | 新增 | 错误表解析器 |
| `scripts/validate_error_tables.py` | 新增 | CI 校验 |
| `scripts/tcloud_error_codes.py` | 修改 | 扩展产品子码 |
| `scripts/cross_skill_impact.py` | 修改 | delegate_to 优先 |
| `scripts/harness_router.py` | 修改 | SkillRegistry 集成 |
| `scripts/gcl_trace_aggregate.py` | 修改 | +cross-skill 模式 |
| `scripts/evidence_kernel.py` | 修改 | span_id 关联 |
| `qcloud-copilot/copilot/integration/skills.py` | 修改 | SkillRegistry 参数 |
| `qcloud-copilot/copilot/dispatcher.py` | 修改 | ErrorEscalator + span |
| `qcloud-copilot/copilot/models.py` | 修改 | StepResult 扩展 |
| `qcloud-copilot/copilot/observ.py` | 修改 | TraceSpan dataclass |
| `qcloud-copilot/copilot/engine.py` | 修改 | SkillRegistry 传入 |
| `.env.example` | 修改 | GCL_LLM_* |
| 30 个 SKILL.md | 修改 | delegate_to + 错误表标准化 |
| 30 个 `references/rubric.md` | 无需修改 | LLM Critic 直接读取现有格式 |
| `docs/architecture/ADR-0004-*.md` | 新增 | 本文档对应的 ADR |
