"""P1-10 桌面四级反馈条的行为契约。

## 挡的是什么

反馈条最容易出的两种"看起来对、实际错"：
1. **颜色不跟主题走** —— 构造时缓存一次 QSS，切到暗色主题后浅色底/浅色字；
2. **拼错等级就崩** —— `show_message(text, "erorr")` 抛 KeyError，UI 层因为一个
   字符串拼写错误把整局游戏干掉。

所以这里断言的都不是"控件存在"，而是"颜色等于当前主题对应的键"与"非法输入不炸"。

## 口径

- 四个 level 的背景色**两两不同**（error 复用横幅那套红，不许与 success 撞）；
- 取色时**现取** `THEMES[主题][键]`，把期望值也从同一个字典算出来，而不是写死色值；
- 自动隐藏用真 QTimer 等：`QTest.qWait` 走事件循环，不用 `time.sleep`（那不会派发超时）。
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6", reason="反馈条是 Qt 控件")

from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.desktop.ui import theme  # noqa: E402
from xionghan_chess.desktop.ui.feedback import (  # noqa: E402
    DEFAULT_LEVEL,
    DEFAULT_TIMEOUT_MS,
    LEVELS,
    FeedbackBar,
)

HERE = Path(__file__).resolve().parents[1]
SOURCE = HERE / "src" / "xionghan_chess" / "desktop" / "ui" / "feedback.py"

#: level → 主题调色键；`error` 指向横幅那一套（与 feedback.py 的实现约定一致）。
EXPECTED_KEYS = {
    "success": ("success_bg", "success_fg"),
    "warn": ("warn_bg", "warn_fg"),
    "error": ("banner_bg", "banner_fg"),
    "info": ("info_bg", "info_fg"),
}


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def bar(qt_app: QApplication) -> FeedbackBar:
    widget = FeedbackBar("classic")
    yield widget
    widget.deleteLater()


def _style(bar: FeedbackBar) -> str:
    return bar.label.styleSheet()


def test_initial_state_is_hidden_and_empty(bar: FeedbackBar) -> None:
    """新建时整体隐藏 —— 隐藏控件在 QVBoxLayout 里不占高度（棋盘不被挤压）。"""
    assert not bar.isVisible()
    assert bar.current_text == ""
    assert bar.current_level == DEFAULT_LEVEL


@pytest.mark.parametrize("level", LEVELS)
def test_background_comes_from_the_theme(bar: FeedbackBar, level: str) -> None:
    """每个等级的背景色/前景色等于 `THEMES[当前主题]` 里对应的键值。"""
    palette = theme.THEMES["classic"]
    bg_key, fg_key = EXPECTED_KEYS[level]
    bar.show_message("x", level)
    css = _style(bar)
    assert palette[bg_key] in css, f"{level} 背景不是主题里的 {bg_key}：{css}"
    assert palette[fg_key] in css, f"{level} 前景不是主题里的 {fg_key}：{css}"
    assert bar.current_level == level


def test_four_levels_are_visually_distinct(bar: FeedbackBar) -> None:
    """四级背景色两两不同：撞色等于分级失效（玩家读不出严重程度）。"""
    palette = theme.THEMES["classic"]
    backgrounds = {}
    for level in LEVELS:
        bar.show_message("x", level)
        backgrounds[level] = palette[EXPECTED_KEYS[level][0]]
    assert len(set(backgrounds.values())) == len(LEVELS), f"存在撞色：{backgrounds}"


def test_illegal_level_falls_back_to_info_without_raising(bar: FeedbackBar) -> None:
    """拼错等级不抛异常、不丢文案，只退化成 info。"""
    bar.show_message("保存失败", "erorr")
    assert bar.current_level == DEFAULT_LEVEL
    assert bar.current_text == "保存失败"
    palette = theme.THEMES["classic"]
    assert palette["info_bg"] in _style(bar)


def test_set_theme_repaints_a_visible_message(qt_app: QApplication) -> None:
    """切主题后已显示的那条要换色（暗色主题取的是暗色那一套）。"""
    widget = FeedbackBar("classic")
    widget.show_message("网络已断开", "error")
    light_bg = theme.THEMES["classic"]["banner_bg"]
    dark_bg = theme.THEMES["dark"]["banner_bg"]
    assert light_bg in _style(widget)
    widget.set_theme("dark")
    assert dark_bg in _style(widget)
    assert light_bg not in _style(widget)
    widget.deleteLater()


def test_message_hides_itself_after_the_timeout(bar: FeedbackBar, qt_app: QApplication) -> None:
    """超时自动隐藏：反馈条**不常驻**（P1-10 的"不加常驻信息"）。"""
    bar.show_message("已保存", "success", 60)
    assert bar.isVisible()
    QTest.qWait(240)
    qt_app.processEvents()
    assert not bar.isVisible(), "超时后仍然可见 —— 定时器没接上或时长没生效"


def test_zero_timeout_stays_until_replaced(bar: FeedbackBar, qt_app: QApplication) -> None:
    """`timeout_ms <= 0` 表示不自动隐藏（调用方显式要求常驻到下一句）。"""
    bar.show_message("请等待对手", "info", 0)
    QTest.qWait(120)
    qt_app.processEvents()
    assert bar.isVisible()
    bar.clear()
    assert not bar.isVisible()


def test_new_message_restarts_the_timer(bar: FeedbackBar, qt_app: QApplication) -> None:
    """连发两条时，第二条的停留时间从头算（不能被第一条的旧定时器提前收掉）。"""
    bar.show_message("第一条", "info", 60)
    QTest.qWait(40)
    bar.show_message("第二条", "info", 240)
    QTest.qWait(120)
    qt_app.processEvents()
    assert bar.isVisible(), "旧定时器把新消息收掉了"
    assert bar.current_text == "第二条"


def test_module_contains_no_literal_colors() -> None:
    """裸色禁令：本模块内不得出现任何 hex 字面量（颜色只许来自 THEMES）。"""
    hits = re.findall(r"#[0-9a-fA-F]{3,8}", SOURCE.read_text(encoding="utf-8"))
    assert hits == [], f"feedback.py 出现字面量颜色：{hits}"


def test_default_timeout_matches_the_documented_contract() -> None:
    """默认停留 4000ms（P1-10 规格）。"""
    assert DEFAULT_TIMEOUT_MS == 4000
