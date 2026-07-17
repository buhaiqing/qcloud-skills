# P0-B: Failure Patterns Layered Storage — Design & Plan

> 将 `docs/failure-patterns.md`（单层 ≤200 行）升级为三层分层存储。
> 与 `docs/success-patterns.md`（success-patterns-design.md §2）架构对称。
> **设计原则**：活跃度驱动淘汰，Substitution 优先于 Silence。

---

## 1. 背景与动机

当前 `failure-patterns.md` 是单层 ≤200 行：
- 新 pattern 持续追加 → 200 行满 → count<3 的低频 pattern 被修剪
- **问题**：count=2 的 pattern 可能是重要但不常见的错误（如 `AuthFailure.CamNoAuth`），被修剪后下次遇到仍然会失败

**解法**：三层分层，让高价值低频 pattern 有更长存活窗口。

---

## 2. 架构

```
写入（failure_pattern_extract.py --since-hours 168）
  └── 合并 pending traces
       └── 写入 hot 层
            └── 触发分层淘汰逻辑（见 §3）

读取（reflexion_retrieve.py）
  └── 查询 hot → warm → cold（lazy，每层按 score 截断 top_n）
       └── 跨层去重（已出现在 hot 的 key 不从 warm/cold 返回）
```

**三层容量**：

| 层 | 文件 | 容量 | 淘汰条件 |
|---|---|---|---|
| hot | `docs/failure-patterns.md` | ≤ 200 行 | last_seen > 30 天 **或** hot 满时强制淘汰 |
| warm | `docs/failure-patterns-warm.md` | ≤ 500 行 | last_seen > 90 天 **或** warm 满时强制淘汰 |
| cold | `docs/failure-patterns-cold.md` | ≤ 2000 行 | 无时间限制，仅容量超标时修剪最低 count |

**与 success-patterns 的对称性**：

| 维度 | success-patterns | failure-patterns |
|---|---|---|
| 活跃信号 | 复用频率（count 增长）| 命中频率（count 增长）|
| 衰减信号 | 长时间无复用 | 长时间无命中 |
| 淘汰触发 | hot 满 → silence 淘汰 | hot 满 → silence 淘汰 |
| 复活机制 | warm ≤30天可复活到 hot | warm ≤30天可复活到 hot |
| 严重性来源 | iter（1=一枪命中最高）| rubric（Safety=0=最危险）|

---

## 3. 淘汰算法

> 核心原则：**Substitution 优先于 Silence；Substitution 通过 count 自然排序实现，不需主动淘汰。**

### 3.1 Key Insight

failure-patterns 的唯一键 = `(skill, command, error)`。
- 同一错误重复出现 → `count++`，自然排序靠前 → 不被淘汰
- 长时间无命中 → count 不增长 → 按 last_seen 排序逐渐下沉

### 3.2 淘汰算法（merge_batch）

```python
def merge_failure_batch(new_patterns, hot, warm, cold):
    """
    new_patterns: 从 failure_pattern_extract.py 提取的失败 pattern
    hot/warm/cold: 当前三层数据

    步骤1：合并 new → hot（substitution）
      if key in hot: count += new.count
      elif key in warm:
          if gap <= 30 days: warm → hot (keep count)
          else: hot[new] = new
      else: hot[new] = new

    步骤2：hot 容量保护（静默淘汰）
      if len(hot) > 200:
          candidates = [k for k in hot if last_seen > 30 days ago]
          evict = sorted(candidates, key=lambda k: hot[k].last_seen)[:needed]
          for k in evict: warm[k] = hot[k]; del hot[k]
          if still over: evict oldest by last_seen

    步骤3：warm → cold（静默淘汰）
      if len(warm) > 500:
          candidates = [k for k in warm if last_seen > 90 days ago]
          evict = sorted(candidates, key=lambda k: warm[k].last_seen)[:needed]
          for k in evict: cold[k] = warm[k]; del warm[k]

    步骤4：cold 硬上限（安全阀）
      if len(cold) > 2000:
          keep = top-2000 by count
```

### 3.3 与 success-patterns 的差异

| 差异维度 | failure-patterns | success-patterns |
|---|---|---|
| 唯一键 | skill + command + error | skill + operation + command_signature |
| 活跃信号 | count 增长（每次命中+1）| count 增长（每次复用+1）|
| 淘汰键 | last_seen（最后命中时间）| last_hit（最后复用时间）|
| 复活条件 | last_seen gap ≤ 30 天 | last_hit gap ≤ 30 天 |

---

## 4. Schema

与现有 `failure-patterns.md` 完全兼容，新增字段：

```json
{
  "category": "cli_parameter",
  "skill": "qcloud-cvm-ops",
  "command": "TerminateInstances",
  "error": "MissingParameter",
  "fix": "--InstanceIds \"[\\\"ins-xxx\\\"]\"",
  "count": 3,
  "severity": "minor",
  "first_seen": "2026-07",
  "last_seen": "2026-07-20"
}
```

---

## 5. 实施清单

### Phase 1: 升级 failure_pattern_extract.py

- [x] HOT=200, WARM=500, COLD=2000 常量 ✅
- [x] `load_all_layers()`: 读取 hot/warm/cold 三个 md 文件 ✅
- [x] `merge_failure_batch()`: §3.2 算法（substitution + silence eviction + cold cap）✅
- [x] `self_verify_failure()` V1-V5（与 success_pattern_mine 对称）✅
- [x] `emit_layer()` + `save_layer()`: 输出 hot/warm/cold 三个文件 ✅
- [x] `--layered` flag 支持（向后兼容单文件模式）✅

### Phase 2: 升级 reflexion_retrieve.py

- [x] `load_all_layers()`: 读取 hot/warm/cold 三个文件 ✅
- [x] 分层 lazy load + 跨层去重（hot 优先） ✅
- [x] `_score_pattern()` 抽取评分逻辑 ✅
- [x] `--layer` flag 支持单层查询 ✅
- [x] reflexion_retrieve.py dry-run 验证通过 ✅

### Phase 3: 迁移现有数据

- [x] `failure-patterns.md` = HOT_PATH（现有文件自动成为 hot 层）✅
- [x] warm/cold 层首次 `--layered` 写入时自动创建（空）✅
- [x] `parse_existing` 向后兼容单文件格式（LastSeen/Severity 列）✅

### Phase 4: 测试

- [x] `failure_pattern_layered_test.py`：17 tests ✅
- [x] `reflexion_retrieve_layered_test.py`：15 tests ✅
- [x] 全量测试 196 ✅

### Phase 5: 端到端验证

- [x] `--dry-run --layered` 正常执行（no traces → expected exit 1）✅
- [x] `reflexion_retrieve.py retrieve` 返回 hot 层数据 ✅
- [x] ruff: 0 errors ✅
- [x] 196 tests pass ✅
- [x] 新增共享模块 `_failure_pattern_store.py`（parse_existing + load_all_layers）✅
