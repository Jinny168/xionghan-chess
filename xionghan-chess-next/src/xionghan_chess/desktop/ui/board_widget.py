"""棋盘控件（阶段1 S1-2 从 app.py 抽出，362 行）。

职责很窄：**只做渲染与鼠标输入**。规则、合法着法、判和全在 `core/`；
坐标换算委托给 `ui/board_geometry.py`（纯函数，可单测）。

抽出的动机：`app.py` 原本 1200+ 行单体，UI/交互/网络/渲染全混在一起，无法单测也无法
分人维护（见 docs/AUDIT_DESKTOP_1.7.0.md 轴 4）。
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QWidget

from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color, Move, PieceType, Position
from xionghan_chess.i18n import t

from . import theme
from .board_geometry import cell_layout, point_to_position, view_position


class BoardWidget(QWidget):
    move_requested = Signal(object)
    piece_selected = Signal()

    def __init__(self, parent: QWidget | None = None):
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
        self.background = QPixmap()
        self.piece_style = "traditional"
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
        self.animation_timer.setInterval(25)
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
                       piece_style: str = "traditional") -> None:
        self.theme = theme.THEMES.get(theme_name, theme.THEMES["classic"])
        self.piece_style = piece_style
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
        if self.animation_frame >= 14:
            self.animation_target = None
            self.animation_source = None
        self.check_pulse_frame += 1
        if self.check_pulse_frame >= 24 and self.animation_target is None:
            self.animation_timer.stop()
        self.update()

    def _controlled(self, piece) -> bool:
        return bool(piece and not self.game.state.paused and piece.color is self.game.state.turn and
                    (self.control_both or piece.color is self.human_color))

    def paintEvent(self, event) -> None:
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
        self._draw_capture_hints(painter, left, top, cw, ch)
        self._draw_animation(painter, left, top, cw, ch)
        if self.game.state.paused:
            painter.fillRect(rect, QColor(30, 25, 20, 150))
            painter.setPen(QColor("white")); painter.setFont(QFont(theme.UI_FONT, 19, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{t('status.paused', self.language)}\n{t('status.timer_stopped', self.language)}")
        if self.locked:
            painter.fillRect(rect, QColor(30, 25, 20, 90))
            painter.setPen(QColor("white")); painter.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, t("status.thinking_desktop", self.language))

    def _geometry(self):
        bounds = self.rect().adjusted(13, 13, -13, -13)
        rows = self.game.profile.rows if self.game else 13
        cols = self.game.profile.cols if self.game else 13
        # 阶段1 S1-2：布局数学抽到 desktop/ui/board_geometry.py（纯函数，可单测）。
        # 注意 cell_layout 返回的是「可用区域局部坐标」，而绘制/命中测试要的是窗口
        # 绝对像素，故这里仍用 rect.left()+pad 还原（与原实现逐字节等价）。
        ix, iy, _gl, _gt, cw, ch, pad = cell_layout(bounds.width(), bounds.height(), rows, cols)
        rect = bounds.adjusted(ix, iy, -ix, -iy)
        return rect, rect.left() + pad, rect.top() + pad, cw, ch

    def _draw_xionghan_grid(self, painter, left, top, cw, ch):
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

    def _draw_traditional_grid(self, painter, left, top, cw, ch):
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

    def _draw_initial_position_marks(self, painter, left, top, cw, ch):
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

    def _draw_star_points(self, painter, left, top, cw, ch):
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

    def _draw_palaces(self, painter, left, top, cw, ch, rows):
        starts = ((0, 3), (7, 3)) if rows == 10 else ((1, 5), (9, 5))
        for row, col in starts:
            painter.drawLine(QPointF(left + col*cw, top + row*ch), QPointF(left + (col+2)*cw, top + (row+2)*ch))
            painter.drawLine(QPointF(left + (col+2)*cw, top + row*ch), QPointF(left + col*cw, top + (row+2)*ch))

    def _draw_marks(self, painter, left, top, cw, ch):
        if not self.game:
            return
        if self.game.rules.in_check(self.game.state, self.game.state.turn):
            king = next((p for p in self.game.state.pieces if p.type is PieceType.KING and p.color is self.game.state.turn), None)
            if king:
                pulse = 70 + int(70 * (1 - min(1, self.check_pulse_frame / 24)))
                self._mark(painter, king.position, left, top, cw, ch, QColor(190, 28, 28, pulse), .47)
                painter.save(); painter.setPen(QColor(190, 28, 28, min(255, pulse + 40)))
                painter.setFont(QFont(theme.UI_FONT, max(14, int(min(cw, ch) * .22)), QFont.Weight.Bold))
                shown = self._view_position(king.position)
                painter.drawText(QPointF(left + shown.col * cw, top + shown.row * ch - min(cw, ch) * .55), t("status.check", self.language))
                painter.restore()
        if self.selected and self.show_selection:
            self._mark(painter, self.selected, left, top, cw, ch, QColor(221, 166, 40, 145), .48)
        for move in self.legal if self.show_legal_targets else ():
            target = self.game.state.piece_at(move.target)
            self._mark(painter, move.target, left, top, cw, ch, QColor(148, 30, 30, 90) if target else QColor(43, 104, 72, 180), .4 if target else .1)

    def _draw_capture_hints(self, painter, left, top, cw, ch):
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

    def _draw_animation(self, painter, left, top, cw, ch):
        if self.animation_target is None:
            return
        progress = min(1.0, self.animation_frame / 14)
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

    def _mark(self, painter, pos, left, top, cw, ch, color, ratio):
        pos = self._view_position(pos)
        radius = min(cw, ch) * ratio
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(color)
        painter.drawEllipse(QPointF(left + pos.col*cw, top + pos.row*ch), radius, radius)

    def _draw_piece(self, painter, piece, left, top, cw, ch):
        radius = min(cw, ch) * .39
        shown = self._view_position(piece.position)
        center = QPointF(left + shown.col*cw, top + shown.row*ch)
        if self.piece_style == "modern":
            brush = QBrush(QColor("#f9e7bb"))
        elif self.piece_style == "cartoon":
            brush = QBrush(QColor("#ffd98e"))
        else:
            gradient = QRadialGradient(center.x()-radius*.25, center.y()-radius*.3, radius*1.2)
            gradient.setColorAt(0, QColor("#fff0c5")); gradient.setColorAt(1, QColor("#d4a763"))
            brush = QBrush(gradient)
        outline = QColor("#9a2424") if piece.color is Color.RED else QColor("#24211e")
        painter.setBrush(brush); painter.setPen(QPen(outline, max(2, radius*(.13 if self.piece_style == "cartoon" else .1))))
        painter.drawEllipse(center, radius, radius)
        if self.piece_style == "modern":
            painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(QPen(outline, 1))
            painter.drawEllipse(center, radius * .82, radius * .82)
        painter.setFont(QFont(theme.PIECE_FONT, max(13, int(radius*1.15)), QFont.Weight.Bold))
        painter.setPen(QColor("#9a2424") if piece.color is Color.RED else QColor("#24211e"))
        painter.drawText(int(center.x()-radius), int(center.y()-radius), int(radius*2), int(radius*2), Qt.AlignmentFlag.AlignCenter, theme.NAMES[piece.color][piece.type])

    def _position(self, point) -> Position | None:
        if not self.game:
            return None
        _, left, top, cw, ch = self._geometry()
        # 阶段1 S1-2：像素→棋盘坐标抽到 desktop/ui/board_geometry.py（纯函数，可单测）
        return point_to_position(point.x(), point.y(), left, top, cw, ch,
                                 self.game.profile.rows, self.game.profile.cols, self.flipped)

    def mousePressEvent(self, event) -> None:
        if event.button() is Qt.MouseButton.LeftButton and not self.locked and self.interactive and self.game:
            self.drag_origin = self._position(event.position())
            piece = self.game.state.piece_at(self.drag_origin) if self.drag_origin else None
            if self._controlled(piece):
                self._select(self.drag_origin)
                self.piece_selected.emit()
                self.update()

    def mouseReleaseEvent(self, event) -> None:
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


