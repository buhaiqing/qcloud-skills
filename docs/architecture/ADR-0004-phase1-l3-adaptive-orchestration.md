# ADR-0004: Phase 1 — L3 Adaptive Orchestration 补齐

> **Status**: Proposed
> **Date**: 2026-08-01
> **Deciders**: Architecture review (bohaiqing)
> **Supersedes**: —
> **Related**: AGENTS.md §GCL, ADR-0002 (L3→L4 daemon), ADR-0003 (FAIOps event-driven)

## 1. Context

当前 qcloud-skills 在 Gartner Agentic AI 成熟度模型中处于 **L2+**（向 L3 过渡中）。核心差距在四个方面：

| 差距 | 现状 | 影响 |
|------|------|------|
| **GCL Critic 依赖外部 LLM** | `gcl_runner.py` 的 Critic 需外部 JSON 输入，内置 `structural_critic()` 仅做规则检查 | GCL 闭环无法在单个进程中完成 |
| **Skill 注册硬编码** | Copilot 的 `KNOWN_SKILLS`、`SKILL_TO_PRODUCT`、`OPERATION_ALIAS`、`SKILL_PARAM_MAPPING` 均为硬编码 | 新增 skill 需修改 4 处代码 |
| **错误升级链未运行时化** | SKILL.md 中的 HALT/RETRY/Delegate 指令是文档，dispatcher 不做错误码解析 | 跨 skill 错误恢复需人工介入 |
| **观测面三套独立** | GCL trace + Copilot health metrics + Evidence Kernel audit 各自独立 | 跨 skill 调用链不可追溯 |

## 2. Decision

我们将在 **Phase 1** 中补齐这四项 L3 核心能力，为后续 L4 跃迁奠定基础。

### 2.1 四个模块

| # | 模块 | 目标 | 优先级 |
|---|------|------|:------:|
| 1.1 | **内建 LLM Critic** | `gcl_runner.py` 内置 LLM API 调用，替代外部 Critic JSON 输入 | P0 |
| 1.2 | **动态 Skill 注册与路由** | `SkillRegistry` 统一注册表，Copilot 和 Harness 共用 | P0 |
| 1.3 | **运行时错误升级链** | `ErrorEscalator` 解析 SKILL.md 错误表，自动执行 HALT/RETRY/Delegate | P1 |
| 1.4 | **统一观测面** | `TraceSpan` schema 统一 GCL trace + Copilot step + Evidence audit | P1 |

### 2.2 关键架构决策

#### 2.2.1 LLM Critic 集成方式

**选择**：在 `gcl_runner.py` 中新增 `llm_critic()` 函数，通过 OpenAI-compatible API 调用 LLM，读取 skill 的 `rubric.md` + `prompt-templates.md` 构建 system prompt。

**弃选方案**：
- ❌ 独立 Critic 进程/服务 — 增加部署复杂度，Phase 1 不需要
- ❌ 仅增强 structural_critic — 无法替代 LLM 的语义理解能力

**向后兼容**：`--critic-json` / `--critic-stdin` 模式保持不变。`--llm-critic` 新增可选模式。

#### 2.2.2 Skill 注册表架构

**选择**：新增 `scripts/skill_registry.py` 中的 `SkillRegistry` 类，从文件系统扫描 `qcloud-*-ops/SKILL.md` 的 YAML frontmatter 构建。`build_skill_registry.py` 输出 `audit-results/skill-registry.json` 供 Harness 和 Copilot 共用。

**弃选方案**：
- ❌ 数据库存储 — 引入外部依赖，与 repo 的纯文件系统架构冲突
- ❌ 继续扩展硬编码 — 34+ 个 skill 已不可维护

#### 2.2.3 错误表标准化

**选择**：标准化为 6 列格式：`Error Code | Action | Max Retries | Backoff | Delegate To | Recovery Hint`。`ErrorEscalator` 解析新旧两种格式。

**弃选方案**：
- ❌ YAML/JSON 独立错误表文件 — 增加维护负担，与 SKILL.md 不同步风险
- ❌ 仅增强 `tcloud_error_codes.py` — 缺少产品级子错误码

#### 2.2.4 观测面统一

**选择**：扩展已有 OBS-1 spec 中的 `Observation` dataclass，增加 `parent_span_id` + `skill_chain` 字段，兼容 GCL trace 和 Evidence audit。

**弃选方案**：
- ❌ 引入 OpenTelemetry SDK — 重型依赖，Phase 1 过度工程
- ❌ 保持三套独立 — 无法实现 L4 所需的调用链可追溯

### 2.3 依赖关系

```
1.2 SkillRegistry  ← 1.3 ErrorEscalator 需要 skill 注册表做 delegate-to 校验
       ↓
1.1 LLM Critic     ← 1.4 统一观测面需要 GCL trace 中的 critic 模式标记
       ↓
1.3 ErrorEscalator ← 1.4 统一观测面需要错误升级链的 span 事件
       ↓
1.4 统一观测面     ← 集成前三者的 trace/span 数据
```

**推荐执行顺序**：1.2 → 1.1 → 1.3 → 1.4

## 3. Consequences

### Positive

- GCL 闭环不再依赖外部 Critic，CI 和本地均可完整运行
- 新增 skill 零代码修改，仅需创建目录 + SKILL.md
- 错误恢复从人工升级到自动跨 skill 委托
- 跨 skill 调用链可追溯，为 L4 自适应编排提供数据基础

### Negative

- LLM Critic 引入 API 调用延迟（预计 2-5s/次）和费用
- 错误表标准化需修改 34 个 SKILL.md 文件
- SkillRegistry 需要与 Copilot 的硬编码注册表保持同步直到迁移完成

### Mitigation

- LLM Critic 失败时 fallback 到 structural critic（零延迟）
- 错误表标准化用脚本批量迁移，非手工修改
- SkillRegistry 与硬编码注册表双写验证，CI 检查一致性

## 4. Status Tracking

| 文档 | 路径 | 状态 |
|------|------|:----:|
| Spec | `docs/superpowers/specs/phase1-l3-adaptive-orchestration-design.md` | Draft |
| Plan | `docs/superpowers/plans/phase1-l3-adaptive-orchestration-plan.md` | Draft |
| ADR | 本文档 | Proposed |
