"""D1「上一步起讫格」高亮的绘制契约（离屏渲染实测）。

## 为什么用像素而不用"看代码"

这层标记的全部要求都是**观感约束**，读代码看不出来：
- 它必须**弱于**将军标注、且不与选择态抢；
- 它必须跟着棋盘线色走（浅色盘上是变深、深色盘上是变浅），否则深色主题直接消失；
- 它必须画在棋子**之前**（所以被棋子盖住是**预期**，不是 bug——这一条要写进断言，
  免得后人来"修"成画在棋子之后）。

所以四条断言全部落在真实渲染出的像素上，且**只做相对比较**（不写死色值）：
色值调整不会假红，但"顺序变了/颜色写死了/画都没画"一定红。

## 采样点为什么偏移 .25 格

棋盘是交叉点布局，格心正好压着两根网格线的交点，而标记色**取的就是网格线色**
（`theme["line"]`）——在交点上取样会把"标记"和"网格线"混成一个数，测了个寂寞。
偏移 .25 格后距交点 `√2 × .25 ≈ .35` 格，仍在标记圆（半径 .46 格）内，
且躲开了两条线本身。
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
from xionghan_chess.desktop.ui import theme  # noqa: E402
from xionghan_chess.desktop.ui.board_widget import BoardWidget  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "web" / "js" / "app.js"

SIZE = 700
SOURCE = Position(3, 4)      # 空位（13×13 的完整布局里这格没有棋子）
TARGET = Position(4, 4)      # 兵位 —— 落子后该格必有棋子，用来验"标记被棋子盖住"
OFFSET = 0.25


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    theme.load_bundled_fonts()
    return app


def render(*, with_history: bool, theme_name: str = "classic",
           selected: Position | None = None) -> tuple[QImage, BoardWidget]:
    game = Game("web")
    if with_history:
        game.state.history.append(MoveRecord(
            Move(SOURCE, TARGET), Color.RED, PieceType.PAWN, (), "兵四进一"))
    board = BoardWidget()
    board.resize(SIZE, SIZE)
    board.set_game(game, Color.RED, True)
    board.set_appearance(theme_name, "none", "traditional", "glyph")
    board.interactive = False
    board.selected = selected
    canvas = QPixmap(SIZE, SIZE)
    canvas.fill(QColor("white"))
    board.render(canvas)
    return canvas.toImage(), board


def sample(image: QImage, board: BoardWidget, pos: Position) -> tuple[int, int, int]:
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


def test_marks_are_drawn_before_pieces(qt_app: QApplication) -> None:
    """终点格被棋子完全盖住 —— 这是**预期契约**，不是缺陷。

    `_draw_marks` 里的一切标记都在 `_draw_piece` 之前画（将军/选择/可走点同理）。
    若有人把本标记挪到棋子之后，这条会红：那时终点格像素会变。
    """
    plain, board = render(with_history=False)
    marked, _ = render(with_history=True)
    assert sample(marked, board, TARGET) == sample(plain, board, TARGET), \
        "终点格像素变了 —— 标记被画到棋子之后了（应保持在 _draw_marks 内）"


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

    写死一个深色的话，深色主题里这个圆直接看不见（这正是本项目其它标记踩过的坑）。
    """
    plain_dark, board_dark = render(with_history=False, theme_name="dark")
    marked_dark, _ = render(with_history=True, theme_name="dark")
    before = sample(plain_dark, board_dark, SOURCE)
    after = sample(marked_dark, board_dark, SOURCE)
    assert after != before, "深色主题下没有标注"
    assert brightness(after) > brightness(before), (
        f"深色盘上标注应比底色**更亮**（棋盘线色 #c9b58e 混出来）：{before} → {after}")


# --- 网页端同步 -----------------------------------------------------------

def test_web_highlight_shares_desktop_parameters_and_skips_replay() -> None:
    """网页那份必须与桌面同参数（半径 .46 / 不透明度 .25），且回放时跳过。"""
    source = APP_JS.read_text(encoding="utf-8")

    assert "function lastMoveInk(" in source, "网页端缺少上一步高亮的取色助手"
    assert "lastMoveInk(.25)" in source, "网页端上一步高亮的不透明度应与桌面 .25 一致"
    assert re.search(r"ring\(g,last\.move\.(from|to),ink,\.46\)", source), \
        "网页端上一步高亮的半径应与桌面 .46 一致"

    # 回放必须跳过：网页的 history 是实时对局的，不随回放索引切换
    assert "app.replayIndex===null?app.state.history?.at(-1):null" in source, \
        "网页端在上一步高亮里没有排除回放态（会与所显示的局面错位）"
