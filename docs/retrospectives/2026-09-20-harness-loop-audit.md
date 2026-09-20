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
| 08:44 | 编排者接管：写本审计登记（`2c8aa70`），补 `AGENTS.md` L25、修正 L24 陈旧数字、`TODO.md` 加指针 |
| 08:47 | CR-3 Generator 恢复并提交 `724afc9` |
| 08:5x | 编排者独立复现 5 项此前损坏行为，全部通过（见 §D） |
| 09:0x | **CR-3 Round 1 Critic**：3A / 3B 均 NEEDS-WORK（**无 BLOCKER**，为三轮中最轻）；确认 H-21…H-28 全数关闭 |
| — | CR-3 Round 2 派出（处理 H-29…H-39）；登记表同步刷新 |

## 已交付

| commit | CR | 说明 |
|---|---|---|
| `9bca8fc` | CR-2 R1 | `_bulk_update` 修剪了首次出现的 pattern，store 结构性空转 |
| `e8ac19d` | CR-1 R1 | KPI gate 改为按所属 skill 评分 + 读真实证据流 |
| `737e722` | CR-2 R2 | 计数改为 distinct traces；不再修剪本轮观测项；cap 落实 |
| `30744b7` | CR-2 R2 | store 段落空行；重算后重建 store |
| `f92f633` | CR-1 R2 | KPI gate 读真实证据流与真实路由基线 |
| `2c8aa70` | — | 本审计登记（文档） |
| `724afc9` | CR-3 R1 | **根因**：pattern store 与测试工作区隔离 + 格式可往返（关闭 H-21…H-28） |

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

### D. 产物格式 —— ✅ **已关闭**（CR-3 `724afc9`，2026-09-20）

> 两个 Critic 独立确认「H-21…H-28 all genuinely closed by execution」。
> 编排者另在一次性副本中独立复现了下列全部 5 项（此前均为实测损坏）。

| ID | 现象 | 关闭证据 |
|---|---|---|
| **H-21** ✅ | `\|` 出现在 `command`/`error`/`fix` → 8 列变 9 格 → `Count` 读错列、`error` 被截断 → prune 见陈旧键 → 删除 → merge 重加 → **每轮同时报 `Retired: 1` + `New patterns: 1`** | `\|` 已转义；`parse_existing` 还原出精确 key `('qcloud-pipe-ops','tccli cvm Run \| jq .','InvalidParameter: a \| b')`，count=1；sources 改为 JSON 数组 |
| **H-22** ✅ | 文件名含空格 → `sources` 空格分隔被切碎 → **count 每轮 +1** | 4 次运行 count **恒为 1**，sources 稳定为 `['ev il trace.json']` |
| **H-23** ✅ | R3 gate 在 line cap **之前**求值，`missing` 恒为空 → cap 丢弃观测项仍 exit 0 | 250 traces → `Dropped (cap 200): 106`，gate **逐个点名** 106 个丢失 key，**rc=3** |
| **H-24** ✅ | `merge()` 对无 sources 的行把 `count` 重置为 1 | 无 sources 且 `count=11` 的行 + 一次观测 → 保留并递增，不再重置 |
| **H-25** ✅ | `reflexion_retrieve retrieve --json` → `TypeError: Object of type set is not JSON serializable` | 返回合法 JSON，rc=0 |
| **H-26** ✅ | `enforce_line_cap` 无 `max_lines` 参数 → warm 层被静默压到 200 行 | 已参数化 |
| **H-27** ✅ | store 内嵌说明仍教已废弃语义 | 已改写为新语义 |
| **H-28** ✅ | `write_trace()` 在 cap 处静默驱逐 | 已报告驱逐 |

**根因（接缝）也已关闭** —— 编排者实测：全量 672 个测试跑完后，
`docs/failure-patterns.md` 的 md5 与 `audit-results/evidence-local.jsonl` 行数**双双不变**；
Critic 另验证 `pytest`（964 passed）与 `gcl_runner --root <tmp>` 两条路径同样不污染仓库副本。

#### D-新. CR-3 Round-1 Critic 发现的新增项 —— 状态见本节末尾的「Round-2 复核」

> 下表为 Round 1 发现时的原始记录，**保留不改**（证据是历史）；
> 各条的最新状态以下方「**Round-2 复核结果**」为准。

| ID | 现象 | 证据 | 严重度 |
|---|---|---|---|
| **H-29** | `--layered` 走另一条 emitter（`emit_layer`，7 列、无 `Sources`）→ `_sources_recorded=False` → `merge()` 用 `len(sources)` 覆盖存储值 → **Round 2 的「Sources 静默胜出」由一个 flag 即可复现** | `count=6 sources=6` → `--layered` → 一次重观测 → **`count=1`** | 🔴 |
| **H-30** | 转义在单元格边缘不对称：`unescape_cell(c.strip().strip("`"))` 对**仍处转义态**的文本剥反引号 → 转义的尾反引号被孤立。`error` 是去重键的一部分 → 同一故障会**改键成新行** | 23 组 fuzz → **14 处不匹配**；`error = "expected \`"` 读回 `expected \` | 🔴 |
| **H-31** | 单元格内含 `\n`/`\r` → `parse_existing` 按行切分 → **整行静默消失**，而 `write_trace` 仍返回 `True` | `error = "boom\n\| forged \| row"` → `parse_existing` 返回 **0 行**（合法行原本存在） | 🔴 |
| **H-32** | `docs/reflexion-memory.md:128` 称「**三条**路径写该文件」—— **第四次**错。实际第四条是 `failure_pattern_extract.main`（`:859`、`:822` 经 `HOT_PATH`），未出现在任何表格行 | 3B 复现；本轮 CR 重写的两个 docstring 反而**点出了**这条路径 | 🟠 |
| **H-33** | 「store 不可能被误改」是**调用方纪律而非代码保证**：`reflexion_auto_writer.py:86` 仍默认 `PATTERNS_FILE`。一次不带 `patterns_path` 的调用即改变已提交 store 的 sha | `ea524363611f → ae54c1283c2c`，并新增一行 | 🟠 |
| **H-34** | exit-3 消息给出的成因**结构上不可能**（空 `skill` 键永不进入 `observed`），两条补救措施**均无效**（`--min-count` 与 cap 驱逐无关；`MAX_LINES` 无 CLI 开关）。且它会让 `make reflexion-update` 变红 | 250 traces → exit 3 → `make: *** [reflexion-update] Error 3` | 🟠 |
| **H-35** | `severity` / `last_seen` 是仅有的两个未转义单元格；一个反引号即可吃掉整个 `Sources` 单元格（provenance 被毁、count 不变） | `severity='a\`b'` → `sources=[]` | 🟡 |
| **H-36** | hot→warm 降级触发器**不可达**：`HOT_LIMIT = 200` 按**行数**比较，而 200 行实测只容 ~130 行；`docs/failure-patterns-warm.md` / `-cold.md` 在仓库中不存在 | 5 类分节满载 → 130 行存活 | 🟡 |
| **H-37** | 每个单元格的 `.strip()` 抹掉首尾空白与制表符 → 同一故障**改键成新行** | `' lead-trail '` → `'lead-trail'`；`'\ttab'` → `'tab'` | 🟡 |
| **H-38** | `docs/failure-patterns.md` 表头内嵌当天日期 → 「byte-identical」仅在**同一天内**成立 | `failure_pattern_extract.py:620`；同日两次运行 md5 相同 | 🟡 |
| **H-39** | 证据已跟随 `gcl_runner --root`，但 `check_kpi_gates.py` 仍读 `ROOT/audit-results` → 异 root 运行的证据**永不被打分**，exit 0 | `gcl_runner.py:899` vs `check_kpi_gates.py:53,130`；**归属 ADR 候选 1** | 🟡 |

#### Round-2 复核结果（Critic-3R2-A / 3R2-B 逐条实测，2026-09-20）

| ID | Round-2 状态 | 关闭证据 |
|---|---|---|
| H-29 | ⚠️ **部分** | 8 列共享 schema 落地（`_SECTION_HEADERS` 单一定义，`grep` 确认无第二条列定义路径）；但**语义未统一** → 见 H-40 |
| H-30 | ✅ 关闭 | 独立 fuzz（含 `severity='a\`b'`、`'a\|b'`、`'a\\b'`）全部精确读回；`_decode_cell` 在反转义前只剥一层**配对的**包装 |
| H-31 | ✅ 关闭 | `new\nline` 正常往返，零丢行 |
| H-32 | ✅ 关闭 | `_store_writers() == _documented_writers()` → `EQUAL: True`（5 个）；且**检查可证伪** —— 注入第 6 个写者 → `1 failed` |
| H-33 | ✅ 关闭，**且已是代码保证而非调用方纪律** | `write_trace()` 现要求 `patterns_path` 为**必填 keyword-only**；省略即 `TypeError`；store sha 前后一致；`gcl_runner.py:729` 按关键字传入 `root/docs/failure-patterns.md` |
| H-34 | ✅ 关闭 | 超 cap 时为**非致命**（`REFLEXION GATE (non-fatal): … rc=0`），`make reflexion-update` → rc=0；exit-3 仍可达但成因措辞已准确 |
| H-35 | ✅ 关闭 | `severity='a\`b'` → `sources` 保留、count 正确（原为 `sources=[]`） |
| **H-36** | 🔴 **未关闭，且恶化** | `HOT_LIMIT=200` 是**行**数，200 行渲染成 **214 行**，**突破 AGENTS.md:208 的 P0「≤200 行」约束**；更糟的是新的非致命 gate 消息**主动推荐 `--layered`** 作为 cap 驱逐的补救 —— 照做等于把「有损但有上限」的 store 换成「无损但无上限」 |
| H-37 | ✅ 关闭（走 spec 允许的「记录为 key 归一化」路线） | `docs/reflexion-memory.md:193-197` 明确写出归一化语义 |
| H-38 | ✅ 关闭 | 断言已收窄为「同日」，收窄本身准确 |
| H-39 | ✅ 按 spec 处理（不修，登记） | `git diff 724afc9..f9e0691 -- scripts/check_kpi_gates.py` 为空；ADR 候选 1 已收窄为「H-39 仍开放」 |

#### Round-2 新暴露项

| ID | 现象 | 证据 | 严重度 |
|---|---|---|---|
| **H-40** | `--layered` 走的 `merge_failure_batch()` 是**第二套独立计数实现**：按**原始观测**逐次 `count += 1`，从不调 `source_of()`/`merge()`，**从不建 `sources` 集合** → 既非幂等，又在首次写入时**销毁 provenance**（渲染为 `—`）。膨胀值还会被洗进 `unattributed` 并**永久固化、永不痊愈**：`12 → 18 → 冻结 → 24` | 函数级：同语料 3 次 → `6/12/18` 而 `sources` 键缺失；对照 `merge()` → `6/6/6` 且 `len(sources)=6`。CLI 同样复现 | 🔴 |
| **H-41** | 那条看似覆盖 `--layered` 的测试是**重言式**：手工构造 `patterns`（**含它随后要断言的 `sources` 集合**）并调 `save_layer()`+`merge()`，**从不调用生产中唯一产生 layered 写入的 `merge_failure_batch()`** → 读回自己的输入。**68/68 全绿，H-40 活着** | `failure_pattern_extract_test.py:467-479` | 🔴 |
| **H-42** | `merge_failure_batch()` 的**孪生拷贝**有同一缺陷：`success_pattern_mine.py:353` 逐次 `count += 1`，且 `avg_iter` 也被 run-multiplicity 重新加权。`docs/success-patterns.md` **没有 sources 列**，无从交叉校验 | 该函数 docstring 自述「mirrors `success_pattern_mine.py` merge_batch」 | 🟠 |
| **H-43** | `--layered --root .` 在**已经写完 layers 之后**抛 traceback —— 部分成功被报告为崩溃 | 3R2-B 实测 | 🟡 |
| **H-44** | `docs/reflexion-memory.md:56` 的 `count ≥ len(sources)` 是**重言式**（`unattributed` 定义即 `max(0, count-len)`，`count` 又被设回 `len+unattributed`），**测不出 H-40 这一类** | 3R2-A 无法构造反例 —— 因该式非可证伪 | 🟡 |
| **H-45** | 「临时 root 不能改动已提交文件」的表述**作用域被读成通用**：`failure_pattern_extract.py --root <tmp>` 与 `--layered --root <tmp>` 都写**仓库绝对路径**的 store（`--root` 只影响 `collect_traces`） | `failure_pattern_extract.py:837`、`_failure_pattern_store.py:15`(`HOT_PATH`) | 🟡 |

> **往轮备注（供 ADR 候选 1 参考）**：3R2-B 指出工作区中 `scripts/check_kpi_gates.py`
> 有**未提交改动**，属并发进行的 CR-4，不是 CR-3 越界。

#### Round-3 复核结果（CR-3 `cbeab00`，Critic-3R3-B 逐条实测）

**结构性修复生效** —— 第 3 轮不再补路径，而是把两份计数实现**收敛为一份**：

```
--layered 连跑（同一语料 6 traces）:
  修复前  count 6 → 12 → 18   sources 缺失 / 渲染为 —
  修复后  count 6 →  6 →  6   sources=6                ✅ 幂等 + provenance 保留

250-pattern 语料:
  Hot layer: 190 (+190 new, 10 to warm over the 200-line cap)
  docs/failure-patterns.md = 200 行                       ✅ 守住 P0 上限（原 214）
```

| ID | Round-3 状态 | 关闭证据 |
|---|---|---|
| H-36 | ✅ 关闭 | 恰好 200 行，pattern **无丢失**；200/201 边界行为一致 |
| H-40 | ✅ 关闭 | `--layered` 连跑 `count 6/6/6`，`Sources` 已填充（不再是 `—`） |
| H-41 | ✅ 关闭 | 新测试驱动生产函数（非手工构造），可证伪 |
| H-43 | ✅ 关闭 | `--layered --root .` → exit 0，不再 traceback |
| H-44 | ✅ 关闭 | 不变量改为可证伪表述 |
| H-45 | ✅ 关闭 | 文档表述与行为一致（作用域已收窄） |
| H-42 | ✅ 按要求处理 | `success_pattern_mine.py` **未被改动**（`git diff` 为空），已在 commit body 精确登记 |
| **H-29** | ⚠️ **仍在** | 语义统一完成，但见 H-46/H-47 —— 该路径仍有独立缺陷 |

#### Round-3 新暴露项（回归 + 新面）

| ID | 现象 | 证据 | 严重度 |
|---|---|---|---|
| **H-46** | **回归**：`--layered` 在 store 溢出到 cold 后**不再可重跑**（≥701 patterns → exit 1、跨层重复键、什么都没写）。修复前 700 与 701 都能通过 | `failure_pattern_extract.py:455-488` + `:809-825` | 🟠 |
| **H-47** | demotion 写入 `warm` 发生在 `self_verify_failure()` **之后** → 800-pattern 运行**报告成功**，而落盘状态其实**不满足 V2**（warm 510 > 500）。**与 H-23（gate 求值早于 cap）同一形态**，只是换了个位置 | `failure_pattern_extract.py:798-825` | 🟠 |
| **H-48** | `docs/reflexion-memory.md:243`,`:64` 用「200 rows ≈ 214 lines」为修复做论证，但两个 emitter 实测都不产出该数字（实测 210 / 250） | 3R3-B 实测 | 🟡 |
| **H-49** | **第三个 count 变更点**：`self_heal_pr_workflow._deduplicate_pattern()` 按**位置**读 `cells[-2]`（在 8 列 schema 下那是 `Severity` 列）→ `int("major")` 失败 → 回落为 1 → `count <= 1` 成立 → **该行被删除**。它同时也是「一个 count 函数」目标的漏网者 | `self_heal_pr_workflow.py:379-390`；3R2-A 亦独立复现，并确认 `docs/reflexion-memory.md:155-160` 已**如实记载**该缺陷 | 🟠 |


> **H-47 的形态值得单独标注**：「校验发生在被校验对象之前」这个模式，在本会话里已是**第四次**出现
> （R3 gate 早于 cap → `missing` 恒空；CI gate 早于 evidence 读取；run_id 隔离被 glob 加宽抵消；
> 现在 demotion 晚于 self-verify）。它不是巧合，是**编排顺序从不被断言**的必然结果。

#### 系统性观察：五次「修好一条路径，镜像的那条被漏掉」

| # | 修好 | 漏掉 |
|---|---|---|
| 1 | `write_trace()` | `_bulk_update()`（`make all` 实际走的那条） |
| 2 | 加宽 glob 读 `.jsonl` | 同一改动使 run_id 隔离失效 |
| 3 | 主 emitter `_emit_store` | 备用 emitter `emit_layer`（`--layered`） |
| 4 | 给两个 emitter 统一**列** | 备用路径的**计数语义** |
| 5 | 把计数归一落进 `merge()` | `merge_failure_batch()` 与 `success_pattern_mine` 孪生拷贝 |

**结论：根因是「同一份逻辑存在两份拷贝」，不是某个具体 bug。** 故 CR-3 第 3 轮（§3.3 最后一轮）
的指令是**消除重复计数实现（one count function, not two）**，而非再补一条路径。

## CR-4 `kpi-honesty` 复核（Critic-4A / 4B，2026-09-20）

**D-2=B 的核心实现是真的**：CI 现在自己从 `scripts/fixtures/evidence/` 落文件，并用
`GATE_EVIDENCE_GLOB` **精确点名**被判分的那个文件（不再靠 glob 猜）；两侧都测
（clean 必须过、violating 必须红，不红则 `::error::` 并 exit 1）；`trap ... EXIT` 清理。

Critic 逐条实测确认：**注册表下限真的封死了 H-15**（在基线复现了 exploit：`15/30 → ✅ pass`、
top1 30.16%；同一输入在 `1399f58` → `❌ fail | registry has 30 skill(s), below the recorded
floor of 31`，exit 1）；缺失/空/超龄证据一律 fail-closed；本地 `make kpi-gates` 默认路径未变；
CI 注释里的事实陈述逐条属实；单测隔离成立。**H-17…H-20 经执行验证关闭。**

### 未关闭项

| ID | 现象 | 证据 | 严重度 |
|---|---|---|---|
| **H-50** | **fire-side 无法检出「单条安全规则失效」**：violating fixture 同时触发 `leak_checked`/`token`/`plan_hash` **三条**规则，任一条死掉其余仍会开火 → 步骤依旧变红 → **看不出某条规则已停止工作**。而 D-2=B 的全部意义正是「证明规则本身还能开火」 | `.github/workflows/validate-skills.yml:140-148` | 🟠 |
| **H-51** | **新 KPI 步骤在 CI 中永不执行**：其上游的**阻断式**单测步骤在**全新检出**上就是红的（`build_skill_registry_test.py:23` 读 gitignored 的 `audit-results/skill-registry.json`，文件不存在 → ERROR）。编排者独立复现：fresh clone `Ran 688 tests … FAILED (errors=1)`，而 CI 中该步骤在 `:81`、KPI 步骤在 `:113`。**与 H-08（`make all` 走不到 `reflexion-update`）同类** | 编排者实测 + 4A 独立复现 | 🔴 |
| | ↳ **精确机制**：`test_intent_keywords_populated`（`:22`）读注册表却**不自己 emit**，依赖兄弟测试 `test_registry_has_all_skills`（`:11`）的副作用；而 unittest 按**字母序**执行方法名，`i` < `r` → **依赖方先跑**。开发者机器上有一个 gitignored 的陈旧 `skill-registry.json` 掩盖了它，全新检出则 ERROR。**又是一个「依赖别处的副作用、且无人断言接缝」** | 见 CR-5 修复 | |
| **H-52** | `GATE_EVIDENCE_GLOB` 被**无条件信任**，且可**穿出 `audit-results/`**（路径遍历） | `check_kpi_gates.py:151-152` | 🟠 |
| **H-53** | *「单个翻转的 query 就让 ratchet 触发」* 是**假的** —— 而这是「把 ratchet 留在 0.28」的**全部理由** | `kpi-pattern.md:113-115`、`:225-227`、`runbooks/kpi7-*.md:31-33` | 🟠 |
| **H-54** | `kpi1` runbook V4 仍在告诉 on-call **CI 使用本 CR 已删除的那个 escape** | `runbooks/kpi1-leak-checked-failure.md:60-64` | 🟠 |
| **H-55** | spec（**被本 CR 编辑过的行**）与 AGENTS.md L24 的 `29/31` 混淆了两个分母；实为 `29/36`（注册表口径 `24/31`）。**AGENTS.md 已由编排者修正**（`0fb0314`） | `spec:258`；`AGENTS.md:165` | 🟠 |
| **H-56** | kpi2 runbook 两条命令在本机仍失败（glob 不匹配）；kpi1 V3 行号引用过期；KPI#7 模板 yaml 漏了新增阈值；*"26 skills at 0.0"* 实为 27 | 4B 实测 | 🟡 |

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

### D-2（✅ 已裁定 **B 案**，2026-09-20，按推荐）CI 是否应对证据流设门禁

Critic-1R2-A 指出 Round 2 实际上**替您选了一个政策而未曾标明这是选择**：

- **A 案**：证据是**本地监控信号**，不是合并门禁。接受「KPI#1/#2 永不在 merge 时执行」，但文档必须大声说清，且 CI 注释必须改（**现在是事实错误的**，见 H-14）。
- **B 案**：CI 对一份**已提交的 fixture** 执行门禁 —— 验证的是「安全规则本身还能不能开火」，不是集群行为。成本约 1 个 fixture 文件 + 4 行 workflow。

**Critic 推荐 B**，理由：`audit-results/` 被 gitignore 后，**一个把 `leak_checked` 改成 false 的 PR，CI 抓不到、本地也抓不到**（本地流里只有 PR 之前的代码铸的记录）。

**编排者倾向 B**，但新增受版本控制的 fixture 属策略决定，故上报裁定。

> **裁定结果（2026-09-20）：采纳 B 案**，按编排者推荐执行。
> CR-4 `kpi-honesty` 据此实现：提交两份 fixture（一份干净 → gate 绿；一份含故意的
> `leak_checked: false` / 破坏性操作无 token → gate 红，exit 1），两份均须满足
> `evidence_min_records` 下限并覆盖 aged-out 路径，以满足 **AGENTS.md L6
> 「新门禁必须同时证明会开火与会静默」**。
> 同时把 workflow 注释改写为点明 escape 才是真正的控制点（H-14），
> 并把 `CI-hooked ✅` 一栏改为与事实相符（H-13）。

## ADR 候选

两项运行时拓扑决策，按 AGENTS.md「影响 >1 子系统 / 运行时拓扑 → ADR」应走 ADR，
**本会话未创建 ADR 文件**（决策未定，创建 TBD 的 ADR 只是噪声）：

| 候选 | 内容 | 阻塞于 |
|---|---|---|
| **ADR 候选 1** | 证据流（`audit-results/evidence-*.jsonl`）的**归属**：D-2 已裁定 CI 改判 fixture（不再依赖集群流），但**集群流本身仍无家可归** —— 它被 gitignore、无轮转、随 `--root` 漂移，而 gate 只读 `ROOT/audit-results`（H-39），因此异 root 运行永不被打分。需决定：集群证据是本地监控信号、集中上报、还是入库 | D-2 部分已决；**H-39 仍开放** |
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
