# P1-D: 操作类型成功率 — 设计文档

## 背景

当前轨迹分析只知道"某个 skill 通过率是多少"，但不知道是哪种操作导致的。

**问题场景**：
- `qcloud-cos-ops` 通过率 60%，但不知道是 DELETE 操作失败还是 PUT 操作失败
- 安全团队只知道有安全事件，不知道是哪个操作触发的

**机会**：从 tccli 命令行直接解析出操作类型，无需 schema 变更。

---

## 操作类型分类

tccli 命令结构：`tccli <product> <Action> [options]`

| 类型 | 关键词（Action 中） | 风险 |
|------|------------------|------|
| `read` | Describe / Query / List / Search / Get / Check / Inspect | 低 |
| `write` | Create / Modify / Update / Set / Resize / Start / Stop / Restart / Reboot | 中 |
| `delete` | Delete / Destroy / Release / Remove / Cancel / Drop | 高 |

**优先级规则**：delete > write > read（匹配第一个）

**命令示例**：
```
tccli cvm DescribeInstances              → read
tccli cvm StopInstances                 → write
tccli cdb DeleteAccounts               → delete
tccli cos DeleteObject                 → delete
tccli vpc DeleteVpc                    → delete
tccli clb DescribeLoadBalancers        → read
```

---

## 算法设计

### 函数签名

```python
def classify_operation(command: str) -> str:
    """Classify tccli command into read/write/delete.
    
    Args:
        command: tccli command string, e.g. 'tccli cvm DescribeInstances --Region ap-guangzhou'
    
    Returns:
        'read' | 'write' | 'delete'
    
    Examples:
        classify_operation('tccli cvm DescribeInstances')  → 'read'
        classify_operation('tccli cdb DeleteAccounts')    → 'delete'
        classify_operation('tccli cos PutObject')         → 'write'
    """
```

### 分类规则（按优先级）

1. `delete` 关键词：Delete / Destroy / Release / Remove / Cancel / Drop
2. `write` 关键词：Create / Modify / Update / Set / Resize / Start / Stop / Restart / Reboot / Open / Close / Associate / Disassociate / Attach / Detach
3. 默认：`read`

### 分类结果存储

在 `gcl_trace_aggregate.py` 或 `gcl_trajectory_quality.py` 中为每条 trace 增加 `operation_type` 字段：

```json
{
  "skill": "qcloud-cvm-ops",
  "operation_type": "write",
  "operation": "StopInstances",
  "final": {"status": "PASS", "iter": 1},
  ...
}
```

---

## 输出设计

### 控制台输出

```
=== 操作类型成功率 (30天, 42 traces) ===

per-skill × per-operation-type:

qcloud-cos-ops:
  read:   12 traces, pass_rate=100%, avg_iters=1.0
  write:   8 traces, pass_rate= 87%, avg_iters=1.2
  delete:  3 traces, pass_rate= 33%, avg_iters=2.7  ⚠ DELETE 成功率最低！

qcloud-cvm-ops:
  read:   20 traces, pass_rate= 95%, avg_iters=1.1
  write:  10 traces, pass_rate= 80%, avg_iters=1.5
  delete:  5 traces, pass_rate= 60%, avg_iters=2.0
```

### JSON 输出

```json
{
  "generated_at": "2025-07-17T12:00:00Z",
  "window_days": 30,
  "by_skill": {
    "qcloud-cos-ops": {
      "read":   {"total": 12, "pass_rate": 1.0,  "avg_iters": 1.0},
      "write":  {"total":  8, "pass_rate": 0.875, "avg_iters": 1.25},
      "delete": {"total":  3, "pass_rate": 0.333, "avg_iters": 2.7}
    }
  },
  "alerts": [
    {"skill": "qcloud-cos-ops", "op_type": "delete", "pass_rate": 0.333, "threshold": 0.8, "severity": "high"}
  ]
}
```

---

## 与现有代码集成

两种方案：

**方案 A（侵入式）**：修改 `gcl_runner.py` 的 trace 写入，在 `persist_trace` 前解析 `command` 字段，增加 `operation_type`

**方案 B（非侵入式）**：在 `gcl_trace_aggregate.py` 和 `gcl_trajectory_quality.py` 中按需解析，不修改 trace schema

**选择**：方案 B。理由：
- 不需要修改 trace schema（向后兼容）
- 可以在任意历史 trace 上运行
- 不影响 gcl_runner.py 的稳定性

---

## Phase 清单

- [ ] **Phase 1**: `scripts/op_type_classifier.py` — 纯函数 `classify_operation`，TDD（10+ 测试用例覆盖边界）
- [ ] **Phase 2**: `gcl_trajectory_quality.py` — 集成 `operation_type` 到分析输出
- [ ] **Phase 3**: 告警逻辑（pass_rate < 阈值时标记 ⚠）
- [ ] **Phase 4**: 单元测试（`op_type_classifier_test.py`）
- [ ] **Phase 5**: self-verify + GCL review

---

## 验收标准

1. `classify_operation('tccli cvm DescribeInstances')` → `'read'`
2. `classify_operation('tccli cdb DeleteAccounts')` → `'delete'`
3. `classify_operation('tccli cos PutObject')` → `'write'`
4. `classify_operation('tccli vpc DescribeVpcEx')` → `'read'`（带 Ex 后缀）
5. `classify_operation('tccli clb CreateLoadBalancer')` → `'write'`
6. `classify_operation('')` → `'read'`（空命令默认为 read，安全）
7. 集成后 JSON 输出包含 `by_skill.<skill>.<op_type>.pass_rate`
8. 当 delete 操作 pass_rate < 0.5 时，产生告警条目

---

## 算法自验证

```python
assert classify_operation('tccli cvm DescribeInstances') == 'read'
assert classify_operation('tccli cdb DeleteAccounts') == 'delete'
assert classify_operation('tccli cos PutObject') == 'write'
assert classify_operation('tccli vpc DeleteVpc') == 'delete'
assert classify_operation('tccli clb DescribeLoadBalancers') == 'read'
assert classify_operation('tccli redis StopInstance') == 'write'
assert classify_operation('tccli cvm RebootInstances') == 'write'
assert classify_operation('') == 'read'  # safe default
```
