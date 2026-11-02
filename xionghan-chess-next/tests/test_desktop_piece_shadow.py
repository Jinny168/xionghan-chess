"""P1-1 桌面棋子投影：必须在 `_draw_piece` 这个**分发入口**上一视同仁。

## 这一层的两个硬约束，都是"看不见的代码"型契约

1. **不许三个渲染分支各画一遍。** 字形 / 位图 / 回退（`draw_piece_glyph`、
   `_draw_piece_image`、`draw_fallback_piece`）的坐标系与半径算法各不相同，
   各画一遍早晚漏一条 —— 回退分支在本项目历史上就被漏过一次。
   所以投影只写在 `_draw_piece` 里，让任何棋子都必然有。
   本条用"三种模式都有像素变化"来证伪：
   若哪天有人把投影搬进某一个分支，另外两个模式立刻少掉这些像素。

2. **不许用 `QGraphicsDropShadowEffect`。** 棋盘是自带 QPainter 的手绘控件，
   图形特效会接管 paint 流程并二次离屏合成，与 `paintEvent` 的绘制顺序和坐标系冲突，
   也会拖慢 60fps 的走子动画。本条用源码断言把它钉死。

## 测量口径

不看具体色值（投影强度属于设计参数，会调），只比"开投影 / 关投影"两张图的
**差异像素数**。关投影用 `monkeypatch` 把 `PIECE_SHADOW_ALPHA` 置 0 实现，
不依赖被测代码里有没有开关。
"""

from __future__ import annotations

import io
import tokenize
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="棋盘渲染依赖 PySide6")

from PySide6.QtGui import QColor, QImage, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import Color, Piece, PieceType  # noqa: E402
from xionghan_chess.desktop.ui import board_widget, piece_assets, theme  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WIDGET_PY = ROOT / "src" / "xionghan_chess" / "desktop" / "ui" / "board_widget.py"

SIZE = 480
GLYPH_MODE = board_widget.GLYPH_MODE
IMAGE_MODE = board_widget.IMAGE_MODE


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    theme.load_bundled_fonts()
    return app


def render(*, mode: str) -> QImage:
    """只放一枚棋子：投影改动有多少个像素，一眼可比。"""
    game = Game("web")
    game.state.pieces = [Piece.create(PieceType.ROOK, Color.RED, 5, 5)]
    board = board_widget.BoardWidget()
    board.resize(SIZE, SIZE)
    board.set_game(game, Color.RED, True)
    board.set_appearance("classic", "none", "traditional", mode)
    board.interactive = False
    canvas = QPixmap(SIZE, SIZE)
    canvas.fill(QColor("white"))
    board.render(canvas)
    return canvas.toImage()


def differing_pixels(a: QImage, b: QImage) -> int:
    assert (a.width(), a.height()) == (b.width(), b.height())
    return sum(1 for y in range(a.height()) for x in range(a.width())
               if a.pixel(x, y) != b.pixel(x, y))


@pytest.mark.parametrize("mode", [GLYPH_MODE, IMAGE_MODE])
def test_shadow_is_drawn_in_every_render_branch(qt_app: QApplication,
                                                monkeypatch: pytest.MonkeyPatch,
                                                mode: str) -> None:
    """字形与位图两条分支都必须有投影像素。"""
    on = render(mode=mode)
    monkeypatch.setattr(board_widget, "PIECE_SHADOW_ALPHA", 0)
    off = render(mode=mode)
    changed = differing_pixels(on, off)
    assert changed > 0, f"{mode} 模式下没有画投影（开/关投影渲染结果完全相同）"


def test_shadow_is_drawn_in_the_fallback_branch(qt_app: QApplication,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    """回退分支（无美术棋子）同样有投影 —— 因为它画在分发入口，不在分支里。"""
    monkeypatch.setattr(piece_assets, "pixmap", lambda *args, **kwargs: None)
    on = render(mode=IMAGE_MODE)
    monkeypatch.setattr(board_widget, "PIECE_SHADOW_ALPHA", 0)
    off = render(mode=IMAGE_MODE)
    assert differing_pixels(on, off) > 0, "回退分支没有投影 —— 投影被搬进分支了"


def test_no_graphics_effect_is_used_for_the_shadow() -> None:
    """禁止 `QGraphicsDropShadowEffect`：与自带 QPainter 的绘制流程冲突。

    判据是"**代码里真的用了**"，不是"文件里出现过这个词" —— `_draw_piece` 的注释
    正是在解释为什么不用它，所以先剥掉注释再查（否则注释会把这条断言说成假话）。
    """
    offenders: list[str] = []
    for path in sorted(WIDGET_PY.parent.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        kept: list[str] = []
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type in (tokenize.COMMENT, tokenize.STRING):
                continue            # 文档字符串里提到它不算使用
            kept.append(token.string)
        if "QGraphicsDropShadowEffect" in " ".join(kept):
            offenders.append(path.name)
    assert not offenders, (
        "棋盘棋子投影不得用 QGraphicsDropShadowEffect（会接管 paint 流程、"
        f"与 paintEvent 的坐标系和绘制顺序冲突，并拖慢走子动画）：{offenders}")


def test_shadow_geometry_comes_from_named_constants() -> None:
    """几何参数必须走具名常量（便于设计调参、也便于本条指出该调哪个）。"""
    for name in ("PIECE_SHADOW_ALPHA", "PIECE_SHADOW_OFFSET", "PIECE_SHADOW_RATIO"):
        assert hasattr(board_widget, name), f"缺少投影参数常量 {name}"
