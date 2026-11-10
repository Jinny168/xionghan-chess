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

import sys

import pytest

pytest.importorskip("PySide6", reason="渲染测试依赖 PySide6")

from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from xionghan_chess.core.game import Game  # noqa: E402
from xionghan_chess.core.model import Color, Piece, PieceType  # noqa: E402
from xionghan_chess.core.profiles import PROFILES  # noqa: E402
from xionghan_chess.desktop.config import DEFAULTS  # noqa: E402
from xionghan_chess.desktop.ui import piece_assets, theme  # noqa: E402
from xionghan_chess.desktop.ui.board_widget import (  # noqa: E402
    GLYPH_MODE,
    IMAGE_MODE,
    BoardWidget,
    _piece_font,
    draw_fallback_piece,
)

SIZE = 620
STYLES = ("traditional", "modern", "cartoon")
# 美术已覆盖全部 11 型（2026-10-31 起无缺图型）：没有"回退绘制"的样本
MISSING: tuple[PieceType, ...] = ()


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    theme.load_bundled_fonts()
    return app


@pytest.fixture(autouse=True)
def _no_piece_shadow(monkeypatch: pytest.MonkeyPatch) -> None:
    """本文件量的是**棋子本体**的墨迹，投影必须先关掉。

    P1-1 加了棋子投影后，投影的可见带（外半径 1.30r + 圆心下移 0.09r）会落在
    棋子之外，于是「墨迹包围盒」量到的就不再是盘径，而是「盘径 + 一圈影」——
    `test_disk_diameter_stays_0_78_cell` 因此假红。

    这不是放宽阈值：被测命题本来就是「棋子本体是 0.78 cell」，
    把影算进去属于**测量对象错了**。投影本身的行为由
    `test_desktop_piece_shadow.py` 单独覆盖（可见强度 / 向下的重心 / 三分支）。

    **关投影的方式是改「数据」而不是改「函数」**：这里把强度旋钮置 0，语义上就是
    "关掉"（`test_strength_zero_renders_exactly_like_no_shadow` 已经把
    "强度 0 ⇒ 逐像素无影"钉死）。改成 patch 函数曾经踩过坑：
    `_piece_shadow_brush` 后来加了 `gain` 形参，而本文件的 `lambda:` 是 0 参写法，
    TypeError 在 `paintEvent` 里被 Qt 吞掉 → 这个文件 7 条渲染断言集体假红，
    且报错看不出根因。**签名是跨文件契约，能不 patch 函数就别 patch。**
    """
    import xionghan_chess.desktop.ui.board_widget as board_widget

    monkeypatch.setattr(board_widget, "PIECE_SHADOW_STRENGTH", 0.0)


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
    min_x, min_y, max_x, max_y = 10**9, 10**9, -1, -1
    for y in range(y0, y1):
        for x in range(x0, x1):
            if base.pixel(x, y) != marked.pixel(x, y):
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
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
    assert abs(image_width - expected) <= tolerance, (
        f"图片盘径 {image_width}，期望 {expected:.1f}（0.78 cell），容差 {tolerance:.1f}"
    )
    assert abs(image_width - glyph_width) <= 4, (
        f"字形与图片盘径相差 {abs(image_width - glyph_width)} px（{glyph_width} vs {image_width}）"
    )


@pytest.mark.parametrize("kind", MISSING)
def test_missing_art_still_draws_ink_in_image_mode(qt_app: QApplication, kind: PieceType) -> None:
    """刺没有美术，但 image 模式下必须画出同风格底盘 + 字形（不能空白）。"""
    style = "traditional"
    empty, board = render(style, IMAGE_MODE, [])
    marked, _ = render(style, IMAGE_MODE, one_piece(kind))
    ink_bounds(empty, marked, board)  # 没有墨迹会在这里 assert 失败
    assert piece_assets.is_missing(style, Color.RED, kind)


def test_default_glyph_mode_never_touches_artwork(qt_app: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
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
    board.set_appearance("classic", "none", "modern", legacy_config.get("piece_render", "glyph"))
    assert board.piece_render == GLYPH_MODE


# ---------------------------------------------------------------------------
# image 模式的回退字形：字族随风格、字号与字重与位图同量级
# ---------------------------------------------------------------------------
# ⚠️ 密度判据**只用同一次测量内的比值**（`alpha>128` 的不同标定会让绝对值差 20–25%，
# 硬编码绝对密度必然在另一种量法下误红）。这里两侧共用同一个掩膜：
#   · 画布底填**该风格盘面色**；
#   · 字用**该风格该色的字色**（不是纯黑，否则色距掩膜会把字形权重算偏）；
#   · 只统计 `r < 0.62R` 的圆盘内部，排除外环与描边。
# 回退渲染**与具体兵种无关**（画的是字形，不看美术在不在），
# 所以用在用 11 型做样本即可 —— 既保住这条管线，又不依赖"缺图型"。
FALLBACK_KINDS: tuple[PieceType, ...] = tuple(piece_assets.SUFFIX)
ART_KINDS = tuple(piece_assets.SUFFIX)
SAMPLE_RADIUS = 55.0  # 盘径 110px：密度只在 dev ≥ 110px 档有意义
FILL_COLOR = {
    "traditional": (252, 248, 238),
    "modern": (255, 255, 255),
    "cartoon": (255, 255, 255),
}
# 密度基线**按 (平台, Qt 平台插件) 二维登记**：Qt 的字族光栅后端不同，同一份代码的
# 密度**不可互比**。这条口径经过两次修正才定下来，别再退回去：
#   ① 第一版只按 `sys.platform` 分档 —— **不够**。实测同一台 win32 机器、同一个
#      commit、同一条命令，只改一个环境变量就翻脸：
#        windows 插件   ratio = 1.14 / 1.45 / 1.00 → 对旧 win32 档 1.10/1.51/1.04 绿
#        offscreen 插件 ratio = 0.77 / 0.91 / 0.78 → 三风格一致偏低约 30%，远超 ±0.12
#      于是"本机绿 / 本机红"会随 shell 里有没有 `QT_QPA_PLATFORM=offscreen` 漂移，
#      而门禁只认得其中一档。**隐含上下文依赖比阈值松紧危险得多**，这是修正的动机。
#      （触发路径：整跑会 import 到 `tests/test_desktop_dialog_lifetime.py`，它在
#       import 期 `setdefault("QT_QPA_PLATFORM","offscreen")`；单跑不会 → 同一份代码
#       两种渲染上下文。修法不是删那行 setdefault，而是把插件变成**登记维度**。）
#   ② 所以键改成 `(sys.platform, QApplication.platformName())`，未登记的组合
#      **skip 并说明原因**，绝不拿另一档的基线硬比（那必然误红）。
# 这是**回归指标**（防漂移），不是"正确性判据" —— Windows 窗口插件下没有任何字重能让
# 三风格同时进 0.85–1.25。
#
# 标定来源（每条都要能追到一次实测，不许凭感觉填）：
#   · ("win32","windows") —— Windows 11 本机标定，原值原样保留（不许为了让 Linux 通过
#     而放宽，否则会掩盖 Windows 侧回归）；复测 ratio = 1.14 / 1.45 / 1.00，在 ±0.12 内。
#   · ("win32","offscreen") —— 2026-11-10 本机实测（commit f4d0fcd，仅设
#     `QT_QPA_PLATFORM=offscreen`）：fallback/artwork = 0.334/0.433、0.407/0.446、
#     0.407/0.524 ⇒ ratio 0.77 / 0.91 / 0.78；两次独立整跑逐位相同（lead-programmer
#     另一台独立复算 0.7720/0.9116/0.7780，逐位一致）。
#   · ("linux","offscreen") —— CI #127（ubuntu runner，2026-11-10）的 `::notice::` 注解
#     原文（ci.yml 的 `-rfEP` 取证首次生效，注释可匿名经 API 复核）：
#       [density] linux/traditional: fallback=0.295 artwork=0.433 ratio=0.68 baseline=0.76
#       [density] linux/modern:      fallback=0.213 artwork=0.446 ratio=0.48 baseline=0.48
#       [density] linux/cartoon:     fallback=0.214 artwork=0.524 ratio=0.41 baseline=0.41
#     traditional 从 **0.76（历史暂记）改为实测 0.68**：暂记值不是"保守"而是**吃掉灵敏度**
#     —— 真值 0.68 时，基线 0.76 要掉到 0.65 以下才报（|0.65-0.76|=0.11<0.12），
#     等于漏掉一次 0.03 的真实漂移；写死 0.68 后两侧各留 0.12。modern/cartoon 与
#     CI #123 的实测（0.48 / 0.41）一致，未动。
#     精度：本文件那行 ratio 打 **3 位小数**，所以下一次 notice 能把每一档定到 ±0.001；
#     0.68 这格是 2 位小数的历史值（0.295/0.433 = 0.6813），在 ±0.12 公差下绰绰有余。
# 旧的单键 "offscreen"（0.76/0.96/0.82）已废弃：它把 macOS/Windows 的 offscreen 度量
# 混成一档，与 ubuntu fontconfig 不是一回事（#123 实证差一倍），与现在这版也不同源。
DENSITY_BASELINE: dict[tuple[str, str], dict[str, float]] = {
    ("win32", "windows"): {"traditional": 1.10, "modern": 1.51, "cartoon": 1.04},
    ("win32", "offscreen"): {"traditional": 0.77, "modern": 0.91, "cartoon": 0.78},
    ("linux", "offscreen"): {"traditional": 0.68, "modern": 0.48, "cartoon": 0.41},
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
            distance = abs(color.red() - fill[0]) + abs(color.green() - fill[1]) + abs(color.blue() - fill[2])
            if distance > 60:
                area += 1
                min_y = min(min_y, y)
                max_y = max(max_y, y)
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
        image = _fallback_image(style, kind, SAMPLE_RADIUS) if fallback else _artwork_image(style, kind, SAMPLE_RADIUS)
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
def test_fallback_density_matches_the_platform_baseline(qt_app: QApplication, style: str) -> None:
    """密度是**回归指标**，不是"正确性判据"——只防漂移，不判对错。

    口径：**3 型回退均值 ÷ 11 型位图均值**，两侧共用同一个 `_ink_stats()` 掩膜
    （画布填该风格盘面色 + 色距 >60 + 只统计 `r < 0.62R`）。

    ⚠️ 三条铁律：
    1. **基线按 (平台, Qt 平台插件) 二维登记**：Qt 的字族光栅后端不同，同一份代码的
       密度不可互比。同一个 win32 在 `windows` 与 `offscreen` 两种插件下差约 30%
       （实测 1.14/1.45/1.00 vs 0.77/0.91/0.78）—— 只按 `sys.platform` 分档会让
       "本机绿/本机红"随 `QT_QPA_PLATFORM` 漂移。见 `DENSITY_BASELINE` 的标定来源注释；
    2. **未登记的组合一律 skip**，不拿另一档的基线硬比 —— 跨组合比较必然误红；
    3. **必须先 `theme.load_bundled_fonts()`**（`qt_app` fixture 已做），否则字族落到
       系统替代字体，墨量只剩约 1/10，任何比值都不可信。

    真正的硬门禁在别处：字族随风格（`test_fallback_family_follows_style`）、
    字重三风格一致且为 Normal（`test_fallback_weight_is_normal_and_uniform`）、
    字高/盘径 0.48–0.56、盘径 0.78 格。这里只在超出基线 ±0.12 时报「漂移了」。
    """
    platform = sys.platform
    # 插件名从**实际在跑的** QApplication 取，不读 env：env 只说明"请求了什么"，
    # platformName() 才是"真的用了什么"（插件加载失败会 fallback，两者会不一致）。
    qpa = qt_app.platformName()
    key = (platform, qpa)
    baseline = DENSITY_BASELINE.get(key)
    if baseline is None:
        pytest.skip(
            f"采集环境 {key!r} 没有密度基线（已登记：{sorted(DENSITY_BASELINE)}）。"
            "密度与 Qt 平台插件强相关，不要拿没标定过的组合的数来比"
        )
    _fh, fallback = _style_density(style, FALLBACK_KINDS, fallback=True)
    _ah, artwork = _style_density(style, ART_KINDS, fallback=False)
    ratio = fallback / artwork
    expected = baseline[style]
    # 实测值无论绿红都打进日志。linux/offscreen 的每一格都是靠这行 notice 定的值
    # （见基线表注释）。**ratio 打 3 位小数**：2 位会让"精确标定"的上限只有 ±0.005，
    # 而标定值直接决定下次能发现多大的漂移；3 位够把每一档定到 ±0.001。
    # 行里必须带 qpa：同一平台两种插件的数差 30%，只写 platform 的话日志会误导标定。
    print(
        f"[density] {platform}/{qpa}/{style}: fallback={fallback:.3f} artwork={artwork:.3f} "
        f"ratio={ratio:.3f} baseline={expected:.2f}",
        flush=True,
    )
    assert abs(ratio - expected) <= DENSITY_TOLERANCE, (
        f"{platform}/{qpa}/{style}: 回退密度 {fallback:.3f} / 图片 {artwork:.3f} = {ratio:.3f}，"
        f"基线 {expected:.2f} ± {DENSITY_TOLERANCE} —— 渲染管线或字重/字族被改动了？"
    )


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
