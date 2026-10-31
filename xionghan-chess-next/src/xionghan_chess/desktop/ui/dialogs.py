"""桌面端的 6 个对话框（阶段1 S1-2 从 app.py 抽出，约 300 行）。

- `SettingsDialog`      —— 设置（游戏 / 外观 / 棋子与规则 三个 tab）
- `HandicapDialog`      —— 等量让子（摆子）
- `ReplayDialog`        —— 复盘 + AI 分析（分析已异步化，见 workers.AnalysisWorker）
- `TrainingDialog`      —— 残局与排局训练
- `GameLibraryDialog`   —— 本地棋谱库
- `DocumentDialog`      —— 纯文本弹窗（规则/帮助/关于/分析结果复用）

**合成一个模块而不是拆 6 个文件**：结构审计与主程序的方案都指出
「Dialog 拆开只是文件变多，收益有限」，而 `ReplayDialog` 依赖 `DocumentDialog`；
合在一个模块里既省掉跨文件导入，也避免拆完再拼。
"""
from __future__ import annotations

from dataclasses import asdict
import json
import os
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QScrollArea, QSlider, QSpinBox, QSplitter, QTabWidget,
    QTextBrowser, QVBoxLayout, QWidget,
)

from xionghan_chess.core.game import Game
from xionghan_chess.core.model import Color, GameState, PieceType
from xionghan_chess.core.profiles import PROFILES, profile_rule_values
from xionghan_chess.core.setup import profile_slots
from xionghan_chess.core.storage import game_from_document
from xionghan_chess.i18n import normalize_language, t

from ..puzzle_store import available_puzzles, install_puzzles
from ..storage import load_game
from ..texts import dl, dlf
from . import piece_assets, theme
from .board_widget import BoardWidget
from .workers import AnalysisWorker

# 「棋子美术风格」下拉里的回退项：选中它 = 回到 1.7.0 的字形棋子（`piece_render="glyph"`）。
GLYPH_STYLE_DATA = "glyph"   # 四值之一，见 config.PIECE_STYLES


class SettingsDialog(QDialog):
    def __init__(self, config: dict, parent: QWidget | None = None,
                 initial_tab: int = 0) -> None:
        super().__init__(parent); self.language=normalize_language(config.get("language")); self.setWindowTitle(t("settings.desktop_title", self.language)); self.resize(720, 760)
        self._config=config
        layout=QVBoxLayout(self); tabs=QTabWidget(); layout.addWidget(tabs,1)
        self.profile=QComboBox(); [self.profile.addItem(t(f"profile.{p.id}", self.language),p.id) for p in PROFILES.values()]
        self.profile.setCurrentIndex(max(0,self.profile.findData(config["profile"])))
        self.language_select=QComboBox();self.language_select.addItem(t("language.zh-CN", self.language),"zh-CN");self.language_select.addItem(t("language.en", self.language),"en");self.language_select.setCurrentIndex(max(0,self.language_select.findData(self.language)))
        self.game_mode=QComboBox();self.game_mode.addItem(t("mode.ai", self.language),"ai");self.game_mode.addItem(t("mode.local_full", self.language),"local");self.game_mode.setCurrentIndex(max(0,self.game_mode.findData(config.get("game_mode","ai"))))
        # ⚠️ 口径：`difficulty.*` 文案里凡写"每手约 N 秒"，数字来源必须是**实测完成时刻**，
        # 而不是 `CONFIGS[d].time_limit`。hard=12 就是教训：12 是配置上限，而玩家实际等待
        # 将来会变成"提前返回时刻"，两者不再相等。当前文案仍是 12 秒（本版本确实跑满 12s），
        # 等"提前收手"落地后要连同大师档一起改（大师不吃提前收手，"与高级同预算"会说谎）。
        self.difficulty=QComboBox();[(self.difficulty.addItem(t(f"difficulty.{value}", self.language),value)) for value in ("beginner","easy","medium","hard","master")]
        # 未知档位（旧档 / 手改 / 将来并档）**显式回落**到默认，并把原值作为不可选条目
        # 显示出来。原来的 `max(0, findData(...))` 会静默落到「入门」——并档那天就成了
        # 「所有高级玩家无声降级」，而且用户在界面上看不出任何异样。
        self._unknown_difficulty = self.difficulty.findData(config["difficulty"]) < 0
        if self._unknown_difficulty:
            self.difficulty.insertItem(
                0, dlf("未知档位「{name}」，已回落到默认", name=str(config["difficulty"])),
                config["difficulty"])
            self.difficulty.model().item(0).setEnabled(False)
            self.difficulty.setCurrentIndex(max(0, self.difficulty.findData("medium")))
        else:
            self.difficulty.setCurrentIndex(max(0, self.difficulty.findData(config["difficulty"])))
        self.color=QComboBox();self.color.addItem(t("option.red_first", self.language),"red");self.color.addItem(t("option.black_second", self.language),"black");self.color.setCurrentIndex(max(0,self.color.findData(config["human_color"])))
        self.first_move=QComboBox();self.first_move.addItem(t("desktop.first_red",self.language),"red");self.first_move.addItem(t("desktop.first_black",self.language),"black");self.first_move.addItem(t("desktop.first_random",self.language),"random");self.first_move.setCurrentIndex(max(0,self.first_move.findData(config.get("first_move","red"))))
        self.minutes=QSpinBox();self.minutes.setRange(1,180);self.minutes.setValue(config["initial_minutes"])
        self.countdown=QComboBox();[(self.countdown.addItem(t("option.last_seconds", self.language, count=value),value)) for value in (10,30,60)];self.countdown.addItem(t("option.off", self.language),0);self.countdown.setCurrentIndex(max(0,self.countdown.findData(config.get("countdown_seconds",30))))
        self.sound=QCheckBox(t("settings.sound_effects", self.language));self.sound.setChecked(config["sound"])
        self.music=QCheckBox(t("settings.music", self.language));self.music.setChecked(config.get("music",False))
        self.music_style=QComboBox();self.music_style.addItem(t("option.music_fc", self.language),"fc");self.music_style.addItem(t("option.music_qq", self.language),"qq");self.music_style.setCurrentIndex(max(0,self.music_style.findData(config.get("music_style","fc"))))
        self.sound_volume=QSlider(Qt.Orientation.Horizontal);self.sound_volume.setRange(0,100);self.sound_volume.setValue(config.get("sound_volume",70))
        self.music_volume=QSlider(Qt.Orientation.Horizontal);self.music_volume.setRange(0,100);self.music_volume.setValue(config.get("music_volume",40))
        self.theme=QComboBox();[(self.theme.addItem(t(f"option.theme_{value}", self.language),value)) for value in ("classic","green","blue","purple","dark")];self.theme.setCurrentIndex(max(0,self.theme.findData(config.get("theme","classic"))))
        self.font=QComboBox();[(self.font.addItem(text,value)) for value,text in (("system",dl("微软雅黑")),("kaiti",dl("楷体")),("songti",dl("宋体")),("fangsong",dl("仿宋")))];self.font.setCurrentIndex(max(0,self.font.findData(config.get("font","system"))))
        self.background=QComboBox();self.background.addItem(dl("原色（无背景图片）"),"none");[(self.background.addItem(dlf("背景 {index}", index=index),str(index))) for index in range(1,6)];self.background.setCurrentIndex(max(0,self.background.findData(str(config.get("background","none")))))
        # 「棋子美术风格」下拉的第一项是**回退项**：选中它 = `piece_render="glyph"`。
        # 没有它就成了单向门 —— 用户切到图片风格后再也回不到 1.7.0 的字形棋子。
        # 只有四个值：字形 + 三套美术（`piece_render` 由它派生，不再单独让用户选）
        self.piece_style=QComboBox()
        self.piece_style.addItem(t("desktop.atlas_glyph_mode_default", self.language),GLYPH_STYLE_DATA)
        [(self.piece_style.addItem(t(f"option.piece_{value}", self.language),value)) for value in ("traditional","modern","cartoon")]
        current=config.get("piece_style","glyph")
        if current not in ("glyph","traditional","modern","cartoon"):
            current="glyph"
        self.piece_style.setCurrentIndex(max(0,self.piece_style.findData(current)))
        # 整套风格资源缺失（目录被改名的极端情况）时，该风格在下拉里**不可选** ——
        # 与图谱的「该风格资源缺失」保持一致；棋盘另有字形回退，所以程序不崩。
        for _index in range(1, self.piece_style.count()):
            _data = self.piece_style.itemData(_index)
            if _data and piece_assets.preload(_data) == 0:
                _item = self.piece_style.model().item(_index)
                if _item is not None:
                    _item.setEnabled(False)
        self.animations=QCheckBox(t("settings.animation", self.language));self.animations.setChecked(config.get("animations",True))
        self.selection_highlight=QCheckBox(t("settings.selection", self.language));self.selection_highlight.setChecked(config.get("selection_highlight",True))
        self.legal_targets=QCheckBox(t("settings.legal_targets", self.language));self.legal_targets.setChecked(config.get("legal_targets",True))
        self.capture_hints=QCheckBox(t("settings.capture_hints", self.language));self.capture_hints.setChecked(config.get("capture_hints",True))
        self.taunts=QCheckBox("棋灵挑衅短语" if self.language!="en" else "AI taunts");self.taunts.setChecked(config.get("taunts",True))
        self.autosave=QCheckBox(t("settings.autosave_desktop", self.language));self.autosave.setChecked(config.get("autosave",True))

        game_tab=QWidget();game_layout=QVBoxLayout(game_tab);game_form=QFormLayout()
        game_form.addRow(t("settings.game_mode", self.language),self.game_mode);game_form.addRow(t("settings.profile", self.language),self.profile);game_form.addRow(t("difficulty.label", self.language),self.difficulty)
        game_form.addRow(t("settings.human_color", self.language),self.color);game_form.addRow(t("settings.initial_minutes", self.language),self.minutes);game_form.addRow(t("settings.countdown", self.language),self.countdown)
        game_form.addRow(t("desktop.first_move",self.language),self.first_move)
        game_layout.addLayout(game_form);game_layout.addWidget(self.autosave)
        tabs.addTab(game_tab,t("settings.game_tab", self.language))

        appearance_tab=QWidget();appearance_form=QFormLayout(appearance_tab)
        appearance_form.addRow(t("language.label", self.language),self.language_select)
        appearance_form.addRow(t("settings.board_theme", self.language),self.theme);appearance_form.addRow(t("settings.font", self.language),self.font)
        appearance_form.addRow(t("settings.background", self.language),self.background)
        # 「预览三风格」与菜单「帮助 → 棋子图谱」打开的是**同一个**窗口（同一实现）。
        piece_row=QWidget();piece_row_layout=QHBoxLayout(piece_row);piece_row_layout.setContentsMargins(0,0,0,0)
        piece_row_layout.addWidget(self.piece_style,1)
        preview=QPushButton(dl("预览三风格"));preview.clicked.connect(self.open_piece_atlas)
        piece_row_layout.addWidget(preview)
        appearance_form.addRow(t("settings.piece_style", self.language),piece_row)
        appearance_form.addRow(t("settings.sound_effects", self.language),self.sound)
        appearance_form.addRow(t("settings.sound_volume", self.language),self.sound_volume);appearance_form.addRow(t("settings.music", self.language),self.music)
        appearance_form.addRow(t("settings.music_style", self.language),self.music_style);appearance_form.addRow(t("settings.music_volume", self.language),self.music_volume)
        appearance_form.addRow(t("settings.animation", self.language),self.animations);appearance_form.addRow(t("settings.selection", self.language),self.selection_highlight)
        appearance_form.addRow(t("settings.legal_targets", self.language),self.legal_targets);appearance_form.addRow(t("settings.capture_hints", self.language),self.capture_hints);appearance_form.addRow("棋灵挑衅" if self.language!="en" else "AI taunts",self.taunts)
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
            PieceType.PAWN:("piece.pawn_label","piece_rule.pawn_long",("pawn_fast_move_before_enemy_territory","pawn_charge","pawn_three_line_capture","pawn_backward_at_base","pawn_full_movement_at_base","pawn_resurrection","pawn_promotion")),
            PieceType.GUARD:("piece.guard_label","piece_rule.guard_long",()),
            PieceType.ARCHER:("piece.archer_label","piece_rule.archer_long",("archer_enhanced_mode",)),
            PieceType.THUNDER:("piece.thunder_label","piece_rule.thunder_long",()),
            PieceType.ASSASSIN:("piece.assassin_label","piece_rule.assassin_long",()),
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
        tabs.setCurrentIndex(max(0, min(tabs.count()-1, int(initial_tab))))

    def open_piece_atlas(self) -> None:
        """打开棋子图谱（与应用菜单「帮助 → 棋子图谱」同一个窗口）。

        图谱里点「使用此风格」会即时改 `piece_style` —— 这里把主窗口的
        `apply_piece_style` 传下去，棋盘立刻重绘；返回后下拉框跟随新值，
        点「确定」不会把它改回去。
        """
        from .piece_atlas import PieceAtlasDialog

        parent = self.parent()
        applier = getattr(parent, "apply_piece_style", None)
        PieceAtlasDialog(self._config, parent or self, applier).exec()
        # 图谱里可能选了风格，也可能选回「书法字形」—— 下拉框按 `piece_render`
        # 决定停在哪一项，否则点「确定」会把刚切过去的画法又覆盖掉。
        current = (GLYPH_STYLE_DATA if self._config.get("piece_render", "glyph") == "glyph"
                   else self._config.get("piece_style", "traditional"))
        self.piece_style.setCurrentIndex(max(0, self.piece_style.findData(current)))

    def _update_piece_availability(self) -> None:
        profile=PROFILES[self.profile.currentData()]
        for kind in PieceType:
            # 软删的兵种（甲/楯）不在弹窗里，没有对应复选框 → 跳过而不是 KeyError
            check=self.checks.get(f"{kind.value}_appear")
            if check is None:
                continue
            available=kind in profile.enabled_piece_types
            self.piece_groups[kind].setEnabled(available)
            check.setEnabled(available and kind is not PieceType.KING)
            if not available:check.setChecked(False)
            elif kind is PieceType.KING:check.setChecked(True)

    def _capture_profile_values(self) -> None:
        values = {key: check.isChecked() for key, check in self.checks.items()}
        values["king_appear"] = True
        self._profile_values[self._active_profile_id] = values

    def _profile_changed(self) -> None:
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
        # 画法就是一个字段：选中「书法字形」= `piece_style="glyph"`（不再保留旧美术偏好，
        # 四个值互斥才不会有"风格是现代但画法是字形"这种自相矛盾的配置）。
        choice=self.piece_style.currentData()
        piece_style=choice if choice in ("glyph","traditional","modern","cartoon") else "glyph"
        piece_render="glyph" if piece_style==GLYPH_STYLE_DATA else "image"
        return {"profile":self.profile.currentData(),"language":self.language_select.currentData(),"game_mode":self.game_mode.currentData(),"difficulty":self.difficulty.currentData(),"human_color":self.color.currentData(),"first_move":self.first_move.currentData(),"initial_minutes":self.minutes.value(),"countdown_seconds":self.countdown.currentData(),"sound":self.sound.isChecked(),"music":self.music.isChecked(),"music_style":self.music_style.currentData(),"sound_volume":self.sound_volume.value(),"music_volume":self.music_volume.value(),"theme":self.theme.currentData(),"font":self.font.currentData(),"background":self.background.currentData(),"piece_style":piece_style,"piece_render":piece_render,"flipped":previous.get("flipped",False),"setup_slots":previous.get("setup_slots",{}),"account_token":previous.get("account_token",""),"animations":self.animations.isChecked(),"selection_highlight":self.selection_highlight.isChecked(),"legal_targets":self.legal_targets.isChecked(),"capture_hints":self.capture_hints.isChecked(),"taunts":self.taunts.isChecked(),"autosave":self.autosave.isChecked(),"server_url":previous.get("server_url","http://127.0.0.1:8000"),"rule_options":values}


class HandicapDialog(QDialog):
    def __init__(self, profile_id: str, options: dict, selected: dict | None = None, parent: QWidget | None = None) -> None:
        lang=(parent.config.get("language","zh-CN") if parent and hasattr(parent,"config") else "zh-CN")
        super().__init__(parent);self.language=lang;self.setWindowTitle(t("desktop.handicap_title",lang));self.resize(720,620)
        profile=PROFILES[profile_id];active=profile.options.merged(options);slots=profile_slots(profile,active)
        defaults={color:[slot["id"] for slot in slots if slot["color"]==color] for color in ("red","black")}
        self.selected={color:list((selected or {}).get(color,defaults[color])) for color in defaults};self.checks={}
        layout=QVBoxLayout(self);note=QLabel(t("desktop.handicap_note",lang));layout.addWidget(note)
        columns=QHBoxLayout();layout.addLayout(columns,1)
        for color,title in (("red",dl("红方")),("black",dl("黑方"))):
            group=QGroupBox(title);group_layout=QVBoxLayout(group);scroll=QScrollArea();scroll.setWidgetResizable(True);content=QWidget();items=QVBoxLayout(content)
            for slot in (item for item in slots if item["color"]==color):
                check=QCheckBox(f"{theme.NAMES[Color(color)][PieceType(slot['type'])]}  {slot['type']}  ({slot['row']+1},{slot['col']+1})");check.setChecked(slot["id"] in self.selected[color]);check.setProperty("slot_id",slot["id"]);check.setProperty("color",color)
                if slot["type"]=="king":check.setChecked(True);check.setEnabled(False)
                check.toggled.connect(self._update_counts);self.checks[slot["id"]]=check;items.addWidget(check)
            items.addStretch();scroll.setWidget(content);group_layout.addWidget(scroll);columns.addWidget(group)
        self.counts=QLabel();layout.addWidget(self.counts)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Reset)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(t("action.confirm", lang));buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(t("action.cancel", lang));buttons.button(QDialogButtonBox.StandardButton.Reset).setText(t("action.reset", lang))
        buttons.accepted.connect(self._accept);buttons.rejected.connect(self.reject);buttons.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(lambda:self._set_all(True));layout.addWidget(buttons);self._update_counts()

    def _set_all(self, checked: bool) -> None:
        for check in self.checks.values():check.setChecked(checked)
        self._update_counts()

    def _update_counts(self) -> None:
        counts={color:sum(check.isChecked() and check.property("color")==color for check in self.checks.values()) for color in ("red","black")}
        self.counts.setText(dlf("红方 {red} 枚 · 黑方 {black} 枚", red=counts['red'], black=counts['black']))

    def _accept(self) -> None:
        result=self.value()
        if len(result["red"])!=len(result["black"]):QMessageBox.warning(self,t("desktop.invalid_setup",self.language),t("desktop.equal_setup",self.language));return
        self.accept()

    def value(self) -> dict:
        return {color:[slot_id for slot_id,check in self.checks.items() if check.property("color")==color and check.isChecked()] for color in ("red","black")}


class ReplayDialog(QDialog):
    def __init__(self, game: Game, config: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.language=normalize_language(config.get("language"));self.setWindowTitle(t("dialog.replay_title",self.language))
        self.resize(960, 820)
        # 复盘分析的取消信号：关窗即置位，让后台分析在下一手前退出
        # （否则关窗后还要等 `40 手 × 每手预算` 才停得下来）。
        self._analysis_cancel = threading.Event()
        self.snapshots = [GameState.from_dict(item) for item in game._snapshots] + [game.state.clone()]
        self.options = asdict(game.options)
        layout = QVBoxLayout(self)
        self.info = QLabel(); self.info.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(self.info)
        split=QSplitter();layout.addWidget(split,1)
        self.board = BoardWidget(); self.board.interactive = False
        self.board.set_appearance(config.get("theme","classic"), str(config.get("background","none")),
                                  config.get("piece_style","traditional"),
                                  config.get("piece_render","glyph"))
        split.addWidget(self.board)
        side=QWidget();side_layout=QVBoxLayout(side);side_layout.addWidget(QLabel(t("desktop.replay_moves",self.language)))
        self.moves=QListWidget();self.moves.addItem(f"0. {t('desktop.opening',self.language)}")
        self.moves.addItems([f"{index}. {record.notation}" for index,record in enumerate(game.state.history,1)])
        self.moves.currentRowChanged.connect(self.set_step);side_layout.addWidget(self.moves,1)
        split.addWidget(side);split.setSizes([700,230])
        controls = QHBoxLayout()
        for text, callback in (("|<", lambda: self.set_step(0)), ("<", lambda: self.set_step(self.slider.value()-1)), (">", lambda: self.set_step(self.slider.value()+1)), (">|", lambda: self.set_step(len(self.snapshots)-1))):
            button=QPushButton(text);button.clicked.connect(callback);controls.addWidget(button)
        self.slider=QSlider(Qt.Orientation.Horizontal);self.slider.setRange(0,len(self.snapshots)-1);self.slider.valueChanged.connect(self.show_step);controls.addWidget(self.slider,1)
        self.play=QPushButton(t("desktop.play",self.language));self.play.clicked.connect(self.toggle_play);controls.addWidget(self.play)
        close=QPushButton(t("dialog.exit_replay",self.language));close.clicked.connect(self.accept);controls.addWidget(close);layout.addLayout(controls)
        self.timer=QTimer(self);self.timer.setInterval(900);self.timer.timeout.connect(self.next_step)
        self.set_step(len(self.snapshots)-1)

        analyze=QPushButton(t("desktop.analysis",self.language));analyze.clicked.connect(self.show_analysis);controls.insertWidget(0,analyze)

    def closeEvent(self, event: object) -> None:
        self._analysis_cancel.set()     # 关窗即取消后台分析
        super().closeEvent(event)

    def show_analysis(self) -> None:
        # 阶段0 S0-C：analyze_game(40 ply) 原先在 GUI 线程同步跑，复盘窗直接冻结。
        # 移到线程池，完成后经 Signal 回到 GUI 线程弹结果。
        game=Game.from_state(self.snapshots[-1].clone(),self.options);game._snapshots=[item.to_dict() for item in self.snapshots[:-1]]
        worker=AnalysisWorker(game, self._analysis_cancel)
        worker.signals.finished.connect(self._show_analysis_result)
        worker.signals.failed.connect(lambda message:QMessageBox.warning(self,dl("分析失败"),str(message)))
        self.statusBar().showMessage(dl("正在分析对局…"),30000)
        self.pool.start(worker)

    def _show_analysis_result(self, result: object) -> None:
        labels={"best":dl("最佳"),"good":dl("良好"),"inaccuracy":dl("欠准"),"mistake":dl("失误"),"blunder":dl("严重失误")}
        lines=["  ".join(f"{labels[key]} {value}" for key,value in result["summary"].items()),""]
        lines.extend(dlf("{ply}. {notation}  · {quality}  · 损失 {loss}", ply=item['ply'], notation=item['notation'], quality=labels[item['quality']], loss=item['scoreLoss']) for item in result["moves"])
        DocumentDialog(t("desktop.analysis_title",self.language),"\n".join(lines),self).exec()

    def set_step(self, step: int) -> None:
        self.slider.setValue(max(0,min(len(self.snapshots)-1,step)))

    def show_step(self, step: int) -> None:
        state=self.snapshots[step].clone(); replay=Game.from_state(state,self.options)
        self.board.set_game(replay,Color.RED,True);self.board.interactive=False
        notation=state.history[-1].notation if state.history else t("desktop.opening",self.language)
        self.info.setText(dlf("第 {step} / {total} 步 · {notation}", step=step, total=len(self.snapshots)-1, notation=notation))
        self.moves.blockSignals(True);self.moves.setCurrentRow(step);self.moves.blockSignals(False)

    def toggle_play(self) -> None:
        if self.timer.isActive():
            self.timer.stop();self.play.setText(t("desktop.play",self.language))
        else:
            if self.slider.value() >= self.slider.maximum():self.set_step(0)
            self.timer.start();self.play.setText(t("action.pause",self.language))

    def next_step(self) -> None:
        if self.slider.value() >= self.slider.maximum():
            self.timer.stop();self.play.setText(t("desktop.play",self.language));return
        self.set_step(self.slider.value()+1)


class TrainingDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        lang=(parent.config.get("language","zh-CN") if parent and hasattr(parent,"config") else "zh-CN")
        super().__init__(parent);self.language=lang;self.setWindowTitle(t("desktop.training_title",lang));self.resize(760,560);self.selected_game=None;self.selected_puzzle=None
        layout=QVBoxLayout(self);filters=QHBoxLayout();self.level=QComboBox();self.level.addItem(t("desktop.beginner",lang),"beginner");self.level.addItem(t("desktop.advanced",lang),"advanced");self.level.addItem(t("desktop.master",lang),"master");filters.addWidget(self.level);import_button=QPushButton(t("desktop.import_puzzles",lang));import_button.clicked.connect(self.import_puzzles);filters.addWidget(import_button);layout.addLayout(filters)
        self.list=QListWidget();self.list.itemDoubleClicked.connect(lambda _:self.start_selected());layout.addWidget(self.list,1)
        actions=QHBoxLayout();self.hint=QPushButton(t("desktop.hint",lang));self.hint.clicked.connect(self.show_hint);start=QPushButton(t("desktop.start_training",lang));start.clicked.connect(self.start_selected);close=QPushButton(t("common.close",lang));close.clicked.connect(self.reject);actions.addWidget(self.hint);actions.addStretch();actions.addWidget(start);actions.addWidget(close);layout.addLayout(actions)
        self.level.currentIndexChanged.connect(self.reload);self.puzzles=[];self.reload()

    def reload(self) -> None:
        # P1-K：随包题库 + 用户导入的题库（见 desktop/puzzle_store.py）。
        all_puzzles,warning=available_puzzles()
        self.puzzles=[item for item in all_puzzles if item.difficulty==self.level.currentData()];self.list.clear()
        for puzzle in self.puzzles:self.list.addItem(f"{puzzle.title}  ·  {puzzle.description}")
        if warning:
            # 自定义题库坏了不该让窗口打不开 —— 但要让人知道它被忽略了
            note=QListWidgetItem("⚠ "+warning);note.setFlags(Qt.ItemFlag.NoItemFlags);self.list.addItem(note)

    def current(self) -> object:
        row=self.list.currentRow()
        # 警告项不可选，但 currentRow 仍可能指向它，越界检查已经在下面兜住
        return self.puzzles[row] if 0<=row<len(self.puzzles) else None

    def show_hint(self) -> None:
        puzzle=self.current();QMessageBox.information(self,t("desktop.hint",self.language),puzzle.hints[0] if puzzle and puzzle.hints else t("desktop.select_puzzle",self.language))

    def start_selected(self) -> None:
        puzzle=self.current()
        # S2-7 配套：除了载入局面，还要把题目本身交出去 —— 主窗口要靠它的
        # `solution` 判对错。此前只 `accept()`，解法字段在桌面端形同废纸。
        if puzzle:self.selected_puzzle=puzzle;self.selected_game=game_from_document(puzzle.document);self.accept()

    def import_puzzles(self) -> None:
        """P1-K：真的把外部题库并入用户题库，而不是只弹一句「已选择」。"""
        path,_=QFileDialog.getOpenFileName(self,dl("导入题库"),"","JSON (*.json)")
        if not path:return
        try:
            result=install_puzzles(Path(path))
        except Exception as exc:  # 非法题库：给出原因，不写坏存储
            QMessageBox.warning(self,dl("题库导入失败"),dlf("{exc}\n\n文件：{path}", exc=exc, path=path))
            return
        QMessageBox.information(self,dl("题库导入"),result.summary)
        self.reload()


class GameLibraryDialog(QDialog):
    def __init__(self, folder: Path, config: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent);self.setWindowTitle(dl("本地棋谱库"));self.resize(700,520)
        self.folder=folder;self.config=config;self.selected_path:Path|None=None
        self.folder.mkdir(parents=True,exist_ok=True)
        layout=QVBoxLayout(self);layout.addWidget(QLabel(dlf("棋谱目录：{path}", path=self.folder)))
        self.list=QListWidget();layout.addWidget(self.list,1)
        files=sorted((*self.folder.glob("*.xhgame"),*self.folder.glob("*.fen"),*self.folder.glob("*.json")),key=lambda path:path.stat().st_mtime,reverse=True)
        for path in files:
            item=QListWidgetItem(f"{path.stem}    {path.stat().st_size//1024+1} KB")
            item.setData(Qt.ItemDataRole.UserRole,str(path));self.list.addItem(item)
        if not files:self.list.addItem(dl("暂无本地棋谱；结束对局后将自动保存到这里"))
        actions=QHBoxLayout();replay=QPushButton(dl("复盘"));resume=QPushButton(dl("继续对局"));open_folder=QPushButton(dl("打开目录"));close=QPushButton(dl("关闭"))
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
        except Exception as exc:QMessageBox.warning(self,dl("棋谱读取失败"),str(exc))

    def resume_selected(self) -> None:
        path=self.current_path()
        if path:self.selected_path=path;self.accept()

    def open_folder(self) -> None:
        try:os.startfile(self.folder)
        except OSError as exc:QMessageBox.warning(self,dl("打开目录失败"),str(exc))


class DocumentDialog(QDialog):
    def __init__(self, title: str, content: str, parent: QWidget | None = None) -> None:
        super().__init__(parent);self.setWindowTitle(title);self.resize(760,680)
        layout=QVBoxLayout(self);browser=QTextBrowser();browser.setHtml(content) if content.lstrip().startswith("<") else browser.setMarkdown(content);layout.addWidget(browser)
        lang=getattr(parent,"config",{}).get("language","zh-CN") if parent else "zh-CN"
        close=QPushButton(t("common.close", lang));close.clicked.connect(self.accept);layout.addWidget(close)


