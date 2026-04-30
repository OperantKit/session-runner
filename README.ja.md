# session-runner

:gb: [English README](README.md)

OperantKit の手動セッションドライバ。`experiment-core.Session` を
コールバック型 API で包み、emit された全イベントを下流の
`experiment_core.EventSink` に転送する。

## 役割

`session-runner` は任意の入力源（GUI / テスト / シミュレータ /
ハードウェアループ）と `experiment_core.Session` の間に立つ
**ドライバレイヤ**。**ハードウェア・wire format・DSL を知らない**。

| 責務 | パッケージ |
|---|---|
| セッションライフサイクル（イベント） | `experiment-core` |
| **手動駆動（本パッケージ）** | `session-runner` |
| HAL Protocol + ハードウェア駆動 | `experiment-io` |
| OKL v1 永続化 | `session-recorder` |
| DSL パース | `contingency-dsl-py` |
| エンドツーエンド CLI glue | `operant-cli` |

## インストール

```bash
mise exec -- python -m venv .venv
mise exec -- .venv/bin/python -m pip install -e ../experiment-core
mise exec -- .venv/bin/python -m pip install -e ../../core/contingency-py
mise exec -- .venv/bin/python -m pip install -e ../../core/contingency-dsl-py
mise exec -- .venv/bin/python -m pip install -e '.[dev]'
```

## クイックスタート

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

### 永続化と観測の同時実行

`tee()` で複数 sink にイベントをファンアウトできる:

```python
from session_recorder import OklSink
from session_runner import tee

osl_sink = OklSink("session.txt")
osl_sink.write_header(session_name="demo", clock_type="ManualClock", session_start=0.0)

runner = SessionRunner(
    SessionConfig(name="demo", schedule=...),
    sink=tee(InMemorySink(), osl_sink),
)
```

### ハードウェア

`SessionRunner` 自体はハードウェアをポーリングしない。
`handle_response_on` / `handle_tick` / `end_reinforcement` を公開し、
任意のループから駆動できる構造にしている。HAL 駆動ループは
`experiment-io.drive` を参照。

## 公開 API

- `SessionConfig(name, schedule, exit_condition?, metadata?)` — セッション identity。
- `SessionRunner(config, sink?, clock?)` — ドライバ。
  - `start(start_time?)`
  - `handle_response(timestamp)` — 単一コンポーネント
  - `handle_response_on(operandum, timestamp)` — 並立
  - `handle_tick(timestamp)` — 時間ベース / 時間制限
  - `end_reinforcement(timestamp)`
  - `is_finished`, `is_reinforcing`, `total_responses`,
    `component_responses`, `session_metadata`
- `tee(*sinks) -> EventSink` — 複数 sink を結合。

## 開発

```bash
.venv/bin/pytest
.venv/bin/pytest --cov=src --cov-report=term-missing
.venv/bin/ruff check src tests
.venv/bin/black --check src tests
```

## 参考文献

- Ferster, C. B., & Skinner, B. F. (1957). *Schedules of reinforcement*.
  Appleton-Century-Crofts.
