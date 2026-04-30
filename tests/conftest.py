"""Shared fixtures for session-runner tests.

Tests use real :mod:`contingency` schedules via
:class:`contingency.ScheduleBuilder`. The legacy fixture names
(``FakeFR`` etc.) are preserved as thin wrappers for readability.
"""

from __future__ import annotations

import pytest
from contingency import ScheduleBuilder
from experiment_core import ReinforcementCountExit


def FakeFR(n: int = 1):  # noqa: N802 — preserve legacy fixture name
    return ScheduleBuilder.fr(n)


def FakeFI(t: float = 1.0):  # noqa: N802
    return ScheduleBuilder.fi(t)


def FakeConcurrentFR(ratios: list[int] | None = None):  # noqa: N802
    if ratios is None:
        ratios = [1, 1]
    components = {f"c{i}": ScheduleBuilder.fr(r) for i, r in enumerate(ratios)}
    return ScheduleBuilder.concurrent(components)


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
