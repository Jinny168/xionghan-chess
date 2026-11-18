"""P1-5 双 AI 观战（桌面单端）行为守卫。

口径：
- 观战期间禁用人手落子（点 / 拖都不生效），悔棋 / 认输 / 提和 / 暂停均被拦下；
- 进入观战把原对局整体保留，演示局写在另一个 Game 对象上；退出逐项还原，
  历史与棋谱不被演示局污染；
- 调速至少三档，暂停 / 继续 / 单步有明确状态位。
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    from xionghan_chess.desktop.ui import theme

    theme.load_bundled_fonts()
    return app


@pytest.fixture()
def window(qt_app, monkeypatch):
    from xionghan_chess.desktop.app import MainWindow

    w = MainWindow()
    # 不真起后台 worker：只验证观战编排，不跑搜索。
    monkeypatch.setattr(w.pool, "start", lambda worker: None, raising=False)
    w.show()
    qt_app.processEvents()
    yield w
    w._spectate_timer.stop()
    w.close()


def test_enter_spectate_uses_separate_game_and_locks_board(window) -> None:
    original = window.game
    window.enter_spectate()

    assert window.spectating is True
    assert window.game is not original, "演示局必须写在独立 Game 对象上，不能改原对局"
    assert window.board.locked is True, "观战期间棋盘必须锁定，禁人手落子"


def test_exit_spectate_restores_original_game_history(window) -> None:
    original = window.game
    before_history = list(original.state.history)
    before_turn = original.state.turn
    before_pieces = len(original.state.pieces)

    window.enter_spectate()
    # 演示局即便已经走了若干手，退出也不能回写原对局。
    demo_move = window.game.rules.legal_moves(window.game.state, window.game.state.turn)[0]
    window.game.move(demo_move)
    assert len(window.game.state.history) == 1

    window.exit_spectate()

    assert window.spectating is False
    assert window.game is original
    assert len(window.game.state.history) == len(before_history), "退出观战后棋谱被演示局污染"
    assert window.game.state.turn == before_turn
    assert len(window.game.state.pieces) == before_pieces


def test_human_move_is_ignored_during_spectate(window) -> None:
    window.enter_spectate()
    demo = window.game
    move = demo.rules.legal_moves(demo.state, demo.state.turn)[0]
    history_before = len(demo.state.history)

    window.human_move(move)

    assert len(demo.state.history) == history_before, "观战态仍接受了人手落子"


def test_management_actions_blocked_during_spectate(window, monkeypatch) -> None:
    window.enter_spectate()
    for method in ("undo_move", "resign_game", "draw_game", "toggle_pause"):
        monkeypatch.setattr(window.game, "undo", lambda *_a, **_k: pytest.fail(f"{method} 不该走原对局"))
        getattr(window, method)()


def test_speed_has_three_tiers_and_state_flags(window) -> None:
    from xionghan_chess.desktop.app import SPECTATE_SPEED_MS

    assert len(SPECTATE_SPEED_MS) >= 3
    window.enter_spectate()

    assert window._spectate_paused is False
    window.toggle_spectate_pause()
    assert window._spectate_paused is True
    window.toggle_spectate_pause()
    assert window._spectate_paused is False

    window.spectate_step()
    assert window._spectate_step_only is True

    first = window._spectate_speed
    window.cycle_spectate_speed()
    assert window._spectate_speed != first
