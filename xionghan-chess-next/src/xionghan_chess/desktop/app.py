from __future__ import annotations

from dataclasses import asdict
import os
import sys
import threading
import json
import urllib.request
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, QRunnable, Qt, QThreadPool, QTimer, Signal, QUrl
from PySide6.QtGui import QAction, QColor, QFont, QFontDatabase, QIcon, QPainter, QPen, QBrush, QRadialGradient, QPixmap, QKeySequence
from PySide6.QtWebSockets import QWebSocket
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QSpinBox, QSplitter, QVBoxLayout, QWidget, QGroupBox,
    QInputDialog, QLineEdit, QFileDialog, QTextBrowser, QSlider, QTabWidget, QListWidgetItem,
)

from xionghan_chess.core.ai import ChessAI, Difficulty
from xionghan_chess.core.game import Game, GameError
from xionghan_chess.core.model import Color, GameState, Move, PieceType, Position
from xionghan_chess.core.profiles import PROFILES, profile_rule_values
from .audio import DesktopAudio
from .config import config_path, load_config, save_config
from .storage import autosave_game, load_game, load_statistics, record_result, reset_statistics, save_game


NAMES = {
    Color.RED: {PieceType.KING:"漢",PieceType.ROOK:"俥",PieceType.HORSE:"傌",PieceType.ELEPHANT:"相",PieceType.ADVISOR:"仕",PieceType.CANNON:"炮",PieceType.PAWN:"兵",PieceType.GUARD:"尉",PieceType.ARCHER:"射",PieceType.THUNDER:"檑",PieceType.ARMOR:"甲",PieceType.ASSASSIN:"刺",PieceType.SHIELD:"楯",PieceType.PATROL:"巡"},
    Color.BLACK: {PieceType.KING:"汗",PieceType.ROOK:"車",PieceType.HORSE:"馬",PieceType.ELEPHANT:"象",PieceType.ADVISOR:"士",PieceType.CANNON:"砲",PieceType.PAWN:"卒",PieceType.GUARD:"衛",PieceType.ARCHER:"䠶",PieceType.THUNDER:"礌",PieceType.ARMOR:"胄",PieceType.ASSASSIN:"伺",PieceType.SHIELD:"碷",PieceType.PATROL:"廵"},
}

UI_FONT = "Microsoft YaHei"
PIECE_FONT = "KaiTi"

THEMES = {
    "classic": {"board": "#e7c88d", "line": "#684726", "frame": "#5a3b20", "panel": "#fff9ed", "window": "#d9c8a6", "accent": "#315c48"},
    "green": {"board": "#dfeeda", "line": "#315c36", "frame": "#365a3e", "panel": "#f6fbf2", "window": "#c8d8c1", "accent": "#315c48"},
    "blue": {"board": "#dcebf1", "line": "#285c73", "frame": "#31586a", "panel": "#f3f8fa", "window": "#c4d4da", "accent": "#315f76"},
    "purple": {"board": "#eee1f2", "line": "#724585", "frame": "#5c386d", "panel": "#fbf6fc", "window": "#d8c7dc", "accent": "#6d3e79"},
    "dark": {"board": "#34302b", "line": "#c9b58e", "frame": "#171513", "panel": "#29241f", "window": "#1d1a17", "accent": "#8e3b32"},
}

FONT_CHOICES = {"system": UI_FONT, "kaiti": PIECE_FONT, "songti": "SimSun", "fangsong": "FangSong"}


def load_bundled_fonts() -> None:
    global UI_FONT, PIECE_FONT
    font_dir = Path(__file__).resolve().parent / "resources" / "fonts"
    loaded: dict[str, str] = {}
    for filename, key in (("msyh.ttc", "ui"), ("simkai.ttf", "piece")):
        font_id = QFontDatabase.addApplicationFont(str(font_dir / filename))
        families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
        if families:
            loaded[key] = families[0]
    UI_FONT = loaded.get("ui", UI_FONT)
    PIECE_FONT = loaded.get("piece", PIECE_FONT)
    FONT_CHOICES["system"] = UI_FONT
    FONT_CHOICES["kaiti"] = PIECE_FONT
    QApplication.instance().setFont(QFont(UI_FONT, 10))


class WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(object)


class AIWorker(QRunnable):
    def __init__(self, game: Game, difficulty: str, cancel: threading.Event):
        super().__init__()
        self.game = Game.from_state(game.state.clone(), game.options)
        self.ai = ChessAI(difficulty)
        self.cancel = cancel
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            self.signals.finished.emit((self.ai.choose_move(self.game, self.cancel), self.cancel))
        except Exception as exc:
            self.signals.failed.emit((str(exc), self.cancel))


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
        self.theme = THEMES["classic"]
        self.background = QPixmap()
        self.piece_style = "traditional"
        self.show_selection = True
        self.show_legal_targets = True
        self.show_capture_hints = True
        self.animations_enabled = True
        self.animation_target: Position | None = None
        self.animation_capture = False
        self.animation_frame = 0
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

    def set_appearance(self, theme_name: str, background_name: str,
                       piece_style: str = "traditional") -> None:
        self.theme = THEMES.get(theme_name, THEMES["classic"])
        self.piece_style = piece_style
        if background_name == "none":
            self.background = QPixmap()
        else:
            path = Path(__file__).resolve().parent / "resources" / "backgrounds" / f"{background_name}.jpg"
            self.background = QPixmap(str(path))
        self.update()

    def set_assists(self, *, selection: bool, legal_targets: bool,
                    capture_hints: bool, animations: bool) -> None:
        self.show_selection = selection
        self.show_legal_targets = legal_targets
        self.show_capture_hints = capture_hints
        self.animations_enabled = animations
        self.update()

    def animate_move(self, target: Position, capture: bool) -> None:
        if not self.animations_enabled:
            return
        self.animation_target, self.animation_capture, self.animation_frame = target, capture, 0
        self.animation_timer.start()

    def _advance_animation(self) -> None:
        self.animation_frame += 1
        if self.animation_frame >= 14:
            self.animation_timer.stop()
            self.animation_target = None
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
            painter.setPen(QColor("white")); painter.setFont(QFont(UI_FONT, 19, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "对局已暂停\n计时已停止")
        if self.locked:
            painter.fillRect(rect, QColor(30, 25, 20, 90))
            painter.setPen(QColor("white")); painter.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "棋灵思考中...")

    def _geometry(self):
        bounds = self.rect().adjusted(13, 13, -13, -13)
        rows = self.game.profile.rows if self.game else 13
        cols = self.game.profile.cols if self.game else 13
        cell = min(bounds.width() / max(1, cols - 1 + 1.35), bounds.height() / max(1, rows - 1 + 1.35))
        pad = cell * .675
        width = cell * (cols - 1) + pad * 2
        height = cell * (rows - 1) + pad * 2
        rect = bounds.adjusted((bounds.width()-width)/2, (bounds.height()-height)/2,
                               -(bounds.width()-width)/2, -(bounds.height()-height)/2)
        return rect, rect.left()+pad, rect.top()+pad, cell, cell

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

        painter.setFont(QFont(PIECE_FONT, max(17, int(cw * .38))))
        painter.drawText(int(left), int(separator_y - ch * .5), int(cw * 6), int(ch),
                         Qt.AlignmentFlag.AlignCenter, "长 城")
        painter.drawText(int(left + cw * 6), int(separator_y - ch * .5), int(cw * 6), int(ch),
                         Qt.AlignmentFlag.AlignCenter, "阴 山")

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
        painter.setFont(QFont(PIECE_FONT, max(16, int(cw * .38))))
        painter.drawText(int(left), int(river_y - ch * .5), int(cw * 4), int(ch),
                         Qt.AlignmentFlag.AlignCenter, "楚  河")
        painter.drawText(int(left + cw * 4), int(river_y - ch * .5), int(cw * 4), int(ch),
                         Qt.AlignmentFlag.AlignCenter, "汉  界")

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
                self._mark(painter, king.position, left, top, cw, ch, QColor(190, 28, 28, 100), .47)
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
            x, y = left + position.col * cw, top + position.row * ch
            painter.drawLine(QPointF(x - size, y - size), QPointF(x + size, y + size))
            painter.drawLine(QPointF(x + size, y - size), QPointF(x - size, y + size))
        painter.restore()

    def _draw_animation(self, painter, left, top, cw, ch):
        if self.animation_target is None:
            return
        progress = min(1.0, self.animation_frame / 14)
        radius = min(cw, ch) * (.25 + progress * .38)
        color = QColor("#9d2525" if self.animation_capture else "#315c48")
        color.setAlphaF(max(0.0, 1.0 - progress))
        painter.save(); painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(color, max(1.0, 5.0 * (1.0 - progress))))
        painter.drawEllipse(QPointF(left + self.animation_target.col * cw,
                                    top + self.animation_target.row * ch), radius, radius)
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

    @staticmethod
    def _mark(painter, pos, left, top, cw, ch, color, ratio):
        radius = min(cw, ch) * ratio
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(color)
        painter.drawEllipse(QPointF(left + pos.col*cw, top + pos.row*ch), radius, radius)

    def _draw_piece(self, painter, piece, left, top, cw, ch):
        radius = min(cw, ch) * .39
        center = QPointF(left + piece.position.col*cw, top + piece.position.row*ch)
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
        painter.setFont(QFont(PIECE_FONT, max(13, int(radius*1.15)), QFont.Weight.Bold))
        painter.setPen(QColor("#9a2424") if piece.color is Color.RED else QColor("#24211e"))
        painter.drawText(int(center.x()-radius), int(center.y()-radius), int(radius*2), int(radius*2), Qt.AlignmentFlag.AlignCenter, NAMES[piece.color][piece.type])

    def _position(self, point) -> Position | None:
        if not self.game:
            return None
        _,left,top,cw,ch=self._geometry()
        col=round((point.x()-left)/cw);row=round((point.y()-top)/ch)
        return Position(row,col) if 0<=row<self.game.profile.rows and 0<=col<self.game.profile.cols else None

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


class SettingsDialog(QDialog):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent); self.setWindowTitle("设置"); self.resize(720, 760)
        layout=QVBoxLayout(self); tabs=QTabWidget(); layout.addWidget(tabs,1)
        self.profile=QComboBox(); [self.profile.addItem(p.title,p.id) for p in PROFILES.values()]
        self.profile.setCurrentIndex(max(0,self.profile.findData(config["profile"])))
        self.game_mode=QComboBox();self.game_mode.addItem("人机对战","ai");self.game_mode.addItem("双人同机对弈","local");self.game_mode.setCurrentIndex(max(0,self.game_mode.findData(config.get("game_mode","ai"))))
        self.difficulty=QComboBox();[(self.difficulty.addItem(text,value)) for value,text in (("beginner","入门"),("easy","初级"),("medium","中级"),("hard","高级"))]
        self.difficulty.setCurrentIndex(max(0,self.difficulty.findData(config["difficulty"])))
        self.color=QComboBox();self.color.addItem("红方先手","red");self.color.addItem("黑方后手","black");self.color.setCurrentIndex(max(0,self.color.findData(config["human_color"])))
        self.minutes=QSpinBox();self.minutes.setRange(1,180);self.minutes.setValue(config["initial_minutes"])
        self.countdown=QComboBox();[(self.countdown.addItem(text,value)) for value,text in ((10,"最后 10 秒"),(30,"最后 30 秒"),(60,"最后 60 秒"),(0,"关闭"))];self.countdown.setCurrentIndex(max(0,self.countdown.findData(config.get("countdown_seconds",30))))
        self.sound=QCheckBox("启用音效");self.sound.setChecked(config["sound"])
        self.music=QCheckBox("启用背景音乐");self.music.setChecked(config.get("music",False))
        self.music_style=QComboBox();self.music_style.addItem("FC 风格","fc");self.music_style.addItem("QQ 风格","qq");self.music_style.setCurrentIndex(max(0,self.music_style.findData(config.get("music_style","fc"))))
        self.sound_volume=QSlider(Qt.Orientation.Horizontal);self.sound_volume.setRange(0,100);self.sound_volume.setValue(config.get("sound_volume",70))
        self.music_volume=QSlider(Qt.Orientation.Horizontal);self.music_volume.setRange(0,100);self.music_volume.setValue(config.get("music_volume",40))
        self.theme=QComboBox();[(self.theme.addItem(text,value)) for value,text in (("classic","经典木纹"),("green","翠绿"),("blue","海洋蓝"),("purple","紫晶"),("dark","暗黑"))];self.theme.setCurrentIndex(max(0,self.theme.findData(config.get("theme","classic"))))
        self.font=QComboBox();[(self.font.addItem(text,value)) for value,text in (("system","微软雅黑"),("kaiti","楷体"),("songti","宋体"),("fangsong","仿宋"))];self.font.setCurrentIndex(max(0,self.font.findData(config.get("font","system"))))
        self.background=QComboBox();self.background.addItem("原色（无背景图片）","none");[(self.background.addItem(f"背景 {index}",str(index))) for index in range(1,6)];self.background.setCurrentIndex(max(0,self.background.findData(str(config.get("background","none")))))
        self.piece_style=QComboBox();[(self.piece_style.addItem(text,value)) for value,text in (("traditional","传统书法"),("modern","现代简约"),("cartoon","卡通风格"))];self.piece_style.setCurrentIndex(max(0,self.piece_style.findData(config.get("piece_style","traditional"))))
        self.animations=QCheckBox("走棋与吃子动画");self.animations.setChecked(config.get("animations",True))
        self.selection_highlight=QCheckBox("选中棋子高亮");self.selection_highlight.setChecked(config.get("selection_highlight",True))
        self.legal_targets=QCheckBox("显示可行落点");self.legal_targets.setChecked(config.get("legal_targets",True))
        self.capture_hints=QCheckBox("提示可吃棋子");self.capture_hints.setChecked(config.get("capture_hints",True))
        self.autosave=QCheckBox("对局结束后自动保存棋谱");self.autosave.setChecked(config.get("autosave",True))

        game_tab=QWidget();game_layout=QVBoxLayout(game_tab);game_form=QFormLayout()
        game_form.addRow("对战方式",self.game_mode);game_form.addRow("规则模式",self.profile);game_form.addRow("AI 难度",self.difficulty)
        game_form.addRow("玩家执子",self.color);game_form.addRow("每方时间（分钟）",self.minutes);game_form.addRow("读秒提醒",self.countdown)
        game_layout.addLayout(game_form);game_layout.addWidget(self.autosave)
        tabs.addTab(game_tab,"对局设置")

        appearance_tab=QWidget();appearance_form=QFormLayout(appearance_tab)
        appearance_form.addRow("棋盘主题",self.theme);appearance_form.addRow("界面字体",self.font)
        appearance_form.addRow("背景图片",self.background);appearance_form.addRow("棋子样式",self.piece_style);appearance_form.addRow("音效",self.sound)
        appearance_form.addRow("音效音量",self.sound_volume);appearance_form.addRow("背景音乐",self.music)
        appearance_form.addRow("音乐风格",self.music_style);appearance_form.addRow("音乐音量",self.music_volume)
        appearance_form.addRow("动画",self.animations);appearance_form.addRow("选中提示",self.selection_highlight)
        appearance_form.addRow("合法落点",self.legal_targets);appearance_form.addRow("吃子提示",self.capture_hints)
        tabs.addTab(appearance_tab,"界面与声音")

        self._active_profile_id = config["profile"]
        self._profile_values = {profile_id: profile_rule_values(profile_id) for profile_id in PROFILES}
        self._profile_values[self._active_profile_id] = profile_rule_values(
            self._active_profile_id, config.get("rule_options", {}))
        self.checks={}; options=PROFILES[self._active_profile_id].options.merged(
            self._profile_values[self._active_profile_id])
        general=QGroupBox("通用裁定");general_layout=QVBoxLayout(general)
        for key,text in (("enforce_self_check","禁止送将"),("threefold_draw","三次重复和棋")):
            check=QCheckBox(text);check.setChecked(bool(getattr(options,key)));self.checks[key]=check;general_layout.addWidget(check)
        game_layout.addWidget(general);game_layout.addStretch()

        piece_definitions={
            PieceType.KING:("汉 / 汗","主帅；正式规则允许出九宫，并可通过进入敌方九宫取胜",(
                ("king_can_leave_palace","允许出九宫"),("king_diagonal_in_palace","九宫内可斜走"),
                ("king_lose_diagonal_outside_palace","出九宫后失去斜走"),("invasion_victory","进入敌方九宫立即获胜"))),
            PieceType.ROOK:("俥 / 車","沿横线或竖线行走，路径不可有棋子",()),
            PieceType.HORSE:("傌 / 馬","日字走法，受蹩马腿限制",(("horse_straight_three","允许直走三格"),)),
            PieceType.ELEPHANT:("相 / 象","斜走两格，受象眼和过界规则限制",(
                ("elephant_can_cross_river","允许越过长城阴山"),("elephant_gain_jump_two_enemy_territory","进入敌境后可横竖两格"))),
            PieceType.ADVISOR:("仕 / 士","基础为九宫内斜走一格",(
                ("advisor_can_leave_palace","允许出九宫"),("advisor_gain_straight_outside_palace","出九宫后可直走"))),
            PieceType.CANNON:("炮 / 砲","直线移动；吃子时必须恰好隔一子",()),
            PieceType.PAWN:("兵 / 卒","向前推进，进入敌境后可横走",(
                ("pawn_fast_move_before_enemy_territory","进入敌境前可快速行军"),("pawn_backward_at_base","到底线可后退"),
                ("pawn_full_movement_at_base","到底线四向移动"),("pawn_resurrection","允许复活"),("pawn_promotion","允许升变"))),
            PieceType.GUARD:("尉 / 卫","沿直线或斜线隔一子跳到空位",()),
            PieceType.ARCHER:("射 / 䠶","弱化时沿有效星轨移动；强化时可脱离星轨斜走",(
                ("archer_enhanced_mode","加强射/䠶（自由斜走三格）"),)),
            PieceType.THUNDER:("檑 / 礌","沿八方向移动，只能近身攻击落单敌子",()),
            PieceType.ARMOR:("甲 / 胄","直线移动并通过三子连线触发夹击",()),
            PieceType.ASSASSIN:("刺 / 伺","直线移至空位并执行反向兑子",()),
            PieceType.SHIELD:("楯 / 碷","隔一子跳；自身不可被吃并保护邻子",()),
            PieceType.PATROL:("巡 / 廵","在指定边界线上按偶数格横移",()),
        }
        content=QWidget();content_layout=QVBoxLayout(content);self.piece_groups={}
        for kind,(title,description,rules) in piece_definitions.items():
            group=QGroupBox(title);group_layout=QVBoxLayout(group);self.piece_groups[kind]=group
            detail=QLabel(description);detail.setWordWrap(True);detail.setStyleSheet("color:#6f6254");group_layout.addWidget(detail)
            appear_key=f"{kind.value}_appear";appear=QCheckBox("本局登场")
            appear.setChecked(bool(getattr(options,appear_key)));self.checks[appear_key]=appear;group_layout.addWidget(appear)
            for key,text in rules:
                check=QCheckBox(text);check.setChecked(bool(getattr(options,key)));self.checks[key]=check;group_layout.addWidget(check)
            content_layout.addWidget(group)
        content_layout.addStretch()
        self.checks["king_appear"].setChecked(True);self.checks["king_appear"].setEnabled(False)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(content);tabs.addTab(scroll,"棋子与规则")
        self.profile.currentIndexChanged.connect(self._profile_changed);self._update_piece_availability()
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);layout.addWidget(buttons)

    def _update_piece_availability(self):
        profile=PROFILES[self.profile.currentData()]
        for kind in PieceType:
            check=self.checks[f"{kind.value}_appear"]
            available=kind in profile.enabled_piece_types
            self.piece_groups[kind].setEnabled(available)
            check.setEnabled(available and kind is not PieceType.KING)
            if not available:check.setChecked(False)
            elif kind is PieceType.KING:check.setChecked(True)

    def _capture_profile_values(self):
        values = {key: check.isChecked() for key, check in self.checks.items()}
        values["king_appear"] = True
        self._profile_values[self._active_profile_id] = values

    def _profile_changed(self):
        self._capture_profile_values()
        self._active_profile_id = self.profile.currentData()
        values = self._profile_values[self._active_profile_id]
        for key, check in self.checks.items():
            check.setChecked(bool(values.get(key, False)))
        self._update_piece_availability()

    def value(self) -> dict:
        self._capture_profile_values()
        values=self._profile_values[self._active_profile_id]
        return {"profile":self.profile.currentData(),"game_mode":self.game_mode.currentData(),"difficulty":self.difficulty.currentData(),"human_color":self.color.currentData(),"initial_minutes":self.minutes.value(),"countdown_seconds":self.countdown.currentData(),"sound":self.sound.isChecked(),"music":self.music.isChecked(),"music_style":self.music_style.currentData(),"sound_volume":self.sound_volume.value(),"music_volume":self.music_volume.value(),"theme":self.theme.currentData(),"font":self.font.currentData(),"background":self.background.currentData(),"piece_style":self.piece_style.currentData(),"animations":self.animations.isChecked(),"selection_highlight":self.selection_highlight.isChecked(),"legal_targets":self.legal_targets.isChecked(),"capture_hints":self.capture_hints.isChecked(),"autosave":self.autosave.isChecked(),"server_url":self.parent().config.get("server_url","http://127.0.0.1:8000") if self.parent() else "http://127.0.0.1:8000","rule_options":values}


class ReplayDialog(QDialog):
    def __init__(self, game: Game, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("棋局复盘")
        self.resize(960, 820)
        self.snapshots = [GameState.from_dict(item) for item in game._snapshots] + [game.state.clone()]
        self.options = asdict(game.options)
        layout = QVBoxLayout(self)
        self.info = QLabel(); self.info.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(self.info)
        split=QSplitter();layout.addWidget(split,1)
        self.board = BoardWidget(); self.board.interactive = False
        self.board.set_appearance(config.get("theme","classic"), str(config.get("background","none")),
                                  config.get("piece_style","traditional"))
        split.addWidget(self.board)
        side=QWidget();side_layout=QVBoxLayout(side);side_layout.addWidget(QLabel("着法列表"))
        self.moves=QListWidget();self.moves.addItem("0. 开局")
        self.moves.addItems([f"{index}. {record.notation}" for index,record in enumerate(game.state.history,1)])
        self.moves.currentRowChanged.connect(self.set_step);side_layout.addWidget(self.moves,1)
        split.addWidget(side);split.setSizes([700,230])
        controls = QHBoxLayout()
        for text, callback in (("|<", lambda: self.set_step(0)), ("<", lambda: self.set_step(self.slider.value()-1)), (">", lambda: self.set_step(self.slider.value()+1)), (">|", lambda: self.set_step(len(self.snapshots)-1))):
            button=QPushButton(text);button.clicked.connect(callback);controls.addWidget(button)
        self.slider=QSlider(Qt.Orientation.Horizontal);self.slider.setRange(0,len(self.snapshots)-1);self.slider.valueChanged.connect(self.show_step);controls.addWidget(self.slider,1)
        self.play=QPushButton("播放");self.play.clicked.connect(self.toggle_play);controls.addWidget(self.play)
        close=QPushButton("退出复盘");close.clicked.connect(self.accept);controls.addWidget(close);layout.addLayout(controls)
        self.timer=QTimer(self);self.timer.setInterval(900);self.timer.timeout.connect(self.next_step)
        self.set_step(len(self.snapshots)-1)

    def set_step(self, step: int) -> None:
        self.slider.setValue(max(0,min(len(self.snapshots)-1,step)))

    def show_step(self, step: int) -> None:
        state=self.snapshots[step].clone(); replay=Game.from_state(state,self.options)
        self.board.set_game(replay,Color.RED,True);self.board.interactive=False
        notation=state.history[-1].notation if state.history else "开局"
        self.info.setText(f"第 {step} / {len(self.snapshots)-1} 步 · {notation}")
        self.moves.blockSignals(True);self.moves.setCurrentRow(step);self.moves.blockSignals(False)

    def toggle_play(self) -> None:
        if self.timer.isActive():
            self.timer.stop();self.play.setText("播放")
        else:
            if self.slider.value() >= self.slider.maximum():self.set_step(0)
            self.timer.start();self.play.setText("暂停")

    def next_step(self) -> None:
        if self.slider.value() >= self.slider.maximum():
            self.timer.stop();self.play.setText("播放");return
        self.set_step(self.slider.value()+1)


class GameLibraryDialog(QDialog):
    def __init__(self, folder: Path, config: dict, parent=None):
        super().__init__(parent);self.setWindowTitle("本地棋谱库");self.resize(700,520)
        self.folder=folder;self.config=config;self.selected_path:Path|None=None
        self.folder.mkdir(parents=True,exist_ok=True)
        layout=QVBoxLayout(self);layout.addWidget(QLabel(f"棋谱目录：{self.folder}"))
        self.list=QListWidget();layout.addWidget(self.list,1)
        files=sorted((*self.folder.glob("*.xhgame"),*self.folder.glob("*.json")),key=lambda path:path.stat().st_mtime,reverse=True)
        for path in files:
            item=QListWidgetItem(f"{path.stem}    {path.stat().st_size//1024+1} KB")
            item.setData(Qt.ItemDataRole.UserRole,str(path));self.list.addItem(item)
        if not files:self.list.addItem("暂无本地棋谱；结束对局后将自动保存到这里")
        actions=QHBoxLayout();replay=QPushButton("复盘");resume=QPushButton("继续对局");open_folder=QPushButton("打开目录");close=QPushButton("关闭")
        replay.clicked.connect(self.replay_selected);resume.clicked.connect(self.resume_selected);open_folder.clicked.connect(self.open_folder);close.clicked.connect(self.reject)
        for button in (replay,resume,open_folder,close):actions.addWidget(button)
        layout.addLayout(actions);self.list.itemDoubleClicked.connect(lambda _:self.replay_selected())

    def current_path(self) -> Path | None:
        item=self.list.currentItem();value=item.data(Qt.ItemDataRole.UserRole) if item else None
        return Path(value) if value else None

    def replay_selected(self) -> None:
        path=self.current_path()
        if not path:return
        try:ReplayDialog(load_game(path),self.config,self).exec()
        except Exception as exc:QMessageBox.warning(self,"棋谱读取失败",str(exc))

    def resume_selected(self) -> None:
        path=self.current_path()
        if path:self.selected_path=path;self.accept()

    def open_folder(self) -> None:
        try:os.startfile(self.folder)
        except OSError as exc:QMessageBox.warning(self,"打开目录失败",str(exc))


class DocumentDialog(QDialog):
    def __init__(self, title: str, content: str, parent=None):
        super().__init__(parent);self.setWindowTitle(title);self.resize(760,680)
        layout=QVBoxLayout(self);browser=QTextBrowser();browser.setMarkdown(content);layout.addWidget(browser)
        close=QPushButton("关闭");close.clicked.connect(self.accept);layout.addWidget(close)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__();load_bundled_fonts();self.config=load_config();self.game=None;self.cancel=threading.Event();self.pool=QThreadPool.globalInstance();self.network=None;self.room_id=None;self.token=None;self.revision=0;self.audio=DesktopAudio();self._stats_recorded=False;self._autosaved=False
        self.setWindowTitle("匈汉象棋")
        icon_path = Path(__file__).resolve().parent / "resources" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1260,850);self.setMinimumSize(760,560);self._build();self.new_game()
        self.audio.configure(self.config);self.apply_appearance()
        self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(250)

    def _build(self):
        file_menu = self.menuBar().addMenu("文件")
        for title, callback, shortcut in (("导入棋局",self.import_game,"Ctrl+O"),("导出棋局",self.export_game,"Ctrl+S")):
            action=QAction(title,self);action.triggered.connect(callback)
            if shortcut:action.setShortcut(QKeySequence(shortcut))
            file_menu.addAction(action)
        file_menu.addSeparator();library=QAction("本地棋谱库",self);library.triggered.connect(self.show_game_library);file_menu.addAction(library);autosaves=QAction("打开自动保存目录",self);autosaves.triggered.connect(self.open_autosave_folder);file_menu.addAction(autosaves)
        game_menu = self.menuBar().addMenu("对局")
        ai_game=QAction("人机对战",self);ai_game.triggered.connect(lambda:self.start_mode("ai"));game_menu.addAction(ai_game)
        local_game=QAction("双人同机对弈",self);local_game.triggered.connect(lambda:self.start_mode("local"));game_menu.addAction(local_game);game_menu.addSeparator()
        for title, callback, shortcut in (("新建对局",self.new_game,"Ctrl+N"),("悔棋",self.undo_move,"Ctrl+Z"),("暂停/继续",self.toggle_pause,"Ctrl+P")):
            action=QAction(title,self);action.triggered.connect(callback);action.setShortcut(QKeySequence(shortcut));game_menu.addAction(action)
        game_menu.addSeparator()
        for title, callback in (("认输",self.resign_game),("提和",self.draw_game),("复活兵卒",self.resurrect_pawn)):
            action=QAction(title,self);action.triggered.connect(callback);game_menu.addAction(action)
        game_menu.addSeparator()
        for title, callback in (("创建局域网房间", self.create_online), ("加入局域网房间", self.join_online)):
            action = QAction(title, self); action.triggered.connect(callback); game_menu.addAction(action)
        replay_menu=self.menuBar().addMenu("复盘")
        replay=QAction("进入复盘",self);replay.setShortcut(QKeySequence("Ctrl+R"));replay.triggered.connect(self.replay_game);replay_menu.addAction(replay)
        library_replay=QAction("本地棋谱库",self);library_replay.triggered.connect(self.show_game_library);replay_menu.addAction(library_replay)
        view_menu=self.menuBar().addMenu("视图")
        fullscreen=QAction("全屏",self);fullscreen.setShortcut(QKeySequence("F11"));fullscreen.triggered.connect(self.toggle_fullscreen);view_menu.addAction(fullscreen)
        panels=QAction("显示/隐藏侧栏",self);panels.triggered.connect(self.toggle_panels);view_menu.addAction(panels)
        settings_menu = self.menuBar().addMenu("设置")
        settings_action = QAction("打开设置...", self); settings_action.triggered.connect(self.settings); settings_menu.addAction(settings_action);settings_menu.addSeparator()
        stats=QAction("对局统计",self);stats.triggered.connect(self.show_statistics);settings_menu.addAction(stats)
        help_menu=self.menuBar().addMenu("帮助")
        guide=QAction("使用帮助",self);guide.setShortcut(QKeySequence("F1"));guide.triggered.connect(self.show_help);help_menu.addAction(guide)
        rules=QAction("棋子规则",self);rules.triggered.connect(self.show_rules);help_menu.addAction(rules)
        help_menu.addSeparator()
        about=QAction("关于",self);about.triggered.connect(self.show_about);help_menu.addAction(about)
        root=QWidget();root.setObjectName("root");self.setCentralWidget(root);layout=QVBoxLayout(root);self.banner=QLabel();self.banner.setAlignment(Qt.AlignmentFlag.AlignCenter);self.banner.setObjectName("banner");layout.addWidget(self.banner)
        split=QSplitter();layout.addWidget(split,1);self.board=BoardWidget();self.board.move_requested.connect(self.human_move);self.board.piece_selected.connect(lambda:self.audio.play("select"));split.addWidget(self.board)
        self.side=QWidget();self.side.setMaximumWidth(330);right=QVBoxLayout(self.side);self.black=QLabel();self.red=QLabel();self.history=QListWidget();self.captured=QLabel();self.captured.setWordWrap(True)
        right.addWidget(self.black);right.addWidget(self.red)
        side_tabs=QTabWidget();record_page=QWidget();record_layout=QVBoxLayout(record_page);record_layout.addWidget(self.history)
        chat_page=QWidget();chat_layout=QVBoxLayout(chat_page);self.chat_messages=QListWidget();chat_layout.addWidget(self.chat_messages,1)
        self.chat_quick=QComboBox();[(self.chat_quick.addItem(label,text)) for label,text in (
            ("请多指教","请多指教"),("好棋","好棋！"),("承让","承让"),("稍等一下","稍等一下"),
            ("再来一局","再来一局"),("挑衅","这一步，你可要想好了！"))]
        quick_send=QPushButton("发送快捷短语");quick_send.clicked.connect(lambda:self.send_chat(True));chat_layout.addWidget(self.chat_quick);chat_layout.addWidget(quick_send)
        chat_row=QHBoxLayout();self.chat_input=QLineEdit();self.chat_input.setMaxLength(80);self.chat_input.setPlaceholderText("输入聊天内容")
        self.chat_input.returnPressed.connect(self.send_chat);chat_send=QPushButton("发送");chat_send.clicked.connect(self.send_chat);chat_row.addWidget(self.chat_input,1);chat_row.addWidget(chat_send);chat_layout.addLayout(chat_row)
        side_tabs.addTab(record_page,"棋谱");side_tabs.addTab(chat_page,"聊天");right.addWidget(side_tabs,1);right.addWidget(QLabel("阵亡子力"));right.addWidget(self.captured)
        actions=QGridLayout();self.undo=QPushButton("悔棋");self.undo.clicked.connect(self.undo_move);self.pause=QPushButton("暂停");self.pause.clicked.connect(self.toggle_pause);self.resign=QPushButton("认输");self.resign.clicked.connect(self.resign_game);self.draw=QPushButton("提和");self.draw.clicked.connect(self.draw_game);self.resurrect=QPushButton("复活兵卒");self.resurrect.clicked.connect(self.resurrect_pawn)
        for i,b in enumerate((self.undo,self.pause,self.resign,self.draw,self.resurrect)):actions.addWidget(b,i//2,i%2)
        right.addLayout(actions);split.addWidget(self.side);split.setSizes([850,300])
        self.apply_appearance()

    def new_game(self):
        self.close_network();self.cancel.set();self.cancel=threading.Event();self.game=Game(self.config["profile"],self.config.get("rule_options"),self.config["initial_minutes"]);human=Color(self.config["human_color"]);local=self.config.get("game_mode","ai")=="local";self.board.set_game(self.game,human,local);self.configure_board();self.board.locked=False;self._stats_recorded=False;self._autosaved=False;self.refresh();
        if not local and self.game.state.turn is not human:self.start_ai()

    def start_mode(self, mode: str) -> None:
        self.config["game_mode"]=mode;save_config(self.config);self.new_game()

    def human_move(self, move: Move):
        if self.network:
            self.send_network("move",{"from":{"row":move.source.row,"col":move.source.col},"to":{"row":move.target.row,"col":move.target.col},"promotion":move.promotion.value if move.promotion else None});return
        try:
            piece=self.game.state.piece_at(move.source)
            if piece and piece.type is PieceType.PAWN and self.game.options.pawn_promotion and move.target.row in {0,self.game.profile.rows-1}:
                choices={p.type for p in self.game.state.captured[piece.color] if p.type not in {PieceType.PAWN,PieceType.KING} and p.type in self.game.rules.enabled_piece_types}
                if choices:
                    options=[(NAMES[piece.color][kind],kind) for kind in sorted(choices,key=lambda item:item.value)]
                    label,ok=QInputDialog.getItem(self,"兵卒升变","选择升变棋子",[item[0] for item in options],0,False)
                    if not ok:return
                    move=Move(move.source,move.target,next(kind for text,kind in options if text==label))
            record=self.game.move(move);self.board.animate_move(move.target,bool(record.captured));self.play_sound();self.refresh();
            if not self.game.state.finished and self.config.get("game_mode","ai")=="ai":self.start_ai()
        except GameError as exc:QMessageBox.warning(self,"非法走棋",str(exc))

    def start_ai(self):
        if self.board.locked or self.game.state.finished or self.game.state.paused:return
        self.board.locked=True;self.board.update();worker=AIWorker(self.game,self.config["difficulty"],self.cancel);worker.signals.finished.connect(self.finish_ai);worker.signals.failed.connect(self.ai_failed);self.pool.start(worker)

    def finish_ai(self, result):
        move,cancel=result
        if cancel.is_set():return
        try:
            if move:
                record=self.game.move(move);self.board.animate_move(move.target,bool(record.captured));self.play_sound()
        except GameError as exc:self.ai_failed(str(exc));return
        self.board.locked=False;self.refresh()

    def ai_failed(self,result):
        message,cancel=result if isinstance(result,tuple) else (str(result),self.cancel)
        if cancel.is_set():return
        self.board.locked=False;self.refresh();QMessageBox.warning(self,"AI 异常",message)
    def play_sound(self):
        if not self.game or not self.game.state.history:return
        record=self.game.state.history[-1]
        if self.game.state.finished:self.audio.play("win" if self.game.state.winner is Color(self.config["human_color"]) else "lose")
        elif self.game.rules.in_check(self.game.state,self.game.state.turn):self.audio.play("check")
        else:self.audio.play("capture" if record.captured else "move")
    def undo_move(self):
        if self.network:self.send_network("undo_request");return
        try:self.cancel.set();plies=1 if self.config.get("game_mode")=="local" else (2 if len(self.game.state.history)>=2 else 1);self.game.undo(plies);self.cancel=threading.Event();self.board.locked=False;self.refresh()
        except GameError as exc:QMessageBox.information(self,"悔棋",str(exc))
    def toggle_pause(self):
        if not self.game or self.game.state.finished:return
        if self.network:self.send_network("pause",{"paused":not self.game.state.paused});return
        try:
            pausing=not self.game.state.paused
            if pausing:self.cancel.set();self.board.locked=False
            self.game.set_paused(pausing,Color(self.config["human_color"]));self.cancel=threading.Event();self.refresh()
            if not pausing and self.config.get("game_mode")=="ai" and self.game.state.turn is not Color(self.config["human_color"]):self.start_ai()
        except GameError as exc:QMessageBox.information(self,"暂停",str(exc))
    def resign_game(self):
        if self.network:self.send_network("resign");return
        color=self.game.state.turn if self.config.get("game_mode")=="local" else Color(self.config["human_color"]);self.game.resign(color);self.refresh()
    def draw_game(self):
        if self.network:self.send_network("draw_offer");return
        if QMessageBox.question(self,"提和","确认以和棋结束当前对局？")==QMessageBox.StandardButton.Yes:self.game.state.draw=True;self.game.state.result_reason="draw_agreement";self.refresh()

    def replay_game(self):
        if not self.game or not self.game.state.history:
            QMessageBox.information(self, "复盘", "当前棋局还没有棋谱")
            return
        ReplayDialog(self.game,self.config,self).exec()
    def resurrect_pawn(self):
        color=self.game.state.turn if self.config.get("game_mode")=="local" else Color(self.config["human_color"]);row=8 if color is Color.RED else 4
        for col in range(0,self.game.profile.cols,2):
            try:self.game.resurrect_pawn(color,Position(row,col));self.refresh();
            except GameError:continue
            if self.config.get("game_mode","ai")=="ai":self.start_ai()
            return
        QMessageBox.information(self,"复活","当前没有可用的兵卒复活位置")

    def settings(self):
        dialog=SettingsDialog(self.config,self)
        if dialog.exec():self.config=dialog.value();save_config(self.config);self.audio.configure(self.config);self.apply_appearance();self.new_game()

    def apply_appearance(self):
        if not hasattr(self,"board"):return
        theme=THEMES.get(self.config.get("theme","classic"),THEMES["classic"]);font=FONT_CHOICES.get(self.config.get("font","system"),UI_FONT)
        QApplication.instance().setFont(QFont(font,10));self.configure_board()
        text="#f3ead7" if self.config.get("theme")=="dark" else "#211b17"
        hover="#4a433b" if self.config.get("theme")=="dark" else "#f1dfbf"
        self.setStyleSheet(f"""QMainWindow,#root{{background:{theme['window']};color:{text}}}QMenuBar,QMenu,QToolBar{{background:{theme['panel']};color:{text};border-bottom:1px solid {theme['line']};padding:5px}}#banner{{background:{theme['accent']};color:white;padding:8px;font-weight:bold;font-size:15px}}QListWidget,QLabel,QFrame,QGroupBox,QComboBox,QSpinBox,QLineEdit{{background:{theme['panel']};color:{text};border:1px solid {theme['line']};padding:7px}}QPushButton{{min-height:35px;background:{theme['panel']};color:{text};border:1px solid {theme['line']}}}QPushButton:hover{{background:{hover}}}""")

    def configure_board(self):
        self.board.set_appearance(self.config.get("theme","classic"),str(self.config.get("background","none")),self.config.get("piece_style","traditional"))
        self.board.set_assists(selection=self.config.get("selection_highlight",True),legal_targets=self.config.get("legal_targets",True),capture_hints=self.config.get("capture_hints",True),animations=self.config.get("animations",True))

    def toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def toggle_panels(self):
        self.side.setVisible(not self.side.isVisible())

    def export_game(self):
        if not self.game:return
        path,_=QFileDialog.getSaveFileName(self,"导出棋局",str(config_path().parent / "games" / "当前棋局.xhgame"),"匈汉棋谱 (*.xhgame);;JSON (*.json)")
        if not path:return
        if not Path(path).suffix:path += ".xhgame"
        try:save_game(self.game,path);self.statusBar().showMessage(f"棋局已保存：{path}",5000)
        except Exception as exc:QMessageBox.warning(self,"导出失败",str(exc))

    def import_game(self):
        path,_=QFileDialog.getOpenFileName(self,"导入棋局",str(config_path().parent / "games"),"匈汉棋谱 (*.xhgame *.json)")
        if not path:return
        self.load_game_path(Path(path))

    def load_game_path(self,path:Path):
        try:
            game=load_game(path);self.close_network();self.cancel.set();self.cancel=threading.Event();self.game=game;self.config["profile"]=game.profile.id;self.config["rule_options"]=asdict(game.options);save_config(self.config);self.board.set_game(game,Color(self.config["human_color"]),self.config.get("game_mode","ai")=="local");self.configure_board();self._stats_recorded=game.state.finished;self._autosaved=game.state.finished;self.refresh();self.statusBar().showMessage(f"已载入：{path}",5000)
        except Exception as exc:QMessageBox.warning(self,"导入失败",str(exc))

    def show_game_library(self):
        dialog=GameLibraryDialog(config_path().parent / "games",self.config,self)
        if dialog.exec() and dialog.selected_path:self.load_game_path(dialog.selected_path)

    def open_autosave_folder(self):
        folder=config_path().parent / "games";folder.mkdir(parents=True,exist_ok=True)
        try:os.startfile(folder)
        except OSError as exc:QMessageBox.warning(self,"打开目录失败",str(exc))

    def show_statistics(self):
        stats=load_statistics();rate=(stats["wins"]*100/stats["games"]) if stats["games"] else 0
        box=QMessageBox(self);box.setWindowTitle("对局统计");box.setText(f"总对局：{stats['games']}\n胜：{stats['wins']}  负：{stats['losses']}  和：{stats['draws']}\n累计走子：{stats['moves']}\n胜率：{rate:.1f}%");reset=box.addButton("重置统计",QMessageBox.ButtonRole.DestructiveRole);box.addButton(QMessageBox.StandardButton.Close);box.exec()
        if box.clickedButton() is reset and QMessageBox.question(self,"确认","确定清空统计数据？")==QMessageBox.StandardButton.Yes:reset_statistics()

    def show_rules(self):
        path=Path(__file__).resolve().parent / "resources" / "docs" / "PIECE_RULES.md"
        try:content=path.read_text(encoding="utf-8")
        except OSError as exc:content=f"规则文档读取失败：{exc}"
        DocumentDialog("棋子规则",content,self).exec()

    def show_help(self):
        path=Path(__file__).resolve().parent / "resources" / "docs" / "HELP.md"
        try:content=path.read_text(encoding="utf-8")
        except OSError as exc:content=f"帮助文档读取失败：{exc}"
        DocumentDialog("匈汉象棋使用帮助",content,self).exec()

    def show_about(self):
        path=Path(__file__).resolve().parent / "resources" / "docs" / "ABOUT.md"
        try:content=path.read_text(encoding="utf-8")
        except OSError as exc:content=f"关于文档读取失败：{exc}"
        DocumentDialog("关于匈汉象棋",content,self).exec()

    def server_base(self) -> str | None:
        value,ok=QInputDialog.getText(self,"服务器地址","FastAPI 服务地址",QLineEdit.EchoMode.Normal,self.config.get("server_url","http://127.0.0.1:8000"))
        if not ok:return None
        self.config["server_url"]=value.rstrip("/");save_config(self.config);return self.config["server_url"]

    def create_online(self):
        base=self.server_base()
        if not base:return
        try:
            data=self.http_json(base+"/api/rooms",{"profileId":self.config["profile"],"mode":"online","playerName":"桌面玩家","playerColor":self.config["human_color"],"options":self.config.get("rule_options",{}),"initialMinutes":self.config["initial_minutes"]})
            self.open_network(base,data)
            QMessageBox.information(self,"房间已创建",f"房间号：{data['roomId']}")
        except Exception as exc:QMessageBox.warning(self,"创建失败",str(exc))

    def join_online(self):
        base=self.server_base()
        if not base:return
        room,ok=QInputDialog.getText(self,"加入房间","房间号")
        if not ok or not room:return
        try:self.open_network(base,self.http_json(f"{base}/api/rooms/{room.strip().upper()}/join",{"playerName":"桌面玩家"}))
        except Exception as exc:QMessageBox.warning(self,"加入失败",str(exc))

    @staticmethod
    def http_json(url,payload):
        request=urllib.request.Request(url,json.dumps(payload).encode("utf-8"),{"Content-Type":"application/json"},method="POST")
        with urllib.request.urlopen(request,timeout=8) as response:return json.loads(response.read().decode("utf-8"))

    def open_network(self,base,data):
        self.cancel.set();self.room_id=data["roomId"];self.token=data["token"];self.revision=data["snapshot"]["revision"];self.apply_network_state(data["snapshot"])
        self.network=QWebSocket();self.network.textMessageReceived.connect(self.network_message);self.network.disconnected.connect(lambda:self.statusBar().showMessage("网络已断开"));ws=base.replace("https://","wss://",1).replace("http://","ws://",1)+f"/ws/{self.room_id}?token={self.token}";self.network.open(QUrl(ws));self.statusBar().showMessage(f"房间 {self.room_id} · 正在连接")

    def network_message(self,text):
        message=json.loads(text)
        if message["type"]=="error":QMessageBox.warning(self,"服务器拒绝",message["payload"]["message"]);self.apply_network_state(message["payload"].get("state",{}))
        elif message["type"]=="chat":
            payload=message["payload"];self.chat_messages.addItem(f"{payload.get('sender','玩家')}：{payload.get('text','')}");self.chat_messages.scrollToBottom()
        elif message["type"]=="state":
            snapshot=message["payload"];game_data=snapshot["game"]
            if game_data.get("pendingDrawOffer") and game_data["pendingDrawOffer"]!=self.config["human_color"]:self.send_network("draw_response",{"accept":QMessageBox.question(self,"提和","对手请求和棋，是否接受？")==QMessageBox.StandardButton.Yes})
            if game_data.get("pendingUndoOffer") and game_data["pendingUndoOffer"]!=self.config["human_color"]:self.send_network("undo_response",{"accept":QMessageBox.question(self,"悔棋","对手请求悔棋，是否接受？")==QMessageBox.StandardButton.Yes})
            self.apply_network_state(snapshot)

    def apply_network_state(self,snapshot):
        if not snapshot:return
        self.revision=snapshot["revision"];self.config["human_color"]=snapshot.get("youAre") or self.config["human_color"];self.game=Game.from_state(GameState.from_dict(snapshot["game"]),snapshot["game"]["profile"]["options"]);self.board.set_game(self.game,Color(self.config["human_color"]),False);self.configure_board();self.board.locked=False
        if not self.game.state.history:self._stats_recorded=False;self._autosaved=False
        self.statusBar().showMessage(f"房间 {snapshot['roomId']} · 状态版本 {self.revision}");self.refresh()

    def send_network(self,type_,payload=None):
        if not self.network or not self.network.isValid():QMessageBox.information(self,"网络","连接尚未建立");return
        self.network.sendTextMessage(json.dumps({"type":type_,"roomId":self.room_id,"revision":self.revision,"payload":payload or {},"protocolVersion":1},ensure_ascii=False))

    def send_chat(self, quick=False):
        if not self.network:
            QMessageBox.information(self,"聊天","聊天仅在联机房间中可用")
            return
        text=self.chat_quick.currentData() if quick else self.chat_input.text().strip()
        if not text:return
        self.send_network("chat",{"text":text,"quick":bool(quick)})
        if not quick:self.chat_input.clear()

    def close_network(self):
        if self.network:self.network.close();self.network.deleteLater()
        self.network=None;self.room_id=None;self.token=None

    def refresh(self):
        if not self.game:return
        if not self.network:self.game.tick()
        state=self.game.state;self.banner.setText("对局结束" if state.finished else ("对局已暂停" if state.paused else f"{'红方' if state.turn is Color.RED else '黑方'}行棋"))
        self.red.setText(f"红方  {self._clock(state.clocks_ms[Color.RED])}");self.black.setText(f"黑方  {self._clock(state.clocks_ms[Color.BLACK])}")
        threshold=max(0,int(self.config.get("countdown_seconds",30)))*1000
        self.red.setStyleSheet("color:#b21f1f;font-weight:bold" if threshold and state.clocks_ms[Color.RED]<=threshold and not state.paused else "")
        self.black.setStyleSheet("color:#b21f1f;font-weight:bold" if threshold and state.clocks_ms[Color.BLACK]<=threshold and not state.paused else "")
        self.history.clear();self.history.addItems([r.notation for r in state.history]);self.captured.setText("红："+" ".join(NAMES[p.color][p.type] for p in state.captured[Color.RED])+"\n黑："+" ".join(NAMES[p.color][p.type] for p in state.captured[Color.BLACK]));self.board.update()
        self.pause.setText("继续" if state.paused else "暂停");self.pause.setEnabled(not state.finished);self.undo.setEnabled(bool(state.history) and not state.paused);self.draw.setEnabled(not state.finished and not state.paused);self.resign.setEnabled(not state.finished);self.resurrect.setEnabled(not state.finished and not state.paused)
        if state.finished and not self._stats_recorded:record_result(self.game,self.config["human_color"]);self._stats_recorded=True
        if state.finished and self.config.get("autosave",True) and not self._autosaved:
            try:path=autosave_game(self.game);self.statusBar().showMessage(f"棋谱已自动保存：{path}",8000)
            except OSError as exc:self.statusBar().showMessage(f"自动保存失败：{exc}",8000)
            self._autosaved=True
        if state.finished and not getattr(self,"_shown_result",False):self._shown_result=True;winner="和棋" if state.draw else f"{'红方' if state.winner is Color.RED else '黑方'}胜利";QMessageBox.information(self,"对局结果",winner)
        if not state.finished:self._shown_result=False

    @staticmethod
    def _clock(ms):seconds=max(0,ms//1000);return f"{seconds//60:02d}:{seconds%60:02d}"

    def closeEvent(self,event):self.cancel.set();self.close_network();self.audio.stop();save_config(self.config);super().closeEvent(event)


def run() -> None:
    app=QApplication(sys.argv);app.setApplicationName("匈汉象棋")
    icon_path=Path(__file__).resolve().parent / "resources" / "icon.ico"
    if icon_path.exists():app.setWindowIcon(QIcon(str(icon_path)))
    load_bundled_fonts();window=MainWindow();window.show();sys.exit(app.exec())


if __name__ == "__main__":run()
