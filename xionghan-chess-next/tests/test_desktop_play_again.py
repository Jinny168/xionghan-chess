"""结束态「再来一局」：弹窗主按钮 / 右栏入口 / Enter 三个口子。

## 为什么必须两个入口都做

结果弹窗是**模态**的 —— 只加右栏按钮的话，玩家在弹窗上点不到它；
反过来只做弹窗，关掉之后再想重开又要去菜单里找。所以：
`show_result_dialog()` 提供主按钮，右栏 `self.again` 提供常驻入口，
`keyPressEvent` 的 Enter 提供快捷入口，三者最终都走 `trigger_play_again()`。

## 三个"不该出现"的场景

残局题（`puzzle_session`）、联机局（`network`）、未终局 —— 前者重开会丢题目会话，
中者新局要双方重新进房，后者没有"结束"可言。这三条在 `can_play_again()` 里统一判。
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="桌面端用例依赖 PySide6")

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QKeyEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from xionghan_chess.core.model import Color  # noqa: E402
from xionghan_chess.desktop import app as appmod  # noqa: E402
from xionghan_chess.desktop.ui import theme  # noqa: E402


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _finish(window) -> None:
    """把当前对局判成红胜（不关心怎么赢的，只要 `state.finished`）。"""
    window.game.state.winner = Color.RED
    window.game.state.result_reason = "checkmate"


@pytest.fixture()
def window(qt_app: QApplication, monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    theme.load_bundled_fonts()
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))
    # 默认静默结果弹窗（返回"未点再来一局"），个别用例再单独改写
    monkeypatch.setattr(appmod, "show_result_dialog", staticmethod(lambda *a, **k: False))
    win = appmod.MainWindow()
    win.config["language"] = "zh-CN"
    yield win
    win.timer.stop()
    win.thinking_timer.stop()
    win.close()
    win.deleteLater()


def drain(qt_app: QApplication, rounds: int = 4) -> None:
    """跑几轮事件循环。

    一次重开会经过**两层** `QTimer.singleShot(0, ...)`（弹窗回调 → trigger → new_game），
    单跑一轮 `processEvents()` 只够推进一层。
    """
    for _ in range(rounds):
        qt_app.processEvents()


# ---------------------------------------------------------------------------
# 1) 弹窗上的两个按钮
# ---------------------------------------------------------------------------
def test_result_dialog_has_play_again_as_default(qt_app: QApplication) -> None:
    box, again = appmod.build_result_dialog(None, "对局结束", "红方胜", "zh-CN", allow_again=True)
    assert again is not None
    assert again.text() == "再来一局"
    assert box.buttonRole(again) is QMessageBox.ButtonRole.AcceptRole
    assert box.defaultButton() is again, "「再来一局」必须是默认按钮（回车即可重开）"

    others = [button for button in box.buttons() if button is not again]
    assert len(others) == 1 and others[0].text() == "关闭"
    assert box.buttonRole(others[0]) is QMessageBox.ButtonRole.RejectRole
    box.deleteLater()


def test_result_dialog_hides_play_again_where_it_is_not_allowed(qt_app: QApplication) -> None:
    """残局题 / 联机局 / 未终局的弹窗只给「关闭」。"""
    box, again = appmod.build_result_dialog(None, "对局结束", "红方胜", "zh-CN", allow_again=False)
    assert again is None
    assert [button.text() for button in box.buttons()] == ["关闭"]
    box.deleteLater()


def test_dialog_choice_starts_exactly_one_new_game(window, monkeypatch) -> None:
    """点「再来一局」→ 开新局、历史归零；且结果弹窗只出现一次。"""
    _finish(window)
    shown: list[int] = []

    def fake_dialog(*args, **kwargs) -> bool:
        shown.append(1)
        return True

    monkeypatch.setattr(appmod, "show_result_dialog", staticmethod(fake_dialog))
    before = window.game
    window._settle_finished(window.game.state, "zh-CN")
    drain(QApplication.instance())
    assert shown == [1], "结果弹窗应当只出现一次"
    assert window.game is not before, "点「再来一局」后应当换成新的一局"
    assert window.game.state.history == [], "新局的历史应当为空"
    assert not window.game.state.finished

    # 再 refresh 一次：新局未终局，不得再弹
    window.refresh()
    assert shown == [1], "新局刷新不得重复弹结果框"


# ---------------------------------------------------------------------------
# 2) 右栏按钮的启用状态
# ---------------------------------------------------------------------------
def test_again_button_is_disabled_until_the_game_ends(window) -> None:
    window.refresh()
    assert window.again.text() == "再来一局"
    assert not window.again.isEnabled(), "未终局时不该能点"

    _finish(window)
    window.refresh()
    assert window.again.isEnabled(), "终局后应当可点"


def test_again_is_disabled_by_pending_guard(window) -> None:
    """连点保护：第一次点击后按钮立刻置灰，第二次点击被吃掉。"""
    _finish(window)
    window.refresh()
    assert window.again.isEnabled()
    window.trigger_play_again()
    assert window._play_again_pending is True
    assert not window.again.isEnabled()


def test_two_clicks_open_only_one_game(window, monkeypatch) -> None:
    _finish(window)
    window.refresh()
    calls: list[int] = []
    real_new_game = window.new_game

    def counting_new_game() -> None:
        calls.append(1)
        real_new_game()

    monkeypatch.setattr(window, "new_game", counting_new_game)
    window.trigger_play_again()
    window.trigger_play_again()          # 第二下应当被 `_play_again_pending` 吃掉
    drain(QApplication.instance())
    assert len(calls) == 1, f"连点两次开了 {len(calls)} 局"


# ---------------------------------------------------------------------------
# 3) Enter 键
# ---------------------------------------------------------------------------
def _press_enter(window) -> None:
    event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
    window.keyPressEvent(event)


def test_enter_starts_a_new_game_after_the_game_ended(window) -> None:
    _finish(window)
    window.refresh()
    _press_enter(window)
    drain(QApplication.instance())
    assert window.game.state.history == [] and not window.game.state.finished


def test_enter_does_nothing_before_the_game_ends(window) -> None:
    window.refresh()
    before = window.game
    _press_enter(window)
    drain(QApplication.instance())
    assert window.game is before, "未终局时 Enter 不得开新局"


def test_enter_does_nothing_when_a_modal_is_open(window, monkeypatch) -> None:
    _finish(window)
    window.refresh()
    monkeypatch.setattr(QApplication, "activeModalWidget", staticmethod(lambda: object()))
    before = window.game
    _press_enter(window)
    drain(QApplication.instance())
    assert window.game is before, "有模态框时 Enter 应当被忽略"


# ---------------------------------------------------------------------------
# 4) 残局题 / 联机局：不给入口
# ---------------------------------------------------------------------------
class _FakeSession:
    """只提供横幅会读的字段（`cursor` / `total` / `puzzle.title`）。"""

    cursor = 0
    total = 3

    class puzzle:            # noqa: N801 - 仅作占位
        title = "测试题"


def test_puzzle_session_blocks_play_again(window) -> None:
    _finish(window)
    window.puzzle_session = _FakeSession()
    window.refresh()
    assert not window.can_play_again()
    assert not window.again.isEnabled()
    before = window.game
    _press_enter(window)
    drain(QApplication.instance())
    assert window.game is before


class _FakeSocket:
    """`close_network()` 在 teardown 会调 `close()` / `deleteLater()`，这里给两个空实现。"""

    closed = False

    def close(self) -> None:
        self.closed = True

    def deleteLater(self) -> None:
        return None


def test_network_game_blocks_play_again(window) -> None:
    _finish(window)
    window.network = _FakeSocket()
    window.refresh()
    assert not window.can_play_again()
    assert not window.again.isEnabled()
    before = window.game
    _press_enter(window)
    drain(QApplication.instance())
    assert window.game is before
