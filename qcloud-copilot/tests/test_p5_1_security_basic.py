"""P5.1 — security / observability hygiene:
  - scan_text_for_secrets: detect AK/SK/Token/AWS secret-like patterns
  - hash_resource_id: stable non-reversible id for resource references
  - check_low_cardinality_labels: Prometheus labels with bounded cardinality

All three are pure functions that never mutate input.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Secret scanning
# ---------------------------------------------------------------------------


def test_scan_text_detects_ak_id_pattern():
    from copilot.security import scan_text_for_secrets
    text = "AKID1234567890EXAMPLE  some logs"
    findings = scan_text_for_secrets(text)
    assert any(f["pattern"] == "tencent_ak" for f in findings)


def test_scan_text_detects_secret_key_block():
    from copilot.security import scan_text_for_secrets
    text = "see my key: AKIAIOSFODNN7EXAMPLE"
    findings = scan_text_for_secrets(text)
    assert any(f["pattern"] == "aws_access_key" for f in findings)


def test_scan_text_detects_bearer_token():
    from copilot.security import scan_text_for_secrets
    text = "Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123456789ABCD"
    findings = scan_text_for_secrets(text)
    assert any("bearer" in f["pattern"] for f in findings)


def test_scan_text_clean_returns_empty():
    from copilot.security import scan_text_for_secrets
    text = "query ins-abc123 status OK in region ap-guangzhou"
    findings = scan_text_for_secrets(text)
    assert findings == []


def test_scan_text_returns_offset_and_pattern_only():
    """Findings carry enough metadata to redact; never echo the raw secret."""
    from copilot.security import scan_text_for_secrets
    text = "AKID1234567890EXAMPLE"
    findings = scan_text_for_secrets(text)
    f = findings[0]
    assert "offset" in f
    assert "pattern" in f
    assert "AKID" not in f.get("excerpt", "")  # excerpt may be safely-redacted placeholder
    assert "raw" not in f


# ---------------------------------------------------------------------------
# Resource ID hashing
# ---------------------------------------------------------------------------


def test_hash_resource_id_deterministic_and_irreversible_lookalike():
    """Same input -> same hash; hash looks nothing like the original literal."""
    from copilot.security import hash_resource_id
    a = hash_resource_id("ins-abc-12345")
    b = hash_resource_id("ins-abc-12345")
    assert a == b
    assert "ins-abc-12345" not in a


def test_hash_resource_id_distinct_inputs_produce_distinct_hashes():
    from copilot.security import hash_resource_id
    a = hash_resource_id("ins-abc-12345")
    b = hash_resource_id("ins-xyz-99999")
    assert a != b


def test_hash_resource_id_accepts_optional_salt():
    """Salt changes output (key rotation)."""
    from copilot.security import hash_resource_id
    a = hash_resource_id("ins-abc-12345", salt="v1")
    b = hash_resource_id("ins-abc-12345", salt="v2")
    assert a != b


# ---------------------------------------------------------------------------
# Low-cardinality prom label audit
# ---------------------------------------------------------------------------


def test_check_low_cardinality_labels_passes_for_bounded_values():
    from copilot.security import check_low_cardinality_labels
    labels = {"skill": "qcloud-cvm-ops", "region": "ap-guangzhou", "status": "success"}
    issues = check_low_cardinality_labels(labels)
    assert issues == []


def test_check_low_cardinality_labels_flags_unbounded_values():
    from copilot.security import check_low_cardinality_labels

    labels = {
        "skill": "qcloud-cvm-ops",        # OK
        "trace_id": "trc-very-long-id-with-many-characters",  # unbounded — each trace is unique
        "user_email": "alice@example.com",  # unbounded
    }
    issues = check_low_cardinality_labels(labels)
    flagged = {i["key"] for i in issues}
    assert "trace_id" in flagged
    assert "user_email" in flagged
    assert "skill" not in flagged


def test_check_low_cardinality_labels_rejects_high_cardinality_threshold():
    """Suggest cardinalities above 100 distinct values are flagged."""
    from copilot.security import check_low_cardinality_labels

    labels = {f"rare_{i}": "x" for i in range(101)}
    issues = check_low_cardinality_labels(labels)
    # All 101 keys look unbounded
    assert len(issues) == 101
