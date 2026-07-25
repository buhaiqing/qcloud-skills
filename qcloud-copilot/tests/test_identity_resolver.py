"""P1.6 / P1.7 — Identity resolution across CLI, config, env, session, automation, fallback.

Tests:
  - IdentityResolver pulls from explicit overrides (CLI > config > env > session > automation > fallback)
  - Missing values round-trip as None, never "" / "unknown"
  - resolve() returns IdentityTree that survives to_dict round-trip
  - TraceContext accepts resolver output and uses it as ctx.identity
"""

from __future__ import annotations

import json


def test_identity_resolver_priority_cli_wins():
    from copilot.identity_resolver import IdentityResolver

    r = IdentityResolver(
        cli_overrides={"user_id": "cli-u"},
        config_dict={"user_id": "cfg-u"},
        env={},
        session_hint={},
        automation_hint={},
    )
    it = r.resolve()
    assert it.user_id == "cli-u"


def test_identity_resolver_priority_config_over_env():
    from copilot.identity_resolver import IdentityResolver

    r = IdentityResolver(
        cli_overrides={},
        config_dict={"tenant_id": "from-cfg"},
        env={"QCLOUD_TENANT_ID": "from-env"},
        session_hint={},
        automation_hint={},
    )
    it = r.resolve()
    assert it.tenant_id == "from-cfg"


def test_identity_resolver_priority_env_over_session():
    from copilot.identity_resolver import IdentityResolver

    r = IdentityResolver(
        cli_overrides={},
        config_dict={},
        env={"QCLOUD_CUSTOMER_ID": "env-cust"},
        session_hint={"customer_id": "ses-cust"},
        automation_hint={},
    )
    it = r.resolve()
    assert it.customer_id == "env-cust"


def test_identity_resolver_priority_session_over_automation():
    from copilot.identity_resolver import IdentityResolver

    r = IdentityResolver(
        cli_overrides={},
        config_dict={},
        env={},
        session_hint={"operator_id": "ses-op"},
        automation_hint={"operator_id": "auto-op"},
    )
    it = r.resolve()
    assert it.operator_id == "ses-op"


def test_identity_resolver_fallback_to_automation():
    from copilot.identity_resolver import IdentityResolver

    r = IdentityResolver(
        cli_overrides={},
        config_dict={},
        env={},
        session_hint={},
        automation_hint={"job_id": "auto-job"},
    )
    it = r.resolve()
    assert it.user_id is None
    assert it.identity_source == "fallback"


def test_identity_resolver_missing_fields_serialize_as_null():
    from copilot.identity_resolver import IdentityResolver

    r = IdentityResolver({}, {}, {}, {}, {})
    it = r.resolve()
    d = it.to_dict()
    assert d["user_id"] is None
    json_str = json.dumps(d)
    assert '"user_id": null' in json_str
    assert '"user_id": ""' not in json_str
    assert '"user_id": "unknown"' not in json_str


def test_identity_resolver_env_mapping():
    """Specific env keys map to identity fields."""
    from copilot.identity_resolver import IdentityResolver

    env = {
        "QCLOUD_USER_ID": "env-user-123",
        "QCLOUD_TENANT_ID": "env-tnt-456",
        "QCLOUD_OPERATOR_ID": "env-op-789",
    }
    r = IdentityResolver({}, {}, env, {}, {})
    it = r.resolve()
    assert it.user_id == "env-user-123"
    assert it.tenant_id == "env-tnt-456"
    assert it.operator_id == "env-op-789"
    assert it.identity_source == "env"


def test_identity_resolver_attaches_to_trace_context():
    from copilot.identity_resolver import IdentityResolver
    from copilot.trace_context import TraceContext

    r = IdentityResolver(
        cli_overrides={"user_id": "ctx-user"},
        config_dict={},
        env={},
        session_hint={},
        automation_hint={},
    )
    ctx = TraceContext(trace_id="trc-idr-001", identity=r.resolve())
    assert ctx.identity.user_id == "ctx-user"
    assert ctx.identity.identity_source == "cli"


def test_blackboard_carries_identity_block():
    """Blackboard dict can carry identity keys without breaking schema 1.1 readers."""
    from copilot.trace_records import IdentityTree

    identity = IdentityTree(
        user_id="bb-user",
        tenant_id="bb-tenant",
        customer_id="bb-cust",
        initiator_type="cli",
        identity_source="cli",
    )
    board = {
        "schema_version": "1.1",
        "session_id": "ses-bb-1",
        "evidence_chain": [],
        "identity": identity.to_dict(),
        "regions": [],
    }
    assert board["schema_version"] == "1.1"
    assert board["identity"]["user_id"] == "bb-user"
    assert board["identity"]["tenant_id"] == "bb-tenant"
