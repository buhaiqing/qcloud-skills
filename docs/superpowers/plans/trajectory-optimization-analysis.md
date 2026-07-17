# 轨迹采集优化分析报告

> 基于 P1-A review-fix 循环的真实执行轨迹（2026-07-17）

## 数据来源

5 个 subagent session：
- R1-reviewer, R2-reviewer, R3-reviewer, fix-worker, R4-reviewer
- 共 **73 turns，85 tool calls，~1430 行输出日志**

---

## 5 个优化点（按 ROI 排序）

### ROI 1: `wait({ all: true })` 并行等待 — 省 ~45s

**问题**：父 Agent 逐个 `wait(id)` 串行等待：
```
R1 完成前 → R2 等待 2m41s
R2 完成前 → R3 等待 46s
R3 完成前 → fix-worker 等待 1m16s
fix-worker 完成前 → R4 等待 24s
─────────────────────────────
实际总时间: 5m07s
```

**优化**：3 个 reviewer 并行 launch → `wait({ all: true })` 一次等完
```
理论最优: max(2m41s, 46s, 1m16s) ≈ 2m41s + wait(fix) + wait(R4)
```

**实现**：`review-fix-loop.chain.json` Phase 1 使用 `concurrency: 3` + chain 内部并行

---

### ROI 2: 第一轮合成后再发 R2/R3 — 省 ~60s + 减少重复发现

**问题**：3 个 reviewer 各自独立全量扫描，高度重叠的发现：
- R1 发现：`_dimension_status` 死代码 + `status=="warn"` 死循环
- R2 发现：同上 + 缺失测试覆盖
- R3 发现：同上 + `_fmt` + spec gap

三个评审结论高度重复，浪费 ~60s 执行时间。

**优化**：R1 先跑 → 父 Agent 合成 → 有针对性的发 R2/R3

**实现**：_chain.json Phase 2 synthesis step，读 R1 输出决定是否需要 R2/R3

---

### ROI 3: fix-worker 读全部 → 规划 → 一次性 edit — 减少 14次→3次

**问题**：fix-worker 对同一文件编辑了 14 次（`rubric_calibrate.py` ×10，`rubric_calibrate_test.py` ×4），实际只需要 3 个改动。

**根因**：缺少规划阶段，边读边改，反复尝试。

**优化**：worker prompt 强制三步：
1. **Read ALL** relevant files BEFORE any edit
2. **Plan** all changes (list exact files + lines)
3. **Edit ONCE** per file (batch all changes)

**实现**：_chain.json Phase 3 fix-worker 的 `Critical Constraints` 明确三条规则

---

### ROI 4: Reviewer 输出限 3KB — 省 ~90KB 总输出

**问题**：每个 reviewer 产生 28-32 KB JSON 报告，但有效信息密度极低（R1: 1个死代码函数，R2: 2个缺失测试类，R3: 重复R1+1个spec gap）。

**优化**：reviewer prompt 约束 `Output MUST be under 3KB`，结构化三段：
```
BLOCKERS: (list or 'none')
WARNINGS: (list or 'none')
PRAISE: (brief or 'none')
```

**实现**：_chain.json Phase 1 每个 reviewer task 的 `Constraints` 第 2 条

---

### ROI 5: Reviewer 共享文件预载 — 省 3x I/O

**问题**：R1 + R2 + R3 各读了 `rubric_calibrate.py`（4次）和 `rubric_calibrate_test.py`（1次），3 份重复 I/O。

**优化**：
- 预知要读的文件，在 prompt 中直接 embed 关键代码段
- 或使用 chain 的 shared artifact 机制

**实现**：_chain.json Phase 1 reviewer task 的 `{files}` 参数填充 + `reads` 预加载

---

## 时间收益汇总

| 优化 | 节省 | 证据 |
|------|------|------|
| wait(all) | ~45s | 串行等待总和 |
| R1 合成 | ~60s | 减少 2 个冗余 review |
| Worker 规划 | ~30s | 14 edits → 3 |
| Reviewer 3KB | ~30s | 减少 ~90KB 处理 |
| **合计** | **~165s** | **~2.75min** |

---

## 产物

| 文件 | 说明 |
|------|------|
| `.pi/chains/review-fix-loop.chain.json` | 可执行的优化编排链 |
| `.pi/chains/review-fix-loop.chain.md` | Chain 骨架文档 |
| `docs/superpowers/plans/trajectory-optimization-analysis.md` | 本分析报告 |
