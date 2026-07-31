#!/usr/bin/env python3
"""Tests for SkillDispatcher SkillRegistry integration (Phase 1 Step 1.2.4).

TDD: written before skills.py modifications.
Run: cd qcloud-copilot && python3 -m unittest copilot.integration.skills_test -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

# Set up import path for copilot package
HERE = Path(__file__).resolve().parent
COPILOT_ROOT = HERE.parents[1]  # qcloud-copilot/
REPO_ROOT = COPILOT_ROOT.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(COPILOT_ROOT))
sys.path.insert(0, str(SCRIPTS))

from copilot.integration.skills import (
    KNOWN_SKILLS,
    SKILL_TO_PRODUCT,
    SkillDispatcher,
)


class SkillDispatcherRegistryIntegrationTest(unittest.TestCase):
    """SkillDispatcher accepts optional SkillRegistry; uses it when provided."""

    def setUp(self):
        from skill_registry import SkillRegistry, load_hardcoded_from_copilot
        self.tmp = Path(tempfile.mkdtemp(prefix="dispatcher_test_"))
        # Use a registry from the real repo (or a fixture) + copilot hardcoded
        self.reg = SkillRegistry.from_skill_dirs(
            REPO_ROOT, hardcoded=load_hardcoded_from_copilot()
        )
        self.dispatcher_with_reg = SkillDispatcher(registry=self.reg)
        self.dispatcher_default = SkillDispatcher()  # legacy hardcoded

    def test_dispatcher_with_registry_uses_registry(self):
        # With a registry, validate must work for any skill in the registry
        # (more than the legacy KNOWN_SKILLS set of 23)
        names = self.reg.discover()
        self.assertGreater(len(names), len(KNOWN_SKILLS),
                           "registry should cover more skills than legacy KNOWN_SKILLS")
        # Some registry-only skills should validate even though they are
        # absent from KNOWN_SKILLS
        registry_only = set(names) - KNOWN_SKILLS
        self.assertGreater(len(registry_only), 0,
                           "expected at least one skill only in registry (e.g. qcloud-agsx-ops)")
        sample = next(iter(registry_only))
        self.assertTrue(self.dispatcher_with_reg.validate_skill(sample),
                        f"registry-backed dispatcher should accept {sample}")
        # Legacy dispatcher should reject it
        self.assertFalse(self.dispatcher_default.validate_skill(sample),
                         f"legacy dispatcher must not accept {sample}")

    def test_dispatcher_with_registry_uses_registry_products(self):
        # get_product goes through registry when provided
        self.assertEqual(
            self.dispatcher_with_reg.get_product("qcloud-cvm-ops"),
            "cvm",
        )

    def test_dispatcher_default_uses_legacy_fallback(self):
        # When no registry is provided, fallback to legacy SKILL_TO_PRODUCT
        # (whatever it returns today must be returned)
        legacy = SKILL_TO_PRODUCT.get("qcloud-cvm-ops")
        self.assertIsNotNone(legacy)
        # Default dispatcher's get_product behavior is unchanged
        self.assertEqual(
            self.dispatcher_default.get_product("qcloud-cvm-ops"),
            legacy,
        )

    def test_dispatcher_resolve_operation_via_registry(self):
        # Use SkillRegistry to resolve "describe" → "describe-instances"
        canonical = self.dispatcher_with_reg.resolve_operation(
            "qcloud-cvm-ops", "describe"
        )
        self.assertEqual(canonical, "describe-instances")

    def test_dispatcher_resolve_param_via_registry(self):
        flag = self.dispatcher_with_reg.resolve_param(
            "qcloud-cvm-ops", "describe-instance"
        )
        self.assertEqual(flag, "InstanceIds.0")

    def test_dispatcher_known_skills_property_intact(self):
        """The exported KNOWN_SKILLS constant is unchanged (backward compat)."""
        self.assertIn("qcloud-cvm-ops", KNOWN_SKILLS)
        self.assertIn("qcloud-vpc-ops", KNOWN_SKILLS)


class SkillDispatcherRegistryConsistencyTest(unittest.TestCase):
    """CI gate: SkillRegistry output must agree with hardcoded KNOWN_SKILLS."""

    def test_registry_superset_of_known_skills(self):
        from skill_registry import SkillRegistry, load_hardcoded_from_copilot
        reg = SkillRegistry.from_skill_dirs(
            REPO_ROOT, hardcoded=load_hardcoded_from_copilot()
        )
        registry_names = set(reg.discover())
        # Registry covers qcloud-*-ops/ directories. Cross-product skills
        # (qcloud-copilot, qcloud-aiops-diagnosis, qcloud-proactive-inspection)
        # have SKILL.md but no -ops suffix; they are intentionally out of
        # SkillRegistry's scope and remain handled by KNOWN_SKILLS fallback.
        ops_backed = {s for s in KNOWN_SKILLS if s.endswith("-ops")}
        for s in ops_backed:
            self.assertIn(s, registry_names,
                          f"KNOWN_SKILLS has {s} (ops-backed) but registry does not")


if __name__ == "__main__":
    unittest.main()