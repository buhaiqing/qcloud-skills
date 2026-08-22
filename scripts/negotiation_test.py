from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import negotiation as _neg

NegotiationHub = _neg.NegotiationHub
ResourceOp = _neg.ResourceOp


class NegotiationTest(unittest.TestCase):
    def test_write_vs_read_conflicts(self) -> None:
        hub = NegotiationHub()
        p1 = hub.propose(ResourceOp("a1", "ins-001", "WRITE", priority=1))
        p2 = hub.propose(ResourceOp("a2", "ins-001", "READ", priority=0))
        pairs = hub.detect_conflicts()
        self.assertEqual(pairs, [(p1, p2)])

    def test_read_vs_read_no_conflict(self) -> None:
        hub = NegotiationHub()
        hub.propose(ResourceOp("a1", "ins-001", "READ", priority=1))
        hub.propose(ResourceOp("a2", "ins-001", "READ", priority=0))
        self.assertEqual(hub.detect_conflicts(), [])

    def test_detect_conflicts_pairs(self) -> None:
        hub = NegotiationHub()
        p1 = hub.propose(ResourceOp("a1", "ins-001", "WRITE", priority=1))
        p2 = hub.propose(ResourceOp("a2", "ins-001", "DELETE", priority=2))
        p3 = hub.propose(ResourceOp("a3", "ins-002", "WRITE", priority=3))
        pairs = hub.detect_conflicts()
        self.assertIn((p1, p2), pairs)
        self.assertNotIn((p1, p3), pairs)
        self.assertNotIn((p2, p3), pairs)

    def test_resolve_grants_higher_priority(self) -> None:
        hub = NegotiationHub()
        p_low = hub.propose(ResourceOp("a1", "ins-001", "WRITE", priority=1))
        p_high = hub.propose(ResourceOp("a2", "ins-001", "WRITE", priority=10))
        result = hub.resolve()
        self.assertEqual(result[p_high], "GRANTED")
        self.assertEqual(result[p_low], "DENIED")

    def test_tie_break_by_proposal_id_deterministic(self) -> None:
        hub = NegotiationHub()
        p1 = hub.propose(ResourceOp("a1", "ins-001", "WRITE", priority=5))
        p2 = hub.propose(ResourceOp("a2", "ins-001", "WRITE", priority=5))
        result = hub.resolve()
        # p1 < p2 lexicographically, so p1 wins on equal priority
        self.assertEqual(result[p1], "GRANTED")
        self.assertEqual(result[p2], "DENIED")
        # Deterministic across repeated resolves
        result2 = hub.resolve()
        self.assertEqual(result, result2)

    def test_independent_resources_never_conflict(self) -> None:
        hub = NegotiationHub()
        p1 = hub.propose(ResourceOp("a1", "ins-001", "WRITE", priority=1))
        p2 = hub.propose(ResourceOp("a2", "ins-002", "WRITE", priority=1))
        self.assertEqual(hub.detect_conflicts(), [])
        result = hub.resolve()
        self.assertEqual(result[p1], "GRANTED")
        self.assertEqual(result[p2], "GRANTED")

    def test_non_conflicting_granted(self) -> None:
        hub = NegotiationHub()
        p1 = hub.propose(ResourceOp("a1", "ins-001", "READ", priority=0))
        p2 = hub.propose(ResourceOp("a2", "ins-001", "READ", priority=0))
        result = hub.resolve()
        self.assertEqual(result[p1], "GRANTED")
        self.assertEqual(result[p2], "GRANTED")

    def test_decisions_accessor(self) -> None:
        hub = NegotiationHub()
        p1 = hub.propose(ResourceOp("a1", "ins-001", "WRITE", priority=1))
        self.assertEqual(hub.decisions(), {})
        hub.resolve()
        self.assertEqual(hub.decisions()[p1], "GRANTED")


if __name__ == "__main__":
    unittest.main()
