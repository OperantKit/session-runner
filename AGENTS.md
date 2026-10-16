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

## Do not

- Do not call `handle_response` for a concurrent schedule; it routes every response to operandum 0. Use `handle_response_on`.
- Do not forget `end_reinforcement(timestamp)`; the runner stays in the reinforcing state until it is called.
- Do not rely on `handle_response` alone for FI, VI, FT, VT, or DRO; send `handle_tick` on a regular clock.
- Do not pass decreasing timestamps, and do not reuse one runner across subjects or sessions.
- Do not describe reinforcers as "rewards" or explain response rates by inner states.

## Terminology

Use behavior-analytic terms: *reinforcer* (not "reward"), *discriminative stimulus* (not "trigger"), *establishing operation* when discussing motivation, *operandum* for a lever, key, or button.

## Working on this repository

- Python 3.11+. Create the environment with `python -m venv .venv` and `.venv/bin/python -m pip install -e ".[dev]"`; run `.venv/bin/pytest`.
- `README.md` (English) is canonical; keep `README.ja.md` in sync in the same commit.
- Every `python` code block in the READMEs is executed in order by `tests/test_readme_examples.py`.
