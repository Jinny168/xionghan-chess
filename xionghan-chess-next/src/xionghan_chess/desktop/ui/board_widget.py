"""棋盘控件（阶段1 S1-2 从 app.py 抽出，362 行）。

职责很窄：**只做渲染与鼠标输入**。规则、合法着法、判和全在 `core/`；
坐标换算委托给 `ui/board_geometry.py`（纯函数，可单测）。

抽出的动机：`app.py` 原本 1200+ 行单体，UI/交互/网络/渲染全混在一起，无法单测也无法
分人维护（见 docs/AUDIT_DESKTOP_1.7.0.md 轴 4）。
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush, QColor, QFont, QMouseEvent, QPainter, QPaintEvent, QPen, QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget

from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color, Move, Piece, PieceType, Position
from xionghan_chess.i18n import t

from . import piece_assets, theme
from .board_geometry import cell_layout, point_to_position, view_position


# 缺图回退（**仅 image 模式**）的配色：美术从 66 张位图反推，让回退格与位图同材质。
# 传统=象牙白+深棕环，现代=纯白+细红/黑环，卡通=纯白+粗粉/蓝环。
# `radius_ratio` 是描边宽相对盘半径的系数（160 画布下 3/5/≥8 px 折算而来）。
FALLBACK_STYLE: dict[str, dict[str, object]] = {
    "traditional": {
        "fill": (252, 248, 238), "inner_fill": (245, 240, 228),
        "ring": (80, 50, 20), "ring_ratio": 0.022, "inner_ring": (180, 160, 130),
        "text": {Color.RED: (190, 35, 35), Color.BLACK: (30, 30, 30)},
    },
    "modern": {
        "fill": (255, 255, 255), "inner_fill": None,
        "ring": {Color.RED: (220, 50, 50), Color.BLACK: (40, 40, 40)},
        "ring_ratio": 0.036, "inner_ring": "ring",
        "text": {Color.RED: (220, 50, 50), Color.BLACK: (40, 40, 40)},
    },
    "cartoon": {
        "fill": (255, 255, 255), "inner_fill": None,
        "ring": {Color.RED: (255, 100, 100), Color.BLACK: (100, 150, 220)},
        "ring_ratio": 0.058, "inner_ring": None,
        "text": {Color.RED: (200, 50, 50), Color.BLACK: (50, 100, 180)},
    },
}

# 可走点（空位落点）的视觉参数。
# 半径 `.13`（上限 .16）：再大会和 0.39 的棋子抢视觉，三格连点会连成"毛毛虫"。
# 颜色按主题取：浅色四主题用**该主题的 accent**；深色主题必须换成浅灰绿，
# 因为 dark 的 accent `#8e3b32` 是红色，会和"可吃红叉"混淆，且深绿在深底上直接消失。
LEGAL_DOT_RATIO = 0.13
LEGAL_DOT_ALPHA_LIGHT = 0.55
LEGAL_DOT_ALPHA_DARK = 0.60
LEGAL_DOT_DARK_RGB = (0x9F, 0xBF, 0xA8)   # #9fbfa8 浅灰绿

# 落子动画：460ms / 20ms = 23 帧（原来 350ms / 25ms ≈ 14 帧，肉眼只有 ~9 帧可见）。
# 为什么不抄网页的 900ms：太拖沓。为什么不是 550/16：实测 900×900 单帧 p95 10.9ms、
# **max 14.3ms**（超 12ms 掉帧线），1470px 更大时 p95 已 16.2ms —— 按"单帧 >12ms 就回退"
# 的规则取 450ms/20ms 一档：预算 20ms 时两个尺寸的 p95（10.9 / 16.2）都在预算内。
# 结束即停表，不常驻定时器。
ANIMATION_TIMER_MS = 20
ANIMATION_FRAMES = 23
# 将军脉冲保持原来的 600ms 观感（24 帧 × 25ms），换 16ms 定时器后需重算帧数。
CHECK_PULSE_FRAMES = 38

GLYPH_MODE = "glyph"
IMAGE_MODE = "image"
PIECE_RENDER_MODES = (GLYPH_MODE, IMAGE_MODE)


def _color(value: object, color: Color) -> QColor:
    """配色项可能是三元素元组，也可能是 `{Color: 元组}` 映射。"""
    if isinstance(value, dict):
        value = value[color]
    return QColor(*value)  # type: ignore[misc]


# 缺图回退的字族随风格：位图传统是衬线笔锋、现代/卡通是黑体，
# 用同一族会让 12 枚回退子（占一盘 19.4%）在 modern/cartoon 下像「外来户」。
# 值存**属性名**而不是 family 字符串：`theme.PIECE_FONT/UI_FONT` 会被
# `load_bundled_fonts()` **重新绑定**，import 时把名字拷进字典就会读到默认值。
# ⚠️ 晚绑定，勿改成字面量 —— 改了就只在对 `load_bundled_fonts()` 之前生效。
STYLE_FONT: dict[str, str] = {
    "traditional": "PIECE_FONT",
    "modern": "UI_FONT",
    "cartoon": "UI_FONT",
}


def _piece_font(radius: float, mode: str, style: str = "traditional") -> QFont:
    """棋子字体：两种模式的字号/字重**刻意不同**，不要合并参数。

    - `glyph`：**逐字保留 1.7.0 的构造**（pointSize + Bold）。默认模式占 62 枚棋子，
      改一个数字就是全盘观感回归；`tests/test_desktop_piece_render.py` 守着这条。
    - `image_fallback`：与位图同度量 —— `pixelSize`（逻辑像素，Qt 自己乘 DPR，
      **不要**再乘 `devicePixelRatioF()`）+ `Normal`（Bold 在 7 字均值下偏重 34~60%），
      字族随 `style` 变（传统衬线 / 现代·卡通无衬线）。

    ⚠️ 别按 `OS/2.usWeightClass` 推断粗细：随包两个子集的元数据（Sans=100、
    Serif=200）与实际光栅结果**相反**（同字高下 Sans 比 Serif 重 11%~71%）。
    """
    if mode == GLYPH_MODE:
        return QFont(theme.PIECE_FONT, max(13, int(radius * 1.15)), QFont.Weight.Bold)
    family = getattr(theme, STYLE_FONT.get(style, "PIECE_FONT"))
    font = QFont()
    font.setFamilies([family])
    # `round` 不是 `int`：760×560 时 radius=12.30，int 给 13、round 给 14，
    # 差这 1px 会让「字高 / 盘径」从 0.52 掉到 0.49（刚好出带）。
    font.setPixelSize(max(9, round(radius * 1.12)))
    # 字重 **Normal，三风格一致**。
    # 密度（3 型回退均值 ÷ 11 型位图均值）在两个平台上差 40%，不可互比：
    #   offscreen(Normal) 0.89 / 1.11 / 0.95；windows(Normal) 1.10 / 1.51 / 1.04。
    # Windows（用户实际看到的）上**没有任何字重能让三风格同时进 0.85–1.25** ——
    # modern 位图笔画远细于任何系统无衬线，同字高下最低就是 1.51；且 Medium/Bold
    # 只会更大（1.72 / 2.01）。所以选三条里最接近的 Normal，密度只当**回归指标**。
    font.setWeight(QFont.Weight.Normal)
    return font


def draw_piece_glyph(painter: QPainter, center: QPointF, radius: float,
                     piece: Piece, style: str) -> None:
    """画一枚**字形**棋子（圆片 + 汉字）—— 默认 `piece_render="glyph"` 的渲染路径。

    1.7.0 的观感即此实现，**不要改动里面的颜色/字号/字重**：`glyph` 模式下
    62 枚棋子全都走这里，任何「顺手整洁化」都是全盘回归。
    """
    if style == "modern":
        brush = QBrush(QColor("#f9e7bb"))
    elif style == "cartoon":
        brush = QBrush(QColor("#ffd98e"))
    else:
        gradient = QRadialGradient(center.x()-radius*.25, center.y()-radius*.3, radius*1.2)
        gradient.setColorAt(0, QColor("#fff0c5")); gradient.setColorAt(1, QColor("#d4a763"))
        brush = QBrush(gradient)
    outline = QColor("#9a2424") if piece.color is Color.RED else QColor("#24211e")
    painter.setBrush(brush); painter.setPen(QPen(outline, max(2, radius*(.13 if style == "cartoon" else .1))))
    painter.drawEllipse(center, radius, radius)
    if style == "modern":
        painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(QPen(outline, 1))
        painter.drawEllipse(center, radius * .82, radius * .82)
    painter.setFont(_piece_font(radius, GLYPH_MODE, style))
    painter.setPen(QColor("#9a2424") if piece.color is Color.RED else QColor("#24211e"))
    painter.drawText(int(center.x()-radius), int(center.y()-radius), int(radius*2), int(radius*2), Qt.AlignmentFlag.AlignCenter, theme.NAMES[piece.color][piece.type])


def draw_fallback_piece(painter: QPainter, center: QPointF, radius: float,
                        color: Color, piece_type: PieceType, style: str) -> None:
    """`image` 模式下**没有美术**的棋型（甲/刺/楯）怎么画。

    与位图同材质：盘径仍是 `0.78 cell`，填充/环色/描边宽按风格取自 `FALLBACK_STYLE`，
    字用 `pixelSize` + `Normal` 把「字高/盘径」压到 0.52（位图实测 0.496–0.555）。
    棋盘与棋子图谱**共用这一个函数**，两处不允许各写一份。
    """
    spec = FALLBACK_STYLE[style if style in FALLBACK_STYLE else "traditional"]
    ring = _color(spec["ring"], color)
    painter.setBrush(QBrush(_color(spec["fill"], color)))
    painter.setPen(QPen(ring, max(2, radius * float(spec["ring_ratio"]))))  # type: ignore[arg-type]
    painter.drawEllipse(center, radius, radius)
    inner_fill = spec["inner_fill"]
    if inner_fill is not None:
        painter.setBrush(QBrush(_color(inner_fill, color)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius * .86, radius * .86)
    inner_ring = spec["inner_ring"]
    if inner_ring is not None:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(_color(spec["ring"] if inner_ring == "ring" else inner_ring, color), 1))
        painter.drawEllipse(center, radius * .82, radius * .82)
    painter.setFont(_piece_font(radius, "image_fallback", style))
    painter.setPen(_color(spec["text"], color))  # type: ignore[arg-type]
    painter.drawText(int(center.x()-radius), int(center.y()-radius), int(radius*2), int(radius*2),
                     Qt.AlignmentFlag.AlignCenter, theme.NAMES[color][piece_type])


class BoardWidget(QWidget):
    move_requested = Signal(object)
    piece_selected = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.game: Game | None = None
        self.human_color = Color.RED
        self.control_both = False
        self.selected: Position | None = None
        self.legal: list[Move] = []
        self.capturable: set[Position] = set()
        self.drag_origin: Position | None = None
        self.locked = False
        self.interactive = True
        self.theme = theme.THEMES["classic"]
        self.theme_name = "classic"
        self.background = QPixmap()
        self.piece_style = "traditional"
        # `piece_render`：`glyph` = 1.7.0 的字形棋子（默认，逐像素不变）；
        # `image` = 三风格美术图，缺图（甲/刺/楯）按同风格配色回退字形。
        self.piece_render = GLYPH_MODE
        self.show_selection = True
        self.show_legal_targets = True
        self.show_capture_hints = True
        self.animations_enabled = True
        self.language = "zh-CN"
        self.flipped = False
        self.animation_target: Position | None = None
        self.animation_source: Position | None = None
        self.animation_capture = False
        self.animation_frame = 0
        self.check_pulse_frame = 0
        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(ANIMATION_TIMER_MS)
        self.animation_timer.timeout.connect(self._advance_animation)
        self.setMinimumSize(420, 420)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_game(self, game: Game, human_color: Color, control_both: bool = False) -> None:
        self.game, self.human_color = game, human_color
        self.control_both = control_both
        self.selected, self.legal, self.capturable = None, [], set()
        self.update()

    def set_flipped(self, flipped: bool) -> None:
        self.flipped = flipped
        self.selected, self.legal, self.capturable = None, [], set()
        self.update()

    def _view_position(self, position: Position) -> Position:
        if not self.flipped or not self.game:
            return position
        # 阶段1 S1-2：翻转换算抽到 desktop/ui/board_geometry.py（纯函数）
        return view_position(position.row, position.col,
                             self.game.profile.rows, self.game.profile.cols, True)

    def set_appearance(self, theme_name: str, background_name: str,
                       piece_style: str = "traditional",
                       piece_render: str = GLYPH_MODE) -> None:
        self.theme_name = theme_name if theme_name in theme.THEMES else "classic"
        self.theme = theme.THEMES[self.theme_name]
        self.piece_style = piece_assets.normalize_style(piece_style)
        self.piece_render = piece_render if piece_render in PIECE_RENDER_MODES else GLYPH_MODE
        # 棋子美术的**唯一**预热点：换风格/换外观时才解码图片。
        # paintEvent 里同步解码会让首帧卡顿，并在动画期间反复触发磁盘 IO。
        # 缓存命中后这里只是遍历 22 个键，代价可以忽略。
        piece_assets.preload(self.piece_style)
        if background_name == "none":
            self.background = QPixmap()
        else:
            # 阶段1 S1-2：路径改用 theme.resource()。
            # 原写法 Path(__file__).parent/"resources" 在 app.py 里是对的（desktop/），
            # 搬到这里后 __file__ 是 desktop/ui/ → 会指向不存在的 ui/resources，
            # 背景图会**静默加载失败**。theme.resource() 内部按 desktop/ 解析。
            path = theme.resource("backgrounds", f"{background_name}.jpg")
            self.background = QPixmap(str(path))
        self.update()

    def set_assists(self, *, selection: bool, legal_targets: bool,
                    capture_hints: bool, animations: bool) -> None:
        self.show_selection = selection
        self.show_legal_targets = legal_targets
        self.show_capture_hints = capture_hints
        self.animations_enabled = animations
        self.update()

    def animate_move(self, target: Position, capture: bool, source: Position | None = None) -> None:
        if not self.animations_enabled:
            return
        self.animation_source, self.animation_target = source, target
        self.animation_capture, self.animation_frame = capture, 0
        self.animation_timer.start()

    def pulse_check(self) -> None:
        self.check_pulse_frame = 0
        self.animation_timer.start()

    def _advance_animation(self) -> None:
        self.animation_frame += 1
        if self.animation_frame >= ANIMATION_FRAMES:
            self.animation_target = None
            self.animation_source = None
        self.check_pulse_frame += 1
        if self.check_pulse_frame >= CHECK_PULSE_FRAMES and self.animation_target is None:
            self.animation_timer.stop()
        self.update()

    def _controlled(self, piece: Piece | None) -> bool:
        return bool(piece and not self.game.state.paused and piece.color is self.game.state.turn and
                    (self.control_both or piece.color is self.human_color))

    def paintEvent(self, event: QPaintEvent) -> None:
        if not self.game:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect, left, top, cw, ch = self._geometry()
        painter.fillRect(rect, QColor(self.theme["board"]))
        if not self.background.isNull():
            painter.save(); painter.setOpacity(.12)
            painter.drawPixmap(rect, self.background, self.background.rect())
            painter.restore()
        painter.setPen(QPen(QColor(self.theme["frame"]), 5))
        painter.drawRect(rect)
        rows, cols = self.game.profile.rows, self.game.profile.cols
        painter.setPen(QPen(QColor(self.theme["line"]), 1.15))
        if rows == 13:
            self._draw_xionghan_grid(painter, left, top, cw, ch)
        else:
            self._draw_traditional_grid(painter, left, top, cw, ch)
        self._draw_palaces(painter, left, top, cw, ch, rows)
        if rows == 13:
            self._draw_initial_position_marks(painter, left, top, cw, ch)
            self._draw_star_points(painter, left, top, cw, ch)
        self._draw_marks(painter, left, top, cw, ch)
        for piece in self.game.state.pieces:
            self._draw_piece(painter, piece, left, top, cw, ch)
        self._draw_check_label(painter, left, top, cw, ch)
        # 「思索中」遮罩必须画在**棋子之后、走子动画之前**：
        # `human_move` 落子后立刻 `start_ai()`，于是玩家自己这一手的 350ms 动画
        # 全程处在 `locked=True` 状态。若遮罩压在动画上，玩家看到的是"我落子没反馈、
        # AI 落子有反馈"——观感差异全来自绘制顺序，与动画本身无关。
        # 遮罩的颜色/文案/透明度一个字都没改，只调顺序。
        if self.locked:
            painter.fillRect(rect, QColor(30, 25, 20, 90))
            painter.setPen(QColor("white")); painter.setFont(QFont(theme.UI_FONT, 18, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, t("status.thinking_desktop", self.language))
        self._draw_capture_hints(painter, left, top, cw, ch)
        self._draw_animation(painter, left, top, cw, ch)
        if self.game.state.paused:
            painter.fillRect(rect, QColor(30, 25, 20, 150))
            painter.setPen(QColor("white")); painter.setFont(QFont(theme.UI_FONT, 19, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{t('status.paused', self.language)}\n{t('status.timer_stopped', self.language)}")

    def _geometry(self) -> tuple[float, float, float, float]:
        bounds = self.rect().adjusted(13, 13, -13, -13)
        rows = self.game.profile.rows if self.game else 13
        cols = self.game.profile.cols if self.game else 13
        # 阶段1 S1-2：布局数学抽到 desktop/ui/board_geometry.py（纯函数，可单测）。
        # 注意 cell_layout 返回的是「可用区域局部坐标」，而绘制/命中测试要的是窗口
        # 绝对像素，故这里仍用 rect.left()+pad 还原（与原实现逐字节等价）。
        ix, iy, _gl, _gt, cw, ch, pad = cell_layout(bounds.width(), bounds.height(), rows, cols)
        rect = bounds.adjusted(ix, iy, -ix, -iy)
        return rect, rect.left() + pad, rect.top() + pad, cw, ch

    def _draw_xionghan_grid(self, painter: QPainter, left: float, top: float, cw: float, ch: float) -> None:
        right, bottom = left + 12 * cw, top + 12 * ch
        for row in range(13):
            if row != 6:
                painter.drawLine(QPointF(left, top + row * ch), QPointF(right, top + row * ch))
        for col in range(13):
            x = left + col * cw
            painter.drawLine(QPointF(x, top), QPointF(x, top + 5 * ch))
            painter.drawLine(QPointF(x, top + 7 * ch), QPointF(x, bottom))

        separator_y = top + 6 * ch
        marker = min(cw, ch) * .16
        for col in range(13):
            x = left + col * cw
            painter.drawLine(QPointF(x - marker, separator_y), QPointF(x + marker, separator_y))
            if 0 < col < 12:
                painter.drawLine(QPointF(x, separator_y - marker), QPointF(x, separator_y + marker))

        painter.setFont(QFont(theme.PIECE_FONT, max(17, int(cw * .38))))
        painter.drawText(int(left), int(separator_y - ch * .5), int(cw * 6), int(ch),
                         Qt.AlignmentFlag.AlignCenter, t("board.great_wall", self.language))
        painter.drawText(int(left + cw * 6), int(separator_y - ch * .5), int(cw * 6), int(ch),
                         Qt.AlignmentFlag.AlignCenter, t("board.yin_mountains", self.language))

    def _draw_traditional_grid(self, painter: QPainter, left: float, top: float, cw: float, ch: float) -> None:
        right, bottom = left + 8 * cw, top + 9 * ch
        for row in range(10):
            painter.drawLine(QPointF(left, top + row * ch), QPointF(right, top + row * ch))
        for col in range(9):
            x = left + col * cw
            if col in (0, 8):
                painter.drawLine(QPointF(x, top), QPointF(x, bottom))
            else:
                painter.drawLine(QPointF(x, top), QPointF(x, top + 4 * ch))
                painter.drawLine(QPointF(x, top + 5 * ch), QPointF(x, bottom))

        river_y = top + 4.5 * ch
        painter.setFont(QFont(theme.PIECE_FONT, max(16, int(cw * .38))))
        painter.drawText(int(left), int(river_y - ch * .5), int(cw * 4), int(ch),
                         Qt.AlignmentFlag.AlignCenter, t("board.chu_river", self.language))
        painter.drawText(int(left + cw * 4), int(river_y - ch * .5), int(cw * 4), int(ch),
                         Qt.AlignmentFlag.AlignCenter, t("board.han_boundary", self.language))

    def _draw_initial_position_marks(self, painter: QPainter, left: float, top: float, cw: float, ch: float) -> None:
        positions = [(row, col) for row in (4, 8) for col in range(0, 13, 2)]
        positions += [(3, 1), (3, 11), (9, 1), (9, 11)]
        offset, length = min(cw, ch) * .14, min(cw, ch) * .2
        painter.save()
        painter.setPen(QPen(QColor(self.theme["line"]), 1.25))
        for row, col in positions:
            x, y = left + col * cw, top + row * ch
            for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                corner_x, corner_y = x + sx * offset, y + sy * offset
                painter.drawLine(QPointF(corner_x, corner_y), QPointF(corner_x + sx * length, corner_y))
                painter.drawLine(QPointF(corner_x, corner_y), QPointF(corner_x, corner_y + sy * length))
        painter.restore()

    def _draw_star_points(self, painter: QPainter, left: float, top: float, cw: float, ch: float) -> None:
        """Draw only endpoints that belong to the reachable weak-archer lattice."""
        inner = min(cw, ch) * .07
        outer = min(cw, ch) * .18
        painter.save()
        color = QColor(self.theme["line"]); color.setAlpha(175)
        painter.setPen(QPen(color, 1.25))
        for point in sorted(self.game.rules.archer_star_points,
                            key=lambda item: (item.row, item.col)):
            center = QPointF(left + point.col * cw, top + point.row * ch)
            for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                painter.drawLine(
                    QPointF(center.x() + sx * inner, center.y() + sy * inner),
                    QPointF(center.x() + sx * outer, center.y() + sy * outer),
                )
        painter.restore()

    def _draw_palaces(self, painter: QPainter, left: float, top: float, cw: float, ch: float, rows: int) -> None:
        starts = ((0, 3), (7, 3)) if rows == 10 else ((1, 5), (9, 5))
        for row, col in starts:
            painter.drawLine(QPointF(left + col*cw, top + row*ch), QPointF(left + (col+2)*cw, top + (row+2)*ch))
            painter.drawLine(QPointF(left + (col+2)*cw, top + row*ch), QPointF(left + col*cw, top + (row+2)*ch))

    def _draw_marks(self, painter: QPainter, left: float, top: float, cw: float, ch: float) -> None:
        if not self.game:
            return
        if self.game.rules.in_check(self.game.state, self.game.state.turn):
            king = next((p for p in self.game.state.pieces if p.type is PieceType.KING and p.color is self.game.state.turn), None)
            if king:
                pulse = 70 + int(70 * (1 - min(1, self.check_pulse_frame / CHECK_PULSE_FRAMES)))
                self._mark(painter, king.position, left, top, cw, ch, QColor(190, 28, 28, pulse), .47)
        if self.selected and self.show_selection:
            self._mark(painter, self.selected, left, top, cw, ch, QColor(221, 166, 40, 145), .48)
        # 空位落点：统一半径 .13、按主题取色（深色主题必须提亮，见 legal_dot_color）。
        # **每个可走格都画**，不合并中间点——点同时承担"这格能点"的暗示，
        # 合并等于宣称"中间不能停"，与事实冲突。
        dot_color = self.legal_dot_color()
        for move in self.legal if self.show_legal_targets else ():
            target = self.game.state.piece_at(move.target)
            if target:
                self._mark(painter, move.target, left, top, cw, ch, QColor(148, 30, 30, 90), .4)
            else:
                self._mark(painter, move.target, left, top, cw, ch, dot_color, LEGAL_DOT_RATIO)

    def legal_dot_color(self) -> QColor:
        """可走点的颜色：浅色主题 = 该主题 accent @.55；深色 = #9fbfa8 @.60。

        判据是"与棋盘底色的绿通道差不低于 40"，否则 13×13 上根本看不见。
        深色主题的旧做法（深绿 `#315c48` @.72 混在 `#34302b` 上）绿差只有 +32，
        本来就不达标；换浅灰绿后约 +60。
        """
        if self.theme_name == "dark":
            color = QColor(*LEGAL_DOT_DARK_RGB)
            color.setAlphaF(LEGAL_DOT_ALPHA_DARK)
            return color
        color = QColor(self.theme["accent"])
        color.setAlphaF(LEGAL_DOT_ALPHA_LIGHT)
        return color

    def _draw_check_label(self, painter: QPainter, left: float, top: float, cw: float, ch: float) -> None:
        """「将军」二字单独一层，画在**棋子之后**。

        原来它和红晕一起画在棋子层之下，被相邻棋子盖住就看不清（尤其九宫附近子力密集）。
        红晕/环仍留在下层（那是"哪枚子被将"的空间指示，不该盖住棋子）。
        """
        if not self.game or not self.game.rules.in_check(self.game.state, self.game.state.turn):
            return
        king = next((p for p in self.game.state.pieces
                     if p.type is PieceType.KING and p.color is self.game.state.turn), None)
        if king is None:
            return
        pulse = 70 + int(70 * (1 - min(1, self.check_pulse_frame / CHECK_PULSE_FRAMES)))
        painter.save()
        painter.setPen(QColor(190, 28, 28, min(255, pulse + 40)))
        painter.setFont(QFont(theme.UI_FONT, max(14, int(min(cw, ch) * .22)), QFont.Weight.Bold))
        shown = self._view_position(king.position)
        painter.drawText(QPointF(left + shown.col * cw,
                                 top + shown.row * ch - min(cw, ch) * .55), t("status.check", self.language))
        painter.restore()

    def _draw_capture_hints(self, painter: QPainter, left: float, top: float, cw: float, ch: float) -> None:
        if not self.show_capture_hints:
            return
        painter.save()
        painter.setPen(QPen(QColor(205, 32, 32, 220), max(2.5, min(cw, ch) * .055)))
        size = min(cw, ch) * .3
        for position in self.capturable:
            shown = self._view_position(position)
            x, y = left + shown.col * cw, top + shown.row * ch
            painter.drawLine(QPointF(x - size, y - size), QPointF(x + size, y + size))
            painter.drawLine(QPointF(x + size, y - size), QPointF(x - size, y + size))
        painter.restore()

    def _draw_animation(self, painter: QPainter, left: float, top: float, cw: float, ch: float) -> None:
        if self.animation_target is None:
            return
        progress = min(1.0, self.animation_frame / ANIMATION_FRAMES)
        if self.animation_source is not None:
            source = self._view_position(self.animation_source)
            target = self._view_position(self.animation_target)
            sx, sy = left + source.col * cw, top + source.row * ch
            tx, ty = left + target.col * cw, top + target.row * ch
            angle = math.atan2(ty - sy, tx - sx)
            head = min(cw, ch) * .18
            painter.save(); painter.setOpacity(max(0.0, 1.0 - progress))
            color = QColor("#9d2525" if self.animation_capture else "#315c48")
            painter.setPen(QPen(color, max(2.0, min(cw, ch) * .06))); painter.setBrush(color)
            painter.drawLine(QPointF(sx, sy), QPointF(tx, ty))
            painter.drawPolygon([QPointF(tx, ty), QPointF(tx - head * math.cos(angle - .55), ty - head * math.sin(angle - .55)), QPointF(tx - head * math.cos(angle + .55), ty - head * math.sin(angle + .55))])
            painter.restore()
        radius = min(cw, ch) * (.25 + progress * .38)
        color = QColor("#9d2525" if self.animation_capture else "#315c48")
        color.setAlphaF(max(0.0, 1.0 - progress))
        painter.save(); painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(color, max(1.0, 5.0 * (1.0 - progress))))
        shown = self._view_position(self.animation_target)
        painter.drawEllipse(QPointF(left + shown.col * cw,
                                    top + shown.row * ch), radius, radius)
        painter.restore()

    def _select(self, position: Position) -> None:
        self.selected = position
        self.legal = [move for move in self.game.rules.legal_moves(self.game.state)
                      if move.source == position]
        self.capturable = {
            captured.position
            for move in self.legal
            for captured in self.game.rules.captured_by_move(self.game.state, move)
        }

    def _mark(self, painter: QPainter, pos: Position, left: float, top: float, cw: float, ch: float, color: str, ratio: float) -> None:
        pos = self._view_position(pos)
        radius = min(cw, ch) * ratio
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(color)
        painter.drawEllipse(QPointF(left + pos.col*cw, top + pos.row*ch), radius, radius)

    def _draw_piece(self, painter: QPainter, piece: Piece, left: float, top: float, cw: float, ch: float) -> None:
        # 盘径是**不变量**：字形模式与图片模式共用这一个 radius（= 0.78 格），
        # 所以切风格时棋子不会「变大/变小」。图片的留白在载入时已按常量裁掉。
        radius = min(cw, ch) * .39
        shown = self._view_position(piece.position)
        center = QPointF(left + shown.col*cw, top + shown.row*ch)
        if self.piece_render == IMAGE_MODE:
            if self._draw_piece_image(painter, piece, center, radius):
                return
            # 甲/刺/楯 三型没有美术：同风格底盘 + 统一字形，不留白、不报错。
            draw_fallback_piece(painter, center, radius, piece.color, piece.type, self.piece_style)
            return
        draw_piece_glyph(painter, center, radius, piece, self.piece_style)

    def _draw_piece_image(self, painter: QPainter, piece: Piece, center: QPointF,
                          radius: float) -> bool:
        """把棋子画成美术图；没有可用美术时返回 False，由调用方走回退分支。

        图片已在载入时裁到盘径、并预缩放到 `dev = round(0.78 * cell * dpr)`，
        这里只用目标矩形贴一次（不再做绘制期缩放，那会丢掉预缩放的收益）。
        `pixmap()` 返回的图已 `setDevicePixelRatio()`，所以**不要**再
        `painter.scale(dpr, dpr)`：那会把缩放叠乘一次，棋子整整放大一倍。
        """
        artwork = piece_assets.pixmap(self.piece_style, piece.color, piece.type,
                                      round(radius * 2 * self.devicePixelRatioF()))
        if artwork is None:
            return False
        painter.drawPixmap(
            QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2),
            artwork, QRectF(artwork.rect()))
        return True

    def _position(self, point: QPointF) -> Position | None:
        if not self.game:
            return None
        _, left, top, cw, ch = self._geometry()
        # 阶段1 S1-2：像素→棋盘坐标抽到 desktop/ui/board_geometry.py（纯函数，可单测）
        return point_to_position(point.x(), point.y(), left, top, cw, ch,
                                 self.game.profile.rows, self.game.profile.cols, self.flipped)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() is Qt.MouseButton.LeftButton and not self.locked and self.interactive and self.game:
            self.drag_origin = self._position(event.position())
            piece = self.game.state.piece_at(self.drag_origin) if self.drag_origin else None
            if self._controlled(piece):
                self._select(self.drag_origin)
                self.piece_selected.emit()
                self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if (self.locked or not self.interactive or not self.game or self.game.state.finished
                or self.game.state.paused):
            return
        position = self._position(event.position())
        if not position:
            return
        if position == self.selected and position == self.drag_origin:
            self.update()
            return
        if self.selected and any(m.target == position for m in self.legal):
            move = next(m for m in self.legal if m.target == position)
            self.selected, self.legal, self.capturable = None, [], set()
            self.move_requested.emit(move); self.update(); return
        piece = self.game.state.piece_at(position)
        if self._controlled(piece):
            self._select(position)
            self.piece_selected.emit()
        else:
            self.selected, self.legal, self.capturable = None, [], set()
        self.update()


