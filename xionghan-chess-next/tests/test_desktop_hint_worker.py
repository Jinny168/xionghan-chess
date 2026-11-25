"""P0-2 常规对局提示：`HintWorker` 的行为契约。

## 挡的是什么

提示功能最容易出的错，不是"算不出来"，而是**算出来之后做了不该做的事**：

1. 把结果当成 AI 的落子直接走掉（复用 `AIWorker` 就会这样：它的 `finished`
   在 app 层连着落子）；
2. 搜索期间玩家已经落子，结果回来仍然画到新局面上（过期结果）；
3. 为了让提示"聪明一点"顺手接个云端接口 —— 项目零遥测硬约束，一步都不许。

本文件钉的是第 1 条（不落子）与第 3 条（零网络/零存储原语）。第 2 条在
`_apply_move_hint` 的请求号/棋谱长度双判据里，属于 app 层，用源码守卫覆盖。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from xionghan_chess.core.ai import Difficulty
from xionghan_chess.core.game import Game
from xionghan_chess.desktop.ui.workers import HintWorker

ROOT = Path(__file__).resolve().parents[1]
WORKERS = ROOT / "src" / "xionghan_chess" / "desktop" / "ui" / "workers.py"
APP = ROOT / "src" / "xionghan_chess" / "desktop" / "app.py"

#: 零遥测原语。桌面端**任何**地方都不该出现，提示更不能为了"更准"接一个上去。
TELEMETRY = ("XMLHttpRequest", "sendBeacon", "localStorage", "sessionStorage", "fetch(")


def test_hint_worker_returns_a_legal_move_for_the_side_to_move() -> None:
    """初始局面下返回的着法必须属于**当前走子方**，且真的合法。"""
    game = Game()
    mover = game.state.turn
    worker = HintWorker(game)
    captured: list[object] = []
    worker.signals.finished.connect(captured.append)
    worker.run()

    assert captured, "worker 没有发 finished"
    move = captured[0]
    assert move is not None, "初始局面算不出着法，提示功能等于不可用"
    legal = game.rules.legal_moves(game.state, mover)
    assert move in legal, f"{move} 不在 {mover} 的合法着法里"
    piece = game.state.piece_at(move.source)
    assert piece is not None and piece.color is mover


def test_hint_worker_never_plays_the_move() -> None:
    """跑完 worker 后棋谱长度**不变**：提示只回着法，落子永远由玩家完成。"""
    game = Game()
    before = len(game.state.history)
    worker = HintWorker(game)
    worker.run()
    assert len(game.state.history) == before, "提示把棋走了 —— 这不叫提示，叫代打"
    assert len(worker.game.state.history) == before


def test_hint_worker_does_not_touch_the_source_game() -> None:
    """worker 在**克隆**上搜索：原 `Game` 的走子方与局面指纹都不许被动到。"""
    game = Game()
    snapshot = game.state.to_dict()
    worker = HintWorker(game)
    worker.run()
    assert worker.game is not game
    assert game.state.to_dict() == snapshot


def test_hint_worker_uses_the_beginner_tier() -> None:
    """提示走入门档：给的是"能下的一步"，不是"最强的一步"（否则等于替人打）。"""
    game = Game()
    worker = HintWorker(game)
    assert worker.ai.difficulty is Difficulty.BEGINNER
    assert worker.ai.time_scale is None, "提示不该被标定缩放影响：那是基准测试的开关"


def test_hint_path_has_no_network_or_storage_primitives() -> None:
    """零遥测：worker 与 app 里都不许出现 fetch / XHR / beacon / localStorage。"""
    for path in (WORKERS, APP):
        text = path.read_text(encoding="utf-8")
        hits = [token for token in TELEMETRY if token in text]
        assert hits == [], f"{path.name} 出现遥测/浏览器存储原语：{hits}"


def test_hint_worker_is_kept_alive_by_the_window() -> None:
    """在飞的 worker 必须被强引用。

    实测踩过：`QThreadPool.start(worker)` 之后局部变量出作用域，worker 的 Python 包装
    被回收 → 它身上的 `signals` 子对象跟着销毁 → 连接**静默失效**（不报错、不回调，
    表现为"按了提示没反应"）。AI 那条路径靠 bound method 侥幸躲过，lambda 连接躲不过。
    """
    body = APP.read_text(encoding="utf-8")
    block = body.split("def show_move_hint", 1)[1].split("\n    def ", 1)[0]
    assert "self._hint_worker = worker" in block, "worker 没被保住引用：提示回调会静默丢失"


def test_hint_result_is_validated_against_the_current_position() -> None:
    """过期结果双判据在 `_apply_move_hint` 里：请求号 + 棋谱长度。"""
    body = APP.read_text(encoding="utf-8")
    block = body.split("def _apply_move_hint", 1)[1].split("\n    def ", 1)[0]
    assert "request_id != self._hint_request_id" in block, "缺少请求号校验：连按两次提示会画旧结果"
    assert "len(self.game.state.history) != plies" in block, "缺少棋谱长度校验：搜索期间落子后仍会画提示"
    assert re.search(r"self\.board\.legal = \[move\]", block), "提示没有落到棋盘高亮上"


@pytest.mark.parametrize("token", TELEMETRY)
def test_telemetry_token_list_is_non_empty(token: str) -> None:
    """自检：守卫清单本身别被写空（空清单永远绿）。"""
    assert token.strip()
