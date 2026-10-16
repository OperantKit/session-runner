"""Shared fixtures for session-runner tests.

Tests build real :mod:`contingency` schedules directly via
:class:`contingency.ScheduleBuilder`.
"""

from __future__ import annotations

import pytest
from experiment_core import ReinforcementCountExit


class ManualClock:
    """Deterministic monotonic clock for tests."""

    __name__ = "ManualClock"

    def __init__(self, start: float = 0.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, delta: float) -> float:
        self._t += delta
        return self._t


@pytest.fixture
def manual_clock() -> ManualClock:
    return ManualClock()


@pytest.fixture
def reinforcement_count_exit():
    return lambda n: ReinforcementCountExit(count=n)
