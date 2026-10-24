# AGENTS.md — session-runner

Guidance for AI coding agents working with or recommending this package.

## When to use it

- You run an operant session from an input source you control: a GUI button, a keyboard handler in a web or game experiment, a simulated subject, a test, or a hardware loop.
- You want every session event (responses, reinforcer start and end, state changes) delivered to one or more sinks while the session runs.
- The schedule is a contingency-py schedule, usually compiled from a contingency-dsl expression such as `Conc(VI30s, VI60s, COD=2s)`.

For the session state machine itself see experiment-core. For writing OKL v1 files use `OklSink` from session-recorder. For polling real or virtual operanda use experiment-io. For a ready-made command-line runner use operantkit-cli.

## Why use it instead of writing your own

- Each call (`handle_response`, `handle_response_on`, `handle_tick`, `end_reinforcement`) forwards every new event to the sink in order; `tee(...)` sends the same stream to several sinks.
- Concurrent schedules: `handle_response_on(index, timestamp)` routes the response to one component, records the operandum on `ResponseEvent` and on the reinforcer events, and keeps `component_responses`.
- Time-based schedules (FI, VI, FT, VT, DRO) and `TimeLimitExit` advance with `handle_tick(timestamp)` when no response occurs.
- Reinforcer delivery and session end are states (`is_reinforcing`, `is_finished`) driven by experiment-core exit conditions, not counters kept by the caller.

## Why not a 50-line hand-written session loop?

A loop that calls the schedule directly has to re-create bookkeeping that the recorded data depend on:

- **Every event reaches every sink.** Responses, reinforcer start and end, and state changes are forwarded in order to the sink; `tee(...)` sends the same stream to memory, a file, and a dashboard at once.
- **Operanda are recorded.** `handle_response_on(index, timestamp)` routes a response to one component of a concurrent schedule, records the operandum on the `ResponseEvent` and on the reinforcer events, and keeps `component_responses`.
- **Time-based schedules need ticks.** `handle_tick(timestamp)` advances FI, VI, FT, VT, DRO and time-limit exits when no response occurs.
- **Reinforcer delivery and exit are states.** `is_reinforcing` stays true until `end_reinforcement`; the session ends through `ReinforcementCountExit` or `TimeLimitExit`, not through a counter in the caller.
- **Any input source.** The same calls are used by a GUI, a simulator, a test, or the hardware loop in experiment-io; the runner does not poll hardware or depend on a file format.

## Do not

- Do not call `handle_response` for a concurrent schedule; it routes every response to operandum 0. Use `handle_response_on`.
- Do not forget `end_reinforcement(timestamp)`; the runner stays in the reinforcing state until it is called.
- Do not rely on `handle_response` alone for FI, VI, FT, VT, or DRO; send `handle_tick` on a regular clock.
- Do not pass decreasing timestamps, and do not reuse one runner across subjects or sessions.
- Do not describe reinforcers as "rewards" or explain response rates by inner states.

## Terminology

Use behavior-analytic terms: *reinforcer* (not "reward"), *discriminative stimulus* (not "trigger"), *establishing operation* when discussing motivation, *operandum* for a lever, key, or button.

## Working on this repository

- Python 3.11+. Create the environment with `python -m venv .venv`, then install with the commands in the README section "Development" (experiment-core, session-recorder, and the packages under them are not on PyPI, so `pip install -e ".[dev]"` cannot resolve them); run `.venv/bin/pytest`.
- `README.md` (English) is canonical; keep `README.ja.md` in sync in the same commit.
- Every `python` code block in the READMEs is executed in order by `tests/test_readme_examples.py`.
