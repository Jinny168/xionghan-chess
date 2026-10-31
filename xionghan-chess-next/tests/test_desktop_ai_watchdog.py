"""AI 看门狗（3-1）：worker 不回信号时，棋盘不能永久锁死。

以前只靠 worker 的两个信号（finished/failed）解锁；worker 崩在原生代码里就再没人解锁，
棋盘连同轮次状态一起卡死。看门狗到点后走**与正常结束同一条**收尾路径（`_release_ai`）。
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
    w.show()
    qt_app.processEvents()
    yield w
    w.close()


def test_watchdog_unlocks_a_stuck_ai(window, qt_app) -> None:
    window.board.locked = True
    window._ai_generation = 7
    window._ai_watchdog(7)
    qt_app.processEvents()

    assert window.board.locked is False, "看门狗没有解除锁定"
    message = window.statusBar().currentMessage()
    assert "超时" in message or "timed out" in message, message


def test_watchdog_ignores_stale_generation(window) -> None:
    """上一局的看门狗不能误伤这一局（否则刚起步就被解锁）。"""
    window.board.locked = True
    window._ai_generation = 9
    window._ai_watchdog(8)
    assert window.board.locked is True


def test_start_ai_schedules_a_watchdog(window, qt_app, monkeypatch) -> None:
    """`start_ai` 必须真的排一个 `limit + 宽限` 的定时器。"""
    from xionghan_chess.desktop import app as app_module

    delays: list[int] = []
    monkeypatch.setattr(app_module.QTimer, "singleShot",
                        staticmethod(lambda ms, fn: delays.append(ms)), raising=False)
    monkeypatch.setattr(window.pool, "start", lambda worker: None, raising=False)

    window.board.locked = False
    window.start_ai()

    assert delays, "start_ai 没有排看门狗"
    assert delays[0] > 0
    window.board.locked = False
