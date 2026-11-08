from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Move, Position
from xionghan_chess.training.encoding import ACTION_SIZE, FEATURE_SIZE, action_index, encode_state
from xionghan_chess.training.selfplay import append_jsonl, collect_game


def test_training_encoding_and_action_ids_are_stable():
    game = Game("traditional")
    encoded = encode_state(game.state)
    assert len(encoded) == FEATURE_SIZE
    assert set(encoded) <= {-1.0, 0.0, 1.0}
    index = action_index(Move(Position(0, 0), Position(12, 12)))
    assert 0 <= index < ACTION_SIZE
    assert index == 168


def test_selfplay_writes_versioned_local_jsonl(tmp_path):
    samples = collect_game(simulations=1, max_plies=2, seed=4)
    assert len(samples) == 2
    assert all(item["schema"] == 1 for item in samples)
    target = tmp_path / "samples.jsonl"
    assert append_jsonl(target, samples) == 2
    loaded = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
    assert loaded == samples


def test_numpy_policy_value_training_smoke() -> None:
    """训练链路冒烟：**在独立子进程里跑** `tests/_smoke_training_impl.py`。

    ## 为什么隔离（不是跳过、也不是标 slow 摘出门禁）

    整跑 `pytest tests/` 时，这条排在最后，会在原生层把进程打死（无 traceback）。
    复现与排除：`git stash` 回到 `512cb56` 干净树仍崩；逐文件跑 / 分段跑都过；
    把它排到最前跑也过。所以不是断言逻辑的问题，而是"累积的进程状态 + 一次大块 numpy 分配"
    触发的原生崩溃，根因未定（疑似 Qt 对象/位图缓存与 numpy 的内存交互）。

    处置＝**隔离执行、保留覆盖**：换一个干净解释器跑同一段逻辑，断言退出码与完成标记。
    """
    pytest.importorskip("numpy")
    script = Path(__file__).with_name("_smoke_training_impl.py")
    completed = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, timeout=300, cwd=str(script.parent.parent),
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0 or "TRAINING_SMOKE_OK" not in output:
        tail = "\n".join(output.strip().splitlines()[-30:])
        pytest.fail(f"训练冒烟子进程失败（returncode={completed.returncode}）\n{tail}")
