"""2-1：聊天区限 200 条，换局清空，悔棋不清。

原实现只追加不清空：长局内存线性涨；而且换局后上一局的聊天还留在那里。
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
def window(qt_app):
    from xionghan_chess.desktop.app import MainWindow

    w = MainWindow()
    yield w
    w.close()


def test_chat_keeps_only_the_latest_200(window, qt_app) -> None:
    from xionghan_chess.desktop.app import CHAT_HISTORY_LIMIT

    for index in range(300):
        window._append_chat(f"第 {index} 条")
    qt_app.processEvents()

    assert window.chat_messages.count() == CHAT_HISTORY_LIMIT
    assert window.chat_messages.item(CHAT_HISTORY_LIMIT - 1).text() == "第 299 条"
    assert window.chat_messages.item(0).text() == "第 100 条"


def test_new_game_clears_chat(window, qt_app, monkeypatch) -> None:
    # `new_game` 会按配置拉起 AI worker（测试里没必要，而且线程池会拖住解释器退出）。
    monkeypatch.setattr(window, "start_ai", lambda: None)
    for index in range(5):
        window._append_chat(f"第 {index} 条")
    window.new_game()
    qt_app.processEvents()
    assert window.chat_messages.count() == 0


def test_undo_does_not_clear_chat(window, qt_app, monkeypatch) -> None:
    """聊天是历史，不该被悔棋回滚。

    注意：**必须真有一步棋可悔**——无棋可悔时 `undo_move` 会弹模态提示框，
    在测试里会永久阻塞（这条踩过）。
    """
    monkeypatch.setattr(window, "start_ai", lambda: None)
    window.new_game()

    move = next(iter(window.game.rules.legal_moves(window.game.state)))
    window.game.move(move)

    window._append_chat("保留这条")
    before = window.chat_messages.count()
    window.undo_move()
    qt_app.processEvents()
    assert window.chat_messages.count() == before
