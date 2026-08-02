# qcloud-skills — Agent guidance

## Repo purpose

Collection of Tencent Cloud AI Agent skills (OpenSpec) for ops runbooks. Each skill is a `SKILL.md` file with YAML frontmatter. Live work happens via `tccli` CLI (primary) or `tencentcloud-sdk-python` (fallback).

## Layout

```
qcloud-skills/
  scripts/                     # Shared executables: validate_*, gcl_runner, gcl_trace_aggregate
  audit-results/               # Runtime output (gitignored)
  qcloud-[product]-ops/        # 34 skill directories
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
- **Shared constants (TE-4/TE-6)**: Use `assets/shared/` for cross-skill constants:
  - `destructive_verbs.json` — destructive verb list for safety gates
  - `thresholds.json` — GCL/Reflexion/AGENTS.md thresholds
  - `validation_commands.yaml` — all validation command strings

## Coding Discipline

通用行为准则详见 `~/.pi/agent/AGENTS.md §行为准则`（中英等价权威源）。本仓库仅需遵循，不重复定义。

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
- **Build-time regression commands** (see `assets/shared/validation_commands.yaml` for full list):
  - `validate_local` — Full local validation
  - `validate_frontmatter` — SKILL.md frontmatter
  - `validate_assessment` — well-architected-assessment.md JSON
  - `validate_gcl` — GCL rubric/prompt/Quality Gate
  - `validate_cadl` — CADL hook compliance
  - `validate_python` — Python files (ruff)
  - `script_tests` — Script unit tests
  - `validate_links` / `validate_markdown_python` — Markdown specs/links/Python blocks
  - `gcl_smoke` + `gcl_trace_aggregate` — GCL smoke + trace aggregation
  - `skill_quality_score` — Skill quality score / upgrade signal
  - `reflexion_retrieve` — Reflexion retrieval (self-evolution)
  - `gcl_alarm_wire` — GCL alarm wiring

- **Runtime GCL**: `scripts/gcl_runner.py` requires external isolated Critic scores in production. `--structural-critic-only` only for CI/local smoke tests.

## Execution lessons (CADL — distilled, reusable)

> Machine-hardened lessons updated as tasks land; de-duplicated against rules above. Absorb before writing test or credential-masking code.

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
| `qcloud-skill-generator/references/qcloud-skill-template.md` | Canonical SKILL.md template (with YAML anchors for common frontmatter) |
| `qcloud-skill-generator/references/user-experience-spec.md` | UX compliance requirements |
| `docs/gcl-spec.md` | Runtime GCL spec — rubric, trace schema, prompt templates |
| `docs/reflexion-memory.md` | Reflexion rules — cross-session failure-pattern memory governance |
| `docs/failure-patterns.md` | Reflexion memory store |
| `docs/cadl-spec.md` | CADL long-form spec — trigger conditions, 5-step loop, asset types, anti-patterns |
| `docs/architecture/README.md` | ADR index — cross-subsystem decisions |
| `docs/architecture/ADR-0001-establish-adr-mechanism.md` | ADR mechanism — format, lifecycle, when to write |

## GCL & Reflexion — summary (details in linked docs)

**GCL hard constraints** (`docs/gcl-spec.md`):
- Production GCL requires isolated Generator and Critic contexts. Critic is read-only, sees only sanitized `{{output.operation_intent}}`, Generator output, trace, and rubric.
- `Safety = 0` / `SAFETY_FAIL` aborts immediately.
- Every GCL loop bounded by `max_iterations`; persists masked trace under `audit-results/gcl-trace-*.json`.
- Production MUST use external isolated Critic scores; `--structural-critic-only` only for CI/local smoke tests.
- GCL prompt templates use `{{env.*}}`/`{{user.*}}`/`{{output.*}}` (no bare `{...}`).

**Reflexion hard constraints** (`docs/reflexion-memory.md`):
- Reflexion retrieval is optional hint, not mandatory gate.
- `docs/failure-patterns.md` ≤ 200 lines.
- Deduplicate patterns by `skill` + `command` + `error`; from GCL trace `failure_pattern` or self-review findings only.
- Promote high-frequency patterns to anti-pattern docs.
- Independent gate from build-time 2-round self-review.

**GCL Trigger Check (MANDATORY)** — any YES triggers GCL Multi sub-Agent architecture:
1. **Task type**: Contains 修复/新增/重构/变更/优化/测试 or fix/add/refactor/change/optimize/test? → YES
2. **Code lines**: Expected change >5 lines? → YES
3. **File type**: Modifying `*/SKILL.md`, `*/references/rubric.md`, `*/references/prompt-templates.md`, `AGENTS.md`, `qcloud-skill-generator/SKILL.md`, `docs/gcl-spec.md`, `docs/reflexion-memory.md`? → YES
4. **Ops config**: Modifying YAML/JSON/TOML/HCL/Terraform/K8s/Ansible/Docker Compose? → YES (no exceptions)

**GCL Execution** — create worktree, Generator + ≥2 Critics parallel review, GCL loop, PASS/RETRY/ABORT, merge & cleanup worktree. See `docs/gcl-spec.md` for full flow.

**Worktree Lifecycle (applies to ALL worktree tasks)**:
1. Merge back: `git merge --no-ff feature/<feature>`
2. Clean up: `git worktree remove ../<repo>-<feature> --force` then `git branch -d feature/<feature>`
3. Verify: `git worktree list` shows only `main` checkout.

## CADL — 复利资产沉淀机制 (P0)

实质任务完成 = 走完 CADL 闭环。长篇规范 → `docs/cadl-spec.md`；本节只列硬规则。

**硬规则（MUST / SHOULD NOT）**：
- **MUST**：每个完成的任务走 5 步：`提取 → 落点判定 → 写入 → 门禁 → 复用`（详见 `docs/cadl-spec.md` §3）。
- **MUST**：所有 `qcloud-*-ops/SKILL.md` 末尾保留规范的钩子行；`scripts/cadl_lint.py` 是强制门禁，缺钩子即构建失败。
- **MUST**：沉淀前先 `grep` 现有 AGENTS.md / `docs/failure-patterns.md` 避免重复（去重键：`skill + command + error`）。
- **MUST**：写本文件前查 `wc -l AGENTS.md`；≥500 行先精简再写。
- **SHOULD NOT**：一次性上下文、跨任务无复用价值的经验，写进 AGENTS.md。

**钩子行（canonical hook）**：
```
> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
```
源头：`qcloud-skill-generator/references/qcloud-skill-template.md` 末尾。生成时强制注入；`scripts/cadl_lint.py` 验证时强制存在。

**快速入口**：`python3 scripts/cadl_lint.py`（lint）/ `--fix`（幂等补钩子）

## Architecture Decision Records (ADR, P0)

ADR 记录**跨子系统**架构决策（参见 `docs/architecture/ADR-0001-establish-adr-mechanism.md` §2.5 边界规则）。

**ADR vs CADL 边界**：
| 触发 | 落点 |
|---|---|
| 影响 >1 个子系统 / 运行时拓扑 / 长期方向 | ADR（`docs/architecture/ADR-NNNN-*.md`） |
| 单次任务经验 / CLI 错误模式 / 跨任务小技巧 | CADL（`docs/failure-patterns.md` 或本文件 L*-rules） |

"We picked X over Y because …" → ADR；"I learned a tricky parameter" → CADL。

## Agent-Agnostic Principle (P0)

本仓库的全部规则、规范、质量门与沉淀机制，均不绑定任何特定的 coding agent 或其运行时检测机制。规则在任何 OpenSpec 兼容 agent 下都应可被落实。

- 不依赖特定 agent 的目录 / 文件制品（如 `.codegraph/`、`.omc/`、`.omo/`、`.codebuddy/` 等）。
- 不硬编码特定 agent 的指引文件路径（AGENTS / CLAUDE / CURSOR 等路径随 agent 而变）。
- 工具可选，提供等价 fallback（如代码智能推荐具体工具时，必须给出 Read/Grep 等价做法）。
- 规则以行为结果为导向（如"任务结束前完成资产沉淀"），而非"调用某 agent 的某命令"。

## CodeGraph — code intelligence (P0, mandatory where available)

> **Agent-Agnostic note:** CodeGraph is optional. If available (`.codegraph/` + `codegraph_explore`), rules below are mandatory. If unavailable, fall back to Read / Grep — expected result unchanged.

`codegraph_explore` is Read-equivalent: one call returns verbatim source + call path + blast radius.

**Rule 0 — CodeGraph-first, Grep-last (P0)**: For ANY code-understanding task in THIS repo: A) `codegraph_explore` → B) `Read` specific file (if stale) → C) `Grep` (LAST RESORT).

**Rule 1 — Query-first**: Prefer `codegraph_explore` with symbol/file names or natural-language question.

**Rule 2 — API-First before tests**: Confirm actual signature with `codegraph_explore` before writing tests or calling external tools.

**Rule 3 — Sync after edits**: Before next `codegraph_explore` depending on edit, confirm sync; if staleness banner, `Read` that file.

**Rule 4 — anti-pattern**: Do NOT fire `explore` / `librarian` sub-agents or grep+read loops for indexed code.

**Rule 5 — scope guard**: CodeGraph covers THIS repo only. Doesn't index configs/docs. Read-only intelligence; verify with compiler/tests.

## Code Review Best Practices

> 来自 Phase G review 实战：5 分钟读代码发现 1 个 CRITICAL + 2 个 HIGH 安全隐患，单元测试 100% 通过但从未触发。

**Review 时必须检查的边界（与测试正交）**：
- **审计/日志类**：`__exit__` 是否 re-raise 原始异常？（静默吞异常 = 审计数据丢失, CRITICAL）；写入文件时磁盘满 / 权限错误是否有 fallback？
- **外部调用类**：`subprocess.run()` 后是否检查 `returncode`？错误信息是否可见给调用方？tccli/API 失败时是否一致检查 `"Error"` key？
- **正则类**：regex 是否在 `__post_init__` 预编译？是否有搜索长度限制（`[:10_000]`）防止 ReDoS？
- **Fallback/降解类**：模块级 fallback 用 `except Exception` 而非 `except ImportError`；外部库私有属性跨版本可能失效 → 用公共 API 替代
- **Docstring 类**：示例代码块是否与实际 `__init__` 签名一致？默认路径/配置是否与代码一致？

**Review 产出标准**：每条 issue 必须包含：`file:line` 精确定位、severity 评级（CRITICAL/HIGH/MEDIUM/LOW）、修复建议（具体代码，不是方向）。

**子 Agent MCP 不可用时的 Fallback**：code-reviewer 返回 403 → 直接用 `Read` 工具读文件，手动执行上述检查列表。

## Senior Delivery Protocol

- **Autonomous execution**: Once requirements and risk boundaries are clear, proceed without repeated confirmation; ask only when an irreversible decision or missing external fact cannot be safely inferred.
- **Complexity-based isolation**: For multi-file, high-risk, or parallel work, choose a worktree when it improves isolation or rollback. Merge, verify, and remove it before handoff.
- **Plan-before-code**: For substantial work, complete SPEC/PLAN and execution gates before touching implementation. Do not use documentation as a substitute for tests or verification.
- **Evidence before claims**: Never claim fixed, complete, or passing without fresh command output. Report pre-existing failures separately from regressions introduced by the task.
- **Minimal senior refactoring**: Prefer root-cause fixes and coherent boundaries over compatibility clutter; preserve legacy adapters only where they protect existing consumers, and define their removal criteria.
- **Post-delivery review**: After every substantial task, review architecture, tests, failures, operational risks, and reusable lessons. Record only cross-task assets; place repo-wide rules here and detailed patterns in the narrowest relevant document.
- **AGENTS.md budget**: Before adding rules, search for overlap and check line count. If this file grows, consolidate or move detailed examples/checklists to linked docs; keep this file as a concise policy index.

## 进度文档维护规范（Progress Document Maintenance）

进度文档是团队协作的事实来源；任务完成但文档未更新等于未交付。

**触发条件**：满足任一即必须更新（与 CADL 触发条件重叠，不重复）：
- 任意 SPEC/PLAN 中标记的任务项完成
- 跨 Phase 依赖打通或新增遗留项
- 架构决策变更（即使未写代码）
- Pre-existing 问题发现（不影响本任务但需记录）

**范围认定**：进度文档包括 `docs/superpowers/plans/*.md` 中的 Phase/Step checkbox 表、`docs/superpowers/specs/*.md` 中的 DoD/验收标准对照表。

**最小更新单位**：单个 `[ ]` 勾选可单独更新；跨 Phase 共用项同步勾注引用；DoD 未满足时先标记 `[⚠️]` + 说明阻塞原因。

**反模式**：
| 反模式 | 正确做法 |
|---|---|
| 任务完成后不更新 plan，留在 `[ ]` 状态 | 立即更新 checkbox + 证据 |
| 遗留项不记录，假装已完成 | 标记 `[ ]` 保留或 `[❌]` + 说明原因 |
| 只更新 checkbox 不写证据 | 证据是必需的；无 commit 时写变更摘要 |
| 批量完成后一次性补更新 | 单项完成即更新，不攒批 |

**与 CADL 的关系**：进度文档更新是 CADL "复用" 步骤的显式门禁之一：完成某项后若不更新进度文档，CADL 闭环不完整。

**AGENTS.md 行数门禁**：本规范若使 AGENTS.md ≥500 行，应将详细示例/检查清单移至 linked docs，保持本文件为简洁策略索引。