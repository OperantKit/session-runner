# session-runner

:jp: [日本語版 README](README.ja.md)

session-runner runs an operant session from whatever produces the responses: a button in a GUI, a key press in a web or game experiment, a simulated subject, a test, or a hardware loop. You call it once per response, per clock tick, and at the end of each reinforcer; it keeps the session going and sends every event, as it happens, to one or more sinks (memory, an OKL log file, a live viewer). Within [OperantKit](https://github.com/OperantKit) it is the driver on top of the session in [experiment-core](https://github.com/OperantKit/experiment-core).

- **Every event reaches every sink, in order.** `tee(...)` sends the same stream to memory, a file, and a viewer at once.
- **Concurrent schedules record the operandum** (lever or key) of each response and reinforcer, and keep a response count per operandum.
- **The session ends by its exit condition** (a number of reinforcers or a time limit), not by a counter in your code.

Notes for AI coding agents are in [AGENTS.md](AGENTS.md).

## Installation

Python 3.11 or newer. session-runner is not on PyPI yet. Install it and the packages under it from GitHub without dependency resolution; add [session-recorder](https://github.com/OperantKit/session-recorder) to write OKL log files:

```bash
G=git+https://github.com/OperantKit
pip install --no-deps $G/contingency-dsl-py $G/contingency-py $G/experiment-core $G/session-runner \
  $G/session-recorder
```

`pip check` reports version mismatches between these development builds; they do not affect the examples below.

## Example

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

The subject responds once per second on operandum 0 for the first 10 s and on operandum 1 afterwards. The first reinforcer on operandum 1 comes at 14 s: five responses (FR 5) that start after the 2-s changeover delay (COD), the time after a switch during which no response is reinforced.

### Writing a log file at the same time

`tee` sends the events to several sinks. `OklSink` from session-recorder writes them as an OKL file, OperantKit's plain-text log: a short header and one tab-separated line per event.

```python
from contingency import ScheduleBuilder
from session_recorder import OklSink
from session_runner import tee

okl_sink = OklSink("session.okl")
okl_sink.write_header(session_name="demo", clock_type="ManualClock", session_start=0.0)

runner = SessionRunner(
    SessionConfig(name="demo", schedule=ScheduleBuilder.fr(3)),
    sink=tee(InMemorySink(), okl_sink),
)
```

## API

- `SessionConfig(name, schedule, exit_condition=None, metadata={})`: what to run.
- `SessionRunner(config, sink=None, clock=time.time)`: the driver. Without a sink, events go to an `InMemorySink`.
  - `start(start_time=None)`
  - `handle_response(timestamp)`: a response under a single schedule.
  - `handle_response_on(operandum, timestamp)`: a response on operandum `operandum` (0, 1, …) under a concurrent schedule.
  - `handle_tick(timestamp)`: the passage of time, so FI, VI, FT, VT, DRO, and time limits are evaluated when no response occurs.
  - `end_reinforcement(timestamp)`: the end of reinforcer delivery.
  - `is_finished`, `is_reinforcing`, `state_name`, `reinforcement_count`, `total_responses`, `component_responses`, `session_metadata`.
- `tee(*sinks)`: one sink that forwards to all of them.

session-runner does not poll hardware; the loop that reads devices and calls these methods is `drive` in [experiment-io](https://github.com/OperantKit/experiment-io). For a ready-made command-line runner use [operantkit-cli](https://github.com/OperantKit/operantkit-cli).

## Limitations

- Not on PyPI yet, and the API can still change.
- The runner keeps no clock of its own: your code passes the timestamps, and they must not decrease. Timing accuracy depends on that code.
- Under a concurrent schedule, `handle_response` sends every response to operandum 0; use `handle_response_on`.
- Time-based schedules advance only when you call `handle_tick`.
- One runner serves one subject in one session.

## Development

```bash
git clone https://github.com/OperantKit/session-runner && cd session-runner
python -m venv .venv
G=git+https://github.com/OperantKit
.venv/bin/python -m pip install --no-deps $G/contingency-dsl-py $G/contingency-py $G/experiment-core $G/session-recorder -e .
.venv/bin/python -m pip install pytest pytest-cov
.venv/bin/pytest
```

## License

MIT. See [LICENSE](LICENSE).
