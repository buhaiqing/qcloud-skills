# Plan: EVO-1 自动自我进化闭环 — 开发任务

> 对应 spec: `docs/superpowers/specs/evo-1-self-evolution-loop-design.md`
> 前置依赖: OBS-1 的 `observ_query`（信号上游）必须先行落地
> 目标: 让 failure/success pattern 真正影响运行时行为，且不退化为"越进化越差"

## 阶段 0 — 记忆层（E1/E2: 消费死库）

- [x] **E0.1** 新增 `qcloud-copilot/copilot/evolution/__init__.py`（空包）
- [x] **E0.2** 新增 `qcloud-copilot/copilot/evolution/store.py`
  - `Pattern` dataclass（category/skill/command/error/fix/count/confidence/kind）
  - `EvolutionStore.load()` 解析 `docs/failure-patterns.md` + `docs/success-patterns.md` 表格
  - 复用 `reflexion.normalize_reflexion_key` 去重
  - `high_confidence(kind, min_conf=0.7)` 过滤
  - **DoD**: 读取真实 `docs/failure-patterns.md` 能解析出 failure pattern；`test_evolution_store.py` 通过

- [x] **E0.3** 新增 `qcloud-copilot/tests/test_evolution_store.py`
  - 构造最小 markdown 表格 → `load()` 返回结构化对象
  - `high_confidence` 对 count 高的项返回 True

## 阶段 1 — 决策层（E3: 进化接入点）

- [x] **E1.1** 新增 `qcloud-copilot/copilot/evolution/policy.py`
  - `EvolutionPolicy(store, query)`：`query` = OBS-1 observ_query
  - `route_hint(intent) -> str | None`（高频 failure skill → 降级 warning hint）
  - `op_allowlist(skill) -> set[str]`（success 中未列操作 → 临时放行）
  - `recommend_threshold(skill, dim) -> float | None`（结合 success_rate + failure）
  - **DoD**: 注入构造 pattern → `route_hint`/`op_allowlist` 返回预期；`test_evolution_policy.py` 通过

- [x] **E1.2** 新增 `qcloud-copilot/tests/test_evolution_policy.py`

## 阶段 2 — 护栏层（E5: 不退化）

- [x] **E2.1** 新增 `qcloud-copilot/copilot/evolution/guard.py`
  - `DriftGuard.clamp(value, floor, ceil)`
  - `DriftGuard.should_use_evolution(run_id)`（hash 稳定分流，默认 5%）
  - `DriftGuard.evaluate(before_rate, after_rate) -> bool`（下降则 revert）
  - **DoD**: `clamp(1.5)==1.0`；同一 run_id 分流稳定；`test_evolution_guard.py` 通过

- [x] **E2.2** 新增 `qcloud-copilot/tests/test_evolution_guard.py`

## 阶段 3 — 接通 hook 点（E3 落地）

- [x] **E3.1** 改造 `qcloud-copilot/copilot/quality/hallucination.py`
  - `KNOWN_OPERATIONS` 查询时并入 `EvolutionPolicy.op_allowlist(skill)`
  - **DoD**: success-pattern 中未列操作被运行时放行（构造测试）

- [x] **E3.2** 改造 `qcloud-copilot/copilot/integration/skills.py`
  - 路由决策接收 `EvolutionPolicy.route_hint(intent)` 作为加权输入（非强制）
  - **DoD**: 高频 failure 的 skill 路由被加 warning（构造测试）

## 阶段 4 — 反馈信号采集（E4: ground-truth 校对）

- [x] **E4.1** 改造 `qcloud-copilot/copilot/engine.py`
  - `_deliver_report` 后补埋点（复用 OBS-1 `emit_metric`）：
    - `copilot_user_adopt{session_id}`（二次追问 / override 信号）
    - `copilot_report_override{...}`
  - **DoD**: 断言 metrics.jsonl 出现 adopt 信号

## 阶段 5 — 闭环集成验证

- [x] **E5.1** 新增 `qcloud-copilot/tests/test_evolution_integration.py`
  - 构造 failure-pattern → 跑 dispatcher → 断言 `route_hint` 影响上游 warning
  - 断言 `DriftGuard.evaluate` 在 success_rate 下降时 revert 策略
  - **DoD**: 集成测试通过

- [x] **E5.2** 跑 `cd qcloud-copilot && python3 -m pytest tests/ -q` 全绿
- [x] **E5.3** 跑 `ruff check qcloud-copilot/copilot/evolution/` 零 error
- [x] **E5.4** 写 `TE-Audit: evo-1` 提交 footer
- [x] **E5.5** 在 `docs/failure-patterns.md` 的 Usage Guidelines 增加"自动消费说明"

---
## 依赖与顺序
E0 → E1 → E2 → E3 → E4 → E5（串行）
⚠️ OBS-1 的 P4（observ_query）必须在 E1.1 之前完成，否则 `EvolutionPolicy.__init__` 缺 query 依赖

> 实现说明：E0–E5 已全部落地。单元测试整合进 `qcloud-copilot/tests/test_evo_generator.py`（覆盖 store / policy / guard / hooks / feedback 全部 DoD）；OBS-1 的 `observ_query` 已先行落地，依赖已满足；提交 footer 含 `TE-Audit: evo-1`。
