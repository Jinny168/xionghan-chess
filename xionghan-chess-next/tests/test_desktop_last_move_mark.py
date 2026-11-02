"""D1「上一步起讫格」高亮的绘制契约（离屏渲染实测）。

## 为什么用像素而不用"看代码"

这层标记的全部要求都是**观感约束**，读代码看不出来：
- 它必须**弱于**将军标注、且不与选择态抢；
- 它必须跟着棋盘线色走（浅色盘变深、深色盘变浅），否则深色主题直接消失；
- **终点格（有子）上仍然要读得出来** —— 这一条推翻了第一版的设计：
  第一版用实心圆盘（半径 .46 格），和圆棋子同心得只剩一圈约 2.5px 的环，
  25% 透明度下不可读，实测只看得见"没子的起点格"。
  改成「格内圆角方框」（内缩 5%、圆角 16% 格）后棋子只遮中间、**四个角照样可见**。

## 关于面积验收线的算术天花板（重要）

标记只有两个方框，合计 `2 × 0.9² = 1.62 格²`；13×13 棋盘共 169 格 →
**上限就是 0.96%**（对 700×700 全图是 0.84%）。所以任何 `≥1.0% 棋盘面积` 的验收线
在算术上都不可达，与实现无关。因此这里改成两条能真正判定的断言：
1. **终点格四角必须可感知**（Δ≥6）—— 这是"读得出来"的直接判据；
2. 可感知面积落在 `[0.5%, 0.96%]` 区间 —— 下界保证不是白画，上界防止有人把
   标记扩到两格以外（那就不再是"淡色标注"了）。

## 采样点为什么偏移 .25 格

棋盘是交叉点布局，格心正好压着两根网格线的交点，而标记色**取的就是网格线色**
（`theme["line"]`）——在交点上取样会把"标记"和"网格线"混成一个数，测了个寂寞。
偏移 .25 格后距交点 `√2 × .25 ≈ .35` 格，仍在标记方框内，且躲开了两条线本身。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="棋盘渲染依赖 PySide6")

from PySide6.QtGui import QColor, QImage, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import (  # noqa: E402
    Color, Move, MoveRecord, PieceType, Position,
)
from xionghan_chess.desktop.ui import board_widget, theme  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "web" / "js" / "app.js"

SIZE = 700
BOARD = SIZE * SIZE
SOURCE = Position(3, 4)      # 空位（完整布局里这格没有棋子）
TARGET = Position(4, 4)      # 兵位 —— 落子后该格必有棋子，用来验"四角仍可见"
OFFSET = 0.25
PERCEPTIBLE_DELTA = 6
THEMES = ("classic", "green", "blue", "purple", "dark")
MIN_COVERAGE = 0.005         # 下界：不能白画
MAX_COVERAGE = 0.0096        # 上界：两个 0.9 格方框的算术天花板（169 格棋盘）


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    theme.load_bundled_fonts()
    return app


def render(*, with_history: bool, theme_name: str = "classic",
           selected: Position | None = None) -> tuple[QImage, board_widget.BoardWidget]:
    game = Game("web")
    if with_history:
        game.state.history.append(MoveRecord(
            Move(SOURCE, TARGET), Color.RED, PieceType.PAWN, (), "兵四进一"))
    board = board_widget.BoardWidget()
    board.resize(SIZE, SIZE)
    board.set_game(game, Color.RED, True)
    board.set_appearance(theme_name, "none", "traditional", "glyph")
    board.interactive = False
    board.selected = selected
    canvas = QPixmap(SIZE, SIZE)
    canvas.fill(QColor("white"))
    board.render(canvas)
    return canvas.toImage(), board


def _raw(image: QImage) -> bytes:
    return bytes(image.constBits())


def _delta(a: QImage, x: int, y: int, other: QImage) -> int:
    ca, cb = a.pixelColor(x, y), other.pixelColor(x, y)
    return max(abs(ca.red() - cb.red()), abs(ca.green() - cb.green()),
               abs(ca.blue() - cb.blue()))


def perceptible_delta(a: QImage, b: QImage) -> int:
    pa, pb = _raw(a), _raw(b)
    count = 0
    for i in range(0, len(pa), 4):
        if (abs(pa[i] - pb[i]) >= PERCEPTIBLE_DELTA
                or abs(pa[i + 1] - pb[i + 1]) >= PERCEPTIBLE_DELTA
                or abs(pa[i + 2] - pb[i + 2]) >= PERCEPTIBLE_DELTA):
            count += 1
    return count


def sample(image: QImage, board: board_widget.BoardWidget,
           pos: Position) -> tuple[int, int, int]:
    _, left, top, cw, ch = board._geometry()
    x = int(left + (pos.col + OFFSET) * cw)
    y = int(top + (pos.row + OFFSET) * ch)
    color = image.pixelColor(x, y)
    return color.red(), color.green(), color.blue()


def brightness(rgb: tuple[int, int, int]) -> int:
    return sum(rgb)


def test_no_history_draws_nothing(qt_app: QApplication) -> None:
    """开局（`history` 为空）时不得有任何标记 —— 复盘到第 0 手也走这条路径。"""
    plain, board = render(with_history=False)
    assert sample(plain, board, SOURCE) == sample(plain, board, Position(2, 3)), \
        "没有 history 却画出了标记"


def test_last_move_marks_the_source_square(qt_app: QApplication) -> None:
    """有 history 时起点格出现淡色标注（浅色盘上表现为变深）。"""
    plain, board = render(with_history=False)
    marked, _ = render(with_history=True)
    before = sample(plain, board, SOURCE)
    after = sample(marked, board, SOURCE)
    assert after != before, "history 有末手，起点格却没有标注"
    assert brightness(after) < brightness(before), (
        f"浅色盘上标注应比底色**更暗**（取棋盘线色混出来）：{before} → {after}")


@pytest.mark.parametrize("theme_name", THEMES)
def test_target_square_corners_stay_visible_under_a_piece(
        qt_app: QApplication, theme_name: str) -> None:
    """**D1 的核心验收**：终点格有棋子时，方框的四个角仍必须可感知（五套主题全测）。

    第一版圆盘在这里得 0（环太细），这条会直接拦下它。
    同时锁定"标记画在棋子之前"这个层级不变：棋子中心仍被盖住，只有四角露出来。

    为什么要五套全测：标记色取的是**棋盘线色**，五套盘线色差很多
    （classic #684726 / dark #c9b58e），只测两套等于赌另外三套碰巧也够。
    """
    marked, board = render(with_history=True, theme_name=theme_name)
    plain, _ = render(with_history=False, theme_name=theme_name)
    _, left, top, cw, ch = board._geometry()

    misses = []
    for tag, (dx, dy) in {"左上": (-.40, -.40), "右上": (.40, -.40),
                          "左下": (-.40, .40), "右下": (.40, .40)}.items():
        x = int(left + TARGET.col * cw + dx * cw)
        y = int(top + TARGET.row * ch + dy * ch)
        delta = _delta(marked, x, y, plain)
        if delta < PERCEPTIBLE_DELTA:
            misses.append(f"{tag}(Δ={delta})")
    assert not misses, f"终点格这些角读不出来：{misses}"

    # 层级契约：棋子正中心（棋子盖住的地方）像素不变
    centre_x = int(left + TARGET.col * cw)
    centre_y = int(top + TARGET.row * ch)
    assert _delta(marked, centre_x, centre_y, plain) == 0, \
        "棋子中心像素变了 —— 标记被画到棋子之后了（应保持在 _draw_marks 内）"


def test_mark_coverage_is_within_the_arithmetic_ceiling(qt_app: QApplication) -> None:
    """可感知面积必须落在 [0.5%, 0.96%]：下界防空画，上界防有人把标记扩到两格以外。"""
    marked, _ = render(with_history=True)
    plain, _ = render(with_history=False)
    ratio = perceptible_delta(marked, plain) / BOARD
    assert MIN_COVERAGE <= ratio <= MAX_COVERAGE, (
        f"可感知面积 {ratio:.2%} 不在 [{MIN_COVERAGE:.1%}, {MAX_COVERAGE:.2%}] 内"
        "（上限是两个 0.9 格方框在 169 格棋盘上的算术天花板，超过说明标记不止两格）")


def test_selection_wins_over_last_move(qt_app: QApplication) -> None:
    """同一格既被选中又是上一步起点时，选择态（金色）必须显示在上。

    顺序判据：选择态 `(221,166,40)` 的 r−b 远大于棋盘线色 `#684726`
    （r−b ≈ 66），所以"金色压上去"这件事在 r−b 上一定是**单调变大**。
    """
    marked, board = render(with_history=True)
    both, _ = render(with_history=True, selected=SOURCE)
    plain_last = sample(marked, board, SOURCE)
    plain_both = sample(both, board, SOURCE)
    spread = lambda rgb: rgb[0] - rgb[2]
    assert spread(plain_both) > spread(plain_last), (
        f"选择态没有盖在上一步标记之上：{plain_last} → {plain_both}")


def test_mark_follows_board_line_colour_across_themes(qt_app: QApplication) -> None:
    """深色盘上标注应**变浅**而不是变深 —— 证明颜色来自 `theme["line"]` 而非写死。

    写死一个深色的话，深色主题里这个方框直接看不见（这正是本项目其它标记踩过的坑）。
    """
    plain_dark, board_dark = render(with_history=False, theme_name="dark")
    marked_dark, _ = render(with_history=True, theme_name="dark")
    before = sample(plain_dark, board_dark, SOURCE)
    after = sample(marked_dark, board_dark, SOURCE)
    assert after != before, "深色主题下没有标注"
    assert brightness(after) > brightness(before), (
        f"深色盘上标注应比底色**更亮**（棋盘线色 #c9b58e 混出来）：{before} → {after}")


def test_mark_alpha_ladder_is_locked() -> None:
    """三档标注的强弱顺序必须被锁死：上一步(64) < 吃子提示(90) < 选择态(145)。

    判据不是"数值好看"，而是**出现频率**：
    选中 / 可吃 / 被将都是**事件性**提示，出现即"此刻有事"；
    而上一步是**全场唯一恒常存在**的标注 —— 每走一手它就在，而且永远在。
    一个"永远在"的元素必须是最弱的一档，否则会把注意力从棋盘本身拉走
    （违背计划开头那条对标结论"棋盘即主角"）。
    谁想"调明显一点"，会先撞到这条。
    """
    assert board_widget.LAST_MOVE_ALPHA < board_widget.CAPTURE_MARK_ALPHA \
        < board_widget.SELECTION_MARK_ALPHA, (
            "标注强弱顺序被打乱：上一步 {} / 吃子提示 {} / 选择态 {}".format(
                board_widget.LAST_MOVE_ALPHA, board_widget.CAPTURE_MARK_ALPHA,
                board_widget.SELECTION_MARK_ALPHA))
    assert (board_widget.LAST_MOVE_ALPHA, board_widget.CAPTURE_MARK_ALPHA,
            board_widget.SELECTION_MARK_ALPHA) == (64, 90, 145), (
            "三档 alpha 的定稿值是 64 / 90 / 145；改动请同时更新本条与 UI 审计文档")


# --- 网页端同步 -----------------------------------------------------------

def test_web_highlight_shares_desktop_geometry_and_skips_replay() -> None:
    """网页那份必须与桌面同几何（方框 + 内缩 5% + 圆角 16% + alpha .25），且回放跳过。"""
    source = APP_JS.read_text(encoding="utf-8")

    assert "function lastMoveInk(" in source, "网页端缺少上一步高亮的取色助手"
    assert "lastMoveInk(.25)" in source, "网页端上一步高亮的不透明度应与桌面 .25 一致"

    # 几何必须用方框（cellFrame），不是圆盘（ring）
    assert "function cellFrame(" in source, "网页端上一步高亮应使用格内方框"
    assert re.search(r"cellFrame\(g,last\.move\.(from|to),ink\)", source), \
        "网页端上一步高亮没有对起讫两格都画方框"
    assert "g.cw*.05" in source and "g.ch*.05" in source, "网页端方框内缩应为 5% 格"
    assert "Math.min(g.cw,g.ch)*.16" in source, "网页端方框圆角应为 16% 格"

    # 回放必须跳过：网页的 history 是实时对局的，不随回放索引切换
    assert "app.replayIndex===null?app.state.history?.at(-1):null" in source, \
        "网页端在上一步高亮里没有排除回放态（会与所显示的局面错位）"


def test_web_cell_frame_falls_back_when_round_rect_is_missing() -> None:
    """老浏览器没有 `ctx.roundRect` 时要退化成直角矩形，而不是整块不画。"""
    source = APP_JS.read_text(encoding="utf-8")
    assert "ctx.roundRect?ctx.roundRect(x,y,w,h,r):ctx.rect(x,y,w,h)" in source, \
        "cellFrame 缺少 roundRect 的降级分支"
