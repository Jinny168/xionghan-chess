"""设置窗口拆分：菜单四个入口 + 单页独立打开。

原来是一个窗口三个标签，改声音要"先开设置、再找标签"。现在拆成四个独立窗口，
菜单里各给一个入口。这里守两件事：菜单条目在，且独立打开时确实只剩一页。

tab / 菜单顺序是产品口径：对局设置 → 棋子规则 → 界面 → 声音。
「界面」与「声音」原本挤在同一页（界面与声音），关个 BGM 得翻过字体/主题/棋子风格；
「通用裁定」（自我将军、三次重复）原本在对局设置里，属于规则，已挪进棋子规则页。
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.desktop.config import DEFAULTS  # noqa: E402
from xionghan_chess.desktop.ui.dialogs import SettingsDialog  # noqa: E402

SECTIONS = [(0, "对局设置"), (1, "棋子规则"), (2, "界面"), (3, "声音")]


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_each_section_opens_as_its_own_window(qt_app) -> None:
    for index, title in SECTIONS:
        dialog = SettingsDialog(dict(DEFAULTS), None, initial_tab=index, standalone=True)
        dialog.show()
        qt_app.processEvents()
        try:
            assert dialog.tabs.currentIndex() == index
            assert dialog.windowTitle() == title, f"标题应是 {title}，实际 {dialog.windowTitle()!r}"
            assert not dialog.tabs.tabBar().isVisible(), "独立窗口不该还带标签栏"
        finally:
            dialog.close()


def test_default_construction_keeps_the_tabbed_window(qt_app) -> None:
    """不传 `standalone` 时保持原样（老调用点与测试还在用多标签形态）。"""
    dialog = SettingsDialog(dict(DEFAULTS), None)
    assert dialog.tabs.count() == 4
    # 对话框没 show 时 isVisible() 恒为 False；要用 isVisibleTo(父窗口) 判断"相对可见"
    assert dialog.tabs.tabBar().isVisibleTo(dialog)


def test_menu_lists_the_four_sections(qt_app) -> None:
    # 写盘隔离已由 `tests/conftest.py` 的 autouse fixture（`isolated_user_data`）
    # 统一兜住：这里原先只 patch `config.save_config`，而 app.py 持有的是
    # `from .config import save_config` 的副本 —— 拦不住，跑完会写真实配置。
    from xionghan_chess.desktop.app import MainWindow

    window = MainWindow()
    try:
        labels = []
        for menu_action in window.menuBar().actions():
            menu = menu_action.menu()
            if menu and menu.title() in ("设置", "Settings"):
                labels = [action.text() for action in menu.actions() if not action.isSeparator()]
                break
        for _index, title in SECTIONS:
            assert title in labels, f"设置菜单缺少入口：{title}（当前 {labels}）"
    finally:
        window.close()
