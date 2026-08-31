# Traceability BLOCKER 一键修复模板

## Problem Statement

`Response missing RequestId — traceability degraded` 是 GCL 全场第二慢的 BLOCKER
（MTTR ≈ 9.0m，39 次，仅次于 yaml_python_drift 12m）。

根因：tccli / SDK 响应**有** `RequestId`，但代码没读取/记录 → 审计与调试无法把
GCL 输出关联回腾讯云 API 日志。

MTTR 高的原因不是修复难，而是**每次从零开始**：定位响应处理代码 → 猜写入位置
（log? trace? audit?）→ 手写捕获片段。模板化后三步都变为「查表 + 粘贴」。

## 标准修复步骤（5 步）

| # | 步骤 | 动作 | 耗时 |
|---|---|---|---|
| 1 | 定位 | 运行 `python3 scripts/auto_fix_gcl_blockers.py --scan-code-traceability --dry-run`，输出含行号 + SUGGEST | ~30s |
| 2 | 确认 | 打开对应文件确认该响应有 `RequestId` 字段（tccli 必有） | ~30s |
| 3 | 捕获 | 按下方场景模板粘贴 `request_id = ...` 一行 | ~10s |
| 4 | 写入 | 按「写入位置决策树」选 trace / log / audit 之一 | ~10s |
| 5 | 验收 | 跑下方验收清单（hook + self-test + 扫描复跑） | ~1m |

## 场景模板

### 场景 1: tccli subprocess

```python
result = subprocess.run(["tccli", "cvm", "DescribeInstances", ...], capture_output=True, text=True)
data = json.loads(result.stdout)
# FIX: 捕获 RequestId
request_id = data["Response"].get("RequestId", "unknown")
logger.info("cvm.DescribeInstances", request_id=request_id)  # 写入 log
# 或写入 trace（见决策树）
```

### 场景 2: tencentcloud-sdk

```python
response = client.DescribeInstances(req)
# FIX
request_id = response.Response.RequestId
logger.info("cvm.DescribeInstances", request_id=request_id)
```

### 场景 3: requests（HTTP 直调）

```python
resp = requests.get(url, headers=...)
# FIX
request_id = resp.headers.get("X-TC-RequestId") or resp.json().get("Response", {}).get("RequestId", "unknown")
logger.info("cvm.DescribeInstances", request_id=request_id)
```

## 写入位置决策树

```
响应处理代码拿到 request_id 后：
├─ 有 trace 对象（GCL trace dict）      → trace["request_id"] = request_id
├─ 有 logger                            → logger.info("<product>.<action>", request_id=request_id)
├─ 有 audit（audit.record / audit log）  → audit.record(..., request_id=request_id)
└─ 都没有                               → 至少 print(f"... request_id={request_id}") / 随结果返回
```

优先级：trace > audit > log > print。只读操作（Describe/Query/List/Get/Check）
可跳过捕获（`check_requestid_capture.py` 不拦截只读）。

## 验收检查清单

1. `python3 scripts/check_requestid_capture.py --self-test` → 0
2. `python3 scripts/auto_fix_gcl_blockers.py --scan-code-traceability --dry-run`
   → 该文件不再出现（若无其他文件有同类问题则输出 "No RequestId capture issues found"）
3. `python3 scripts/auto_fix_gcl_blockers.py --self-test` → 0
4. 修复后的代码真实可追溯：GCL trace 中该命令的 `result_excerpt` 含 `RequestId`，
   且代码中有 `request_id` 变量被 trace/log/audit 消费（grep `request_id` 确认）

## 与现有工具集成

| 工具 | 角色 | 交互方式 |
|---|---|---|
| `scripts/check_requestid_capture.py` | 预防 hook（pre-commit） | 不修改；检测到缺失即阻止提交 |
| `scripts/auto_fix_gcl_blockers.py` | 定位 + 建议 | `--scan-code-traceability` 输出行号 + `SUGGEST: ... see traceability-fix-template.md#场景N`；`traceability_fix_suggestion()` 返回带锚点建议 |
| 本文档 | 修复模板 | 场景 1-3 粘贴即用；决策树选写入位置 |

## 已知限制

- 模板解决「捕获与写入」；若 `RequestId` 本身缺失（API 层），需另查 tccli 版本/鉴权。
- 修复后需真实 GCL run 验证 MTTR；本模板只消除「从零开始」的时间（实测场景：
  `collect_mttr_samples.py` 中 template 场景 iter 耗时 1m vs 非模板 4-5m）。
