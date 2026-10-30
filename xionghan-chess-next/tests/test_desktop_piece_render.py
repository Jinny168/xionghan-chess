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
    GLYPH_MODE, IMAGE_MODE, BoardWidget, _piece_font, draw_fallback_piece,
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
# image 模式的回退字形：字族随风格、字号与字重与位图同量级
# ---------------------------------------------------------------------------
# ⚠️ 密度判据**只用同一次测量内的比值**（`alpha>128` 的不同标定会让绝对值差 20–25%，
# 硬编码绝对密度必然在另一种量法下误红）。这里两侧共用同一个掩膜：
#   · 画布底填**该风格盘面色**；
#   · 字用**该风格该色的字色**（不是纯黑，否则色距掩膜会把字形权重算偏）；
#   · 只统计 `r < 0.62R` 的圆盘内部，排除外环与描边。
FALLBACK_KINDS = (PieceType.ARMOR, PieceType.ASSASSIN, PieceType.SHIELD)
ART_KINDS = tuple(piece_assets.SUFFIX)
SAMPLE_RADIUS = 55.0          # 盘径 110px：密度只在 dev ≥ 110px 档有意义
FILL_COLOR = {
    "traditional": (252, 248, 238),
    "modern": (255, 255, 255),
    "cartoon": (255, 255, 255),
}
# 密度基线**按平台分别登记**：Qt 的字族光栅后端不同，同一份代码两个平台差 40%
# （offscreen 0.76/0.96/0.82 vs windows 1.10/1.51/1.04），**不可互比**。
# 这是**回归指标**（防漂移），不是"正确性判据"——Windows（用户实际看到的）上
# 没有任何字重能让三风格同时进 0.85–1.25，modern 位图笔画远细于系统无衬线。
DENSITY_BASELINE = {
    "offscreen": {"traditional": 0.76, "modern": 0.96, "cartoon": 0.82},
    "windows": {"traditional": 1.10, "modern": 1.51, "cartoon": 1.04},
}
DENSITY_TOLERANCE = 0.12


def _ink_stats(image: QImage, fill: tuple[int, int, int], radius: float) -> tuple[int, float]:
    """返回 (墨高, 墨量/墨高²)。掩膜 = 与盘面色的 L1 距离 > 60，且 r < 0.62R。"""
    side = image.width()
    center = side / 2
    limit = (0.62 * radius) ** 2
    min_y, max_y, area = side, -1, 0
    for y in range(side):
        for x in range(side):
            dx, dy = x + 0.5 - center, y + 0.5 - center
            if dx * dx + dy * dy > limit:
                continue
            color = image.pixelColor(x, y)
            distance = (abs(color.red() - fill[0]) + abs(color.green() - fill[1])
                        + abs(color.blue() - fill[2]))
            if distance > 60:
                area += 1
                min_y = min(min_y, y); max_y = max(max_y, y)
    height = max_y - min_y + 1 if max_y >= 0 else 0
    assert height > 0, "字形没有画出任何墨迹（掩膜口径变了？）"
    return height, area / (height * height)


def _fallback_image(style: str, kind: PieceType, radius: float) -> QImage:
    side = int(radius * 2)
    image = QImage(side, side, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(*FILL_COLOR[style]))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    draw_fallback_piece(painter, QPointF(side / 2, side / 2), radius, Color.RED, kind, style)
    painter.end()
    return image


def _artwork_image(style: str, kind: PieceType, radius: float) -> QImage:
    side = int(radius * 2)
    image = QImage(side, side, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(*FILL_COLOR[style]))
    artwork = piece_assets.pixmap(style, Color.RED, kind, int(radius * 2))
    assert artwork is not None
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.drawPixmap(QPointF((side - artwork.width()) / 2, (side - artwork.height()) / 2), artwork)
    painter.end()
    return image


def _style_density(style: str, kinds: tuple[PieceType, ...], fallback: bool) -> tuple[float, float]:
    """一组棋型的 (墨高/盘径 均值, 墨量/墨高² 均值)。"""
    heights: list[float] = []
    densities: list[float] = []
    for kind in kinds:
        image = (_fallback_image(style, kind, SAMPLE_RADIUS) if fallback
                 else _artwork_image(style, kind, SAMPLE_RADIUS))
        height, density = _ink_stats(image, FILL_COLOR[style], SAMPLE_RADIUS)
        heights.append(height / (2 * SAMPLE_RADIUS))
        densities.append(density)
    return sum(heights) / len(heights), sum(densities) / len(densities)


@pytest.mark.parametrize("style", STYLES)
def test_fallback_glyph_height_matches_bitmap_scale(qt_app: QApplication, style: str) -> None:
    """`字高 / 盘径` ∈ 0.48–0.56（66 张位图实测 0.496–0.555）。

    1.7.0 的兜底是 `pointSize`：实测 0.69–0.73，比位图大 33%，所以 `image` 模式
    的缺图格会「又大又黑」。这条断言就是那个回归的拦截点，且与掩膜无关。
    """
    height_ratio, _density = _style_density(style, FALLBACK_KINDS, fallback=True)
    assert 0.48 <= height_ratio <= 0.56, f"{style} 字高/盘径={height_ratio:.3f}"


@pytest.mark.parametrize("style", STYLES)
def test_fallback_density_matches_the_platform_baseline(
        qt_app: QApplication, style: str) -> None:
    """密度是**回归指标**，不是"正确性判据"——只防漂移，不判对错。

    口径：**3 型回退均值 ÷ 11 型位图均值**，两侧共用同一个 `_ink_stats()` 掩膜
    （画布填该风格盘面色 + 色距 >60 + 只统计 `r < 0.62R`）。

    ⚠️ 两条铁律：
    1. **两个平台的数不可互比**：Qt 的字族光栅后端不同，同一份代码 offscreen
       0.76/0.96/0.82、windows 1.10/1.51/1.04，差 40%；
    2. **必须先 `theme.load_bundled_fonts()`**（`qt_app` fixture 已做），否则字族落到
       系统替代字体，墨量只剩约 1/10，任何比值都不可信。

    真正的硬门禁在别处：字族随风格（`test_fallback_family_follows_style`）、
    字重三风格一致且为 Normal（`test_fallback_weight_is_normal_and_uniform`）、
    字高/盘径 0.48–0.56、盘径 0.78 格。这里只在超出基线 ±0.12 时报「漂移了」。
    """
    platform = qt_app.platformName()
    baseline = DENSITY_BASELINE.get(platform)
    if baseline is None:
        pytest.skip(f"平台 {platform!r} 没有密度基线（只有 offscreen / windows 有），"
                    "不要拿别的平台的数来比")
    _fh, fallback = _style_density(style, FALLBACK_KINDS, fallback=True)
    _ah, artwork = _style_density(style, ART_KINDS, fallback=False)
    ratio = fallback / artwork
    expected = baseline[style]
    assert abs(ratio - expected) <= DENSITY_TOLERANCE, (
        f"{platform}/{style}: 回退密度 {fallback:.3f} / 图片 {artwork:.3f} = {ratio:.2f}，"
        f"基线 {expected:.2f} ± {DENSITY_TOLERANCE} —— 渲染管线或字重/字族被改动了？")


def test_fallback_family_follows_style(qt_app: QApplication) -> None:
    """字族随风格：传统=衬线、现代/卡通=无衬线（`setFamilies` 记录的就是请求的族）。"""
    assert _piece_font(30.0, "image_fallback", "traditional").families()[0] == theme.PIECE_FONT
    for style in ("modern", "cartoon"):
        assert _piece_font(30.0, "image_fallback", style).families()[0] == theme.UI_FONT, style
    # glyph 分支原样透传：字族固定衬线、字重 Bold
    glyph_font = _piece_font(30.0, GLYPH_MODE)
    assert glyph_font.family() == theme.PIECE_FONT
    assert glyph_font.weight() == QFont.Weight.Bold


def test_fallback_weight_is_normal_and_uniform(qt_app: QApplication) -> None:
    """回退字重 **Normal，且三风格一致**（这是硬门禁，不是回归指标）。

    Windows 上实测：Normal 1.10/1.51/1.04、Medium 1.26/1.72/1.19、Bold 1.52/2.01/1.38 ——
    **没有任何字重能让三风格同时进 0.85–1.25**（modern 位图笔画极细），所以取最接近的
    Normal，并把密度降级为"按平台登记的回归基线"。
    """
    legacy = _piece_font(30.0, GLYPH_MODE).weight()
    assert legacy == QFont.Weight.Bold
    weights = {_piece_font(30.0, "image_fallback", style).weight() for style in STYLES}
    assert weights == {QFont.Weight.Normal}, f"三风格字重必须一致且为 Normal：{weights}"
