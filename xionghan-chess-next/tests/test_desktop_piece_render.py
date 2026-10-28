"""棋子渲染的像素级验收：字形模式与图片模式的几何必须对齐。

## 三种渲染路径

- `piece_render="glyph"`（**默认**）：1.7.0 的字形棋子。这条路径必须**逐像素不变**，
  它是升级后老用户的默认观感；本文件用「禁掉图片缓存后仍能画出同样结果」守它。
- `piece_render="image"`：三风格美术图。
- 图片缺省（甲/刺/楯）：`image` 模式下按同风格底盘 + 统一衬线字形回退。

## 为什么用 `QWidget.render()` 而不是直接调 `paintEvent`

`BoardWidget.paintEvent` 自己 `QPainter(self)`，忽略传进来的 painter（历史实现如此）。
直接调用只能证明「不抛异常」，画布上什么也没有。`render()` 会走真正的绘制链，
所以像素断言才有意义。
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="渲染测试依赖 PySide6")

from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import Color, Piece, PieceType  # noqa: E402
from xionghan_chess.core.profiles import PROFILES  # noqa: E402
from xionghan_chess.desktop.config import DEFAULTS  # noqa: E402
from xionghan_chess.desktop.ui import piece_assets, theme  # noqa: E402
from xionghan_chess.desktop.ui.board_widget import (  # noqa: E402
    GLYPH_MODE, IMAGE_MODE, BoardWidget, _piece_font,
)

SIZE = 620
STYLES = ("traditional", "modern", "cartoon")
MISSING = (PieceType.ARMOR, PieceType.ASSASSIN, PieceType.SHIELD)


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    theme.load_bundled_fonts()
    return app


def render(style: str, mode: str, pieces: list[Piece]) -> tuple[QImage, BoardWidget]:
    game = Game(PROFILES["desktop_complete"])
    game.state.pieces = list(pieces)
    board = BoardWidget()
    board.resize(SIZE, SIZE)
    board.set_game(game, Color.RED, True)
    board.set_appearance("classic", "none", style, mode)
    board.interactive = False
    canvas = QPixmap(SIZE, SIZE)
    canvas.fill(QColor("white"))
    board.render(canvas)
    return canvas.toImage(), board


def ink_bounds(base: QImage, marked: QImage, board: BoardWidget) -> tuple[int, int, int, int]:
    """棋子盖住的像素区域（与「空盘」逐像素比对，只看棋子附近）。"""
    _, left, top, cw, ch = board._geometry()
    center_x, center_y = left + 6 * cw, top + 6 * ch
    span = int(cw * 0.75)
    x0 = max(0, int(center_x) - span)
    x1 = min(SIZE, int(center_x) + span)
    y0 = max(0, int(center_y) - span)
    y1 = min(SIZE, int(center_y) + span)
    min_x, min_y, max_x, max_y = 10 ** 9, 10 ** 9, -1, -1
    for y in range(y0, y1):
        for x in range(x0, x1):
            if base.pixel(x, y) != marked.pixel(x, y):
                min_x = min(min_x, x); max_x = max(max_x, x)
                min_y = min(min_y, y); max_y = max(max_y, y)
    assert max_x >= 0, "棋子在画布上没有留下任何墨迹"
    return min_x, min_y, max_x, max_y


def one_piece(kind: PieceType = PieceType.KING, color: Color = Color.RED) -> list[Piece]:
    return [Piece.create(kind, color, 6, 6)]


@pytest.mark.parametrize("style", STYLES)
def test_centers_do_not_move_between_glyph_and_image(qt_app: QApplication, style: str) -> None:
    """同一局面，字形与图片的棋子中心必须重合（±1px）。"""
    empty, _ = render(style, GLYPH_MODE, [])
    glyph, board = render(style, GLYPH_MODE, one_piece())
    image, _ = render(style, IMAGE_MODE, one_piece())
    gx0, gy0, gx1, gy1 = ink_bounds(empty, glyph, board)
    ix0, iy0, ix1, iy1 = ink_bounds(empty, image, board)
    assert abs((gx0 + gx1) - (ix0 + ix1)) / 2 <= 1, "图片模式水平偏移"
    assert abs((gy0 + gy1) - (iy0 + iy1)) / 2 <= 1, "图片模式垂直偏移"


@pytest.mark.parametrize("style", STYLES)
def test_disk_diameter_stays_0_78_cell(qt_app: QApplication, style: str) -> None:
    """盘径不变量：图片的墨迹直径 == `0.78 × cell`（±3%），与字形同量级。

    字形那条含描边（`max(2, 0.1R)` 向外各半），所以两者宽度允许差几个像素；
    判据是「图片没有缩水」，即图片宽度不能明显小于 `0.78 cell`。
    """
    empty, _ = render(style, GLYPH_MODE, [])
    image, board = render(style, IMAGE_MODE, one_piece())
    glyph, _ = render(style, GLYPH_MODE, one_piece())
    _, _left, _top, cw, _ch = board._geometry()
    expected = piece_assets.DISK_CELL_RATIO * cw
    ix0, _iy0, ix1, _iy1 = ink_bounds(empty, image, board)
    gx0, _gy0, gx1, _gy1 = ink_bounds(empty, glyph, board)
    image_width = ix1 - ix0 + 1
    glyph_width = gx1 - gx0 + 1
    # 容差取 `max(2px, 3%)`：小尺寸（cell≈44 → 盘径 34.7）下，平滑缩放会把
    # 4px 量化的源图（36px）画进 34.7 的目标矩形，抗锯齿再各吃掉半个像素，
    # ±1px 的纯像素容差必然误报。放大到 2px 下限才是「没有缩水」的真实判据。
    tolerance = max(2.0, expected * 0.03)
    assert abs(image_width - expected) <= tolerance, \
        f"图片盘径 {image_width}，期望 {expected:.1f}（0.78 cell），容差 {tolerance:.1f}"
    assert abs(image_width - glyph_width) <= 4, \
        f"字形与图片盘径相差 {abs(image_width - glyph_width)} px（{glyph_width} vs {image_width}）"


@pytest.mark.parametrize("kind", MISSING)
def test_missing_art_still_draws_ink_in_image_mode(qt_app: QApplication, kind: PieceType) -> None:
    """甲/刺/楯 没有美术，但 image 模式下必须画出同风格底盘 + 字形（不能空白）。"""
    style = "traditional"
    empty, board = render(style, IMAGE_MODE, [])
    marked, _ = render(style, IMAGE_MODE, one_piece(kind))
    ink_bounds(empty, marked, board)  # 没有墨迹会在这里 assert 失败
    assert piece_assets.is_missing(style, Color.RED, kind)


def test_default_glyph_mode_never_touches_artwork(qt_app: QApplication,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    """默认 `piece_render="glyph"` 必须与 1.7.0 完全一致 —— 连图片缓存都不该碰。

    判据不是「跟另一个 glyph 渲染比」（那是永真），而是把 `piece_assets.pixmap`
    换成直接 raise：glyph 模式下渲染仍必须成功、且结果逐像素等于替换前的渲染。
    """
    before, board = render("traditional", GLYPH_MODE, one_piece())
    assert board.piece_render == GLYPH_MODE
    assert DEFAULTS["piece_render"] == "glyph"

    def explode(*args: object, **kwargs: object) -> None:
        raise AssertionError("glyph 模式不应访问图片缓存")

    monkeypatch.setattr(piece_assets, "pixmap", explode)
    after, _ = render("traditional", GLYPH_MODE, one_piece())
    assert before == after, "glyph 模式的渲染结果发生了变化（1.7.0 观感被改动）"


def test_config_without_piece_render_stays_glyph(qt_app: QApplication) -> None:
    """老配置没有 `piece_render` 这个键：`.get(..., "glyph")` 必须落在字形模式。"""
    legacy_config: dict[str, object] = {"piece_style": "modern"}
    assert legacy_config.get("piece_render", "glyph") == "glyph"
    board = BoardWidget()
    board.set_appearance("classic", "none", "modern",
                         legacy_config.get("piece_render", "glyph"))
    assert board.piece_render == GLYPH_MODE


# ---------------------------------------------------------------------------
# image 模式的回退字形：字号必须与位图同度量
# ---------------------------------------------------------------------------
def _text_ink(radius: float, mode: str, glyph: str = "漢") -> tuple[int, float, float]:
    """在透明画布上只画那个字，返回 (字高, 字高/盘径, 墨量/字高²)。"""
    font: QFont = _piece_font(radius, mode)
    side = int(radius * 2)
    image = QImage(side, side, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setFont(font)
    painter.setPen(QColor(0, 0, 0))
    painter.drawText(0, 0, side, side, Qt.AlignmentFlag.AlignCenter, glyph)
    painter.end()
    min_x, min_y, max_x, max_y, area = side, side, -1, -1, 0
    for y in range(side):
        for x in range(side):
            if image.pixelColor(x, y).alpha() > 128:
                area += 1
                min_x = min(min_x, x); max_x = max(max_x, x)
                min_y = min(min_y, y); max_y = max(max_y, y)
    height = max_y - min_y + 1 if max_y >= 0 else 0
    assert height > 0, "回退字形没有画出任何墨迹"
    return height, height / (2 * radius), area / (height * height)


@pytest.mark.parametrize("radius", [24.6, 39.0, 50.0])
def test_fallback_glyph_height_matches_bitmap_scale(qt_app: QApplication, radius: float) -> None:
    """`字高 / 盘径` 必须落在 0.49–0.56（66 张位图实测 0.496–0.555）。

    1.7.0 的兜底是 `pointSize`：实测 0.69–0.73，比位图大 33%，所以 `image` 模式
    的缺图格会「又大又黑」。这条断言就是那个回归的拦截点。
    """
    _height, ratio, _density = _text_ink(radius, "image_fallback")
    assert 0.49 <= ratio <= 0.56, f"radius={radius} 字高/盘径={ratio:.3f}"


@pytest.mark.parametrize("radius", [24.6, 39.0, 50.0])
def test_fallback_glyph_is_lighter_than_legacy_glyph(qt_app: QApplication, radius: float) -> None:
    """回退字形必须比 1.7.0 的兜底更轻（Bold → Normal）。

    实测口径：`墨量 / 字高²` 从 0.43~0.45 降到 0.32~0.36。这里只钉「明显变轻」
    （≥10%），不钉绝对值 —— 绝对值依赖抗锯齿与阈值，跨 Qt 版本会漂。
    """
    _h1, _r1, legacy = _text_ink(radius, GLYPH_MODE)
    _h2, _r2, fallback = _text_ink(radius, "image_fallback")
    assert fallback <= legacy * 0.9, f"radius={radius} 回退 {fallback:.3f} 未比旧兜底 {legacy:.3f} 更轻"
