"""Manual session driver.

:class:`SessionRunner` wraps :class:`experiment_core.Session` and
exposes a small callback-style API (``start``, ``handle_response``,
``handle_response_on``, ``handle_tick``, ``end_reinforcement``) for
arbitrary input sources (GUI, test harness, hardware loop, simulator).

Every event the underlying :class:`~experiment_core.session.Session`
produces is mirrored to a downstream
:class:`~experiment_core.EventSink`. Multiple sinks are supported
via :func:`tee`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from experiment_core import (
    EventSink,
    InMemorySink,
    ResponseEvent,
    Session,
    SessionEvent,
    SessionState,
)

from .config import SessionConfig


def tee(*sinks: EventSink) -> EventSink:
    """Combine N sinks into a single :class:`EventSink`.

    Useful for running the same session against an in-memory sink
    (for assertions) and an OKL v1 sink (for persistence).
    """

    class _Tee:
        def emit(self, event: SessionEvent) -> None:
            for s in sinks:
                s.emit(event)

    return _Tee()


class SessionRunner:
    """Manual session driver.

    Callers advance the session by invoking :meth:`handle_response`
    (single-component), :meth:`handle_response_on` (concurrent), or
    :meth:`handle_tick` (time-based). Every produced
    :class:`~experiment_core.events.SessionEvent` is forwarded to
    ``sink``.

    If no sink is supplied the runner attaches an
    :class:`~experiment_core.InMemorySink`, accessible via
    :attr:`sink`.
    """

    def __init__(
        self,
        config: SessionConfig,
        sink: EventSink | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if config.schedule is None:
            raise ValueError("SessionConfig.schedule is required")
        self.config = config
        self.sink: EventSink = sink if sink is not None else InMemorySink()
        self._clock = clock
        self._mirrored_count = 0

        self.session = Session(
            schedule=config.schedule,
            exit_condition=config.exit_condition,
        )
        self.total_responses = 0
        # Per-operandum response counts. Non-empty only for concurrent schedules.
        self.component_responses: list[int] = (
            [0] * len(self.session._concurrent_component_keys)
            if self.session._is_concurrent
            else []
        )

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start(self, start_time: float | None = None) -> None:
        """Begin the session.

        Calls the underlying :meth:`Session.start` and forwards any
        emitted events to the sink. The companion ``session_meta``
        header record (if desired) is the writer's concern, not the
        runner's — see :meth:`session_recorder.OklSink.write_header`.
        """
        if start_time is None:
            start_time = self._clock()
        self.session.start(start_time)
        self._sync_events()

    def handle_response(self, timestamp: float) -> None:
        """Record a response on the (implicit) single operandum.

        For concurrent schedules the response is routed to operandum
        ``0`` as a legacy single-operandum fallback. New code should
        prefer :meth:`handle_response_on`.
        """
        self.total_responses += 1
        self.session.events.append(ResponseEvent(id=self.total_responses, timestamp=timestamp))
        if self.session._is_concurrent:
            self.component_responses[0] += 1
            self.session.handle_response_on(0, timestamp)
        else:
            self.session.update(timestamp, self.total_responses)
        self._sync_events()

    def handle_response_on(self, operandum: int, timestamp: float) -> None:
        """Record a response on a specific operandum (concurrent only)."""
        if not self.session._is_concurrent:
            raise ValueError(
                "handle_response_on requires a concurrent schedule; "
                "use handle_response() for single-component sessions."
            )
        self.total_responses += 1
        self.component_responses[operandum] += 1
        self.session.events.append(ResponseEvent(id=self.total_responses, timestamp=timestamp))
        self.session.handle_response_on(operandum, timestamp)
        self._sync_events()

    def handle_tick(self, timestamp: float) -> None:
        """Advance the session by a pure time tick (no new response).

        Required for time-based schedules (FI, VI, FT, VT, DRO) and
        for time-limit exit conditions to fire.
        """
        self.session.update(timestamp, self.total_responses)
        self._sync_events()

    def end_reinforcement(self, timestamp: float) -> None:
        """Conclude the pending reinforcer delivery."""
        self.session.end_reinforcement(timestamp)
        self._sync_events()

    # ------------------------------------------------------------------
    # Internal bookkeeping
    # ------------------------------------------------------------------

    def _sync_events(self) -> None:
        """Forward any new session events to the sink."""
        while self._mirrored_count < len(self.session.events):
            event = self.session.events[self._mirrored_count]
            self.sink.emit(event)
            self._mirrored_count += 1

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @property
    def is_finished(self) -> bool:
        return self.session.state == SessionState.FINISHED

    @property
    def is_reinforcing(self) -> bool:
        return self.session.state == SessionState.REINFORCING

    @property
    def reinforcement_count(self) -> int:
        """Forwards :attr:`Session.reinforcement_count` for observers."""
        return self.session.reinforcement_count

    @property
    def state_name(self) -> str:
        """Forwards :attr:`Session.state.name` for observers."""
        return self.session.state.name

    @property
    def session_metadata(self) -> dict[str, Any]:
        """Convenience: the metadata dict from the attached config."""
        return dict(self.config.metadata)
