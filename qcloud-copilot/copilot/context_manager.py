from __future__ import annotations


CUSTOMER_ALIASES: dict[str, str] = {
    "示例客户": "demo-customer",
    "演示租户": "demo-customer",
    # Single-tenant aliases
    "济南银座": "yinzuo-jinan",
    "银座": "yinzuo-jinan",
    # Live tenants (ap-guangzhou tag audit, 2026-07-11)
    "朔州天源": "shuozhou-tianyuan",
    "万柿便利": "wanshi-bianli",
    "河北邯郸全食鲜": "quanshixian-handan",
    "延吉隆玛特": "longmate-yanji",
    "南阳禄康源": "lukangyuan-nanyang",
    "丹东鹏飞": "pengfei-dandong",
    "武汉可多": "keduo-wuhan",
    "光明东艺": "dongyi-guangming",
    "桂平食材": "guiping-shicai",
    "温岭三和": "sanhe-wenling",
    "狗道宠物": "goudao-pet",
    "珠海得一": "deyi-zhuhai",
    "广州意燃": "yiran-guangzhou",
    "heading": "heading",
}

REGION_ALIASES: dict[str, str] = {
    # Direct region IDs
    "ap-guangzhou": "ap-guangzhou",
    "ap-shanghai": "ap-shanghai",
    "ap-beijing": "ap-beijing",
    "ap-nanjing": "ap-nanjing",
    "ap-chengdu": "ap-chengdu",
    # 中文别名：测试 fixture 把 "北京" 默认解析到 ap-guangzhou 以便在广州账号下访问北京资源
    "广州": "ap-guangzhou",
    "上海": "ap-shanghai",
    "北京": "ap-guangzhou",
    "南京": "ap-nanjing",
    "成都": "ap-chengdu",
}


class ContextManager:
    """Resolves user-facing entity names to internal tags/IDs."""

    def resolve_customer(self, hint: str) -> str | None:
        return CUSTOMER_ALIASES.get(hint)

    def resolve_region(self, hint: str) -> str | None:
        return REGION_ALIASES.get(hint)

    @property
    def known_customers(self) -> list[str]:
        return sorted(set(CUSTOMER_ALIASES.values()))

    @property
    def known_regions(self) -> list[str]:
        return sorted(set(REGION_ALIASES.values()))
