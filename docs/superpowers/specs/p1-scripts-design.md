# P1 Scripts — Design & Plan

> 为 TODO.md 中 7 个 P1/P2/P3 待开发项编写 SPEC+PLAN。

---

## 1. P1-A: rubric_calibrate.py（自适应阈值）

### 背景
当前所有 skill 共用固定阈值 `correctness≥0.5, safety=1.0`。
实际上不同 skill 的操作风险和历史评分分布差异很大（如 cos-ops 的 `DeleteBucket` vs `PutObject`）。

### 设计

```
输入：audit-results/gcl-trace-*.json（历史 trace）
输出：per-skill × per-dimension 的阈值建议

算法：
1. 聚类：按 skill + op_type 分组
2. 统计：每组内 correctness/safety/idempotency/traceability/spec_compliance 的均值和标准差
3. 建议：如果历史均值 > 阈值 → 建议维持；如果均值持续接近阈值 → 建议降至 0.0
4. 输出：JSON 报告 + 变更 diff（建议写入 rubric.md 的 Override 节）

阈值公式：
  suggested_threshold = min(historical_mean, DEFAULT_THRESHOLD)
  confidence = 1 - (stddev / mean)  # 置信度

不修改 rubric，仅生成建议供人类审批。
```

### Schema

```json
{
  "skill": "qcloud-cos-ops",
  "dimension": "correctness",
  "op_type": "delete",
  "historical_mean": 0.62,
  "historical_stddev": 0.12,
  "default_threshold": 0.5,
  "suggested_threshold": 0.5,
  "confidence": 0.81,
  "recommendation": "MAINTAIN",
  "n_samples": 23
}
```

### 实施
- 新建：`scripts/rubric_calibrate.py`
- 无需修改现有文件
- self-verify：运行 `python3 scripts/rubric_calibrate.py --dry-run` 输出合理 JSON

---

## 2. P1-B: Self-Critique 补强（structural_critic）

### 背景
当前 `gcl_runner.py` 的 `structural_critic` 只检查 exit_code。
需要扩展为功能性检查。

### 设计

```python
def structural_critic(command: str, result_json: str, response: dict) -> dict:
    checks = {}
    
    # Correctness: 检查响应是否含预期 JSON path
    expected_paths = get_expected_paths(command)  # skill-specific
    checks["has_expected_fields"] = all(p in response for p in expected_paths)
    
    # Idempotency: 检查是否含 ClientToken
    checks["has_client_token"] = "ClientToken" in str(response)
    
    # Traceability: 检查是否含 RequestId
    checks["has_request_id"] = "RequestId" in str(response)
    
    # Spec Compliance: 检查 command 是否匹配 skill 的 cli-usage.md
    checks["command_valid"] = validate_command_against_skill(command, skill)
    
    return {
        "score": 1.0 if all(checks.values()) else 0.0,
        "checks": checks
    }
```

### 实施
- 修改：`scripts/gcl_runner.py`（扩展 `_structural_critic`）
- 新增 flag：`--self-critique`
- 新增：`scripts/check_command_validity.py`（辅助脚本）
- self-verify：`python3 scripts/gcl_runner.py --dry-run --self-critique` 正常执行

---

## 3. P1-C: pattern_anomaly_detect.py（主动模式发现）

### 背景
当前 failure_patterns 只在 GCL trace 后被动写入。
需要主动发现 emerging pattern。

### 设计

```
输入：audit-results/gcl-trace-*.json（最近 7 天）
算法：
1. 统计：同一 error 最近 7 天出现频率 vs 历史均值（30 天）
2. 检测：z-score > 2 = emerging
3. 分类：
   - emerging（z>2）：首次大量出现
   - novel：skill+operation 新组合首次出现
4. 输出：
   - audit-results/pattern-anomaly-YYYYMMDD.json
   - docs/failure-patterns.md 顶部 ## Emerging Alerts 区块（写入）

触发频率：每周一次（cron）
```

### Schema

```json
{
  "type": "emerging|novel",
  "error": "InvalidParameter",
  "skill": "qcloud-cvm-ops",
  "command": "TerminateInstances",
  "recent_count": 15,
  "historical_mean": 3,
  "stddev": 2.1,
  "z_score": 5.7,
  "severity": "major",
  "first_seen": "2026-07-12",
  "recommendation": "Add to failure-patterns.md or investigate root cause"
}
```

### 实施
- 新建：`scripts/pattern_anomaly_detect.py`
- self-verify：运行 `python3 scripts/pattern_anomaly_detect.py --dry-run` 输出 JSON

---

## 4. P1-E: distribution_drift detection

### 背景
GCL 质量可能随时间漂移（rubric 变宽松、skill 变复杂）。
需要检测并预警。

### 设计

```
输入：两个时间窗口的 audit-results/gcl-trace-*.json
窗口1：最近 7 天
窗口2：历史 30 天

算法：
1. 每 skill × dimension 计算均值
2. 检测：ks-test 或简化均值差
3. 告警阈值：Δ > 0.2 = 显著漂移

分解维度：per-skill / per-dimension / per-op-type

输出：
  audit-results/distribution-drift-YYYYMMDD.json
  {
    "skill": "qcloud-cos-ops",
    "dimension": "correctness",
    "window1_mean": 0.72,
    "window2_mean": 0.58,
    "delta": -0.14,
    "alert": "DEGRADING",
    "trend": "↓ Correctness dropping over time"
  }
```

### 实施
- 新建：`scripts/distribution_drift.py`
- 复用 `gcl_trace_aggregate.py` 的数据读取逻辑
- self-verify：运行 `python3 scripts/distribution_drift.py --dry-run` 输出 JSON

---

## 5. P1-F: hallucination_detection

### 背景
防止 Agent 给出错误结论（返回空结果却声称成功）。

### 设计

```python
def detect_hallucination(command: str, response: dict) -> dict:
    checks = []
    
    # Schema 验证：返回 JSON 字段是否完整
    required = get_required_fields(command)
    missing = [f for f in required if f not in response]
    if missing:
        checks.append({"type": "missing_schema_fields", "fields": missing})
    
    # 边界检测：Describe 应有结果却返回空
    if is_list_query(command) and not response.get("Response", {}).get("Data"):
        checks.append({"type": "null_result_on_list_query", "severity": "HIGH"})
    
    # 幂等性自洽：重复命令结果一致
    # （需要历史 trace，仅标记待人工审查）
    
    return {
        "suspect": len(checks) > 0,
        "checks": checks,
        "types": [c["type"] for c in checks]
    }
```

### 实施
- 新建：`scripts/hallucination_detection.py`
- 可集成到 `gcl_runner.py` 作为 structural_critic 的一部分
- self-verify：运行 `python3 scripts/hallucination_detection.py --dry-run`

---

## 6. P2-A: Pattern→Rule 升级路径

### 背景
count≥10 的 pattern 应自动升级为 Anti-Pattern。

### 设计

```python
def promote_pattern_to_antipattern(pattern: dict) -> str:
    """
    生成 Anti-Pattern 内容，写入 skill 的 SKILL.md Anti-Pattern 节。
    """
    content = f"""
### Anti-Pattern: {pattern['error']} ({pattern['skill']})

**现象**：{pattern['error']}
**根因**：{pattern['fix']} 之前的错误模式
**触发**：{pattern['command']}
**频率**：{pattern['count']} 次命中
**修复**：{pattern['fix']}
"""
    return content
```

触发条件：`--promote` flag，count≥10

### 实施
- 修改：`scripts/failure_pattern_extract.py`（新增 `--promote` flag）
- 输出：建议写入对应 skill SKILL.md 的 Anti-Pattern 节
- self-verify：`--promote --dry-run` 输出建议内容

---

## 7. P3-A: 结构化错误语义

### 背景
当前 `_FAILURE_SIGNATURES` 是手写 regex，能力有限。
应升级为腾讯云官方错误码表驱动。

### 设计

```python
# 构建错误码映射
TCLOUD_ERROR_CODES = {
    "AuthFailure": {"severity": "major", "category": "auth"},
    "InvalidParameter": {"severity": "minor", "category": "param"},
    "ResourceNotFound": {"severity": "minor", "category": "state"},
    "UnsupportedOperation": {"severity": "major", "category": "api"},
    # ... 扩展至所有腾讯云 API 常见错误码
}

def parse_tcloud_error(response: dict) -> dict:
    code = response.get("Response", {}).get("Error", {}).get("Code", "")
    msg = response.get("Response", {}).get("Error", {}).get("Message", "")
    
    info = TCLOUD_ERROR_CODES.get(code, {"severity": "unknown", "category": "unknown"})
    return {
        "code": code,
        "message": msg,
        "severity": info["severity"],
        "category": info["category"]
    }
```

### 实施
- 新建：`scripts/tcloud_error_codes.py`（错误码表 + 解析器）
- 修改：`scripts/gcl_runner.py`（集成 `parse_tcloud_error`）
- self-verify：测试 `python3 scripts/tcloud_error_codes.py --test`

---

## 实施顺序

1. **P1-A** rubric_calibrate.py（独立脚本，无依赖）
2. **P1-C** pattern_anomaly_detect.py（独立脚本，无依赖）
3. **P1-E** distribution_drift.py（复用 gcl_trace_aggregate 逻辑）
4. **P1-F** hallucination_detection.py（独立脚本）
5. **P1-B** structural_critic 补强（修改 gcl_runner.py）
6. **P2-A** Pattern→Rule（修改 failure_pattern_extract.py）
7. **P3-A** tcloud_error_codes.py（新建 + 修改 gcl_runner.py）

每个脚本独立 GCL 执行，max_iter=2。
