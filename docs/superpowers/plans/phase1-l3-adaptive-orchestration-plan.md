# Plan: Phase 1 — L3 Adaptive Orchestration 补齐

> **Status**: Draft
> **Date**: 2026-08-01
> **Spec**: `docs/superpowers/specs/phase1-l3-adaptive-orchestration-design.md`
> **ADR**: `docs/architecture/ADR-0004-phase1-l3-adaptive-orchestration.md`

---

## Phase 1.2: 动态 Skill 注册与路由（P0，先行）

> 依赖：无。被 1.3 依赖。

### Step 1.2.1 — SkillRegistry 核心实现

- [ ] 新增 `scripts/skill_registry.py`
  - `SkillEntry` dataclass（所有字段）
  - `SkillRegistry` 类（from_skill_dirs / discover / validate / route / get_product / resolve_operation / resolve_param / get_dependencies / get_dependents / topological_order）
  - 从 SKILL.md YAML frontmatter 提取 `name`, `description`, `intent_keywords`, `delegate_to`, `cli_applicability`
  - 从 `assets/eval_queries.json` 补充 intent_keywords
  - **DoD**: `ruff check` 零 error；`test_skill_registry.py` 通过

### Step 1.2.2 — build_skill_registry.py 重构

- [ ] 重构 `scripts/build_skill_registry.py`
  - 使用 `SkillRegistry.from_skill_dirs()` 作为核心
  - 输出 `audit-results/skill-registry.json`（包含完整的 SkillEntry 列表）
  - 保持现有 JSON 输出格式向后兼容
  - **DoD**: `make registry` 输出与重构前一致；CI 通过

### Step 1.2.3 — 34 个 SKILL.md 批量添加 YAML 字段

- [ ] 编写脚本 `scripts/migrate_skill_frontmatter.py`
  - 为每个 SKILL.md 添加 `delegate_to` 字段（从 prose "delegate to:" 解析）
  - 添加 `product_name` 字段（从现有 `SKILL_TO_PRODUCT` 映射推导）
  - 添加 `operation_aliases` 和 `param_mapping` 字段
  - Dry-run 模式：仅输出 diff，不写入
  - **DoD**: dry-run 输出覆盖全部 34 个 skill，无错误

- [ ] 审查 dry-run 输出，逐 skill 确认 delegate_to 正确性
  - 使用 `cross_skill_impact.py` 验证依赖图完整性
  - **DoD**: 依赖图无孤立节点，无循环依赖

- [ ] 执行迁移（`--apply`）
  - **DoD**: 34 个 SKILL.md frontmatter 均含 `delegate_to` + `product_name`

### Step 1.2.4 — Copilot SkillDispatcher 集成

- [ ] 修改 `qcloud-copilot/copilot/integration/skills.py`
  - `SkillDispatcher.__init__` 接受可选 `SkillRegistry` 参数
  - 默认加载 `audit-results/skill-registry.json`
  - `validate_skill()` 使用 `SkillRegistry.validate()`
  - `resolve_operation()` 使用 `SkillRegistry.resolve_operation()`
  - `resolve_param()` 使用 `SkillRegistry.resolve_param()`
  - **DoD**: 现有 copilot 测试全部通过；新增 `test_integration_skills.py` 验证 SkillRegistry 集成

### Step 1.2.5 — CI 一致性验证

- [ ] 新增 CI 步骤
  - `SkillRegistry` 输出的 skill 列表 == 硬编码 `KNOWN_SKILLS`
  - 差异时报错，提示更新硬编码注册表
  - **DoD**: CI 绿；硬编码与动态注册表一致

---

## Phase 1.1: 内建 LLM Critic（P0）

> 依赖：无。可与 1.2 并行。

### Step 1.1.1 — llm_critic() 实现

- [ ] 新增 `llm_critic()` 函数到 `scripts/gcl_runner.py`
  - 加载 `gcl-prompt-backbone.md` §2（Critic 模板）
  - 加载 skill 的 `rubric.md`
  - 替换占位符: `{{skill_id}}`, `{{output.rubric}}`, `{{output.generator_output}}`, `{{output.trace}}`
  - 调用 OpenAI-compatible API (requests/httpx)
  - 解析 JSON 响应 → `validate_critic_payload()`
  - 失败 fallback: retry once → structural_critic()
  - **DoD**: `ruff check` 零 error；mock LLM 测试通过

### Step 1.1.2 — CLI 参数和环境变量

- [ ] 新增 `--llm-critic`, `--llm-model`, `--llm-base-url` CLI 参数
- [ ] 新增 `_build_llm_config()` 从环境变量读取
- [ ] 新增 `.env.example` 的 `GCL_LLM_*` 块
- [ ] **DoD**: `gcl_runner run --help` 显示新参数；环境变量缺失时有明确错误提示

### Step 1.1.3 — cmd_run() 集成

- [ ] 修改 `cmd_run()` 的 Critic 分支逻辑
  ```
  if structural_critic_only → structural_critic()
  elif llm_critic → llm_critic()
  else → load_critic(critic_json, stdin)  # 现有逻辑
  ```
- [ ] **DoD**: 三种模式均通过回归测试

### Step 1.1.4 — 测试

- [ ] 新增 `test_llm_critic.py`
  - Mock LLM 返回正常评分 JSON → PASS
  - Mock LLM 返回 malformed JSON → fallback 到 structural critic
  - Mock LLM 超时 → fallback 到 structural critic
  - Mock LLM 返回 Safety=0 → SAFETY_FAIL
  - **DoD**: 4 个测试通过；`cd scripts && python3 -m unittest discover -p "*_test.py" -v` 零 failure

### Step 1.1.5 — 集成测试

- [ ] 对 1 个 skill（qcloud-cvm-ops）执行端到端 GCL 运行
  - `gcl_runner run --llm-critic --skill qcloud-cvm-ops --command "tccli cvm DescribeInstances --Region ap-guangzhou"`
  - 验证 trace 中 `_mode: "llm-builtin"`
  - **DoD**: 完整 Generate → Critique → Decide 闭环成功

---

## Phase 1.3: 运行时错误升级链（P1）

> 依赖：1.2 (SkillRegistry)。可与 1.1 并行。

### Step 1.3.1 — ErrorEscalator 核心实现

- [ ] 新增 `scripts/error_escalator.py`
  - `Action` enum: HALT, RETRY, FIX, DELEGATE
  - `ErrorRule` dataclass
  - `ErrorEscalator` 类: load_from_skill / load_all_skills / resolve / execute / _compute_backoff / _has_error
  - 前缀匹配: `InvalidVpc.NotFound` → 先精确匹配 → 前缀匹配 `InvalidVpc` → fallback
  - 安全默认值: 未知错误码 → HALT
  - **DoD**: `ruff check` 零 error；`test_error_escalator.py` 通过

### Step 1.3.2 — 错误表解析器

- [ ] 新增 `scripts/error_table_parser.py`
  - 解析新旧两种错误表格式（当前 2-5 列 + 新 6 列）
  - 正则提取 HALT/RETRY/Delegate 语义
  - 输出标准化 `ErrorRule` 列表
  - **DoD**: 解析 CVM、CDB、Redis 三个 skill 的错误表，输出一致的 ErrorRule 格式

### Step 1.3.3 — 34 个 SKILL.md 错误表标准化

- [ ] 编写脚本 `scripts/migrate_error_tables.py`
  - 将每个 SKILL.md 中的错误表标准化为 6 列格式
  - Dry-run 模式先输出 diff
  - **DoD**: dry-run 覆盖全部 34 个 skill

- [ ] 审查 + 执行迁移
  - **DoD**: 34 个 SKILL.md 错误表均为 6 列标准格式

### Step 1.3.4 — tcloud_error_codes.py 扩展

- [ ] 扩展 `scripts/tcloud_error_codes.py`
  - 新增产品级子错误码（从各 SKILL.md 汇总）
  - 每个错误码增加 `action`, `max_retries`, `backoff`, `delegate_to` 字段
  - **DoD**: 包含至少 30 个产品级子错误码

### Step 1.3.5 — dispatcher.py 集成

- [ ] 修改 `qcloud-copilot/copilot/dispatcher.py`
  - `_execute_step` 中调用 `ErrorEscalator.resolve()`
  - DELEGATE → 修改 `step.skill` → 重试执行
  - RETRY → `_retry_with_backoff()`
  - HALT → 立即返回失败，标记 `stop_on_first_critical`
  - FIX → 重试一次（参数已由 skill 修正）
  - **DoD**: 集成测试验证 CVM InvalidVpc.NotFound → 自动委托 VPC

### Step 1.3.6 — 测试与验证

- [ ] 新增 `test_error_escalator.py`
  - 已知错误码返回正确 Action
  - 未知错误码默认 HALT
  - 前缀匹配正确
  - 重试退避时间计算正确
  - **DoD**: 5+ 个测试通过

- [ ] 新增 CI 校验 `scripts/validate_error_tables.py`
  - 所有错误码的 Action 是有效枚举值
  - 所有 delegate_to 的 skill 在 SkillRegistry 中存在
  - Backoff 字符串可解析
  - **DoD**: CI 通过全部 34 个 skill

---

## Phase 1.4: 统一观测面（P1）

> 依赖：1.1 (GCL trace), 1.2 (SkillRegistry), 1.3 (ErrorEscalator)

### Step 1.4.1 — TraceSpan schema

- [ ] 扩展 `qcloud-copilot/copilot/observ.py`
  - 新增 `TraceSpan` dataclass（span_id, trace_id, parent_span_id, run_id, skill, operation, step_id, start_time, end_time, duration_ms, status, error_code, gcl_scores, evidence, metadata）
  - 新增 `emit_span()` 方法到 `ObservableSink`
  - 持久化: `.runtime/traces/{run_id}/spans.jsonl` (append)
  - 汇总: `.runtime/traces/{run_id}/_summary.json`
  - **DoD**: `ruff check` 零 error

### Step 1.4.2 — GCL runner span 集成

- [ ] 修改 `scripts/gcl_runner.py`
  - `cmd_run()` 开始/结束各 emit 一个 span
  - span 包含 `gcl_scores` + `_mode`
  - 向后兼容: 现有 GCL trace JSON 格式不变
  - **DoD**: GCL 运行后在 spans.jsonl 中可见对应 span

### Step 1.4.3 — Copilot dispatcher span 集成

- [ ] 修改 `qcloud-copilot/copilot/dispatcher.py`
  - 每个 step 开始前 emit span（status=pending）
  - 每个 step 结束后更新 span（status=success/failure/halted/delegated）
  - DELEGATE 场景生成 child span（parent_span_id 指向原 step）
  - ErrorEscalator 的错误码写入 span.error_code
  - **DoD**: 一次跨 skill 委托执行后，spans.jsonl 包含完整 parent-child 链

### Step 1.4.4 — Evidence Kernel 关联

- [ ] 修改 `scripts/evidence_kernel.py`
  - `post_record()` 接受可选 `span_id` 参数
  - Evidence JSON 中新增 `span_id` 字段
  - **DoD**: Evidence record 可通过 span_id 关联到 TraceSpan

### Step 1.4.5 — gcl_trace_aggregate.py 扩展

- [ ] 新增 `--cross-skill` 模式
  - 读取 spans.jsonl 构建调用链 DAG
  - 输出跨 skill 调用链拓扑 + 耗时统计
  - **DoD**: `gcl_trace_aggregate.py --cross-skill --run-id xxx` 输出正确调用链

### Step 1.4.6 — 测试

- [ ] 新增 `test_trace_span.py`
  - span 序列化/反序列化
  - parent-child 链完整性
  - 跨 skill 委托 span 标记
  - **DoD**: 3+ 个测试通过

---

## 执行顺序

```
Week 1-2:  1.2 (SkillRegistry) + 1.1 (LLM Critic) 并行
Week 3-4:  1.3 (ErrorEscalator) + 1.4 (统一观测面) 串行（1.3 依赖 1.2，1.4 依赖 1.1+1.2+1.3）
```

## 风险与缓解

| 风险 | 等级 | 缓解 |
|------|:----:|------|
| LLM Critic 引入延迟和费用 | MEDIUM | Fallback 到 structural critic；LLM Critic 默认关闭 |
| 34 个 SKILL.md 批量迁移出错 | HIGH | Dry-run 先行；逐 skill diff 审查；Git 保护 |
| SkillRegistry 与硬编码注册表不一致 | MEDIUM | CI 双写验证；迁移期间保持双注册表 |
| 错误表解析器覆盖不全 | MEDIUM | 先覆盖 3 个代表性 skill；渐进覆盖全部 34 个 |
| OBS-1 已有 schema 与 TraceSpan 冲突 | LOW | TraceSpan 新增字段均为 optional；OBS-1 现有代码不受影响 |

## 里程碑验收

### M1: SkillRegistry + LLM Critic 就绪（Week 2）

- [ ] `SkillRegistry.from_skill_dirs()` 扫描到全部 34 个 skill
- [ ] `gcl_runner run --llm-critic` 完整闭环通过
- [ ] CI: `build_skill_registry.py` 输出与硬编码注册表一致

### M2: ErrorEscalator + 统一观测面就绪（Week 4）

- [ ] CVM InvalidVpc.NotFound → 自动委托 VPC → 自动重试 CVM
- [ ] 跨 skill 调用链在 spans.jsonl 中完整追溯
- [ ] `validate_error_tables.py` 通过全部 34 个 skill

### M3: Phase 1 整体验收

- [ ] 新增一个 skill（如 `qcloud-test-ops`）零代码修改即可被路由和调用
- [ ] 一次 "诊断 CVM 高 CPU → 发现 VPC 问题 → 修复 VPC → 验证 CVM" 完整闭环
- [ ] 所有新增测试通过；回归测试零 failure
- [ ] ADR、Spec、Plan 文档状态更新为 Accepted / Complete
