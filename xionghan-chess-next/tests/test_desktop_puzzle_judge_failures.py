"""题解判定的失败路径：提示必须与盘面事实一致，题面不能与解法错位。

两处 `except GameError: pass` 都在说谎：

1. **答错后退棋失败**：界面仍弹「这不是正解，棋已退回」，可盘面上那一手还在；
2. **对手应着落不下去**：`session.advance_auto()` 照走，游标越过这一手，之后
   玩家的每一手都会判错，而题面看起来一切正常。

本文件用一个可控的假会话钉住：失败要有明确反馈，且控制流按各自语义中止。
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="MainWindow 依赖 PySide6")

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from xionghan_chess.core.game import GameError  # noqa: E402
from xionghan_chess.core.model import Move, Position  # noqa: E402
from xionghan_chess.desktop import app as appmod  # noqa: E402
from xionghan_chess.desktop import training as puzzle_judge  # noqa: E402
from xionghan_chess.desktop.ui import theme  # noqa: E402

_PLAYER_MOVE = Move(Position(0, 0), Position(1, 0))


class _Title:
    title = "测试题"


class _WrongSession:
    """提交任意着法都判错，不推进游标。"""

    attempts = 1
    _hints_shown = 0
    cursor = 0
    total = 1
    puzzle = _Title()

    def submit(self, move: Move) -> str:
        return puzzle_judge.VERDICT_WRONG

    def next_hint(self) -> str:
        return ""


class _AutoReplySession:
    """玩家这一手判对，但对手的被迫应着会落子失败。"""

    attempts = 0
    _hints_shown = 0
    player_index = 2
    player_total = 3
    auto_reply = Move(Position(2, 2), Position(3, 2))

    def __init__(self) -> None:
        self.advanced = 0

    def submit(self, move: Move) -> str:
        return puzzle_judge.VERDICT_CORRECT

    def advance_auto(self) -> None:
        self.advanced += 1


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def window(monkeypatch: pytest.MonkeyPatch, tmp_path, qt_app: QApplication):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(appmod, "show_result_dialog", staticmethod(lambda *a, **k: False))
    theme.load_bundled_fonts()
    win = appmod.MainWindow()
    win.config["language"] = "zh-CN"
    win._stats_recorded = True
    win._autosaved = True
    yield win
    win.timer.stop()
    win.close()
    win.deleteLater()


def test_undo_failure_does_not_claim_the_move_was_taken_back(window, monkeypatch: pytest.MonkeyPatch) -> None:
    dialogs: list[str] = []
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: dialogs.append(a[2])))
    notes: list[tuple[str, str]] = []
    monkeypatch.setattr(window, "notify", lambda text, level="info", timeout_ms=0: notes.append((text, level)))

    def fail_undo(count: int = 1) -> None:
        raise GameError("no history to undo")

    monkeypatch.setattr(window.game, "undo", fail_undo)
    window.puzzle_session = _WrongSession()

    assert window._judge_puzzle(_PLAYER_MOVE) is False
    assert any(level == "warn" for _, level in notes), f"退棋失败没有 warn 反馈：{notes}"
    assert dialogs, "答错仍应给玩家一个提示框"
    assert "已退回" not in dialogs[0], "退棋失败却仍说「棋已退回」—— 提示与盘面相反"
    assert "手动悔棋" in dialogs[0], "退棋失败时应告诉玩家手动悔棋"


def test_auto_reply_failure_aborts_puzzle_instead_of_desyncing(window, monkeypatch: pytest.MonkeyPatch) -> None:
    notes: list[tuple[str, str]] = []
    monkeypatch.setattr(window, "notify", lambda text, level="info", timeout_ms=0: notes.append((text, level)))

    def fail_move(move: Move):
        raise GameError("reply not legal in this position")

    monkeypatch.setattr(window.game, "move", fail_move)
    session = _AutoReplySession()
    window.puzzle_session = session
    window.puzzle_is_daily = False
    window.puzzle_scored = False

    assert window._judge_puzzle(_PLAYER_MOVE) is False
    assert session.advanced == 0, "对手应着失败后仍推进了游标 —— 之后每一手都会判错"
    assert window.puzzle_session is None, "题面已与解法错位，应当中止本题"
    assert window.hint_button.isVisible() is False
    assert any(level == "error" for _, level in notes), f"中止本题没有 error 提示：{notes}"
