# 性能优化回归验证执行报告

## 测试概述

**测试时间**: 2026-08-02
**测试范围**: 本会话全部性能优化改动后的完整回归验证
**改动范围**:
- 性能修复 #1-#5（tccli 并发化、TopologyGraph O(1) 去重、skill_quality_score 缓存读、gcl_runner 错误码提循环外、trace mtime 预过滤）
- copilot 中优修复（blackboard 读路径、synthesize 双 audience 预计算、P0/P1/P2 单趟 Counter）
- 2 个预存测试问题修复（test_p5_5_fixtures 断言、test_customer_tag_key skip 顺序）
**测试架构**: GCL 质量门禁（2 轮 gcl_batch：3 子任务 + 2 子任务）
**测试结果**: ✅ 全部通过

## 测试套件执行结果

| # | 套件 | 命令 | 结果 |
|---|------|------|------|
| 1 | scripts/ unittest | `python3 -m unittest discover -s . -p "*_test.py"` | **439 tests OK** |
| 2 | copilot pytest | `python3 -m pytest tests/` | **562 passed, 1 skipped** |
| 3 | aiops-diagnosis | `python3 -m pytest tests/` | **75 passed** |
| 4 | proactive-inspection | `python3 -m pytest scripts/test_*.py` | **12 passed** |
| 5 | phase2_ai_models | `python3 -m pytest tests/` | **63 passed** |
| 6 | ruff（全部改动文件） | `ruff check <改动的文件>` | **All checks passed** |

**合计**: 1151 tests passed / 0 failed / 1 skipped（设计性 skip）

## GCL 执行轨迹

### 批次 1 — 性能修复 #1-#5（3 子任务并行）

```
gcl_batch (concurrency=3, preflight PASS)
├── S1: tccli 子进程并发化        → commit df510a6 + 031f2f6 (Critic: 补队列化顺序测试)
├── S2: TopologyGraph + skillscore → commit bc6285c (Critic: PASS 满分)
└── S3: gcl_runner + trace        → commit f6ee4ef + 4f7bf9b (Critic: MAJOR mtime 语义, 已修)
```

### 批次 2 — copilot 中优修复（2 子任务并行）

```
gcl_batch (concurrency=2, preflight PASS)
├── S1: blackboard 读路径          → commit fff487c + 5630f03 (Critic: MAJOR 缺测试 + MINOR 缓存key, 已修)
└── S2: synthesize 双跑 + P0/P1/P2 → commit 15e59c8 (Critic: PASS, 8/8 逐字节一致)
```

## 关键验证点

### 1. Critic 抓到的 MAJOR 及修复

| 子任务 | MAJOR | 修复 |
|--------|-------|------|
| S3 (gcl_runner) | mtime 预过滤改变了无 timestamp trace 的窗口语义 | 补充无 timestamp 边界测试 + 文档化 |
| S1 (blackboard) | commit 零测试改动，核心风险无覆盖 | 新增 5 个读路径回归测试 + 缓存 key 加内容哈希 |

### 2. 回归验证中发现并修复的预存测试问题

| 文件 | 问题 | 修复 |
|------|------|------|
| `test_p5_5_fixtures.py` | 断言 `getattr(e,"error_code")` 检查顶层属性，实际在 metadata，恒为 False | 改为 `(e.metadata or {}).get("error_code")` |
| `test_customer_tag_key.py` | `pytest.skip` 在 import 之后，ImportError 先抛出中断收集 | skip 移到 import 前 |

### 3. 关键证据

- **synthesize 重构**：Critic 独立对比旧版 vs 新版渲染，**8/8 逐字节一致**
- **blackboard 去 deepcopy**：逐一确认所有调用方只读，无污染回归
- **validator 缓存**：内容哈希 key 防同 size+mtime 陈旧 schema 静默生效

## 最终仓库状态

- 本地 main 与 origin/main 同步（`ffc8a66`）
- worktree 已清理，仅剩 main
- 全部改动已推送到远端

## 结论

**回归验证通过。** 所有性能优化改动在功能不回归的前提下完成，完整测试套件 1151 项全部通过。期间通过 Critic 评审和完整回归发现并修复了 2 个预存测试问题（断言错误、skip 顺序错误），copilot 套件从最初「561 passed + 1 failed + 1 collection error」提升为「562 passed + 1 skipped」。
