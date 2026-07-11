from copilot.context_manager import ContextManager


def test_resolve_customer_exact_match():
    cm = ContextManager()
    tag = cm.resolve_customer("济南银座")
    assert tag == "yinzuo-jinan"


def test_resolve_customer_alias():
    cm = ContextManager()
    tag = cm.resolve_customer("银座")
    assert tag == "yinzuo-jinan"


def test_resolve_customer_unknown():
    cm = ContextManager()
    tag = cm.resolve_customer("不存在的客户")
    assert tag is None


def test_resolve_region_alias():
    cm = ContextManager()
    region = cm.resolve_region("北京")
    assert region == "ap-guangzhou"


def test_resolve_region_direct():
    cm = ContextManager()
    region = cm.resolve_region("ap-guangzhou")
    assert region == "ap-guangzhou"


def test_resolve_region_unknown():
    cm = ContextManager()
    region = cm.resolve_region("火星")
    assert region is None


# ── Live tenants (ap-guangzhou tag audit, 2026-07-11) ────────────────
LIVE_TENANT_FIXTURES = [
    ("朔州天源", "shuozhou-tianyuan"),
    ("万柿便利", "wanshi-bianli"),
    ("河北邯郸全食鲜", "quanshixian-handan"),
    ("延吉隆玛特", "longmate-yanji"),
    ("南阳禄康源", "lukangyuan-nanyang"),
    ("丹东鹏飞", "pengfei-dandong"),
    ("武汉可多", "keduo-wuhan"),
    ("光明东艺", "dongyi-guangming"),
    ("桂平食材", "guiping-shicai"),
    ("温岭三和", "sanhe-wenling"),
    ("狗道宠物", "goudao-pet"),
    ("珠海得一", "deyi-zhuhai"),
    ("广州意燃", "yiran-guangzhou"),
    ("heading", "heading"),
]


def test_live_tenants_resolve():
    cm = ContextManager()
    for label, slug in LIVE_TENANT_FIXTURES:
        assert cm.resolve_customer(label) == slug, f"failed: {label} → {slug}"


def test_known_customers_includes_live_tenants():
    cm = ContextManager()
    known = set(cm.known_customers)
    expected_slugs = {slug for _, slug in LIVE_TENANT_FIXTURES}
    missing = expected_slugs - known
    assert not missing, f"missing live tenant slugs: {missing}"
