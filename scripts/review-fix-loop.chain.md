---
name: review-fix-loop
package: qcloud-optimized
description: Optimized GCL review-fix loop: parallel reviewers → synthesis → fork worker → parallel validation
---

# Optimized Review-Fix Loop

## 优化点
1. **并行 launch 3 reviewer** + `wait({ all: true })` — 省串行等待 ~45s
2. **R1 先跑，合成就发 R2/R3** — 减少重复发现
3. **fix-worker 读全部 → 规划 → 一次性 edit** — 减少 10次→3次
4. **reviewer 输出限 3KB** — 减少 ~90KB 总输出
5. **reviewer 预载共享文件** — 省重复 I/O

## Chain

### Phase 1: 并行 Review（R1-R3，max 3 concurrent）
Parallel fanout, fresh context, distinct angles:

- **R1 正确性**: correctness/regression/edge-cases
- **R2 测试+lint**: test coverage/validation/evidence gate
- **R3 Ponytail**: over-engineering/token-efficiency/simplicity

每个 reviewer:
- 读文件直接来自 disk（不要依赖父会话历史）
- 输出限 **3KB 结构化摘要**（BLOCKERS / WARNINGS / PRAISE 三段）
- `outputMode: file-only` 避免 inline 冗长报告

### Phase 2: 合成（父 Agent）
- 读 3 个 reviewer 输出文件
- 合并 BLOCKERS → 必须修
- 合并 WARNINGS → 可选修
- 判断是否需要 fix-worker（无 BLOCKER + 无 WARNINGS → 跳过）

### Phase 3: Fix Worker（fork context，单 writer）
- 读所有 reviewer findings
- **先读完整文件并规划** → 再一次性 edit
- 验证：ruff + tests + self-verify
- 报告：改了哪些文件、命令退出码、剩余问题

### Phase 4: 验证 Round（如 fix-worker 有改动）
- 并行 2 个 reviewer 验证修复结果
- 确认无新 blocker
- 剩余 optional → 记录 deferred

### Stop Rules
- reviewers 无 BLOCKER + 无 WARNINGS → stop
- max 3 review rounds → stop
- 剩余全 optional/deferred → stop

## Phase 清单

- [ ] **Phase 1**: 并行 launch 3 reviewer（outputMode: file-only）
- [ ] **Phase 2**: 父 Agent 合成 findings，决定是否需要 fix-worker
- [ ] **Phase 3**: fix-worker（fork，read-all → plan → edit-once）
- [ ] **Phase 4**: 验证 round（如有修复）
- [ ] **Phase 5**: 记录 deferred items，停止
