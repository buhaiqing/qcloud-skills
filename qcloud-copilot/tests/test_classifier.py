from copilot.models import IntentType
from copilot.classifier import classify
from copilot.parser import parse


def test_parse_then_classify_diagnose():
    req = parse("为什么我的 VM 这么慢")
    intent = classify(req)
    assert intent.primary == IntentType.DIAGNOSE


def test_parse_then_classify_inspect():
    req = parse("查看 ins-abc 的状态")
    intent = classify(req)
    assert intent.primary == IntentType.INSPECT


def test_parse_then_classify_cruise():
    req = parse("巡检济南银座全部资源")
    intent = classify(req)
    assert intent.primary == IntentType.CRUISE


def test_parse_then_classify_act():
    req = parse("重启 ins-abc")
    intent = classify(req)
    assert intent.primary == IntentType.ACT


def test_parse_then_classify_report():
    req = parse("帮我生成上周的运维报告")
    intent = classify(req)
    assert intent.primary == IntentType.REPORT


def test_classify_unknown():
    req = parse("你好")
    intent = classify(req)
    assert intent.primary == IntentType.UNKNOWN


def test_classify_targets_vm():
    req = parse("查看 ins-abc 的信息")
    intent = classify(req)
    assert "vm" in intent.targets


def test_classify_targets_redis():
    req = parse("检查 redis-xyz 的状态")
    intent = classify(req)
    assert "redis" in intent.targets
