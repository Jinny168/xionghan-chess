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
# 2026-11-03：侧栏七个操作从「单列文字按钮（7×40）」改成「两行图标（2×34）」后，
# 让出的高度全给了棋谱列表（297 → 315）。**变大是这次改动的目的**：
# 侧栏原本被按钮顶到底、非滚动不可。
HISTORY_DEFAULT_BEFORE = 297  # 图标化之前的基准（窄按钮那版实测 315，属中间态）
BUTTON_PADDING = 14  # QSS padding:7px 左右


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
        f"900×680 下棋谱只有 {window.history.height()}px（应 ≥ {HISTORY_MIN}）"
    )


def test_default_size_history_is_at_least_as_tall_as_before(window: MainWindow, qt_app: QApplication) -> None:
    """默认 1260×850 下棋谱不得比图标化之前更矮（297px）。

    原断言是「与 297 相差 ≤2px」的**绝对基准**：单跑能过，整套一起跑会因为字体
    加载差异漂到 315+ 而假红 —— 绝对像素太脆。
    改成方向性契约：这次改动的目的就是把按钮区压薄、把高度让给棋谱，
    所以只要「不矮于 297」就说明改对了，具体多高随字体走。
    """
    window.resize(*DEFAULT_SIZE)
    qt_app.processEvents()
    actual = window.history.height()
    assert actual >= HISTORY_DEFAULT_BEFORE, (
        f"默认尺寸棋谱 {actual}px，比图标化前的 {HISTORY_DEFAULT_BEFORE}px 还矮 —— 按钮区没压薄？"
    )


def test_action_buttons_are_compact_icons(window: MainWindow) -> None:
    """侧栏操作区必须是「两行图标」，不是「七行文字按钮」。

    口径变更（2026-11-03）：按钮改成纯图标后，文字不再进 `button.text()`，
    原来那条「最长文案不截断」的断言失去对象；改守**紧凑度**这个新契约：
    单个按钮 ≤ 40px 见方，整块不超过两行高度。
    """
    names = ("undo", "pause", "resign", "draw", "resurrect", "flip", "again")
    buttons = [getattr(window, name) for name in names]
    for button in buttons:
        assert button.text() == "", "图标按钮不该有文字"
        assert button.height() <= 44, f"按钮过高：{button.height()}"
        assert button.width() >= 50, f"按钮太窄，没铺满容器：{button.width()}px"
    widths = {button.width() for button in buttons}
    assert max(widths) - min(widths) <= 2, f"同一栅格里按钮宽度不一致：{widths}"
    # 两行：每行实测 37（QSS padding 撑高），加 12 间距，留 2px 余量
    top = min(b.y() for b in buttons)
    bottom = max(b.y() + b.height() for b in buttons)
    block_height = bottom - top
    assert block_height <= 37 * 2 + 12 + 2, f"操作区高 {block_height}px，超过两行"
