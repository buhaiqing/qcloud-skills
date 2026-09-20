# 2026-09-20 Harness / Loop Engineering 审计 — 会话记录与未关闭项登记

## 背景

用户要求从 **Loop Engineering / Harness Engineering** 双视角评审 `qcloud-skills`，
随后要求「locate root cause, fix it」，并**以 GCL（Generator-Critic-Loop）流程执行**。

本会话执行了 3 个 CR、8 次独立 Critic 评审（每轮每 CR 两个不同角度）、以及编排者自身的
独立复现验证。

## 结论（一句话）

> **这套 harness 度量的是「机制是否存在」，而非「机制是否生效」。**
> 全仓没有任何一个 gate 断言「某个循环产出了非空结果」，因此空产出与正常工作完全不可区分。

## 根因

> **仓库里每个契约都有两端（生产者↔消费者、声明↔接线、规范↔实现），而没有任何检查断言两端一致。**

10 个已确认缺陷是**同一个缺陷**：

| # | 声明端 / 生产者端 | 实现端 / 消费者端 |
|---|---|---|
| 1 | `write_trace()` — 已在 `4e8e77b` 修好 | `_bulk_update():120` — 同 bug 原封不动 |
| 2 | `eval_queries.json` — 29/36 无 `intent` 字段 | `harness_router.py:71` 读 `intent` |
| 3 | `evidence_kernel.py:78` 写 `evidence-*.jsonl` | `check_kpi_gates.py:63` glob `evidence-*.json` |
| 4 | `Makefile` 定义 9 个门禁目标 | 3 个 workflow **无一调用 `make`** |
| 5 | `validate_error_tables.py` docstring 自称 *"CI gate"* | 无任何 workflow 引用 |
| 6 | 14 个文件命名 `test_*.py` | `discover -p "*_test.py"` |
| 7 | AGENTS.md P0：*"≥ 10 个错误码"* | validator 查 5 项结构，**不查数量** |
| 8 | `kpi-pattern.md` 标 KPI#7 `CI-hooked ✅` | 该 gate 不在任何 CI |
| 9 | `gcl_runner.py:726` 传 `trace_path` 形参 | `write_trace` 的 `patterns_path` 落空 → 写已提交 store |
| 10 | CI 注释称 run_id 隔离了 smoke 记录 | glob `evidence-*.json*` 照样匹配；且测试套件另铸 17 条 |

**8 个循环在跑、产出为零或产出为噪声，且没有任何地方因此报错。**

## 时间线

| 时间 | 事件 |
|---|---|
| 23:05 | 评审启动：3 个 explorer 子 Agent 并行（Loops / Harness / Skill 契约） |
| 23:15 | 编排者独立复现关键缺陷；3 个 explorer **全部空报告返回**（6 次尝试，见下「环境限制」） |
| 23:20 | 编排者接管全部评审；CR-1 `kpi-gate-integrity` Generator 启动 |
| 23:18 | CR-2 `reflexion-loop-emptiness` Generator 启动；commit `9bca8fc` |
| 23:34 | **Round 1 Critic**：CR-1 = NEEDS-WORK/BLOCKER；CR-2 = NEEDS-WORK/BLOCKER |
| 23:57 | Round 2 Generator 双发；commit `737e722`、`30744b7`（CR-2）、`f92f633`（CR-1） |
| 00:11 | **Round 2 Critic**：CR-1 = BLOCKER/NEEDS-WORK；CR-2 = BLOCKER/NEEDS-WORK |
| 00:2x | 编排者判定「每轮修复都引入同等级新缺陷」→ 提交人工决策 |
| — | 用户裁定 **Plan A**：停止打补丁，改做根因 CR |
| 00:3x | CR-3 `artifact-isolation` 派出；Generator 停滞被看门狗终止（未 commit 的 7 文件在盘） |

## 已交付

| commit | CR | 说明 |
|---|---|---|
| `9bca8fc` | CR-2 R1 | `_bulk_update` 修剪了首次出现的 pattern，store 结构性空转 |
| `e8ac19d` | CR-1 R1 | KPI gate 改为按所属 skill 评分 + 读真实证据流 |
| `737e722` | CR-2 R2 | 计数改为 distinct traces；不再修剪本轮观测项；cap 落实 |
| `30744b7` | CR-2 R2 | store 段落空行；重算后重建 store |
| `f92f633` | CR-1 R2 | KPI gate 读真实证据流与真实路由基线 |

**独立验证（编排者亲自复现，非采信 subagent 报告）：**

```
CR-2 修复前:  New patterns: 1  Pruned(count<3): 1  Total patterns: 0  Total hits: 0
CR-2 修复后:  加 trace A: count=1 → B: count=2 → C: count=3 → D: count=4
             重复运行: 文件 UNCHANGED（幂等）
CR-1 修复前:  avg top1=14.72%（一个常量，非测量值）
CR-1 修复后:  avg top1=28.28%（16 个可评分 skill 口径），真实 fallback=51.64%
```

## 未关闭项登记

> 全部经 Critic 或编排者实测复现。**本轮未修**，作为独立 CR 排队。

### A. 门禁接线（无任何 CR 认领）

| ID | 现象 | 证据 | 严重度 |
|---|---|---|---|
| **H-01** | `validate_error_tables.py` docstring 自称 "CI gate"，但 Makefile / CI / pre-commit / `validate_local` **引用数均为 0**；功能完好（跑出 `31 skills, 530 rules, 0 violations`） | `grep -c validate_error_tables` 四个接入点全 0 | 🔴 |
| **H-02** | CI 静默排除 29% 的测试：`discover -p "*_test.py"` 不匹配 `test_*.py` | `*_test.py`→624 tests OK；`test_*.py`→**257 tests 被排除**（且全绿） | 🔴 |
| **H-03** | AGENTS.md P0「≥10 错误码」**不可机检**：`validate_error_tables.py` 查 5 项结构、不查数量 | 其自身输出 `OK qcloud-test-ops rules=0` —— 0 条错误码判 OK | 🔴 |
| **H-04** | pre-commit 从未安装：`core.hooksPath` 未设置，`.git/hooks/` 只有 `*.sample` → `check_idempotency` 与 `check_requestid_capture` **在任何地方都不执行** | `.githooks/pre-commit` 首行写着 `Install: git config core.hooksPath .githooks` | 🔴 |
| **H-05** | **没有任何 workflow 调用 `make`** → 整条 Makefile 门禁链（validate/registry/golden/kpi/kpi-gates/manifest/reflexion-update）**仅存在于人手敲** | 逐个 workflow grep `make` 无命中 | 🔴 |
| **H-06** | `make all` 在 `validate` 阶段就死于 pre-existing ruff RUF059（`cadl_lint_test.py:159,214`）→ **走不到 `reflexion-update`** | Critic-2R2-B 实测，标注 pre-existing | 🟠 |
| **H-07** | 16 个 CI 步骤中 3 个 `continue-on-error: true`（affected-skills / quality-score / pattern-anomaly） | `.github/workflows/validate-skills.yml` | 🟠 |
| **H-08** | 24 个脚本无任何调用方（部分可能是设计给人手跑的 CLI） | 全仓引用扫描 | 🟡 |

### B. 循环与状态

| ID | 现象 | 证据 | 严重度 |
|---|---|---|---|
| **H-09** | `.runtime/blackboard/` **355 个 session 文件全部 `status: active`，无一关闭**；`blackboard.py:230` 有 `set_status()` 但**无任何调用方写终态** | `Counter({'active': 355})`；约 340 个来自测试（106+136+48 集中在 7/20、7/25、7/26） | 🟠 |
| **H-10** | 测试直接写**生产 runtime 目录**，夹具与真实会话在磁盘上不可区分 | 同上；另见 CR-1 BLOCKER-2（测试写 17 条证据记录） | 🟠 |
| **H-11** | `audit-results/evidence-local.jsonl` 只追加、无轮转、被 gitignore → **被测流不可复现**（同一 worktree 内先后测到 550 / 357 / 153 行） | Critic-1B 全仓 grep 未找到任何 truncate/rotate 逻辑 | 🟠 |
| **H-12** | Reflexion store 的行容量与 51 行样板耦合：CR-3 Generator 实测「多加 2 行 header → 行平衡从 150 降到 149 → `>150` 降级触发器静默失效」 | CR-3 Generator 停滞前最后一条推理 | 🟡 |

### C. KPI 一致性与可博弈性（CR-4 范围）

| ID | 现象 | 证据 | 严重度 |
|---|---|---|---|
| **H-13** | `CI-hooked ✅` 对 KPI#1/#2 为**假**：escape 在任何证据被读取前短路 → 两个安全 KPI **永不可能在 CI 变红** | `rm -f audit-results/evidence-*; GATE_REQUIRE_EVIDENCE=0 python3 scripts/check_kpi_gates.py` → `skip`, rc=0 | 🔴 |
| **H-14** | workflow 中解释 escape 的注释**事实错误**：声称「CI 检出无证据流，只会有 smoke 那一条」，实际前序 unit-test 步骤铸了 **17 条** | fresh clone：unittest → `wc -l` = 17 → 去掉 escape → `✅ pass, 17 record(s) valid` | 🔴 |
| **H-15** | **删掉一个 skill 目录反而让两个指标都变好**：`qcloud-apigw-ops` 移除 → scoreable 15/**30**，`30>=30` 恰好通过半量守卫 → top1 28.28%→**30.16%**、misdeleg 15.21%→11.78% | Critic-1R2-A 实测 | 🟠 |
| **H-16** | `kpi-pattern.md:161` 声称「缺失/空/超龄的证据流 FAILS」—— 在 escape 生效时（**正是 CI 的环境**）全部 `skip` | 同上 | 🟠 |
| **H-17** | AGENTS.md CADL `L24` 保留了已被修正的错误数字 `10.3%（48/466）`，而 `kpi-pattern.md` 已改为 `9.87%（46/466）` → 两份受版本控制文档互相矛盾 | `grep -rn "48/466" .` → AGENTS.md:165、spec:258 | 🟠 |
| **H-18** | spec 的 CR note 仍写 `router_min_top1_accuracy 0.10` 与「derived `1-target` 预算」，而代码已改为 `0.28` / 显式 `router_max_misdelegation 0.16` | `docs/superpowers/specs/2026-07-28-...design.md:258,260` | 🟠 |
| **H-19** | CI 尾行把安全类 skip 与信息类 skip 合并计为 `skipped (informational)` | `check_kpi_gates.py:346` | 🟡 |
| **H-20** | `evidence_min_records: 10` 与 `evidence_max_age_days: 90` **两个阈值从未在真实数据上触发过** | 真实流：`OK: 357/550 record(s) valid, 0 aged-out` | 🟡 |

### D. 产物格式（CR-3 范围，部分未完成时保留在此）

| ID | 现象 | 证据 | 严重度 |
|---|---|---|---|
| **H-21** | `\|` 出现在 `command`/`error`/`fix` → 8 列变 9 格 → `Count` 读错列、`error` 被截断 → prune 见陈旧键 → 删除 → merge 重加 → **每轮同时报 `Retired: 1` + `New patterns: 1`（Round 1 原 bug 复活）** | 实测 `\|` → `len(cells)=9`；`command` 由 `gcl_runner` 从实际 shell 命令构造，管道符是常态 | 🔴 |
| **H-22** | 文件名含空格 → `sources` 空格分隔被切碎 → **count 每轮 +1**（count 再次成为「扫描次数」的函数，`--promote` 可伪造） | `ev il trace.json`：run1 count=1 → run2 count=**4** | 🔴 |
| **H-23** | R3 gate 在 line cap **之前**求值，且 `missing` 两侧对同一列表求 key 恒为空 → cap 丢弃观测项仍 exit 0 | 250 traces → `Dropped (cap 200): 99`，**exit 0**，99 条观测键消失 | 🔴 |
| **H-24** | `merge()` 对**无 sources 集合**的行把 `count` 重置为 1；`reflexion_store.store_failure_pattern()` 是**第三个写者**、从不记录 sources | `count=10` 行 + 一条新 trace → `count=1` | 🔴 |
| **H-25** | 已发布的 CLI 接口被打崩：`reflexion_retrieve retrieve --json` → `TypeError: Object of type set is not JSON serializable` | `reflexion_retrieve.py:279`；**无测试覆盖 `--json`**，故发布 | 🔴 |
| **H-26** | `enforce_line_cap` 无 `max_lines` 参数 → warm 层被静默压到 200 行而非其声明的 500（`WARM_LIMIT`/`COLD_LIMIT` 成为不可达常量） | `reflexion_store.py:145`；300 行追加 warm → 152 行 / 200 行 | 🟠 |
| **H-27** | store 内嵌的自我说明仍在教 Round 2 已废弃的语义（"If existing: increment count" / "prune count<3"） | `failure_pattern_extract.py:628-629` 渲染进每个重建的 store | 🟠 |
| **H-28** | `write_trace()` 在 cap 处静默驱逐已存 pattern，返回值被 `gcl_runner.py:726` 丢弃 | capped store + 1 次 `write_trace` → `True`，行数不变，一条 pattern 消失 | 🟠 |

## 人工决策

### D-1（已裁定）Plan A — 停止打补丁，改做根因 CR

**背景**：两轮修复**各自引入了同等级的新 BLOCKER**，且全部落在同一层。

```
Round 1 缺陷      → Round 2 修复        → Round 2 新缺陷
──────────────────────────────────────────────────────────
空产出像成功       → 加 R3 gate          → gate 在 cap 之前，仍 exit 0      (H-23)
计数随次数膨胀     → 改 distinct sources → sources 空格分隔，遇空格再次膨胀  (H-22)
                                        → Markdown 表格存储，遇 | 整行崩坏   (H-21)
已提交文件被测试写 → (未修)              → 单测仍写，每行宽度无界增长        (H-09/H-10)
```

**裁定**：Plan A。CR-3 `artifact-isolation` 修根因（路径隔离 + 格式），不再在旧 CR 上追加补丁。

### D-2（**待您裁定**）CI 是否应对证据流设门禁

Critic-1R2-A 指出 Round 2 实际上**替您选了一个政策而未曾标明这是选择**：

- **A 案**：证据是**本地监控信号**，不是合并门禁。接受「KPI#1/#2 永不在 merge 时执行」，但文档必须大声说清，且 CI 注释必须改（**现在是事实错误的**，见 H-14）。
- **B 案**：CI 对一份**已提交的 fixture** 执行门禁 —— 验证的是「安全规则本身还能不能开火」，不是集群行为。成本约 1 个 fixture 文件 + 4 行 workflow。

**Critic 推荐 B**，理由：`audit-results/` 被 gitignore 后，**一个把 `leak_checked` 改成 false 的 PR，CI 抓不到、本地也抓不到**（本地流里只有 PR 之前的代码铸的记录）。

**编排者倾向 B**，但新增受版本控制的 fixture 属策略决定，**未执行，等裁定**。

## ADR 候选

两项运行时拓扑决策，按 AGENTS.md「影响 >1 子系统 / 运行时拓扑 → ADR」应走 ADR，
**本会话未创建 ADR 文件**（决策未定，创建 TBD 的 ADR 只是噪声）：

| 候选 | 内容 | 阻塞于 |
|---|---|---|
| **ADR 候选 1** | 证据流（`audit-results/evidence-*.jsonl`）应否进入版本控制、由谁生成（CI vs 本地） | D-2 |
| **ADR 候选 2** | Reflexion store 应生成到 `.runtime/`，而 `docs/failure-patterns.md` 降级为**显式提升的快照**（当前它同时是构建产物与受版本控制的 agent 输入，这是 H-09/H-10/H-21 的共同土壤） | CR-3 完成后 |

## CADL 经验（可复用）

1. **契约两端必须校验接缝。** 每个契约都有声明端与实现端；不测接缝，两端就会漂移，
   而漂移是不可见的。→ 建议落地 `scripts/check_gate_wiring.py`（4 项确定性检查：
   死门禁 / 未收集测试 / 清单一致 / 生产者↔消费者文件名匹配）。

2. **没有阈值的 gate 会把常量报成 PASS。** 指标若读取语料中普遍缺失的字段，会退化为常量；
   gate 若无阈值，则把这个常量报告为 ✅。落地前先统计字段**存在率**，阈值取自**实测基线**。

3. **修复必须打在**构建实际执行的那条路径**上。** `4e8e77b` 正确诊断了 bug，却只修了
   `write_trace()`；`Makefile:40` / `make all` 走的 `_bulk_update()` 原封不动。
   为修好的那条路径写了测试并通过，构建执行的那条仍在删光一切。

4. **主观保证不是证据。** 两轮修复均在「测试全绿」的状态下带着 BLOCKER。
   唯一有效的证据是**把修复 revert 掉，证明测试会失败**。

## 环境限制（本会话，非仓库缺陷）

- **subagent 最终文本一律丢失**：先后 6 次返回 `Done.` / `Idle.` / `Standing by.` / `No action taken`
  （其中一次实际已完成并 commit）。**绕行方案**：要求 Critic/Generator 把报告写入
  `.runtime/gcl/*.md`，由编排者读文件 —— 这条路可行，但该目录 **gitignored**，
  worktree 清理即丢失，故本文件收录全部结论与证据。

- **一次生成器停滞**：CR-3 Generator 在深度推理中被看门狗终止（600s 无输出），
  7 个文件的未提交成果留在盘上。
