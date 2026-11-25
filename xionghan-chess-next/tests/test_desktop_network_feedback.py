"""断线反馈的**常驻/自动消失**语义（P1-10 迁移的收口）。

## 为什么单独钉这一条

P1-10 把所有反馈从 statusBar 迁到会自己消失的横条之后，出现一个语义回退：
「网络已断开」迁移前是 statusBar 的**常驻**消息（无 timeout），迁移后 8 秒就消失了 ——
玩家还没来得及读，界面就回到了"看起来一切正常"的状态。

裁决（team-lead, G2b）是：终止分支（会话结束 / 不可重连的 close code）**不给超时**，
一直显示到「网络已恢复」把它顶掉；恢复消息照常 5 秒自动消失。这条不用新造常驻指示，
复用的就是同一条反馈条 —— 不碰 banner、不碰侧栏。

## 判据

- 终止断线：`current_level == "error"` 且 `current_timeout_ms == 0`，等一段时间仍可见；
- 网络恢复：`current_level == "success"` 且 `timeout_ms > 0`（会自己走）；
- 恢复消息要能**顶掉**那条常驻的 error（否则界面永远红着）。
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6", reason="断线反馈挂在真实窗口上")

from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.desktop import app as appmod  # noqa: E402
from xionghan_chess.desktop import net  # noqa: E402
from xionghan_chess.desktop.ui import theme  # noqa: E402


class FakeSocket:
    """`_network_disconnected` / `_network_connected` 需要的最小 socket 面。"""

    def __init__(self, close_code: int = 1006) -> None:
        self._close_code = close_code
        self.sent: list[str] = []

    def closeCode(self) -> int:
        return self._close_code

    def deleteLater(self) -> None:  # noqa: N802 - Qt 命名
        pass

    def close(self) -> None:
        """`MainWindow.close_network()` 在窗口关闭时会调它。"""

    def sendTextMessage(self, message: str) -> None:  # noqa: N802 - Qt 命名
        self.sent.append(message)


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def window(monkeypatch: pytest.MonkeyPatch, tmp_path, qt_app: QApplication):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    theme.load_bundled_fonts()
    win = appmod.MainWindow()
    win.show()
    qt_app.processEvents()
    yield win
    win.timer.stop()
    win.close()
    win.deleteLater()


def test_terminal_disconnect_is_persistent(window, qt_app: QApplication) -> None:
    """终止断线（会话已结束）不给超时：一直显示到玩家读到 / 被恢复消息顶掉。"""
    socket = FakeSocket(1006)
    window.network = socket
    window.room_id = None  # `should_reconnect` 的终止条件之一
    window._network_disconnected(socket)

    assert window.feedback.current_level == "error"
    assert window.feedback.current_timeout_ms == 0, "终止断线仍被设了超时，玩家读完之前就会消失"
    assert window.feedback.isVisible()

    QTest.qWait(200)
    qt_app.processEvents()
    assert window.feedback.isVisible(), "常驻的断线提示被定时器收走了"


def test_recovery_message_replaces_the_persistent_error(window, qt_app: QApplication) -> None:
    """「网络已恢复」要能顶掉那条常驻 error，并且自己会走（success，5s）。"""
    socket = FakeSocket(1006)
    window.network = socket
    window.room_id = None
    window._network_disconnected(socket)
    assert window.feedback.current_timeout_ms == 0

    window.token = "tok"
    live = FakeSocket(0)
    window.network = live
    window._network_connected(live)

    assert live.sent, "没有发 auth 帧"
    assert window.feedback.current_level == "success"
    assert window.feedback.current_timeout_ms == 5000, "恢复消息也变成常驻了，界面会一直挂着"


def _drop(window, code: int = 1006, room_id: str | None = "ROOM") -> None:
    """走真实的 `_network_disconnected`；顺手挡住重连定时器，避免测试真的去建连。

    `network_closing` 必须显式置 False：`MainWindow.new_game()` 会先调 `close_network()`，
    那里把它置 True —— 留着的话 `should_reconnect` 恒 False，永远走终止分支。
    """
    window._connect_network = lambda: None
    window.network_closing = False
    socket = FakeSocket(code)
    window.network = socket
    window.room_id = room_id
    window._network_disconnected(socket)


def test_reconnecting_message_is_persistent(window) -> None:
    """「网络中断，正在重连 (n/N)」迁移前也是**无 timeout**，不许变成 6 秒就消失。

    逐次重连时后一条覆盖前一条，所以常驻不会堆积；连上会被「网络已恢复」顶掉。
    """
    window.network_reconnect_attempts = 0
    _drop(window)
    assert window.feedback.current_level == "warn"
    assert window.feedback.current_timeout_ms == 0
    assert "1/" in window.feedback.current_text


def test_reconnect_given_up_message_is_persistent(window) -> None:
    """「自动重连失败，请重新加入房间」是终态，同样原本无 timeout。"""
    window.network_reconnect_attempts = net.MAX_RECONNECT_ATTEMPTS
    _drop(window)
    assert window.feedback.current_level == "error"
    assert window.feedback.current_timeout_ms == 0
    assert "重新加入房间" in window.feedback.current_text
