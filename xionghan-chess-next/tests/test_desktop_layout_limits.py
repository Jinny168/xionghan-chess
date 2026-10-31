"""桌面窗口的最小尺寸自洽性与"文字不被截断"的结构性保证。

四条断言对应审计 U-06 / U-25 的复发点：布局一旦回退，这里先红。

口径说明（U-25 的数字必须带测量条件，否则下一轮又按错的数定宽）：
`'Resurrect pawn'` 的宽度在不同字体下差别极大 ——
  · 默认字体（未 `load_bundled_fonts()`）：**168 px**
  · `QFont(theme.UI_FONT, 10)`：**182 px**（该子集字体缺拉丁字形，走回退，量出来偏大）
  · **按钮实际 fontMetrics**（Noto Sans SC Subset 10pt，即 QSS 生效后）：**95 px**
本节断言用**第三个数**，因为那才是用户看到的。

## 182 的定位：**余量，不是补丁**
真实渲染 95px，用 120 也不截断；182 是按"最长英文文案 × 未来语言更长"留的结构性余量
（德语 `Bauern wiederbeleben`、俄语更长）。**不要把这个改动记成"修了一个截断 bug"** ——
此前"168px 需 182"的说法用的是默认字体（未 `load_bundled_fonts()`），是错误测量。
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="布局断言需要 PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.desktop.app import MainWindow  # noqa: E402

MIN_SIZE = (900, 680)
DEFAULT_SIZE = (1260, 850)
HISTORY_MIN = 120
HISTORY_DEFAULT_BEFORE = 297       # 改动前的实测值，容差 ±2
BUTTON_PADDING = 14                # QSS padding:7px 左右


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    from xionghan_chess.desktop.ui import theme
    theme.load_bundled_fonts()
    return app


@pytest.fixture()
def window(qt_app: QApplication) -> MainWindow:
    w = MainWindow()
    w.show()
    qt_app.processEvents()
    yield w
    w.close()


def test_minimum_size_hint_fits_declared_minimum(window: MainWindow) -> None:
    """`minimumSizeHint` 不得大于 `minimumSize`。

    改动前是 666×740 > 760×560（高度超出 180px）——窗口能被拖到内容放不下的尺寸，
    右栏只剩 447 高、棋谱 53px。这条断言就是那个"声明比需求小"的拦截点。
    """
    hint, declared = window.minimumSizeHint(), window.minimumSize()
    assert hint.width() <= declared.width(), f"hint 宽 {hint.width()} > 声明 {declared.width()}"
    assert hint.height() <= declared.height(), f"hint 高 {hint.height()} > 声明 {declared.height()}"


def test_history_stays_visible_at_minimum_size(window: MainWindow, qt_app: QApplication) -> None:
    """最小尺寸（900×680）下棋谱列表仍 ≥ 120px（≈6 行）。"""
    window.resize(*MIN_SIZE)
    qt_app.processEvents()
    assert window.history.height() >= HISTORY_MIN, (
        f"900×680 下棋谱只有 {window.history.height()}px（应 ≥ {HISTORY_MIN}）")


def test_default_size_history_height_is_unchanged(window: MainWindow, qt_app: QApplication) -> None:
    """默认 1260×850 下棋谱高度与改动前（297）差 ≤ 2px —— 布局改动不得影响常态。"""
    window.resize(*DEFAULT_SIZE)
    qt_app.processEvents()
    actual = window.history.height()
    assert abs(actual - HISTORY_DEFAULT_BEFORE) <= 2, (
        f"默认尺寸棋谱 {actual}px，改动前 {HISTORY_DEFAULT_BEFORE}px（容差 ±2）")


def test_longest_button_label_is_not_truncated(window: MainWindow) -> None:
    """最长英文文案放得进按钮可用内宽（结构保证，不针对某一句文案）。

    用按钮**实际 fontMetrics**（QSS 生效后的字体），不是默认字体。
    """
    button = window.resurrect
    for text in ("Resurrect pawn", button.text()):
        need = button.fontMetrics().horizontalAdvance(text)
        available = button.width() - BUTTON_PADDING
        assert need <= available, f"{text!r} 需 {need}px，可用 {available}px（按钮宽 {button.width()}）"
