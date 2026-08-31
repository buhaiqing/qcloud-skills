# requestid-capture-check — 设计文档

## 1. Problem Statement

GCL trace 分析（R5 G-Autofix-TI 调研）发现 39 次 `traceability BLOCKER`：

> `Response missing RequestId — traceability degraded`

tccli 调用返回的 JSON 中每个响应都包含 `Response.RequestId` 字段，但处理代码往往只读取业务数据（`InstanceSet`、`Instances` 等），不捕获 RequestId。

**影响**：审计、工单关联、调试时无法将日志/trace 与具体 API 调用对应。

## 2. Solution

写一个 pre-commit hook `check_requestid_capture.py`，在提交前扫描 Python 代码，检测 tccli/SDK 响应处理是否捕获 RequestId。

## 3. Detection Rules

### Rule A — tccli subprocess + Response 消费无 RequestId

```python
# BAD
result = subprocess.run(["tccli", "cvm", "RunInstances", "--Region", "ap-guangzhou"])
data = json.loads(result.stdout)
instances = data["Response"]["InstanceSet"]

# GOOD
result = subprocess.run(["tccli", "cvm", "RunInstances", "--Region", "ap-guangzhou"])
data = json.loads(result.stdout)
request_id = data["Response"].get("RequestId")
log.info("cvm.RunInstances", request_id=request_id)
instances = data["Response"]["InstanceSet"]
```

### Rule B — tencentcloud-sdk response.Response 访问无 RequestId

```python
# BAD
resp = client.RunInstances(req)
instances = resp.Response.InstanceSet

# GOOD
resp = client.RunInstances(req)
request_id = resp.Response.RequestId
log.info("run_instances", request_id=request_id)
instances = resp.Response.InstanceSet
```

### Rule C — json.load(stdout) 解析后 Response 消费无 RequestId

```python
# BAD
proc = subprocess.run(["tccli", "cvm", "DescribeInstances"], capture_output=True)
data = json.loads(proc.stdout)
instances = data["Response"]["InstanceSet"]

# GOOD
proc = subprocess.run(["tccli", "cvm", "DescribeInstances"], capture_output=True)
data = json.loads(proc.stdout)
request_id = data.get("RequestId") or data.get("Response", {}).get("RequestId")
logger.info("DescribeInstances", request_id=request_id)
instances = data["Response"]["InstanceSet"]
```

### Skip rules

- 只读操作（`Describe*`、`Query*`、`List*`、`Get*`、`Check*`）跳过（无写语义，traceability 要求较低）
- 已捕获 RequestId（`request_id =`、`RequestId` 在附近 10 行内出现）跳过

## 4. Implementation

```
scripts/check_requestid_capture.py   — pre-commit hook（纯 stdlib）
docs/superpowers/specs/requestid-capture-check.md
```

**自检**：8 个用例（A 4 个 + B 4 个），BAD patterns 触发 Issue，GOOD patterns 不触发。

## 5. auto_fix 增强

`scripts/auto_fix_gcl_blockers.py` 新增 `fix_requestid_in_text()`、`fix_file_traceability()`、`scan_code_traceability()`：

- dry-run 默认
- `--scan-code-traceability` 查看问题
- `--apply --scan-code-traceability` 实际修改（生成 `.bak`）

## 6. 与 R5 G5.3 的关联

R5 G-Autofix-TI 调研了 265 条 GCL trace 中的 BLOCKER 分布，发现 39 次 traceability 问题根本原因是代码层面没有捕获 RequestId，而非 trace schema 问题。因此从代码层加 pre-commit hook，从根上阻断。
