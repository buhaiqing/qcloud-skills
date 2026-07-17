# P1-E: 分布漂移检测 — 设计文档

## 背景

当前轨迹分析只能告诉你"当前窗口内"的质量如何，但无法回答：
- **"最近 7 天 vs 过去 30 天，指标有没有变化？"**
- **"这个 skill 是本来通过率就低，还是最近突然变差了？"**
- **"这次优化改版之后，质量有没有改善？"**

分布漂移检测通过对比两个时间窗口，自动发现指标的变化方向。

---

## 核心概念

### 时间窗口

| 窗口 | 用途 |
|------|------|
| `recent_window` | 最近 7 天数据（当前状态） |
| `baseline_window` | 过去 8-30 天数据（历史基线） |

### 漂移信号

```
drift = recent_mean - baseline_mean
drift_ratio = drift / baseline_stdev  (if stdev > 0)
```

| drift_ratio | 方向 | 含义 |
|-------------|------|------|
| > +1.0σ | ↑ 改善 | 通过率上升 / 安全分上升 / 收敛速度变快 |
| < -1.0σ | ↓ 恶化 | 通过率下降 / 安全分下降 |
| \|drift_ratio\| ≤ 1.0σ | → 稳定 | 指标无显著变化 |

---

## 算法设计

### 核心函数

```python
def compute_drift(
    recent_traces: list[dict],
    baseline_traces: list[dict],
) -> dict[str, Any]:
    """Compare recent vs baseline to detect distribution drift.
    
    Returns:
        {
            "pass_rate": {"recent": 0.6, "baseline": 0.85, "drift": -0.25, "drift_sigma": -2.1, "direction": "↓"},
            "convergence_speed": {...},
            "safety_score": {...},
            "per_skill": {
                "qcloud-cos-ops": {
                    "pass_rate": {"recent": 0.4, "baseline": 0.85, "drift": -0.45, "drift_sigma": -3.0, "direction": "↓"},
                }
            },
            "alerts": [{"metric": "qcloud-cos-ops/pass_rate", "direction": "↓", "severity": "high"}]
        }
    """
```

### 检测逻辑

1. **per-metric 聚合**：对每个指标，计算 recent_mean 和 baseline_mean / baseline_stdev
2. **per-skill 分解**：对每个 skill 分别计算，防止被全局平均掩盖
3. **per-dimension 分解**：correctness / safety / spec_compliance 等维度单独看
4. **告警规则**：
   - drift_sigma < -1.5 → 严重恶化，severity=high
   - drift_sigma < -1.0 → 轻度恶化，severity=medium
   - drift_sigma > +1.0 → 改善，severity=low（信息）

### 简化 KS 检验

不引入 scipy dependency，用**滑动分桶**做简化：

```python
def simplified_ks_test(recent: list[float], baseline: list[float]) -> float:
    """Simplified Kolmogorov-Smirnov: max |CDF diff| across buckets."""
    if len(recent) < 2 or len(baseline) < 2:
        return 0.0
    # 10 equal-width buckets
    all_vals = recent + baseline
    lo, hi = min(all_vals), max(all_vals)
    if hi == lo:
        return 0.0
    buckets = [lo + (hi - lo) * i / 10 for i in range(11)]
    ks_stat = 0.0
    for b in buckets:
        cdf_recent = sum(1 for v in recent if v <= b) / len(recent)
        cdf_baseline = sum(1 for v in baseline if v <= b) / len(baseline)
        ks_stat = max(ks_stat, abs(cdf_recent - cdf_baseline))
    return round(ks_stat, 4)
```

**KS > 0.3** → 分布有显著差异（告警）

---

## 输出设计

### 控制台输出

```
=== 分布漂移检测 (recent=7d vs baseline=8-30d) ===

⚠  qcloud-cos-ops/pass_rate:   recent=40%  baseline=85%  ↓-45%  ⚠ high
⚠  qcloud-cos-ops/safety:      recent=70%  baseline=92%  ↓-22%  ⚠ medium
→  qcloud-cvm-ops/pass_rate:   recent=92%  baseline=88%  ↑+4%    stable
→  global/pass_rate:           recent=82%  baseline=79%  ↑+3%    stable

最近7天通过率趋势: 82% (baseline=79%, 无显著变化)
```

### JSON 输出

```json
{
  "generated_at": "2025-07-17T12:00:00Z",
  "windows": {"recent": "7d", "baseline": "8-30d"},
  "metrics": {
    "global": {
      "pass_rate": {"recent": 0.82, "baseline": 0.79, "drift": 0.03, "drift_sigma": 0.5, "direction": "→", "ks_stat": 0.05},
      "convergence_speed": {"recent": 0.88, "baseline": 0.85, "drift": 0.03, "drift_sigma": 0.6, "direction": "→"}
    }
  },
  "per_skill": {
    "qcloud-cos-ops": {
      "pass_rate": {"recent": 0.4, "baseline": 0.85, "drift": -0.45, "drift_sigma": -3.0, "direction": "↓", "severity": "high"}
    }
  },
  "alerts": [
    {"metric": "qcloud-cos-ops/pass_rate", "direction": "↓", "drift": -0.45, "drift_sigma": -3.0, "severity": "high"}
  ]
}
```

---

## 与现有代码集成

**选择**：集成到 `gcl_trajectory_quality.py`（非侵入式，不修改 trace schema）

新参数：`--drift` → 触发漂移检测，输出两个时间窗口的对比

---

## Phase 清单

- [ ] **Phase 1**: `_compute_window_metrics(traces)` — 提取单个窗口的聚合指标
- [ ] **Phase 2**: `_simplified_ks_test` — 简化 KS 检验（无 scipy）
- [ ] **Phase 3**: `compute_drift(recent, baseline)` — 漂移计算
- [ ] **Phase 4**: `analyze_drift(traces, since_hours)` — 入口函数 + 告警
- [ ] **Phase 5**: 自验证 + 控制台输出格式

---

## 验收标准

1. `compute_drift([PASS, PASS], [PASS, PASS, FAIL])` → pass_rate drift < 0（recent 更高）
2. `compute_drift([FAIL, FAIL], [PASS, PASS, PASS])` → pass_rate drift < 0 且 drift_sigma < -1
3. `simplified_ks_test([1,2,3], [4,5,6])` → ks_stat > 0.3（明显不同分布）
4. 当 qcloud-cos-ops pass_rate 从 85% 跌到 40% 时，产生 high severity 告警
5. 如果 recent_window 数据不足 3 条，返回 `{"error": "insufficient_recent_data"}`
6. self-verify 通过

---

## 自验证

```python
traces_recent = [
    {"final": {"status": "PASS"}, "iterations": [{"critic": {"scores": {"safety": 1.0}}}]},
    {"final": {"status": "PASS"}, "iterations": [{"critic": {"scores": {"safety": 1.0}}}]},
    {"final": {"status": "FAIL"}, "iterations": [{"critic": {"scores": {"safety": 0.5}}}]},
]
traces_baseline = [
    {"final": {"status": "PASS"}, "iterations": [{"critic": {"scores": {"safety": 1.0}}}]},
    {"final": {"status": "PASS"}, "iterations": [{"critic": {"scores": {"safety": 1.0}}}]},
    {"final": {"status": "PASS"}, "iterations": [{"critic": {"scores": {"safety": 1.0}}}]},
]
result = compute_drift(traces_recent, traces_baseline)
# recent pass_rate=2/3=0.67, baseline=3/3=1.0
assert result["pass_rate"]["drift"] < 0
assert result["pass_rate"]["direction"] == "↓"
assert result["alerts"]  # pass_rate drift should trigger alert
```
