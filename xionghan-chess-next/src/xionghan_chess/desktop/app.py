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
from xionghan_chess.core.analysis import analyze_game
from xionghan_chess.core.game import Game, GameError
from xionghan_chess.core.model import Color, GameState, Move, PieceType, Position
from xionghan_chess.core.profiles import PROFILES, profile_rule_values
from xionghan_chess.core.puzzles import load_puzzles
from xionghan_chess.core.setup import GameSetup, profile_slots
from xionghan_chess.core.storage import game_document, game_from_document
from xionghan_chess.i18n import normalize_language, t
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
        self.language = "zh-CN"
        self.flipped = False
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

    def set_flipped(self, flipped: bool) -> None:
        self.flipped = flipped
        self.selected, self.legal, self.capturable = None, [], set()
        self.update()

    def _view_position(self, position: Position) -> Position:
        if not self.flipped or not self.game:
            return position
        return Position(self.game.profile.rows - 1 - position.row,
                        self.game.profile.cols - 1 - position.col)

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
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{t('status.paused', self.language)}\n{t('status.timer_stopped', self.language)}")
        if self.locked:
            painter.fillRect(rect, QColor(30, 25, 20, 90))
            painter.setPen(QColor("white")); painter.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, t("status.thinking_desktop", self.language))

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
        painter.setFont(QFont(PIECE_FONT, max(16, int(cw * .38))))
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
            shown = self._view_position(position)
            x, y = left + shown.col * cw, top + shown.row * ch
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
        painter.setFont(QFont(PIECE_FONT, max(13, int(radius*1.15)), QFont.Weight.Bold))
        painter.setPen(QColor("#9a2424") if piece.color is Color.RED else QColor("#24211e"))
        painter.drawText(int(center.x()-radius), int(center.y()-radius), int(radius*2), int(radius*2), Qt.AlignmentFlag.AlignCenter, NAMES[piece.color][piece.type])

    def _position(self, point) -> Position | None:
        if not self.game:
            return None
        _,left,top,cw,ch=self._geometry()
        col=round((point.x()-left)/cw);row=round((point.y()-top)/ch)
        if self.flipped:
            row=self.game.profile.rows-1-row;col=self.game.profile.cols-1-col
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
        super().__init__(parent); self.language=normalize_language(config.get("language")); self.setWindowTitle(t("settings.desktop_title", self.language)); self.resize(720, 760)
        layout=QVBoxLayout(self); tabs=QTabWidget(); layout.addWidget(tabs,1)
        self.profile=QComboBox(); [self.profile.addItem(t(f"profile.{p.id}", self.language),p.id) for p in PROFILES.values()]
        self.profile.setCurrentIndex(max(0,self.profile.findData(config["profile"])))
        self.language_select=QComboBox();self.language_select.addItem(t("language.zh-CN", self.language),"zh-CN");self.language_select.addItem(t("language.en", self.language),"en");self.language_select.setCurrentIndex(max(0,self.language_select.findData(self.language)))
        self.game_mode=QComboBox();self.game_mode.addItem(t("mode.ai", self.language),"ai");self.game_mode.addItem(t("mode.local_full", self.language),"local");self.game_mode.setCurrentIndex(max(0,self.game_mode.findData(config.get("game_mode","ai"))))
        self.difficulty=QComboBox();[(self.difficulty.addItem(t(f"difficulty.{value}", self.language),value)) for value in ("beginner","easy","medium","hard")]
        self.difficulty.setCurrentIndex(max(0,self.difficulty.findData(config["difficulty"])))
        self.color=QComboBox();self.color.addItem(t("option.red_first", self.language),"red");self.color.addItem(t("option.black_second", self.language),"black");self.color.setCurrentIndex(max(0,self.color.findData(config["human_color"])))
        self.first_move=QComboBox();self.first_move.addItem("默认（红先）","red");self.first_move.addItem("黑先","black");self.first_move.addItem("随机","random");self.first_move.setCurrentIndex(max(0,self.first_move.findData(config.get("first_move","red"))))
        self.minutes=QSpinBox();self.minutes.setRange(1,180);self.minutes.setValue(config["initial_minutes"])
        self.countdown=QComboBox();[(self.countdown.addItem(t("option.last_seconds", self.language, count=value),value)) for value in (10,30,60)];self.countdown.addItem(t("option.off", self.language),0);self.countdown.setCurrentIndex(max(0,self.countdown.findData(config.get("countdown_seconds",30))))
        self.sound=QCheckBox(t("settings.sound_effects", self.language));self.sound.setChecked(config["sound"])
        self.music=QCheckBox(t("settings.music", self.language));self.music.setChecked(config.get("music",False))
        self.music_style=QComboBox();self.music_style.addItem(t("option.music_fc", self.language),"fc");self.music_style.addItem(t("option.music_qq", self.language),"qq");self.music_style.setCurrentIndex(max(0,self.music_style.findData(config.get("music_style","fc"))))
        self.sound_volume=QSlider(Qt.Orientation.Horizontal);self.sound_volume.setRange(0,100);self.sound_volume.setValue(config.get("sound_volume",70))
        self.music_volume=QSlider(Qt.Orientation.Horizontal);self.music_volume.setRange(0,100);self.music_volume.setValue(config.get("music_volume",40))
        self.theme=QComboBox();[(self.theme.addItem(t(f"option.theme_{value}", self.language),value)) for value in ("classic","green","blue","purple","dark")];self.theme.setCurrentIndex(max(0,self.theme.findData(config.get("theme","classic"))))
        self.font=QComboBox();[(self.font.addItem(text,value)) for value,text in (("system","微软雅黑"),("kaiti","楷体"),("songti","宋体"),("fangsong","仿宋"))];self.font.setCurrentIndex(max(0,self.font.findData(config.get("font","system"))))
        self.background=QComboBox();self.background.addItem("原色（无背景图片）","none");[(self.background.addItem(f"背景 {index}",str(index))) for index in range(1,6)];self.background.setCurrentIndex(max(0,self.background.findData(str(config.get("background","none")))))
        self.piece_style=QComboBox();[(self.piece_style.addItem(t(f"option.piece_{value}", self.language),value)) for value in ("traditional","modern","cartoon")];self.piece_style.setCurrentIndex(max(0,self.piece_style.findData(config.get("piece_style","traditional"))))
        self.animations=QCheckBox(t("settings.animation", self.language));self.animations.setChecked(config.get("animations",True))
        self.selection_highlight=QCheckBox(t("settings.selection", self.language));self.selection_highlight.setChecked(config.get("selection_highlight",True))
        self.legal_targets=QCheckBox(t("settings.legal_targets", self.language));self.legal_targets.setChecked(config.get("legal_targets",True))
        self.capture_hints=QCheckBox(t("settings.capture_hints", self.language));self.capture_hints.setChecked(config.get("capture_hints",True))
        self.autosave=QCheckBox(t("settings.autosave_desktop", self.language));self.autosave.setChecked(config.get("autosave",True))

        game_tab=QWidget();game_layout=QVBoxLayout(game_tab);game_form=QFormLayout()
        game_form.addRow(t("settings.game_mode", self.language),self.game_mode);game_form.addRow(t("settings.profile", self.language),self.profile);game_form.addRow(t("difficulty.label", self.language),self.difficulty)
        game_form.addRow(t("settings.human_color", self.language),self.color);game_form.addRow(t("settings.initial_minutes", self.language),self.minutes);game_form.addRow(t("settings.countdown", self.language),self.countdown)
        game_form.addRow("先手",self.first_move)
        game_layout.addLayout(game_form);game_layout.addWidget(self.autosave)
        tabs.addTab(game_tab,t("settings.game_tab", self.language))

        appearance_tab=QWidget();appearance_form=QFormLayout(appearance_tab)
        appearance_form.addRow(t("language.label", self.language),self.language_select)
        appearance_form.addRow(t("settings.board_theme", self.language),self.theme);appearance_form.addRow(t("settings.font", self.language),self.font)
        appearance_form.addRow(t("settings.background", self.language),self.background);appearance_form.addRow(t("settings.piece_style", self.language),self.piece_style);appearance_form.addRow(t("settings.sound_effects", self.language),self.sound)
        appearance_form.addRow(t("settings.sound_volume", self.language),self.sound_volume);appearance_form.addRow(t("settings.music", self.language),self.music)
        appearance_form.addRow(t("settings.music_style", self.language),self.music_style);appearance_form.addRow(t("settings.music_volume", self.language),self.music_volume)
        appearance_form.addRow(t("settings.animation", self.language),self.animations);appearance_form.addRow(t("settings.selection", self.language),self.selection_highlight)
        appearance_form.addRow(t("settings.legal_targets", self.language),self.legal_targets);appearance_form.addRow(t("settings.capture_hints", self.language),self.capture_hints)
        tabs.addTab(appearance_tab,t("settings.appearance_tab", self.language))

        self._active_profile_id = config["profile"]
        self._profile_values = {profile_id: profile_rule_values(profile_id) for profile_id in PROFILES}
        self._profile_values[self._active_profile_id] = profile_rule_values(
            self._active_profile_id, config.get("rule_options", {}))
        self.checks={}; options=PROFILES[self._active_profile_id].options.merged(
            self._profile_values[self._active_profile_id])
        general=QGroupBox(t("settings.general_rules", self.language));general_layout=QVBoxLayout(general)
        for key in ("enforce_self_check","threefold_draw"):
            check=QCheckBox(t(f"rule.{key}", self.language));check.setChecked(bool(getattr(options,key)));self.checks[key]=check;general_layout.addWidget(check)
        game_layout.addWidget(general);game_layout.addStretch()

        piece_definitions={
            PieceType.KING:("piece.king_label","piece_rule.king_long",("king_can_leave_palace","king_diagonal_in_palace","king_lose_diagonal_outside_palace","invasion_victory")),
            PieceType.ROOK:("piece.rook_label","piece_rule.rook_long",()),
            PieceType.HORSE:("piece.horse_label","piece_rule.horse_long",("horse_straight_three",)),
            PieceType.ELEPHANT:("piece.elephant_label","piece_rule.elephant_long",("elephant_can_cross_river","elephant_gain_jump_two_enemy_territory")),
            PieceType.ADVISOR:("piece.advisor_label","piece_rule.advisor_long",("advisor_can_leave_palace","advisor_gain_straight_outside_palace")),
            PieceType.CANNON:("piece.cannon_label","piece_rule.cannon_long",()),
            PieceType.PAWN:("piece.pawn_label","piece_rule.pawn_long",("pawn_fast_move_before_enemy_territory","pawn_backward_at_base","pawn_full_movement_at_base","pawn_resurrection","pawn_promotion")),
            PieceType.GUARD:("piece.guard_label","piece_rule.guard_long",()),
            PieceType.ARCHER:("piece.archer_label","piece_rule.archer_long",("archer_enhanced_mode",)),
            PieceType.THUNDER:("piece.thunder_label","piece_rule.thunder_long",()),
            PieceType.ARMOR:("piece.armor_label","piece_rule.armor_long",()),
            PieceType.ASSASSIN:("piece.assassin_label","piece_rule.assassin_long",()),
            PieceType.SHIELD:("piece.shield_label","piece_rule.shield_long",()),
            PieceType.PATROL:("piece.patrol_label","piece_rule.patrol_long",()),
        }
        content=QWidget();content_layout=QVBoxLayout(content);self.piece_groups={}
        for kind,(title_key,description_key,rules) in piece_definitions.items():
            group=QGroupBox(t(title_key, self.language));group_layout=QVBoxLayout(group);self.piece_groups[kind]=group
            detail=QLabel(t(description_key, self.language));detail.setWordWrap(True);detail.setStyleSheet("color:#6f6254");group_layout.addWidget(detail)
            appear_key=f"{kind.value}_appear";appear=QCheckBox(t("settings.piece_appear", self.language))
            appear.setChecked(bool(getattr(options,appear_key)));self.checks[appear_key]=appear;group_layout.addWidget(appear)
            for key in rules:
                check=QCheckBox(t(f"rule.{key}_short", self.language));check.setChecked(bool(getattr(options,key)));self.checks[key]=check;group_layout.addWidget(check)
            content_layout.addWidget(group)
        content_layout.addStretch()
        self.checks["king_appear"].setChecked(True);self.checks["king_appear"].setEnabled(False)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(content);tabs.addTab(scroll,t("settings.piece_rules_tab", self.language))
        self.profile.currentIndexChanged.connect(self._profile_changed);self._update_piece_availability()
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(t("action.confirm", self.language));buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(t("action.cancel", self.language))
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);layout.addWidget(buttons)

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
        previous=self.parent().config if self.parent() else {}
        return {"profile":self.profile.currentData(),"language":self.language_select.currentData(),"game_mode":self.game_mode.currentData(),"difficulty":self.difficulty.currentData(),"human_color":self.color.currentData(),"first_move":self.first_move.currentData(),"initial_minutes":self.minutes.value(),"countdown_seconds":self.countdown.currentData(),"sound":self.sound.isChecked(),"music":self.music.isChecked(),"music_style":self.music_style.currentData(),"sound_volume":self.sound_volume.value(),"music_volume":self.music_volume.value(),"theme":self.theme.currentData(),"font":self.font.currentData(),"background":self.background.currentData(),"piece_style":self.piece_style.currentData(),"flipped":previous.get("flipped",False),"setup_slots":previous.get("setup_slots",{}),"account_token":previous.get("account_token",""),"animations":self.animations.isChecked(),"selection_highlight":self.selection_highlight.isChecked(),"legal_targets":self.legal_targets.isChecked(),"capture_hints":self.capture_hints.isChecked(),"autosave":self.autosave.isChecked(),"server_url":previous.get("server_url","http://127.0.0.1:8000"),"rule_options":values}


class HandicapDialog(QDialog):
    def __init__(self, profile_id: str, options: dict, selected: dict | None = None, parent=None):
        super().__init__(parent);self.setWindowTitle("登场棋子配置");self.resize(720,620)
        profile=PROFILES[profile_id];active=profile.options.merged(options);slots=profile_slots(profile,active)
        defaults={color:[slot["id"] for slot in slots if slot["color"]==color] for color in ("red","black")}
        self.selected={color:list((selected or {}).get(color,defaults[color])) for color in defaults};self.checks={}
        layout=QVBoxLayout(self);note=QLabel("双方登场数量必须相同，主帅固定登场。");layout.addWidget(note)
        columns=QHBoxLayout();layout.addLayout(columns,1)
        for color,title in (("red","红方"),("black","黑方")):
            group=QGroupBox(title);group_layout=QVBoxLayout(group);scroll=QScrollArea();scroll.setWidgetResizable(True);content=QWidget();items=QVBoxLayout(content)
            for slot in (item for item in slots if item["color"]==color):
                check=QCheckBox(f"{NAMES[Color(color)][PieceType(slot['type'])]}  {slot['type']}  ({slot['row']+1},{slot['col']+1})");check.setChecked(slot["id"] in self.selected[color]);check.setProperty("slot_id",slot["id"]);check.setProperty("color",color)
                if slot["type"]=="king":check.setChecked(True);check.setEnabled(False)
                check.toggled.connect(self._update_counts);self.checks[slot["id"]]=check;items.addWidget(check)
            items.addStretch();scroll.setWidget(content);group_layout.addWidget(scroll);columns.addWidget(group)
        self.counts=QLabel();layout.addWidget(self.counts)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Reset)
        lang=(parent.config.get("language","zh-CN") if parent and hasattr(parent,"config") else "zh-CN")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(t("action.confirm", lang));buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(t("action.cancel", lang));buttons.button(QDialogButtonBox.StandardButton.Reset).setText(t("action.reset", lang))
        buttons.accepted.connect(self._accept);buttons.rejected.connect(self.reject);buttons.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(lambda:self._set_all(True));layout.addWidget(buttons);self._update_counts()

    def _set_all(self, checked: bool):
        for check in self.checks.values():check.setChecked(checked)
        self._update_counts()

    def _update_counts(self):
        counts={color:sum(check.isChecked() and check.property("color")==color for check in self.checks.values()) for color in ("red","black")}
        self.counts.setText(f"红方 {counts['red']} 枚 · 黑方 {counts['black']} 枚")

    def _accept(self):
        result=self.value()
        if len(result["red"])!=len(result["black"]):QMessageBox.warning(self,"配置无效","双方登场棋子数量必须相同");return
        self.accept()

    def value(self):
        return {color:[slot_id for slot_id,check in self.checks.items() if check.property("color")==color and check.isChecked()] for color in ("red","black")}


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

        analyze=QPushButton("AI 分析");analyze.clicked.connect(self.show_analysis);controls.insertWidget(0,analyze)

    def show_analysis(self):
        game=Game.from_state(self.snapshots[-1].clone(),self.options);game._snapshots=[item.to_dict() for item in self.snapshots[:-1]]
        result=analyze_game(game,Difficulty.BEGINNER,40);labels={"best":"最佳","good":"良好","inaccuracy":"欠准","mistake":"失误","blunder":"严重失误"}
        lines=["  ".join(f"{labels[key]} {value}" for key,value in result["summary"].items()),""]
        lines.extend(f"{item['ply']}. {item['notation']}  · {labels[item['quality']]}  · 损失 {item['scoreLoss']}" for item in result["moves"])
        DocumentDialog("AI 棋局分析","\n".join(lines),self).exec()

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


class TrainingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent);self.setWindowTitle("残局与排局训练");self.resize(760,560);self.selected_game=None
        layout=QVBoxLayout(self);filters=QHBoxLayout();self.level=QComboBox();self.level.addItem("入门","beginner");self.level.addItem("进阶","advanced");self.level.addItem("大师","master");filters.addWidget(self.level);import_button=QPushButton("导入题库");import_button.clicked.connect(self.import_puzzles);filters.addWidget(import_button);layout.addLayout(filters)
        self.list=QListWidget();self.list.itemDoubleClicked.connect(lambda _:self.start_selected());layout.addWidget(self.list,1)
        actions=QHBoxLayout();self.hint=QPushButton("步骤提示");self.hint.clicked.connect(self.show_hint);start=QPushButton("开始训练");start.clicked.connect(self.start_selected);close=QPushButton("关闭");close.clicked.connect(self.reject);actions.addWidget(self.hint);actions.addStretch();actions.addWidget(start);actions.addWidget(close);layout.addLayout(actions)
        self.level.currentIndexChanged.connect(self.reload);self.puzzles=[];self.reload()

    def reload(self):
        self.puzzles=[item for item in load_puzzles() if item.difficulty==self.level.currentData()];self.list.clear()
        for puzzle in self.puzzles:self.list.addItem(f"{puzzle.title}  ·  {puzzle.description}")

    def current(self):
        row=self.list.currentRow();return self.puzzles[row] if 0<=row<len(self.puzzles) else None

    def show_hint(self):
        puzzle=self.current();QMessageBox.information(self,"步骤提示",puzzle.hints[0] if puzzle and puzzle.hints else "请先选择习题")

    def start_selected(self):
        puzzle=self.current()
        if puzzle:self.selected_game=game_from_document(puzzle.document);self.accept()

    def import_puzzles(self):
        path,_=QFileDialog.getOpenFileName(self,"导入题库","","JSON (*.json)")
        if path:QMessageBox.information(self,"题库导入","外部题库文件已选择；服务端题库接口可将其合并为共享题库。")


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
        layout=QVBoxLayout(self);browser=QTextBrowser();browser.setHtml(content) if content.lstrip().startswith("<") else browser.setMarkdown(content);layout.addWidget(browser)
        lang=getattr(parent,"config",{}).get("language","zh-CN") if parent else "zh-CN"
        close=QPushButton(t("common.close", lang));close.clicked.connect(self.accept);layout.addWidget(close)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__();load_bundled_fonts();self.config=load_config();self.game=None;self.cancel=threading.Event();self.pool=QThreadPool.globalInstance();self.network=None;self.network_base=None;self.room_id=None;self.token=None;self.revision=0;self.spectator=False;self.network_reconnect_attempts=0;self.network_closing=False;self._handled_draw_offer=None;self._handled_undo_offer=None;self.audio=DesktopAudio();self._stats_recorded=False;self._autosaved=False
        self.setWindowTitle(t("app.name", self.config.get("language", "zh-CN")))
        icon_path = Path(__file__).resolve().parent / "resources" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1260,850);self.setMinimumSize(760,560);self._build();self.new_game()
        self.audio.configure(self.config);self.apply_appearance()
        self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(250)

    def _build(self):
        lang=self.config.get("language","zh-CN")
        file_menu = self.menuBar().addMenu(t("menu.file", lang))
        for title, callback, shortcut in ((t("menu.import_game", lang),self.import_game,"Ctrl+O"),(t("menu.export_game", lang),self.export_game,"Ctrl+S")):
            action=QAction(title,self);action.triggered.connect(callback)
            if shortcut:action.setShortcut(QKeySequence(shortcut))
            file_menu.addAction(action)
        file_menu.addSeparator();library=QAction(t("panel.local_replay_library", lang),self);library.triggered.connect(self.show_game_library);file_menu.addAction(library);autosaves=QAction("打开自动保存目录" if lang!="en" else "Open autosave folder",self);autosaves.triggered.connect(self.open_autosave_folder);file_menu.addAction(autosaves)
        game_menu = self.menuBar().addMenu(t("menu.game", lang))
        ai_game=QAction(t("mode.ai", lang),self);ai_game.triggered.connect(lambda:self.start_mode("ai"));game_menu.addAction(ai_game)
        local_game=QAction(t("mode.local_full", lang),self);local_game.triggered.connect(lambda:self.start_mode("local"));game_menu.addAction(local_game);game_menu.addSeparator()
        for title, callback, shortcut in ((t("menu.new", lang),self.new_game,"Ctrl+N"),(t("menu.undo", lang),self.undo_move,"Ctrl+Z"),(t("menu.pause_resume", lang),self.toggle_pause,"Ctrl+P")):
            action=QAction(title,self);action.triggered.connect(callback);action.setShortcut(QKeySequence(shortcut));game_menu.addAction(action)
        game_menu.addSeparator()
        for title, callback in ((t("action.resign", lang),self.resign_game),(t("action.draw", lang),self.draw_game),(t("action.resurrect", lang),self.resurrect_pawn)):
            action=QAction(title,self);action.triggered.connect(callback);game_menu.addAction(action)
        game_menu.addSeparator()
        for title, callback in (("登场棋子配置",self.configure_handicap),("创建局域网房间", self.create_online), ("加入局域网房间", self.join_online),("观战局域网房间",self.spectate_online)):
            action = QAction(title, self); action.triggered.connect(callback); game_menu.addAction(action)
        replay_menu=self.menuBar().addMenu(t("menu.replay", lang))
        replay=QAction(t("menu.enter_replay", lang),self);replay.setShortcut(QKeySequence("Ctrl+R"));replay.triggered.connect(self.replay_game);replay_menu.addAction(replay)
        library_replay=QAction(t("panel.local_replay_library", lang),self);library_replay.triggered.connect(self.show_game_library);replay_menu.addAction(library_replay)
        training=QAction("残局与排局训练",self);training.triggered.connect(self.show_training);replay_menu.addAction(training)
        view_menu=self.menuBar().addMenu(t("menu.view", lang))
        fullscreen=QAction(t("menu.fullscreen", lang),self);fullscreen.setShortcut(QKeySequence("F11"));fullscreen.triggered.connect(self.toggle_fullscreen);view_menu.addAction(fullscreen)
        panels=QAction(t("menu.toggle_panels", lang),self);panels.triggered.connect(self.toggle_panels);view_menu.addAction(panels)
        flip=QAction("翻转棋盘",self);flip.setShortcut(QKeySequence("F"));flip.triggered.connect(self.flip_board);view_menu.addAction(flip)
        settings_menu = self.menuBar().addMenu(t("menu.settings", lang))
        settings_action = QAction(t("settings.desktop_title", lang), self); settings_action.triggered.connect(self.settings); settings_menu.addAction(settings_action);settings_menu.addSeparator()
        stats=QAction("对局统计" if lang!="en" else "Statistics",self);stats.triggered.connect(self.show_statistics);settings_menu.addAction(stats)
        account=QAction("账号与云同步",self);account.triggered.connect(self.account_sync);settings_menu.addAction(account)
        help_menu=self.menuBar().addMenu(t("menu.help", lang))
        guide=QAction(t("menu.guide", lang),self);guide.setShortcut(QKeySequence("F1"));guide.triggered.connect(self.show_help);help_menu.addAction(guide)
        rules=QAction(t("menu.piece_rules", lang),self);rules.triggered.connect(self.show_rules);help_menu.addAction(rules)
        help_menu.addSeparator()
        about=QAction(t("menu.about", lang),self);about.triggered.connect(self.show_about);help_menu.addAction(about)
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
        side_tabs.addTab(record_page,t("panel.moves", lang));side_tabs.addTab(chat_page,t("panel.chat", lang));right.addWidget(side_tabs,1);right.addWidget(QLabel("阵亡子力" if lang!="en" else "Captured pieces"));right.addWidget(self.captured)
        actions=QGridLayout();self.undo=QPushButton(t("action.undo", lang));self.undo.clicked.connect(self.undo_move);self.pause=QPushButton(t("action.pause", lang));self.pause.clicked.connect(self.toggle_pause);self.resign=QPushButton(t("action.resign", lang));self.resign.clicked.connect(self.resign_game);self.draw=QPushButton(t("action.draw", lang));self.draw.clicked.connect(self.draw_game);self.resurrect=QPushButton(t("action.resurrect", lang));self.resurrect.clicked.connect(self.resurrect_pawn)
        self.flip=QPushButton("↕ 翻转");self.flip.clicked.connect(self.flip_board)
        for i,b in enumerate((self.undo,self.pause,self.resign,self.draw,self.resurrect,self.flip)):actions.addWidget(b,i//2,i%2)
        right.addLayout(actions);split.addWidget(self.side);split.setSizes([850,300])
        self.apply_appearance()

    def new_game(self):
        self.close_network();self.cancel.set();self.cancel=threading.Event();self.game=Game(self.config["profile"],self.config.get("rule_options"),self.config["initial_minutes"],self.config.get("language","zh-CN"),self.current_setup());human=Color(self.config["human_color"]);local=self.config.get("game_mode","ai")=="local";self.board.set_game(self.game,human,local);self.configure_board();self.board.locked=False;self._stats_recorded=False;self._autosaved=False;self.refresh();
        if not local and self.game.state.turn is not human:self.start_ai()

    def start_mode(self, mode: str) -> None:
        self.config["game_mode"]=mode;save_config(self.config);self.new_game()

    def human_move(self, move: Move):
        try:
            piece=self.game.state.piece_at(move.source)
            if piece and piece.type is PieceType.PAWN and self.game.options.pawn_promotion and move.target.row in {0,self.game.profile.rows-1}:
                choices={p.type for p in self.game.state.captured[piece.color] if p.type not in {PieceType.PAWN,PieceType.KING} and p.type in self.game.rules.enabled_piece_types}
                if choices:
                    options=[(NAMES[piece.color][kind],kind) for kind in sorted(choices,key=lambda item:item.value)]
                    label,ok=QInputDialog.getItem(self,"兵卒升变","选择升变棋子",[item[0] for item in options],0,False)
                    if not ok:return
                    move=Move(move.source,move.target,next(kind for text,kind in options if text==label))
            if self.network:
                self.send_network("move",{"from":{"row":move.source.row,"col":move.source.col},"to":{"row":move.target.row,"col":move.target.col},"promotion":move.promotion.value if move.promotion else None});return
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
        if dialog.exec():
            self.config=dialog.value();save_config(self.config);self.audio.configure(self.config)
            self.setWindowTitle(t("app.name", self.config.get("language","zh-CN")))
            self.menuBar().clear()
            old=self.centralWidget()
            if old:old.deleteLater()
            self._build();self.new_game()

    def apply_appearance(self):
        if not hasattr(self,"board"):return
        theme=THEMES.get(self.config.get("theme","classic"),THEMES["classic"]);font=FONT_CHOICES.get(self.config.get("font","system"),UI_FONT)
        QApplication.instance().setFont(QFont(font,10));self.configure_board()
        text="#f3ead7" if self.config.get("theme")=="dark" else "#211b17"
        hover="#4a433b" if self.config.get("theme")=="dark" else "#f1dfbf"
        self.setStyleSheet(f"""QMainWindow,#root{{background:{theme['window']};color:{text}}}QMenuBar,QMenu,QToolBar{{background:{theme['panel']};color:{text};border-bottom:1px solid {theme['line']};padding:5px}}#banner{{background:{theme['accent']};color:white;padding:8px;font-weight:bold;font-size:15px}}QListWidget,QLabel,QFrame,QGroupBox,QComboBox,QSpinBox,QLineEdit{{background:{theme['panel']};color:{text};border:1px solid {theme['line']};padding:7px}}QPushButton{{min-height:35px;background:{theme['panel']};color:{text};border:1px solid {theme['line']}}}QPushButton:hover{{background:{hover}}}""")

    def configure_board(self):
        self.board.language=self.config.get("language","zh-CN")
        self.board.set_appearance(self.config.get("theme","classic"),str(self.config.get("background","none")),self.config.get("piece_style","traditional"))
        self.board.set_assists(selection=self.config.get("selection_highlight",True),legal_targets=self.config.get("legal_targets",True),capture_hints=self.config.get("capture_hints",True),animations=self.config.get("animations",True))
        self.board.set_flipped(self.config.get("flipped",False))

    def current_setup(self):
        selected=self.config.get("setup_slots",{}).get(self.config["profile"],{})
        return {"firstMove":self.config.get("first_move","red"),"redSlots":selected.get("red"),"blackSlots":selected.get("black")}

    def configure_handicap(self):
        selected=self.config.get("setup_slots",{}).get(self.config["profile"])
        dialog=HandicapDialog(self.config["profile"],self.config.get("rule_options",{}),selected,self)
        if dialog.exec():self.config.setdefault("setup_slots",{})[self.config["profile"]]=dialog.value();save_config(self.config);self.new_game()

    def flip_board(self):
        self.config["flipped"]=not self.config.get("flipped",False);save_config(self.config);self.board.set_flipped(self.config["flipped"])

    def show_training(self):
        dialog=TrainingDialog(self)
        if dialog.exec() and dialog.selected_game:
            self.close_network();self.game=dialog.selected_game;self.config["profile"]=self.game.profile.id;self.config["game_mode"]="local";self.board.set_game(self.game,Color.RED,True);self.configure_board();self.refresh()

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
        lang=self.config.get("language","zh-CN")
        stats=load_statistics();rate=(stats["wins"]*100/stats["games"]) if stats["games"] else 0
        box=QMessageBox(self);box.setWindowTitle("对局统计" if lang!="en" else "Statistics");box.setText(f"{t('statistics.total_games', lang)}：{stats['games']}\n{t('statistics.wins', lang)}：{stats['wins']}  {t('statistics.losses', lang)}：{stats['losses']}  {t('statistics.draws', lang)}：{stats['draws']}\n{t('statistics.moves', lang)}：{stats['moves']}\n{t('statistics.win_rate', lang)}：{rate:.1f}%");reset=box.addButton(t("action.reset_statistics", lang),QMessageBox.ButtonRole.DestructiveRole);box.addButton(QMessageBox.StandardButton.Close);box.exec()
        if box.clickedButton() is reset and QMessageBox.question(self,"确认" if lang!="en" else "Confirm",t("dialog.confirm_reset_stats", lang))==QMessageBox.StandardButton.Yes:reset_statistics()

    def show_rules(self):
        lang=self.config.get("language","zh-CN")
        if lang=="en":
            DocumentDialog(t("dialog.rules_title", lang),t("docs.rules", lang),self).exec();return
        path=Path(__file__).resolve().parent / "resources" / "docs" / "PIECE_RULES.md"
        try:content=path.read_text(encoding="utf-8")
        except OSError as exc:content=f"规则文档读取失败：{exc}"
        DocumentDialog(t("dialog.rules_title", lang),content,self).exec()

    def show_help(self):
        lang=self.config.get("language","zh-CN")
        if lang=="en":
            DocumentDialog(t("dialog.help_title", lang),t("docs.help", lang),self).exec();return
        path=Path(__file__).resolve().parent / "resources" / "docs" / "HELP.md"
        try:content=path.read_text(encoding="utf-8")
        except OSError as exc:content=f"帮助文档读取失败：{exc}"
        DocumentDialog(t("dialog.help_title", lang),content,self).exec()

    def show_about(self):
        lang=self.config.get("language","zh-CN")
        if lang=="en":
            DocumentDialog(t("dialog.about_title", lang),t("docs.about", lang),self).exec();return
        path=Path(__file__).resolve().parent / "resources" / "docs" / "ABOUT.md"
        try:content=path.read_text(encoding="utf-8")
        except OSError as exc:content=f"关于文档读取失败：{exc}"
        DocumentDialog(t("dialog.about_title", lang),content,self).exec()

    def account_sync(self):
        base=self.config.get("server_url","http://127.0.0.1:8000").rstrip("/");token=self.config.get("account_token","")
        try:
            if not token:
                mode,ok=QInputDialog.getItem(self,"账号","选择操作",["登录","注册"],0,False)
                if not ok:return
                username,ok=QInputDialog.getText(self,"账号","用户名")
                if not ok:return
                password,ok=QInputDialog.getText(self,"账号","密码",QLineEdit.EchoMode.Password)
                if not ok:return
                display=username
                if mode=="注册":display,_=QInputDialog.getText(self,"账号","显示名称",QLineEdit.EchoMode.Normal,username)
                data=self.request_json(base+("/api/auth/register" if mode=="注册" else "/api/auth/login"),{"username":username,"password":password,"displayName":display},"POST")
                cloud_to_desktop={"boardTheme":"theme","pageBackground":"background","pieceStyle":"piece_style","font":"font","language":"language","flipped":"flipped","musicStyle":"music_style","volume":"sound_volume","animation":"animations","selection":"selection_highlight","legalTargets":"legal_targets","captureHints":"capture_hints","autosave":"autosave","initialMinutes":"initial_minutes","countdownSeconds":"countdown_seconds"}
                self.config["account_token"]=data["token"]
                for cloud_key,value in data.get("preferences",{}).items():
                    local_key=cloud_to_desktop.get(cloud_key,cloud_key)
                    if local_key in self.config:self.config[local_key]=value
                save_config(self.config);QMessageBox.information(self,"账号",f"已登录：{data['account']['displayName']}");return
            action,ok=QInputDialog.getItem(self,"云同步","选择操作",["上传当前棋局","同步外观偏好","查看云端棋谱","退出登录"],0,False)
            if not ok:return
            if action=="退出登录":self.request_json(base+"/api/auth/logout",{},"POST",token);self.config["account_token"]="";save_config(self.config);return
            if action=="上传当前棋局":
                if not self.game:return
                self.request_json(base+"/api/me/games",{"document":game_document(self.game),"title":f"{self.game.profile.title} · {len(self.game.state.history)} 手"},"POST",token);QMessageBox.information(self,"云同步","当前棋局已上传")
            elif action=="同步外观偏好":
                mapping={"boardTheme":"theme","pageBackground":"background","pieceStyle":"piece_style","font":"font","language":"language","flipped":"flipped","musicStyle":"music_style","volume":"sound_volume","animation":"animations","selection":"selection_highlight","legalTargets":"legal_targets","captureHints":"capture_hints","autosave":"autosave","initialMinutes":"initial_minutes","countdownSeconds":"countdown_seconds"}
                preferences={cloud:self.config.get(local) for cloud,local in mapping.items()};self.request_json(base+"/api/me/preferences",{"preferences":preferences},"PUT",token);QMessageBox.information(self,"云同步","偏好设置已同步")
            else:
                games=self.request_json(base+"/api/me/games",None,"GET",token);DocumentDialog("云端棋谱","\n".join(f"{item['title']} · {'已收藏' if item['favorite'] else '未收藏'}" for item in games) or "暂无云端棋谱",self).exec()
        except Exception as exc:QMessageBox.warning(self,"云同步失败",str(exc))

    @staticmethod
    def request_json(url,payload=None,method="GET",token=""):
        headers={"Content-Type":"application/json"}
        if token:headers["Authorization"]=f"Bearer {token}"
        body=json.dumps(payload).encode("utf-8") if payload is not None else None
        request=urllib.request.Request(url,body,headers,method=method)
        with urllib.request.urlopen(request,timeout=15) as response:return json.loads(response.read().decode("utf-8"))

    def server_base(self) -> str | None:
        lang=self.config.get("language","zh-CN")
        value,ok=QInputDialog.getText(self,"服务器地址" if lang!="en" else "Server URL","FastAPI 服务地址" if lang!="en" else "FastAPI server URL",QLineEdit.EchoMode.Normal,self.config.get("server_url","http://127.0.0.1:8000"))
        if not ok:return None
        self.config["server_url"]=value.rstrip("/");save_config(self.config);return self.config["server_url"]

    def create_online(self):
        base=self.server_base()
        if not base:return
        try:
            setup=self.current_setup();data=self.http_json(base+"/api/rooms",{"profileId":self.config["profile"],"mode":"online","playerName":"桌面玩家" if self.config.get("language")!="en" else "Desktop Player","playerColor":self.config["human_color"],"options":self.config.get("rule_options",{}),"initialMinutes":self.config["initial_minutes"],"language":self.config.get("language","zh-CN"),"firstMove":setup["firstMove"],"redSlots":setup["redSlots"],"blackSlots":setup["blackSlots"]})
            self.open_network(base,data)
            lang=self.config.get("language","zh-CN");QMessageBox.information(self,"房间已创建" if lang!="en" else "Room created",f"{'房间号' if lang!='en' else 'Room code'}：{data['roomId']}")
        except Exception as exc:QMessageBox.warning(self,"创建失败" if self.config.get("language")!="en" else "Create failed",str(exc))

    def join_online(self):
        base=self.server_base()
        if not base:return
        lang=self.config.get("language","zh-CN")
        room,ok=QInputDialog.getText(self,"加入房间" if lang!="en" else "Join room","房间号" if lang!="en" else "Room code")
        if not ok or not room:return
        try:self.open_network(base,self.http_json(f"{base}/api/rooms/{room.strip().upper()}/join",{"playerName":"桌面玩家" if lang!="en" else "Desktop Player","language":lang}))
        except Exception as exc:QMessageBox.warning(self,"加入失败" if lang!="en" else "Join failed",str(exc))

    def spectate_online(self):
        base=self.server_base()
        if not base:return
        room,ok=QInputDialog.getText(self,"观战房间","房间号")
        if not ok or not room:return
        try:self.open_network(base,self.http_json(f"{base}/api/rooms/{room.strip().upper()}/spectate",{"displayName":"桌面观众"}),True)
        except Exception as exc:QMessageBox.warning(self,"观战失败",str(exc))

    @staticmethod
    def http_json(url,payload):
        request=urllib.request.Request(url,json.dumps(payload).encode("utf-8"),{"Content-Type":"application/json"},method="POST")
        with urllib.request.urlopen(request,timeout=8) as response:return json.loads(response.read().decode("utf-8"))

    def open_network(self,base,data,spectator=False):
        self.cancel.set();self.network_base=base;self.room_id=data["roomId"];self.token=data["token"];self.spectator=spectator;self.revision=data["snapshot"]["revision"];self.network_reconnect_attempts=0;self.network_closing=False;self.apply_network_state(data["snapshot"]);self._connect_network()

    def _connect_network(self):
        if not self.room_id or not self.token or not self.network_base:return
        lang=self.config.get("language","zh-CN");suffix="/spectate" if self.spectator else "";ws=self.network_base.replace("https://","wss://",1).replace("http://","ws://",1)+f"/ws/{self.room_id}{suffix}?token={self.token}"
        socket=QWebSocket();self.network=socket;socket.textMessageReceived.connect(self.network_message);socket.connected.connect(lambda:self._network_connected(socket));socket.disconnected.connect(lambda:self._network_disconnected(socket));socket.open(QUrl(ws));self.statusBar().showMessage(f"{'房间' if lang!='en' else 'Room'} {self.room_id} · {'正在连接' if lang!='en' else 'Connecting'}")

    def _network_connected(self,socket):
        if socket is not self.network:return
        self.network_reconnect_attempts=0;lang=self.config.get("language","zh-CN");self.statusBar().showMessage("网络已恢复" if lang!="en" else "Network restored",5000)

    def _network_disconnected(self,socket):
        if socket is not self.network:return
        code=int(socket.closeCode());socket.deleteLater();self.network=None;lang=self.config.get("language","zh-CN")
        if self.network_closing or not self.room_id or code in {4001,4403,1008}:
            self.statusBar().showMessage("网络已断开" if lang!="en" else "Network disconnected");return
        if self.network_reconnect_attempts>=3:
            self.statusBar().showMessage("自动重连失败，请重新加入房间" if lang!="en" else "Reconnect failed; join the room again");return
        delay=min(8000,1200*(2**self.network_reconnect_attempts));self.network_reconnect_attempts+=1;self.statusBar().showMessage(f"{'网络中断，正在重连' if lang!='en' else 'Disconnected, reconnecting'} ({self.network_reconnect_attempts}/3)");QTimer.singleShot(delay,self._connect_network)

    def network_message(self,text):
        message=json.loads(text)
        lang=self.config.get("language","zh-CN")
        if message["type"]=="error":QMessageBox.warning(self,"服务器拒绝" if lang!="en" else "Server rejected",message["payload"]["message"]);self.apply_network_state(message["payload"].get("state",{}))
        elif message["type"]=="chat":
            payload=message["payload"];self.chat_messages.addItem(f"{payload.get('sender','玩家')}：{payload.get('text','')}");self.chat_messages.scrollToBottom()
        elif message["type"]=="state":
            snapshot=message["payload"];game_data=snapshot["game"]
            self.apply_network_state(snapshot)
            draw_key=(game_data.get("pendingDrawOffer"),len(game_data.get("history",[])))
            if draw_key[0] and draw_key[0]!=self.config["human_color"] and draw_key!=self._handled_draw_offer:self._handled_draw_offer=draw_key;self.send_network("draw_response",{"accept":QMessageBox.question(self,t("action.draw", lang),t("dialog.pending_draw", lang))==QMessageBox.StandardButton.Yes})
            undo_key=(game_data.get("pendingUndoOffer"),len(game_data.get("history",[])))
            if undo_key[0] and undo_key[0]!=self.config["human_color"] and undo_key!=self._handled_undo_offer:self._handled_undo_offer=undo_key;self.send_network("undo_response",{"accept":QMessageBox.question(self,t("action.undo", lang),t("dialog.pending_undo", lang))==QMessageBox.StandardButton.Yes})

    def apply_network_state(self,snapshot):
        if not snapshot:return
        game_data=snapshot["game"];self.revision=snapshot["revision"];self.config["human_color"]=snapshot.get("youAre") or self.config["human_color"];self.game=Game.from_state(GameState.from_dict(game_data),game_data["profile"]["options"],game_data.get("setup"));replay=game_data.get("replay",[]);self.game._snapshots=[item for item in replay[:-1] if isinstance(item,dict)];self.board.set_game(self.game,Color(self.config["human_color"]),False);self.board.interactive=not self.spectator;self.configure_board();self.board.locked=False
        if not self.game.state.history:self._stats_recorded=False;self._autosaved=False
        lang=self.config.get("language","zh-CN")
        self.statusBar().showMessage(f"{'房间' if lang!='en' else 'Room'} {snapshot['roomId']} · {'状态版本' if lang!='en' else 'revision'} {self.revision}");self.refresh()

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
        self.network_closing=True;socket=self.network;self.network=None;self.room_id=None;self.token=None;self.network_base=None;self.spectator=False;self.network_reconnect_attempts=0
        if socket:socket.close();socket.deleteLater()
        if hasattr(self,"board"):self.board.interactive=True

    def refresh(self):
        if not self.game:return
        if not self.network:self.game.tick()
        lang=self.config.get("language","zh-CN")
        state=self.game.state;self.banner.setText(t("status.game_over", lang) if state.finished else (t("status.paused", lang) if state.paused else t("status.turn", lang, color=t("common.red" if state.turn is Color.RED else "common.black", lang))))
        self.red.setText(f"{t('common.red', lang)}  {self._clock(state.clocks_ms[Color.RED])}");self.black.setText(f"{t('common.black', lang)}  {self._clock(state.clocks_ms[Color.BLACK])}")
        threshold=max(0,int(self.config.get("countdown_seconds",30)))*1000
        self.red.setStyleSheet("color:#b21f1f;font-weight:bold" if threshold and state.clocks_ms[Color.RED]<=threshold and not state.paused else "")
        self.black.setStyleSheet("color:#b21f1f;font-weight:bold" if threshold and state.clocks_ms[Color.BLACK]<=threshold and not state.paused else "")
        self.history.clear();self.history.addItems([r.notation for r in state.history]);self.captured.setText(f"{t('common.red', lang)}："+" ".join(NAMES[p.color][p.type] for p in state.captured[Color.RED])+f"\n{t('common.black', lang)}："+" ".join(NAMES[p.color][p.type] for p in state.captured[Color.BLACK]));self.board.update()
        self.pause.setText(t("action.resume" if state.paused else "action.pause", lang));self.pause.setEnabled(not state.finished);self.undo.setEnabled(bool(state.history) and not state.paused);self.draw.setEnabled(not state.finished and not state.paused);self.resign.setEnabled(not state.finished);self.resurrect.setEnabled(not state.finished and not state.paused)
        if state.finished and not self._stats_recorded:record_result(self.game,self.config["human_color"]);self._stats_recorded=True
        if state.finished and self.config.get("autosave",True) and not self._autosaved:
            try:path=autosave_game(self.game);self.statusBar().showMessage(("棋谱已自动保存：" if lang!="en" else "Replay auto-saved: ")+f"{path}",8000)
            except OSError as exc:self.statusBar().showMessage(("自动保存失败：" if lang!="en" else "Auto-save failed: ")+f"{exc}",8000)
            self._autosaved=True
        if state.finished and not getattr(self,"_shown_result",False):self._shown_result=True;winner=t("result.draw", lang) if state.draw else t("result.victory", lang, color=t("common.red" if state.winner is Color.RED else "common.black", lang));QMessageBox.information(self,t("dialog.result_title", lang),winner)
        if not state.finished:self._shown_result=False

    @staticmethod
    def _clock(ms):seconds=max(0,ms//1000);return f"{seconds//60:02d}:{seconds%60:02d}"

    def closeEvent(self,event):self.cancel.set();self.close_network();self.audio.stop();save_config(self.config);super().closeEvent(event)


def run() -> None:
    app=QApplication(sys.argv);app.setApplicationName(t("app.name"))
    icon_path=Path(__file__).resolve().parent / "resources" / "icon.ico"
    if icon_path.exists():app.setWindowIcon(QIcon(str(icon_path)))
    load_bundled_fonts();window=MainWindow();window.show();sys.exit(app.exec())


if __name__ == "__main__":run()
