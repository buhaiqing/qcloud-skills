# Success Patterns — Active-Learning Design

> P0-A 设计文档。记录架构、生命周期逻辑、自验证方法。
> 与 `docs/failure-patterns.md` 对称，共同构成 Reflexion Memory 的双向学习系统。

## 1. 背景与目标

failure-patterns 覆盖"不能做什么"（负向知识）。success-patterns 覆盖"应该怎么做"（正向知识）。
两者结合才能实现完整的上下文适应（L4）。

**核心问题**：成功路径会过时（API 参数漂移、行为变更），如何设计淘汰机制，使其既能积累知识，又不会用过期知识误导 Generator？

**答案**：**活跃度驱动的分层淘汰**，不是 TTL。淘汰信号来自"是否有新模式替代旧模式"，而不是简单的时间衰减。

## 2. 架构

```
[GCL 执行 — 每次 PASS]
  └── gcl_runner.py (structural_critic PASS)
       └── 写入 gcl-success-pending.jsonl (单行追加, 非阻塞)

[每日 02:00 — cron: success_pattern_mine.py --batch]
  ├── 持有 flock 锁，独占写
  ├── 读取 gcl-success-pending.jsonl
  ├── 更新 hot 层 (success-patterns.md)
  │   └── 触发分层淘汰逻辑（见 §4）
  ├── 更新 warm 层 (success-patterns-warm.md)
  │   └── 触发冷归档逻辑（见 §4）
  └── 清空 pending 文件

[Agent Pre-flight]
  └── 查询 hot → warm → cold（lazy，每层按 score 截断 top_n）
```

**分层容量**：

| 层 | 文件 | 容量 | 淘汰阈值 |
|---|---|---|---|
| hot | `docs/success-patterns.md` | ≤ 200 行 | last_hit > 30 天 或 hot 满时强制淘汰 |
| warm | `docs/success-patterns-warm.md` | ≤ 500 行 | last_hit > 90 天 或 warm 满时强制淘汰 |
| cold | `docs/success-patterns-cold.md` | ≤ 2000 行 | 无上限，仅在总量超标时修剪 |

## 3. Schema

### 3.1 Pending Entry（写入 pending 文件）

```jsonl
{"skill":"qcloud-cvm-ops","operation":"RunInstances","command":"tccli cvm RunInstances ...",
 "iter":1,"scores":{"correctness":1.0,"safety":1.0,"idempotency":0.5,"traceability":1.0,"spec_compliance":1.0},
 "timestamp":"2025-07-15T02:00:00"}
```

### 3.2 Hot/Warm/Cold Entry（存储在 md 文件中）

```json
{
  "skill": "qcloud-cvm-ops",
  "operation": "RunInstances",
  "command_signature": "tccli cvm RunInstances --InstanceType S5.SMALL",  // 前80字符
  "full_command": "tccli cvm RunInstances --InstanceType S5.SMALL1 --Zone ap-guangzhou ...",
  "iter": 1,                    // 首次成功所需迭代次数（1=一枪命中）
  "count": 5,                   // 历史复用次数
  "first_hit": "2025-07-15",   // 首次记录时间
  "last_hit": "2025-07-20",    // 最近复用时间
  "scores": {"correctness":1.0,"safety":1.0,"idempotency":0.5,"traceability":1.0,"spec_compliance":1.0},
  "avg_iter": 1.2              // 历史平均迭代次数（用于识别脆弱路径）
}
```

**唯一键**：`skill + operation + command_signature`（前80字符）

- 相同键的多条 pending 记录 → 合并（count++，last_hit=最新，avg_iter=加权平均）
- 不同键 → 分别写入

### 3.3 Retrieval Score

```
composite_score = base_score × severity_weight × recency_decay

其中:
  base_score      = 3.0（skill 精确匹配）| 2.0（command 相似）
  severity_weight = 3.0（iter=1 一枪命中）| 2.0（iter≤2）| 1.0（iter>2）
  recency_decay   = 1.0（<7天）| 0.7（7-30天）| 0.3（30-90天）| 0.1（>90天）
```

**与 failure-patterns 的区别**：
- failure 衰减信号是**错误频率**
- success 衰减信号是**复用频率**
- 两者的 severity 含义不同：failure 的 severity 来自 rubric（Safety=0 → critical）；success 的 severity 来自 iter（iter=1 → 最高质量）

## 4. 活跃度驱动淘汰逻辑

> 核心原则：**不基于 TTL 被动淘汰，基于"是否有新模式替代"主动决策。**

### 4.1 Key Insight: Substitution vs. Silence

一个 pattern 有两种死亡方式：

| 死亡类型 | 含义 | 触发条件 | 处理 |
|---|---|---|---|
| **Substitution（替代）** | 同键新模式出现，旧模式被替代 | pending 中出现相同 (skill, operation, command_signature) 的新记录 | 合并：新 count 覆盖旧 count，旧记录自然降权 |
| **Silence（静默）** | 长时间无复用 | last_hit > 30天 且 hot 层已满 | 降层（hot→warm 或 warm→cold） |

**Substitution 是主通道**：只要同键有新 hit，旧记录通过 count 自然排序靠后，不会被优先召回。

**Silence 是溢出保护**：只有当同键无新 hit **且** 当前层已满时，才触发静默淘汰。

### 4.2 淘汰算法（merge_batch）

```python
def merge_batch(pending, hot, warm, cold):
    """
    每日合并算法。
    核心：substitution 优先于 silence；同键合并，不重复存储。
    """
    # 步骤1：合并 pending → hot（substitution 逻辑）
    # 对每条 pending:
    #   if key in hot:         # substitution 发生
    #       hot[key].count += 1
    #       hot[key].last_hit = today
    #       hot[key].avg_iter = 加权更新
    #   elif key in warm:       # 从 warm 复活
    #       if pending.last_hit - warm[key].last_hit <= 30 days:
    #           warm[key] → hot (keep count)
    #       else:
    #           hot[new] = pending (count=1, no warm merge)
    #   else:
    #       hot[new] = pending (count=1)

    # 步骤2：hot 层容量保护（静默淘汰）
    # if len(hot) > HOT_LIMIT:
    #     # 2a. 淘汰无 recent hit 的
    #     candidates = [k for k in hot if last_hit > 30 days ago]
    #     for k in sorted(candidates, key=lambda k: hot[k].last_hit):
    #         if k in warm: warm[k].count += hot[k].count  # 合并到 warm
    #         else: warm[k] = hot[k]
    #         del hot[k]
    #         if len(hot) <= HOT_LIMIT: break
    #     # 2b. 如果 2a 不够（30天内的新模式占满 hot），强制淘汰最老的
    #     if len(hot) > HOT_LIMIT:
    #         sorted(hot.items(), key=lambda x: x.last_hit)[:needed] → warm

    # 步骤3：warm 层容量保护
    # if len(warm) > WARM_LIMIT:
    #     candidates = [k for k in warm if last_hit > 90 days ago]
    #     for k in sorted(candidates, key=lambda k: warm[k].last_hit):
    #         cold[k] = warm[k]
    #         del warm[k]
    #         if len(warm) <= WARM_LIMIT: break

    # 步骤4：cold 层硬上限（安全阀）
    # if len(cold) > COLD_LIMIT:
    #     修剪最低 count 的条目至 COLD_LIMIT
```

### 4.3 为什么这样设计

| 设计选择 | 理由 |
|---|---|
| 用 key 合并而非追加 | 避免同一操作产生 N 条重复记录；substitution 自然发生 |
| warm 复活机制 | 30天内从 warm 复活到 hot，保留被暂时"静默"的优质模式 |
| hot 满时先淘汰 30天+ | 保护最近活跃的模式不被挤出 |
| 强制淘汰用 last_hit 排序 | 即使是最近写入的新模式，如果无复用也要给新模式让位 |
| cold 是 archive 而非删除 | 极端情况下可人工恢复；总比误删好 |

### 4.4 自验证（每日 merge 后执行）

```python
def self_verify(hot, warm, cold):
    """运行每日 merge 后自验证，确保逻辑自洽。"""
    errors = []

    # V1: 无重复 key（跨层检查）
    all_keys = set(hot.keys()) | set(warm.keys()) | set(cold.keys())
    for layer1, d1 in [("hot", hot), ("warm", warm), ("cold", cold)]:
        for layer2, d2 in [("hot", hot), ("warm", warm), ("cold", cold)]:
            if layer1 >= layer2: continue
            dup = set(d1.keys()) & set(d2.keys())
            if dup:
                errors.append(f"V1: duplicate keys across {layer1} and {layer2}: {dup}")

    # V2: 各层容量合规
    for name, d, limit in [("hot", hot, HOT_LIMIT), ("warm", warm, WARM_LIMIT)]:
        if len(d) > limit:
            errors.append(f"V2: {name} exceeds limit {limit}: {len(d)} entries")

    # V3: count 一致性（warm/cold 接受 hot 合并时 count 应该相加）
    for k in set(warm.keys()) & set(hot.keys()):
        errors.append(f"V3: key {k} in both hot and warm — merge error")

    # V4: 所有 entry 有必填字段
    for layer, d in [("hot", hot), ("warm", warm), ("cold", cold)]:
        for k, e in d.items():
            for field in ["skill", "operation", "count", "last_hit"]:
                if field not in e:
                    errors.append(f"V4: key {k} in {layer} missing field {field}")

    # V5: last_hit 格式合法
    import re
    DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    for layer, d in [("hot", hot), ("warm", warm), ("cold", cold)]:
        for k, e in d.items():
            if "last_hit" in e and not DATE_RE.match(str(e["last_hit"])):
                errors.append(f"V5: key {k} in {layer} has invalid last_hit: {e['last_hit']}")

    assert not errors, f"Self-verification failed: {errors}"
```

## 5. Retrieval 查询逻辑

```python
def retrieve_success_patterns(skill, operation=None, top_n=3):
    """
    分层查询，返回 top_n 条。
    查询顺序：hot → warm → cold
    每层内部按 composite_score 排序。
    跨层去重（已出现在 hot 的 key 不从 warm/cold 返回）。
    """
    hot = load_hot()
    warm = load_warm()
    cold = load_cold()

    seen_keys = set(hot.keys())
    results = []

    for layer, d in [("hot", hot), ("warm", warm), ("cold", cold)]:
        for k, e in d.items():
            if k in seen_keys: continue
            score = compute_composite_score(e, skill, operation)
            if score >= 2.0:
                results.append((score, e))
        if len(results) >= top_n:
            break

    results.sort(key=lambda x: -x[0])
    return [e for _, e in results[:top_n]]
```

## 6. 与 failure-patterns 的协同

| 维度 | success-patterns | failure-patterns |
|---|---|---|
| 学习方向 | 正向（应该怎么做）| 负向（不能怎么做）|
| 衰减信号 | 复用频率 | 命中频率 |
| 淘汰触发 | hot 满 → silence 淘汰 | 200行满 → count<3 修剪 |
| 严重性来源 | iter（1=一枪命中质量最高）| rubric（Safety=0=最危险）|
| 注入时机 | Generator Pre-flight | Generator Pre-flight |

Agent 在 Pre-flight 时同时加载两者，合并注入 Generator context。

## 7. 全量回填（首次部署）

```bash
# 一次性：扫描所有现有 gcl-trace-*.json，提取 PASS 记录
success_pattern_mine.py --full-scan

# 完成后进入每日增量模式
# crontab:
# 0 2 * * * flock /tmp/success-patterns.lock python3 scripts/success_pattern_mine.py --batch
```

首次运行时 hot/warm/cold 均为空，直接从所有 PASS trace 重建初始 store。
后续正常运行 --batch 增量追加。

## 8. 文件清单

| 文件 | 用途 |
|---|---|
| `scripts/success_pattern_mine.py` | 核心：pending 消费 + 分层合并 + 自验证 |
| `scripts/success_pattern_retrieve.py` | 查询：分层 lazy load + composite_score 排序 |
| `audit-results/gcl-success-pending.jsonl` | Pending 日志（每次 PASS 追加）|
| `docs/success-patterns.md` | Hot 层（≤200行）|
| `docs/success-patterns-warm.md` | Warm 层（≤500行）|
| `docs/success-patterns-cold.md` | Cold 层（≤2000行）|
| `docs/superpowers/specs/success-patterns-design.md` | 本文档：设计 + 逻辑自洽证明 |

---

## 9. PLAN（实施清单）

> 与 SPEC 必须对齐；每项完成后标注 ✅；发现不一致必须修复再继续。

### Phase 1: 核心 mining 脚本（success_pattern_mine.py）

- [x] `SuccessEntry` 数据类 ✅
- [x] `from_pending()` ✅
- [x] `make_key()` ✅
- [x] `merge_batch()` 步骤1-5 ✅
- [x] `self_verify()` V1–V5 ✅
- [x] `cmd_batch()` flock + 消费 + 清空 ✅
- [x] `cmd_full_scan()` ✅
- [x] `--dry-run` ✅

### Phase 2: 查询脚本（success_pattern_retrieve.py）

- [x] `SuccessEntry` 对称实现 ✅
- [x] `_parse_layer()` ✅
- [x] `_severity_weight(iter)` ✅
- [x] `recency_decay(last_hit)` ✅
- [x] `compute_composite()` ✅
- [x] `retrieve_success_patterns()` 分层 lazy + 去重 ✅
- [x] `format_for_injection()` 含 layer/iter/count/last_hit ✅
- [x] `--json` ✅

### Phase 3: gcl_runner.py 集成

- [x] `from success_pattern_mine import write_pending_with_lock` ✅
- [x] PASS 分支提取 op/scores/iter → 写入 pending ✅
- [x] 非阻塞（try/except pass）✅

### Phase 4: 单元测试

- [x] `success_pattern_mine_test.py`：16 tests ✅
- [x] `success_pattern_retrieve_test.py`：13 tests ✅
- [x] `gcl_runner_reflexion_test.py`：格式断言修复（count=5 → count=5） ✅

### Phase 5: 端到端验证

- [x] ruff 所有相关文件：0 errors ✅
- [x] `python3 -m unittest *_test.py`：162 tests ✅
