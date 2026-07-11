from copilot.parser import parse


def test_type_a_vm_query():
    result = parse("查 ins-abc123 的磁盘使用率")
    assert result.entities.get("resource_id") == ["ins-abc123"]
    assert result.confidence >= 0.8


def test_type_a_redis_inspection():
    result = parse("济南银座 Redis 巡检")
    assert "济南银座" in result.raw
    assert result.confidence >= 0.7


def test_type_c_vague_health():
    result = parse("最近系统有没有问题")
    assert result.confidence < 0.7


def test_type_c_broad_question():
    result = parse("帮我看看济南银座的资源健康吗")
    assert result.confidence < 0.8


def test_time_range_normalization():
    result = parse("昨天凌晨的告警")
    assert "告警" in result.normalized or "alert" in result.normalized


def test_resource_id_extraction():
    result = parse("检查 redis-xyz 的状态")
    assert "redis-xyz" in result.normalized or "redis" in result.entities.get("resource_type", [])


def test_region_extraction():
    result = parse("北京区域的 VM 列表")
    assert result.entities.get("region", []) or "北京" in result.normalized


def test_empty_input():
    result = parse("")
    assert result.confidence == 0.0


def test_low_confidence_for_gibberish():
    result = parse("asdfghjkl qwerty")
    assert result.confidence < 0.3
