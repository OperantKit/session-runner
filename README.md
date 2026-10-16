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

## 30-second example

Run a concurrent schedule written in [contingency-dsl](https://github.com/OperantKit/contingency-dsl) until three reinforcers have been delivered, with every event captured by a sink:

```python
from contingency_dsl import parse
from contingency import from_dsl
from experiment_core import InMemorySink, ReinforcementCountExit
from session_runner import SessionConfig, SessionRunner

sink = InMemorySink()
runner = SessionRunner(
    SessionConfig(
        name="conc-fr",
        schedule=from_dsl(parse("Conc(FR 3, FR 5, COD=2s)")),
        exit_condition=ReinforcementCountExit(count=3),
    ),
    sink=sink,
)
runner.start(start_time=0.0)
t = 0.0
while not runner.is_finished:
    t += 1.0
    if runner.is_reinforcing:
        runner.end_reinforcement(t)  # 1-s reinforcer access
        continue
    operandum = 0 if (t // 10) % 2 == 0 else 1  # switch operanda every 10 s
    runner.handle_response_on(operandum, t)

print(runner.state_name, runner.reinforcement_count, runner.component_responses)
# FINISHED 3 [7, 5]
print([(e["timestamp"], e["operandum"]) for e in sink.to_dicts() if "potency" in e])
# [(3.0, 0), (7.0, 0), (14.0, 1)]  — reinforcer onsets and the operandum that produced them
```

The subject responds once per second on operandum 0 for the first 10 s and on operandum 1 afterwards. The first reinforcer on operandum 1 comes at 14 s: five responses (FR 5) that start after the 2-s changeover delay. To write the same events to an OKL v1 file, add an `OklSink` from [session-recorder](https://github.com/OperantKit/session-recorder) with `tee` (below); for a command-line runner use [operantkit-cli](https://github.com/OperantKit/operantkit-cli).

## Why not a 50-line hand-written session loop?

A loop that calls the schedule directly has to re-create bookkeeping that the recorded data depend on:

- **Every event reaches every sink.** Responses, reinforcer start and end, and state changes are forwarded in order to the sink; `tee(...)` sends the same stream to memory, a file, and a dashboard at once.
- **Operanda are recorded.** `handle_response_on(index, timestamp)` routes a response to one component of a concurrent schedule, records the operandum on the `ResponseEvent` and on the reinforcer events, and keeps `component_responses`.
- **Time-based schedules need ticks.** `handle_tick(timestamp)` advances FI, VI, FT, VT, DRO and time-limit exits when no response occurs.
- **Reinforcer delivery and exit are states.** `is_reinforcing` stays true until `end_reinforcement`; the session ends through `ReinforcementCountExit` or `TimeLimitExit`, not through a counter in the caller.
- **Any input source.** The same calls are used by a GUI, a simulator, a test, or the hardware loop in experiment-io; the runner does not poll hardware or depend on a file format.

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

okl_sink = OklSink("session.okl")
okl_sink.write_header(session_name="demo", clock_type="ManualClock", session_start=0.0)

runner = SessionRunner(
    SessionConfig(name="demo", schedule=ScheduleBuilder.fr(3)),
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
