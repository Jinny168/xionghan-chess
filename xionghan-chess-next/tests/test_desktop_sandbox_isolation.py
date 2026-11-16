"""推演沙盘的三层隔离守卫。

沙盘最容易出的不是"走不了"，而是**静默污染权威对局**：棋盘还是那块棋盘，
信号却接到了 app.human_move，或者滑块把棋盘指向了一份过期 Game。这些都不会
报错，只会在玩家关掉复盘后从棋谱里冒出来。所以这里的断言全部盯着"权威状态
逐字节没动"和"控制面确实互斥"，而不是"沙盘能走几步"。
"""

from __future__ import annotations

import json
import os
import random
import statistics
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

pytest.importorskip("PySide6", reason="桌面端沙盘 GUI 用例依赖 PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import Color  # noqa: E402
from xionghan_chess.desktop.sandbox import (  # noqa: E402
    SANDBOX_CLOCK_MS,
    build_sandbox_game,
    undo_sandbox_move,
)
from xionghan_chess.desktop.ui.dialogs import ReplayDialog  # noqa: E402


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _first_move(game: Game):
    moves = game.rules.legal_moves(game.state)
    assert moves, "测试局面无合法着法"
    return moves[0]


def _played_game(plies: int, seed: int | None = None) -> Game:
    """seed=None 用固定首着（短局面）；给 seed 则随机，避免长局面提前重复判和。"""
    rng = random.Random(seed) if seed is not None else None
    game = Game()
    for _ in range(plies):
        moves = game.rules.legal_moves(game.state)
        assert moves, "测试局面无合法着法"
        game.move(rng.choice(moves) if rng else moves[0])
    return game


def _bytes(state: object) -> bytes:
    return json.dumps(state.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")


def test_sandbox_move_leaves_authoritative_state_byte_identical() -> None:
    """权威走 5 手后开沙盘试走 6 手悔 3 手，权威状态必须逐字节不变。

    红证路径：把 `build_sandbox_game` 改成直接 `return game`（错误接线），
    这条立刻会在试走第 1 手后红 —— 沙盘与权威共享了同一个 state 对象。
    """
    game = _played_game(5)
    before = _bytes(game.state)
    before_history = [record.notation for record in game.state.history]
    before_counts = dict(game.state.position_counts)
    before_clocks = dict(game.state.clocks_ms)

    sandbox = build_sandbox_game(game)
    assert sandbox is not game
    assert sandbox.state is not game.state

    for _ in range(6):
        sandbox.move(_first_move(sandbox))
    for _ in range(3):
        assert undo_sandbox_move(sandbox)

    assert _bytes(game.state) == before, "权威 state.to_dict() 被沙盘改动了"
    assert [record.notation for record in game.state.history] == before_history, "沙盘着法进了权威棋谱"
    assert game.state.position_counts == before_counts, "权威重复局面计数被污染"
    assert game.state.clocks_ms == before_clocks, "权威时钟被沙盘消费"


def test_sandbox_clock_is_not_consumed() -> None:
    """24h 哨兵足够长；沙盘 tick 不花权威的钟。"""
    game = _played_game(2)
    before = dict(game.state.clocks_ms)
    sandbox = build_sandbox_game(game)
    assert all(value == SANDBOX_CLOCK_MS for value in sandbox.state.clocks_ms.values())

    time.sleep(0.05)
    sandbox.move(_first_move(sandbox))
    assert game.state.clocks_ms == before
    assert all(0 < value <= SANDBOX_CLOCK_MS for value in sandbox.state.clocks_ms.values())


def test_sandbox_from_finished_position_can_move_and_undo() -> None:
    """终局局面也能试走：构造时已清 winner/result_reason/draw。"""
    game = Game()
    game.state.winner = Color.RED
    game.state.result_reason = "resignation"
    assert game.state.finished

    sandbox = build_sandbox_game(game)
    assert not sandbox.state.finished
    sandbox.move(_first_move(sandbox))  # 不抛 GameError
    assert undo_sandbox_move(sandbox)


def test_sandbox_undo_needs_explicit_snapshots() -> None:
    """from_state 不重建快照，起点必须手工补一格；起点悔棋返回 False。"""
    game = Game()
    sandbox = build_sandbox_game(game)
    assert len(sandbox._snapshots) >= 1
    assert undo_sandbox_move(sandbox) is False

    start = sandbox.state.to_dict()
    sandbox.move(_first_move(sandbox))
    assert undo_sandbox_move(sandbox)
    after = sandbox.state.to_dict()
    # Game.move 的快照在 tick() 之后拍，悔棋后时钟会差几毫秒（既有语义）；
    # 棋盘/回合/历史必须完全回到起点，时钟仍应是 24h 哨兵而非被消费掉。
    start.pop("clocksMs")
    after.pop("clocksMs")
    assert after == start, "悔 1 手应回到沙盘起点"
    assert all(0 < value <= SANDBOX_CLOCK_MS for value in sandbox.state.clocks_ms.values())


def test_replay_scrub_blocked_while_sandbox_active(qt_app: QApplication) -> None:
    """GUI：沙盘态拖滑块不得把棋盘指向复盘 Game；退出后恢复只读复盘。"""
    game = _played_game(3)
    dialog = ReplayDialog(game, {"language": "zh-CN"})
    replay_game = dialog.board.game

    dialog.tabs.setCurrentIndex(1)
    sandbox = dialog._sandbox_game
    assert sandbox is not None and sandbox is not replay_game
    assert dialog.board.game is sandbox
    assert dialog.board.interactive is True
    assert not dialog.slider.isEnabled() and not dialog.moves.isEnabled()

    # 控制面互斥：setValue 会发 valueChanged → show_step，但入口已被挡住。
    dialog.slider.setValue(0)
    assert dialog.board.game is sandbox

    dialog.tabs.setCurrentIndex(0)
    assert dialog._sandbox_game is None
    assert isinstance(dialog.board.game, Game) and dialog.board.game is not sandbox
    assert dialog.board.interactive is False
    assert dialog.slider.isEnabled() and dialog.moves.isEnabled()
    dialog.close()


def test_clone_latency_budget() -> None:
    """clone 是每次进入/重置沙盘的固定开销：100ply 局面中位数 ≤2ms、p95 ≤3.5ms。"""
    game = _played_game(100, seed=0)
    assert len(game.state.history) == 100, f"只走到 {len(game.state.history)} 手，延迟样本不成立"

    samples: list[float] = []
    for _ in range(2000):
        started = time.perf_counter()
        game.state.clone()
        samples.append((time.perf_counter() - started) * 1000)

    median = statistics.median(samples)
    p95 = sorted(samples)[int(0.95 * len(samples))]
    assert median <= 2.0, f"clone 中位数 {median:.3f}ms > 2.0ms"
    assert p95 <= 3.5, f"clone p95 {p95:.3f}ms > 3.5ms"
