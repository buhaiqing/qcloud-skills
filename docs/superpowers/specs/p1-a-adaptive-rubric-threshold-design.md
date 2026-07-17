# P1-A: Rubric 自适应阈值 — 设计文档

## 背景

当前 `scripts/gcl_runner.py` 中 `RUBRIC_THRESHOLDS` 是静态硬编码：
```python
RUBRIC_THRESHOLDS = {
    "correctness": 0.5,
    "safety": 1.0,       # 安全维度永不降
    "idempotency": 0.5,
    "traceability": 0.5,
    "spec_compliance": 0.5,
}
```

**问题**：不同 skill 的执行难度差异巨大：
- `qcloud-cos-ops` 的 spec_compliance 历史均值只有 0.3 → 固定 0.5 导致每次 RETRY
- `qcloud-vpc-ops` 的 correctness 历史均值 0.95 → 固定 0.5 太宽松，漏检真实问题

**机会**：利用 `audit-results/gcl-trace-*.json` 历史数据，统计每个 skill + 维度的评分分布，计算动态阈值。

---

## 算法设计

### 输入

- `audit-results/gcl-trace-*.json`（GCL 轨迹文件）
- `--skill` 可选：只分析指定 skill
- `--days` 可选：只分析最近 N 天数据（默认 90）

### 核心公式

```python
# 每次迭代的最终评分 = 该 iteration 的 critic scores
# "最终"定义：PASS iter 的评分 / MAX_ITER 的最后一次 RETRY iter 的评分

# 维度 d 的阈值建议 = 均值(所有 d 评分) - k × 标准差(d 评分)
# k = 1.0（1σ 容忍度，约 68% 覆盖）
# 建议阈值下限 = max(0.0, 均值 - k × σ)（safety 除外）
```

**safety 特殊处理**：`safety` 永远不降，建议值仅供参考（用于观察）。

### 统计方法

| 指标 | 公式 | 用途 |
|------|------|------|
| 均值 | `mean(scores[d])` | 反映整体水平 |
| 标准差 | `std(scores[d])` | 反映波动幅度 |
| 中位数 | `median(scores[d])` | 抗极端值干扰 |
| 样本数 | `n = len(scores[d])` | 样本不足时给出警告 |
| 建议阈值 | `max(0.0, mean - k * std)` | 校准输出 |
| 均值偏离度 | `abs(suggested - default)` | 判断是否需要调整 |

### 样本数门槛

- `n < 10` → 警告 "样本不足，建议维持默认阈值"
- `n ≥ 10` → 正常计算
- `n ≥ 50` → 可信度标记为 "HIGH"

---

## 输出设计

### 控制台表格

```
=== Rubric 阈值校准报告 (最近 90 天) ===
Skill: qcloud-cos-ops  |  样本: 23  |  可信度: MEDIUM

维度              默认阈值   均值      σ       建议阈值   偏离度   状态
--------------------------------------------------------------------------
correctness       0.50      0.72     0.31     0.41       -0.09   ⚠ 偏低
safety            1.00      0.96     0.14     0.86       -0.14   🔒 锁定
idempotency       0.50      0.50     0.00     0.50        0.00   ✓ 匹配
traceability      0.50      0.95     0.10     0.85       +0.35   ↑ 可提升
spec_compliance   0.50      0.30     0.22     0.08       -0.42   ⚠ 偏低

⚠ spec_compliance 历史均值=0.30，当前阈值=0.50，建议降至 0.0~0.1
💡 注意：safety 维度永远不降，建议值仅供参考
```

### JSON 输出（`--json` flag）

```json
{
  "generated_at": "2025-07-10T10:00:00Z",
  "period_days": 90,
  "skills": {
    "qcloud-cos-ops": {
      "sample_count": 23,
      "confidence": "MEDIUM",
      "dimensions": {
        "correctness": {
          "default": 0.5,
          "mean": 0.72,
          "std": 0.31,
          "suggested": 0.41,
          "deviation": -0.09,
          "status": "warn"
        },
        "safety": {
          "default": 1.0,
          "mean": 0.96,
          "std": 0.14,
          "suggested": 0.86,
          "deviation": -0.14,
          "status": "locked"
        }
      }
    }
  }
}
```

---

## 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/rubric_calibrate.py` | 新增 | 核心脚本 |
| `scripts/rubric_calibrate_test.py` | 新增 | 单元测试 |
| `docs/superpowers/specs/p1-a-adaptive-rubric-threshold-design.md` | 本文档 | 设计规格 |

---

## 算法验证（self-check）

```python
# 1. 空数据 → 报告 "No traces found"，不 crash
# 2. 单个 trace → 正常计算（n=1 警告）
# 3. 所有评分相同 → std=0 → suggested=mean → 偏离度=0
# 4. safety 永远 ≥ 0.5，即使建议值更低 → safety floor
```

---

## 与 gcl_runner.py 的集成方式

**建议制，非自动生效**：输出报告 → 人类审批 → 手动写入 `references/rubric.md`。

理由：
1. 安全：自动降低阈值可能导致风险漏检
2. 可审计：所有阈值变更都有记录
3. 依赖清晰：只需要现有 `audit-results/gcl-trace-*.json`（P0-A 已就绪）

未来可扩展为 `--apply` flag，直接写入 rubric.md（需人工确认）。

---

## Phase 清单

- [x] **Phase 1**: `rubric_calibrate.py` 核心逻辑（parse args、load traces、compute stats、format table）✅
- [x] **Phase 2**: `--json` 输出 + `--skill` 过滤 ✅
- [x] **Phase 3**: 单元测试 `rubric_calibrate_test.py`（18 tests）✅
- [x] **Phase 4**: self-verify（`python3 scripts/rubric_calibrate.py --dry-run`）✅
- [x] **Phase 5**: TE-Audit 记录（见 TODO.md P1-A）✅
