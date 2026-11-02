"""P1-1 桌面棋子投影：必须在 `_draw_piece` 这个**分发入口**上一视同仁，且必须真的看得见。

## 这一层的三个硬约束，都是"看不见的代码"型契约

1. **不许三个渲染分支各画一遍。** 字形 / 位图 / 回退（`draw_piece_glyph`、
   `_draw_piece_image`、`draw_fallback_piece`）的坐标系与半径算法各不相同，
   各画一遍早晚漏一条 —— 回退分支在本项目历史上就被漏过一次。
   所以投影只写在 `_draw_piece` 里，让任何棋子都必然有。
   本条用"三种模式都有像素变化"来证伪：若哪天有人把投影搬进某一个分支，
   另外两个模式立刻少掉这些像素。

2. **不许用 `QGraphicsDropShadowEffect`。** 棋盘是自带 QPainter 的手绘控件，
   图形特效会接管 paint 流程并二次离屏合成，与 `paintEvent` 的绘制顺序和坐标系冲突，
   也会拖慢 60fps 的走子动画。本条用源码断言把它钉死。

3. **必须真的看得见。** 这条是踩过坑换来的：第一版用纯色椭圆
   （半径 0.98r / 偏移 0.07r），可见面积几何上为 0 —— 字形棋子可见外沿 1.05r，
   而 0.98r + 0.07r 正好也是 1.05r，**两者恰好重合**，
   实测开/关投影只差 0.40% 像素（且全是抗锯齿溢出）。
   "参数写进去了"不等于"用户看得见"，所以这里直接断言可见强度与方向。

## 测量口径

不看具体色值（投影强度属于设计参数，会调），只比"开投影 / 关投影"两张图。
**关投影的方式与参数解耦**：把 `_piece_shadow_brush` 换成一个空刷子，
不依赖任何一个数值常量 —— 否则改参数会把测试连同断言一起改瞎。
"""

from __future__ import annotations

import io
import tokenize
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="棋盘渲染依赖 PySide6")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QBrush, QColor, QImage, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import Color, Piece, PieceType  # noqa: E402
from xionghan_chess.desktop.ui import board_widget, piece_assets, theme  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WIDGET_PY = ROOT / "src" / "xionghan_chess" / "desktop" / "ui" / "board_widget.py"

GLYPH_MODE = board_widget.GLYPH_MODE
IMAGE_MODE = board_widget.IMAGE_MODE

# 可见强度验收线：设计口径「开/关差异像素 ≥ 2.0% 棋盘面积」（light 与 dark 各一次）。
# 判"可见"的像素阈值取 Δ≥6（每通道）—— Δ=1~5 肉眼基本分辨不出，
# 把它们算进去等于用"抗锯齿溢出"冒充影子，正是第一版 0.40% 却"测得出差异"的原因。
PERCEPTIBLE_DELTA = 6
MIN_VISIBLE_RATIO = 0.02
# 影子必须重心向下：底部厚度 ≥ 顶部厚度的 1.5 倍。等宽就是描边，不是影子。
MIN_DOWNWARD_LEAN = 1.5

SMALL = 480          # 三类分支的开关判定用小画布，跑得快
MEASURE = 700        # 强度/方向验收按设计口径的 700×700


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    theme.load_bundled_fonts()
    return app


def render_without_shadow(**kwargs) -> QImage:
    """关投影：把刷子换成 NoBrush，不碰任何数值常量。

    只在**这一次**渲染内生效（`MonkeyPatch.context`），否则连"开投影"那张图
    也会被一起关掉，比出来的差异恒为 0。
    """
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(board_widget, "_piece_shadow_brush",
                      lambda: QBrush(Qt.BrushStyle.NoBrush))
        return render(**kwargs)


def render(*, mode: str, size: int = SMALL, theme_name: str = "classic") -> QImage:
    """只放一枚棋子：投影改动有多少个像素，一眼可比。"""
    game = Game("web")
    game.state.pieces = [Piece.create(PieceType.ROOK, Color.RED, 5, 5)]
    board = board_widget.BoardWidget()
    board.resize(size, size)
    board.set_game(game, Color.RED, True)
    board.set_appearance(theme_name, "none", "traditional", mode)
    board.interactive = False
    canvas = QPixmap(size, size)
    canvas.fill(QColor("white"))
    board.render(canvas)
    return canvas.toImage()


def _raw(image: QImage) -> bytes:
    return bytes(image.constBits())


def differing_pixels(a: QImage, b: QImage) -> int:
    assert (a.width(), a.height()) == (b.width(), b.height())
    pa, pb = _raw(a), _raw(b)
    changed = 0
    for i in range(0, len(pa), 4):      # RGB32：每像素 4 字节
        if pa[i:i + 3] != pb[i:i + 3]:
            changed += 1
    return changed


def perceptible_pixels(a: QImage, b: QImage, delta: int = PERCEPTIBLE_DELTA) -> int:
    pa, pb = _raw(a), _raw(b)
    count = 0
    for i in range(0, len(pa), 4):
        if (abs(pa[i] - pb[i]) >= delta or abs(pa[i + 1] - pb[i + 1]) >= delta
                or abs(pa[i + 2] - pb[i + 2]) >= delta):
            count += 1
    return count


# --- 三个分支都要有 -------------------------------------------------------

@pytest.mark.parametrize("mode", [GLYPH_MODE, IMAGE_MODE])
def test_shadow_is_drawn_in_every_render_branch(qt_app: QApplication, mode: str) -> None:
    """字形与位图两条分支都必须有投影像素。"""
    on = render(mode=mode)
    off = render_without_shadow(mode=mode)
    assert differing_pixels(on, off) > 0, f"{mode} 模式下没有画投影（开/关投影渲染结果完全相同）"


def test_shadow_is_drawn_in_the_fallback_branch(qt_app: QApplication,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    """回退分支（无美术棋子）同样有投影 —— 因为它画在分发入口，不在分支里。"""
    monkeypatch.setattr(piece_assets, "pixmap", lambda *args, **kwargs: None)
    on = render(mode=IMAGE_MODE)
    off = render_without_shadow(mode=IMAGE_MODE)
    assert differing_pixels(on, off) > 0, "回退分支没有投影 —— 投影被搬进分支了"


# --- 必须真的看得见（这条抓的是"参数写了但不可见"） ----------------------

@pytest.mark.parametrize("theme_name", ["classic", "dark"])
def test_shadow_is_actually_visible(qt_app: QApplication, theme_name: str) -> None:
    """开/关投影的**可感知**差异必须 ≥ 2.0% 棋盘面积（浅色 / 深色各一次）。

    第一版纯色椭圆实测只有 0.40%（且是抗锯齿溢出，几何可见面积为 0），
    靠这条会被直接拦下 —— 而不是等到人肉截图才发现"加了等于没加"。
    """
    game = Game("web")
    board = board_widget.BoardWidget()
    board.resize(MEASURE, MEASURE)
    board.set_game(game, Color.RED, True)
    board.set_appearance(theme_name, "none", "traditional", GLYPH_MODE)
    board.interactive = False

    def snapshot() -> QImage:
        canvas = QPixmap(MEASURE, MEASURE)
        canvas.fill(QColor("white"))
        board.render(canvas)
        return canvas.toImage()

    on = snapshot()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(board_widget, "_piece_shadow_brush",
                      lambda: QBrush(Qt.BrushStyle.NoBrush))
        off = snapshot()
    ratio = perceptible_pixels(on, off) / (MEASURE * MEASURE)
    assert ratio >= MIN_VISIBLE_RATIO, (
        f"[{theme_name}] 投影可感知面积只有 {ratio:.2%}，低于验收线 {MIN_VISIBLE_RATIO:.0%}"
        "（参数写进去了但用户看不见 —— 先确认 PIECE_SHADOW_CORE_ALPHA / RATIO 是否又调回硬边椭圆）")


def test_shadow_leans_downward_instead_of_being_a_uniform_ring(qt_app: QApplication) -> None:
    """底部可见厚度必须 ≥ 顶部的 1.5 倍：影子重心向下，等宽就不是影子而是描边。"""
    game = Game("web")
    game.state.pieces = [Piece.create(PieceType.ROOK, Color.RED, 5, 5)]
    board = board_widget.BoardWidget()
    board.resize(MEASURE, MEASURE)
    board.set_game(game, Color.RED, True)
    board.set_appearance("classic", "none", "traditional", GLYPH_MODE)
    board.interactive = False

    def snapshot() -> QImage:
        canvas = QPixmap(MEASURE, MEASURE)
        canvas.fill(QColor("white"))
        board.render(canvas)
        return canvas.toImage()

    on = snapshot()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(board_widget, "_piece_shadow_brush",
                      lambda: QBrush(Qt.BrushStyle.NoBrush))
        off = snapshot()
    pa, pb = _raw(on), _raw(off)
    width = on.width()
    stride = len(pa) // on.height()

    def changed_at(x: int, y: int) -> bool:
        i = y * stride + x * 4
        return (abs(pa[i] - pb[i]) >= PERCEPTIBLE_DELTA
                or abs(pa[i + 1] - pb[i + 1]) >= PERCEPTIBLE_DELTA
                or abs(pa[i + 2] - pb[i + 2]) >= PERCEPTIBLE_DELTA)

    _, left, top, cw, ch = board._geometry()
    cx, cy = int(left + 5 * cw), int(top + 5 * ch)
    band = range(cx - 2, cx + 3)

    up = sum(1 for dy in range(-60, 0) if any(changed_at(x, cy + dy) for x in band))
    down = sum(1 for dy in range(0, 60) if any(changed_at(x, cy + dy) for x in band))
    assert up > 0 and down > 0, f"投影没有同时出现在上下两侧（上 {up}px / 下 {down}px）"
    assert down >= up * MIN_DOWNWARD_LEAN, (
        f"投影上下等宽（上 {up}px / 下 {down}px），看起来会是描边而不是落影")


# --- 硬约束 ---------------------------------------------------------------

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
    for name in ("PIECE_SHADOW_ALPHA", "PIECE_SHADOW_OFFSET", "PIECE_SHADOW_RATIO",
                 "PIECE_SHADOW_CORE_ALPHA", "PIECE_SHADOW_CORE_STOP"):
        assert hasattr(board_widget, name), f"缺少投影参数常量 {name}"


def test_shadow_brush_is_reused_instead_of_rebuilt_per_piece(qt_app: QApplication) -> None:
    """刷子必须复用：61 枚子 × 60fps = 每秒最多 3660 次构造，不能每枚子重建。

    判据是"渲染一整盘之后，缓存里只多了一个条目" —— 与实现方式（渐变/纯色）无关。

    `qt_app` 参数是**必需的**：本文件其它渲染用例都会先建 QApplication，
    这条若省掉就会"单独跑崩、跟文件跑过"—— 那是执行顺序在偷偷兜底，
    正是本项目最不想要的那种假绿（QA 在验收时点过这条风险）。
    """
    board_widget._SHADOW_BRUSH_CACHE.clear()
    game = Game("web")
    board = board_widget.BoardWidget()
    board.resize(MEASURE, MEASURE)
    board.set_game(game, Color.RED, True)
    board.set_appearance("classic", "none", "traditional", GLYPH_MODE)
    board.interactive = False
    canvas = QPixmap(MEASURE, MEASURE)
    canvas.fill(QColor("white"))
    board.render(canvas)
    assert len(board_widget._SHADOW_BRUSH_CACHE) == 1, (
        f"整盘渲染后应只缓存 1 个投影刷子，实际 {len(board_widget._SHADOW_BRUSH_CACHE)} 个"
        "（说明每枚子都在重建渐变）")
