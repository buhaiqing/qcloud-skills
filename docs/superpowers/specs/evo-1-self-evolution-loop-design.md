# EVO-1: Copilot 自动自我进化闭环 — 设计文档

## 背景

`qcloud-copilot` 已建立"进化记忆"写入能力：
- `copilot/quality/reflexion.py::write_reflexion` + `aggregate_scratch` → 合并进 `docs/failure-patterns.md`
- `docs/success-patterns.md` 存在同类意图

**诊断结论（grep 证实，关键事实）**：这两个文件是**只写不读的死库**——
全仓库**无任何运行时代码读取它们来决策**（仅 `tests/` 与文档引用）。
等价关系：**"长期记忆已写入，但推理大脑从不调取" → 无进化闭环**。

静态决策点（进化接入点缺失）：
- 路由/skill 选择：`integration/skills.py::KNOWN_SKILLS` 硬编码
- 操作校验：`quality/hallucination.py::KNOWN_OPERATIONS` 硬编码
- 阈值：`scripts/gcl_runner.py::RUBRIC_THRESHOLDS` 硬编码（见 `p1-a-adaptive-rubric-threshold-design.md`）

**目标**：建立"采集 → 记忆 → 调取 → 决策 → 验证 → 回滚"的自动进化回路，
让 failure/success pattern 真正影响运行时行为，且不退化为"越进化越差"。

---

## 架构设计

```
              ┌─────────────── 采集层 (已有) ───────────────┐
              │ write_reflexion / success-patterns writer   │
              └──────────────────────┬──────────────────────┘
                                     │ docs/failure-patterns.md
                                     │ docs/success-patterns.md
                                     ▼
              ┌─────────────── 记忆层 (新增 EVO store) ───────────────┐
              │ EvolutionStore.load() → 结构化 pattern 对象            │
              │   - 去重/计数/recency (复用 reflexion.normalize_key)   │
              │   - 置信度 = f(count, recency, severity)              │
              └──────────────────────┬──────────────────────┘
                                     │ 结构化 patterns
                                     ▼
              ┌─────────────── 决策层 (新增 EvolutionPolicy) ──────────┐
              │ apply_routing_override(intent) -> skill_hint          │
              │ apply_op_allowlist(skill) -> extra_ops               │
              │ recommend_threshold(skill, dim) -> float | None       │
              │   ← 消费 OBS-1 的 observ_query 信号做闭环             │
              └──────────────────────┬──────────────────────┘
                                     │ 决策建议 (非强制)
                                     ▼
              ┌─────────────── 护栏层 (新增 DriftGuard) ──────────────┐
              │ - 边界: 阈值∈[floor, ceiling], 路由不跨产品域         │
              │ - 回滚: 若新策略使 success_rate 下降 → 自动 revert    │
              │ - A/B: 默认 5% 流量走进化策略, 95% 走基线             │
              └──────────────────────┬──────────────────────┘
                                     │ 生效
                                     ▼
                          运行时 dispatcher / gcl_runner
                                     │
                                     └──► OBS-1 采集 success_rate 变化 ──► 回灌
```

---

## 模块设计

### 1. `copilot/evolution/store.py` — 记忆层（解决 E1/E2）

读取 `docs/failure-patterns.md` 与 `docs/success-patterns.md`（Markdown 表格），
解析为结构化 `Pattern` 对象。复用 `reflexion.normalize_reflexion_key` 去重。

```python
@dataclass
class Pattern:
    category: str
    skill: str
    command: str
    error: str
    fix: str
    count: int
    confidence: float      # 0..1, 由 count + recency 计算
    kind: str              # "failure" | "success"

class EvolutionStore:
    def __init__(self, failure_path, success_path): ...
    def load(self) -> list[Pattern]: ...
    def high_confidence(self, kind, min_conf=0.7) -> list[Pattern]: ...
```

### 2. `copilot/evolution/policy.py` — 决策层（解决 E3）

决策层**只产出建议**，不强制覆写静态配置：

```python
class EvolutionPolicy:
    def __init__(self, store: EvolutionStore, query):  # query = OBS-1 observ_query
        ...

    def route_hint(self, intent) -> str | None:
        """高频 failure 的 skill → 建议降级/加 warning, 而非硬切。"""
        # 例: 某 skill failure count > 阈值 → 返回 hint 让上游加 confirm

    def op_allowlist(self, skill: str) -> set[str]:
        """success-patterns 中出现但 KNOWN_OPERATIONS 未列的操作 → 临时放行。"""

    def recommend_threshold(self, skill, dim) -> float | None:
        """结合 OBS-1 skill_success_rate 与 failure-patterns 给出阈值建议。"""
```

### 3. `copilot/evolution/guard.py` — 护栏层（解决 E5）

```python
class DriftGuard:
    FLOOR = 0.0
    CEIL = 1.0
    SHADOW_RATIO = 0.05   # 默认 5% 流量走进化策略

    def clamp(self, value, floor=None, ceil=None) -> float: ...
    def should_use_evolution(self, run_id) -> bool:
        # 按 run_id hash 稳定分流, 保证同一 run 一致
        ...
    def evaluate(self, before_rate, after_rate) -> bool:
        # after_rate 不显著下降才保留策略
        ...
```

### 4. 反馈信号采集（解决 E4）

在 `engine.py` 的 `_deliver_report` 后补埋点（复用 OBS-1 的 `emit_metric`）：
- `copilot_user_adopt{session_id}` — 用户是否二次追问 / override
- `copilot_report_override{...}` — 是否手动修改了最终报告

这些信号回灌 `EvolutionStore` 的 confidence 计算，形成 ground-truth 校对。

---

## 数据结构 / Schema

### 新增文件
- `qcloud-copilot/copilot/evolution/__init__.py`
- `qcloud-copilot/copilot/evolution/store.py`
- `qcloud-copilot/copilot/evolution/policy.py`
- `qcloud-copilot/copilot/evolution/guard.py`
- `qcloud-copilot/tests/test_evolution_store.py`
- `qcloud-copilot/tests/test_evolution_policy.py`
- `qcloud-copilot/tests/test_evolution_guard.py`

### 复用/改造
- `copilot/quality/reflexion.py` — 复用 `normalize_reflexion_key`（不改动）
- `copilot/quality/hallucination.py` — `KNOWN_OPERATIONS` 增加 hook：`EvolutionPolicy.op_allowlist` 在运行时补充
- `copilot/integration/skills.py` — `KNOWN_SKILLS` 路由决策增加 `route_hint` 输入
- `copilot/engine.py` — 交付后补 E4 反馈埋点
- （OBS-1 必须先落地，本 spec 依赖其 `observ_query`）

---

## 文件清单

| 文件 | 动作 |
|------|------|
| `qcloud-copilot/copilot/evolution/__init__.py` | 新增 |
| `qcloud-copilot/copilot/evolution/store.py` | 新增 |
| `qcloud-copilot/copilot/evolution/policy.py` | 新增 |
| `qcloud-copilot/copilot/evolution/guard.py` | 新增 |
| `qcloud-copilot/copilot/quality/hallucination.py` | 改造（op_allowlist hook） |
| `qcloud-copilot/copilot/integration/skills.py` | 改造（route_hint 输入） |
| `qcloud-copilot/copilot/engine.py` | 改造（E4 反馈埋点） |
| `qcloud-copilot/tests/test_evolution_*.py` | 新增（3 个） |

---

## 自验证（self-check）

```python
# test_evolution_store.py
patterns = EvolutionStore(failure_path, success_path).load()
assert any(p.kind == "failure" for p in patterns)
assert store.high_confidence("failure", 0.7) 返回 count 足够高的项

# test_evolution_policy.py
# 注入构造的 failure-pattern → route_hint 返回降级 hint
# 注入 success 中未列操作 → op_allowlist 返回该操作

# test_evolution_guard.py
assert DriftGuard().clamp(1.5) == 1.0
assert DriftGuard().should_use_evolution("stable-run") 稳定一致
```

**闭环验证（集成测试）**：构造 failure-pattern → 跑一次 dispatcher →
断言 `route_hint` 影响了上游 warning，且 `DriftGuard` 在 success_rate 下降时 revert。

---

## 与 OBS-1 的依赖关系

EVO-1 **依赖 OBS-1 的 `observ_query`** 作为反馈信号源。开发顺序：
1. 先完成 OBS-1（信号上游）
2. 再实现 EVO-1 的 store / policy / guard
3. 最后接通 dispatcher + engine 的 hook 点

两者通过 `.runtime/metrics` 单一数据源解耦，EvolutionPolicy 仅"建议"不"强制"，
保证进化可观测、可回滚。
