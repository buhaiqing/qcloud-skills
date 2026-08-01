# qcloud-skills — Agent guidance

## Repo purpose

Collection of Tencent Cloud AI Agent skills (OpenSpec) for ops runbooks. Each skill is a `SKILL.md` file with YAML frontmatter. Live work happens via `tccli` CLI (primary) or `tencentcloud-sdk-python` (fallback).

## Layout

```
qcloud-skills/
  scripts/                     # Shared executables: validate_*, gcl_runner, gcl_trace_aggregate
  audit-results/               # Runtime output (gitignored)
  qcloud-[product]-ops/        # 31 skill directories
    SKILL.md                   # YAML frontmatter + Markdown runbook
    assets/
      eval_queries.json        # Intent classification test set
      example-config.yaml      # Optional example YAML
      *.schema.json            # JSON Schema / handoff contracts
    references/                # Supporting docs: cli-usage, api-sdk-usage, troubleshooting
```

All schemas, handoff contracts, and skill-specific config live under the owning skill's `assets/` (or `references/` for Markdown-only contracts).

## Skills inventory (34)

- Product-scoped (29): `cvm`, `cdb`, `clb`, `cos`, `es`, `redis`, `monitor`, `tke`, `vpc`, `cam`, `cdn`, `cbs`, `cls`, `ckafka`, `scf`, `mongodb`, `postgres`, `ssl`, `agsx`, `finops`, `ccn`, `vpn`, `dc`, `cicd`, `service-mesh`, `migration`, `tcop`, `tdmq`, `apigw`
- Cross-product (4): `qcloud-aiops-diagnosis`, `qcloud-proactive-inspection`, `qcloud-well-architected-review`, `qcloud-copilot`
- Meta-skill (1): `qcloud-skill-generator` (scaffolds/updates other skills)

Run `ls qcloud-*-ops/` for canonical list.

## Key conventions

- **Dual-path execution**: `tccli` primary; `tencentcloud-sdk-python` fallback. `cli_applicability` field: `cli-first` / `dual-path` (most common, requires `references/cli-usage.md`) / `cli-only` (read-only) / `sdk-only` (verify via `tccli <product> help`).
- **Pre-check → Execute → Verify → Recover**: Standard 4-step runbook shape.
- **Cross-skill delegation**: Check target skill's `## Trigger & Scope` for `delegate-to` markers.
- **Five Core Standards (P0)**: Clear Boundaries, Structured I/O (`{{env.*}}`/`{{user.*}}`/`{{output.*}}`), Explicit Actionable Steps, Complete Failure Strategies (≥10 product-specific error codes with HALT vs retry), Absolute Single Responsibility.
- **Token Efficiency (P0)**: Minimize tokens while preserving executability. Rules: TE-1 (API queries instead of hardcoded tables), TE-3 (error tables ≤3 columns), TE-4 (JSON paths centralized), TE-5 (YAML anchors), TE-6 (eliminate cross-file duplication).
  - **TE Audit Trigger**: After any `SKILL.md`/`references/*.md`/`rubric.md`/`prompt-templates.md` change, scan for >10-line repetitive blocks or >5 inline hardcoded values. Record result in commit footer: `TE-Audit: ...`.
- **Subagent concurrency limit (P0)**: Max 3 concurrent subagents.
- **No web console execution path** (only for docs reference).
- **Minimal-change principle**: Don't reformat/rename/restructure unrelated files.
- **Commit hygiene**:
  - Default: One commit per logical unit.
  - **Hard stops (MUST pause)**: Credentials/secrets in diff, irreversible destructive ops without confirmation, bypassed safety gates, wrong remote/branch/protected branch, sensitive info in commit, mass destructive changes.
- **Python lint gate**: After `*.py` changes, run `ruff check <changed-files>`. If that exits non-zero, run `ruff check .` to catch pre-existing errors (e.g. E741 ambiguous variable name like `l`) that would break CI — fix them in the same commit. After Python SDK code blocks in Markdown, run `python3 scripts/check_markdown_python.py --root .`.
- **Spec-Plan-Code Alignment Gate (硬性约束)**: 每次任务开发必须经过三阶段闭环：
  1. **SPEC**：在 `docs/superpowers/specs/` 下编写设计文档（背景、架构、Schema、算法、文件清单）
  2. **PLAN**：在同一文档中编写 Phase 清单（每个 Phase 含具体步骤，checkbox 格式）
  3. **Code vs Spec+Plan 核对**：代码完成后逐条对照 SPEC/PHAN，每条注明 ✅/⚠️/❌；发现不一致必须修复再继续
  - **适用场景**：新增功能模块（`scripts/*.py`）、新数据结构、新算法、新子系统
  - **不适用**：单文件 typo 修复、纯粹格式化调整（<5行无逻辑变更）
  - **Spec 位置**：`docs/superpowers/specs/<short-name>-design.md`
  - **自验证**：SPEC 中必须包含 self-check / self-verify 逻辑（如 `assert not errors`）
  - **后续任务**：同一子系统的后续迭代应追加到已有 SPEC/PROD 文件，而非新建
- **UX spec mandatory**: `qcloud-skill-generator/references/user-experience-spec.md`.
- **Asset & schema placement (mandatory)**:
  | Location | Allowed contents |
  |---|---|
  | `qcloud-*-ops/assets/` | `eval_queries.json`, `example-config.yaml`, `*.schema.json`, skill-specific templates |
  | `qcloud-*-ops/references/` | Runbooks, Markdown output contracts, delegation stubs |
  | `scripts/` | Shared executables used by multiple skills |
  | `audit-results/` | Generated traces/reports |

  **Owner skill rule**: Skill defining/primarily consuming a contract owns it. Secondary consumers link via relative path.

## Coding Discipline (Karpathy Guidelines)

### 1. Think Before Coding
- Explicitly state assumptions; ask if uncertain.
- Present multiple interpretations if they exist.
- Suggest simpler approaches when warranted.

### 2. Simplicity First
- No features beyond what was asked.
- No single-use abstractions.
- No unrequested flexibility/configurability.
- Rewrite 200-line solutions that could be 50 lines.

### 3. Surgical Changes
- Touch only what you must.
- Match existing style.
- Don't refactor working code.
- Remove only your own unused imports/variables/functions.

### 4. Goal-Driven Execution
- Define verifiable success criteria.
- For multi-step tasks, state a brief plan with verify checkpoints.

## Mandatory rule: 2-round self-review after every skill update

After modifying `SKILL.md`, `references/`, or `assets/`, MUST run 2 rounds before declaring done.

**Round 1 — Self-check against template & standards**:
1. Re-read `qcloud-skill-generator/references/qcloud-skill-template.md` and `qcloud-skill-generator/SKILL.md`.
2. Verify Five Core Standards (see Key Conventions above).
3. Verify Token Efficiency rules (TE-1/TE-3/TE-4/TE-5/TE-6).
4. Cross-check `cli_applicability` against CLI support.
5. Verify YAML frontmatter validity, bumped `version`/`last_updated`, and `related_skills`.
6. Confirm credentials never printed (only `<masked>`).
7. Check `eval_queries.json` coverage (2-4 positive + 2-4 negative cases for new functionality).
8. Verify asset placement (no repo-root `assets/`).

**Round 2 — Adversarial review**:
1. Apply R1 Security, R2 API Fidelity, R3 Safety Gates, R4 UX from `qcloud-skill-generator/references/governance-and-adversarial-review.md`.
2. Walk through Adversarial Scenarios.
3. Verify cross-skill delegation (manual review step; verify delegate-to markers are present in referenced skills and chains are not broken).

**Fix-on-find**: Any problem must be fixed in same change set.

## Prerequisites for execution

```bash
export TENCENTCLOUD_SECRET_ID=your_secret_id
export TENCENTCLOUD_SECRET_KEY=your_secret_key
export TENCENTCLOUD_REGION=ap-guangzhou
cp .env.example .env   # edit TENCENTCLOUD_SECRET_ID / TENCENTCLOUD_SECRET_KEY / TENCENTCLOUD_REGION
```

Requires `tccli` (pip-installable) and Python 3.8+. `qcloud-finops-ops` additionally needs `TENCENTCLOUD_FINOPS_CONFIG` (see `.env.example`).

## SKILL.md frontmatter — required fields

- `name` / `description` (skill identity and triggers)
- `compatibility` (execution environment)
- `cli_applicability` (`dual-path`/`cli-first`/`cli-only`/`sdk-only`)
- `cli_support_evidence` (verification command)
- `environment` (required env vars)
- `metadata.version` / `metadata.last_updated` (bump on every change)

## Evaluation

- `assets/eval_queries.json`: Intent-classification test cases (`should_trigger: true/false`).
- **Build-time regression commands**:
  | Change scope | Command |
  |---|---|
  | Full local validation | `python3 scripts/validate_local.py` |
  | SKILL.md frontmatter | `python3 scripts/validate_skills_frontmatter.py` |
  | well-architected-assessment.md JSON | `python3 scripts/validate_product_assessment.py` |
  | GCL rubric/prompt/Quality Gate | `python3 scripts/check_gcl_conformance.py` |
  | gcl_runner.py/gcl_trace_aggregate.py | GCL smoke command + `python3 scripts/gcl_trace_aggregate.py --since-hours 168` |
  | Skill quality score / upgrade signal | `python3 scripts/skill_quality_score.py --json` (optional; skipped by `validate_local.py` if absent) |
  | Reflexion retrieval (self-evolution) | `python3 scripts/reflexion_retrieve.py retrieve --skill <skill>` |
  | CADL hook compliance | `python3 scripts/cadl_lint.py` (exit 1 if any `qcloud-*-ops/SKILL.md` lacks the canonical hook; `--fix` injects idempotently) |
  | Python files | `ruff check <changed-files>` |
  | Script tests | `cd scripts && python3 -m unittest discover -p "*_test.py" -v` |
  | GCL alarm wiring | `python3 scripts/gcl_alarm_wire.py plan --summary scripts/fixtures/gcl-quality-summary-healthy.json` |
  | Markdown specs/links | `python3 scripts/check_markdown_links.py` |
  | Python SDK code blocks in Markdown | `python3 scripts/check_markdown_python.py --root .` |

- **Runtime GCL**: `scripts/gcl_runner.py` requires external isolated Critic scores in production. `--structural-critic-only` only for CI/local smoke tests.

## Execution lessons (CADL — distilled, reusable)

> Machine-hardened lessons updated as tasks land; de-duplicated against rules above. Absorb before writing test or credential-masking code.

### L1 — `unittest discover` only finds `TestCase` subclasses
裸 `def test_*(self)` 不被 discover 发现("Ran 0 tests")。必须 `class XxxTest(unittest.TestCase)` + `unittest.main()`。

### L2 — Subprocess test paths must be cwd-independent
`subprocess.run(["scripts/validate_x.py", ...])` 从 scripts/ 内执行会解析成 `scripts/scripts/...`。用 `Path(__file__).resolve().parent / "validate_x.py"`。

### L3 — Credential-masking regex must cover bare secret-id suffixes
mask 正则必须覆盖裸 `AKID<hex>`(无分隔符)和 `TENCENTCLOUD_SECRET_KEY=<val>`。用 `re.sub(r"(AKID|secretId|secretKey)[A-Za-z0-9]+", r"\1<masked>", text)`。

### L4 — KPI rejection paths need explicit tests
每个 gating 验证器的拒绝分支都要有测试(destructive-without-token → KPI#2、`leak_checked=false` → KPI#1),否则回归静默通过。

### L5 — Tests must assert populated values, not just key presence
断言 key 存在会在值为 `[]`/空时假绿(实测:YAML block-scalar `>-` 弄坏全部 30 个 skill 的 `intent_keywords`)。至少对一个代表性用例断言真实填充值。

### L6 — New CI gates must be proven to BOTH fire and stay silent
新门禁双向证明:(1) 无触发条件时 exit-0 静默;(2) 故意坏的 fixture 触发时 exit≠0(如 `evidence-*.json` 带 `safety.leak_checked=false` → validate_local exit 1)。

### L7 — Re-read the live target file before writing integration specs
计划中的集成步骤是假设不是指令——目标文件可能已被并行工作实现(gcl_runner.py 已有 mask_secrets/run_command/persist_trace)。编辑前 Read 当前文件,规范改为严格增量。

### L8 — Green but vacuous: assert metrics are non-vacuous, not just well-typed
"返回合法 float" 断言在算法饿数据/匹配策略错时也通过(confusion_matrix 全 0.0)。ranking/ML 组件断言指标 MEANINGFUL(如 `top1_accuracy > 0`)。

### L9 — Consumer quality is bounded by producer data contract
消费方只解析生产方发出的数据;组件依赖另一模块数据时,先验证 PRODUCER 发出填充且形状正确的数据,别在消费方打补丁。端到端追踪数据契约再宣布完成。

### L10 — Convergence gates on runtime artifacts must skip gracefully, not fail
依赖 gitignored/运行时产物(如 `audit-results/evidence-*.json`)的入口必须缺省时静默跳过(`if ls ...; then ...; else echo "skipped"; fi`);对已提交输入的门禁必须硬失败。配测试证明 artifact 存在时确实触发。

### L11 — A KPI gate is only as real as the data it ingests
门禁读另一模块 emit 的数据时,追踪 PRODUCER 实际发射(别信字段名:曾硬编码 `"destructive": False`)且 CONSUMER 拒绝畸形/空输入;两侧都配触发测试(无 token 破坏性操作 → exit 1)。

### L12 — Stricter detection that fixes a bug can break tests relying on the bug
修复使检测更严格时旧测试会失败——先问"测试是否在断言 bug?"是 → 更新测试到修正后的契约(如设 `HARNESS_CONFIRM_TOKEN = plan_hash(command)`),不要 revert 修复。

### L13 — Destructive-verb detection must be inflection-tolerant
破坏性动词匹配必须容忍屈折("deleted"/"removes"/"stopping"):用 `t == v or t.startswith(v)`,单一来源 `harness_safety.VERBS` 复用,不复制。

### L14 — Major architectural initiative: build CHECKPOINT.md FIRST
多文件倡议(>3 artifacts)先建 `.runtime/<scope>/CHECKPOINT.md`(状态表 + 步骤 + 硬约束 + 续跑日志),每步翻转时更新——断点恢复成本从"重读一切"降到"读顶部 + 最后 ✅"。

### L15 — Multi-perspective review without sub-agents: fold into artifact bodies
无并行子代理时,把多角色视角折进相关 ADR/Spec 的专属小节(§Architect Risks / §Domain Use Cases / §Quality Invariants),不产独立意见文档(省 30-50% token)。

### L16 — AGENTS.md surgical edits at >500 lines
>500 行时用行锚定 `sed -i.bak` + `a\` 追加;先 `cp AGENTS.md /tmp/AGENTS.md.bak`,diff 验证后删 .bak;绝不整体重写(会丢 CADL hook 行引用、L*-rule 编号等对齐标记)。

### L17 — YAML frontmatter readers must look up `metadata.*` first, fallback top-level
读取 SKILL.md frontmatter 先查 `metadata.<key>` 再回退顶层:`val = (meta.get(key) if isinstance(meta, dict) else "") or fm.get(key, "")`(否则 ~30 文件报空字段,Phase 1 commit 60a6cf8)。

### L18 — `ruamel.yaml` round-trip preserves per-sequence indent; `yaml.dump` does not
批量改 frontmatter 用 `ruamel.yaml.YAML(typ="rt")` + `YAML.indent(mapping=2, sequence=4, offset=2)`;别用 PyYAML `yaml.dump`(统一缩进会搅动 30 文件 diff,Phase 1 commit f764c9a)。先 `--dry-run`。

### L19 — Cross-instance races need file locks + forced reload; weak asserts mask lost updates
`threading.Lock` 只串行化同实例;多实例/多进程共享数据目录时用 per-resource `fcntl.flock` 锁文件包住读改写,锁内**强制重载**磁盘状态(bypass 内存缓存,如 `_load_index(force_reload=True)`),否则陈旧缓存掩盖他进程更新。Windows 无 fcntl 时降级为线程锁并注释说明。并发测试用 `>= N` + `except: pass` 容忍冲突会假绿(实测双实例 15+15 保存后断言 `>=5` 通过),修复后收紧为精确断言(如 `== 31` + `errors == []`)证明零丢失。

### L20 — unittest default buffer=False: direct calls to print-capable functions leak stdout into CI logs
`python -m unittest discover` 默认 buffer=False;测试内直接调用会打印的函数(如 self_verify→_print_alerts)会把告警表格泄漏进 validate_local 日志,伪造假告警。修复:用 `contextlib.redirect_stdout(io.StringIO())` 包裹直接调用(CLI 子进程已有 capture_output 不受影响)。诊断:日志告警与 CLI 直跑矛盾时,优先怀疑测试输出泄漏而非数据漂移。

## Adding or modifying a skill

1. **New skill**: Use `qcloud-skill-generator` (enforces 2-round review).
2. **Existing skill update**: Read meta-skill workflow, apply 2-round self-review.
3. After `git add`, re-run Round 2 against staged version.

## Files that do NOT exist

- No repo-root `assets/` directory.
- No repo-root `Makefile`, `package.json`, or non-stdlib test runner (except listed scripts in `scripts/` and `.github/workflows/validate-skills.yml`). A scripts/Makefile exists as the harness convergence entry point — it is NOT a repo build system.
- No agent-specific config files (e.g. `CLAUDE.md`, `opencode.json`, `.cursorrules`, and similar per-agent artifacts).
- Agent runtime state dirs (e.g. `.omc/`, `.omo/`, `.codebuddy/`, and similar) are gitignored.
- `docs/superpowers/plans/` contains historical notes, not runtime source.

## Key References

| Document | Description |
|----------|-------------|
| `qcloud-skill-generator/SKILL.md` | Meta Skill generator — full workflow, P0/P1 checklist, Token Efficiency rules |
| `qcloud-skill-generator/references/governance-and-adversarial-review.md` | Governance & adversarial review — R1–R4 pre-merge security/resilience/UX |
| `qcloud-skill-generator/references/qcloud-skill-template.md` | Canonical SKILL.md template |
| `qcloud-skill-generator/references/user-experience-spec.md` | UX compliance requirements |
| `docs/gcl-spec.md` | Runtime GCL spec — rubric, trace schema, prompt templates |
| `docs/reflexion-memory.md` | Reflexion rules — cross-session failure-pattern memory governance |
| `docs/failure-patterns.md` | Reflexion memory store |
| `docs/cadl-spec.md` | CADL long-form spec — trigger conditions, 5-step loop, asset types, anti-patterns |
| `docs/architecture/README.md` | ADR index — cross-subsystem decisions |
| `docs/architecture/ADR-0001-establish-adr-mechanism.md` | ADR mechanism — format, lifecycle, when to write |

## Runtime Quality Gates: GCL & Reflexion

Detailed specs externalized to reduce context size. Read before modifying:
- `docs/gcl-spec.md`: GCL-related changes
- `docs/reflexion-memory.md`: Reflexion-related changes
- `docs/failure-patterns.md`: Only when retrieving/updating failure patterns

### GCL hard constraints

- Production GCL requires isolated Generator and Critic contexts. Critic is read-only (no `tccli`/SDK calls, no resource mutation) and sees only sanitized `{{output.operation_intent}}`, Generator output, trace, and rubric.
- Orchestrator generates `operation_intent` before Critic scoring (omits raw user wording, credentials, sensitive IDs).
- `Safety = 0` / `SAFETY_FAIL` aborts immediately.
- Every GCL loop bounded by `max_iterations`; persists masked trace under `audit-results/gcl-trace-*.json`.
- Production MUST use external isolated Critic scores; `--structural-critic-only` only for CI/local smoke tests.
- GCL prompt templates use `{{env.*}}`/`{{user.*}}`/`{{output.*}}` (no bare `{...}`).

### Reflexion hard constraints

- Reflexion retrieval is optional hint, not mandatory gate.
- `docs/failure-patterns.md` ≤ 200 lines.
- Deduplicate patterns by `skill` + `command` + `error`; from GCL trace `failure_pattern` or self-review findings only.
- Promote high-frequency patterns to anti-pattern docs.
- Independent gate from build-time 2-round self-review (build-time and runtime GCL are separate gates).

## GCL Trigger Check (MANDATORY)

Before coding, check if GCL is required — any YES triggers GCL Multi sub-Agent architecture:

1. **Task type**: Contains 修复/新增/重构/变更/优化/测试 or fix/add/refactor/change/optimize/test? → YES
2. **Code lines**: Expected change >5 lines? → YES
3. **File type**: Modifying `*/SKILL.md`, `*/references/rubric.md`, `*/references/prompt-templates.md`, `AGENTS.md`, `qcloud-skill-generator/SKILL.md`, `docs/gcl-spec.md`, `docs/reflexion-memory.md`? → YES
4. **Ops config**: Modifying YAML/JSON/TOML/HCL/Terraform/K8s/Ansible/Docker Compose? → YES (no exceptions)

### GCL Execution Steps (when triggered)

0. **Pre-flight check**: Confirm current branch is not `main`/`master`/`trunk` and `git remote -v` points to the expected remote. Pause if on a protected branch or mismatched remote.
1. Create worktree: `git worktree add ../<repo>-<feature> -b feature/<feature>`
2. Announce model configuration: Generator (vendor X) + Critics (vendor Y, ≥2, different from Generator)
3. Launch Generator Agent in worktree
4. Launch ≥2 parallel Critic Agents (Data Quality, Safety Rules, Spec Compliance, Token Efficiency)
5. Execute GCL loop (max_iter per skill defaults — see `docs/gcl-spec.md` §8): Generator code → Critics parallel review → Generator fix → Critics re-review
6. Main Agent makes PASS/RETRY/ABORT decision, merges, deletes worktree

### Hard Rule: Worktree Lifecycle (applies to ALL worktree tasks)

Every feature developed in a git worktree MUST be merged back to `main` and the
worktree cleaned up once the task is complete — mandatory for **every** worktree,
not only GCL-triggered ones.

1. **Merge back**: From the `main` checkout, `git merge --no-ff feature/<feature>` (or fast-forward if linear).
2. **Clean up**: `git worktree remove ../<repo>-<feature> --force` then `git branch -d feature/<feature>`.
3. **Verify**: `git worktree list` shows only the `main` checkout; no orphaned worktree directories remain on disk.

### Exceptions

- <5-line typo/comment fixes
- Pure doc/formatting changes

### Verification

After task completion, run: `python3 scripts/verify_gcl_execution.py "<task_description>" <commit_hash>`

## 复利资产沉淀机制（Compound-Asset Distillation Loop, CADL, P0）

实质任务完成 = 走完 CADL 闭环（不做沉淀 = 任务未完成）。**长篇规范 → [`docs/cadl-spec.md`](docs/cadl-spec.md)**；本节只列硬规则。

### 硬规则（MUST / SHOULD NOT）
- **MUST**：每个完成的任务走 5 步：`提取 → 落点判定 → 写入 → 门禁 → 复用`（详见 `docs/cadl-spec.md` §3）。
- **MUST**：所有 `qcloud-*-ops/SKILL.md` 末尾保留规范的钩子行；`scripts/cadl_lint.py` 是强制门禁，缺钩子即构建失败。
- **MUST**：沉淀前先 `grep` 现有 AGENTS.md / `docs/failure-patterns.md` 避免重复（去重键：`skill + command + error`）。
- **MUST**：写本文件前查 `wc -l AGENTS.md`；≥500 行先精简再写。
- **SHOULD NOT**：一次性上下文、跨任务无复用价值的经验，写进 AGENTS.md。
- **SHOULD NOT**：覆盖 Reflexion 的 200 行 cap 或去重约束（详见 `docs/reflexion-memory.md`）。

### 钩子行（canonical hook, byte-for-byte）
```
> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
```
源头：`qcloud-skill-generator/references/qcloud-skill-template.md` 末尾。`Standard 6` 在生成时强制注入；`scripts/cadl_lint.py` 在验证时强制存在。

### 快速入口
- 自动化：`python3 scripts/cadl_lint.py`（lint）/ `--fix`（幂等补钩子）

## Architecture Decision Records (ADR, P0)

ADR 记录**跨子系统**架构决策（参见 [`docs/architecture/ADR-0001-establish-adr-mechanism.md`](docs/architecture/ADR-0001-establish-adr-mechanism.md) §2.5 边界规则）。

### ADR vs CADL 边界

| 触发 | 落点 |
|---|---|
| 影响 >1 个子系统 / 运行时拓扑 / 长期方向 | ADR（`docs/architecture/ADR-NNNN-*.md`） |
| 单次任务经验 / CLI 错误模式 / 跨任务小技巧 | CADL（`docs/failure-patterns.md` 或本文件 L*-rules） |

**Rule of thumb**："We picked X over Y because …" → ADR；"I learned a tricky parameter" → CADL。


## Agent-Agnostic Principle (P0)

**本仓库的全部规则、规范、质量门与沉淀机制，均不绑定任何特定的 coding agent 或其运行时检测机制（所谓"扣点检测"）。规则在任何 OpenSpec 兼容 agent 下都应可被落实。**

- **不依赖特定 agent 的目录 / 文件制品**：如 `.codegraph/`、`.omc/`、`.omo/`、`.codebuddy/` 等属各 agent 自身运行时状态，本仓库规则不得将其作为触发或判定条件；它们仅被 gitignore，不参与规则落实。
- **不硬编码特定 agent 的指引文件路径**：用户级 / 项目级指引文件（AGENTS / CLAUDE / CURSOR 等）的路径随所用 agent 而变，规则只描述"落到哪一层（用户级 / 项目级 / 独立 Skill）"，不写死具体产品路径。
- **工具可选，提供等价 fallback**：当某规则推荐具体工具（如代码智能、KG 索引）时，必须同时给出不依赖该工具的等价做法（如 Read / Grep），使规则在缺失该工具的环境下依然成立。
- **规则以行为结果为导向**：每条规则以"期望的可验证结果"定义（如"任务结束前完成资产沉淀""破坏性操作前确认"），而非"调用某 agent 的某命令"。这样无论底层 agent 是 OpenCode / Cursor / Claude Code / 其他，行为一致。

> 本原则是本文件的最高约束之一：任何新增规则若隐含对特定 coding agent 的依赖，视为违反 P0，须在合并前解耦。

## CodeGraph — code intelligence (P0, mandatory where available)

> **Agent-Agnostic note:** CodeGraph is an optional local tool. If the current agent
> environment provides it (`.codegraph/` + `codegraph_explore`), the rules below are
> **mandatory**. If unavailable, fall back to Read / Grep directly — the *expected
> result* (accurate, blast-radius-aware code understanding) is unchanged. Never blocks work.

`.codegraph/` (SQLite KG + file watcher) pre-indexes every symbol, edge, and call
path in THIS repo. `codegraph_explore` is the Read-equivalent: one capped call
returns verbatim source PLUS caller/callee blast-radius and test-coverage flags.
Sync half already enforced in `qcloud-copilot/SKILL.md` ("改 `.py` 后 `codegraph sync`")
and the two `agent-inspection-prompt.md` checklists.

### Rule 0 — CodeGraph-first, Grep-last (P0, hard rule)

For ANY code-understanding task in THIS repo, execution order:

```
A. Execute codegraph_explore     ← MUST try first (when CodeGraph available)
B. Fallback to Read (specific file)  ← only if CodeGraph unavailable or staleness banner
C. Resort to Grep                  ← LAST RESORT, only for patterns CodeGraph can't answer
```

**Violation**: Grep or Explore sub-agents for tasks `codegraph_explore` can answer is
a process violation (5 Explore sub-agents, 16–22 min, zero results vs one call — see Rule 4).

### Rule 1 — Query-first (highest frequency)

Prefer `codegraph_explore` with symbol/file names or a natural-language question;
ONE call usually answers the whole question and returns source you can `Edit` from
directly. "how does X work" / architecture / a bug / "where is X" → `codegraph_explore`.
Reading/editing a named symbol → put its name in the query; treat returned source as
already Read. Need a flow across symbols → name the endpoints; it rides
dynamic-dispatch hops grep can't follow.

### Rule 2 — API-First before writing tests or invoking external tools (P0 when CodeGraph available)

Before writing tests for any module/class, or before calling an external tool/MCP
that depends on a module's API, confirm the actual signature with `codegraph_explore`.
Misread signatures cause: (1) tests that crash at import, (2) tests that pass against
wrong behavior, (3) rework in CI. **Workflow**: `codegraph_explore <symbol_name>` →
if stale (staleness banner) `Read` the file → only then write tests. **Fallback**
(no CodeGraph): `Read` the source directly. Applies to ALL test files, including
those written in previous sessions or by other agents. Evidence: `ml/predictors/` and
`lib/selective_workflow` tests without signature confirmation → `TypeError` on every
test (3 rounds of rework); after confirmation, all 49 tests pass in one shot.

### Rule 3 — Sync after edits

After editing code files in a CodeGraph-enabled environment, the index lags writes by
~1s. Before the NEXT `codegraph_explore` that depends on the edit, confirm sync; if a
query returns a staleness banner for a file you just wrote, `Read` that specific file.

### Rule 4 — anti-pattern: Grep/sub-agent for indexed code (CodeGraph environments)

Do NOT fire `explore` / `librarian` sub-agents or run grep+read loops to map code THIS
repo already indexes (one session: 5 delegated `explore` agents hung 16–22 min and
returned nothing; one `codegraph_explore` call answered with blast-radius + coverage
flags). Delegated agents are for UNINDEXED targets (other repos, web, docs), never for
re-deriving the local KG. (In non-CodeGraph environments this rule is moot — just Read / Grep.)

### Rule 5 — scope guard

- CodeGraph covers THIS repo only. For an unindexed project, run `codegraph init` first
  (don't run it yourself unprompted — it's the user's decision).
- It does NOT index configs/docs as code; use Read/Grep for those.
- It is read-only intelligence. Correctness is still the compiler/tests' job — trust
  the returned source, but verify with LSP/tests before claiming done.

### What to extract from each result

- **Source blocks**: safe to Edit from; do not re-Read.
- **Blast radius** ("N callers", "⚠️ no tests found"): scope your change and know
  what needs new tests BEFORE editing.
- **Staleness banner**: only the listed files are pending re-index — Read those, trust the rest.

## Code Review Best Practices

> 来自 Phase G review 实战：5 分钟读代码发现 1 个 CRITICAL + 2 个 HIGH 安全隐患，单元测试 100% 通过但从未触发。

### Review 时必须检查的边界（与测试正交）

- **审计/日志类**：`__exit__` 是否 re-raise 原始异常？（静默吞异常 = 审计数据丢失, CRITICAL）；写入文件时磁盘满 / 权限错误是否有 fallback？
- **外部调用类**：`subprocess.run()` 后是否检查 `returncode`？错误信息是否可见给调用方？tccli/API 失败时是否一致检查 `"Error"` key？
- **正则类**：regex 是否在 `__post_init__` 预编译（不在循环/热路径现编译）？是否有搜索长度限制（`[:10_000]`）防止 ReDoS？
- **Fallback/降解类**：模块级 fallback 用 `except Exception` 而非 `except ImportError`（捕获语法错误和传递依赖）；外部库私有属性（`_tree_variance` 等）跨版本可能失效 → 用公共 API 替代
- **Docstring 类**：示例代码块是否与实际 `__init__` 签名一致？默认路径/配置是否与代码一致？

### Review 产出标准

每条 issue 必须包含：`file:line` 精确定位、severity 评级（CRITICAL/HIGH/MEDIUM/LOW）、修复建议（具体代码，不是方向）。

### 子 Agent MCP 不可用时的 Fallback

code-reviewer 返回 403 → 直接用 `Read` 工具读文件，手动执行上述检查列表。

## Senior Delivery Protocol

- **Autonomous execution**: Once requirements and risk boundaries are clear, proceed without repeated confirmation; ask only when an irreversible decision or missing external fact cannot be safely inferred.
- **Complexity-based isolation**: For multi-file, high-risk, or parallel work, choose a worktree when it improves isolation or rollback. Merge, verify, and remove it before handoff; keep small, low-risk changes in the current checkout.
- **Plan-before-code**: For substantial work, complete SPEC/PLAN and execution gates before touching implementation. Do not use documentation as a substitute for tests or verification.
- **Evidence before claims**: Never claim fixed, complete, or passing without fresh command output. Report pre-existing failures separately from regressions introduced by the task.
- **Minimal senior refactoring**: Prefer root-cause fixes and coherent boundaries over compatibility clutter; preserve legacy adapters only where they protect existing consumers, and define their removal criteria.
- **Post-delivery review**: After every substantial task, review architecture, tests, failures, operational risks, and reusable lessons. Record only cross-task assets; place repo-wide rules here and detailed patterns in the narrowest relevant document.
- **AGENTS.md budget**: Before adding rules, search for overlap and check line count. If this file grows, consolidate or move detailed examples/checklists to linked docs; keep this file as a concise policy index.

## 进度文档维护规范（Progress Document Maintenance）

> 进度文档是团队协作的事实来源；任务完成但文档未更新等于未交付。

### 触发条件

满足任一即必须更新对应进度文档（与 CADL 触发条件重叠，不重复）：

- 任意 SPEC/PLAN 中标记的任务项完成（`[ ]` → `[x]`/`[⚠️]`/`[❌]`）
- 跨 Phase 依赖打通或新增遗留项
- 架构决策变更（即使未写代码）
- Pre-existing 问题发现（不影响本任务但需记录）

### 范围认定

进度文档包括：`docs/superpowers/plans/*.md` 中的 Phase/Step checkbox 表、`docs/superpowers/specs/*.md` 中的 DoD/验收标准对照表。

每项勾选须注明：状态（`[x]` 完成 / `[⚠️]` 部分完成 / `[❌]` 放弃）、证据（commit hash 或变更摘要）、说明（关键决策、遗留项、跨 Phase 依赖）。

### 最小更新单位

- 单个 `[ ]` 勾选可单独更新，无需等待整个 Phase 完成
- 跨 Phase 共用项在一个 Phase 更新后，其他 Phase 同步勾注引用
- DoD 未满足但需继续前进时，先标记 `[⚠️]` + 说明阻塞原因，再继续

### 反模式

| 反模式 | 正确做法 |
|---|---|
| 任务完成后不更新 plan，留在 `[ ]` 状态 | 立即更新 checkbox + 证据 |
| 遗留项不记录，假装已完成 | 标记 `[ ]` 保留或 `[❌]` + 说明原因 |
| 只更新 checkbox 不写证据 | 证据是必需的；无 commit 时写变更摘要 |
| 批量完成后一次性补更新 | 单项完成即更新，不攒批 |

### 与 CADL 的关系

进度文档更新是 CADL "复用" 步骤的显式门禁之一：完成某项后若不更新进度文档，CADL 闭环不完整。不要求每条 CADL 都写进度文档（那是规范层），但每条 SPEC/PLAN checkbox 变更必须同步。

### AGENTS.md 行数门禁

本规范若使 AGENTS.md ≥500 行，应将详细示例/检查清单移至 linked docs，保持本文件为简洁策略索引。
