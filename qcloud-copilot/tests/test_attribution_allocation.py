"""P3.3 + P3.4 — attribution + allocation.

P3.3: AttributionTree (tenant / customer / account_hash / business_unit /
cost_center / region / service / environment / product / resource_id). Plus
build_attribution_tree() that walks TraceContext + IdentityTree fields and
returns the union AttributionTree (idempotent, None-safe).

P3.4: AllocationRecord + allocate_cost(). Methods:
  - direct         : one AttributionKey gets 100% of total
  - shared         : split evenly by declared attribution key count
  - resource       : split proportionally to resource_count vector
  - request        : split proportionally to request_count vector
  - usage          : split proportionally to usage (LLM token total) vector
  - equal_split    : alias for shared with even denominator
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# P3.3 — AttributionTree
# ---------------------------------------------------------------------------


def _mk_obs(obs_id: str, **kw):
    from copilot.trace_records import ObservationRecord

    md = kw.pop("metadata", {}) or {}
    return ObservationRecord(
        id=obs_id,
        trace_id="trc-attribution",
        name=kw.pop("name", obs_id),
        metadata={**md, **kw.pop("extra_metadata", {})},
    )


def test_attribution_tree_dataclass_fields():
    from copilot.trace_records import AttributionTree

    a = AttributionTree(
        tenant_id="t1",
        customer_id="c1",
        account_id_hash="acct:abc",
        business_unit="bu-1",
        cost_center="cc-42",
        region="ap-guangzhou",
        service="cvm",
        environment="prod",
        product="qcloud-cvm-ops",
        resource_id="ins-123",
    )
    assert a.tenant_id == "t1"
    assert a.cost_center == "cc-42"
    assert a.resource_id == "ins-123"
    assert a.to_dict()["account_id_hash"] == "acct:abc"


def test_attribution_tree_round_trip():
    from copilot.trace_records import AttributionTree

    a = AttributionTree(business_unit="bu-2", cost_center="cc-7", region="ap-shanghai")
    d = a.to_dict()
    restored = AttributionTree.from_dict(d)
    assert restored.business_unit == "bu-2"
    assert restored.cost_center == "cc-7"
    assert restored.region == "ap-shanghai"


def test_build_attribution_tree_from_observation_metadata():
    """Pull attribution fields from observation.metadata into AttributionTree."""
    from copilot.attribution import build_attribution_tree

    obs_list = [
        _mk_obs("o1", extra_metadata={
            "tenant_id": "t1",
            "business_unit": "bu-x",
            "cost_center": "cc-99",
            "region": "ap-guangzhou",
            "product": "qcloud-cvm-ops",
            "resource_id": "ins-abc",
        }),
    ]
    tree = build_attribution_tree(obs_list)
    assert tree.tenant_id == "t1"
    assert tree.business_unit == "bu-x"
    assert tree.cost_center == "cc-99"
    assert tree.region == "ap-guangzhou"
    assert tree.product == "qcloud-cvm-ops"
    assert tree.resource_id == "ins-abc"


def test_build_attribution_tree_first_non_null_wins():
    """When multiple observations carry overlapping keys, first non-null keeps."""
    from copilot.attribution import build_attribution_tree

    obs_list = [
        _mk_obs("o1", extra_metadata={"tenant_id": "t1", "region": "ap-guangzhou"}),
        _mk_obs("o2", extra_metadata={"tenant_id": "t2", "region": "ap-shanghai"}),
    ]
    tree = build_attribution_tree(obs_list)
    assert tree.tenant_id == "t1"
    assert tree.region == "ap-guangzhou"


def test_build_attribution_tree_handles_empty():
    from copilot.attribution import build_attribution_tree

    tree = build_attribution_tree([])
    assert tree.tenant_id is None
    assert tree.business_unit is None
    assert tree.resource_id is None


def test_build_attribution_tree_is_idempotent():
    from copilot.attribution import build_attribution_tree

    obs_list = [
        _mk_obs("o1", extra_metadata={"tenant_id": "t1", "cost_center": "cc-42"}),
    ]
    a1 = build_attribution_tree(obs_list)
    a2 = build_attribution_tree(obs_list)
    assert a1.to_dict() == a2.to_dict()


# ---------------------------------------------------------------------------
# P3.4 — AllocationRecord + allocate_cost
# ---------------------------------------------------------------------------


def test_allocate_direct_one_share_total():
    """Method='direct' assigns 100% to the single key."""
    from copilot.attribution import allocate_cost

    total = 10.0
    keys = [("tenant", "t1")]
    # shares map keys by full tuple; share values must sum to 1.0
    shares = {("tenant", "t1"): 1.0}
    out = allocate_cost(
        total_cost=total,
        attribution_keys=keys,
        method="direct",
        shares=shares,
    )
    assert len(out) == 1
    assert out[0].allocated_cost == 10.0
    assert out[0].share == 1.0


def test_allocate_shared_even_split():
    """Method='shared' splits evenly across keys."""
    from copilot.attribution import allocate_cost

    out = allocate_cost(
        total_cost=12.0,
        attribution_keys=[
            ("tenant", "t1"),
            ("tenant", "t2"),
            ("tenant", "t3"),
        ],
        method="shared",
    )
    assert len(out) == 3
    assert all(abs(r.allocated_cost - 4.0) < 1e-9 for r in out)
    assert all(abs(r.share - 1 / 3) < 1e-9 for r in out)


def test_allocate_resource_weighted_split():
    """Method='resource' weights by resource_count vector."""
    from copilot.attribution import allocate_cost

    out = allocate_cost(
        total_cost=100.0,
        attribution_keys=[
            ("tenant", "t1"),
            ("tenant", "t2"),
        ],
        method="resource",
        weights={"t1": 3, "t2": 1},
    )
    assert len(out) == 2
    # 75 / 25 split
    assert abs(out[0].allocated_cost - 75.0) < 1e-9
    assert abs(out[1].allocated_cost - 25.0) < 1e-9


def test_allocate_request_weighted_split():
    """Method='request' weights by request_count vector."""
    from copilot.attribution import allocate_cost

    out = allocate_cost(
        total_cost=80.0,
        attribution_keys=[
            ("tenant", "alpha"),
            ("tenant", "beta"),
        ],
        method="request",
        weights={"alpha": 6, "beta": 2},
    )
    assert abs(out[0].allocated_cost - 60.0) < 1e-9
    assert abs(out[1].allocated_cost - 20.0) < 1e-9


def test_allocate_usage_weighted_split():
    """Method='usage' weights by token usage vector (or any usage unit)."""
    from copilot.attribution import allocate_cost

    out = allocate_cost(
        total_cost=50.0,
        attribution_keys=[
            ("tenant", "x"),
            ("tenant", "y"),
        ],
        method="usage",
        weights={"x": 4, "y": 1},
    )
    assert abs(out[0].allocated_cost - 40.0) < 1e-9
    assert abs(out[1].allocated_cost - 10.0) < 1e-9


def test_allocate_equal_split_alias_for_shared():
    """equal_split == shared with even denominator."""
    from copilot.attribution import allocate_cost

    out = allocate_cost(
        total_cost=10.0,
        attribution_keys=[("tenant", "a"), ("tenant", "b")],
        method="equal_split",
    )
    assert len(out) == 2
    assert abs(out[0].allocated_cost - 5.0) < 1e-9
    assert abs(out[1].allocated_cost - 5.0) < 1e-9


def test_allocate_shared_handles_empty_keys_with_unallocated_bucket():
    """Empty keys => single 'unallocated' bucket with full cost + share=1."""
    from copilot.attribution import allocate_cost

    out = allocate_cost(total_cost=7.0, attribution_keys=[], method="shared")
    assert len(out) == 1
    assert out[0].key == ("scope", "unallocated")
    assert out[0].allocated_cost == 7.0
    assert out[0].share == 1.0


def test_allocate_weighted_missing_weight_treated_as_zero_weight():
    """Keys not in weights map assume 0; others normalize; missing keys get 0 share."""
    from copilot.attribution import allocate_cost

    out = allocate_cost(
        total_cost=10.0,
        attribution_keys=[("tenant", "a"), ("tenant", "b")],
        method="resource",
        weights={"a": 1},  # b is missing — weight treated as 0
    )
    assert len(out) == 2
    assert abs(out[0].allocated_cost - 10.0) < 1e-9
    assert abs(out[1].allocated_cost - 0.0) < 1e-9
