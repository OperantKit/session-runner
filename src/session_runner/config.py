"""Lightweight session identity carried by :class:`SessionRunner`."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from experiment_core import ExitCondition, Schedule


@dataclass
class SessionConfig:
    """Minimal session identity.

    ``schedule`` must be a :class:`experiment_core.Schedule` (atomic
    ``contingency.Schedule`` or compound
    ``contingency.schedules.concurrent.Concurrent``).
    ``exit_condition`` is optional; when omitted the session runs
    until the caller stops driving it.

    This is a lightweight handle that carries a pre-built schedule
    object rather than a declarative spec — declarative spec parsing
    lives in ``contingency-dsl-py`` + ``contingency-py``'s bridge.
    """

    name: str = "session"
    schedule: Schedule | None = None
    exit_condition: ExitCondition | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
