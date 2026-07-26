# AIOps Cruise Enhancement — Design Spec

## 背景（Background）

`qcloud-aiops-diagnosis` 当前定位为"被动故障诊断引擎"（11个工作流 + 9类产品RCA规则），缺少主动巡检所需的：

1. **Topology-First 架构**：无显式拓扑发现阶段驱动分析优先级
2. **ML 异常检测**：动态基线仅为 z-score prose 描述，无独立模块
3. **容量预测**：无 OLS/XGBoost 容量预测能力
4. **跨轮次追踪**：无 Finding Fingerprint，无法对比 new/resolved/regressed
5. **Finding 过滤**：配置合规项混入异常处理环
6. **选择性执行**：全量 RCA 规则总是执行，不感知拓扑稀疏性
7. **巡检报告结构**：无拓扑路径骨架，以资源类型而非业务路径组织报告
8. **结构化反思**：无巡检后反思沉淀机制

**目标**：将 `qcloud-aiops-diagnosis` 从单一诊断引擎，升级为"主动巡检 + 被动诊断"双模 AIOps 能力中心，参考 `jdcloud-aiops-cruise` 的工程化优势，结合腾讯云产品 RCA 成熟度，形成更完整的智能巡检闭环。

## 架构（Architecture）

```
                    ┌─────────────────────────────────────┐
                    │      qcloud-aiops-diagnosis         │
                    │                                     │
                    │  Phase 0: Topology Discovery (NEW)  │
                    │    tccli cvm DescribeInstances       │
                    │    tccli clb DescribeLoadBalancers   │
                    │    tccli vpc DescribeVpcPeeringConnections │
                    │    → 拓扑图 + 节点优先级排序         │
                    │                                     │
                    │  Phase 1: Selective Analyzer         │
                    │    按拓扑稀疏性选择工作流            │
                    │    skip if no Redis found            │
                    │                                     │
                    │  Phase 2: ML Anomaly Detection       │
                    │    ml/detectors/                     │
                    │      IsolationForestDetector           │
                    │      ThresholdDetector                │
                    │    ml/predictors/                   │
                    │      LinearTrendPredictor             │
                    │      XGBoostCapacityPredictor        │
                    │                                     │
                    │  Phase 3: RCA + Capacity Forecast    │
                    │    输出 RCA Bundle (extended)         │
                    │    + capacity_forecast               │
                    │    + finding_fingerprint            │
                    │    + finding_type (anomaly/config)   │
                    │                                     │
                    │  Phase 4: Report + Diff              │
                    │    topology-aware report              │
                    │    cruise_diff: new/resolved/regressed│
                    │                                     │
                    │  Cruise Audit Logger (NEW)           │
                    │    lib/cruise_logger.py              │
                    │    结构化事件流 → audit-results/     │
                    │    供人诊断 + AI 训推数据分析        │
                    └─────────────────────────────────────┘
```

## 目录结构

```
qcloud-aiops-diagnosis/
  ml/                              # NEW — ML 模块（纯 Python，graceful degradation）
    __init__.py
    detectors/
      __init__.py
      base.py                      # BaseDetector ABC
      isolation_forest.py          # IsolationForestDetector
      threshold_based.py           # ThresholdDetector
    predictors/
      __init__.py
      base.py                      # BasePredictor ABC
      linear_trend.py              # LinearTrendPredictor
      xgboost_capacity.py          # XGBoostCapacityPredictor
  lib/                             # NEW — 共享库
    __init__.py
    topology_discovery.py          # 拓扑发现 + 优先级排序
    finding_fingerprint.py         # Finding 稳定指纹
    finding_filters.py             # 异常 vs 配置合规过滤
    selective_workflow.py          # 按拓扑稀疏性选择工作流
    cruise_diff.py                 # 跨轮次 new/resolved/regressed
    capacity_forecaster.py         # 线性容量预测
    cruise_logger.py               # 结构化审计日志（人读+AI训推）
  references/
    topology-discovery-workflow.md # NEW — Phase 0 工作流定义
    ml-anomaly-detection.md        # NEW — ML 检测模块使用说明
    capacity-forecast.md           # NEW — 容量预测说明
    finding-fingerprint.md         # NEW — 指纹机制说明
    cruise-report-format.md        # NEW — 拓扑路径报告格式
    anomaly-detection.md           # UPDATE — 增加 ML 集成说明
    output-schemas.md              # UPDATE — 增加 capacity_forecast/fingerprint/finding_type
    diagnostic-workflows.md        # UPDATE — 增加 Topology-First Router
  audit-results/
    cruise-diff/                   # 跨轮次 diff 输出目录
    baselines/                     # 动态基线持久化（.runtime/ 下）
```

## 新增文件详细规格

### 1. ml/detectors/base.py — BaseDetector ABC

```python
class BaseDetector(ABC):
    name: str = "BaseDetector"

    @abstractmethod
    def fit(self, data: list[float]) -> BaseDetector:
        """Train detector on historical values."""
        raise NotImplementedError

    @abstractmethod
    def detect(self, point: float) -> dict[str, Any]:
        """Detect anomaly for single point.

        Returns:
            {anomaly: bool, score: float, threshold: float, model: str}
        """
        raise NotImplementedError

    def detect_batch(self, points: list[float]) -> list[dict[str, Any]]:
        """Run detect() on list of points."""
        return [self.detect(p) for p in points]
```

### 2. ml/detectors/isolation_forest.py — IsolationForestDetector

- 依赖 `sklearn.ensemble.IsolationForest`，缺失时 fallback 到 z-score `ThresholdDetector`
- `__init__(contamination=0.05, n_estimators=100)`
- `fit(data)` → 训练IsolationForest
- `detect(point)` → `{"anomaly": bool, "score": float, "threshold": float, "model": "IsolationForestDetector"}`
- `detect_batch(points)` → 向量化 sklearn `score_samples()` 单次调用
- 无 sklearn 时返回 `{"anomaly": False, "score": 0.0, "threshold": 0.5, "model": "IsolationForestDetector", "degraded": True}`

### 3. ml/detectors/threshold_based.py — ThresholdDetector

- 无外部依赖
- `__init__(warning_threshold=float, critical_threshold=float, direction="upper")`
- `detect(point)` → `{"anomaly": bool, "level": "warning"|"critical"|"normal", "value": float, ...}`
- `direction="lower"` 支持错误率骤降等低值异常场景

### 4. ml/predictors/base.py — BasePredictor ABC

```python
class BasePredictor(ABC):
    name: str = "BasePredictor"

    @abstractmethod
    def fit(self, data: list[tuple[Any, float]]) -> BasePredictor:
        """Train on [(timestamp, value), ...] sorted ascending."""
        raise NotImplementedError

    @abstractmethod
    def predict(self, steps: int = 1) -> dict[str, Any]:
        """Forecast N steps ahead.

        Returns:
            {predictions: list, confidence: str, model: str,
             current_usage: float, days_to_full: float|None,
             growth_rate: float|None}
        """
        raise NotImplementedError
```

### 5. ml/predictors/linear_trend.py — LinearTrendPredictor

- 纯 Python OLS 线性回归，无外部依赖
- `__init__(max_points=24)`
- `fit(data)` → OLS 训练，取最近 max_points 个点
- `predict(steps=7)` → 返回每日预测值 + `days_to_full`（达到100%天数）+ `growth_rate`（日增长率pp）+ `confidence`（high≥12点/medium≥6点/low≥3点/insufficient_data<3点）

### 6. ml/predictors/xgboost_capacity.py — XGBoostCapacityPredictor

- 依赖 `xgboost`，缺失时 fallback 到 `LinearTrendPredictor`
- `__init__(max_depth=4, n_estimators=50, max_points=24)`
- `fit(data)` → XGBoost 回归训练
- `predict(steps=7)` → 同 `LinearTrendPredictor` 接口
- 无 xgboost 时返回 `LinearTrendPredictor` 的结果 + `"model": "XGBoostCapacityPredictor-fallback"`

### 7. lib/topology_discovery.py — 拓扑发现

```python
def discover_topology(region: str, time_window: str = "1h") -> dict:
    """Build topology graph for all products.

    Returns:
        {
          "vpcs": [...],
          "nodes": [
            {"type": "clb", "id": "...", "name": "...", "tier": "ingress",
             "priority": "highest", "upstream": [], "downstream": ["vm-1", "vm-2"]},
            {"type": "cvm", "id": "...", "tier": "app", "priority": "high",
             "upstream": ["clb-1"], "downstream": ["cdb-1", "redis-1"]},
            {"type": "cdb", "id": "...", "tier": "data", "priority": "highest",
             "upstream": ["vm-1"], "downstream": []},
            ...
          ],
          "priority_order": ["cdb-1", "clb-1", "vm-1", "vm-2"],
          "single_points": ["cdb-1"],  # 无冗余的数据节点
        }
    """
```

**节点分层优先级**：

| Tier | 类型 | Priority | 说明 |
|------|------|----------|------|
| `ingress` | EIP / CLB / NAT | **highest** | 所有流量必经之路 |
| `data` | CDB / Redis / MongoDB / ES | **highest** | 数据一致性风险 |
| `app` | CVM / Pod | **high** | 承压上游流量 |
| `egress` | NAT Gateway | **high** | 出网流量 |
| `edge` | 闲置 EIP | **low** | 仅费用风险 |

**单点风险识别**：CDB 无副本、CLB 单后端、NAT 无冗余链路 → 标记 `single_points`。

### 8. lib/finding_fingerprint.py — Finding 指纹

```python
# 稳定指纹 key = resource_id || || service || || normalized_message
# severity 不参与 key（warning→critical 变化算 regressed，不算新 key）
_MAX_MSG_LEN = 200

def fingerprint(finding: dict) -> str:
    rid = finding.get("resource_id") or finding.get("resource") or ""
    svc = finding.get("service", "")
    msg = _normalize_message(finding.get("message", "") or "")
    return f"{rid}||{svc}||{msg}"

def _normalize_message(msg: str) -> str:
    """Trim + collapse whitespace + truncate to 200 chars."""
    collapsed = re.sub(r'\s+', ' ', msg).strip()
    return collapsed[:_MAX_MSG_LEN]
```

### 9. lib/finding_filters.py — Finding 过滤

```python
# 配置合规 findings 排除在异常处理环之外
EXCLUDED_SUBSTRINGS = ("未加密",)

def is_excluded(finding: dict) -> bool:
    msg = finding.get("message", "") or ""
    return any(sub in msg for sub in EXCLUDED_SUBSTRINGS)

def filter_findings(findings: list[dict]) -> list[dict]:
    """Drop config-compliance findings."""
    return [f for f in findings if not is_excluded(f)]

def summarize(findings: list[dict]) -> dict:
    """{total, critical, warning, info, excluded}"""
    kept = filter_findings(findings)
    return {
        "total": len(kept),
        "critical": sum(1 for f in kept if f.get("severity") == "critical"),
        "warning": sum(1 for f in kept if f.get("severity") == "warning"),
        "info": sum(1 for f in kept if f.get("severity") == "info"),
        "excluded": len(findings) - len(kept),
    }
```

### 10. lib/selective_workflow.py — 选择性工作流

```python
# 工作流与拓扑 key 的映射
_WORKFLOW_RAW_KEYS = {
    "workflow_5_alarm_aggregation": "tke_alarms",
    "workflow_6_multi_source_rca": "cvm",        # 有 CVM 才需要多源 RCA
    "workflow_8_baseline_anomaly": None,          # 始终可选
    "workflow_9_product_rca": {
        "cdb": "cdb_instances",
        "redis": "redis_instances",
        "es": "es_instances",
        "cos": "cos_buckets",
        "ckafka": "ckafka_instances",
        "mongodb": "mongodb_instances",
        "postgres": "postgres_instances",
        "scf": "scf_functions",
        "cdn": "cdn_domains",
    },
}

def resolve_workflows(topology: dict) -> list[str]:
    """Return workflows to run based on topology presence."""
    # 无 TKE 告警 → skip workflow_5
    # 无 CVM → skip workflow_6
    # 有哪些产品 → 只跑对应 workflow_9 子规则
```

### 11. lib/cruise_diff.py — 跨轮次对比

```python
def diff(previous: list[dict], current: list[dict]) -> dict:
    """Compare two cruise runs.

    Returns:
        {
          "new": [...findings only in current],
          "resolved": [...findings only in previous],
          "regressed": [...same fingerprint but severity worse],
          "unchanged": [...same fingerprint + same severity],
          "summary": {"new": N, "resolved": N, "regressed": N}
        }
    """
    prev_fp = {fingerprint(f): f for f in previous}
    curr_fp = {fingerprint(f): f for f in current}

    # 比较逻辑...
```

### 12. lib/capacity_forecaster.py — 容量预测

```python
class CapacityForecaster:
    """Linear regression capacity forecaster.

    MIN_POINTS = 3, LOW_POINTS = 6, MED_POINTS = 12
    """

    def predict(self, data: list[tuple]) -> dict:
        """Returns {current_usage, days_to_full, confidence, growth_rate}."""
```

## 更新 output-schemas.md

RCA Bundle 新增字段：

```json
{
  "capacity_forecast": {
    "days_to_full": 42.1,
    "growth_rate": 1.05,
    "confidence": "high",
    "current_usage": 56.3,
    "model": "LinearTrendPredictor"
  },
  "finding_fingerprint": "ins-xxx||cdb||连接数使用率 82%",
  "finding_type": "anomaly",
  "finding_status": "new",
  "topology_context": {
    "tier": "data",
    "priority": "highest",
    "single_point": true,
    "upstream": ["vm-1"],
    "downstream": []
  }
}
```

## 更新 diagnostic-workflows.md

在 Workflow Router 之前增加 **Topology-First Router**：

```
IF topology not yet built → invoke topology_discovery → output topology graph
ELIF topology exists and {{user.intent}} matches "巡检" / "主动检查" / "全链路"
  → selective_workflow.resolve_workflows(topology) → run selected workflows
ELIF {{user.handoff_source}} == finops → Workflow 11
ELIF TKE alarm storm → Workflow 5
ELIF multi-source RCA → Workflow 6
...
```

## FinOps 容量利用率阈值（新增）

| 资源类型 | 判定条件 | Severity | Finding 消息 |
|---------|---------|----------|-------------|
| CVM | CPU均值<15% 且 内存均值<20%（6h） | info | FinOps降配信号：CPU平均X% |
| Redis | 内存均值<30%（6h） | info | FinOps降配信号：内存平均X% |
| CDB | CPU均值<20% 且 内存均值<30%（6h） | info | FinOps降配信号：CPU平均X% |
| CLB | 并发均值<规格上限×10%（6h） | info | FinOps降配信号：并发平均X |
| CVM | 带宽利用率<30%（6h均值） | info | FinOps降配信号：带宽平均X% |

**执行时机**：每个产品 RCA 规则的 `analyze()` 末尾调用 `_check_cost_efficiency()`，与其他 findings 一起输出。

## Self-Check / Self-Verification

```python
# ML 模块自验
from ml.detectors import IsolationForestDetector, ThresholdDetector
from ml.predictors import LinearTrendPredictor

# IsolationForest fallback
d = IsolationForestDetector()
d.fit([50.0]*50 + [95.0])   # 50 normal + 1 anomaly
result = d.detect(95.0)
assert result["anomaly"] is True
assert result["score"] > 0.5

# ThresholdDetector
d2 = ThresholdDetector(warning_threshold=70.0, critical_threshold=85.0)
assert d2.detect(82.5)["level"] == "warning"
assert d2.detect(90.0)["level"] == "critical"
assert d2.detect(50.0)["level"] == "normal"

# LinearTrendPredictor
p = LinearTrendPredictor(max_points=12)
p.fit([(0, 50.0), (1, 51.0), (2, 52.0)] * 4)  # 12 points, 1pp/day growth
forecast = p.predict(steps=7)
assert forecast["confidence"] == "high"
assert forecast["growth_rate"] is not None

# Finding fingerprint
from lib.finding_fingerprint import fingerprint
f1 = {"resource_id": "ins-xxx", "service": "cvm", "message": "CPU 95% Warning"}
f2 = {"resource_id": "ins-xxx", "service": "cvm", "message": "CPU 95% Warning"}
assert fingerprint(f1) == fingerprint(f2)   # 相同 finding 产生相同指纹
assert "||" in fingerprint(f1)              # 分隔符存在

# Finding filter
from lib.finding_filters import is_excluded, filter_findings
assert is_excluded({"message": "数据盘 未加密"}) is True
assert is_excluded({"message": "CPU 95%"}) is False

# Cruise diff
from lib.cruise_diff import diff
prev = [{"resource_id": "ins-1", "service": "cvm", "message": "CPU 95%", "severity": "warning"}]
curr = [{"resource_id": "ins-1", "service": "cvm", "message": "CPU 95%", "severity": "critical"}]
d = diff(prev, curr)
assert len(d["regressed"]) == 1
assert len(d["new"]) == 0
assert len(d["resolved"]) == 0

# Selective workflow
from lib.selective_workflow import resolve_workflows
topo_empty = {"cvm": [], "cdb_instances": []}
assert "workflow_5_alarm_aggregation" not in resolve_workflows(topo_empty)
```

## 13. 结构化审计日志 — lib/cruise_logger.py

### 13.1 目标

巡检全流程的结构化事件流，同时服务于：

1. **人读诊断**：清晰日记轨迹，覆盖每个 phase/step 的开始/完成/跳过/错误/决策
2. **AI 训推数据**：每个 `decision` 事件携带 (prior_events → chosen_option) 对，可用于微调巡检 Agent

### 13.2 设计原则

| 原则 | 说明 |
|------|------|
| 双路径输出 | 每个事件同时写入人类可读的 phase/step/event_type 和结构化 data 字段 |
| 零侵入集成 | `CruiseLogger` 作为独立工具注入各 phase，不需要修改业务逻辑 |
| 上下文完整 | 每个 `decision` 事件携带前 10 个历史事件作为 context |
| AI-first schema | event schema 与训练数据 schema 一一对应，无语义丢失 |

### 13.3 事件类型

| event_type | 触发时机 | 典型 data 字段 |
|---|---|---|
| `start` | phase/step 开始 | `{phase, context}` |
| `complete` | phase/step 成功结束 | `{result, summary}` |
| `skip` | 拓扑稀疏性跳过 | `{reason}` |
| `error` | 步骤失败（可恢复/不可恢复） | `{error, recoverable}` |
| `warning` | 非致命异常 | `{message, context}` |
| `metric` | 定量测量 | `{metric, value, tags}` |
| `finding` | 异常 finding 输出 | `{finding: {...}}` |
| `decision` | Agent 决策点 | `{decision, rationale, options, chosen}` |

### 13.4 数据模型

```python
class CruiseLogEvent:
    event_id: str          # UUIDv4
    timestamp: str         # ISO 8601 with timezone (UTC)
    cruise_id: str         # 本轮巡检唯一 ID
    phase: str             # Phase enum value
    step: str              # sub-step within phase
    event_type: str        # EventType enum value
    data: dict             # 事件类型相关 payload
    duration_ms: int|null  # 从 cruise_start 累计耗时
    error: str|null        # error event 时填入
    trace_id: str|null     # 关联事件链 ID
    model: str|null        # 使用的 LLM 模型（如有）
    tokens_used: int|null  # token 消耗（如有）
    metadata: dict         # 扩展字段

class Phase(str, Enum):
    TOPOLOGY_DISCOVERY = "topology_discovery"
    SELECTIVE_WORKFLOW = "selective_workflow"
    ML_DETECTION = "ml_detection"
    CAPACITY_FORECAST = "capacity_forecast"
    FINGERPRINT = "fingerprint"
    FINDING_FILTER = "finding_filter"
    REPORT = "report"
    CRUISE_DIFF = "cruise_diff"
```

### 13.5 输出格式

JSONL（`audit-results/cruise/{cruise_id}-{ts}.jsonl`）：

```
{header 行 — type: cruise_audit_header, version, cruise_id, event_count, total_duration_ms}
{每行一个事件 — 完整 CruiseLogEvent JSON}
{footer 行 — type: cruise_audit_footer, event_count, total_duration_ms 校验}
```

- `grep` / `jq` 友好
- 流式读取（无一次性全量加载）
- 每条事件独立可解析（AI 训练数据基础）

### 13.6 AI 训练对生成

```python
def to_training_pairs(self) -> list[dict]:
    """每个 decision 事件 → (context: {prior_events, current_event}, output: {decision, rationale, chosen})"""
    # context = cruise_id + region + 前10个历史事件 + 当前事件
    # output = {decision 名称, 决策理由, 最终选择}
```

### 13.7 Phase 集成点

| Phase | 注入位置 | 事件 |
|---|---|---|
| topology_discovery | `discover_topology()` | start/complete/skip/error/metric |
| selective_workflow | `resolve_workflows()` | decision (选择哪个 analyzer) |
| ML detection | 各 Detector | finding + decision |
| capacity_forecast | `CapacityForecaster` | metric + decision |
| finding_filter | `filter_findings()` | decision (过滤/保留) |
| report | 报告生成 | decision (报告结构) |

### 13.8 与 jdcloud-aiops-cruise 的差异

| 维度 | jdcloud-aiops-cruise | qcloud-aiops-diagnosis |
|---|---|---|
| 格式 | prose 日志 | 结构化 JSONL |
| AI 训推 | 无 | decision events → training pairs |
| 持久化 | 单次报告 | JSONL 文件 + 内存缓冲 |
| context 深度 | 无 | 每个 decision 携带前 10 个事件 |

## Layer Compliance

| 规则 | 合规 |
|------|------|
| Agent-Agnostic (P0) | YES — no `.codegraph/`/`.omc/`/`.codebuddy/` paths; pure stdlib + optional sklearn/xgboost |
| Token Efficiency (TE-1/3/4/5/6) | YES — no hardcoded tables; one-liner reports; YAML anchors; centralized JSON paths |
| Five Core Standards | YES — Phase 0 只读拓扑发现；诊断结论不变；新增 capacity_forecast 嵌入 RCA Bundle |
| Subagent concurrency (P0) | YES — max 3 concurrent subagents per AGENTS.md |
| Commit hygiene Hard stops | None — all new files, no credentials, no destructive ops |
| 2-round self-review | MANDATORY — Round 1 (template/standards) + Round 2 (adversarial) |
