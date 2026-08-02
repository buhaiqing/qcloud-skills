"""P5.2 — tenant isolation + sensitive field redactor.
"""
from __future__ import annotations


def _trace(tenant_id=None, trace_id="trc-p5-2"):
    from copilot.trace_records import IdentityTree, TraceRecord

    tr = TraceRecord(
        id=trace_id,
        name="t",
        timestamp="2026-07-25T00:00:00Z",
        started_at="2026-07-25T00:00:00Z",
        ended_at="2026-07-25T00:00:05Z",
        status="success",
    )
    tr.identity = IdentityTree(tenant_id=tenant_id)
    return tr


def test_enforce_tenant_isolation_passes_when_tenant_id_matches():
    from copilot.tenant_guard import enforce_tenant_isolation
    records = [_trace(tenant_id="t1"), _trace(tenant_id="t1")]
    assert enforce_tenant_isolation(records, current_tenant_id="t1") == []


def test_enforce_tenant_isolation_flags_mismatched_tenant():
    from copilot.tenant_guard import enforce_tenant_isolation
    records = [
        _trace(tenant_id="t1"),
        _trace(tenant_id="t2", trace_id="trc-bad"),
    ]
    issues = enforce_tenant_isolation(records, current_tenant_id="t1")
    assert len(issues) == 1
    assert issues[0]["record_id"] == "trc-bad"
    assert issues[0]["record_tenant"] == "t2"
    assert issues[0]["current_tenant"] == "t1"


def test_enforce_tenant_isolation_ignores_null_tenant():
    from copilot.tenant_guard import enforce_tenant_isolation
    records = [
        _trace(tenant_id=None),
        _trace(tenant_id="t1"),
        _trace(tenant_id=None),
    ]
    assert enforce_tenant_isolation(records, current_tenant_id="t1") == []


def test_enforce_tenant_isolation_empty_records():
    from copilot.tenant_guard import enforce_tenant_isolation
    assert enforce_tenant_isolation([], current_tenant_id="t1") == []


# --- require_tenant_isolation: fail-closed gate ------------------------------


def test_require_tenant_isolation_returns_records_when_all_match():
    from copilot.tenant_guard import require_tenant_isolation
    records = [_trace(tenant_id="t1"), _trace(tenant_id="t1")]
    assert require_tenant_isolation(records, current_tenant_id="t1") == records


def test_require_tenant_isolation_empty_records_allowed():
    from copilot.tenant_guard import require_tenant_isolation
    assert require_tenant_isolation([], current_tenant_id="t1") == []


def test_require_tenant_isolation_raises_without_current_tenant():
    import pytest
    from copilot.tenant_guard import require_tenant_isolation
    with pytest.raises(PermissionError, match="no current_tenant_id"):
        require_tenant_isolation([_trace(tenant_id="t1")], current_tenant_id="")


def test_require_tenant_isolation_raises_on_untagged_record():
    import pytest
    from copilot.tenant_guard import require_tenant_isolation
    # Unlike the advisory variant, an untagged record cannot be proven to
    # belong to the caller, so it is denied instead of passed through.
    records = [_trace(tenant_id=None, trace_id="trc-untagged")]
    with pytest.raises(PermissionError, match="trc-untagged.*no tenant_id"):
        require_tenant_isolation(records, current_tenant_id="t1")


def test_require_tenant_isolation_raises_on_cross_tenant_record():
    import pytest
    from copilot.tenant_guard import require_tenant_isolation
    records = [_trace(tenant_id="t1"), _trace(tenant_id="t2", trace_id="trc-bad")]
    with pytest.raises(PermissionError, match="trc-bad.*belongs to tenant 't2'"):
        require_tenant_isolation(records, current_tenant_id="t1")


def test_require_tenant_isolation_does_not_consume_iterator_twice():
    from copilot.tenant_guard import require_tenant_isolation
    # A generator must survive validation so callers can still use the result.
    records = (t for t in [_trace(tenant_id="t1"), _trace(tenant_id="t1")])
    assert len(require_tenant_isolation(records, current_tenant_id="t1")) == 2


def test_enforce_tenant_isolation_emits_deprecation_warning():
    import warnings

    from copilot.tenant_guard import enforce_tenant_isolation
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        enforce_tenant_isolation([], current_tenant_id="t1")
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)


def test_redact_sensitive_fields_strips_password_token_secret():
    from copilot.tenant_guard import redact_sensitive_fields
    payload = {
        "user": "alice",
        "password": "super-secret",
        "api_key": "AKID1234EXAMPLE",
        "authorization": "Bearer xyz",
        "metadata": {"token": "abc", "role": "admin"},
    }
    out = redact_sensitive_fields(payload)
    assert out["user"] == "alice"
    assert out["password"] == "REDACTED"
    assert out["api_key"] == "REDACTED"
    assert out["authorization"] == "REDACTED"
    assert out["metadata"]["token"] == "REDACTED"
    assert out["metadata"]["role"] == "admin"
    assert payload["password"] == "super-secret"


def test_redact_sensitive_fields_case_insensitive():
    from copilot.tenant_guard import redact_sensitive_fields
    payload = {"Password": "x", "TOKEN": "y", "SecRet_Key": "z", "name": "alice"}
    out = redact_sensitive_fields(payload)
    assert out["Password"] == "REDACTED"
    assert out["TOKEN"] == "REDACTED"
    assert out["SecRet_Key"] == "REDACTED"
    assert out["name"] == "alice"


def test_redact_sensitive_fields_partial_keyword_does_not_match():
    from copilot.tenant_guard import redact_sensitive_fields
    payload = {
        "passwordless_login": True,
        "tokenizer": "bert",
        "username": "alice",
    }
    out = redact_sensitive_fields(payload)
    assert out["passwordless_login"] is True
    assert out["tokenizer"] == "bert"
    assert out["username"] == "alice"


def test_redact_sensitive_fields_nested_list_of_dicts():
    from copilot.tenant_guard import redact_sensitive_fields
    payload = {"users": [{"name": "alice", "token": "abc"}, {"name": "bob", "token": "def"}]}
    out = redact_sensitive_fields(payload)
    assert out["users"][0]["token"] == "REDACTED"
    assert out["users"][0]["name"] == "alice"
    assert out["users"][1]["token"] == "REDACTED"


def test_redact_sensitive_fields_handles_non_string_values():
    from copilot.tenant_guard import redact_sensitive_fields
    payload = {"password": 12345, "token": True, "name": "alice"}
    out = redact_sensitive_fields(payload)
    assert out["password"] == "REDACTED"
    assert out["token"] == "REDACTED"
    assert out["name"] == "alice"


def test_assert_no_secrets_on_disk_passes_for_clean_payload_dump():
    from copilot.tenant_guard import assert_no_secrets_on_disk
    assert_no_secrets_on_disk("ok text with no credentials")


def test_assert_no_secrets_on_disk_raises_when_secret_present():
    import pytest
    from copilot.tenant_guard import assert_no_secrets_on_disk
    payload = "Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123456789"
    with pytest.raises(AssertionError, match="secrets|secret"):
        assert_no_secrets_on_disk(payload)
