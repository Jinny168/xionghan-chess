"""棋子图谱（QDialog）：三风格美术对比 + 单子规则速查 + 即时切换。

## 为什么单独开一个窗口

玩家要回答三个问题，此前一个都答不了：这枚子长什么样（三风格并排）、它怎么走
（中文读 `PIECE_RULES.md` 对应小节，英文读 `piece_rule.*_long`）、它在本档案下
哪几个开关是开的（只读展示 + 一键跳设置）。

## 刻意**不依赖** `game`

窗口只需要「当前档案 + 当前配置」。构造时不碰 `MainWindow.game`，所以：
- 没有对局也能开（首次启动、刚关掉一局）；
- 单元测试可以直接构造，不必先摆一局棋。

## 缩略图**不跟随** `piece_render`

棋盘默认 `piece_render="glyph"`（1.7.0 观感）。若图谱也跟着走字形，三风格缩略图
会几乎一模一样（三个金色圆片），图谱等于没展示；而且甲/刺/楯 用金色底盘、其余用
象牙白位图，同一个窗口里出现两种材质。所以**图谱一律按图片路径画**，只有最后一格
「书法字形」是刻意展示字形回退的样子。

## 即时切换的边界

「使用此风格」只做三件事：写 `config`（`piece_style` + `piece_render="image"`）→
让主窗口 `configure_board()`（内部预热新风格图片）→ 重绘。**不重建界面、不开新局**。
设置页那条「重建菜单 + deleteLater 中央控件 + `_build()`」的路径在这里是错的：
它会把侧栏文本、按钮可用性、棋谱列表全部重来。
"""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QScrollArea, QSizePolicy, QTextBrowser, QVBoxLayout, QWidget,
)

from xionghan_chess.core.model import Color, Piece, PieceType
from xionghan_chess.core.profiles import PROFILES, profile_rule_values
from xionghan_chess.core.rules import RulesEngine
from xionghan_chess.i18n import normalize_language, t

from ..config import save_config
from ..texts import dl
from . import piece_assets, theme
from .board_widget import GLYPH_MODE, IMAGE_MODE, draw_fallback_piece, draw_piece_glyph
from .dialogs import GLYPH_STYLE_DATA, DocumentDialog

# 左侧清单的顺序：先「常规 7 型」（任何档案都有），再「特色 7 型」。
REGULAR_KINDS: tuple[PieceType, ...] = (
    PieceType.KING, PieceType.ROOK, PieceType.HORSE, PieceType.ELEPHANT,
    PieceType.ADVISOR, PieceType.CANNON, PieceType.PAWN,
)
SPECIAL_KINDS: tuple[PieceType, ...] = (
    PieceType.GUARD, PieceType.ARCHER, PieceType.THUNDER,
    PieceType.ASSASSIN, PieceType.PATROL,
)   # 甲/楯已软删，不再进图鉴

# 每型在该档案下会影响它的规则开关（与 `SettingsDialog` 的棋子分组成员一致）。
PIECE_OPTION_KEYS: dict[PieceType, tuple[str, ...]] = {
    PieceType.KING: ("king_can_leave_palace", "king_diagonal_in_palace",
                     "king_lose_diagonal_outside_palace", "invasion_victory"),
    PieceType.ROOK: (),
    PieceType.HORSE: ("horse_straight_three",),
    PieceType.ELEPHANT: ("elephant_can_cross_river", "elephant_gain_jump_two_enemy_territory"),
    PieceType.ADVISOR: ("advisor_can_leave_palace", "advisor_gain_straight_outside_palace"),
    PieceType.CANNON: (),
    PieceType.PAWN: ("pawn_fast_move_before_enemy_territory", "pawn_charge",
                     "pawn_three_line_capture", "pawn_backward_at_base",
                     "pawn_full_movement_at_base", "pawn_resurrection", "pawn_promotion"),
    PieceType.GUARD: (),
    PieceType.ARCHER: ("archer_enhanced_mode",),
    PieceType.THUNDER: (),
    PieceType.ASSASSIN: (),
    PieceType.PATROL: (),
}

# 缩略图逻辑边长：**单值 72**，这里给的是**盘径**（图片已裁掉留白）。
# 曾经有 80 的大窗档，但 80×2（200% DPI）÷ 源盘径 137 = **1.17× 上采样**，
# 越过我们给棋盘定的「>1.15 记已知缺陷」那条线；72×2 ÷ 137 = 1.05×，
# 任何 DPI 下都≈1:1。72 在格宽 97 下仍有 25 px 净间隙，不挤。
THUMB = 72
# 「去规则设置调整」要跳到设置里的「棋子与规则」tab（第 3 个）。
PIECE_RULES_TAB = 2


def _draw_glyph_badge(painter: QPainter, edge: int, text: str) -> None:
    """缺图格左下角的 10px「字」小标：说明这枚子是字形回退，不是美术。"""
    painter.setPen(QColor("#6f6254"))
    painter.setFont(QFont(theme.UI_FONT, 7))
    painter.drawText(int(edge * 0.06), int(edge * 0.94), text)


class PieceAtlasDialog(QDialog):
    def __init__(self, config: dict, parent: QWidget | None = None,
                 apply_style: Callable[[str], None] | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.language = normalize_language(config.get("language"))
        self.profile = PROFILES.get(str(config.get("profile")), PROFILES["desktop_complete"])
        # 用 RulesEngine 而不是 profile.enabled_piece_types：前者已经把每局的
        # 「登场开关」算进去，才能回答「本档案下这枚子到底会不会出现」。
        self.rules = RulesEngine(self.profile, self.profile.options.merged(config.get("rule_options")))
        self._apply_style_cb = apply_style
        self.style = piece_assets.normalize_style(config.get("piece_style"))
        self.kind: PieceType = PieceType.KING
        self.setWindowTitle(t("desktop.piece_atlas", self.language))
        self.resize(900, 640)
        self.setMinimumSize(760, 560)
        self._build()

    # ------------------------------------------------------------------ 布局
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)
        root.addWidget(self._top_bar())
        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._piece_list())
        body.addWidget(self._detail_area(), 1)
        root.addLayout(body, 1)
        root.addWidget(self._bottom_bar())

    def _top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(44)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel(t("desktop.piece_atlas", self.language))
        title.setFont(QFont(theme.UI_FONT, 15, QFont.Weight.Bold))
        layout.addWidget(title)
        layout.addStretch(1)
        group = QButtonGroup(self)
        group.setExclusive(True)
        self._style_buttons: dict[str, QPushButton] = {}
        for style in piece_assets.STYLES:
            button = QPushButton(t(f"option.piece_{style}", self.language))
            button.setCheckable(True)
            button.setChecked(style == self.style)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, value=style: self._preview_style(value))
            group.addButton(button)
            self._style_buttons[style] = button
            layout.addWidget(button)
        self._style_group = group
        return bar

    def _piece_list(self) -> QWidget:
        frame = QFrame()
        frame.setFixedWidth(188)
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 6, 6, 6)
        self._list = QListWidget()
        self._list.setFrameShape(QFrame.Shape.NoFrame)
        for label, kinds in ((dl("常规棋子"), REGULAR_KINDS), (dl("特色棋子"), SPECIAL_KINDS)):
            header = QListWidgetItem(label)
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            header.setForeground(QColor("#8a7b68"))
            self._list.addItem(header)
            for kind in kinds:
                enabled = kind in self.rules.enabled_piece_types
                # 红黑字形对照：漢/汗 这种一眼看出双方的写法差异
                glyphs = f"{theme.NAMES[Color.RED][kind]}/{theme.NAMES[Color.BLACK][kind]}"
                text = f"{glyphs}　{t(f'piece_name.{kind.value}', self.language)}"
                if not enabled:
                    text += "　·　" + t("desktop.atlas_unavailable", self.language)
                item = QListWidgetItem(text)
                # 存字符串而不是 PieceType：`PieceType` 是 StrEnum，经 QVariant
                # 往返后可能变成普通 str，直接拿枚举比较会静默失配。
                item.setData(Qt.ItemDataRole.UserRole, kind.value)
                if not enabled:
                    item.setForeground(QColor("#9b9186"))
                self._list.addItem(item)
        self._list.setCurrentRow(1)
        self._list.currentItemChanged.connect(self._selection_changed)
        layout.addWidget(self._list)
        return frame

    def _detail_area(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._detail = QWidget()
        self._detail_layout = QVBoxLayout(self._detail)
        self._detail_layout.setContentsMargins(0, 0, 0, 0)
        self._detail_layout.setSpacing(10)
        scroll.setWidget(self._detail)
        self._rebuild_detail()
        return scroll

    def _bottom_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(44)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        self.status = QLabel(t("desktop.atlas_hint", self.language))
        self.status.setWordWrap(True)
        self.status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.status, 1)
        # 图谱固定按图片路径展示，与棋盘的 `piece_render` 无关 —— 明说一句，
        # 免得默认（字形）模式下用户以为「点了立刻变」，结果棋盘没动。
        note = QLabel(t("desktop.atlas_image_note", self.language))
        note.setStyleSheet("color:#6f6254")
        layout.addWidget(note)
        close = QPushButton(t("common.close", self.language))
        close.clicked.connect(self.accept)
        layout.addWidget(close)
        return bar

    # ------------------------------------------------------------------ 交互
    def _selection_changed(self, current: QListWidgetItem | None, _previous=None) -> None:
        if current is None:
            return
        value = current.data(Qt.ItemDataRole.UserRole)
        if not isinstance(value, str):
            return
        self.kind = PieceType(value)
        self._rebuild_detail()

    def _preview_style(self, style: str) -> None:
        self.style = piece_assets.normalize_style(style)
        self._rebuild_detail()

    def _is_active(self, choice: str) -> bool:
        """这一格是否就是当前生效的渲染方式（四值互斥，直接比 `piece_style`）。"""
        return self.config.get("piece_style") == choice

    def apply_style(self, choice: str) -> None:
        """「使用此风格」：原地生效，不重开对局、不重建界面。

        `choice == GLYPH_STYLE_DATA`（`"__glyph__"`）表示回到字形渲染，此时
        **不动 `piece_style`** —— 用户下次再选图片风格还是上次挑的那一套。
        """
        glyph = choice == GLYPH_STYLE_DATA
        if glyph:
            self.config["piece_style"] = GLYPH_STYLE_DATA
            self.config["piece_render"] = GLYPH_MODE
        else:
            self.config["piece_style"] = piece_assets.normalize_style(choice)
            self.config["piece_render"] = IMAGE_MODE
            self.style = piece_assets.normalize_style(choice)
        if self._apply_style_cb is not None:
            self._apply_style_cb(choice)
        else:
            save_config(self.config)
        name = (t("desktop.atlas_glyph_mode", self.language) if glyph
                else t(f"option.piece_{choice}", self.language))
        self.status.setText(t("desktop.atlas_switched", self.language, style=name))
        button = self._style_buttons.get(self.style)
        if button is not None and not glyph:
            button.setChecked(True)
        self._rebuild_detail()

    # ------------------------------------------------------------------ 右栏
    def _rebuild_detail(self) -> None:
        while self._detail_layout.count():
            item = self._detail_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._detail_layout.addWidget(self._style_row())
        self._detail_layout.addWidget(self._card_row())
        self._detail_layout.addWidget(self._moves_row())
        self._detail_layout.addWidget(self._rule_state_row())
        self._detail_layout.addStretch(1)

    def _cell_pixmap(self, choice: str, color: Color, edge: int) -> QPixmap:
        """一枚棋子的缩略图（边长 = 盘径）。

        - `choice` 是风格名 → 走**图片**路径；没有美术的棋型（甲/刺/楯）用
          `draw_fallback_piece()` 画同风格底盘 + 统一衬线字形，并加「字」标。
        - `choice == GLYPH_STYLE_DATA` → 展示「书法字形」的样子（`piece_render="glyph"`）。
        """
        if choice == GLYPH_STYLE_DATA:
            canvas = QPixmap(edge, edge)
            canvas.fill(Qt.GlobalColor.transparent)
            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            draw_piece_glyph(painter, QPointF(edge / 2, edge / 2), edge / 2,
                             Piece.create(self.kind, color, 0, 0), self.style)
            painter.end()
            return canvas
        artwork = piece_assets.pixmap(choice, color, self.kind, round(edge * self.devicePixelRatioF()))
        if artwork is not None:
            return artwork
        canvas = QPixmap(edge, edge)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_fallback_piece(painter, QPointF(edge / 2, edge / 2), edge / 2,
                            color, self.kind, choice)
        _draw_glyph_badge(painter, edge, dl("字"))
        painter.end()
        return canvas

    def _style_row(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._heading(t("settings.piece_style", self.language)))
        row = QHBoxLayout()
        row.setSpacing(12)
        edge = THUMB
        for choice in (GLYPH_STYLE_DATA, *piece_assets.STYLES):
            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(4)
            preview = QLabel()
            preview.setPixmap(self._cell_pixmap(choice, Color.RED, edge))
            preview.setFixedSize(edge, edge)
            preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell_layout.addWidget(preview, 0, Qt.AlignmentFlag.AlignHCenter)
            if choice == GLYPH_STYLE_DATA:
                name = QLabel(t("desktop.atlas_glyph_mode", self.language))
            else:
                name = QLabel(t(f"option.piece_{choice}", self.language))
            name.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            cell_layout.addWidget(name)
            if choice != GLYPH_STYLE_DATA and piece_assets.preload(choice) == 0:
                note = QLabel(t("desktop.atlas_missing_asset", self.language))
            elif choice != GLYPH_STYLE_DATA and piece_assets.resolve(choice, Color.RED, self.kind) is None:
                note = QLabel(t("desktop.atlas_glyph_fallback", self.language))
            else:
                note = None
            if note is not None:
                note.setWordWrap(True)
                note.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                cell_layout.addWidget(note)
            else:
                cell_layout.addWidget(QLabel(""))
            button = QPushButton()
            if self._is_active(choice):
                button.setText(t("desktop.atlas_in_use", self.language))
                button.setEnabled(False)
            else:
                button.setText(t("desktop.atlas_use_style", self.language))
                button.setEnabled(choice == GLYPH_STYLE_DATA or piece_assets.preload(choice) > 0)
                button.clicked.connect(lambda _checked=False, value=choice: self.apply_style(value))
            cell_layout.addWidget(button)
            row.addWidget(cell)
        row.addStretch(1)
        layout.addLayout(row)
        return box

    def _card_row(self) -> QWidget:
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        edge = min(THUMB * 2, 160)
        for color in (Color.RED, Color.BLACK):
            column = QVBoxLayout()
            column.setSpacing(4)
            big = QLabel()
            big.setPixmap(self._cell_pixmap(self.style, color, edge))
            big.setFixedSize(edge, edge)
            big.setAlignment(Qt.AlignmentFlag.AlignCenter)
            column.addWidget(big, 0, Qt.AlignmentFlag.AlignHCenter)
            label = QLabel(t(f"piece_name.{self.kind.value}", self.language))
            label.setFont(QFont(theme.UI_FONT, 12, QFont.Weight.Bold))
            label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            column.addWidget(label)
            column.addStretch(1)
            layout.addLayout(column)
        text = QVBoxLayout()
        text.setSpacing(4)
        positioning = QLabel(t(f"piece_rule.{self.kind.value}_long", self.language))
        positioning.setWordWrap(True)
        text.addWidget(positioning)
        # 该型在当前风格下没有美术时，第二行说明回退字形是怎么来的（字族随风格、
        # 墨量与位图同量级）——否则用户只看得出「这枚子长得不一样」。
        if piece_assets.resolve(self.style, Color.RED, self.kind) is None:
            fallback = QLabel(t("desktop.atlas_glyph_family_note", self.language))
            fallback.setWordWrap(True)
            fallback.setStyleSheet("color:#6f6254")
            text.addWidget(fallback)
        text.addStretch(1)
        layout.addLayout(text, 1)
        return box

    def _moves_row(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._heading(t("desktop.atlas_moves", self.language)))
        body = QTextBrowser()
        body.setFrameShape(QFrame.Shape.NoFrame)
        body.setMinimumHeight(120)
        body.setOpenExternalLinks(False)
        if self.language == "en":
            # 英文侧**不读** PIECE_RULES.md：`read_docs()` 失败时返回中文串，
            # 一旦读失败英文界面就会漏出中文。这里只用既有的 `piece_rule.*_long`。
            body.setPlainText(t(f"piece_rule.{self.kind.value}_long", self.language))
        else:
            body.setMarkdown(self._rules_section() or
                             t(f"piece_rule.{self.kind.value}_long", self.language))
        body.setStyleSheet("background:transparent;")
        layout.addWidget(body)
        full = QPushButton(t("desktop.atlas_full_rules", self.language))
        full.clicked.connect(self._open_full_rules)
        layout.addWidget(full, 0, Qt.AlignmentFlag.AlignLeft)
        return box

    def _rule_state_row(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._heading(t("desktop.atlas_rule_state", self.language)))
        values = profile_rule_values(self.profile.id, self.config.get("rule_options"))
        rows = [(t("settings.piece_appear", self.language), f"{self.kind.value}_appear")]
        rows += [(t(f"rule.{key}_short", self.language), key)
                 for key in PIECE_OPTION_KEYS.get(self.kind, ())]
        for label, key in rows:
            line = QHBoxLayout()
            line.addWidget(QLabel(label))
            line.addStretch(1)
            on = bool(values.get(key, False))
            value = QLabel(t("common.yes" if on else "common.no", self.language))
            value.setAlignment(Qt.AlignmentFlag.AlignRight)
            line.addWidget(value)
            layout.addLayout(line)
        goto = QPushButton(t("desktop.atlas_goto_rules", self.language))
        goto.clicked.connect(self._open_rule_settings)
        layout.addWidget(goto, 0, Qt.AlignmentFlag.AlignLeft)
        return box

    def _heading(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setFont(QFont(theme.UI_FONT, 11, QFont.Weight.Bold))
        return label

    # ------------------------------------------------------------------ 细则
    def _rules_section(self) -> str | None:
        """从 `PIECE_RULES.md` 取该子的 H2 小节（中文侧的唯一来源）。"""
        marker = f"（{self.kind.value.upper()}）"
        lines = theme.read_docs("PIECE_RULES.md").splitlines()
        collected: list[str] = []
        capturing = False
        for line in lines:
            if line.startswith("## "):
                if capturing:
                    break
                capturing = marker in line
                continue
            if capturing:
                collected.append(line)
        text = "\n".join(collected).strip()
        return text or None

    def _open_full_rules(self) -> None:
        parent = self.parent()
        opener = getattr(parent, "show_rules", None)
        if callable(opener):
            opener()
            return
        # 没有主窗口（单测/独立构造）时按 show_rules() 的同一分派给出全文。
        if self.language == "en":
            DocumentDialog(t("dialog.rules_title", self.language),
                           t("docs.rules", self.language), self).exec()
            return
        DocumentDialog(t("dialog.rules_title", self.language),
                       theme.read_docs("PIECE_RULES.md", dl("规则文档")), self).exec()

    def _open_rule_settings(self) -> None:
        parent = self.parent()
        opener = getattr(parent, "settings", None)
        if callable(opener):
            # 先关图谱再走主窗口的设置流程：设置若改了盘面类规则会重建界面。
            self.accept()
            opener(PIECE_RULES_TAB)
            return
        # 独立构造时只展示，不回写配置 —— 没有主窗口就没有「当前对局」可对齐。
        from .dialogs import SettingsDialog
        SettingsDialog(self.config, parent, initial_tab=PIECE_RULES_TAB).exec()
