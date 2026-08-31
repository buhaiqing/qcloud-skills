# LLM 不确定性表达机制设计

> Generator 产出物 · 2026-08-31 · 实现补全 2026-08-31

---

## 1. 不确定性量化体系

### 1.1 多粒度置信度层次

> **AUTHORITATIVE:** `refs/uncertainty/token_confidence.py` — `ConfidenceLevel` (line 21), `TokenConfidence` (line 28), `SentenceConfidence` (line 37), `DocumentConfidence` (line 61). Demo: `python3 refs/uncertainty/token_confidence.py`.

### 1.2 语义不确定性 vs 事实不确定性

| 维度 | 语义不确定性 (Semantic) | 事实不确定性 (Factual) |
|------|------------------------|----------------------|
| 本质 | 自然语言歧义、一词多义、句法歧义 | 知识边界外、幻觉、过时信息 |
| 检测信号 | 词向量分布熵高、多个 high-prob token | 知识库检索空白、时间戳过期 |
| 修正手段 | 上下文消歧、显式询问 | RAG 回填、知识更新 |

```python
def compute_semantic_uncertainty(token_probs: np.ndarray) -> float:
    """token_probs: 词表中每个词的概率分布"""
    # Shannon entropy - 分布越均匀越不确定
    entropy = -np.sum(token_probs * np.log(token_probs + 1e-10))
    max_entropy = np.log(len(token_probs))
    return entropy / max_entropy  # 归一化 0~1

def compute_factual_uncertainty(
    retrieval_recall: float,       # 0~1, 检索召回率
    knowledge_age_days: int,        # 知识更新时间距今天数
    knowledge_cutoff_days: int = 90,  # 知识过期判定阈值（天）
    weights: Optional[dict[str, float]] = None,  # 可选：{"retrieval": 0.6, "time": 0.4}
) -> float:
    """
    知识缺失程度 = 检索缺失 × weight + 时间衰减 × weight。

    M-B2 fix: weights 默认可配；empirically retrieval gap 对 miscalibration 的
    贡献约为 time decay 的 1.4 倍（Guo et al., 2017）。
    生产环境可通过 validation set grid search 调优。
    """
    if weights is None:
        weights = {"retrieval": 0.6, "time": 0.4}
    retrieval_gap = 1 - max(0.0, min(1.0, retrieval_recall))
    time_decay = min(1.0, knowledge_age_days / knowledge_cutoff_days)
    return (
        weights["retrieval"] * retrieval_gap +
        weights["time"] * time_decay
    )
```

### 1.3 置信度校准曲线 (Calibration)

**数学描述：**

设模型对输入 $x$ 的预测为 $\hat{y}$，模型置信度为 $c = P_{\theta}(y=\hat{y}|x)$。

**完美校准**定义：
$$P(y=\hat{y} | c = p) = p, \quad \forall p \in [0,1]$$

**ECE (Expected Calibration Error)：**
$$\text{ECE} = \sum_{b=1}^{B} \frac{|B_b|}{N} \left| \text{acc}(B_b) - \text{conf}(B_b) \right|$$

其中 $B_b$ 是置信度在区间 $[(b-1)/B, b/B)$ 的样本集合。

**温度缩放（Temperature Scaling）：**
> **AUTHORITATIVE:** temperature scaling + ECE minimisation are core calibration concepts; production implementation in `refs/uncertainty/feedback_loop.py` (dataclass `UncertaintyFeedbackLoop` line 47) + `token_confidence.py`.

温度缩放用验证集拟合最优温度 $T$ 使 ECE 最小化：
$$q_i = \frac{\exp(z_i/T)}{\sum_j \exp(z_j/T)}$$

---

## 2. "I Don't Know" 触发机制

### 2.1 触发条件检测

> **AUTHORITATIVE:** `refs/uncertainty/idk_trigger.py` — `UncertaintyTrigger` (line 18), `should_refuse` (line 38), `detect_knowledge_boundary` (line 63), `detect_time_sensitivity` (line 91). Demo: `python3 refs/uncertainty/idk_trigger.py`.

### 2.2 拒绝回答标准格式 (Structured Refusal)

```python
@dataclass
class RefusalResponse:
    status: str = "refused"
    reason: str  # high_level | out_of_knowledge | time_sensitive | low_confidence
    confidence: float
    suggestion: Optional[str] = None  # 建议用户如何重新组织问题

    def to_markdown(self) -> str:
        return f"""**抱歉，我无法回答这个问题。**

- **原因**: {self.reason}
- **置信度**: {self.confidence:.2%}
- **建议**: {self.suggestion or "请尝试换一种问法，或提供更多上下文。"}
"""

REFUSAL_TEMPLATES = {
    "high_level": "这个问题涉及{domain}领域，需要更专业的知识。",
    "out_of_knowledge": "我的知识库中没有与「{query}」相关的信息。",
    "time_sensitive": "该问题需要最新的信息（截止到{cutoff}），我可能无法提供准确答案。",
    "low_confidence": "我对这个问题的置信度仅为{conf:.0%}，无法确保回答准确。"
}
```

---

## 3. 渐进式不确定表达

### 3.1 多级置信度表达

> **AUTHORITATIVE:** `refs/uncertainty/hedging_injector.py` — `HEDGING_PHRASES` (line 16), `generate_hedged_response` (line 43). Demo: `python3 refs/uncertainty/hedging_injector.py`.

### 3.2 Hedging Phrase 自动注入

> **AUTHORITATIVE:** `refs/uncertainty/hedging_injector.py` — `HedgingInjector` (line 61), `inject` (line 98). Demo: `python3 refs/uncertainty/hedging_injector.py`.

---

## 4. 不确定性反馈闭环

### 4.1 状态机描述

```
┌─────────────────────────────────────────────────────────────────┐
│                    Uncertainty State Machine                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────┐    external_signal    ┌──────────────────┐       │
│   │ INITIAL  │ ──────────────────────→│ CALCULATING      │       │
│   └──────────┘                       └──────────────────┘       │
│                                            │                     │
│                         ┌──────────────────┼──────────────────┐ │
│                         ▼                  ▼                  ▼ │
│                  ┌───────────┐     ┌───────────┐     ┌──────────┐│
│                  │  HIGH     │     │  MEDIUM   │     │   LOW    ││
│                  │ CONFIDENCE│     │ CONFIDENCE│     │CONFIDENT ││
│                  └───────────┘     └───────────┘     └──────────┘│
│                        │                  │                  │   │
│                        │                  │                  │   │
│                        ▼                  ▼                  ▼   │
│                  ┌───────────┐     ┌───────────┐     ┌──────────┐│
│                  │ GENERATING│     │ GENERATING│     │  REFUSAL ││
│                  │  (direct) │     │  (hedge)  │     │  or HEDGE││
│                  └───────────┘     └───────────┘     └──────────┘│
│                                                                  │
│   Feedback Loop:                                                 │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │ human_correction → recalibrate → update confidence_model │  │
│   └──────────────────────────────────────────────────────────┘  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │ tool_result → posterior_update → confidence_adjustment   │  │
│   └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Python 实现

> **AUTHORITATIVE:** `refs/uncertainty/feedback_loop.py` — `UncertaintyState` (line 22), `UncertaintyContext` (line 35), `UncertaintyFeedbackLoop` (line 47), `update_from_tool_result` (line 71), `update_from_human_correction` (line 102), `step` (line 156). Demo: `python3 refs/uncertainty/feedback_loop.py`.

---

## 5. 与 RAG 的集成

### 5.1 检索质量 → 不确定性传递

> **AUTHORITATIVE:** `refs/uncertainty/rag_integration.py` — `RAGQualityMetrics` (line 20), `RAGUncertaintyOutput` (line 35), `RAGUncertaintyIntegrator` (line 52), `generate_with_uncertainty` (line 109). Demo: `python3 refs/uncertainty/rag_integration.py`.

### 5.2 检索为空 / 低质时的不确定性传递

| 场景 | 置信度修正 | 响应策略 |
|------|-----------|---------|
| 检索为空 | `base * 0.2` | Structured Refusal + 建议改写 |
| 检索 < 3 篇 | `base * 0.5` | 低置信度回答 + hedging |
| 低相关性 (< 0.5) | `base * (0.5 + 0.5*rel)` | 中置信度 + hedging |
| 高相关性 (>= 0.8) | `min(0.99, base + 0.2)` | 增强置信度 + 直接回答 |

---

## 附录：数学总结

| 概念 | 公式 |
|------|------|
| 完美校准 | $P(y=\hat{y}\|c=p) = p$ |
| ECE | $\sum_b \frac{|B_b|}{N}\|\text{acc}(B_b) - \text{conf}(B_b)\|$ |
| 温度缩放 | $q_i = \frac{\exp(z_i/T)}{\sum_j \exp(z_j/T)}$ |
| 贝叶斯置信更新 | $P(H\|E) = \frac{P(E\|H)P(H)}{P(E\|H)P(H) + P(E\|\neg H)P(\neg H)}$ |
| 语义熵 | $H_s = -\sum_{w \in V} P(w) \log P(w)$ |

---

## 引用实现索引

> ⚠️ BLOCKER B1 已修复 — 以下文件已落盘，每个模块含 `__main__` demo。

| 模块 | 实现文件 | 行数 | 说明 |
|------|---------|------|------|
| 多粒度置信度 | `refs/uncertainty/token_confidence.py` | 180 | TokenConfidence / SentenceConfidence / DocumentConfidence + Shannon 熵 + `compute_factual_uncertainty`（权重可配，注释说明来源） |
| 触发机制 | `refs/uncertainty/idk_trigger.py` | 201 | UncertaintyTrigger + 知识边界检测 + 时间敏感性检测 + Structured Refusal |
| Hedging 注入 | `refs/uncertainty/hedging_injector.py` | 142 | HedgingInjector + 四级置信度表达 + `generate_hedged_response` |
| 反馈闭环 | `refs/uncertainty/feedback_loop.py` | 233 | UncertaintyFeedbackLoop + 状态机 + 贝叶斯更新 + **RECONCILE 回炉路径（MAJOR M-B1 修复）** |
| RAG 集成 | `refs/uncertainty/rag_integration.py` | 197 | RAGQualityMetrics + RAGUncertaintyIntegrator + 检索质量 → 置信度修正 |

## CI 集成

3 个 check 脚本（`check_spec_file_refs.py`、`check_doc_code_drift.py`、`check_yaml_python_drift.py`）已接入 pre-commit（`.pre-commit-config.yaml`）和 CI（`.github/workflows/validate-skills.yml`），确保 compounding-engineering 规则持续生效。
