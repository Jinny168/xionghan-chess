"""`MainWindow.refresh()` 的行为契约（问题 P1-B）。

`refresh()` 是 250ms 定时器的回调，历史上把 12 件事挤在一起：走时钟、拼横幅、
刷玩家标签、重建棋谱列表、重建阵亡文本、全盘重绘、刷按钮可用性，还顺手把
**战绩落盘 / 自动存档 / 终局弹窗**三个副作用藏在里面。

拆之前先用这个文件把「用户能看到的行为」钉住：拆完这些断言必须一字不变地通过。
拆的目标（不在本文件断言实现细节，见 `test_refresh_rebuilds_only_on_change.py`）
是：**没变化时不要重建**。

本文件只管「该显示的显示对了」，不管「调用了几次 addItems」。
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="MainWindow 依赖 PySide6")

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from xionghan_chess.core.model import Color  # noqa: E402
from xionghan_chess.desktop import app as appmod  # noqa: E402
from xionghan_chess.desktop.ui import theme  # noqa: E402
from xionghan_chess.i18n import t  # noqa: E402


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def silent_dialogs(monkeypatch: pytest.MonkeyPatch) -> dict[str, list]:
    """全局静默模态框。

    终局会弹「对局结束」，弃权会弹二次确认 —— 这些模态框在 offscreen 下会把
    测试**永久挂住**。所以本文件所有用例统一拦掉，并记录 information 的调用
    次数供断言使用。
    """
    calls: dict[str, list] = {"information": [], "question": []}
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: calls["information"].append(a[1:3])))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))
    return calls


@pytest.fixture()
def window(monkeypatch: pytest.MonkeyPatch, tmp_path, qt_app: QApplication):
    """每个用例一个干净的用户目录 + 一个真实 MainWindow。"""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    theme.load_bundled_fonts()
    win = appmod.MainWindow()
    win.config["language"] = "zh-CN"
    yield win
    win.timer.stop()
    win.close()
    win.deleteLater()


@pytest.fixture()
def recorded(monkeypatch: pytest.MonkeyPatch, silent_dialogs) -> dict[str, int]:
    """统计三个终局副作用被调用的次数。

    注意 `silent_dialogs` 只是「别把测试挂住」的兜底，这里要**重新**劫持
    `information` 才能计数（后设的 patch 覆盖先设的）。
    """
    counts = {"stats": 0, "autosave": 0, "dialog": 0}

    def fake_record(*args, **kwargs) -> None:
        counts["stats"] += 1

    def fake_autosave(*args, **kwargs):
        counts["autosave"] += 1
        return tmp_path_marker()

    def fake_dialog(*args, **kwargs) -> None:
        counts["dialog"] += 1

    monkeypatch.setattr(appmod, "record_result", fake_record)
    monkeypatch.setattr(appmod, "autosave_game", fake_autosave)
    monkeypatch.setattr(QMessageBox, "information", staticmethod(fake_dialog))
    return counts


def tmp_path_marker():
    from pathlib import Path

    return Path("memory://autosave")


def test_clock_formats_minutes_and_seconds() -> None:
    assert appmod.MainWindow._clock(0) == "00:00"
    assert appmod.MainWindow._clock(65_000) == "01:05"
    assert appmod.MainWindow._clock(3_600_000) == "60:00"
    assert appmod.MainWindow._clock(-5) == "00:00"


def test_banner_shows_whose_turn_it_is(window) -> None:
    window.refresh()
    assert window.banner.text() == t("status.turn", "zh-CN", color=t("common.red", "zh-CN"))


def test_banner_shows_paused_state(window) -> None:
    window.game.set_paused(True)
    window.refresh()
    assert window.banner.text() == t("status.paused", "zh-CN")


def test_banner_shows_game_over_state(window) -> None:
    window.game.resign(Color.RED)
    window.refresh()
    assert window.banner.text() == t("status.game_over", "zh-CN")


def test_puzzle_banner_appends_title_and_step(window) -> None:
    """S2-7 的横幅附加信息不能被这次重构弄丢。"""
    from xionghan_chess.core.puzzles import load_puzzles
    from xionghan_chess.desktop.training import PuzzleSession

    puzzle = load_puzzles()[0]
    window.puzzle_session = PuzzleSession(puzzle)
    window.refresh()
    assert puzzle.title in window.banner.text()
    assert "1/1" in window.banner.text()


def test_history_list_matches_notations(window) -> None:
    legal = window.game.rules.legal_moves(window.game.state)
    window.game.move(legal[0])
    window.refresh()
    assert window.history.count() == 1
    assert window.history.item(0).text() == window.game.state.history[0].notation


def test_captured_panel_lists_both_sides(window) -> None:
    window.refresh()
    text = window.captured.text()
    assert t("common.red", "zh-CN") in text
    assert t("common.black", "zh-CN") in text


def test_buttons_reflect_finished_game(window) -> None:
    window.game.resign(Color.RED)
    window.refresh()
    assert not window.pause.isEnabled()
    assert not window.draw.isEnabled()
    assert not window.resign.isEnabled()
    assert not window.resurrect.isEnabled()


def test_undo_button_follows_history(window) -> None:
    window.refresh()
    assert not window.undo.isEnabled(), "开局没有历史，悔棋应禁用"
    window.game.move(window.game.rules.legal_moves(window.game.state)[0])
    window.refresh()
    assert window.undo.isEnabled()


def test_terminal_side_effects_run_exactly_once(window, recorded) -> None:
    """终局副作用由哨兵保证只跑一次 —— 这是拆分的红线，不能改成每 tick 都跑。"""
    window.game.resign(Color.RED)
    for _ in range(5):
        window.refresh()
    assert recorded == {"stats": 1, "autosave": 1, "dialog": 1}


def test_terminal_side_effects_do_not_run_before_finish(window, recorded) -> None:
    for _ in range(3):
        window.refresh()
    assert recorded == {"stats": 0, "autosave": 0, "dialog": 0}


def test_autosave_respects_config(window, recorded, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(window.config, "autosave", False)
    window.game.resign(Color.RED)
    window.refresh()
    assert recorded["autosave"] == 0
    assert recorded["stats"] == 1, "关掉自动存档不影响战绩落盘"


def test_banner_prefixes_check_state(window, monkeypatch: pytest.MonkeyPatch) -> None:
    """被将时横幅要写「将军 · 红方行棋」——盘内那两个字常被棋子盖住。"""
    monkeypatch.setattr(window, "_check_state", lambda state: True)
    window.refresh()
    assert window.banner.text().startswith("将军 · "), window.banner.text()

    monkeypatch.setattr(window, "_check_state", lambda state: False)
    window.refresh()
    assert "将军" not in window.banner.text()


def test_banner_prefixes_check_state(window, monkeypatch: pytest.MonkeyPatch) -> None:
    """被将时横幅要写「将军 · 红方行棋」——盘内那两个字常被棋子盖住。"""
    monkeypatch.setattr(window, "_check_state", lambda state: True)
    window.refresh()
    assert window.banner.text().startswith("将军 · "), window.banner.text()

    monkeypatch.setattr(window, "_check_state", lambda state: False)
    window.refresh()
    assert "将军" not in window.banner.text()
