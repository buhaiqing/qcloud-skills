"""
qcloud-proactive-inspection / analyzers / __init__.py
Analyzer registry.
"""

import sys
from pathlib import Path

_REASON_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_ROOT = _REASON_ROOT.parent
for path in (_SCRIPTS_ROOT, _REASON_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

_A: dict[str, type] = {}


def register(name: str, cls):
    _A[name] = cls


def get(name: str):
    return _A.get(name)


def list_available():
    return list(_A.keys())


def create_all() -> list:
    from analyzers import (
        clb_analyzer,  # noqa: F401
        eip_analyzer,  # noqa: F401
        es_analyzer,  # noqa: F401
        k8s_analyzer,  # noqa: F401
        mongodb_analyzer,  # noqa: F401
        nat_analyzer,  # noqa: F401
        rds_mysql_analyzer,  # noqa: F401
        rds_postgresql_analyzer,  # noqa: F401
        redis_analyzer,  # noqa: F401
        sg_analyzer,  # noqa: F401
        vm_analyzer,  # noqa: F401
    )

    return [cls() for cls in _A.values()]


def create_by_names(names: list[str]) -> list:
    create_all()
    from analyzers.selective import list_catalog

    order = {n: i for i, n in enumerate(list_catalog())}
    sorted_names = sorted(names, key=lambda n: order.get(n, 999))
    instances = []
    for name in sorted_names:
        cls = _A.get(name)
        if cls:
            instances.append(cls())
    return instances
