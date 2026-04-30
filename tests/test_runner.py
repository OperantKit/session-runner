"""Tests for :class:`session_runner.SessionRunner`."""

from __future__ import annotations

import pytest
from experiment_core import (
    InMemorySink,
    ReinforcerEndEvent,
    ReinforcerStartEvent,
    ResponseEvent,
    StateChangeEvent,
)

from session_runner import SessionConfig, SessionRunner, tee

from .conftest import FakeConcurrentFR, FakeFI, FakeFR, ManualClock


def make_runner(
    schedule, *, sink=None, clock=None, name="test", exit_condition=None
) -> SessionRunner:
    return SessionRunner(
        SessionConfig(
            name=name,
            schedule=schedule,
            exit_condition=exit_condition,
        ),
        sink=sink,
        clock=clock or ManualClock(),
    )


@pytest.mark.unit
def test_runner_requires_schedule() -> None:
    with pytest.raises(ValueError, match="schedule is required"):
        SessionRunner(SessionConfig(name="x", schedule=None))


@pytest.mark.unit
def test_runner_attaches_in_memory_sink_by_default() -> None:
    runner = make_runner(FakeFR(n=1))
    assert isinstance(runner.sink, InMemorySink)


@pytest.mark.unit
def test_fr1_reinforces_every_response() -> None:
    sink = InMemorySink()
    runner = make_runner(FakeFR(n=1), sink=sink)
    runner.start(0.0)
    runner.handle_response(timestamp=1.0)
    assert runner.is_reinforcing
    runner.end_reinforcement(timestamp=1.5)
    assert not runner.is_reinforcing
    starts = [e for e in sink.events if isinstance(e, ReinforcerStartEvent)]
    assert len(starts) == 1


@pytest.mark.unit
def test_fr3_reinforces_on_third_response() -> None:
    runner = make_runner(FakeFR(n=3))
    runner.start(0.0)
    runner.handle_response(1.0)
    assert not runner.is_reinforcing
    runner.handle_response(2.0)
    assert not runner.is_reinforcing
    runner.handle_response(3.0)
    assert runner.is_reinforcing


@pytest.mark.unit
def test_fi_requires_both_time_and_response() -> None:
    runner = make_runner(FakeFI(t=2.0))
    runner.start(0.0)
    runner.handle_tick(1.0)
    runner.handle_response(1.5)
    assert not runner.is_reinforcing
    runner.handle_tick(2.5)
    runner.handle_response(2.6)
    assert runner.is_reinforcing


@pytest.mark.unit
def test_concurrent_routes_to_correct_operandum() -> None:
    runner = make_runner(FakeConcurrentFR(ratios=[2, 3]))
    runner.start(0.0)
    runner.handle_response_on(0, 1.0)
    runner.handle_response_on(0, 2.0)
    assert runner.is_reinforcing
    assert runner.session._last_reinforced_operandum == 0


@pytest.mark.unit
def test_handle_response_on_rejects_non_concurrent_schedule() -> None:
    runner = make_runner(FakeFR(n=1))
    runner.start(0.0)
    with pytest.raises(ValueError, match="concurrent schedule"):
        runner.handle_response_on(0, 1.0)


@pytest.mark.unit
def test_handle_response_default_routes_to_operandum_zero_in_concurrent() -> None:
    runner = make_runner(FakeConcurrentFR(ratios=[1, 1]))
    runner.start(0.0)
    runner.handle_response(1.0)
    assert runner.is_reinforcing
    assert runner.component_responses == [1, 0]


@pytest.mark.unit
def test_reinforcement_count_exit() -> None:
    from experiment_core import ReinforcementCountExit

    runner = make_runner(FakeFR(n=1), exit_condition=ReinforcementCountExit(count=2))
    runner.start(0.0)
    for i in range(1, 3):
        runner.handle_response(float(i))
        runner.end_reinforcement(float(i) + 0.1)
    assert runner.is_finished


@pytest.mark.unit
def test_double_end_reinforcement_is_noop() -> None:
    runner = make_runner(FakeFR(n=1))
    runner.start(0.0)
    runner.handle_response(1.0)
    runner.end_reinforcement(1.5)
    runner.end_reinforcement(1.6)  # idempotent


@pytest.mark.unit
def test_total_responses_increments_on_response_during_reinforcing() -> None:
    runner = make_runner(FakeFR(n=1))
    runner.start(0.0)
    runner.handle_response(1.0)
    assert runner.is_reinforcing
    runner.handle_response(1.1)  # arrives while reinforcing
    assert runner.total_responses == 2  # runner counts it
    # but Session.observation drops it
    assert runner.session.observation.total_responses == 1


@pytest.mark.unit
def test_events_mirror_to_sink() -> None:
    sink = InMemorySink()
    runner = make_runner(FakeFR(n=1), sink=sink)
    runner.start(0.0)
    runner.handle_response(1.0)
    runner.end_reinforcement(1.5)
    types = [type(e) for e in sink.events]
    assert ReinforcerStartEvent in types
    assert ReinforcerEndEvent in types
    assert ResponseEvent in types
    assert StateChangeEvent in types


@pytest.mark.unit
def test_tee_fans_out_to_multiple_sinks() -> None:
    a, b = InMemorySink(), InMemorySink()
    runner = make_runner(FakeFR(n=1), sink=tee(a, b))
    runner.start(0.0)
    runner.handle_response(1.0)
    runner.end_reinforcement(1.5)
    assert len(a.events) == len(b.events) > 0


@pytest.mark.unit
def test_state_observers_forward_to_session() -> None:
    runner = make_runner(FakeFR(n=1))
    assert runner.state_name == "IDLE"
    runner.start(0.0)
    assert runner.state_name == "RUNNING"
    assert runner.reinforcement_count == 0
    runner.handle_response(1.0)
    assert runner.reinforcement_count == 1
    assert runner.state_name == "REINFORCING"


@pytest.mark.unit
def test_session_metadata_returns_copy() -> None:
    runner = SessionRunner(
        SessionConfig(name="x", schedule=FakeFR(n=1), metadata={"k": "v"}),
    )
    md = runner.session_metadata
    md["k"] = "tampered"
    assert runner.session_metadata == {"k": "v"}
