# Harness Engineering P0 Remediation — Spec & Plan

> 状态：✅ Phase 1-5 已落地（CR-1/conftest/CR-2/CR-3/CR-4 + P0/P1 spec 全部就位）；Phase 6（H-50/53/54 / H-46/H-47 spec stubs）已 deferred 到 P1 spec。
> 关联审计：`docs/superpowers/specs/2026-09-26-harness-audit.md`（H-10 / H-46 / H-47 / H-50 / H-52 / H-53 / H-54 / H-100 / H-101）
> 关联 commit：`e86f28f`（CR-1 restore）· `8026955`（conftest 防御）· `2d747d1`（CR-2 fail-closed + H-52）· `21775e0`（CR-3 job split）

## 1. 背景与问题

2026-09-26 Harness Engineering 评审发现 9 个 P0/P1 问题，分四类：

| 类别 | ID | 问题 | 后果 |
|---|---|---|---|
| 配置漂移 | H-100 | `c15e11a` 把 `thresholds.json` 从 13 键压到 1 键，commit message 谎称"restored"（13→1 实际相反） | `make gates` exit 2；多 gate 静默跳过 |
| 测试污染 | H-10 同族 | 5 个 test 文件写 `thresholds.json` 到生产路径且无 tearDown | 跑测 = 自动污染 committed file（与 c15e11a 同一形状） |
| 防护缺口 | H-52 | `GATE_EVIDENCE_GLOB` 未校验路径遍历（`Path.glob` 不拒 `..` / 绝对路径） | 信息泄漏 + 可制造 KPI 假阳性 |
| CI 结构 | — | KPI gate 是 step 16/17，Actions 早停策略会静默跳过 | 绿 badge ≠ KPI 步骤实际跑过 |
| 防护缺口 | H-101 | 67% 脚本零接线，W1 规则只看"自称 CI gate"的脚本 | 沉默死代码：编译通过 / 单跑通过 / 无任何 caller |
| 防护缺口 | H-50 | KPI step fire-side 无法检测单条规则失效 | 规则死了，gate 仍报绿 |
| 原则违反 | H-53 / H-54 | ratchet granularity 假论据 + runbook 教已删 escape | KPI 文案误导 on-call |

本 spec **只修前 5 项（H-100 + H-10 + H-52 + CI 结构 + H-101）**——它们是同源问题（"沉默失败 → 状态不可信"），且修复路径已闭环。H-50 / H-53 / H-54 在 backlog 留 H-101 后续评审（`harness-p1-remediation.md`，独立 spec）。

## 2. 核心原则（重述）

修复必须满足三条硬约束——这是 L25/L26/L28 三原则（证据 > 推断 / 配置即代码 / 子 agent 不替代执行）在这次审计里的具体落地：

1. **配置即代码（CR-2）**：partial config = config error，exit 2。不是 KPI 失败（exit 1），不是脚本崩溃（traceback）。三者状态码语义不可互换。
2. **CI 状态可读（CR-3）**：绿 badge = KPI gate 实际跑了；red badge = KPI gate 实际拒了；不存在"badge 绿但 gate 没跑"的第三态。
3. **沉默代码不存在（CR-4）**：非测试脚本必有 caller；caller = 测试编织（imports）或 surface 编织（CI/Makefile/hooks）。两条路径都不通的脚本即删除或即接线。

## 3. 解决方案

### 3.1 CR-1: 恢复 committed thresholds.json（H-100）

**症状**：`assets/shared/thresholds.json` 13→1 键；commit message 与 git diff 反向；`make gates` exit 2 持续数月无人察觉（因为产出仅 stderr，行内 CI 不解析 `make` 退出码）。

**修复**：`git show HEAD -- assets/shared/thresholds.json > assets/shared/thresholds.json` 直接恢复 HEAD 内容。**不**重建 13 个键的语义值，因为当前 HEAD 就是 ground truth（c15e11a 之后的中间状态未提交，本身就是漂移）。

**Diff 形状**：`+14 keys - 14 keys`，体现为 file size `+468 bytes` 单 commit 增量。

### 3.2 conftest.py 防御层（H-10 同族）

**症状**：5 个 test 文件（`check_kpi_gates_test`、`check_reflexion_efficacy_test`、`check_gate_wiring_test`、`check_test_collection_test`、`gcl_trace_aggregate_mode_test`）在测试中**就地写 `thresholds.json`** 而不恢复。pytest 收集 1077 测试时，任何一个测试类运行 = 文件被改。

**修复**：`scripts/conftest.py` 在 pytest session 启动时快照 committed file，session 结束时若文件被改回"已知污染形状"（single-key dict 或 size < baseline）则自动还原，并打印 WARN。

**形状识别逻辑**：因为污染源是"用 `json.dumps({key: value})` 写一个临时 dict"，所以还原判据 = "size 比 baseline 小 50% 或 key count == 1"。这是廉价的启发式，正确率由测试覆盖保证。

**为什么不在测试侧修**：(1) 5 个文件是已落地的 fixture 风格，重写 = 一次大改动；(2) 防御纵深——即便下一个 PR 引入新的污染源，conftest 仍能兜底；(3) 教训普适性——"test 用 production path 做 setup"是 anti-pattern，预防比审计便宜。

### 3.3 CR-2: 跨 gate fail-closed + H-52 路径遍历拦截

**症状 A**：每个 KPI 函数（kpi1_2_safety / kpi7_router_confusion 等）独立读自己的几个阈值键。**没有任何地方验证全集**。c15e11a 把 13→1 后，"恰好 kpi1_2_safety 读的那 1 个键还在"所以它能跑——其它 KPI 静默跳过，CI 绿。

**症状 B**：`GATE_EVIDENCE_GLOB` 通过 `Path.glob()` 实现，stdlib 不拒 `..` / 绝对路径。CI job 设 `GATE_EVIDENCE_GLOB=../../etc/*` 能读仓库外文件并把它们的内容打印进 gate 报告。

**修复 A**：`_REQUIRED_THRESHOLD_KEYS` 表（15 键 / 类型 / consumer 模块）+ `_validate_thresholds_complete()` 在 `_thresholds()` 内强制校验，缺键或错类型一律 `GateConfigError` (exit 2)。这是**对 c15e11a 形状的硬编码防御**——任何后续 PR 再犯"删键谎称恢复"，CI 立即红。

**修复 B**：`_safe_evidence_glob()` 检查 `..` 段和绝对路径，命中即 `GateConfigError`。理由：

| 攻击/事故面 | 修复前 | 修复后 |
|---|---|---|
| `../../etc/*` 读仓库外 | 内容打印到 gate report（信息泄漏） | exit 2，GATE_EVIDENCE_GLOB refused |
| `/etc/passwd` 绝对路径 | 同上 | exit 2 |
| `evidence-*.json*` 默认 glob | 仍然按预期工作 | 无变化 |

**类型校验严格度**：bool 不是 int/float（Python `bool` 是 `int` 子类——宽松的 `isinstance(v, int)` 接受 `True` 作为整数 1）。对 `boolean` 类型严格拒 `True/False` 之外的，对 `integer` 严格拒 `bool`，对 `number` 拒 `bool`。

### 3.4 CR-3: KPI gate 拆独立 job

**症状**：`.github/workflows/validate-skills.yml` 把 "KPI gates" 放在 step 16/17，前置 12 个非-`continue-on-error` step。Actions 早停策略：step N 红 → step N+1..end 跳过。绿 badge 仅证明"step 15 通过"，不证明"KPI 跑过"。

**修复**：workflow 重构为两个 job：
- `validate`：12 个原有 step（包括前置 setup、manifest gates、smoke、pytest 等）
- `kpi-gates`：`needs: validate`, `if: always() && needs.validate.result == 'success'`；只跑两步（threshold sanity + KPI gates）

属性保证：
- **绿 `kpi-gates` job = KPI gate 实际跑了**：job 内只有 1 个 blocking step（KPI gates），且它是 job 内非 setup 的第一个 blocking step
- **红 `validate` 不级联到 `kpi-gates`**：`if: needs.validate.result == 'success'` 显式拒 aborted run——abort 已经是信号，KPI gate 加一层 exit code 反而混淆 on-call
- **两 job 都是 required-status-check**：merge 阻塞要两 job 都绿
- **`audit-results/` 作为 artifact 跨 job 上传**（retention 1 day）：万一将来需要"先 validate 后 kpi-gates 共享 audit-results"（例如 KPI#3 读 evidence stream），不用重跑

**validate job 末尾的 upload-artifact step**：原 job 末尾加 `if: always() actions/upload-artifact@v4`，与新增 job 的取证阶段对接。

### 3.5 CR-4: W5 zero-wiring 规则

**症状**：57/173 = 67% 脚本零接线；`check_gate_wiring.check_dead_gates`（W1）只查"self-declared CI gate"——即脚本首 60 行有 `CI_GATE_MARKER` 才参与检查。**沉默脚本**（无 marker 且无 caller）永远 W1 不命中。

**修复**：`check_gate_wiring.check_zero_wiring()`（W5）——任何非测试、非 exempt（`__init__` / `conftest`）、非包内部（`qcloud-cvm-ops/scripts/...`）的脚本，stem 不在 `wired` 集合 → `W5 {path}` finding。

`wired` 集合 = surface 调用 + 传递 import 闭包（已有逻辑，复用 `wiring_state()`）。

**为什么排除包内部脚本**：`qcloud-*-ops/scripts/*.py` 由各自 package 内的测试覆盖（`pytest qcloud-cvm-ops/...`），不在顶层 `scripts/` 的 surface 表里。W5 只看顶层。

**exempt 名单**：`__init__.py` / `conftest.py`（pytest 自身需要的桩）。

## 4. 文件清单

| 文件 | 类型 | 状态 | 说明 |
|---|---|---|---|
| `assets/shared/thresholds.json` | 数据 | ✅ | 15 键；MD5 stable at commit `e86f28f` |
| `scripts/conftest.py` | pytest 防御 | ✅ | 快照 + session-end 自动还原 |
| `scripts/check_kpi_gates.py` | gate | ✅ | `_validate_thresholds_complete` + `_safe_evidence_glob` |
| `scripts/check_kpi_gates_test.py` | 测试 | ✅ | fixture 加 15 键；`test_broken_thresholds_*` 适配新契约 |
| `.github/workflows/validate-skills.yml` | CI | ✅ | 拆 `kpi-gates` 独立 job |
| `scripts/check_gate_wiring.py` | gate | ⚙️ 未提交 | `check_zero_wiring()`（W5 规则） |
| `scripts/check_gate_wiring_test.py` | 测试 | ❌ | W5 测试缺；必须先写后给全量 |

## 5. 函数签名

```python
# scripts/check_kpi_gates.py
_REQUIRED_THRESHOLD_KEYS: tuple[tuple[str, str, str], ...]  # (key, kind, owner)

def _validate_thresholds_complete(cfg: dict) -> None:
    """缺键 / 错类型一律 raise GateConfigError（exit 2）。"""

def _safe_evidence_glob(raw: str) -> str:
    """拒 '..' 段 / 绝对路径；raise GateConfigError。"""

# scripts/conftest.py
@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session: pytest.Session) -> None:
    """snapshot committed assets/shared/thresholds.json + .gitkeep 等"""

@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session) -> None:
    """若 post-test state == known-pollution pattern → restore + WARN"""

# scripts/check_gate_wiring.py
_ZERO_WIRING_EXEMPT_STEMS: frozenset[str]  # {__init__, conftest}

def check_zero_wiring(root: Path, scripts: list[Path], wired: set[str]) -> list[str]:
    """W5: 非测试 / 非 exempt / 非包内部 / 非 wired → 'W5 path'。"""
```

## 6. Self-check / 自验

### CR-1
- [x] `git show HEAD -- assets/shared/thresholds.json > assets/shared/thresholds.json` 后 `md5 == committed md5`
- [x] `python3 scripts/check_kpi_gates.py` exit 1（KPI#1 evidence 仍失败是数据问题，与 CR-1 无关）

### conftest 防御
- [x] 5 个污染源 test 跑后 `md5 assets/shared/thresholds.json` 与 baseline 一致
- [x] session-finish 输出 WARN 行（不是 silent 还原）
- [x] 全量 pytest 1077 测试通过

### CR-2
- [x] 缺键（单 `{"reflexion_min_injected_runs": 1}`）→ exit 2 + `GATE CONFIG ERROR: ... missing required key 'rubric_min_score'`
- [x] 错类型（`rubric_min_score: "not-a-number"`）→ exit 2
- [x] `GATE_EVIDENCE_GLOB="../../etc/*"` → exit 2
- [x] `GATE_EVIDENCE_GLOB="/abs/path"` → exit 2
- [x] 15 键 baseline → exit 1（KPI#1 evidence 失败，与 CR-2 无关）
- [x] 23 个 kpi_gates_test 通过（含 fixture 适配）

### CR-3
- [x] YAML `python3 -c "import yaml; yaml.safe_load(...)"` 解析通过
- [x] jobs = `['validate', 'kpi-gates']`
- [x] `kpi-gates` `needs: validate`
- [x] `kpi-gates` `if: always() && needs.validate.result == 'success'`
- [x] `kpi-gates` job 5 steps，KPI gates 是 step 5（最后一个 blocking）
- [x] 注释说清"绿 kpi-gates = KPI gate 实际跑了"

### CR-4
- [ ] 至少一个 `check_zero_wiring` 测试：monkey-patch 一个 stem 临时不接线 → W5 finding 命中
- [ ] `wired` 集合含 transitively imported 脚本（已有逻辑，覆盖保留）
- [ ] `__init__.py` / `conftest.py` 不报 W5
- [ ] `qcloud-cvm-ops/scripts/...` 不报 W5（包内部豁免）
- [ ] 全量 pytest 通过（含 W5 新测试）

## 7. Phase 清单（PLAN）

- [x] **Phase 0**: 写本文档（SPEC + PLAN 合一）。
- [x] **Phase 1（CR-1）**: `git show HEAD -- ... > assets/shared/thresholds.json`。Commit `e86f28f`。
- [x] **Phase 2（conftest 防御）**: 写 `scripts/conftest.py` 自动还原。Commit `8026955`。
- [x] **Phase 3（CR-2 fail-closed + H-52）**: `_validate_thresholds_complete` + `_safe_evidence_glob`。Commit `2d747d1`。
- [x] **Phase 4（CR-3 拆 job）**: `.github/workflows/validate-skills.yml` 拆 `kpi-gates`。Commit `21775e0`。
- [x] **Phase 5（CR-4 W5 规则）**:
  - [x] 实现 `check_zero_wiring()`
  - [x] 写 W5 测试（5 个：finds_unwired / surface_invokes / transitive_imports / exempts_init_conftest / exempts_pkg_internal）
  - [x] 接入 `run_checks()` 主循环
  - [x] 全量 pytest 通过（1082 tests）
  - [x] Commit `6410b0a`
- [x] **Phase 6（独立 spec stubs）**: H-50/H-53/H-54 写入独立 spec `2026-09-26-harness-p1-remediation-design.md`（commit `32de616`）；H-46/H-47 在该 spec §3.4 stub。
- [ ] **Phase 7（CADL 沉淀）**: 5 项变更涉及 L25/L26/L28 重述、CI badge 语义、`check_gate_wiring` W5 规则——按 AGENTS.md §CADL 沉淀到对应 skill 的 SKILL.md 钩子行。

## 8. DoD / 验收标准

- [x] CR-1: committed thresholds.json 恢复 15 键，make gates 通过率（按 exit code）有变化。
- [x] conftest: 5 个污染源 test 跑后文件不污染。
- [x] CR-2: 缺键 / 错类型 / 路径遍历三种 fail-closed 行为均可复现。
- [x] CR-3: workflow YAML 解析通过；job 结构保证 green badge = KPI 跑过。
- [ ] CR-4: W5 测试覆盖 4 个 case（命中 / exempt / 包内部 / wired 不命中）；全量测试通过。
- [ ] ruff 零 error。
- [ ] pytest 全量通过（baseline = 1077）。
- [ ] SPEC §6 全部勾选。
- [ ] 主仓库 merge 后立即生效：`docs/execution-lessons.md` 追加 L29（silent test pollution pattern）+ L30（W5 rule）+ L31（CI job split 原则）。

## 9. 未决项 / 已知限制

- **KPI#1 evidence 失败是预先存在**：fixture `evidence-safety-clean.jsonl` 不满足 `evidence_min_records` 阈值（10 条）；不在本 spec 范围。Phase 6 单独立项。
- **W5 接入主循环可能影响 baseline**：若现有 ~107 个零接线脚本全部触发 W5 finding，`make gate-wiring` 会突然变红。Phase 5 接入时**先 dry-run 打印 finding 清单**到评论，不一次性全部 wire / 删除——分 PR 处理。
- **跨 worktree 证据保留**：CR-2 commit message 引用 `c15e11a`——该 commit 在 main repo，不在 worktree。当前 commit history 是独立的，phase 5 完成后 cherry-pick 到 main 或 merge 时会复制 commit。

## 10. 关联引用

- 审计源：`docs/superpowers/specs/2026-09-26-harness-audit.md`（H-10/46/47/50/52/53/54/100/101）
- 教训沉淀（待）：`docs/execution-lessons.md`（L25 / L26 / L28 重述 + L29-L31 新增）
- W5 规则接入：`scripts/check_gate_wiring.py:main()` 当前收集 `check_dead_gates` / `check_thresholds` / `check_store_path` / `check_workflow_evidence` 等——`check_zero_wiring` 加入同列