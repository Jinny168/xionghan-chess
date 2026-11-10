"""桌面端「AI 快捷语」全局开关：关掉后本地 AI 一条都不说。

服务端已在 `tests/test_ai_draw.py::test_declined_taunt_respects_disabled_setting`
与 `tests/test_taunts.py::test_ai_taunt_history_respects_setting_and_deduplicates`
覆盖；桌面这条补的是"本地 AI 对局走同一开关"。
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
    monkeypatch.setattr(w, "start_ai", lambda: None)
    w.new_game()
    qt_app.processEvents()
    yield w
    w.close()


def test_disabled_switch_suppresses_local_ai_taunts(window, qt_app) -> None:
    window.config["taunts"] = False
    window.add_ai_taunt("opening")
    qt_app.processEvents()
    assert window.chat_messages.count() == 0

    window.config["taunts"] = True
    window.add_ai_taunt("opening")
    qt_app.processEvents()
    assert window.chat_messages.count() == 1
    assert window.chat_messages.item(0).text().startswith("匈汉棋灵：")
