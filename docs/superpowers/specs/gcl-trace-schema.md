# GCL Trace Schema

> Trace JSON 文件路径: `audit-results/gcl-trace-YYYYMMDD-HHMMSS.json`

## 1. 现状 trace schema (v1)

GCL Loop 生成的实际 trace 格式，用于 `qcloud-*-ops` skill 场景。

### 顶层字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `skill` | string | 触发的 skill 名，如 `qcloud-well-architected-review` |
| `request` | string | 原始用户请求（已脱敏） |
| `rubric_version` | string | 评分 rubric 版本，默认 `v1` |
| `iterations[]` | array | 每个 iteration 的生成→批判记录 |
| `preflight_reflexion` | object | GCL Pre-flight reflexion 结果 |
| `final.status` | string | 最终状态：`PASS` / `MAX_ITER` / `ABORT` |
| `final.iter` | int | 达到最终状态时的 iteration 编号 |
| `final.output` | string | 最终输出摘要 |

### iterations[] 元素

| 字段 | 类型 | 描述 |
|------|------|------|
| `iter` | int | Iteration 编号，从 1 开始 |
| `generator.command` | string | 实际执行的 tccli / SDK 命令 |
| `generator.exit_code` | int | 进程退出码 |
| `generator.result_excerpt` | string | 结果片段（已截断） |
| `generator.op_type` | string | `read` / `write` / `delete` |
| `critic.scores` | object | 五维评分：`correctness`, `safety`, `idempotency`, `traceability`, `spec_compliance` |
| `critic.suggestions[]` | array | 改进建议列表 |
| `critic.blocking` | bool | 是否有 blocking 问题 |
| `decision` | string | 决策：`PASS` / `RETRY` / `ABORT` |

### 已知缺失字段

当前 trace 文件**不包含**以下字段，聚合器中标注为 `N/A`：

| 字段 | 用途 | 影响 |
|------|------|------|
| `started_at` / `finished_at` | Loop 总时长、MTTR 计算 | 无法计算真实 duration 和 MTTR |
| `files_changed` | 落盘文件数统计 | 无法统计每 trace 产出 |
| `commits` | 提交数统计 | 无法统计每 trace 提交 |
| `strategy` | 编排策略标签 | 无法按策略分类统计 |

> 如需精确 duration/MTTR，推荐在 GCL runner 层面增加 `started_at` / `finished_at` 字段。

## 2. Orchestrator trace schema (subagent-orchestrator)

另一类 trace 文件，由 subagent-orchestrator 生成，路径同 `gcl-trace-YYYYMMDD-HHMMSS.json`。

| 字段 | 类型 | 描述 |
|------|------|------|
| `task_id` | string | 任务唯一标识 |
| `ts` | string | ISO timestamp |
| `strategy` | string | 编排策略 |
| `complexity` | int | 复杂度评分 |
| `risk` | string | 风险等级 |
| `chosen_strategy` | string | 最终选择策略 |
| `concurrency` | int | 并发度 |
| `batch_size` | int | batch size |
| `agents[]` | array | subagent 列表 |
| `safety_gates[]` | array | 安全门列表 |
| `trace_path` | string | 关联的 trace 路径 |

**聚合器兼容策略**: orchestrator trace 无 `final.status`，在 PASS 率等指标中该文件不计入。

## 3. 聚合指标定义

| 指标 | 算法 | 数据来源 |
|------|------|----------|
| 累计 GCL Loop 数 | `len(traces)` | 全部 `gcl-trace-*.json` |
| 总 iteration 轮次 | `sum(len(t['iterations']))` | 全部 trace |
| 最终 PASS 数/率 | `count(final.status=='PASS')` | `final.status` |
| 最终 MAX_ITER 数/率 | `count(final.status=='MAX_ITER')` | `final.status` |
| 最终 ABORT 数/率 | `count(final.status=='ABORT')` | `final.status` |
| RETRY 触发率 | `count(decision=='RETRY') / total_iters` | `iterations[].decision` |
| BLOCKER 类型分布 | Counter of normalized suggestion tags | `iterations[].critic.suggestions` |
| MAJOR 类型分布 | Counter of normalized suggestion tags | `iterations[].critic.suggestions` |
| 平均每 trace 问题数 | `sum(blockers+majors) / n` | suggestion tagging |
| drift→fix 次数 | `count(PASS & len(iterations)>1)` | `final.status` + `iterations` |
| MTTR | N/A（缺 started_at/finished_at） | — |
| PASS 趋势 | `sorted(ts_map)[:20]` | 从文件名提取 timestamp |

### BLOCKER/MAJOR 判定算法

```
suggestion → lowercase
if any(keyword in suggestion for keyword in ["blocker","critical","safety","abort","fail"]):
    → BLOCKER
elif any(keyword in suggestion for keyword in ["major","error","drift","missing","invalid"]):
    → MAJOR
else:
    → 无分类
```

### 类型归一化（用于分布统计）

| 归一化 Tag | 触发关键词 |
|------------|-----------|
| `yaml_python_drift` | `yaml`, `drift`, `schema` |
| `spec_file_refs_missing` | `spec`, `file`, `ref`, `missing` |
| `auth_credential` | `auth`, `credential`, `secret` |
| `invalid_params` | `param`, `argument`, `flag` |
| `spec_compliance` | `rubric`, `compliance`, `spec_compliance` |
| `traceability` | `trace`, `audit`, `log` |
| `idempotency` | `idempot` |
| `error_handling` | `error`, `code` |
| `other` | 其余 |

## 4. 使用示例

```bash
# 聚合全部 trace
python3 scripts/aggregate_gcl_traces.py

# 指定目录
python3 scripts/aggregate_gcl_traces.py --dir /path/to/audit-results

# 自检模式（使用 fake traces 验证聚合逻辑）
python3 scripts/aggregate_gcl_traces.py --self-test

# CI 集成（只关心 exit code）
python3 scripts/aggregate_gcl_traces.py && echo "GCL stats OK"
```

## 5. Schema 演进建议

若需要精确 duration / MTTR / files_changed / commits，建议在 trace 层面新增字段：

```json
{
  "started_at": "2026-08-31T15:00:00+08:00",
  "finished_at": "2026-08-31T15:03:22+08:00",
  "duration_seconds": 202,
  "outcome": {
    "files_changed": 12,
    "commits": 3,
    "blocker_types": ["yaml_python_drift"]
  }
}
```

聚合器已预留字段兼容，新字段出现时自动纳入报告。
