"""`refresh()` 的「按需重建」契约（问题 P1-B 的目标）。

上一份 `test_desktop_refresh.py` 钉的是「该显示的显示对了」；这里钉的是
「**没变化就别重建**」——这正是 P1-B 要解决的东西：

- 棋谱列表原来每 250ms 做一次 `clear()+addItems(全部)`，一局 200 手就是每秒
  重建 4 次，还会打断滚动位置；
- 棋盘同理每 tick 全盘重绘；
- `in_check()` 要全盘扫描，原来也每 tick 跑一次。

做法：把 `history` / `captured` / `board` 换成只记调用次数的替身，`refresh()`
仍然走真实代码路径，断言调用次数。这样测的是「有没有跳过」，不是「怎么跳过的」。
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="MainWindow 依赖 PySide6")

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from xionghan_chess.core.model import Color  # noqa: E402
from xionghan_chess.desktop import app as appmod  # noqa: E402
from xionghan_chess.desktop.ui import theme  # noqa: E402


class ListSpy:
    """够用的 QListWidget 替身：只实现 refresh 会调的那几个方法。"""

    def __init__(self) -> None:
        self.items: list[str] = []
        self.clear_calls = 0
        self.add_calls = 0

    def clear(self) -> None:
        self.clear_calls += 1
        self.items = []

    def addItems(self, items: list[str]) -> None:
        self.add_calls += 1
        self.items.extend(items)

    def count(self) -> int:
        return len(self.items)

    def item(self, index: int):
        text = self.items[index]
        return type("Item", (), {"text": staticmethod(lambda: text)})()


class LabelSpy:
    def __init__(self) -> None:
        self.text_value = ""
        self.set_calls = 0

    def setText(self, text: str) -> None:
        self.set_calls += 1
        self.text_value = text

    def text(self) -> str:
        return self.text_value

    def setStyleSheet(self, style: str) -> None:
        pass

    def styleSheet(self) -> str:
        return ""


class BoardSpy:
    def __init__(self) -> None:
        self.locked = False
        self.update_calls = 0

    def update(self) -> None:
        self.update_calls += 1

    def pulse_check(self) -> None:
        pass


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def silent_dialogs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    # 结果弹窗改为自定义按钮框后，静默点转移到 `show_result_dialog`（否则会真模态挂住）
    monkeypatch.setattr(appmod, "show_result_dialog", staticmethod(lambda *a, **k: False))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))


@pytest.fixture()
def window(monkeypatch: pytest.MonkeyPatch, tmp_path, qt_app: QApplication):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    theme.load_bundled_fonts()
    win = appmod.MainWindow()
    win.config["language"] = "zh-CN"
    # 三个替身装好之后再清快照，保证「第一次 refresh」是真正的重建
    win.history = ListSpy()          # type: ignore[assignment]
    win.captured = LabelSpy()        # type: ignore[assignment]
    win.board = BoardSpy()           # type: ignore[assignment]
    win._reset_ui_cache()
    yield win
    win.timer.stop()
    win.close()
    win.deleteLater()


def test_repeated_refresh_does_not_rebuild_anything(window) -> None:
    """同一局面下连刷 5 次：重建各发生一次，其余都是白跑。"""
    for _ in range(5):
        window.refresh()
    assert window.history.clear_calls == 1
    assert window.history.add_calls == 1
    assert window.captured.set_calls == 1
    assert window.board.update_calls == 1


def test_move_rebuilds_history_and_board_but_not_captured(window) -> None:
    window.refresh()
    window.game.move(window.game.rules.legal_moves(window.game.state)[0])
    window.refresh()
    assert window.history.add_calls == 2, "走子后棋谱必须重建"
    assert window.board.update_calls == 2, "走子后棋盘必须重绘"
    assert window.captured.set_calls == 1, "没吃子，阵亡栏不用重拼"


def test_undo_rebuilds_history(window) -> None:
    window.game.move(window.game.rules.legal_moves(window.game.state)[0])
    window.refresh()          # 第 1 次重建：列表里有一手
    window.game.undo(1)
    window.refresh()          # 第 2 次重建：列表回到空
    assert window.history.add_calls == 2, "悔棋后列表要回到上一手的状态"
    assert window.history.items == []


def test_pause_toggles_board_overlay_only(window) -> None:
    """暂停只影响棋盘遮罩与按钮，不该重建棋谱列表。"""
    window.refresh()
    window.game.set_paused(True)
    window.refresh()
    assert window.board.update_calls == 2, "暂停遮罩需要重绘"
    assert window.history.add_calls == 1, "暂停不该动棋谱列表"


def test_language_change_rebuilds_captured_labels(window) -> None:
    window.refresh()
    window.config["language"] = "en"
    window.refresh()
    assert window.captured.set_calls == 2, "语言变了，阵亡栏文案要跟着变"


def test_check_scan_is_not_run_every_tick(window, monkeypatch: pytest.MonkeyPatch) -> None:
    """`in_check()` 要全盘扫描，不能每 250ms 跑一次。"""
    calls = {"n": 0}
    original = window.game.rules.in_check

    def counting(*args, **kwargs):
        calls["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(window.game.rules, "in_check", counting)
    for _ in range(6):
        window.refresh()
    assert calls["n"] <= 1, f"同一局面下跑了 {calls['n']} 次 in_check"

    window.game.move(window.game.rules.legal_moves(window.game.state)[0])
    window.refresh()
    assert calls["n"] >= 2, "走子之后必须重新判断将军"


def test_switching_game_clears_snapshots(window) -> None:
    """换局要清快照，否则「走子数恰好相同」的两局会有一局不重绘。"""
    window.refresh()
    window._reset_ui_cache()
    window.refresh()
    assert window.board.update_calls == 2, "清过快照后必须重新绘制一次"
