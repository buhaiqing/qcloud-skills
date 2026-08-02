"""Unit tests for detection quality feedback loop (P0-2).

Covers SPEC §8 Self-check:
  - ReviewOutcome 四值可用
  - record_outcome 幂等（同一 finding_id 更新而非重复）
  - compute_metrics 按维度正确输出 precision/recall/noise/late/mttd/confirm/calib
  - 确定样本的数值精确断言（非仅键存在）
  - tune_recommendation 只读建议；apply_recommendation 无 token 拒绝
  - 校准误差含 confidence 缺失边缘
  - 脱敏：JSONL 不含 SecretId/SecretKey

Run: python3 -m pytest scripts/test_quality_feedback.py -q
     (or) python3 -m unittest scripts.test_quality_feedback
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

sys_path = str(ROOT / "qcloud-copilot")
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from copilot.quality.feedback import (
    QualityMetrics,
    ReviewOutcome,
    TuningRecommendation,
    apply_recommendation,
    compute_metrics,
    record_outcome,
    tune_recommendation,
)


def _record(
    *,
    finding_id: str,
    rule: str = "cvm-cpu-high",
    model: str = "threshold_based",
    product: str = "cvm",
    tenant_id: str = "tenant-01",
    outcome: str = "confirmed",
    detected_at: str | None = None,
    confirmed_at: str | None = None,
    confidence: float | None = 0.9,
    correctness: float | None = 1.0,
) -> dict:
    if detected_at is None:
        detected_at = "2026-08-02T00:00:00Z"
    if confirmed_at is None:
        confirmed_at = "2026-08-02T00:30:00Z"
    return {
        "finding_id": finding_id,
        "trace_id": f"trace-{finding_id}",
        "rule": rule,
        "model": model,
        "product": product,
        "tenant_id": tenant_id,
        "outcome": outcome,
        "detected_at": detected_at,
        "confirmed_at": confirmed_at,
        "severity": "P1",
        "confidence": confidence,
        "correctness": correctness,
    }


class ReviewOutcomeTests(unittest.TestCase):
    def test_four_values(self) -> None:
        self.assertEqual(ReviewOutcome.CONFIRMED.value, "confirmed")
        self.assertEqual(ReviewOutcome.FALSE_POSITIVE.value, "false_positive")
        self.assertEqual(ReviewOutcome.FALSE_NEGATIVE.value, "false_negative")
        self.assertEqual(ReviewOutcome.INCONCLUSIVE.value, "inconclusive")
        values = {o.value for o in ReviewOutcome}
        self.assertEqual(values, {"confirmed", "false_positive", "false_negative", "inconclusive"})

    def test_str_enum(self) -> None:
        self.assertTrue(issubclass(ReviewOutcome, str))
        self.assertEqual(ReviewOutcome.CONFIRMED.value, "confirmed")


class RecordOutcomeTests(unittest.TestCase):
    def _tmp_path(self) -> str:
        # store_path 被限定在 <worktree>/audit-results 允许根内（B3）。测试在其下建临时文件。
        allowed = ROOT / "audit-results"
        allowed.mkdir(parents=True, exist_ok=True)
        fd, path = tempfile.mkstemp(suffix=".jsonl", dir=str(allowed))
        os.close(fd)
        os.unlink(path)
        return path

    def test_record_outcome_returns_finding_id_and_writes_line(self) -> None:
        path = self._tmp_path()
        try:
            rec = _record(finding_id="f-1")
            returned = record_outcome(rec, store_path=path)
            self.assertEqual(returned, "f-1")
            lines = Path(path).read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            data = json.loads(lines[0])
            self.assertEqual(data["finding_id"], "f-1")
            self.assertEqual(data["outcome"], "confirmed")
            self.assertEqual(data["rule"], "cvm-cpu-high")
        finally:
            Path(path).unlink(missing_ok=True)

    def test_idempotent_same_finding_id_updates_not_duplicates(self) -> None:
        path = self._tmp_path()
        try:
            rec1 = _record(finding_id="f-idem", outcome="confirmed")
            rec2 = _record(finding_id="f-idem", outcome="false_positive")
            record_outcome(rec1, store_path=path)
            record_outcome(rec2, store_path=path)
            lines = Path(path).read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1, "same finding_id must update, not duplicate")
            data = json.loads(lines[0])
            self.assertEqual(data["outcome"], "false_positive")
        finally:
            Path(path).unlink(missing_ok=True)

    def test_invalid_outcome_rejected(self) -> None:
        path = self._tmp_path()
        try:
            rec = _record(finding_id="f-bad", outcome="not_a_real_outcome")
            with self.assertRaises(ValueError):
                record_outcome(rec, store_path=path)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_no_credentials_in_jsonl(self) -> None:
        path = self._tmp_path()
        try:
            rec = _record(
                finding_id="f-sec",
                rule="cvm-cpu-high",
                model="AKIDexampleSecretId0123456789",
            )
            # 即使 record 里塞了带 AKID/SecretId 形状的字段，写盘后不得出现明文凭据 token。
            record_outcome(rec, store_path=path)
            blob = Path(path).read_text(encoding="utf-8")
            self.assertNotIn("exampleSecretId0123456789", blob)  # token 值被掩蔽
            self.assertNotIn("AKIDexampleSecretId0123456789", blob)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_path_traversal_store_path_rejected(self) -> None:
        # B3: `..` 穿越与允许根之外的位置必须拒绝。
        rec = _record(finding_id="f-trav")
        with self.assertRaises(ValueError):
            record_outcome(rec, store_path=os.path.join(ROOT, "..", "..", "etc", "x.jsonl"))
        with self.assertRaises(ValueError):
            record_outcome(rec, store_path="/tmp/../../etc/passwd.jsonl")

    def test_store_path_must_be_inside_allowed_root(self) -> None:
        # B3: 允许根之外的绝对路径（如 /tmp）必须拒绝；允许根内通过。
        rec = _record(finding_id="f-root")
        with self.assertRaises(ValueError):
            record_outcome(rec, store_path="/tmp/out-of-root.jsonl")

    def test_mask_only_token_not_whole_field(self) -> None:
        # M1: 合法值 "secret-scanning" 不得被整字段抹除；真实 secretKey token 必须掩蔽。
        rec = _record(
            finding_id="f-mask",
            rule="secret-scanning",
            model="threshold",
        )
        rec["secretKey"] = "abc12345"  # 真实凭据形状
        path = self._tmp_path()
        try:
            record_outcome(rec, store_path=path)
            blob = Path(path).read_text(encoding="utf-8")
            self.assertIn('"rule": "secret-scanning"', blob)  # 合法字段保持原样
            self.assertIn("<masked>", blob)  # 凭据 token 被掩蔽
            self.assertNotIn("abc12345", blob)  # 明文 token 不落盘
            data = json.loads(Path(path).read_text(encoding="utf-8").strip().splitlines()[0])
            self.assertEqual(data["secretKey"], "<masked>")
            self.assertEqual(data["rule"], "secret-scanning")
        finally:
            Path(path).unlink(missing_ok=True)


class ComputeMetricsTests(unittest.TestCase):
    def test_deterministic_sample_by_rule(self) -> None:
        # 4 confirmed + 1 false_positive + 1 false_negative，同一 rule
        records = [
            _record(finding_id="f-1", outcome="confirmed", confidence=1.0, correctness=1.0),
            _record(finding_id="f-2", outcome="confirmed", confidence=1.0, correctness=1.0),
            _record(finding_id="f-3", outcome="confirmed", confidence=1.0, correctness=1.0),
            _record(finding_id="f-4", outcome="confirmed", confidence=1.0, correctness=1.0),
            _record(finding_id="f-5", outcome="false_positive", confidence=0.9, correctness=0.0),
            _record(finding_id="f-6", outcome="false_negative", confidence=None, correctness=None),
        ]
        groups = compute_metrics(records, by="rule")
        self.assertEqual(list(groups.keys()), ["cvm-cpu-high"])
        m: QualityMetrics = groups["cvm-cpu-high"]
        self.assertEqual(m.n, 6)
        self.assertAlmostEqual(m.precision, 4 / 5)  # TP=4, FP=1
        self.assertAlmostEqual(m.recall, 4 / 5)  # TP=4, FN=1
        self.assertAlmostEqual(m.noise_rate, 1 / 6)  # FP / total
        self.assertAlmostEqual(m.late_rate, 1 / 6)  # FN / total

    def test_calibration_error(self) -> None:
        # confirmed: conf=1.0 corr=1.0 → |1-1|=0
        # false_positive: conf=0.9 corr=0.0 → |0.9-0|=0.9
        # false_negative: confidence=None → 跳过
        # calibration_error = (0 + 0.9) / 2 = 0.45
        records = [
            _record(finding_id="f-1", outcome="confirmed", confidence=1.0, correctness=1.0),
            _record(finding_id="f-2", outcome="false_positive", confidence=0.9, correctness=0.0),
            _record(finding_id="f-3", outcome="false_negative", confidence=None, correctness=None),
        ]
        groups = compute_metrics(records, by="rule")
        m = groups["cvm-cpu-high"]
        self.assertAlmostEqual(m.calibration_error, 0.45)

    def test_by_model_dimension(self) -> None:
        records = [
            _record(finding_id="m-1", model="threshold_based", outcome="confirmed"),
            _record(finding_id="m-2", model="isolation_forest", outcome="confirmed"),
            _record(finding_id="m-3", model="isolation_forest", outcome="false_positive"),
        ]
        groups = compute_metrics(records, by="model")
        self.assertIn("threshold_based", groups)
        self.assertIn("isolation_forest", groups)
        self.assertEqual(groups["threshold_based"].n, 1)
        self.assertEqual(groups["isolation_forest"].n, 2)
        self.assertAlmostEqual(groups["isolation_forest"].precision, 1 / 2)
        self.assertAlmostEqual(groups["isolation_forest"].recall, 1.0)

    def test_by_product_dimension(self) -> None:
        records = [
            _record(finding_id="p-1", product="cvm", outcome="confirmed"),
            _record(finding_id="p-2", product="cdb", outcome="confirmed"),
            _record(finding_id="p-3", product="cdb", outcome="false_negative"),
        ]
        groups = compute_metrics(records, by="product")
        self.assertIn("cvm", groups)
        self.assertIn("cdb", groups)
        self.assertEqual(groups["cdb"].n, 2)
        self.assertAlmostEqual(groups["cdb"].recall, 1 / 2)

    def test_mttd_and_confirm_minutes(self) -> None:
        detected = "2026-08-02T00:00:00Z"
        confirmed = "2026-08-02T01:30:00Z"  # 90 minutes later
        detected_dt = datetime.fromisoformat(detected)
        # detected_at for mttd lag: use a synthetic "issue_start" earlier than detected_at
        start = (detected_dt - timedelta(hours=2)).isoformat().replace("+00:00", "Z")
        records = [
            _record(finding_id="t-1", outcome="confirmed", detected_at=detected, confirmed_at=confirmed),
        ]
        records[0]["issue_start_at"] = start
        groups = compute_metrics(records, by="rule")
        m = groups["cvm-cpu-high"]
        self.assertAlmostEqual(m.avg_confirm_mins, 90.0)
        self.assertAlmostEqual(m.avg_mttd_hours, 2.0)

    def test_tz_mix_naive_and_aware_does_not_crash(self) -> None:
        # B1: naive（无 Z）+ aware（带 Z）时间戳混用不得抛 "can't subtract" 异常。
        rec = _record(finding_id="t-tz", outcome="confirmed")
        rec["detected_at"] = "2026-08-02T00:00:00"  # naive，无时区
        rec["confirmed_at"] = "2026-08-02T00:30:00Z"  # aware
        rec["issue_start_at"] = "2026-08-01T22:00:00"  # naive
        groups = compute_metrics([rec], by="rule")
        m = groups["cvm-cpu-high"]
        self.assertAlmostEqual(m.avg_confirm_mins, 30.0)  # 30 分钟
        self.assertAlmostEqual(m.avg_mttd_hours, 2.0)  # 2 小时


class TuningTests(unittest.TestCase):
    def test_tune_recommendation_read_only_high_noise(self) -> None:
        metrics = QualityMetrics(
            precision=0.6,
            recall=0.9,
            noise_rate=0.4,
            late_rate=0.1,
            avg_mttd_hours=1.0,
            avg_confirm_mins=30.0,
            calibration_error=0.1,
            n=100,
        )
        rec: TuningRecommendation = tune_recommendation(
            metrics, rule="cvm-cpu-high", threshold_ctx={"current": "0.8"}
        )
        self.assertEqual(rec.rule, "cvm-cpu-high")
        self.assertIn(rec.dimension, {"threshold", "window", "rule"})
        self.assertTrue(rec.approval_required)
        self.assertTrue(rec.rationale)
        self.assertTrue(rec.suggested)

    def test_apply_recommendation_rejects_without_token(self) -> None:
        rec = TuningRecommendation(rule="r", dimension="threshold", current="0.8", suggested="0.85", rationale="x", impact="y")
        self.assertFalse(apply_recommendation(rec, approval_token=""))
        self.assertFalse(apply_recommendation(rec, approval_token="invalid-token"))

    def test_apply_recommendation_accepts_valid_token_from_env(self) -> None:
        # B2: token 白名单仅来自环境变量；必须显式设置才放行（失败关闭）。
        rec = TuningRecommendation(rule="r", dimension="threshold", current="0.8", suggested="0.85", rationale="x", impact="y")
        with unittest.mock.patch.dict(
            os.environ, {"QUALITY_FEEDBACK_APPROVAL_TOKENS": "token-a,token-b"}, clear=False
        ):
            self.assertTrue(apply_recommendation(rec, approval_token="token-a"))
            self.assertTrue(apply_recommendation(rec, approval_token="token-b"))
            self.assertFalse(apply_recommendation(rec, approval_token="token-c"))

    def test_apply_recommendation_fails_closed_when_env_unset(self) -> None:
        # B2: 未设置 QUALITY_FEEDBACK_APPROVAL_TOKENS → 拒绝一切 token（无内置默认）。
        rec = TuningRecommendation(rule="r", dimension="threshold", current="0.8", suggested="0.85", rationale="x", impact="y")
        with unittest.mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("QUALITY_FEEDBACK_APPROVAL_TOKENS", None)
            self.assertFalse(apply_recommendation(rec, approval_token="approve-p02"))
            self.assertFalse(apply_recommendation(rec, approval_token="any-token"))


if __name__ == "__main__":
    unittest.main()
