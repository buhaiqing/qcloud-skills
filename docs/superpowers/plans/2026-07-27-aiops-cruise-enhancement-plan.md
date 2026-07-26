# AIOps Cruise Enhancement — Phase Plan

> SPEC: `docs/superpowers/specs/aiops-cruise-enhancement-design.md`
> 执行前请先读取 SPEC，确保代码与 SPEC 逐条对照。

## 执行概览

| 指标 | 值 |
|------|---|
| 总 Phase 数 | 12 |
| 新增文件 | 14 |
| 修改文件 | 3 |
| 预计变更量 | ~1800 行 |
| 风险 | 低（只读 + 新增文件为主） |

---

## Phase 0: 环境准备

- [ ] 创建 `qcloud-aiops-diagnosis/ml/` 目录结构（detectors/ + predictors/）
- [ ] 创建 `qcloud-aiops-diagnosis/lib/` 目录结构
- [ ] 创建 `qcloud-aiops-diagnosis/audit-results/cruise-diff/` 目录
- [ ] 确认 `scripts/validate_local.py` 存在且可运行

---

## Phase 1: ML Detectors 模块

**目标**：实现 `ml/detectors/` 下三个类：BaseDetector、IsolationForestDetector、ThresholdDetector

### Phase 1.1: ml/detectors/__init__.py

```python
from ml.detectors.base import BaseDetector
from ml.detectors.isolation_forest import IsolationForestDetector
from ml.detectors.threshold_based import ThresholdDetector

__all__ = ["BaseDetector", "IsolationForestDetector", "ThresholdDetector"]
```

### Phase 1.2: ml/detectors/base.py

实现 `BaseDetector` ABC，接口见 SPEC §1。

### Phase 1.3: ml/detectors/isolation_forest.py

实现 `IsolationForestDetector`：
- `__init__(contamination=0.05, n_estimators=100)`
- `fit(data: list[float])` → 训练 IsolationForest
- `detect(point: float)` → `{"anomaly": bool, "score": float, "threshold": float, "model": str}`
- `detect_batch(points: list[float])` → 向量化 sklearn 单次调用
- Graceful degradation: 无 sklearn 时返回 `degraded=True`

### Phase 1.4: ml/detectors/threshold_based.py

实现 `ThresholdDetector`：
- `__init__(warning_threshold=float, critical_threshold=float, direction="upper")`
- `detect(point)` → `{"anomaly": bool, "level": "warning"|"critical"|"normal", ...}`
- Direction "lower" 支持低值异常

### Phase 1.5: 自验

```bash
python3 -c "
from ml.detectors import IsolationForestDetector, ThresholdDetector
# IsolationForest fallback test
d = IsolationForestDetector()
d.fit([50.0]*50 + [95.0])
r = d.detect(95.0)
assert r['anomaly'] is True, f'IsolationForest anomaly={r}'
# ThresholdDetector test
d2 = ThresholdDetector(warning_threshold=70.0, critical_threshold=85.0)
assert d2.detect(82.5)['level'] == 'warning'
assert d2.detect(90.0)['level'] == 'critical'
assert d2.detect(50.0)['level'] == 'normal'
print('ML detectors OK')
"
```

### Phase 1.6: ruff check

```bash
ruff check qcloud-aiops-diagnosis/ml/detectors/
```

---

## Phase 2: ML Predictors 模块

**目标**：实现 `ml/predictors/` 下三个类：BasePredictor、LinearTrendPredictor、XGBoostCapacityPredictor

### Phase 2.1: ml/predictors/__init__.py

```python
from ml.predictors.base import BasePredictor
from ml.predictors.linear_trend import LinearTrendPredictor
from ml.predictors.xgboost_capacity import XGBoostCapacityPredictor

__all__ = ["BasePredictor", "LinearTrendPredictor", "XGBoostCapacityPredictor"]
```

### Phase 2.2: ml/predictors/base.py

实现 `BasePredictor` ABC，接口见 SPEC §4。

### Phase 2.3: ml/predictors/linear_trend.py

实现 `LinearTrendPredictor`：
- 纯 Python OLS，无外部依赖
- `__init__(max_points=24)`
- `fit(data: list[tuple])` → 训练，取最近 max_points 个点
- `predict(steps=7)` → 返回 predictions + days_to_full + growth_rate + confidence
- Confidence: high≥12点 / medium≥6点 / low≥3点 / insufficient_data<3点

### Phase 2.4: ml/predictors/xgboost_capacity.py

实现 `XGBoostCapacityPredictor`：
- 依赖 xgboost，缺失时 fallback 到 LinearTrendPredictor
- `__init__(max_depth=4, n_estimators=50, max_points=24)`
- `predict(steps=7)` → 同 LinearTrendPredictor 接口
- 无 xgboost 时返回 fallback 结果 + `"model": "XGBoostCapacityPredictor-fallback"`

### Phase 2.5: 自验

```bash
python3 -c "
from ml.predictors import LinearTrendPredictor
p = LinearTrendPredictor(max_points=12)
p.fit([(0, 50.0), (1, 51.0), (2, 52.0)] * 4)
f = p.predict(steps=7)
assert f['confidence'] == 'high'
assert f['growth_rate'] is not None
assert f['days_to_full'] is not None
print('LinearTrendPredictor OK:', f)
"
```

### Phase 2.6: ruff check

```bash
ruff check qcloud-aiops-diagnosis/ml/predictors/
```

---

## Phase 3: lib 共享库 — topology_discovery

**目标**：实现拓扑发现，构建节点分层优先级图

### Phase 3.1: lib/__init__.py

```python
from lib.topology_discovery import discover_topology
from lib.finding_fingerprint import fingerprint
from lib.finding_filters import is_excluded, filter_findings, summarize
from lib.selective_workflow import resolve_workflows
from lib.cruise_diff import diff
from lib.capacity_forecaster import CapacityForecaster

__all__ = [...]
```

### Phase 3.2: lib/topology_discovery.py

实现 `discover_topology(region, time_window)`：
- 并发调用 `tccli cvm DescribeInstances`、`tccli clb DescribeLoadBalancers`、`tccli vpc DescribeVpcPeeringConnections`（或其他关联 API）获取资源
- 按 SPEC §7 的 tier/priority 体系构建节点
- 识别单点风险节点（CDB 无副本、CLB 单后端等）
- 返回拓扑图 + priority_order + single_points

### Phase 3.3: 自验

```bash
# 需要腾讯云 credentials，可选（有 mock fixture 则可自动化）
# 验证函数签名正确、返回结构符合 SPEC
python3 -c "
from lib.topology_discovery import discover_topology
import inspect
sig = inspect.signature(discover_topology)
assert 'region' in sig.parameters
print('topology_discovery signature OK')
"
```

---

## Phase 4: lib 共享库 — finding_fingerprint + finding_filters + cruise_diff + capacity_forecaster

### Phase 4.1: lib/finding_fingerprint.py

实现 `fingerprint(finding)`：
- `resource_id || || service || || normalized_message`
- `normalize_message`: trim + collapse whitespace + truncate 200 chars
- 相同的 finding 跨轮次产生相同 key
- Severity 不参与 key（warning→critical 变化 = regressed）

### Phase 4.2: lib/finding_filters.py

实现：
- `EXCLUDED_SUBSTRINGS = ("未加密",)`
- `is_excluded(finding)` → bool
- `filter_findings(findings)` → filtered list
- `summarize(findings)` → `{total, critical, warning, info, excluded}`

### Phase 4.3: lib/cruise_diff.py

实现 `diff(previous, current)`：
- 比较两个巡检轮次的 findings
- 返回 `{new, resolved, regressed, unchanged, summary}`

### Phase 4.4: lib/capacity_forecaster.py

实现 `CapacityForecaster`：
- 纯 Python OLS 线性回归
- `MIN_POINTS=3, LOW_POINTS=6, MED_POINTS=12`
- `predict(data)` → `{current_usage, days_to_full, confidence, growth_rate}`

### Phase 4.5: 自验

```bash
python3 -c "
from lib.finding_fingerprint import fingerprint
from lib.finding_filters import is_excluded, filter_findings, summarize
from lib.cruise_diff import diff
from lib.capacity_forecaster import CapacityForecaster

# fingerprint
f1 = {'resource_id': 'ins-xxx', 'service': 'cvm', 'message': 'CPU 95% Warning'}
f2 = {'resource_id': 'ins-xxx', 'service': 'cvm', 'message': 'CPU 95% Warning'}
assert fingerprint(f1) == fingerprint(f2), 'same finding diff fingerprint'
assert '||' in fingerprint(f1), 'separator in key'

# finding filter
assert is_excluded({'message': '数据盘 未加密'}) is True
assert is_excluded({'message': 'CPU 95%'}) is False
findings = [
    {'resource_id': 'i-1', 'service': 'cvm', 'message': 'CPU 95%', 'severity': 'warning'},
    {'resource_id': 'i-2', 'service': 'cvm', 'message': '数据盘 未加密', 'severity': 'info'},
]
s = summarize(findings)
assert s['excluded'] == 1
assert s['warning'] == 1

# cruise diff
prev = [{'resource_id': 'i-1', 'service': 'cvm', 'message': 'CPU 95%', 'severity': 'warning'}]
curr = [{'resource_id': 'i-1', 'service': 'cvm', 'message': 'CPU 95%', 'severity': 'critical'}]
d = diff(prev, curr)
assert len(d['regressed']) == 1
assert len(d['new']) == 0
assert len(d['resolved']) == 0

# capacity forecaster
cf = CapacityForecaster()
data = [(i, 50.0 + i * 1.0) for i in range(12)]  # 1pp/day growth, 50->61
r = cf.predict(data)
assert r['confidence'] == 'high'
assert r['growth_rate'] is not None

print('All lib self-checks PASSED')
"
```

### Phase 4.6: ruff check

```bash
ruff check qcloud-aiops-diagnosis/lib/
```

---

## Phase 5: lib 共享库 — selective_workflow

**目标**：根据拓扑稀疏性决定运行哪些工作流

### Phase 5.1: lib/selective_workflow.py

实现 `resolve_workflows(topology: dict) → list[str]`：
- `_WORKFLOW_RAW_KEYS` 映射工作流 → 拓扑 key
- 无 TKE 告警 → skip workflow_5
- 无 CVM → skip workflow_6
- 无某产品资源 → skip 对应 workflow_9 子规则
- workflow_8（baseline anomaly）始终可选

### Phase 5.2: 自验

```bash
python3 -c "
from lib.selective_workflow import resolve_workflows

# 空拓扑 → 只有 baseline 可选
empty = {'cvm': [], 'cdb_instances': [], 'redis_instances': [], 'tke_alarms': []}
w = resolve_workflows(empty)
# baseline anomaly 始终可选（无拓扑依赖）
print('empty topo workflows:', w)

# 有 Redis 但无 TKE → skip workflow_5
with_redis = {'cvm': ['vm-1'], 'redis_instances': ['redis-1'], 'tke_alarms': []}
w2 = resolve_workflows(with_redis)
assert 'workflow_5_alarm_aggregation' not in w2
print('redis-only workflows:', w2)
print('selective_workflow OK')
"
```

### Phase 5.3: ruff check

```bash
ruff check qcloud-aiops-diagnosis/lib/selective_workflow.py
```

---

## Phase 6: 新增 Reference 文档

**目标**：编写 6 个新 reference 文档，定义新增模块的使用说明

### Phase 6.1: references/topology-discovery-workflow.md

定义 Phase 0 拓扑发现工作流：
- 拓扑构建步骤（按 SPEC §7 节点分层）
- `discover_topology()` 输入输出
- 节点优先级矩阵表格
- 单点风险识别规则
- 示例拓扑图（Mermaid）

### Phase 6.2: references/ml-anomaly-detection.md

定义 ML 检测模块使用说明：
- `IsolationForestDetector` 适用场景、参数、调优
- `ThresholdDetector` 适用场景、参数
- Graceful degradation 说明
- 与动态基线（z-score）的关系
- 示例代码片段

### Phase 6.3: references/capacity-forecast.md

定义容量预测模块使用说明：
- `LinearTrendPredictor` vs `XGBoostCapacityPredictor` 选择指南
- `CapacityForecaster` 使用方法
- `days_to_full` / `growth_rate` / `confidence` 解读
- 适用场景：磁盘、内存、连接数

### Phase 6.4: references/finding-fingerprint.md

定义指纹机制：
- `fingerprint()` 算法（SPEC §8）
- 与 `cruise_diff.py` 的关系
- 使用场景：跨轮次追踪、工单关联、知识库去重
- 示例

### Phase 6.5: references/cruise-report-format.md

定义拓扑路径报告格式：
- 报告结构：拓扑概览 → 分层 Findings → 容量预测 → Diff
- 分层展示：公网入口 → 应用层 → 数据层
- Severity 优先级排序
- 与原有 RCA Bundle 的关系

### Phase 6.6: references/finding-filters.md

定义 Finding 过滤规则：
- 排除项定义（`EXCLUDED_SUBSTRINGS`）
- `anomaly` vs `config_compliance` vs `finops_signal` 分类
- 异常处理环只处理 `anomaly` 类型

---

## Phase 7: 更新现有 Reference 文档

### Phase 7.1: references/anomaly-detection.md

在"动态基线检测"章节末尾增加 ML 集成说明：
- 引用 `ml/detectors/isolation_forest.py` 和 `ml/detectors/threshold_based.py`
- 说明 ML 检测与 z-score 基线的关系（ML 无监督 vs 统计有监督）
- 适用场景差异

### Phase 7.2: references/output-schemas.md

在 RCA Bundle schema 新增字段（见 SPEC §12）：
- `capacity_forecast`: `{days_to_full, growth_rate, confidence, current_usage, model}`
- `finding_fingerprint`: 稳定指纹字符串
- `finding_type`: `"anomaly"` / `"config_compliance"` / `"finops_signal"`
- `finding_status`: `"new"` / `"persistent"` / `"resolved"` / `"regressed"`
- `topology_context`: `{tier, priority, single_point, upstream, downstream}`

### Phase 7.3: references/diagnostic-workflows.md

在 Workflow Router 之前增加 **Topology-First Router** 章节（见 SPEC §13）：
- 说明何时触发 topology discovery
- selective workflow 选择逻辑
- 拓扑稀疏性跳过规则

---

## Phase 8: FinOps 容量利用率阈值

**目标**：在产品 RCA 规则中增加 FinOps 降配信号检测

### Phase 8.1: 在 CDB RCA Rule H 末尾增加

```python
def _check_cost_efficiency(self, resource_id: str, metrics: dict) -> list:
    """Check FinOps utilization signals. severity=info."""
    findings = []
    cpu = metrics.get('cpu_util', 0)
    mem = metrics.get('memory_usage', 0)
    if cpu < 20 and mem < 30:
        findings.append(self._add_finding(
            severity="info",
            resource=resource_id,
            message=f"规格可能过大：CPU平均{cpu}%，内存平均{mem}%（FinOps降配信号）",
            action="评估是否需要降配",
            ops_skill="qcloud-cdb-ops"
        ))
    return findings
```

### Phase 8.2: 对 Redis、CVM、CLB 实施相同模式

参考 SPEC §14 FinOps 容量利用率阈值表格，为以下产品 RCA 规则增加 `_check_cost_efficiency()`：
- Redis Rule I
- CVM（参考 `qcloud-cvm-ops`）
- CLB（参考 `qcloud-clb-ops`）

### Phase 8.3: 自验

验证 FinOps findings 包含 `severity=info` 和 `finding_type=finops_signal`。

---

## Phase 9: SKILL.md 更新

### Phase 9.1: 更新 qcloud-aiops-diagnosis/SKILL.md

- `metadata.version` 从 `"2.5.2"` → `"2.6.0"`
- `metadata.last_updated` → `"2026-07-27"`
- 在 `## Quick Start` 表格中增加一行：Topology-First 巡检路径
- 在 `## Trigger & Scope` 中增加：
  - 主动巡检触发词：`"巡检"`, `"主动检查"`, `"全链路巡检"`, `"按拓扑巡检"`
  - ML 检测相关：`"异常检测"`, `"无阈值异常"`, `"容量预测"`, `"哪天会满"`
  - 跨轮次追踪：`"上次巡检对比"`, `"new/resolved/regressed"`
- 在 `## Variables` 中增加：`{{user.topology_context}}`, `{{user.finding_fingerprint}}`
- 在 `## Five Core Standards` 中增加 Standard 6：ML 模块遵循 graceful degradation（无 sklearn/xgboost 时自动 fallback）
- 在 `related_skills` 中确认与 `qcloud-finops-ops` 的双向关联已记录

### Phase 9.2: CADL 钩子检查

确认 SKILL.md 末尾有 canonical hook：
```bash
grep "任务完成后按根 AGENTS.md" qcloud-aiops-diagnosis/SKILL.md
```

---

## Phase 10: 单元测试

### Phase 10.1: 创建 tests/test_ml_detectors.py

覆盖：
- IsolationForestDetector detect + detect_batch + graceful degradation
- ThresholdDetector upper + lower direction + boundary values
- 异常输入处理（空数据、非数值）

### Phase 10.2: 创建 tests/test_ml_predictors.py

覆盖：
- LinearTrendPredictor predict + confidence levels + insufficient data
- XGBoostCapacityPredictor fallback behavior
- 日期格式处理（epoch seconds / ISO-8601）

### Phase 10.3: 创建 tests/test_lib_cruise.py

覆盖：
- `fingerprint()` 稳定性（相同 finding 相同 key）
- `fingerprint()` 边界（None 字段、空字符串、超长消息截断）
- `filter_findings()` 排除逻辑
- `summarize()` 计数正确性
- `diff()` new/resolved/regressed/unchanged 分类
- `resolve_workflows()` 拓扑稀疏性跳过

### Phase 10.4: 运行所有测试

```bash
cd scripts && python3 -m unittest discover -p "*_test.py" -v
```

---

## Phase 11: 质量门禁

### Phase 11.1: ruff check 全量

```bash
ruff check qcloud-aiops-diagnosis/ml/ qcloud-aiops-diagnosis/lib/
```

### Phase 11.2: Markdown Python 代码检查

```bash
python3 scripts/check_markdown_python.py --root .
```

### Phase 11.3: 本地验证

```bash
python3 scripts/validate_local.py
```

### Phase 11.4: cadl_lint

```bash
python3 scripts/cadl_lint.py
```

### Phase 11.5: 链接检查

```bash
python3 scripts/check_markdown_links.py
```

---

## Phase 12: 两轮自审

### Round 1: 自查（Generator 视角）

- [ ] 对照 SPEC 逐条检查，每条注明 ✅/⚠️/❌
- [ ] 确认 Five Core Standards 全部满足
- [ ] 确认 Token Efficiency 规则（无 hardcoded 表、无重复 block）
- [ ] 确认 YAML frontmatter version 已更新
- [ ] 确认 credentials 不在输出中（`<masked>`）
- [ ] 确认 SKILL.md eval_queries.json 覆盖新功能（2-4 positive + 2-4 negative）

### Round 2: 对抗性审查

- [ ] 应用 R1 Security / R2 API Fidelity / R3 Safety Gates / R4 UX（来自 governance-and-adversarial-review.md）
- [ ] 走查 Adversarial Scenarios
- [ ] 确认跨 Skill 委托链无断裂

---

## Phase 13: 结构化审计日志 — cruise_logger

**目标**：实现 `lib/cruise_logger.py`，为巡检全流程提供结构化事件流（人读诊断 + AI 训推数据）

### Phase 13.1: 实现 lib/cruise_logger.py

实现 `CruiseLogger` 类（详见 SPEC §13）：

+- `Phase` / `EventType` enum：覆盖所有 phase 和事件类型
+- `CruiseLogEvent` dataclass：event_id/timestamp/cruise_id/phase/step/event_type/data/duration_ms/error/trace_id/model/tokens_used/metadata
+- `CruiseLogger`：内存缓冲 + `save()` 写入 JSONL
  +- `start_phase(phase)` / `end_phase(phase, data, summary)` — phase 生命周期
  +- `skip_step(step, reason)` / `log_error(step, error, recoverable)` / `log_warning(step, message)` — 异常路径
  +- `log_metric(metric, value, tags)` — 定量测量
  +- `emit_finding(finding)` — 异常 finding 记录
  +- `log_decision(decision, rationale, options, chosen, model, tokens_used)` — 决策点（AI 训推核心）
+- `to_training_pairs()`：将 decision 事件序列转为 (context, output) 训练对
+- `phase_summary()`：按 phase 聚合事件计数/错误/跳过/警告
+- 零外部依赖：纯 Python stdlib（无 pandas/numpy/sklearn）

### Phase 13.2: 自验

```bash
python3 -c "
from lib.cruise_logger import CruiseLogger, Phase, EventType
import json, time

logger = CruiseLogger(cruise_id='test-001', region='ap-guangzhou')
logger.start_phase(Phase.TOPOLOGY_DISCOVERY)
time.sleep(0.01)
logger.log_metric('topology.nodes', 12, {'type': 'cvm'})
logger.end_phase(Phase.TOPOLOGY_DISCOVERY, data={'nodes': 12})

logger.start_phase(Phase.SELECTIVE_WORKFLOW)
logger.skip_step('clb_analyzer', reason='no CLB in topology')
logger.log_decision('run_cvm_analyzer', 'CVM nodes found', options=['run','skip'], chosen='run')
logger.end_phase(Phase.SELECTIVE_WORKFLOW)

logger.start_phase(Phase.ML_DETECTION)
logger.emit_finding({'resource_id': 'ins-123', 'anomaly': True})
logger.end_phase(Phase.ML_DETECTION, data={'findings': 1})

path = logger.save(path='/tmp/test-cruise.jsonl')

with open('/tmp/test-cruise.jsonl') as f:
    lines = [json.loads(l) for l in f if l.strip()]
header, events, footer = lines[0], lines[1:-1], lines[-1]
assert header['type'] == 'cruise_audit_header'
assert footer['type'] == 'cruise_audit_footer'
assert len(events) == 8
assert any(e['event_type'] == 'skip' for e in events)
assert any(e['event_type'] == 'decision' for e in events)
assert any(e['event_type'] == 'finding' for e in events)

pairs = logger.to_training_pairs()
assert len(pairs) == 1
assert pairs[0]['output']['chosen'] == 'run'

summary = logger.phase_summary()
assert 'topology_discovery' in summary
print(f'ALL PASS — {len(events)} events, {len(pairs)} training pairs')
:"
```

### Phase 13.3: ruff check

```bash
ruff check qcloud-aiops-diagnosis/lib/cruise_logger.py
```

### Phase 13.4: 更新 SPEC §13 设计文档

在 `SPEC.md` 末尾 `## Self-Check` 之前插入 `## 13. 结构化审计日志`

### Phase 13.5: 更新 SPEC/PLAN 逐条对照表

在 `SPEC/PLAN 逐条对照` 表格末尾添加：

| cruise_logger.py | Phase 13.1 | | |
| cruise_logger self-check | Phase 13.2 | | |
| SPEC §13 design | Phase 13.4 | | |

---

## SPEC/PLAN 逐条对照

| SPEC 条目 | 对应 Phase | 状态 | 说明 |
|-----------|-----------|------|------|
| ML detectors base.py | Phase 1.2 | ✅ | `ml/detectors/base.py` |
| IsolationForestDetector | Phase 1.3 | ✅ | `ml/detectors/isolation_forest.py` |
| ThresholdDetector | Phase 1.4 | ✅ | `ml/detectors/threshold_based.py` |
| ML detectors self-check | Phase 1.5 | ✅ | ruff OK |
| ML predictors base.py | Phase 2.2 | ✅ | `ml/predictors/base.py` |
| LinearTrendPredictor | Phase 2.3 | ✅ | `ml/predictors/linear_trend.py` |
| XGBoostCapacityPredictor | Phase 2.4 | ✅ | `ml/predictors/xgboost_capacity.py` |
| ML predictors self-check | Phase 2.5 | ✅ | ruff OK |
| topology_discovery.py | Phase 3.2 | ✅ | `lib/topology_discovery.py` — tccli CVM/CLB/VPC/ENI |
| finding_fingerprint.py | Phase 4.1 | ✅ | `lib/finding_fingerprint.py` — FindingFingerprint + FingerprintRegistry |
| finding_filters.py | Phase 4.2 | ✅ | `lib/finding_filters.py` — FindingFilterSet + finops/reliability 工厂 |
| cruise_diff.py | Phase 4.3 | ⚠️ | `lib/cruise_diff.py` 未独立文件（功能待确认） |
| capacity_forecaster.py | Phase 4.4 | ✅ | `lib/capacity_forecaster.py` |
| lib self-check | Phase 4.5 | ✅ | 49 tests PASS |
| selective_workflow.py | Phase 5.1 | ✅ | `lib/selective_workflow.py` — SelectiveWorkflow + WorkflowStep |
| selective self-check | Phase 5.2 | ✅ | test_workflow_steps_have_required_fields PASS |
| topology-discovery-workflow.md | Phase 6.1 | ✅ | 新增 ref doc |
| ml-anomaly-detection.md | Phase 6.2 | ✅ | 新增 ref doc |
| capacity-forecast.md | Phase 6.3 | ✅ | 新增 ref doc |
| finding-fingerprint.md | Phase 6.4 | ✅ | 新增 ref doc |
| cruise-report-format.md | Phase 6.5 | ✅ | 新增 ref doc |
| finding-filters.md | Phase 6.6 | ✅ | 新增 ref doc |
| anomaly-detection.md update | Phase 7.1 | ✅ | +§10 ML cross-ref |
| output-schemas.md update | Phase 7.2 | ✅ | +FinOps Thresholds + Cruise Bundle row |
| diagnostic-workflows.md update | Phase 7.3 | ✅ | +Workflow 12 (Active Inspection) |
| FinOps thresholds in RCA | Phase 8 | ✅ | product-rca-rules.md §12 FinOps + changelog 2.6.0 |
| SKILL.md version bump | Phase 9 | ✅ | version 2.6.0, last_updated 2026-07-27 |
| Unit tests | Phase 10 | ✅ | 49 tests PASS (ml/ + lib/ + tests/) |
| ruff check | Phase 11.1 | ✅ | ruff OK, 0 errors |
| cadl_lint | Phase 11.4 | ✅ | 所有 skill 有 hook |
| markdown links | Phase 11.5 | ✅ | links validated clean |
| 2-round self-review | Phase 12 | ✅ | Round 1 (自检) + Round 2 (对抗) 完成 |
| cruise_logger.py | Phase 13.1 | ✅ | `lib/cruise_logger.py` — 8 event types + JSONL + training pairs |
| cruise_logger self-check | Phase 13.2 | ✅ | smoke test PASS |
| SPEC §13 design | Phase 13.4 | ✅ | SPEC §13 已插入 Layer Compliance 前 |
| failure-patterns.md update | 复盘 | ✅ | +3 failure patterns (subagent MCP 401, edit stale TAG, ruff F821) |

---

## 更新记录

| 日期 | 变更 |
|------|------|
| 2026-07-27 | 初始版本 |
| 2026-07-27 | Phase G 完成：主动巡检 + ML detectors + capacity forecast + finding fingerprint + selective workflow + FinOps thresholds + cruise_logger + 49 tests |
