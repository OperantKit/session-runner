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
| エンドツーエンド CLI glue | `operantkit-cli` |

## インストール

```bash
pip install session-runner
```

開発用:

```bash
mise exec -- python -m venv .venv
mise exec -- .venv/bin/python -m pip install -e ../experiment-core
mise exec -- .venv/bin/python -m pip install -e ../../core/contingency-py
mise exec -- .venv/bin/python -m pip install -e ../../core/contingency-dsl-py
mise exec -- .venv/bin/python -m pip install -e '.[dev]'
```

## 30 秒で動く例

[contingency-dsl](https://github.com/OperantKit/contingency-dsl) で書いた並立スケジュールを、強化子が 3 回提示されるまで動かし、すべてのイベントを sink で受け取る:

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
        runner.end_reinforcement(t)  # 1 秒間の強化子提示
        continue
    operandum = 0 if (t // 10) % 2 == 0 else 1  # 10 秒ごとにオペランダムを切り替える
    runner.handle_response_on(operandum, t)

print(runner.state_name, runner.reinforcement_count, runner.component_responses)
# FINISHED 3 [7, 5]
print([(e["timestamp"], e["operandum"]) for e in sink.to_dicts() if "potency" in e])
# [(3.0, 0), (7.0, 0), (14.0, 1)]  — 強化子の提示時刻と、それを生んだオペランダム
```

被験体は最初の 10 秒はオペランダム 0、その後はオペランダム 1 に 1 秒 1 反応する。オペランダム 1 の最初の強化子は 14 秒で、2 秒の切替遅延 (COD) の後に始まった 5 反応 (FR 5) による。同じイベントを OKL v1 ファイルに書くには、[session-recorder](https://github.com/OperantKit/session-recorder) の `OklSink` を `tee` で足す（下記）。コマンドラインから動かすなら [operantkit-cli](https://github.com/OperantKit/operantkit-cli) を使う。

## 自作の 50 行のセッションループでは足りない理由

スケジュールを直接呼ぶループは、記録データが依存する次の処理を作り直すことになる:

- **すべてのイベントがすべての sink に届く.** 反応・強化子の開始と終了・状態変化を順に sink に送る。`tee(...)` で同じ流れをメモリ・ファイル・ダッシュボードへ同時に送れる。
- **オペランダムが記録される.** `handle_response_on(index, timestamp)` は反応を並立スケジュールの 1 成分に渡し、`ResponseEvent` と強化子イベントにオペランダムを記録し、`component_responses` を保持する。
- **時間に基づくスケジュールには時刻の進行が要る.** 反応が無いときは `handle_tick(timestamp)` で FI・VI・FT・VT・DRO と時間制限による終了を進める。
- **強化子の提示と終了は状態である.** `is_reinforcing` は `end_reinforcement` まで真のまま。セッションは呼び出し側のカウンタではなく `ReinforcementCountExit` か `TimeLimitExit` で終わる。
- **入力源を選ばない.** GUI・シミュレータ・テスト・experiment-io のハードウェアループが同じ呼び出しを使う。ランナーはハードウェアをポーリングせず、ファイル形式にも依存しない。

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

okl_sink = OklSink("session.okl")
okl_sink.write_header(session_name="demo", clock_type="ManualClock", session_start=0.0)

runner = SessionRunner(
    SessionConfig(name="demo", schedule=ScheduleBuilder.fr(3)),
    sink=tee(InMemorySink(), okl_sink),
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
