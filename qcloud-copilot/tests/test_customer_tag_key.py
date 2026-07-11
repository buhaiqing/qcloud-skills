"""P0 LC-5 follow-up: customer tag key is configurable (Tencent Cloud port pending lib)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:  # pragma: no cover
    from copilot import resource_discovery as rd
    from copilot.proactive_inspection import cruise_sniff as _sniff

pytest.skip(
    "Requires qcloud-proactive-inspection resource_discovery lib (Phase 2)",
    allow_module_level=True,
)


# ────────────────────────────────────────────────────────────────────
# 1. _classify honours customer_tag_key parameter
# ────────────────────────────────────────────────────────────────────


def test_classify_default_key_is_customer():
    tags = {"客户": "烟台振华"}
    cls = rd._classify(tags, "name", "vm")
    assert cls["mode"] == "traditional"
    assert cls["confidence"] == 0.85


def test_classify_custom_key_overrides_default():
    """If tenant uses 'customer' key, _classify must look for that key."""
    tags = {"customer": "ytzh", "env": "prod"}
    cls_default = rd._classify(tags, "name", "vm", customer_tag_key="客户")
    assert cls_default["mode"] == "unknown", "should miss when key is '客户'"

    cls_custom = rd._classify(tags, "name", "vm", customer_tag_key="customer")
    assert cls_custom["mode"] == "traditional"


def test_classify_k8s_takes_precedence_over_customer_tag():
    """K8s detection must win regardless of customer_tag_key value."""
    tags = {
        "客户": "烟台振华",
        "tke.cloud.tencent.com/cluster_id": "k8s-abc",
    }
    cls = rd._classify(tags, "k8s-node", "vm", customer_tag_key="客户")
    assert cls["mode"] == "k8s"
    assert cls["confidence"] == 0.95


# ────────────────────────────────────────────────────────────────────
# 2. discover_customer_resources honours explicit key
# ────────────────────────────────────────────────────────────────────


class _StubClient:
    """Minimal stub for cloud client: returns preset VM lists per region."""

    def __init__(self, by_region: dict[str, list[dict]]):
        self.by_region = by_region

    def list_vms(self, region=None, **_kw):
        return self.by_region.get(region or "ap-guangzhou", [])

    def list_lbs(self, region=None, **_kw):
        return []

    def list_redis(self, region=None, **_kw):
        return []

    def list_mongodb(self, region=None, **_kw):
        return []

    def list_rds(self, region=None, **_kw):
        return []

    def list_eips(self, region=None, **_kw):
        return []

    def list_es(self, region=None, **_kw):
        return []

    def list_vpcs(self, region=None, **_kw):
        return []

    def list_subnets(self, region=None, **_kw):
        return []

    def list_security_groups(self, region=None, **_kw):
        return []


@pytest.fixture
def stub_resources():
    """Two VMs in ap-guangzhou, tagged with different keys."""
    return _StubClient(
        {
            "ap-guangzhou": [
                {
                    "instanceId": "i-cn-1",
                    "instanceName": "ytzh-vm-1",
                    "vpcId": "vpc-x",
                    "tags": [{"key": "客户", "value": "烟台振华"}],
                },
                {
                    "instanceId": "i-cn-2",
                    "instanceName": "ytzh-vm-2",
                    "vpcId": "vpc-x",
                    "tags": [{"key": "customer", "value": "ytzh"}],
                },
            ],
        }
    )


def test_discover_uses_default_key_customer(stub_resources, monkeypatch):
    """Default behaviour: only VMs tagged with key='客户' are returned."""
    monkeypatch.delenv("COPILOT_CUSTOMER_TAG_KEY", raising=False)
    result = rd.discover_customer_resources(stub_resources, "烟台振华", regions=["ap-guangzhou"])
    ids = [vm["instanceId"] for vm in result["raw"]["vms"]]
    assert ids == ["i-cn-1"]
    assert result["customer_tag_key"] == "客户"


def test_discover_honours_explicit_key_customer(stub_resources):
    """When key='customer' is passed, the 'customer'-tagged VM is matched."""
    result = rd.discover_customer_resources(
        stub_resources,
        "ytzh",
        regions=["ap-guangzhou"],
        customer_tag_key="customer",
    )
    ids = [vm["instanceId"] for vm in result["raw"]["vms"]]
    assert ids == ["i-cn-2"]
    assert result["customer_tag_key"] == "customer"


def test_discover_env_var_overrides_default(stub_resources, monkeypatch):
    """COPILOT_CUSTOMER_TAG_KEY env var is respected when arg is None."""
    monkeypatch.setenv("COPILOT_CUSTOMER_TAG_KEY", "customer")
    result = rd.discover_customer_resources(stub_resources, "ytzh", regions=["ap-guangzhou"])
    ids = [vm["instanceId"] for vm in result["raw"]["vms"]]
    assert ids == ["i-cn-2"]
    assert result["customer_tag_key"] == "customer"


def test_discover_classification_uses_same_key(stub_resources, monkeypatch):
    """Classification must use the same key as filtering — no mismatch."""
    monkeypatch.setenv("COPILOT_CUSTOMER_TAG_KEY", "customer")
    result = rd.discover_customer_resources(stub_resources, "ytzh", regions=["ap-guangzhou"])
    modes = {r["mode"] for r in result["classification"]["resources"]}
    assert modes == {"traditional"}


# ────────────────────────────────────────────────────────────────────
# 3. cruise_sniff.list_all_customer_tags honours custom key
# ────────────────────────────────────────────────────────────────────


def test_list_tags_default_key(monkeypatch):
    """Default scan uses '客户' tag key."""
    monkeypatch.delenv("COPILOT_CUSTOMER_TAG_KEY", raising=False)
    client = _StubClient(
        {
            "ap-guangzhou": [
                {"tags": [{"key": "客户", "value": "烟台振华"}]},
                {"tags": [{"key": "customer", "value": "ytzh"}]},
            ],
        }
    )
    tag_map = _sniff.list_all_customer_tags(client, regions=["ap-guangzhou"])
    assert "烟台振华" in tag_map
    assert "ytzh" not in tag_map


def test_list_tags_custom_key(monkeypatch):
    """When key='customer' is passed, only that key's values are counted."""
    monkeypatch.delenv("COPILOT_CUSTOMER_TAG_KEY", raising=False)
    client = _StubClient(
        {
            "ap-guangzhou": [
                {"tags": [{"key": "客户", "value": "烟台振华"}]},
                {"tags": [{"key": "customer", "value": "ytzh"}]},
            ],
        }
    )
    tag_map = _sniff.list_all_customer_tags(client, regions=["ap-guangzhou"], tag_key="customer")
    assert "ytzh" in tag_map
    assert "烟台振华" not in tag_map


# ────────────────────────────────────────────────────────────────────
# 4. Backwards compatibility: callers using old arg signature still work
# ────────────────────────────────────────────────────────────────────


def test_discover_customer_resources_signature_backwards_compat(stub_resources):
    """Old positional callers (customer_tag_key=...) still resolve to '客户'."""
    result = rd.discover_customer_resources(stub_resources, "烟台振华", ["ap-guangzhou"])
    assert result["customer_tag_key"] == "客户"
    assert len(result["raw"]["vms"]) == 1
