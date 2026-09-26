# Harness Engineering P1 Remediation — Spec & Plan

> 状态：Phase 1 落地（spec+plan 撰写，backlog 排序）；Phase 2-4（实际修复）TBD。
> 关联 P0 spec：`docs/superpowers/specs/2026-09-26-harness-p0-remediation-design.md`（P0 已落地的 5 项 CR）
> 关联审计：本 spec 是 P0 spec §10 提到的 `harness-p1-remediation.md`
> 关联 commit：TBD（本 spec 仅设计，不附代码变更）

## 1. 背景与问题

P0 spec 修复了配置漂移（H-100）、测试污染（H-10 同族）、路径遍历（H-52）、CI 结构（CR-3）、沉默脚本（H-101）共 5 项。剩余 5 项 backlog 都是"防御层已搭好但内部逻辑仍有 silent failure"的纵深问题——CI 表面绿，但深入看仍是欺骗自己的报警系统。本 spec 排优先修其中 **3 项（H-50 / H-53 / H-54）**；H-46 / H-47 因前置分析不足，列入 Phase 6-7 单独 spec。

| ID | 一句话 | 优先级 | 状态 |
|---|---|---|---|
| **H-54** | kpi1 runbook V4 自相矛盾："don't add escape" 与 CI 实际使用 `GATE_REQUIRE_EVIDENCE=0` 冲突 | **P1-A** | 设计 |
| **H-50** | KPI step fire-side 只能检测 KPI 全局 fail；单条规则降级（数据流死、KPI 静默 skip）不会触发退出码变化 | **P1-A** | 设计 |
| **H-53** | Ratchet granularity 假论据——`router_min_top1_accuracy` 离 baseline < 1pp，ratchet 在噪声带上即触发，无 meaningful protection | **P1-B** | 设计 |
| H-46 | `--layered store` 溢出 cold 区后无法重跑（`cd` 写到 cold 路径而 store 还在 hot 路径，store fail 后 cold 副本变孤儿） | P1-C | TBD 分析 |
| H-47 | "validate-before-validated-object" 模式第 4 次出现（demotion 写入发生在 self-verify 之后） | P1-C | TBD 分析 |

## 2. 核心原则

本 spec 修复 3 项都必须满足：

1. **No silent degradation (H-50)**：每个 KPI 函数返回 (status, detail, note) 已存在，但聚合步骤忽略 `status=skip` 的可见性。修复必须让"任一规则 skip → 退出码非 0（warn 级别）"。
2. **No contradictory runbooks (H-54)**：runbook 不可教 CI 实际使用的 escape。修复必须删除 V4 段落中的 `GATE_REQUIRE_EVIDENCE=0` 教程，并明确说明 CI 怎么处理的（实际是 CR-3 拆 job 后，`kpi-gates` job 依赖 committed fixture 而不是环境变量）。
3. **No false-protective ratchets (H-53)**：ratchet 必须能区分"回归"和"噪声"。修复必须给 ratchet 加 "buffer zone"（baseline + noise band），baseline 上下的 ratchet 才有效。

## 3. 解决方案

### 3.1 H-54: kpi1 runbook V4 段落删除 escape 教程

**症状**：`docs/harness-engineering/runbooks/kpi1-leak-checked-failure.md` V4 段：

> V4: No evidence stream at all. The gate read zero files. Either this machine has never run the harness [...] **that is why CI runs the gate with `GATE_REQUIRE_EVIDENCE=0`** (an explicit, visible skip). **Do not add that escape to a machine that is supposed to be emitting evidence**; it is not a fix for an empty stream.

**问题**：
1. "Do not add that escape" 与 "CI runs the gate with `GATE_REQUIRE_EVIDENCE=0`" 自相矛盾。
2. CR-3 拆 `kpi-gates` job 后，CI **不再**使用 `GATE_REQUIRE_EVIDENCE=0`——而是依赖 committed fixture `scripts/fixtures/evidence/evidence-safety-clean.jsonl`。runbook 没跟上这次重构（stale since CR-3）。
3. 教 escape hatch = 教 on-call 写一个会让 CI 静默绿的环境变量。这是 L25（证据 > 推断）的反例：runbook 给人"安全逃路"，但不告诉你 escape 失效后没人能看见。

**修复**：

| 改动 | 文件 | 动作 |
|---|---|---|
| 删除 "Do not add that escape" 整句 | `runbooks/kpi1-leak-checked-failure.md` V4 | 删除 |
| 替换 "that is why CI runs the gate with `GATE_REQUIRE_EVIDENCE=0`" | 同上 | 替换为 "CI uses the committed fixture under `scripts/fixtures/evidence/evidence-safety-clean.jsonl` (see the `kpi-gates` job in `validate-skills.yml`) — never `GATE_REQUIRE_EVIDENCE=0`" |
| 加注脚解释 `GATE_REQUIRE_EVIDENCE=0` 实际语义 | 同上 | "Only available for *machine-local, evidence-free* repos. CI never sets it. The CR-3 job split means a red `kpi-gates` job = `kpi-gates` actually ran and rejected — the same evidence stream cannot be both 'required' and 'skippable' on the same workflow." |

**DoD**：grep `GATE_REQUIRE_EVIDENCE` 在 kpi-pattern.md / kpi1/2/3/7 runbooks / validate-skills.yml / check_kpi_gates.py 五处出现次数一致（除非有意为之）；CI 评论引用 runbook 路径时不再提到 `GATE_REQUIRE_EVIDENCE=0`。

### 3.2 H-50: 单条规则 fire-side 检测

**症状**：`scripts/check_kpi_gates.py` 当前聚合逻辑（伪代码）：

```python
results = [kpi1(), kpi2(), kpi3(), kpi7()]  # 每个返回 (pass/fail/skip, ...)
status = "pass" if all(r[0] == "pass" for r in results) else "fail"
sys.exit(0 if status == "pass" else 1)
```

**问题**：当 `GATE_REQUIRE_EVIDENCE=0` 让 KPI#1/#2 返 `skip`（历史上 CI 真这么做），而 KPI#3 / KPI#7 是 `pass`，聚合 `status == "pass"` → CI 绿。但 KPI#1/#2 实际**没跑**。这种"silent skip"是 H-50 的本质。

CR-3 拆 job 后这个症状缓解（CI 现在用 fixture 而不是 escape），但 `check_kpi_gates.py` 本体**仍然会 silent skip**——任何未来误用 `GATE_REQUIRE_EVIDENCE=0` 都不会被检测。

**修复**：

```python
def aggregate(results: list[KpiResult]) -> AggregateVerdict:
    """H-50: 任一规则 status != pass 都升级为 non-pass."""
    statuses = [r.status for r in results]
    n_skip = sum(1 for s in statuses if s == "skip")
    n_fail = sum(1 for s in statuses if s == "fail")
    n_pass = sum(1 for s in statuses if s == "pass")
    if n_fail > 0:
        return AggregateVerdict(status="fail", exit_code=1,
                                note=f"{n_fail} rule(s) failed")
    if n_skip > 0:
        # KEY H-50 修复: skip 也是可见的 degradation
        return AggregateVerdict(status="warn", exit_code=1,
                                note=f"{n_skip} rule(s) skipped (silent degradation)")
    return AggregateVerdict(status="pass", exit_code=0, note="all pass")
```

**退出口语义变化**：
| 旧 | 新 |
|---|---|
| `all pass` → exit 0 | `all pass` → exit 0 |
| `any fail` → exit 1 | `any fail` → exit 1 |
| `any skip, rest pass` → exit 0（静默） | `any skip, rest pass` → exit 1 + 明确的 note |

**副作用处理**：
- 任何测试 fixture 用 `GATE_REQUIRE_EVIDENCE=0` 期望 `exit 0` 的，会变 `exit 1`。需要同步更新 fixture。
- 主仓库 `make kpi-gates` 不设 `GATE_REQUIRE_EVIDENCE=0`，baseline 是 KPI#1/#2 evidence 真读，所以现状下行为不变。但 CI 的 `kpi-gates` job 现在依赖 committed fixture，**绝不能设**这个变量——加测试断言：
  ```python
  def test_kpi_gates_job_never_sets_GATE_REQUIRE_EVIDENCE():
      """H-50 + CR-3: kpi-gates job 必须依赖 fixture, 不用 escape."""
      yaml = (WORKFLOWS / "validate-skills.yml").read_text()
      assert "kpi-gates" in yaml
      # 找 kpi-gates job 段
      job_section = re.search(r"kpi-gates:\s*\n([\s\S]+?)(?=^\S|\Z)", yaml, re.MULTILINE)
      assert job_section
      assert "GATE_REQUIRE_EVIDENCE" not in job_section.group(0), \
          "kpi-gates job must not set GATE_REQUIRE_EVIDENCE (CR-3 + H-50)"
  ```

**DoD**：
- `aggregate()` 区分 `fail` / `warn` / `pass`，`warn` 触发 exit 1。
- CI `kpi-gates` job YAML 不含 `GATE_REQUIRE_EVIDENCE` 字符串（grep 验证）。
- 测试：`test_aggregate_skip_returns_exit_1` + `test_aggregate_fail_returns_exit_1` + `test_aggregate_pass_returns_exit_0` + `test_kpi_gates_job_never_sets_GATE_REQUIRE_EVIDENCE`。

### 3.3 H-53: ratchet granularity + buffer zone

**症状**：`kpi-pattern.md` 段 obs. 8：

> The ratchet's headroom is only 0.2755pp, so that single query trips the floor in **15 of the 16 scoreable skills**; `qcloud-cvm-ops` alone absorbs one flip, and a second trips it. The ratchet is therefore not a guard against *meaningful* regression — for nearly the whole fleet it fires on the smallest possible move.

这是诚实的自我诊断，但没改。`router_min_top1_accuracy = 0.6778` 离 baseline 0.7033 只有 2.55pp，而单 query 翻转就是 1.5pp——ratchet 在统计噪声带上。

**修复（两层）**：

1. **Buffer zone 概念**：每个 ratchet 阈值附带一个 `noise_band`（典型 1.5-2pp for top-1 accuracy）。ratchet 的有效触发区是 `[baseline - noise_band - meaningful_regression, ceiling]`：
   - 低于 `baseline - noise_band - meaningful_regression` → 真回归，fail
   - 在 `[baseline - noise_band, baseline]` 区间 → 噪声，**不** fail（仅打印 note）
   - 高于 `baseline` → 提升，不 fail

2. **Schema 变化**：`assets/shared/thresholds.json` 给每个 ratchet 键加 `noise_band`：

   ```json
   {
     "router_min_top1_accuracy": 0.6778,
     "router_min_top1_accuracy_noise_band": 0.015,
     "router_min_top1_accuracy_meaningful_regression": 0.025
   }
   ```

3. **打印 gap 到 report**：
   ```
   KPI#7 router: pass | measured=0.7051 (ratchet=0.6778, ceiling=0.16, target=0.70)
     noise_band=0.015 → effective fail threshold = 0.6778 - 0.015 - 0.025 = 0.6378
     gap to fail threshold = 0.7051 - 0.6378 = +0.0673 (safe)
     gap to target = 0.7051 - 0.70 = +0.0051
   ```

**反例警告**：buffer zone 是 **统计意义上的**（per fleet, per query set），不是 per-skill。qcloud-cvm-ops 单 skill sample size = 27，所以 noise band 应该按"qcloud-cvm-ops 1pp"算，而不是 fleet-wide 1.5pp。Phase 3 实施时要单独算 per-skill noise band。

**DoD**：
- `kpi7_router_confusion()` 读三个键：`router_min_top1_accuracy` / `noise_band` / `meaningful_regression`
- effective fail threshold = `min_top1 - noise_band - meaningful_regression`
- 实测值在 `(effective_fail, min_top1)` 区间 → `pass` 但打印 noise-zone note
- 实测值 < effective_fail → `fail`
- 实测值 ≥ min_top1 → `pass` no note
- 测试：`test_router_in_noise_zone_passes` + `test_router_below_effective_fails`

### 3.4 H-46 / H-47（仅 scope 定义，不实施）

- **H-46 (--layered store cold overflow)**：前置分析需要 trace 实跑一遍，验证"cold 副本变孤儿"是否真发生还是误报。本 spec 仅记录，**Phase 4 单独 spec**。
- **H-47 (validate-before-validated-object)**：与历史 3 个同源 bug 一并审计；建议独立 spec `validate-ordering-pattern.md`，**Phase 5**。

## 4. 文件清单

| 文件 | 类型 | 状态 | 说明 |
|---|---|---|---|
| `docs/harness-engineering/runbooks/kpi1-leak-checked-failure.md` | 文档 | ⚠️ 改动 | H-54：V4 段删除 escape 教程 |
| `scripts/check_kpi_gates.py` | gate | ❌ 改动 | H-50：`aggregate()` warn 路径 |
| `scripts/check_kpi_gates_test.py` | 测试 | ❌ 新增 | H-50：4 个测试 |
| `scripts/test_kpi_gates_yaml_gating.py` | 测试 | ❌ 新增 | H-50 + CR-3：`test_kpi_gates_job_never_sets_GATE_REQUIRE_EVIDENCE` |
| `assets/shared/thresholds.json` | 配置 | ❌ 改键 | H-53：加 `noise_band` / `meaningful_regression` |
| `scripts/check_kpi_gates.py` | gate | ❌ 改动 | H-53：读 buffer zone 键 |
| `scripts/check_kpi_gates_test.py` | 测试 | ❌ 新增 | H-53：3 个测试 |
| `docs/harness-engineering/kpi-pattern.md` | 文档 | ⚠️ 改动 | H-53：obs. 8 加 "noise band is now buffer zone" 注脚 |
| `docs/superpowers/specs/2026-09-26-harness-p1-remediation-design.md` | spec | ✅ 本文件 | 本文档 |
| `docs/superpowers/specs/2026-09-26-validate-ordering-pattern.md` | spec | ❌ TBD | H-47 独立 spec |
| `docs/superpowers/specs/2026-09-26-layered-store-cold.md` | spec | ❌ TBD | H-46 独立 spec |

## 5. 函数签名

```python
# scripts/check_kpi_gates.py
@dataclass(frozen=True)
class KpiResult:
    rule: str           # "kpi1_leak" / "kpi2_token" / ...
    status: str         # "pass" / "fail" / "skip"
    detail: str
    note: str = ""

@dataclass(frozen=True)
class AggregateVerdict:
    status: str         # "pass" / "fail" / "warn"
    exit_code: int      # 0 / 1 / 1 (H-50: warn 也 exit 1)
    note: str

def aggregate(results: list[KpiResult]) -> AggregateVerdict:
    """H-50: 任一 status != pass 都升级."""

def kpi7_router_confusion(cfg: dict, *, evidence) -> KpiResult:
    """H-53: 读 noise_band + meaningful_regression."""

# scripts/test_kpi_gates_yaml_gating.py
def test_kpi_gates_job_never_sets_GATE_REQUIRE_EVIDENCE() -> None:
    """CR-3 + H-50: kpi-gates job 必须依赖 fixture, 不用 escape."""
```

## 6. Self-check / 自验

### H-54
- [ ] `grep -c GATE_REQUIRE_EVIDENCE docs/harness-engineering/runbooks/*.md` 五处一致（除非有意）
- [ ] `validate-skills.yml` kpi-gates job 段不含 `GATE_REQUIRE_EVIDENCE`
- [ ] kpi1 runbook V4 段不再教 escape，只说 fixture

### H-50
- [ ] `aggregate([skip, pass, pass])` → `exit_code=1` (was 0)
- [ ] `aggregate([fail, pass, pass])` → `exit_code=1`
- [ ] `aggregate([pass, pass, pass])` → `exit_code=0`
- [ ] `aggregate([pass, skip, pass])` → `exit_code=1` + "1 rule(s) skipped"
- [ ] YAML gating test 通过

### H-53
- [ ] 实测值在 `[effective_fail, min_top1]` → pass + noise note
- [ ] 实测值 < effective_fail → fail
- [ ] 实测值 ≥ min_top1 → pass no note
- [ ] 缺 `noise_band` 键 → GateConfigError（CR-2 fail-closed 一致性）
- [ ] kpi-pattern.md obs. 8 注脚更新

## 7. Phase 清单（PLAN）

- [x] **Phase 0**: 写本文档（spec + plan）。
- [ ] **Phase 1（H-54 runbook 修订）**: 改 `runbooks/kpi1-leak-checked-failure.md` V4 段；grep 验证；commit。
- [ ] **Phase 2（H-50 aggregate warn 路径）**:
  - [ ] TDD 红：`scripts/check_kpi_gates_test.py` 加 4 个测试
  - [ ] TDD 绿：`check_kpi_gates.py:aggregate()` 区分 warn
  - [ ] 加 `test_kpi_gates_yaml_gating.py`
  - [ ] ruff + 全量 pytest
  - [ ] commit
- [ ] **Phase 3（H-53 buffer zone）**:
  - [ ] 算 noise band（per-skill）—— 用真实 evidence stream 数据
  - [ ] `thresholds.json` 加 2 键（router 相关）
  - [ ] TDD 红：3 个 kpi7 测试
  - [ ] TDD 绿：kpi7 读 buffer zone 键
  - [ ] kpi-pattern.md obs. 8 注脚更新
  - [ ] ruff + 全量 pytest
  - [ ] commit
- [ ] **Phase 4（H-46 spec stub）**: 写 `2026-09-26-layered-store-cold.md` 仅 scope 设计。
- [ ] **Phase 5（H-47 spec stub）**: 写 `2026-09-26-validate-ordering-pattern.md` 仅 scope 设计。
- [ ] **Phase 6（CADL 沉淀）**: 3 项变更涉及 L25 重述（"no escape hatch teaches"）+ L29（silent skip 模式）+ L30（ratchet noise band）——按 AGENTS.md §CADL 钩子行。

## 8. DoD / 验收标准

- [ ] H-54: kpi1 runbook V4 不再教 `GATE_REQUIRE_EVIDENCE=0`；CI job 也不设。
- [ ] H-50: `aggregate()` 区分 warn 路径；YAML gating 测试守护 kpi-gates job 不引入 escape。
- [ ] H-53: per-skill noise band 实测有效；obs. 8 注脚更新。
- [ ] ruff 零 error。
- [ ] pytest 全量通过（baseline 1077 + 新增 7 个）。
- [ ] SPEC §6 全部勾选。
- [ ] 主仓库 merge 后 `docs/execution-lessons.md` 追加 L29（silent skip pattern）+ L30（noise band）+ L31（CI job escape gating）。

## 9. 未决项 / 已知限制

- **H-50 修复会让历史 fixture 失败的概率上升**：任何用 `GATE_REQUIRE_EVIDENCE=0` 期望 exit 0 的 fixture 需要更新。Phase 2 跑测试时同步审计。
- **H-53 noise band 数值依赖 evidence stream 实测**：Phase 3 开工前先 `make evidence-stream-summary` 看 per-skill 分布；缺数据就推到 Phase 7。
- **H-46 / H-47 单独 spec 仅 scope 定义**：实际修复需要前置 trace + audit 工作，可能跨 1-2 个 sprint。

## 10. 关联引用

- P0 spec：`docs/superpowers/specs/2026-09-26-harness-p0-remediation-design.md` §10（"P1 spec 已 deferred"）
- KPI pattern：`docs/harness-engineering/kpi-pattern.md`（obs. 4 / 6 / 7 / 8 与本 spec 直接相关）
- kpi1 runbook：`docs/harness-engineering/runbooks/kpi1-leak-checked-failure.md`（H-54 直接修订目标）
- CR-3 commit：`21775e0`（kpi-gates job split，本 spec 依赖其结构）
- L25 / L26 / L28 引用：`docs/execution-lessons.md`（CADL 沉淀目标 L29-L31）