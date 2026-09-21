# Execution Lessons (CADL — distilled, reusable)

> Machine-hardened lessons updated as tasks land; de-duplicated against AGENTS.md rules.
> Absorb before writing test or credential-masking code.
>
> **Source of truth**: This file. AGENTS.md retains only a routing pointer.

| ID | Lesson | Key Fix |
|----|--------|---------|
| L1 | `unittest discover` only finds `TestCase` subclasses | Must use `class XxxTest(unittest.TestCase)` + `unittest.main()` |
| L2 | Subprocess test paths must be cwd-independent | Use `Path(__file__).resolve().parent / "validate_x.py"` |
| L3 | Credential-masking regex must cover bare secret-id suffixes | `re.sub(r"(AKID\|secretId\|secretKey)[A-Za-z0-9]+"` |
| L4 | KPI rejection paths need explicit tests | Test destructive-without-token, leak_checked=false |
| L5 | Tests must assert populated values, not just key presence | Assert real values, not just key existence |
| L6 | New CI gates must BOTH fire and stay silent | Prove exit-0 when no trigger, exit≠0 when triggered |
| L7 | Re-read live target file before writing integration specs | Read current file; target may have changed |
| L8 | Green but vacuous: assert metrics are non-vacuous | Assert `top1_accuracy > 0`, not just valid float |
| L9 | Consumer quality bounded by producer data contract | Verify PRODUCER emits populated data first |
| L10 | Convergence gates on runtime artifacts skip gracefully | `if ls ...; then ...; else echo "skipped"; fi` |
| L11 | KPI gate only as real as data it ingests | Trace PRODUCER actual output; reject malformed input |
| L12 | Stricter detection breaking bug-reliant tests | Update tests to corrected contract, don't revert fix |
| L13 | Destructive-verb detection must be inflection-tolerant | Use `t == v or t.startswith(v)`, single source `harness_safety.VERBS` |
| L14 | Major architectural initiative: build CHECKPOINT.md FIRST | `.runtime/<scope>/CHECKPOINT.md` for >3 artifacts |
| L15 | Multi-perspective review: fold into artifact bodies | Fold into ADR/Spec sections, save 30-50% token |
| L16 | AGENTS.md surgical edits at >500 lines | `sed -i.bak` + `a\` with line anchors; diff verify |
| L17 | YAML frontmatter readers: `metadata.*` first, fallback top-level | `val = (meta.get(key) if isinstance(meta, dict) else "") or fm.get(key, "")` |
| L18 | `ruamel.yaml` round-trip preserves indent; `yaml.dump` does not | Use `YAML(typ="rt")` + `indent(mapping=2, sequence=4, offset=2)` |
| L19 | Cross-instance races need file locks + forced reload | `fcntl.flock` + forced reload; exact assertions for zero loss |
| L20 | unittest buffer=False: print-capable funcs leak stdout | Wrap with `contextlib.redirect_stdout(io.StringIO())` |
| L21 | Governance/evaluator fallbacks MUST be deny-by-default | No-match policy rule → `human_approval`, never `auto_confirm`; empty SLO samples → N/A + breach, never 1.0 |
| L22 | GCL 终轮若仅剩「描述精确化 / L* 引用补齐」类 MAJOR（无新逻辑），可省 Critic，由主 Agent fact-check 替代 | 判据：改动不含控制流/接口/算法 → 省 Critic；主 Agent 用 3-5 条命令复核数字与引用真实性（如 `grep -c '^\| L1 '` 验证引用非幻觉）。实证：2026-09-06 R3 4 MAJOR 全为此类，省一轮 Critic，主 Agent 5 条命令复核 4/4 通过、零幻觉引用 |
| L24 | 指标读取语料中普遍缺失的字段会退化为常量，而**无阈值的 gate 会把这个常量报成 PASS**（假绿）。实证：KPI#7 读 `q["intent"]`，29/36 语料无该键（注册表 31 个 skill 口径为 24/31）→ top1 恒为 0.0，gate 却打印 14.72% 并 PASS；按 owning-skill 真值实测仅 9.87%（46/466，口径为全部 36 个 skill 目录） | 指标落地前先统计该字段的**存在率**（逐条统计，如 `grep -c`）/ 确认 ground truth 来自语料本身而非可选键；gate 必须带阈值，阈值取自**实测基线**而非估计；低于 target 时即使 pass 也显式打印差距 |
| L25 | **每个契约都有两端（生产者↔消费者、声明↔接线、规范↔实现），而不校验接缝时两端必然漂移，且漂移不可见。** 实证：一次审计中 10 个缺陷**全部是同一个缺陷**——`evidence_kernel` 写 `.jsonl` 而 gate glob `.json`；`Makefile` 定义 9 个门禁而无一 workflow 调用 `make`；`validate_error_tables.py` 自称 "CI gate" 却零接线；14 个测试叫 `test_*.py` 而 discover 用 `-p "*_test.py"`（静默排除 257 个测试）；AGENTS.md 写 "≥10 错误码" 而 validator 只查结构不查数量 | ① **修复必须打在构建实际执行的那条路径上**：`4e8e77b` 正确诊断了 bug 却只修了 `write_trace()`，而 `make all` 走的 `_bulk_update()` 原封不动——为修好的路径写了测试并通过，构建执行的那条仍在删光一切。改前先确认「谁真正调用这个函数」。② **主观保证不是证据**：两轮修复均在「测试全绿」状态下带着 BLOCKER，唯一有效证据是**把修复 revert 掉并证明测试会失败**。③ 新门禁必须同时证明「会开火」与「会静默」（见 L6），并落一个「门禁接线」检查器，否则第 4 条同类漂移必然出现 |
| L26 | **验证 CI「已修复」必须用 CI 自己的工具版本、且从第 1 步开始。** 实证：CI 第 1 步 ruff pin `0.11.8` 报 **99** 个错误，而本机 ruff `0.16.1` 报 **0** —— 因为 `ruff.toml` 没写 `select`，各版本套用各自的默认规则集（0.16.x 默认不再选 E4/E7；实测 `--select E402` 仍能检出）。据此误判「已修复」两次：一次从 **step 81** 起验证（跳过 step 1），一次用错版本。**升级 pin 到本机版本是被否决的方案 —— 那会静默丢掉 E4/E7 全部覆盖。** 正确修法：显式写 `select` 把覆盖范围钉死，再有理由地 `ignore` 具体规则 | ① 改 CI 前先读 workflow 的**第 1 步**是什么、pin 了什么版本；② 用 `uvx <tool>@<pinned-version>` 复现 CI 环境，不要用本机版本；③ 验证时**从第 1 步往下走**，不要从你刚改的那一步开始 —— 后者会得出「链路已通」的假结论（本会话实际发生）；④ 工具版本与配置不匹配时，先问「是代码错了还是检查器的默认集变了」，优先钉住配置而非升级版本 |
| L27 | **「跑绿了」不等于「跑到了」；测试运行器与文件命名是两个必须对齐的契约。** 实证：`unittest discover -p "*_test.py"` 与 `test_*.py` 命名不匹配 → **292/981（30%）测试从未执行**（274 个在 `test_*.py`；另有 ~18 个是正确命名文件内的 pytest 风格测试，unittest 根本不能跑）；同一批测试用 pytest 收集即 981 全绿。修法：换用能同时收集两种模式/两种风格的运行器（pytest，CI pin 7.4.4），并把收集数写成棘轮 `thresholds.json:tests_min_collected`；门禁 `check_test_collection.py` 另断言「每个测试文件都出现在收集到的 node id 中」 | ① 换运行器前先统计「命名模式 × 测试风格」二维矩阵，别假设默认模式覆盖你的命名；② 新增门禁的判据必须排除它自己的测试文件 —— `check_gate_wiring` W3b 首版把 checker 自身测试（fixture 内构造同名字面量）判成违规，自我误报；③ 火侧证明放进测试（`validate_skills_frontmatter_test.py::CommittedFixtureFireTests`），不要放进 CI 的 shell 片段 —— 同一证明写两遍就是漂移的起点；④ 断言按**名字**取不要按下标：`steps[7].argv` 在插入一步后必红，产出的是噪音不是信号 |
