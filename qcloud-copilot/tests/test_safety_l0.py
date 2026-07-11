from copilot.models import ParsedRequest, ClassifiedIntent, IntentType
from copilot.safety.l0 import check_l0


def test_l0_valid_skill():
    req = ParsedRequest(
        raw="查看 ins-abc", normalized="查看 ins-abc", entities={"resource_id": ["ins-abc"]}
    )
    intent = ClassifiedIntent(primary=IntentType.INSPECT, targets=["vm"])
    result = check_l0(req, intent)
    assert result["passed"] is True
    assert result["issues"] == []


def test_l0_unknown_skill():
    req = ParsedRequest(
        raw="查看 unknown-xyz",
        normalized="查看 unknown-xyz",
        entities={"resource_id": ["unknown-xyz"]},
    )
    intent = ClassifiedIntent(primary=IntentType.INSPECT, targets=["unknown"])
    result = check_l0(req, intent)
    assert result["passed"] is False
    assert any("unknown" in i.lower() for i in result["issues"])


def test_l0_malformed_resource_id():
    req = ParsedRequest(raw="查 abc", normalized="查 abc", entities={"resource_id": ["abc"]})
    intent = ClassifiedIntent(primary=IntentType.INSPECT, targets=["vm"])
    result = check_l0(req, intent)
    assert result["passed"] is False
    assert any("malformed" in i.lower() for i in result["issues"])


def test_l0_valid_region():
    req = ParsedRequest(raw="北京 vm", normalized="北京 vm", entities={"region": ["ap-guangzhou"]})
    intent = ClassifiedIntent(primary=IntentType.INSPECT, targets=["vm"])
    result = check_l0(req, intent)
    assert result["passed"] is True


def test_l0_unknown_region():
    req = ParsedRequest(raw="火星 vm", normalized="火星 vm", entities={"region": ["火星"]})
    intent = ClassifiedIntent(primary=IntentType.INSPECT, targets=["vm"])
    result = check_l0(req, intent)
    assert result["passed"] is False
    assert any("region" in i.lower() for i in result["issues"])
