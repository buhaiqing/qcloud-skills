# P0-C: Severity + Recency-Decay Scoring — Design & Plan

> **目标**：升级 retrieval 评分算法，从单一 count 排序 → composite_score = base × severity × decay
> **文件**：`scripts/reflexion_retrieve.py`、`scripts/failure_pattern_extract.py`、`docs/failure-patterns.md`

---

## SPEC

### 1. 评分公式

```
composite_score = base_score × severity_weight × recency_decay
```

| 因子 | 值 | 来源 |
|---|---|---|
| `base_score` | 3.0（skill 精确匹配）\| 2.0（command 子串匹配）\| 过滤 | `load_failure_patterns()` |
| `severity_weight` | 3.0 critical / 2.0 major / 1.0 minor | 新字段 `severity` |
| `recency_decay` | 1.0 <7d / 0.7 7-30d / 0.3 30-90d / 0.1 >90d / 1.0 unknown | `last_seen` |

**阈值**：composite_score < 2.0 的 pattern 不返回（需至少 base=2 且其中一因子 >1）

### 2. Severity 枚举

| 值 | 触发条件 | 来源 |
|---|---|---|
| `critical` | Safety=0（凭证泄露、破坏性操作无确认）| GCL trace `failure_pattern.severity` |
| `major` | Correctness=0 或 Idempotency=0 | 同上 |
| `minor` | 其他 rubric 失败 | 默认值 |

### 3. 新字段

| 文件 | 新增字段 | 用途 |
|---|---|---|
| `docs/failure-patterns.md` | `LastSeen`、`Severity` 列 | 存储每条 pattern 的最近命中时间和严重性 |
| `failure_pattern_extract.py` `parse_existing()` | `last_seen`、`severity` | 解析时提取 |
| `failure_pattern_extract.py` `merge()` | `last_seen = now` | 每次合并时更新为当前时间 |
| `failure_pattern_extract.py` `enforce_line_cap()` | `last_seen`、`severity` 列 | 写入时输出 |
| GCL trace schema | `failure_pattern.severity` | 新增字段声明 |

### 4. Recency 计算

`last_seen` 格式：`YYYY-MM`（兼容旧数据）或 `YYYY-MM-DD`。
解析时优先取 `last_seen`，fallback 到 `first_seen`。
未知 → decay=1.0（不惩罚现有数据）。

### 5. 输出格式（injection）

旧：
```
- [skill] error=`...` -> fix=`...` (count=N)
```

新：
```
- [skill] error=`...` -> fix=`...` (count=N, last_seen=YYYY-MM [⚠️ severity])
```

JSON 输出额外包含 `_score`、`_severity_weight`、`_recency_decay`。

---

## PLAN

### Phase 1: 数据层（failure_pattern_extract.py）

- [x] `parse_existing()`：新增 `last_seen`（fallback first_seen）、`severity` 字段解析 ✅
- [x] `merge()`：每次合并时设置 `last_seen = now` ✅
- [x] `enforce_line_cap()`：表头新增 `LastSeen`、`Severity` 列；行输出包含这两个字段 ✅

### Phase 2: 查询层（reflexion_retrieve.py）

- [x] 新增 `_parse_severity()` 函数 ✅
- [x] 新增 `recency_decay()` 函数（接受 `YYYY-MM` 或 `YYYY-MM-DD`）✅
- [x] `load_failure_patterns()`：重写评分逻辑 ✅
- [x] `format_for_injection()`：输出新增 `last_seen` + `severity` 标签 ✅
- [x] JSON 模式输出增加 `_score`、`_severity_weight`、`_recency_decay` ✅

### Phase 3: 数据迁移（failure-patterns.md）

- [x] 所有表头增加 `LastSeen`、`Severity` 列 ✅
- [x] AuthFailure 类 → `major`；CamNoAuth → `critical`；其余 → `minor` ✅
- [x] `LastSeen` 列默认值 `—`（历史数据无命中时间）✅

### Phase 4: GCL trace schema

- [x] `docs/failure-patterns.md` Usage 区块：新增 `severity` 字段声明 ✅
- [x] `docs/gcl-spec.md`：trace schema 示例新增 `severity` 字段 ✅
- [x] `gcl_runner.py`：`extract_failure_pattern()` 新增 `_derive_severity()` 并写入 severity ✅

### Phase 5: 验证

- [x] `reflexion_retrieve_test.py`：6/6 ✅
- [x] `failure_pattern_extract_test.py`：17/17 ✅
- [x] `reflexion_store_test.py`：10/10 ✅
- [x] `gcl_runner_test.py`：35/35 ✅
- [x] `ruff check`：0 errors ✅
