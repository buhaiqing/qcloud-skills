from copilot.models import ExecutionPlan, ClassifiedIntent, IntentType
from copilot.session import SessionManager


def test_session_create():
    sm = SessionManager()
    state = sm.create_session()
    assert state.session_id.startswith("ses-")
    assert state.history == []
    assert state.current_plan is None


def test_session_save_and_load():
    sm = SessionManager()
    state = sm.create_session()
    plan = ExecutionPlan(
        intent=ClassifiedIntent(primary=IntentType.INSPECT, targets=["vm"]), steps=[], context={}
    )
    sm.save_plan(state.session_id, plan)
    loaded = sm.load_session(state.session_id)
    assert loaded is not None
    assert loaded.current_plan is not None


def test_session_history_append():
    sm = SessionManager()
    state = sm.create_session()
    sm.append_history(state.session_id, {"role": "user", "content": "test"})
    loaded = sm.load_session(state.session_id)
    assert len(loaded.history) == 1
