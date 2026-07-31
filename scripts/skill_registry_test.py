#!/usr/bin/env python3
"""Tests for SkillRegistry — covers Spec §1.2.5 acceptance criteria.

TDD: written before skill_registry.py implementation. Tests assert
populated values (not just key presence) per project L5 lesson.

Run via: cd scripts && python3 -m unittest skill_registry_test -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from textwrap import dedent

# Make scripts/ importable when running from project root
SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

# Hardcoded fallback mirrors qcloud-copilot/copilot/integration/skills.py
# Used as fallback when SKILL.md frontmatter lacks structured fields.
HARDCODED_PRODUCT = {
    "qcloud-cvm-ops": "cvm",
    "qcloud-redis-ops": "redis",
    "qcloud-cdb-ops": "cdb",
    "qcloud-postgres-ops": "postgres",
    "qcloud-mongodb-ops": "mongodb",
    "qcloud-es-ops": "es",
    "qcloud-tke-ops": "tke",
    "qcloud-monitor-ops": "monitor",
    "qcloud-cam-ops": "cam",
    "qcloud-vpc-ops": "vpc",
    "qcloud-clb-ops": "clb",
    "qcloud-cbs-ops": "cbs",
    "qcloud-cos-ops": "cos",
    "qcloud-cdn-ops": "cdn",
    "qcloud-scf-ops": "scf",
    "qcloud-ssl-ops": "ssl",
    "qcloud-finops-ops": "billing",
    "qcloud-cls-ops": "cls",
    "qcloud-ckafka-ops": "ckafka",
    "qcloud-apigw-ops": "apigateway",
    "qcloud-proactive-inspection": "monitor",
    "qcloud-aiops-diagnosis": "monitor",
}

HARDCODED_ALIASES = {
    ("qcloud-cvm-ops", "describe"): "describe-instances",
    ("qcloud-redis-ops", "describe"): "describe-cache-instances",
    ("qcloud-cdb-ops", "describe"): "describe-db-instances",
    ("qcloud-postgres-ops", "describe"): "describe-db-instances",
    ("qcloud-mongodb-ops", "describe"): "describe-instances",
    ("qcloud-es-ops", "describe"): "describe-instances",
    ("qcloud-tke-ops", "describe"): "describe-clusters",
    ("qcloud-monitor-ops", "describe"): "describe-alarms",
    ("qcloud-cbs-ops", "describe"): "describe-disks",
    ("qcloud-vpc-ops", "describe"): "describe-vpcs",
    ("qcloud-clb-ops", "describe"): "describe-load-balancers",
    ("qcloud-cos-ops", "describe"): "list-buckets",
    ("qcloud-ssl-ops", "describe"): "describe-certificates",
    ("qcloud-finops-ops", "describe"): "describe-bills",
}

HARDCODED_PARAM_MAPPING = {
    ("qcloud-cvm-ops", "describe-instance"): "InstanceIds.0",
    ("qcloud-redis-ops", "describe-cache-instance"): "InstanceId",
    ("qcloud-cdb-ops", "describe-db-instance"): "InstanceId",
    ("qcloud-postgres-ops", "describe-db-instance"): "InstanceId",
    ("qcloud-mongodb-ops", "describe-instance"): "InstanceId",
    ("qcloud-cbs-ops", "describe-disk"): "DiskIds.0",
    ("qcloud-clb-ops", "describe-load-balancers"): "LoadBalancerIds.0",
    ("qcloud-vpc-ops", "describe-vpc"): "VpcIds.0",
    ("qcloud-monitor-ops", "describe-alarm"): "Module",
}


def _make_fixture_skill(tmp: Path, name: str, *, frontmatter_extra: str = "",
                        description: str = "Test skill for SkillRegistry TDD.",
                        intent_queries: list[dict] | None = None) -> Path:
    """Create a fake qcloud-*-ops/SKILL.md under tmp."""
    skill_dir = tmp / f"qcloud-{name}-ops"
    skill_dir.mkdir(parents=True, exist_ok=True)
    # Build frontmatter line-by-line to avoid dedent alignment issues
    lines = [
        "---",
        f"name: qcloud-{name}-ops",
        "description: |",
        f"  {description}",
        "metadata:",
        "  cli_applicability: dual-path",
        "  version: 0.0.1",
        "  last_updated: 2026-08-01",
    ]
    if frontmatter_extra:
        lines.append(frontmatter_extra.rstrip("\n"))
    lines.append("---")
    lines.append("")
    lines.append("# Body")
    lines.append("")
    fm = "\n".join(lines)
    (skill_dir / "SKILL.md").write_text(fm)
    if intent_queries:
        assets = skill_dir / "assets"
        assets.mkdir(exist_ok=True)
        import json
        (assets / "eval_queries.json").write_text(json.dumps({"queries": intent_queries}))
    return skill_dir


def _make_full_registry(tmp: Path) -> SkillRegistry:
    """Build a registry from a small synthetic fixture covering edge cases."""
    # skill with backtick keywords in description + structured delegate_to
    _make_fixture_skill(
        tmp, "cvm",
        frontmatter_extra=dedent("""\
            product_name: cvm
            delegate_to:
              - skill: qcloud-vpc-ops
                reason: VPC must exist before RunInstances
                trigger: pre-flight
            """),
        description="Manages `DescribeInstances` and `RunInstances`.",
        intent_queries=[{"intent": "RunInstances"}],
    )
    # skill with alias only in hardcoded fallback
    _make_fixture_skill(
        tmp, "redis",
        description="Redis cache cluster management.",
        intent_queries=[{"intent": "DescribeInstances"}],
    )
    # skill with no intent keywords anywhere
    _make_fixture_skill(tmp, "noop", description="noop skill for negative test.")
    # skill with cyclic-ish delegate
    _make_fixture_skill(
        tmp, "vpc",
        frontmatter_extra="product_name: vpc\n",
        description="VPC management.",
    )
    return SkillRegistry.from_skill_dirs(
        tmp,
        hardcoded={
            "SKILL_TO_PRODUCT": HARDCODED_PRODUCT,
            "OPERATION_ALIAS": HARDCODED_ALIASES,
            "SKILL_PARAM_MAPPING": HARDCODED_PARAM_MAPPING,
        },
    )


class SkillRegistryTest(unittest.TestCase):
    """Cover Spec §1.2.5: discover/validate/route/get_product/dependencies/etc."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="skill_registry_test_")
        self.reg = _make_full_registry(Path(self.tmp))

    def test_discover_returns_all_fixture_skills(self):
        names = self.reg.discover()
        self.assertEqual(len(names), 4)
        self.assertEqual(set(names), {
            "qcloud-cvm-ops", "qcloud-redis-ops",
            "qcloud-vpc-ops", "qcloud-noop-ops",
        })

    def test_validate_known_skill(self):
        self.assertTrue(self.reg.validate("qcloud-cvm-ops"))

    def test_validate_nonexistent_skill(self):
        self.assertFalse(self.reg.validate("nonexistent-skill"))

    def test_get_product_from_frontmatter(self):
        # cvm fixture declares product_name in frontmatter
        self.assertEqual(self.reg.get_product("qcloud-cvm-ops"), "cvm")

    def test_get_product_from_hardcoded_fallback(self):
        # redis fixture does NOT declare product_name; falls back to HARDCODED_PRODUCT
        self.assertEqual(self.reg.get_product("qcloud-redis-ops"), "redis")

    def test_get_product_unknown(self):
        self.assertIsNone(self.reg.get_product("nonexistent"))

    def test_resolve_operation_with_alias(self):
        # cvm "describe" alias → "describe-instances"
        self.assertEqual(
            self.reg.resolve_operation("qcloud-cvm-ops", "describe"),
            "describe-instances",
        )

    def test_resolve_operation_no_alias(self):
        self.assertEqual(
            self.reg.resolve_operation("qcloud-cvm-ops", "describe-instances"),
            "describe-instances",
        )

    def test_resolve_operation_unknown_skill_raises(self):
        with self.assertRaises(ValueError):
            self.reg.resolve_operation("nonexistent-skill", "describe")

    def test_resolve_param_known(self):
        # hardcoded fallback should resolve for cvm
        self.assertEqual(
            self.reg.resolve_param("qcloud-cvm-ops", "describe-instance"),
            "InstanceIds.0",
        )

    def test_resolve_param_unknown_op_returns_none(self):
        self.assertIsNone(self.reg.resolve_param("qcloud-cvm-ops", "unknown-op"))

    def test_get_dependencies_structured(self):
        deps = self.reg.get_dependencies("qcloud-cvm-ops")
        self.assertIsInstance(deps, set)
        self.assertEqual(deps, {"qcloud-vpc-ops"})

    def test_get_dependencies_empty_when_no_delegate_to(self):
        deps = self.reg.get_dependencies("qcloud-redis-ops")
        self.assertEqual(deps, set())

    def test_get_dependents_inverse_of_dependencies(self):
        dependents = self.reg.get_dependents("qcloud-vpc-ops")
        self.assertIn("qcloud-cvm-ops", dependents)

    def test_topological_order_includes_all(self):
        order = self.reg.topological_order()
        self.assertEqual(set(order), set(self.reg.discover()))
        # dependency precedes dependent
        if {"qcloud-vpc-ops", "qcloud-cvm-ops"} <= set(order):
            self.assertLess(order.index("qcloud-vpc-ops"), order.index("qcloud-cvm-ops"))

    def test_route_keyword_match(self):
        skill, conf = self.reg.route("describe my cvm instances")
        self.assertEqual(skill, "qcloud-cvm-ops")
        self.assertGreater(conf, 0.0)

    def test_route_no_match_returns_empty_with_zero_conf(self):
        skill, conf = self.reg.route("xyz nothing matches anything")
        self.assertEqual(skill, "")
        self.assertEqual(conf, 0.0)

    def test_intent_keywords_populated_from_backtick_and_eval(self):
        # cvm fixture has both `DescribeInstances` backtick + RunInstances intent
        entry = self.reg.get_entry("qcloud-cvm-ops")
        self.assertIn("DescribeInstances", entry.intent_keywords)
        self.assertIn("RunInstances", entry.intent_keywords)


class SkillRegistryFromRepoTest(unittest.TestCase):
    """End-to-end: scan the real repo. Asserts Spec §1.2.5 acceptance point."""

    @classmethod
    def setUpClass(cls):
        cls.reg = SkillRegistry.from_skill_dirs(
            ROOT,
            hardcoded={
                "SKILL_TO_PRODUCT": HARDCODED_PRODUCT,
                "OPERATION_ALIAS": HARDCODED_ALIASES,
                "SKILL_PARAM_MAPPING": HARDCODED_PARAM_MAPPING,
            },
        )

    def test_repo_discover_count(self):
        # 30 production skills + 1 stub (qcloud-test-ops for M3 acceptance).
        # Plan said 34, actual disk had 30 before stub. Assert actual value.
        names = self.reg.discover()
        self.assertEqual(len(names), 31)

    def test_repo_known_skills_have_product_name(self):
        """Skills in the legacy hardcoded mapping must resolve via fallback.

        New skills not yet migrated (e.g. qcloud-agsx-ops) will need Step 1.2.3
        frontmatter migration to add `product_name`. This test gates only the
        backward-compat path.
        """
        names_with_hc = set(HARDCODED_PRODUCT.keys()) & set(self.reg.discover())
        self.assertGreaterEqual(len(names_with_hc), 20,
                                "expected >=20 skills covered by hardcoded fallback")
        for n in names_with_hc:
            p = self.reg.get_product(n)
            self.assertIsNotNone(p, f"{n} missing product_name even after hardcoded fallback")

    def test_repo_validate_known(self):
        self.assertTrue(self.reg.validate("qcloud-cvm-ops"))
        self.assertFalse(self.reg.validate("definitely-not-a-real-skill-xyz"))

    def test_m3_acceptance_stub_discoverable_without_code_change(self):
        """M3 acceptance: a new qcloud-*-ops skill with only SKILL.md must be
        discoverable by SkillRegistry with no code changes anywhere.
        """
        names = self.reg.discover()
        # qcloud-test-ops exists in the repo solely to validate this gate.
        self.assertIn("qcloud-test-ops", names,
                      "M3 stub skill must be auto-discovered")
        e = self.reg.get_entry("qcloud-test-ops")
        self.assertEqual(e.product_name, "test")
        self.assertEqual(e.cli_applicability, "cli-only")
        # delegate_to in metadata.* must be parsed into structured list
        deps = self.reg.get_dependencies("qcloud-test-ops")
        self.assertEqual(deps, {"qcloud-monitor-ops"})
        # Topological order must place dependency first
        order = self.reg.topological_order()
        self.assertLess(order.index("qcloud-monitor-ops"),
                        order.index("qcloud-test-ops"))

    def test_m3_acceptance_stub_wins_route_for_curated_queries(self):
        """M3 acceptance (audit fix): curated queries containing the stub's
        intent keywords must route to qcloud-test-ops, proving that
        zero-code, query-driven routing works for new skills.
        """
        # The stub has eval_queries.json with intent keywords
        # 'M3 acceptance probe', 'M3 stub skill validation',
        # 'zero-code routing acceptance'.
        skill, conf = self.reg.route("M3 acceptance probe stub validation")
        self.assertEqual(skill, "qcloud-test-ops",
                         f"curated query should route to stub, got {skill}")
        self.assertGreater(conf, 0.0)

        skill, _ = self.reg.route("zero-code routing acceptance")
        self.assertEqual(skill, "qcloud-test-ops",
                         f"curated query should route to stub, got {skill}")

    def test_repo_real_skills_read_cli_applicability_from_metadata(self):
        """Real SKILL.md puts cli_applicability/version/last_updated under metadata.*."""
        e_cvm = self.reg.get_entry("qcloud-cvm-ops")
        self.assertEqual(e_cvm.cli_applicability, "dual-path")
        self.assertEqual(e_cvm.version, "1.3.0")
        self.assertEqual(e_cvm.last_updated, "2026-07-04")

    def test_repo_real_skills_intent_keywords_partially_populated(self):
        """At least 50% of skills should have populated intent_keywords."""
        names = self.reg.discover()
        # Exclude the M3 stub (has no eval_queries.json or backtick API names).
        production = [n for n in names if n != "qcloud-test-ops"]
        populated = sum(1 for n in production
                        if self.reg.get_entry(n).intent_keywords)
        self.assertGreaterEqual(populated, len(production) // 2,
                                f"only {populated}/{len(production)} production skills have intent_keywords")


# Late import so test module is self-contained even before SkillRegistry exists
from skill_registry import SkillRegistry

if __name__ == "__main__":
    unittest.main()