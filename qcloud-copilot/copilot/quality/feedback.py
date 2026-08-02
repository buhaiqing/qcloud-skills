"""P0-2 检测质量反馈闭环（Detection Quality Feedback Loop）。

设计见 docs/superpowers/specs/detection-quality-feedback-design.md。本模块在
finding/envelope 之上建立检测质量的度量与反馈闭环：

- ``ReviewOutcome``：人工评审结果枚举（confirmed/false_positive/false_negative/inconclusive）。
- ``record_outcome``：以 finding_id 幂等写回 JSONL（重复提交更新而非重复插入）。
- ``QualityMetrics`` / ``compute_metrics``：按 rule/model/product/tenant 维度聚合
  precision/recall/noise/late/mttd/confirm/calibration_error。
- ``TuningRecommendation`` / ``tune_recommendation``：生成只读调优建议（不落地）。
- ``apply_recommendation``：需审批 token 才放行；无 token 一律拒绝（不落地生产规则）。

Schema version: 0.1
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from statistics import mean
from typing import Any

# 审批 token 白名单仅来自环境变量；未设置时**失败关闭**（拒绝一切 token）。
# 生产环境必须设置 QUALITY_FEEDBACK_APPROVAL_TOKENS，否则无法通过审批。
APPROVAL_TOKENS_ENV = "QUALITY_FEEDBACK_APPROVAL_TOKENS"

DEFAULT_STORE_PATH = "audit-results/quality-feedback.jsonl"

# OutcomeRecord 完整字段集。issue_start_at 作为 MTTD（平均提前发现时间）锚点。
FIELDS = (
    "finding_id",
    "trace_id",
    "rule",
    "model",
    "product",
    "tenant_id",
    "outcome",
    "detected_at",
    "confirmed_at",
    "issue_start_at",
    "severity",
    "confidence",
    "correctness",
)
# 必填字段（record_outcome 强制校验）。
REQUIRED_FIELDS = ("finding_id", "outcome")


def _import_sensitive_key_re() -> re.Pattern:
    """复用 scripts/evidence_kernel.SENSITIVE_KEY_RE，避免重复定义脱敏正则。

    该模块位于 ROOT/scripts/（无包 __init__.py），导入时把 scripts 目录加入
    sys.path。若环境无法导入（如剥离 scripts 的部署），回退到等价内置正则，
    保证相同脱敏语义。
    """
    try:
        # feedback.py 位于 <root>/qcloud-copilot/copilot/quality/，root = parents[3]；
        # evidence_kernel 在 <root>/scripts/。
        _scripts_dir = str(Path(__file__).resolve().parents[3] / "scripts")
        if _scripts_dir not in sys.path:
            sys.path.insert(0, _scripts_dir)
        from evidence_kernel import SENSITIVE_KEY_RE  # type: ignore

        return SENSITIVE_KEY_RE
    except ImportError:  # pragma: no cover - 回退路径，正常环境走上面分支
        return re.compile(
            r'((?:AKID|secretId|secretKey)["\s:=]*)([A-Za-z0-9_\-]{8,})', re.IGNORECASE
        )


# 记录写盘前脱敏：仅掩蔽 token 段，保留键名（复用 evidence_kernel）。
SENSITIVE_KEY_RE = _import_sensitive_key_re()


class ReviewOutcome(str, Enum):
    """人工评审结果：区分真实命中/误报/漏报/不确定。"""

    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    FALSE_NEGATIVE = "false_negative"
    INCONCLUSIVE = "inconclusive"


@dataclass
class QualityMetrics:
    """按维度聚合出的检测质量指标。"""

    precision: float  # TP / (TP + FP)
    recall: float  # TP / (TP + FN)
    noise_rate: float  # FP / total
    late_rate: float  # FN / total
    avg_mttd_hours: float  # 平均提前发现时间
    avg_confirm_mins: float  # 平均人工确认耗时
    calibration_error: float  # mean |confidence - correctness|
    n: int


@dataclass
class TuningRecommendation:
    """阈值/窗口/规则调优建议（只读，不落地）。"""

    rule: str
    dimension: str  # threshold|window|rule
    current: str
    suggested: str
    rationale: str
    impact: str
    approval_required: bool = True
    version: str = ""


def _approval_tokens() -> set[str]:
    """解析审批 token 白名单（仅环境变量；失败关闭）。

    未设置或为空时返回空集 → 任何 token 都判为非法（apply_recommendation 返回 False）。
    """
    env = os.environ.get(APPROVAL_TOKENS_ENV)
    if not env:
        return set()
    return {t.strip() for t in env.split(",") if t.strip()}


def _sanitize(record: dict) -> dict:
    """返回脱敏副本：仅掩蔽凭据 token 段，绝不整字段抹除。

    复用 SENSITIVE_KEY_RE.sub(r"\\1<masked>", ...) 于整条 JSON 序列化文本
    （与 evidence_kernel.mask_trace 同构）：键名+值保留，仅 token 值被掩蔽。
    `{"rule":"secret-scanning"}` 这类合法值保持原样。
    """
    text = json.dumps(record, ensure_ascii=False)
    text = SENSITIVE_KEY_RE.sub(r"\1<masked>", text)
    return json.loads(text)


def _allowed_root() -> Path:
    """store_path 的允许根目录：<worktree>/audit-results。"""
    return Path(__file__).resolve().parents[3] / "audit-results"


def _validate_store_path(path: Path) -> None:
    """校验 store_path 不越界：拒绝 `..` 穿越与允许根之外的位置。

    允许根 = <worktree>/audit-results（默认）。显式路径若含 `..` 组件，或
    resolve 后落在允许根之外，一律 ValueError。相对路径按当前工作目录解析。
    """
    if ".." in path.parts:
        raise ValueError(f"store_path must not contain '..': {path}")
    allowed = _allowed_root()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    try:
        path.resolve().relative_to(allowed)
    except ValueError as e:
        raise ValueError(f"store_path outside allowed root {allowed}: {path}") from e


def _validate(record: dict) -> None:
    for field in REQUIRED_FIELDS:
        if not record.get(field):
            raise ValueError(f"required field {field!r} is missing or empty")
    outcome = record.get("outcome")
    if outcome not in {o.value for o in ReviewOutcome}:
        raise ValueError(
            f"invalid outcome {outcome!r} (expected one of "
            f"{[o.value for o in ReviewOutcome]})"
        )


def record_outcome(record: dict, *, store_path: str | None = None) -> str:
    """以 finding_id 幂等写回一条评审结果到 JSONL。

    Args:
        record: 含 finding_id/outcome 等字段的评审记录字典。
        store_path: JSONL 路径；None 用默认 audit-results/quality-feedback.jsonl。
            必须位于 <worktree>/audit-results 允许根内，禁止 `..` 穿越。

    Returns:
        finding_id（用于审计追踪）。

    Raises:
        ValueError: outcome 非法、缺少必填字段，或 store_path 越界。
    """
    _validate(record)
    path = Path(store_path or DEFAULT_STORE_PATH)
    _validate_store_path(path)
    if path.exists():
        try:
            lines = path.read_text(encoding="utf-8").strip().splitlines()
        except OSError:
            lines = []
    else:
        lines = []

    finding_id = record["finding_id"]
    new_line = json.dumps(_sanitize(record), ensure_ascii=False)

    kept: list[str] = []
    replaced = False
    for line in lines:
        if not line.strip():
            continue
        try:
            existing = json.loads(line)
        except json.JSONDecodeError:
            kept.append(line)
            continue
        if existing.get("finding_id") == finding_id:
            kept.append(new_line)  # 更新旧行，不重复插入
            replaced = True
        else:
            kept.append(line)

    if not replaced:
        kept.append(new_line)

    if not path.parent.is_dir():
        path.parent.mkdir(parents=True, exist_ok=True)
    # 原子写入：写临时文件后 os.replace 原子替换到目标，避免读-写中断损坏 JSONL。
    fd, tmp = tempfile.mkstemp(dir=str(path.parent) or ".", suffix=".jsonl")
    try:
        with open(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(kept) + ("\n" if kept else ""))
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)

    return finding_id


def _parse_ts(value: Any) -> datetime | None:
    """解析时间戳并统一为 UTC-aware datetime。

    无时区的 naive 时间戳按 UTC 处理（replace(tzinfo=UTC)），避免与 aware
    时间戳相减时抛出 "can't subtract offset-naive and offset-aware" 异常。
    """
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value)
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _group_records(records: list[dict], by: str) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for r in records:
        key = r.get(by)
        if not key:
            key = "unknown"
        groups.setdefault(str(key), []).append(r)
    return groups


def _compute_group(group: list[dict]) -> QualityMetrics:
    n = len(group)
    tp = sum(1 for r in group if r.get("outcome") == ReviewOutcome.CONFIRMED.value)
    fp = sum(1 for r in group if r.get("outcome") == ReviewOutcome.FALSE_POSITIVE.value)
    fn = sum(1 for r in group if r.get("outcome") == ReviewOutcome.FALSE_NEGATIVE.value)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    noise_rate = fp / n if n else 0.0
    late_rate = fn / n if n else 0.0

    mttd_hours: list[float] = []
    confirm_mins: list[float] = []
    for r in group:
        detected = _parse_ts(r.get("detected_at"))
        confirmed = _parse_ts(r.get("confirmed_at"))
        if detected and confirmed:
            confirm_mins.append((confirmed - detected).total_seconds() / 60.0)
        start = _parse_ts(r.get("issue_start_at"))
        if start and detected:
            mttd_hours.append((detected - start).total_seconds() / 3600.0)

    calib: list[float] = []
    for r in group:
        conf = r.get("confidence")
        corr = r.get("correctness")
        if conf is None:
            continue  # confidence 缺失 → 跳过校准误差
        if corr is None:
            corr = 1.0 if r.get("outcome") == ReviewOutcome.CONFIRMED.value else 0.0
        calib.append(abs(float(conf) - float(corr)))

    return QualityMetrics(
        precision=precision,
        recall=recall,
        noise_rate=noise_rate,
        late_rate=late_rate,
        avg_mttd_hours=mean(mttd_hours) if mttd_hours else 0.0,
        avg_confirm_mins=mean(confirm_mins) if confirm_mins else 0.0,
        calibration_error=mean(calib) if calib else 0.0,
        n=n,
    )


def compute_metrics(records: list[dict], *, by: str = "rule") -> dict[str, QualityMetrics]:
    """按维度聚合检测质量指标。

    Args:
        records: 评审记录列表（record_outcome 的入参形状）。
        by: 聚合维度，rule/model/product/tenant_id 之一。

    Returns:
        {维度值: QualityMetrics}。
    """
    if by not in {"rule", "model", "product", "tenant_id"}:
        raise ValueError(f"unsupported dimension {by!r}")
    groups = _group_records(records, by)
    return {key: _compute_group(group) for key, group in groups.items()}


def tune_recommendation(
    metrics: QualityMetrics, *, rule: str, threshold_ctx: dict
) -> TuningRecommendation:
    """基于指标生成阈值/窗口/规则调优建议（只读，不落地）。

    纯规则启发式：噪声率过高建议上调阈值；漏报率过高建议收窄窗口/下调阈值。
    """
    current = threshold_ctx.get("current", "N/A")
    if metrics.noise_rate > 0.3:
        return TuningRecommendation(
            rule=rule,
            dimension="threshold",
            current=str(current),
            suggested="raise_threshold",
            rationale=f"noise_rate {metrics.noise_rate:.2f} exceeds 0.3 threshold",
            impact="expected to lower noise_rate and raise precision",
        )
    if metrics.late_rate > 0.3:
        return TuningRecommendation(
            rule=rule,
            dimension="window",
            current=str(current),
            suggested="widen_window",
            rationale=f"late_rate {metrics.late_rate:.2f} exceeds 0.3 threshold",
            impact="expected to lower late_rate and raise recall",
        )
    return TuningRecommendation(
        rule=rule,
        dimension="rule",
        current=str(current),
        suggested="no_change",
        rationale=f"metrics within tolerance (noise {metrics.noise_rate:.2f}, late {metrics.late_rate:.2f})",
        impact="no expected change",
    )


def apply_recommendation(rec: TuningRecommendation, *, approval_token: str) -> bool:
    """审批门禁：需合法审批 token 才放行建议落地。

    不实际修改生产规则；仅当 token 非空且在允许列表时返回 True 表示审批通过。
    """
    if not approval_token:
        return False
    return approval_token in _approval_tokens()
