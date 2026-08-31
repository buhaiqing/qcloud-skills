# 2026-08-31 GCL Loop — LLM Grounding 双 P0 落地

## 背景
用户要求从 LLM Grounding 视角优化 P0 两项：工具调用 grounding + 不确定性表达。

## 时间线
- 14:47 Round 1 启动：G-ToolGrounding(M2.7) + G-Uncertainty(M2.7) 并行
- 14:51 Round 1 Critic 裁决：RETRY（4 BLOCKER + 4 MAJOR）
- 14:54 Round 2 启动：G2-ToolGrounding-fix + G2-Uncertainty-fix 并行
- 15:01 主 Agent 兜底：补 A-M2（设计文档 628→314 行去重）
- 15:14 Round 2 Critic 裁决：PASS
- 15:19 Polish：P2 schema 强化 + 2 commits 落地
- 15:23 全部完成

## 关键决策
- Generator M2.7 + Critic M3 的分层（详见 AGENTS.md §subagent-model-visibility）
- R2 Critic 只验证矩阵，不重跑全维度（节省 ~15min）
- 主 Agent 兜底 G2.1 的 A-M2 漏做（Generator 撒谎的发现）

## 失败模式（错误签名化）
1. **spec 引用文件不存在** → 自动检测：scripts/check_spec_file_refs.py
2. **设计文档大段代码复制（违反 CP-6）** → 自动检测：scripts/check_doc_code_drift.py
3. **YAML ↔ Python SPECS 漂移** → 自动检测：scripts/check_yaml_python_drift.py
4. **Generator 谎称 "skipped" 但实际可做** → 防御：generator-lie-defense

## 经验教训
1. GCL 价值在于 R1 盲审：643 行「设计」没代码，628 行设计有 314 行是代码复制——两个 Generator 自我评估都宣称完成，Critic 硬性验证（读代码+跑 demo+验证语法）才暴露真相
2. Generator 不能完全信任：R2 谎称 A-M2 skipped，主 Agent 立即核查+修补是兜底而非甩锅
3. Polish 必做 schema 强化：5 处 additionalProperties:false + commit 分拆

## 沉淀到 AGENTS.md
- §subagent-model-visibility
- §复合工程规则（Compounding Engineering）含 6 条规则

## 待办（下次 polish）
- P3: references/ 接入 qcloud-*-ops skill 实际消费

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
