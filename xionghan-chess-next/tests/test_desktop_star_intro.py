"""P0-4：首次选中「射」自动开一次星轨提示（一次性引导）。

## 挡的是什么

一次性引导的典型翻车方式不是"不触发"，而是**触发过头**：

1. 用户自己已经在设置里开了星轨，引导还去"教"他，甚至把开关替他关掉 ——
   P1-7 是"不替用户关辅助"，这条属于同一族纪律；
2. 引导只管开不管收：选中一次「射」之后星轨永久压在盘面上，比不做还糟；
3. 观战 / 题目态没拦住 —— 题目态开着星轨等于给计分题开挂（P1-7 已明确屏蔽）。

## 口径

「首次」由 config 键 `archer_star_intro_shown` 表达（本地一次性，不入云同步）。
测试里**真的落盘**（APPDATA 指到 tmp），再用 `load_config()` 读回来核对，
而不是只看内存里的字典 —— 只看内存会漏掉"根本没写文件"这种最常见的错。
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6", reason="一次性引导挂在真实窗口的信号上")

from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.core.model import Color, PieceType, Position  # noqa: E402
from xionghan_chess.desktop import app as appmod  # noqa: E402
from xionghan_chess.desktop.config import load_config  # noqa: E402
from xionghan_chess.desktop.ui import theme  # noqa: E402


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
    # 用例之间互不影响：引导态归零、星轨归零
    win.config["archer_star_intro_shown"] = False
    win.config["archer_star_hints"] = False
    win.configure_board()
    yield win
    win.timer.stop()
    win.close()
    win.deleteLater()


def _position_of(window, color: Color, kind: PieceType) -> Position:
    for piece in window.game.state.pieces:
        if piece.color is color and piece.type is kind:
            return piece.position
    raise AssertionError(f"初始局面里没有 {color} 的 {kind}")


def _select(window, position: Position | None) -> None:
    """模拟一次"选中"：先摆好棋盘状态，再发那个无参信号。"""
    window.board.selected = position
    window.board.piece_selected.emit()


def test_first_archer_selection_turns_star_hints_on_and_persists(window) -> None:
    archer = _position_of(window, Color.RED, PieceType.ARCHER)
    assert not window.board.show_archer_star_hints

    _select(window, archer)

    assert window.board.show_archer_star_hints is True, "首次选中「射」没有打开星轨"
    assert window._star_intro_temp is True, "没有记录这是临时开启（之后收不回去）"
    assert window.config["archer_star_intro_shown"] is True
    assert load_config()["archer_star_intro_shown"] is True, "引导态没落盘，下次启动还会再教一遍"
    assert window.feedback.current_level == "info"
    assert "星位" in window.feedback.current_text


def test_second_archer_selection_does_not_trigger_again(window) -> None:
    archer = _position_of(window, Color.RED, PieceType.ARCHER)
    _select(window, archer)
    # 取消选中 → 临时开关收回
    _select(window, None)
    window.refresh()
    assert window.board.show_archer_star_hints is False, "取消选中后星轨没收回去"

    _select(window, archer)
    assert window.board.show_archer_star_hints is False, "第二次选「射」又触发了引导"
    assert window._star_intro_temp is False


def test_deselect_restores_the_previous_value(window) -> None:
    """取消选中（点空白格）后必须回到引导前的值 —— 引导不许变成常驻辅助。"""
    archer = _position_of(window, Color.RED, PieceType.ARCHER)
    _select(window, archer)
    assert window.board.show_archer_star_hints is True
    _select(window, None)
    window.refresh()
    assert window.board.show_archer_star_hints is False
    assert window._star_intro_temp is False


def test_other_pieces_never_trigger(window) -> None:
    rook = _position_of(window, Color.RED, PieceType.ROOK)
    _select(window, rook)
    assert window.board.show_archer_star_hints is False
    assert window.config["archer_star_intro_shown"] is False, "选了非「射」的棋子却把引导标记掉了"


def test_puzzle_mode_is_excluded(window) -> None:
    """题目态不引导（星轨在计分题里等于开挂）。判据与观战分开，不合并。"""
    archer = _position_of(window, Color.RED, PieceType.ARCHER)
    window.puzzle_session = object()  # 判据只看"是不是 None"
    try:
        _select(window, archer)
    finally:
        window.puzzle_session = None
    assert window.board.show_archer_star_hints is False
    assert window.config["archer_star_intro_shown"] is False


def test_spectate_mode_is_excluded(window) -> None:
    archer = _position_of(window, Color.RED, PieceType.ARCHER)
    window.spectating = True
    try:
        _select(window, archer)
    finally:
        window.spectating = False
    assert window.board.show_archer_star_hints is False
    assert window.config["archer_star_intro_shown"] is False


def test_user_enabled_hints_are_never_turned_off(window) -> None:
    """用户自己开了星轨时：引导既不重复教，也绝不能把开关关掉。"""
    window.config["archer_star_hints"] = True
    window.configure_board()
    assert window.board.show_archer_star_hints is True

    archer = _position_of(window, Color.RED, PieceType.ARCHER)
    _select(window, archer)
    assert window._star_intro_temp is False, "用户已开启时不该走临时开启路径"

    rook = _position_of(window, Color.RED, PieceType.ROOK)
    _select(window, rook)
    _select(window, None)
    window.refresh()
    assert window.board.show_archer_star_hints is True, "引导把用户自己开的星轨关掉了"


def test_flag_defaults_to_false_in_config() -> None:
    """新增键必须有默认值，旧配置文件靠 `{**DEFAULTS, **data}` 补齐。"""
    from xionghan_chess.desktop.config import DEFAULTS

    assert DEFAULTS["archer_star_intro_shown"] is False
