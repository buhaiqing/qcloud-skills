# aggregate-dashboard-mttr — MTTR 量化扩展设计

## 背景

R5 G-Runner-Schema 要求所有 trace 必须包含：
- `started_at` (ISO timestamp)
- `finished_at` (ISO timestamp)
- `commits` (list[str])
- `files_changed` (list[str])

R4 报告遗留：
> MTTR | N/A (trace files lack started_at/finished_at — use real GCL runner timestamps)

R6 T1 补完后，此设计即可启用。

---

## MTTR 算法

### 定义

**MTTR (Mean Time To Repair)** = 从 BLOCKER 首次发现到修复完成的时间。
- 发现时间戳 = `started_at`
- 修复时间戳 = `finished_at`（trace 最终 status == PASS）
- MTTR = `finished_at − started_at`（秒），按 BLOCKER 类型分组

### 计算逻辑 (`compute_mttr`)

```
For each trace with started_at AND finished_at:
  1. Find first iter with a BLOCKER suggestion (matched by _BLOCKER_KEYWORDS)
  2. If final.status == "PASS":
       delta = finished_at - started_at
       by_type[blocker_type].append(delta)
  3. Else: skip (MAX_ITER/ABORT 不计入 MTTR)

Per-type summary:
  avg_seconds = mean(deltas)
  median_seconds = median(deltas)
  min/max = min/max(deltas)
  bucket = _duration_bucket(delta)  # <1h / 1-4h / 4-24h / 1-7d / >7d
```

### 时间字段依赖

| 字段 | 来源 | 缺失时行为 |
|------|------|-----------|
| `started_at` | GCL runner 写入 trace | `compute_mttr` 跳过该 trace，`skipped_no_ts++` |
| `finished_at` | 同上 | 同上 |
| `final.status` | Critic 决策 | 非 PASS 的 trace 不计入 MTTR |

---

## 与其他 Dashboard 指标的区分

| 指标 | 含义 | 公式/来源 |
|------|------|-----------|
| **PASS 率** | 质量 | `final_pass_count / total_traces` |
| **MTTR** | 修复速度 | `finished_at - started_at`（仅 PASS trace） |
| **漂移发现速率** | 问题密度 | `blocker_types_top5` 计数 / 时间窗口 |
| **回放速率** | 吞吐量 | `n traces / time window (days)` |

---

## 其他时间维度分析

### 历史回放速率 (`compute_playback_rate`)

```python
rate = n_timestamps_traces / window_days
# window = max(ts_list) - min(ts_list)
```

### 每日 trace 数 (`compute_daily_counts`)

按 `started_at`（或 filename 解析）提取日期分组，返回 `{"2026-08-25": 3, ...}`

### 最近 7 天趋势 (`compute_7day_trend`)

```
2026-08-29 ████
2026-08-30 ██
2026-08-31 ██████████
```

文本 mini-chart，7 行，每日计数映射到 `█` 字符（最多 10 个）。

### BLOCKER 修复时间分布 (`_duration_bucket`)

| bucket | 含义 |
|--------|------|
| `< 1h` | < 3600s |
| `1-4h` | 3600–14400s |
| `4-24h` | 14400–86400s |
| `1-7d` | 86400–604800s |
| `> 7d` | ≥ 604800s |

---

## Dashboard 新增 Sections

| Section | 位置 | 说明 |
|---------|------|------|
| MTTR (按 BLOCKER 类型) | 产出指标之后 | per-type avg/median/range |
| BLOCKER 修复时间分布 | MTTR 之后 | histogram text table |
| 历史回放速率 | 修复时间分布之后 | rate + window + count |
| 每日 trace 数 | 回放速率之后 | last 30 days table |
| 最近 7 天趋势 | 每日之后 | mini-chart |

---

## Graceful Fallback

旧 trace（无 `started_at`/`finished_at`）不会导致崩溃：

```python
mttr_result = compute_mttr(traces)
# skipped_no_ts += 1 for each trace missing timestamps
# skipped_no_blocker += 1 for each trace with no BLOCKER suggestion
# per_type = {} if no valid traces → render shows "无数据" message
```

---

## 使用示例

```bash
# 自检（fake traces + started_at/finished_at）
python3 scripts/aggregate_gcl_traces.py --self-test

# 全量聚合
python3 scripts/aggregate_gcl_traces.py

# 输出含所有新 sections
```

预期 fake-traces 自检输出：
```
per_type:
  yaml_python_drift: count=2, avg=57.5m, median=1.0h
  spec_file_refs_missing: count=1, avg=1.1h, median=1.1h
fix_time_buckets:
  1-4h: 2, < 1h: 1
```

---

## 自检验证

`--self-test` 验证：
- 旧 trace（无 `started_at`/`finished_at`）→ `skipped_no_ts >= 7`
- 新 trace（带 timestamps）→ `mttr_drifts_fixed == 3`
- `per_type` 非空
- `playback` 有 `rate` key
- `daily_counts` 有数据
- `trend_7day` 有数据
