# session-runner

:gb: [English README](README.md)

session-runner は、反応を生み出すものが何であってもオペラントのセッションを動かします。GUI のボタン、Web やゲームの実験でのキー入力、仮想被験体、テスト、ハードウェアのループのどれでもかまいません。反応ごと、時計の刻みごと、強化子の提示の終わりごとに 1 回呼ぶと、セッションを進め、起きたイベントをそのつど 1 つ以上の受け手（メモリ、OKL のログファイル、実時間の表示器）に送ります。[OperantKit](https://github.com/OperantKit) の中では、[experiment-core](https://github.com/OperantKit/experiment-core) のセッションの上に載る駆動役です。

- **どのイベントも、すべての受け手に順番どおり届きます。** `tee(...)` で同じ流れをメモリ・ファイル・表示器に同時に送れます。
- **並立スケジュールでは、反応と強化子ごとにオペランダム**（レバーやキー）を記録し、オペランダムごとの反応数を数えます。
- **セッションは終了条件**（強化子の回数か制限時間）で終わります。呼び出す側のコードで回数を数える必要はありません。

AI のコーディングエージェント向けの案内は [AGENTS.md](AGENTS.md) にあります。

## インストール

Python 3.11 以上が必要です。session-runner はまだ PyPI に登録されていません。本体とその下のパッケージを、依存の解決をせずに GitHub から入れます。OKL のログファイルを書くには [session-recorder](https://github.com/OperantKit/session-recorder) も加えます。

```bash
G=git+https://github.com/OperantKit
pip install --no-deps $G/contingency-dsl-py $G/contingency-py $G/experiment-core $G/session-runner \
  $G/session-recorder
```

`pip check` はこれらの開発版のあいだの版の不一致を報告しますが、以下の例には影響しません。

## 例

[contingency-dsl](https://github.com/OperantKit/contingency-dsl) で書いた並立スケジュールを、強化子を 3 回提示するまで動かし、すべてのイベントを受け手に集めます。

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
        runner.end_reinforcement(t)  # 1 秒間の強化子への接近
        continue
    operandum = 0 if (t // 10) % 2 == 0 else 1  # 10 秒ごとにオペランダムを切り替え
    runner.handle_response_on(operandum, t)

print(runner.state_name, runner.reinforcement_count, runner.component_responses)
# FINISHED 3 [7, 5]
print([(e["timestamp"], e["operandum"]) for e in sink.to_dicts() if "potency" in e])
# [(3.0, 0), (7.0, 0), (14.0, 1)]  — 強化子の提示時刻と、それを生んだオペランダム
```

被験体は最初の 10 秒はオペランダム 0 で、そのあとはオペランダム 1 で毎秒 1 回反応します。オペランダム 1 での最初の強化子は 14 秒です。2 秒の切替遅延（COD）、つまり切り替え直後に反応を強化しない時間が過ぎてから始まった 5 回の反応（FR 5）によるものです。

### ログファイルを同時に書く

`tee` はイベントを複数の受け手に送ります。session-recorder の `OklSink` は、イベントを OperantKit の素のテキストのログである OKL ファイル（短いヘッダと、1 イベントにつきタブ区切りの 1 行）として書きます。

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

- `SessionConfig(name, schedule, exit_condition=None, metadata={})`: 何を動かすか。
- `SessionRunner(config, sink=None, clock=time.time)`: 駆動役。受け手を渡さないと、イベントは `InMemorySink` に送られます。
  - `start(start_time=None)`
  - `handle_response(timestamp)`: 単一スケジュールでの反応。
  - `handle_response_on(operandum, timestamp)`: 並立スケジュールでの、オペランダム `operandum`（0、1、…）への反応。
  - `handle_tick(timestamp)`: 時間の経過。反応が無いあいだも FI・VI・FT・VT・DRO と制限時間を判定させます。
  - `end_reinforcement(timestamp)`: 強化子の提示の終わり。
  - `is_finished`、`is_reinforcing`、`state_name`、`reinforcement_count`、`total_responses`、`component_responses`、`session_metadata`。
- `tee(*sinks)`: 渡したすべての受け手に転送する 1 つの受け手。

session-runner はハードウェアを読みに行きません。装置を読んでこれらのメソッドを呼ぶループは [experiment-io](https://github.com/OperantKit/experiment-io) の `drive` です。すぐ使えるコマンドラインの実行器には [operantkit-cli](https://github.com/OperantKit/operantkit-cli) を使います。

## 制限

- まだ PyPI に登録されておらず、API は変わることがあります。
- 自前の時計を持ちません。時刻は呼び出す側のコードが渡し、減ってはいけません。時間の精度はそのコードで決まります。
- 並立スケジュールでは、`handle_response` はすべての反応をオペランダム 0 に送ります。`handle_response_on` を使ってください。
- 時間に基づくスケジュールは、`handle_tick` を呼んだときにだけ進みます。
- 1 つの実行器は 1 個体の 1 セッションに使います。

## 開発

```bash
git clone https://github.com/OperantKit/session-runner && cd session-runner
python -m venv .venv
G=git+https://github.com/OperantKit
.venv/bin/python -m pip install --no-deps $G/contingency-dsl-py $G/contingency-py $G/experiment-core $G/session-recorder -e .
.venv/bin/python -m pip install pytest pytest-cov
.venv/bin/pytest
```

## ライセンス

MIT です。[LICENSE](LICENSE) を参照してください。
