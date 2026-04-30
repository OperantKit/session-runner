"""Manual session driver for OperantKit.

Wraps :class:`experiment_core.Session` with a callback-style API and
forwards every emitted event to a downstream
:class:`experiment_core.EventSink`.

This package owns *driving* a session from external triggers
(callbacks). Hardware orchestration (HAL polling loops) lives in
``experiment-io``. Persistence (JSONL) lives in ``session-recorder``.
"""

from __future__ import annotations

from .config import SessionConfig
from .runner import SessionRunner, tee

__version__ = "0.0.0"
__all__ = ["SessionConfig", "SessionRunner", "__version__", "tee"]
