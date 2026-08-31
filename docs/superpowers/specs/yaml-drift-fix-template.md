# YAML ↔ Python Drift 一键修复模板 (yaml_python_drift)

> 目标：把 yaml_python_drift BLOCKER 的 MTTR 从 **12m** 降到 **<4m**。
> 慢的根因不在定位（check 脚本已输出）而在决策（哪份源是权威）+ 手工比对。
> 本模板把决策矩阵前置，修复者只需 5 步、每步 <1m。

## 触发

- `python3 scripts/check_yaml_python_drift.py` 输出 `✗ <tool>: YAML=[...], PY=[...]`
- GCL trace 中出现 `yaml_python_drift` BLOCKER（`spec_compliance` 降级）

## 标准步骤（5 步，每步 <1m）

1. **定位漂移对** — 读 `check_yaml_python_drift.py` 输出中的 `✗` 行（已含工具名 + 两侧差异 + FIX 建议 + 文件行号锚点）
2. **读 YAML 声明** — `references/toolgrounding/tool_state_schema.yaml` 中该工具的 `dependency.requires`
3. **读 Python SPECS** — `references/toolgrounding/state_dependency.py` 中该工具的 `StateDependency(requires=[...])`
4. **决定权威源** — 查下方决策矩阵（唯一需要业务判断的步骤）
5. **同步另一边 → 重跑 check** — `python3 scripts/check_yaml_python_drift.py` 到 `exit=0`

## 权威源决策矩阵

| 条件 | 权威源 | 动作 |
|------|--------|------|
| YAML 更完整（含真实业务依赖） | YAML | 补 Python SPECS（`state_dependency.py` 加 `StateAtom(...)`） |
| PY 更完整（含真实代码依赖） | PY | 改 YAML（`tool_state_schema.yaml` 删/改 `requires`） |
| 两处都只是 demo（无真实消费） | 任选 + 注释 | 同步即可，加 `# 待业务确认` 注释 |
| 有真实客户端消费（StateTracker.can_call） | 消费方为准 | 对齐消费方实际传入的状态 |

**判断技巧（<30s）**：问「业务上该工具调用时，被依赖的资源是否已存在？」
- 已存在（前置步骤产出）→ 依赖真实 → 补 PY
- 不存在（同批创建/独立资源）→ 依赖虚假 → 删 YAML
- 拿不准 → 选**更完整**的一方为权威（少一次往返），加注释留痕

## 修复示例

### cdb_create_account（R4 实案）
```
✗ cdb_create_account: YAML=[cdb_create.InstanceId, vpc_create.VpcId], PY=[cdb_create.InstanceId]
  → FIX (YAML 权威): state_dependency.py:60 补 StateAtom 依赖 ['vpc_create.VpcId']
```
- 业务检查：创建 CDB 账号必须先建 VPC 吗？**否**（VpcId 是 cdb_create 的副产物，非前置）→ YAML 是错的
- 动作：`tool_state_schema.yaml:78` 删 `vpc_create.VpcId` 依赖 → 重跑 check → exit=0
- 教训：YAML 里 `cdb_create.VpcId` 这类「产出副产物」被误写成依赖，是最常见假阳性

### vpc_create_flow_log
```
✗ vpc_create_flow_log: YAML=[vpc_create.VpcId], PY=[]  (示意)
```
- 业务检查：建流日志前必须已有 VPC？**是**（vpc_create 前置）→ YAML 权威
- 动作：`state_dependency.py` 补 `StateAtom("vpc_create", "VpcId")` → 重跑 check → exit=0

### ccn_attach_vpc
```
✗ ccn_attach_vpc: YAML=[ccn_create.CcnId], PY=[ccn_create.CcnId, vpc_create.VpcId]  (示意)
```
- 业务检查：挂载 VPC 前必须已有 CCN 和 VPC？**是** → PY 更完整 → YAML 权威更新
- 动作：`tool_state_schema.yaml` 补 `- tool: vpc_create / output: VpcId` → 重跑 check → exit=0

## 验收清单

- [ ] `python3 scripts/check_yaml_python_drift.py` → `exit=0`，`SUMMARY: 0 tool(s) drifted`
- [ ] `python3 -m py_compile references/toolgrounding/state_dependency.py` 通过（若改过 PY）
- [ ] `python3 -c "import yaml,sys; yaml.safe_load(open('references/toolgrounding/tool_state_schema.yaml'))"` 通过（若改过 YAML）
- [ ] 决策理由写进 commit message（`drift-fix: cdb_create_account drop vpc VpcId — not a real prereq`）
- [ ] 若为真实消费方依赖：跑 `python3 references/toolgrounding/_demo.py` 验证 StateTracker 行为不破

## 防复发

- 新增工具依赖时：**一次写两侧**（YAML + PY 同 PR），check 脚本会当场验证
- GCL Critic 见到 `spec_compliance` 降级时：直接引用本模板路径，不再要求 Generator 自行摸索
- `collect_mttr_samples.py --mode apply` 后对比 `aggregate_gcl_traces.py` 的 MTTR 表确认下降
