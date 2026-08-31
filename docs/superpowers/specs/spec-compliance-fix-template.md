# Spec Compliance BLOCKER 一键修复模板 (spec_compliance)

## Problem Statement

`spec_compliance` 是 GCL 评分维度之一（MTTR ≈ 6.0m，未模板化）。trace 调研
（75 文件 / 111 iterations）发现两类问题：

| 现象 | 次数 | 根因 |
|------|------|------|
| `spec refs unresolved; audit gap` / `refs/xxx not found` | 3+3 | spec 文档引用了不存在的文件 |
| `yaml_python_drift — YAML=[...], PY=[...]` | 2+3 | `tool_state_schema.yaml` 与 `state_dependency.py` 漂移 |
| `echo {...}` mock 响应缺字段 / 形状不符（score 0.5/0.0） | 36+ | Generator 用假响应应付，未按 spec 产出 |
| `analyze` 纯分析命令无结构化输出（score 0.0） | 6 | 命令没产出 spec 要求的字段 |

MTTR 高的根因不是修复难，而是**每次从零判断**：这份 suggestion 属于哪一类？
跑哪个 check？改哪个文件？模板把「分类 → 定位 → 修复」全部前置。

## 失败模式分类决策树（先查表，再动手）

```
suggestion 含 "refs/" 或 "references/" 或 "not found" 或 "does not exist"
├─ 是 → 场景 1（spec 文件引用缺失）
suggestion 含 "yaml_python_drift" 或 "YAML=[" 或 "PY="
├─ 是 → 场景 2（YAML↔Python 漂移，转 yaml-drift-fix-template.md）
suggestion 含 "missing" + "field" 或 command 是 echo/mock/假数据
├─ 是 → 场景 3（mock 输出不满足 spec）
command 是 analyze/解释类，无结构化输出
└─ 是 → 场景 4（分析命令缺输出契约）
```

## 标准修复步骤（5 步）

| # | 步骤 | 动作 | 耗时 |
|---|---|---|---|
| 1 | 分类 | 用上方决策树判断 suggestion 属于哪一场景 | ~10s |
| 2 | 定位 | 跑对应 check 脚本（见各场景）得到精确文件 + 行号 | ~30s |
| 3 | 修复 | 按场景粘贴片段 / 同步两侧 | ~1m |
| 4 | 复跑 | 重跑同一 check 到 `exit=0` | ~30s |
| 5 | 验收 | 跑下方验收清单 | ~1m |

## 场景 1: spec 文件引用缺失（`spec refs unresolved`）

**定位**：
```bash
python3 scripts/check_spec_file_refs.py   # 输出每个缺失 ref 的 spec 文件 + 行号
```

**修复**：二选一，优先 A。
- **A. 引用是错的（推荐）**：把 spec 文档里的错误引用改为真实路径，或删掉引用。
- **B. 引用对应的文件确实该存在**：创建该文件（空壳补全），再跑 check 到 `exit=0`。

**判断技巧（<30s）**：问「这份 spec 真的消费这个文件吗？」
- 不消费 → A（删/改引用）
- 消费且内容缺失 → B（建文件）
- 拿不准 → 选 A（删除引用不引入死文件，少一次往返）

## 场景 2: YAML ↔ Python 漂移（`yaml_python_drift`）

已独立模板化（MTTR 8m → 已降 -83%）。**直接转交**：
```bash
python3 scripts/check_yaml_python_drift.py
```
见 `docs/superpowers/specs/yaml-drift-fix-template.md`（权威源决策矩阵 + 修复示例）。

## 场景 3: mock 输出不满足 spec（echo / 假响应）

**定位**：查 GCL trace 中该命令的 `generator.command`。若为 `echo` / mock 字面量，
即为假响应。

**修复**：把假响应替换为**真实命令**或**符合 spec 形状的响应**。

### 3a. 能跑真实命令 → 用真实命令（首选）

```bash
# 假响应（不可接受）
echo '{"Response":{"RequestId":"ci-smoke"}}'
# → 真实命令
tccli cvm DescribeInstances --Region ap-guangzhou
```

### 3b. 必须 mock → 按 spec 补全字段

```python
# 假响应缺 spec 要求的字段（score 0.5）
data = {"Response": {"RequestId": "ci-smoke"}}
# → 按 spec 补全（每个 spec 必填字段都要有真实值，不用占位空串）
data = {
    "Response": {
        "RequestId": "ci-smoke",
        "TotalCount": 2,
        "InstanceSet": [{"InstanceId": "ins-xxx", "InstanceState": "RUNNING"}],
    }
}
```

**判断技巧（<30s）**：mock 的目的只是绕过真实 API 时，**先问能否直接跑真实命令**；
只有 CI/离线环境才允许 mock，且必须对齐 spec 字段（L5：断言真实值，不是键存在）。

## 场景 4: 纯分析命令无结构化输出（`analyze`）

**定位**：`generator.command` 以 `analyze`/`解释`/`说明` 开头且 `result_excerpt` 为散文。

**修复**：命令产出 spec 要求的结构化字段（YAML/JSON/表格），与 spec 的输出契约一致：

```bash
# 分析类命令输出结构化摘要，而不是纯散文
python3 scripts/analyze_spec_blockers.py --json > /tmp/spec-buckets.json
```

## 验收检查清单

- [ ] 对应 check 脚本复跑 `exit=0`：
  - 场景 1: `python3 scripts/check_spec_file_refs.py`
  - 场景 2: `python3 scripts/check_yaml_python_drift.py`
  - 场景 3/4: 无独立 hook，重跑 GCL 迭代直到 `spec_compliance` score = 1.0
- [ ] `python3 scripts/auto_fix_gcl_blockers.py --self-test` → 0
- [ ] mock 值非空壳：字段值为真实数据（非 `""` / 占位符）
- [ ] 修复理由写进 commit message（如 `spec-fix: drop dangling refs/cli-usage.md from cvm spec`）
- [ ] 非 mock 场景验证命令真实可执行（`tccli ... ` 有真实响应）

## 防复发

- 写 spec 文档时引用文件后**当场** `python3 scripts/check_spec_file_refs.py` 验证
- Generator 输出 mock 前自问：能否跑真实命令？（L11: KPI gate 只信真实输入）
- GCL Critic 见到 `spec_compliance` 降级时：直接引用本模板路径（含场景号），
  不再让 Generator 自行摸索
