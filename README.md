# session-runner

:jp: [日本語版 README](README.ja.md)

Manual session driver for OperantKit. Wraps `experiment-core.Session`
with a callback-style API and forwards every emitted event to a
downstream `experiment_core.EventSink`.

## Role

`session-runner` is the **driver layer** between any input source
(GUI, test harness, simulator, hardware loop) and
`experiment_core.Session`. It does **not** know about hardware, the
on-disk wire format, or DSL syntax.

| Concern | Package |
|---|---|
| Session lifecycle (events) | `experiment-core` |
| **Manual driving (this package)** | `session-runner` |
| HAL Protocols + driving from hardware | `experiment-io` |
| OKL v1 persistence | `session-recorder` |
| DSL parsing | `contingency-dsl-py` |
| End-to-end CLI glue | `operantkit-cli` |

## Installation

```bash
pip install session-runner
```

For development:

```bash
mise exec -- python -m venv .venv
mise exec -- .venv/bin/python -m pip install -e ../experiment-core
mise exec -- .venv/bin/python -m pip install -e ../../core/contingency-py
mise exec -- .venv/bin/python -m pip install -e ../../core/contingency-dsl-py
mise exec -- .venv/bin/python -m pip install -e '.[dev]'
```

## Quick start

```python
from contingency import ScheduleBuilder
from experiment_core import InMemorySink, ReinforcementCountExit
from session_runner import SessionConfig, SessionRunner

sink = InMemorySink()
runner = SessionRunner(
    SessionConfig(
        name="demo",
        schedule=ScheduleBuilder.fr(3),
        exit_condition=ReinforcementCountExit(count=5),
    ),
    sink=sink,
)
runner.start(start_time=0.0)
runner.handle_response(timestamp=1.0)
runner.handle_response(timestamp=2.0)
runner.handle_response(timestamp=3.0)
assert runner.is_reinforcing
runner.end_reinforcement(timestamp=3.1)
```

### Persisting + observing simultaneously

`tee()` fans events out to multiple sinks:

```python
from session_recorder import OklSink
from session_runner import tee

okl_sink = OklSink("session.txt")
okl_sink.write_header(session_name="demo", clock_type="ManualClock", session_start=0.0)

runner = SessionRunner(
    SessionConfig(name="demo", schedule=...),
    sink=tee(InMemorySink(), okl_sink),
)
```

### Hardware

`SessionRunner` does not poll hardware; it exposes
`handle_response_on` / `handle_tick` / `end_reinforcement` so any
loop can drive it. The HAL-driven loop lives in `experiment-io.drive`.

## Public API

- `SessionConfig(name, schedule, exit_condition?, metadata?)` — session identity.
- `SessionRunner(config, sink?, clock?)` — driver.
  - `start(start_time?)`
  - `handle_response(timestamp)` — single-component
  - `handle_response_on(operandum, timestamp)` — concurrent
  - `handle_tick(timestamp)` — time-based / time-limit
  - `end_reinforcement(timestamp)`
  - `is_finished`, `is_reinforcing`, `total_responses`,
    `component_responses`, `session_metadata`
- `tee(*sinks) -> EventSink` — combine multiple sinks.

## Development

```bash
.venv/bin/pytest
.venv/bin/pytest --cov=src --cov-report=term-missing
.venv/bin/ruff check src tests
.venv/bin/black --check src tests
```

## References

- Ferster, C. B., & Skinner, B. F. (1957). *Schedules of reinforcement*.
  Appleton-Century-Crofts.
