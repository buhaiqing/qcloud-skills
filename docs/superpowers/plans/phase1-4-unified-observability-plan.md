# Plan: Phase 1.4 — 统一观测面完成

> **Status**: Complete
> **Date**: 2026-08-25
> **Spec**: `docs/superpowers/specs/phase1-l3-adaptive-orchestration-design.md` §1.4
> **ADR**: `docs/architecture/ADR-0004-phase1-l3-adaptive-orchestration.md`

---

## 现状盘点（截止 2026-08-25）

| 组件 | 状态 | 证据 |
|---|---|---|
| `TraceSpan` dataclass + `ObservableSink.emit_trace_span()` | ✅ 已实现 | observ.py:54-107, 186-232 |
| `ObservableSink._update_trace_summary()` | ✅ 已实现 | observ.py:197-232 |
| `dispatcher._emit_span()` → emit_trace_span | ✅ 已实现 | dispatcher.py:686-704 |
| `dispatcher._apply_escalation()` → DELEGATE span | ✅ 已实现 | dispatcher.py:517-553 |
| `gcl_runner._emit_trace_span()` | ✅ 已实现 | gcl_runner.py:716-762 |
| `gcl_runner.cmd_run()` 调用 `_emit_trace_span` | ✅ 已实现 | gcl_runner.py:1115, 1134, 1177 |
| `evidence_kernel.post_record(span_id=...)` | ✅ 已实现 | evidence_kernel.py:63-75 |
| `emit_evidence_record()` → 调用 `post_record` | ✅ 已实现 | gcl_runner.py:816 |
| `gcl_trace_aggregate --cross-skill` | ✅ 已实现 | gcl_trace_aggregate.py:125-186, 201-207 |
| `test_trace_span.py` | ✅ 已实现（部分） | test_trace_span.py:1-233 |
| `cross_skill_e2e_test.py` | ✅ 已实现 | cross_skill_e2e_test.py |

**Plan 中标记为 pending 但实际已完成的 Step：**

- Step 1.4.1 ✅ TraceSpan schema — `ruff check` 已在 CI 运行
- Step 1.4.2 ✅ GCL runner span 集成 — `_emit_trace_span` + 3 call sites
- Step 1.4.3 ✅ Copilot dispatcher span 集成 — `_emit_span` + DELEGATE 链
- Step 1.4.4 ✅ Evidence Kernel 关联 — `span_id` 参数已实现
- Step 1.4.5 ✅ gcl_trace_aggregate 扩展 — `--cross-skill` 模式
- Step 1.4.6 ⏳ 测试 — `test_trace_span.py` 部分完成，e2e test 存在但未运行

---

## 真正剩余的工作

### GAP-1: `emit_evidence_record` 没有传 `span_id` 给 `post_record` ✅ 已修复

**当前代码**（gcl_runner.py:816）：
```python
post_record(record)  # 无 span_id 参数
```

**应为**：
```python
post_record(record, span_id=f"{run_id}:{args.skill}")
```

证据：`evidence_kernel.post_record` 已支持 `span_id` 参数（evidence_kernel.py:63），但 `emit_evidence_record` 从未传递。

---

### GAP-2: `gcl_trace_aggregate --cross-skill` 无 `--since-hours` 过滤 ✅ 已修复

当前 `gcl_trace_aggregate` 的 `--since-hours` 只过滤 `gcl-trace-*.json` 文件，不支持 `spans.jsonl`。

影响：无法用 `--since-hours 24` 查询最近 24 小时的跨 skill 调用链。

---

### GAP-3: `test_trace_span.py` 缺少 `test_gcl_scores_on_failure` 测试 ✅ 已修复

现有测试只覆盖 success 状态；GCL failure 时 `gcl_scores` 应为 None。

---

### GAP-4: `_current_parent_span_id` 从未在 dispatcher 中设置 ✅ 已修复

代码中 `self._current_parent_span_id` 被读取（dispatcher.py:693），但从未被赋值。这意味着非 DELEGATE 场景的 `parent_span_id` 始终为 None——虽然这在当前实现中是对的（每个 step 自己就是 root），但代码意图不清晰。

---

### GAP-5: `evidence_kernel.post_record` 不支持 `run_id` 重名覆盖 ✅ 已修复

当前实现（evidence_kernel.py:73）：
```python
out = AUDIT / f"evidence-{record['run_id']}.json"
```

若同一 `run_id` 多次调用（如 retry），会覆盖而非追加。

---

## Step 清单

- [x] 修改 `scripts/gcl_runner.py::emit_evidence_record`
  - 验证：运行 smoke test 后 `evidence-*.json` 含 `span_id` 字段

**文件**: `scripts/gcl_runner.py`

---

### Step 2 — `gcl_trace_aggregate --cross-skill` 支持 `--since-hours` (P1)

- [x] 修改 `gcl_trace_aggregate.py::cross_skill_chain`
  - 增加 `since_hours: int | None` 参数
  - 按 `start_time` 过滤 spans
  - `main()` 传递 `--since-hours` 到 `cross_skill_chain`
- [x] 验证：`--cross-skill --run-id X --since-hours 24` 正确过滤

**文件**: `scripts/gcl_trace_aggregate.py`

---

### Step 3 — `test_trace_span.py` 补全失败场景测试 (P1)

- [x] 新增 `GclScoresOnFailureTests`
  - `test_gcl_scores_none_on_failure`: failure span 的 `gcl_scores` 为 None
  - `test_gcl_scores_none_on_halted`: halted span 的 `gcl_scores` 为 None
- [x] 新增 `EvidenceKernelSpanIdTests`
  - 验证 `post_record` 含 `span_id` 字段

**文件**: `qcloud-copilot/copilot/test_trace_span.py`

---

### Step 4 — `evidence_kernel.post_record` 支持幂等追加 (P1)

- [x] 修改 `evidence_kernel.py::post_record`
  - 同一 `run_id` 的多次调用：追加到同一 JSON（`evidence-{run_id}.jsonl`）而非覆盖
  - 向后兼容：若文件不存在则创建

**文件**: `scripts/evidence_kernel.py`

---

### Step 5 — `dispatcher._current_parent_span_id` 清理 (P0)

- [x] 移除 `getattr(self, "_current_parent_span_id", None)` 模式
  - 非 DELEGATE span 的 `parent_span_id = None` 是正确行为（step 是 root）
  - 代码已有注释说明（dispatcher.py:687），无需改动逻辑，仅删掉未赋值的属性读取

**文件**: `qcloud-copilot/copilot/dispatcher.py`

---

### Step 6 — 运行完整测试套件 (P0)

- [x] `cd qcloud-copilot && python3 -m unittest copilot.test_trace_span -v`
- [x] `cd scripts && python3 -m unittest discover -p "*_test.py" -v`
- [x] `ruff check scripts/evidence_kernel.py qcloud-copilot/copilot/dispatcher.py`
- [x] `ruff check scripts/gcl_runner.py`
- [x] `cd scripts && python3 cross_skill_e2e_test.py`

---

## 验收标准

- [x] `emit_evidence_record` 产生的 `evidence-*.json` 含 `span_id` 字段
- [x] `gcl_trace_aggregate --cross-skill --since-hours 24 --run-id X` 正确按时间过滤
- [x] `test_trace_span.py` 所有测试通过（新增 ≥3 个）
- [x] `evidence_kernel.post_record` 同一 `run_id` 多次调用追加而非覆盖
- [x] `ruff check` 零 error（所有修改文件）
- [x] `cross_skill_e2e_test.py` PASS

---

## 执行顺序

```
Step 1 (emit_evidence_record span_id)      ─┐
Step 5 (_current_parent_span_id cleanup)    ─┤  可并行
                                             │
Step 2 (gcl_trace_aggregate --since-hours) ──┤
Step 3 (test_trace_span 补全)              ──┤  可并行
Step 4 (evidence_kernel 幂等追加)           ──┘
                                             │
Step 6 (完整测试套件)                      ──  串行，最后
```

## 依赖

- Step 1: 无
- Step 2: 无
- Step 3: Step 1 完成后 `span_id` 字段才在 evidence 中存在
- Step 4: 无
- Step 5: 无
- Step 6: Step 1-5 全部完成
