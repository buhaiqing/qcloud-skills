"""P2.7 — ObservationType classification aligned with Langfuse semantics.

Rules (per SPEC §14.5):
  - Generator / Critic / Summarizer → GENERATION (produces output content)
  - Skill / API call / Verification / SafetyGate → SPAN (executes a unit of work)
  - Plain "Event" markers / unclassified / state-change emitters → EVENT
"""
from __future__ import annotations


def test_classify_generator_critic_summarizer_is_generation():
    from copilot.observation_classifier import classify_observation_type

    for name in [
        "gcl-generator",
        "Generator",
        "gcl-critic",
        "Critic",
        "summarizer",
        "report-summarizer",
    ]:
        kind = classify_observation_type(name=name)
        assert kind.value == "GENERATION", f"{name} should be GENERATION, got {kind.value}"


def test_classify_skill_api_verification_is_span():
    from copilot.observation_classifier import classify_observation_type

    for name in [
        "qcloud-cvm-ops:DescribeInstances",
        "skill_call:qcloud-monitor-ops",
        "tccli cvm DescribeInstances",
        "api-call",
        "verification:rubric",
        "safety.l2_confirm",
        "safety.l0_format",
        "skill-execute",
    ]:
        kind = classify_observation_type(name=name)
        assert kind.value == "SPAN", f"{name} should be SPAN, got {kind.value}"


def test_classify_event_for_plain_event_names():
    from copilot.observation_classifier import classify_observation_type

    for name in [
        "trace.start",
        "session.init",
        "trace.end",
        "blackboard-init",
    ]:
        kind = classify_observation_type(name=name)
        assert kind.value == "EVENT", f"{name} should be EVENT, got {kind.value}"


def test_classify_with_kind_override():
    """Explicit kind wins over heuristic name inference."""
    from copilot.observation_classifier import classify_observation_type

    # Even with a "generator" name, explicit kind=SPAN is honored
    kind = classify_observation_type(name="gcl-generator", kind="SPAN")
    assert kind.value == "SPAN"


def test_classify_unknown_falls_back_to_event():
    from copilot.observation_classifier import classify_observation_type

    kind = classify_observation_type(name="something-ambiguous-xyz")
    assert kind.value == "EVENT"


def test_classify_returns_enum_instance():
    from copilot.observation_classifier import classify_observation_type
    from copilot.trace_records import ObservationType

    kind = classify_observation_type(name="gcl-generator")
    assert isinstance(kind, ObservationType)
