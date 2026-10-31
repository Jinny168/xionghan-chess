from __future__ import annotations

from dataclasses import asdict
import os
import sys
import threading
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool, QTimer, Signal, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QFont, QIcon, QKeySequence
from PySide6.QtWebSockets import QWebSocket
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QScrollArea,
    QInputDialog, QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox, QPushButton,
    QSpinBox, QSplitter, QTabWidget, QVBoxLayout, QWidget,
)

from xionghan_chess import __version__
from xionghan_chess.core.avatars import BUILTIN_AVATARS, avatar_asset_name
from xionghan_chess.core.ai import CONFIGS, Difficulty
from xionghan_chess.core.game import Game, GameError
from xionghan_chess.core.model import Color, GameState, Move, PieceType, Position
from xionghan_chess.core.profiles import PROFILES, profile_rule_values
from xionghan_chess.core.storage import game_document
from xionghan_chess.core.taunts import choose_taunt, taunts
from xionghan_chess.i18n import t
from .audio import DesktopAudio
# `settings` 别名而非 `config`：本类实例上有一个 `self.config`（用户配置字典），
# 若把模块导入成 `config`，方法体里的 `games_dir()` 会先命中**模块**
# 而 `self.config` 是属性 —— 两者同名极易读错，故模块一律走 `settings.`。
from .config import (
    GAME_BREAKING_KEYS,
    games_dir,
    load_config,
    save_config,
    settings_differ_in_game_breaking_keys,
)
from . import net
from .texts import dl, dlf, set_language
from . import training as puzzle_judge
from . import update as version_check
from .storage import autosave_game, load_game, load_statistics, record_result, reset_statistics, save_game
from .ui.dialogs import DocumentDialog, GameLibraryDialog, GLYPH_STYLE_DATA, HandicapDialog, ReplayDialog, SettingsDialog, TrainingDialog
from .ui.board_widget import THINKING_TICK_MS, BoardWidget
from .ui.piece_atlas import PieceAtlasDialog
from .ui.workers import AIWorker, AnalysisWorker, HttpWorker
from .ui import theme




def build_result_dialog(parent: QWidget, title: str, text: str, lang: str,
                        *, allow_again: bool) -> tuple[QMessageBox, QPushButton | None]:
    """构建「对局结束」对话框，返回 `(对话框, 再来一局按钮)`。

    单独抽出来有两个原因：
    1. 测试要能在**不 exec** 的情况下检查按钮文案与角色；
    2. `QMessageBox.information(...)` 是静态便捷函数，加不了自定义主按钮，
       而右键 / Enter 两条入口都需要「再来一局」成为默认按钮。
    """
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Information)
    again: QPushButton | None = None
    if allow_again:
        again = box.addButton(t("action.play_again", lang), QMessageBox.ButtonRole.AcceptRole)
        box.setDefaultButton(again)
    box.addButton(t("action.close", lang), QMessageBox.ButtonRole.RejectRole)
    return box, again


def show_result_dialog(parent: QWidget, title: str, text: str, lang: str,
                       *, allow_again: bool) -> bool:
    """展示结果对话框，返回用户是否点了「再来一局」。

    ⚠️ 这是**模态**调用：测试必须 patch 这个函数（或 `build_result_dialog`），
    否则 offscreen 下会永久挂住。原来测试 patch `QMessageBox.information`，
    换成自定义按钮后那个 seam 不再成立，所以把它收敛到这一个函数上。
    """
    box, again = build_result_dialog(parent, title, text, lang, allow_again=allow_again)
    box.exec()
    return again is not None and box.clickedButton() is again


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__();theme.load_bundled_fonts();self.config=load_config();set_language(self.config.get("language","zh-CN"));self.game=None;self.cancel=threading.Event();self.pool=QThreadPool.globalInstance();self.network=None;self.network_base=None;self.room_id=None;self.token=None;self.revision=0;self.spectator=False;self.network_reconnect_attempts=0;self.network_closing=False;self._handled_draw_offer=None;self._handled_undo_offer=None;self.audio=DesktopAudio();self._stats_recorded=False;self._autosaved=False;self._shown_result=False;self._play_again_pending=False
        # P1-B：界面刷新快照（棋盘/棋谱/阵亡/将军），换局时必须清空
        self._reset_ui_cache()
        # 思考态读条：100ms 只负责让棋盘重绘，**start_ai 起、finish_ai 止**，不常驻。
        self.thinking_timer = QTimer(self)
        self.thinking_timer.setInterval(THINKING_TICK_MS)
        self.thinking_timer.timeout.connect(self._tick_thinking)
        # S2-7 配套：非 None 时表示正处在「残局题」里，`human_move` 要判对错。
        self.puzzle_session=None
        self.setWindowTitle(t("app.name", self.config.get("language", "zh-CN")))
        icon_path = theme.resource("icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1260,850);self.setMinimumSize(900,680);self._build();self.new_game()
        # P1-S：先挂回调再 configure —— 否则 configure 期间（切 BGM/设音量）暴露的
        # 加载失败会被漏掉，玩家只看到「没声音」。
        self.audio.on_failure=self._report_audio_failure;self.audio.configure(self.config);self.apply_appearance()
        self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(250)

    def _build(self) -> None:
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
        for title, callback in ((dl("登场棋子配置"),self.configure_handicap),(dl("创建局域网房间"), self.create_online), (dl("加入局域网房间"), self.join_online),(dl("观战局域网房间"),self.spectate_online)):
            action = QAction(title, self); action.triggered.connect(callback); game_menu.addAction(action)
        replay_menu=self.menuBar().addMenu(t("menu.replay", lang))
        replay=QAction(t("menu.enter_replay", lang),self);replay.setShortcut(QKeySequence("Ctrl+R"));replay.triggered.connect(self.replay_game);replay_menu.addAction(replay)
        library_replay=QAction(t("panel.local_replay_library", lang),self);library_replay.triggered.connect(self.show_game_library);replay_menu.addAction(library_replay)
        training=QAction(dl("残局与排局训练"),self);training.triggered.connect(self.show_training);replay_menu.addAction(training)
        view_menu=self.menuBar().addMenu(t("menu.view", lang))
        fullscreen=QAction(t("menu.fullscreen", lang),self);fullscreen.setShortcut(QKeySequence("F11"));fullscreen.triggered.connect(self.toggle_fullscreen);view_menu.addAction(fullscreen)
        panels=QAction(t("menu.toggle_panels", lang),self);panels.triggered.connect(self.toggle_panels);view_menu.addAction(panels)
        flip=QAction(dl("翻转棋盘"),self);flip.setShortcut(QKeySequence("F"));flip.triggered.connect(self.flip_board);view_menu.addAction(flip)
        settings_menu = self.menuBar().addMenu(t("menu.settings", lang))
        settings_action = QAction(t("settings.desktop_title", lang), self); settings_action.triggered.connect(self.settings); settings_menu.addAction(settings_action);settings_menu.addSeparator()
        stats=QAction("对局统计" if lang!="en" else "Statistics",self);stats.triggered.connect(self.show_statistics);settings_menu.addAction(stats)
        account=QAction(dl("账号与云同步"),self);account.triggered.connect(self.account_sync);settings_menu.addAction(account)
        help_menu=self.menuBar().addMenu(t("menu.help", lang))
        guide=QAction(t("menu.guide", lang),self);guide.setShortcut(QKeySequence("F1"));guide.triggered.connect(self.show_help);help_menu.addAction(guide)
        # 规则已并入图谱：这里只留一个入口，「完整规则文档」在图谱里点。
        # `menu.piece_rules` 键保留但改作提示语 —— 不再有第二个"规则"菜单项。
        atlas=QAction(t("desktop.piece_atlas", lang),self);atlas.triggered.connect(self.show_piece_atlas)
        atlas.setToolTip(t("menu.piece_rules", lang))
        help_menu.addAction(atlas)
        check_update=QAction("检查更新" if lang!="en" else "Check for updates",self);check_update.triggered.connect(self.check_updates);help_menu.addAction(check_update)
        help_menu.addSeparator()
        about=QAction(t("menu.about", lang),self);about.triggered.connect(self.show_about);help_menu.addAction(about)
        root=QWidget();root.setObjectName("root");self.setCentralWidget(root);layout=QVBoxLayout(root);self.banner=QLabel();self.banner.setAlignment(Qt.AlignmentFlag.AlignCenter);self.banner.setObjectName("banner");layout.addWidget(self.banner)
        split=QSplitter();layout.addWidget(split,1);self.board=BoardWidget();self.board.move_requested.connect(self.human_move);self.board.piece_selected.connect(lambda:self.audio.play("select"));split.addWidget(self.board)
        side_inner=QWidget();right=QVBoxLayout(side_inner);self.side=QScrollArea();self.side.setWidgetResizable(True);self.side.setFrameShape(QFrame.Shape.NoFrame);self.side.setMaximumWidth(330);self.side.setWidget(side_inner);self.black=QLabel();self.red=QLabel();self.history=QListWidget();self.history.setMinimumHeight(120);self.captured=QLabel();self.captured.setWordWrap(True)
        right.addWidget(self.black);right.addWidget(self.red)
        side_tabs=QTabWidget();record_page=QWidget();record_layout=QVBoxLayout(record_page);record_layout.addWidget(self.history)
        chat_page=QWidget();chat_layout=QVBoxLayout(chat_page);self.chat_messages=QListWidget();chat_layout.addWidget(self.chat_messages,1)
        self.chat_quick=QComboBox();[(self.chat_quick.addItem(text,text)) for text in taunts("random")]
        quick_send=QPushButton(dl("发送快捷短语"));quick_send.clicked.connect(lambda:self.send_chat(True));chat_layout.addWidget(self.chat_quick);chat_layout.addWidget(quick_send)
        chat_row=QHBoxLayout();self.chat_input=QLineEdit();self.chat_input.setMaxLength(80);self.chat_input.setPlaceholderText(dl("输入聊天内容"))
        self.chat_input.returnPressed.connect(self.send_chat);chat_send=QPushButton(dl("发送"));chat_send.clicked.connect(self.send_chat);chat_row.addWidget(self.chat_input,1);chat_row.addWidget(chat_send);chat_layout.addLayout(chat_row)
        side_tabs.addTab(record_page,t("panel.moves", lang));side_tabs.addTab(chat_page,t("panel.chat", lang));right.addWidget(side_tabs,1);right.addWidget(QLabel("阵亡子力" if lang!="en" else "Captured pieces"));right.addWidget(self.captured)
        actions=QGridLayout();self.undo=QPushButton(t("action.undo", lang));self.undo.clicked.connect(self.undo_move);self.pause=QPushButton(t("action.pause", lang));self.pause.clicked.connect(self.toggle_pause);self.resign=QPushButton(t("action.resign", lang));self.resign.clicked.connect(self.resign_game);self.draw=QPushButton(t("action.draw", lang));self.draw.clicked.connect(self.draw_game);self.resurrect=QPushButton(t("action.resurrect", lang));self.resurrect.clicked.connect(self.resurrect_pawn);self.again=QPushButton(t("action.play_again", lang));self.again.clicked.connect(self.trigger_play_again)
        self.flip=QPushButton(dl("翻转"));self.flip.clicked.connect(self.flip_board)
        for i,b in enumerate((self.undo,self.pause,self.resign,self.draw,self.resurrect,self.flip,self.again)):
            b.setMinimumWidth(182);actions.addWidget(b,i//2,i%2)
        right.addLayout(actions);split.addWidget(self.side);split.setSizes([850,300])
        self.apply_appearance()

    def new_game(self) -> None:
        self.puzzle_session=None
        self.close_network();self.cancel.set();self.cancel=threading.Event();self.game=Game(self.config["profile"],self.config.get("rule_options"),self.config["initial_minutes"],self.config.get("language","zh-CN"),self.current_setup());human=Color(self.config["human_color"]);local=self.config.get("game_mode","ai")=="local";self._reset_ui_cache();self.board.set_game(self.game,human,local);self.configure_board();self.board.locked=False;self._stats_recorded=False;self._autosaved=False;self.refresh();
        if not local and self.game.state.turn is not human:self.start_ai()

    def start_mode(self, mode: str) -> None:
        self.config["game_mode"]=mode;save_config(self.config);self.new_game()

    def human_move(self, move: Move) -> None:
        try:
            piece=self.game.state.piece_at(move.source)
            if piece and piece.type is PieceType.PAWN and self.game.options.pawn_promotion and move.target.row in {0,self.game.profile.rows-1}:
                # 阶段1 S1-3：原为内联复制 core 谓词（这是 rules.promotable_types 的第 4 份
                # 拷贝，前 3 份已在 bfea053 收敛）。改为调用单一来源，避免再次漂移。
                choices=set(self.game.rules.promotable_types(self.game.state,piece.color))
                if choices:
                    options=[(theme.NAMES[piece.color][kind],kind) for kind in sorted(choices,key=lambda item:item.value)]
                    label,ok=QInputDialog.getItem(self,dl("兵卒升变"),dl("选择升变棋子"),[item[0] for item in options],0,False)
                    if not ok:return
                    move=Move(move.source,move.target,next(kind for text,kind in options if text==label))
            if self.network:
                self.send_network("move",{"from":{"row":move.source.row,"col":move.source.col},"to":{"row":move.target.row,"col":move.target.col},"promotion":move.promotion.value if move.promotion else None});return
            record=self.game.move(move);self.board.animate_move(move.target,bool(record.captured),move.source);self.play_sound()
            # S2-7 配套：题目模式下先判对错。答错时 `_judge_puzzle` 已经把棋退回去并
            # 自己刷新过了，这里直接返回，避免再走进 AI / 终局提示分支。
            if not self._judge_puzzle(move):return
            self.refresh();
            if self.game.state.finished:self.add_ai_taunt("defeat")
            if not self.game.state.finished and self.config.get("game_mode","ai")=="ai":self.start_ai()
        except GameError as exc:QMessageBox.warning(self,dl("非法走棋"),str(exc))

    def _judge_puzzle(self, move: Move) -> bool:
        """判定训练题的一手棋。返回 False 表示答错且已回退（调用方不要再刷新）。

        判定本身在 `desktop/training.py`（纯逻辑、有单测）；这里只负责三件界面的事：
        答错时把棋退回去、按尝试次数给更强的提示、过关时收尾。
        """
        session=self.puzzle_session
        if session is None:return True
        lang=self.config.get("language","zh-CN");english=lang=="en"
        verdict=session.submit(move)
        if verdict==puzzle_judge.VERDICT_WRONG:
            # `Game.move` 在落子前压栈，所以 undo(1) 正好回到题面；多步题也只退一手，
            # 已解出的前几手保留。
            try:self.game.undo(1)
            except GameError:pass
            self.board.set_game(self.game,self.game.state.turn,True);self.board.locked=False
            hint=session.next_hint()
            detail=((dl("提示：")+hint) if hint else "") if not english else (("Hint: "+hint) if hint else "")
            QMessageBox.information(self,"再想想" if not english else "Not quite",
                                    ("这不是正解，棋已退回。\n" if not english else "That is not the solution; the move was taken back.\n")+detail)
            self.refresh()
            return False
        if verdict==puzzle_judge.VERDICT_SOLVED:
            title=session.puzzle.title
            self.puzzle_session=None
            QMessageBox.information(self,"过关" if not english else "Solved",
                                    (f"正解！《{title}》已解出。" if not english else f"Correct — “{title}” solved."))
            self.statusBar().showMessage("训练完成，可继续自由对弈" if not english else "Training complete; free play resumed",8000)
            return True
        self.statusBar().showMessage(
            (f"正解，继续第 {session.cursor+1}/{session.total} 手" if not english
             else f"Correct — step {session.cursor+1}/{session.total}"),5000)
        return True

    def _begin_thinking(self) -> None:
        """起表：预算**只**从 `CONFIGS` 读，前端不写第二份时长。"""
        difficulty = Difficulty(self.config.get("difficulty", "medium"))
        self.board.begin_thinking(CONFIGS[difficulty].time_limit)
        self.thinking_timer.start()

    def _end_thinking(self) -> None:
        self.thinking_timer.stop()
        self.board.end_thinking()

    def _tick_thinking(self) -> None:
        self.board.update()

    def start_ai(self) -> None:
        if self.board.locked or self.game.state.finished or self.game.state.paused:return
        self.board.locked=True;self._begin_thinking();worker=AIWorker(self.game,self.config["difficulty"],self.cancel);worker.signals.finished.connect(self.finish_ai);worker.signals.failed.connect(self.ai_failed);self.pool.start(worker)

    def finish_ai(self, result: tuple[Move | None, threading.Event]) -> None:
        move,cancel=result
        # 读条必须在**每个出口**停掉并归零：成功 / move is None / 取消都一样，
        # 否则取消后条会一直往前爬（预算耗尽了也不会自己归零）。
        self._end_thinking()
        if cancel.is_set():return
        try:
            if move:
                record=self.game.move(move);self.board.animate_move(move.target,bool(record.captured),move.source);self.play_sound();scene="victory" if self.game.state.finished else ("check" if self.game.rules.in_check(self.game.state,self.game.state.turn) else ("opening" if len(self.game.state.history)<=2 else None));self.add_ai_taunt(scene)
        except GameError as exc:self.ai_failed(str(exc));return
        self.board.locked=False;self.refresh()

    def add_ai_taunt(self, scene: str | None) -> None:
        if not scene or not self.config.get("taunts",True):return
        sender="Xionghan AI" if self.config.get("language")=="en" else "匈汉棋灵"
        self.chat_messages.addItem(f"{sender}：{choose_taunt(scene)}");self.chat_messages.scrollToBottom()

    def ai_failed(self, result: object) -> None:
        message,cancel=result if isinstance(result,tuple) else (str(result),self.cancel)
        self._end_thinking()
        if cancel.is_set():return
        self.board.locked=False;self.refresh();QMessageBox.warning(self,dl("AI 异常"),message)
    def play_sound(self) -> None:
        if not self.game or not self.game.state.history:return
        record=self.game.state.history[-1]
        if self.game.state.finished:self.audio.play("win" if self.game.state.winner is Color(self.config["human_color"]) else "lose")
        elif self.game.rules.in_check(self.game.state,self.game.state.turn):self.audio.play("check")
        else:self.audio.play("capture" if record.captured else "move")
    def undo_move(self) -> None:
        if self.network:self.send_network("undo_request");return
        # S2-7 配套：题目模式下悔棋＝重做这道题，进度一律归零。
        # 必须先重置再悔棋 —— 答错的棋已经被退回过，此时 `undo` 会因无可退而抛错，
        # 若把重置放在后面就会被提前 return 跳过（实测 attempts 会停在 2）。
        # 多步题也适用：退一手后 cursor 必须回到 0，否则之后每一手都判错。
        if self.puzzle_session is not None:self.puzzle_session.reset()
        try:self.cancel.set();plies=1 if self.config.get("game_mode")=="local" else (2 if len(self.game.state.history)>=2 else 1);self.game.undo(plies);self.cancel=threading.Event();self.board.locked=False
        except GameError as exc:QMessageBox.information(self,dl("悔棋"),str(exc));self.refresh();return
        self.refresh()
    def toggle_pause(self) -> None:
        if not self.game or self.game.state.finished:return
        if self.network:self.send_network("pause",{"paused":not self.game.state.paused});return
        try:
            pausing=not self.game.state.paused
            if pausing:self.cancel.set();self.board.locked=False
            self.game.set_paused(pausing,Color(self.config["human_color"]));self.cancel=threading.Event();self.refresh()
            if not pausing and self.config.get("game_mode")=="ai" and self.game.state.turn is not Color(self.config["human_color"]):self.start_ai()
        except GameError as exc:QMessageBox.information(self,dl("暂停"),str(exc))
    def resign_game(self) -> None:
        if self.network:self.send_network("resign");return
        # 阶段0 S0-D：认输是「不可逆的破坏性操作」，与同文件 draw_game（提和）保持对称，
        # 也修正与 Web 端已交付「认输二次确认」的行为不一致。误点一下不再毁掉一局。
        if QMessageBox.question(self,dl("认输"),dl("确认认输并结束当前对局？"))!=QMessageBox.StandardButton.Yes:return
        color=self.game.state.turn if self.config.get("game_mode")=="local" else Color(self.config["human_color"]);self.game.resign(color);self.refresh()
    def draw_game(self) -> None:
        if self.network:self.send_network("draw_offer");return
        if QMessageBox.question(self,dl("提和"),dl("确认以和棋结束当前对局？"))==QMessageBox.StandardButton.Yes:self.game.state.draw=True;self.game.state.result_reason="draw_agreement";self.refresh()

    def replay_game(self) -> None:
        if not self.game or not self.game.state.history:
            QMessageBox.information(self, dl("复盘"), dl("当前棋局还没有棋谱"))
            return
        ReplayDialog(self.game,self.config,self).exec()
    def resurrect_pawn(self) -> None:
        color=self.game.state.turn if self.config.get("game_mode")=="local" else Color(self.config["human_color"])
        # Read the rank off the profile's own pawn slots instead of hard coding
        # 8/4; `traditional` (10x9) keeps its pawns on row 6.
        row=next((spec.row for spec in self.game.profile.pieces if spec.type is PieceType.PAWN and spec.color is color),8 if color is Color.RED else 4)
        for col in range(0,self.game.profile.cols,2):
            try:self.game.resurrect_pawn(color,Position(row,col));self.refresh();
            except GameError:continue
            if self.config.get("game_mode","ai")=="ai":self.start_ai()
            return
        QMessageBox.information(self,dl("复活"),dl("当前没有可用的兵卒复活位置"))

    # S1-9：这些设置会改变「规则/对局结构」—— 改了必然要重开一局。
    # 其余设置（主题/字体/语言/音量/翻转/辅助提示…）只是界面差异，应当保留当前对局。
    # 真正的清单放在 config.GAME_BREAKING_KEYS（配置语义，测试与 UI 共用一份）；
    # 这里保留同名类属性仅为向后兼容既有调用方。
    _GAME_BREAKING_KEYS = GAME_BREAKING_KEYS

    def settings(self, tab: int = 0) -> None:
        dialog=SettingsDialog(self.config,self,initial_tab=int(tab))
        if not dialog.exec():return
        self._apply_settings(dialog.value())

    def show_piece_atlas(self) -> None:
        """帮助 → 棋子图谱（与设置里「预览三风格」同一个窗口）。"""
        PieceAtlasDialog(self.config,self,self.apply_piece_style,self.new_game).exec()

    def apply_piece_style(self, style: str) -> None:
        """棋子美术风格**即时生效**：不重开对局、不重建界面。

        `piece_style` / `piece_render` 都不在 `GAME_BREAKING_KEYS` 里 —— 它们只影响
        画法，不影响规则。所以这里只做三件事：写配置、重配棋盘（内部预热新风格图片）、
        重绘。走子数 / 时钟 / 悔棋可用性全部原样保留。

        `style == GLYPH_STYLE_DATA`（`"__glyph__"`）表示回到字形渲染：保留
        `piece_style` 原值，只把 `piece_render` 切回 `glyph` —— 与升级前逐像素一致。
        """
        glyph = style == GLYPH_STYLE_DATA
        if glyph:
            self.config["piece_style"]="glyph"
            self.config["piece_render"]="glyph"
        else:
            self.config["piece_style"]=style
            self.config["piece_render"]="image"
        save_config(self.config);self.configure_board();self.board.update()
        lang=self.config.get("language","zh-CN")
        name=t("desktop.atlas_glyph_mode", lang) if glyph else t(f"option.piece_{style}", lang)
        self.statusBar().showMessage(t("desktop.atlas_switched", lang, style=name),5000)

    def _apply_settings(self, new_config: dict[str, object]) -> None:
        """应用新配置（S1-9）：只在「规则会变」时重开对局，否则保留当前对局。

        从 settings() 拆出来，便于**不弹对话框**地验证（桌面端此前没这个能力）。
        原实现无条件 `_build() + new_game()`，改个主题或音量都会丢掉整局。
        """
        previous=self.config
        self.config=new_config;save_config(self.config);self.audio.configure(self.config);self.audio.set_sound_pack(str(self.config.get("sound_pack","classic")), audition=True)
        self.setWindowTitle(t("app.name", self.config.get("language","zh-CN")))
        breaking=settings_differ_in_game_breaking_keys(previous,self.config)
        preserved=None if breaking else getattr(self,"game",None)
        # 记账/存档/结果弹窗的哨兵必须原样带回，否则 refresh() 会重复记账、重弹结果
        sentinels=(getattr(self,"_stats_recorded",False),getattr(self,"_autosaved",False),getattr(self,"_shown_result",False))
        self.menuBar().clear()
        old=self.centralWidget()
        if old:old.deleteLater()
        self._build()
        if preserved is None or preserved.state is None:
            self.new_game()          # 规则变了（或本来就没有对局）→ 必须新开
        else:
            self._reattach_game(preserved,sentinels)

    def _reattach_game(self, game: Game, sentinels: tuple[bool, bool, bool]) -> None:
        """S1-9：UI 重建后把进行中的对局接回新控件 —— 不重开、不重复记账、不重弹结果。"""
        self.game=game
        human=Color(self.config["human_color"]);local=self.config.get("game_mode","ai")=="local"
        self._reset_ui_cache()
        self.board.set_game(game,human,local)
        self.configure_board()
        # 联机时棋盘由服务器快照驱动，重建后不应变成可交互
        self.board.locked=bool(self.network)
        self._stats_recorded,self._autosaved,self._shown_result=sentinels
        self.refresh()

    def apply_appearance(self) -> None:
        if not hasattr(self,"board"):return
        # P1-J：语言在这里落地 —— 设置变更后 `_apply_settings()` 会重建界面，
        # 重建期间所有 dl()/dlf() 都读这个状态。
        set_language(self.config.get("language","zh-CN"))
        palette=theme.THEMES.get(self.config.get("theme","classic"),theme.THEMES["classic"]);font=theme.FONT_CHOICES.get(self.config.get("font","system"),theme.UI_FONT)
        QApplication.instance().setFont(QFont(font,10));self.configure_board()
        text="#f3ead7" if self.config.get("theme")=="dark" else "#211b17"
        hover="#4a433b" if self.config.get("theme")=="dark" else "#f1dfbf"
        self.setStyleSheet(f"""QMainWindow,#root{{background:{palette['window']};color:{text}}}QMenuBar,QMenu,QToolBar{{background:{palette['panel']};color:{text};border-bottom:1px solid {palette['line']};padding:5px}}#banner{{background:{palette['banner_bg']};color:{palette['banner_fg']};padding:8px;font-weight:bold;font-size:15px}}QListWidget,QLabel,QFrame,QGroupBox,QComboBox,QSpinBox,QLineEdit{{background:{palette['panel']};color:{text};border:1px solid {palette['line']};padding:7px}}QPushButton{{min-height:35px;background:{palette['panel']};color:{text};border:1px solid {palette['line']}}}QPushButton:disabled{{color:{palette['disabled_fg']};background:{palette['disabled_bg']};border:1px solid {palette['line']}}}QPushButton:hover{{background:{hover}}}QPushButton:focus{{border:2px solid {palette['banner_bg']}}}QListWidget:focus,QLineEdit:focus,QComboBox:focus{{border:2px solid {palette['banner_bg']}}}""")

    def _report_audio_failure(self, message: str) -> None:
        """P1-S：音效加载/播放失败时在状态栏说一句。

        不弹模态框：音效缺失不影响下棋，打断对局比听不到提示音更糟。
        """
        prefix = "音效不可用：" if self.config.get("language", "zh-CN") != "en" else "Audio unavailable: "
        self.statusBar().showMessage(prefix + message, 10000)

    def configure_board(self) -> None:
        self.board.language=self.config.get("language","zh-CN")
        self.board.set_appearance(self.config.get("theme","classic"),str(self.config.get("background","none")),self.config.get("piece_style","traditional"),self.config.get("piece_render","glyph"))
        self.board.set_assists(selection=self.config.get("selection_highlight",True),legal_targets=self.config.get("legal_targets",True),capture_hints=self.config.get("capture_hints",True),animations=self.config.get("animations",True))
        self.board.set_flipped(self.config.get("flipped",False))

    def current_setup(self) -> dict[str, object]:
        selected=self.config.get("setup_slots",{}).get(self.config["profile"],{})
        return {"firstMove":self.config.get("first_move","red"),"redSlots":selected.get("red"),"blackSlots":selected.get("black")}

    def configure_handicap(self) -> None:
        selected=self.config.get("setup_slots",{}).get(self.config["profile"])
        dialog=HandicapDialog(self.config["profile"],self.config.get("rule_options",{}),selected,self)
        if dialog.exec():self.config.setdefault("setup_slots",{})[self.config["profile"]]=dialog.value();save_config(self.config);self.new_game()

    def flip_board(self) -> None:
        self.config["flipped"]=not self.config.get("flipped",False);save_config(self.config);self.board.set_flipped(self.config["flipped"])

    def show_training(self) -> None:
        dialog=TrainingDialog(self)
        if dialog.exec() and dialog.selected_game:
            # P1-L：**不要**写 `self.config["profile"]`。训练题自带 profile（可能是
            # traditional 的 10×9），一旦写进全局配置，玩家做完一道题再开新局就会
            # 静默变成那道题的盘型；联机建房、让子设置也会跟着串。
            # 题目的盘型由 `self.game.profile` 承担，与用户自己的偏好配置无关。
            self.close_network();self.game=dialog.selected_game;self.config["game_mode"]="local";self._reset_ui_cache();self.board.set_game(self.game,Color.RED,True);self.configure_board()
            # S2-7 配套：带上题目本身，之后每一手都要对答案。
            self.puzzle_session=puzzle_judge.session_for(dialog.selected_puzzle)
            # 训练棋不是正式对局：既不进战绩，也不往棋谱库塞一条两步的「棋谱」。
            # 这两个标志是 refresh() 里「终局才记账/才自动存」的开关，置 True 即抑制。
            self._stats_recorded=True;self._autosaved=True
            self.refresh()

    def toggle_fullscreen(self) -> None:
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def toggle_panels(self) -> None:
        self.side.setVisible(not self.side.isVisible())

    def export_game(self) -> None:
        if not self.game:return
        path,_=QFileDialog.getSaveFileName(self,dl("导出棋局"),str(games_dir() / dl("当前棋局.xhgame")),dl("匈汉棋谱 (*.xhgame);;JSON (*.json)"))
        if not path:return
        if not Path(path).suffix:path += ".xhgame"
        try:save_game(self.game,path);self.statusBar().showMessage(dlf("棋局已保存：{path}", path=path),5000)
        except Exception as exc:QMessageBox.warning(self,dl("导出失败"),str(exc))

    def import_game(self) -> None:
        # load_game accepts current documents and legacy .fen content.
        path,_=QFileDialog.getOpenFileName(self,dl("导入棋局"),str(games_dir()),dl("匈汉棋谱 (*.xhgame *.fen *.json)"))
        if not path:return
        self.load_game_path(Path(path))

    def load_game_path(self, path: Path) -> None:
        try:
            game=load_game(path);self.close_network();self.cancel.set();self.cancel=threading.Event();self.game=game;self.puzzle_session=None;self._reset_ui_cache();self.config["profile"]=game.profile.id;self.config["rule_options"]=asdict(game.options);save_config(self.config);self.board.set_game(game,Color(self.config["human_color"]),self.config.get("game_mode","ai")=="local");self.configure_board();self._stats_recorded=game.state.finished;self._autosaved=game.state.finished;self.refresh();self.statusBar().showMessage(dlf("已载入：{path}", path=path),5000)
        except Exception as exc:QMessageBox.warning(self,dl("导入失败"),str(exc))

    def show_game_library(self) -> None:
        dialog=GameLibraryDialog(games_dir(),self.config,self)
        if dialog.exec() and dialog.selected_path:self.load_game_path(dialog.selected_path)

    def open_autosave_folder(self) -> None:
        folder=games_dir()
        try:os.startfile(folder)
        except OSError as exc:QMessageBox.warning(self,dl("打开目录失败"),str(exc))

    def show_statistics(self) -> None:
        lang=self.config.get("language","zh-CN")
        stats=load_statistics();rate=(stats["wins"]*100/stats["games"]) if stats["games"] else 0
        total_seconds=stats["totalTimeMs"]//1000;fastest_seconds=stats["fastestWinMs"]//1000
        details=f"\n{t('statistics.total_time', lang)}：{total_seconds//60}:{total_seconds%60:02d}\n{t('statistics.fastest_win', lang)}：{fastest_seconds//60}:{fastest_seconds%60:02d}\n{t('statistics.max_streak', lang)}：{stats['winStreak']['max']}"
        box=QMessageBox(self);box.setWindowTitle("对局统计" if lang!="en" else "Statistics");box.setText(f"{t('statistics.total_games', lang)}：{stats['games']}\n{t('statistics.wins', lang)}：{stats['wins']}  {t('statistics.losses', lang)}：{stats['losses']}  {t('statistics.draws', lang)}：{stats['draws']}\n{t('statistics.moves', lang)}：{stats['moves']}\n{t('statistics.win_rate', lang)}：{rate:.1f}%{details}");reset=box.addButton(t("action.reset_statistics", lang),QMessageBox.ButtonRole.DestructiveRole);box.addButton(QMessageBox.StandardButton.Close);box.exec()
        if box.clickedButton() is reset and QMessageBox.question(self,"确认" if lang!="en" else "Confirm",t("dialog.confirm_reset_stats", lang))==QMessageBox.StandardButton.Yes:reset_statistics()

    def show_rules(self) -> None:
        lang=self.config.get("language","zh-CN")
        if lang=="en":
            DocumentDialog(t("dialog.rules_title", lang),t("docs.rules", lang),self).exec();return
        DocumentDialog(t("dialog.rules_title", lang),theme.read_docs("PIECE_RULES.md",dl("规则文档")),self).exec()

    def show_help(self) -> None:
        lang=self.config.get("language","zh-CN")
        if lang=="en":
            DocumentDialog(t("dialog.help_title", lang),t("docs.help", lang),self).exec();return
        DocumentDialog(t("dialog.help_title", lang),theme.read_docs("HELP.md",dl("帮助文档")),self).exec()

    def show_about(self) -> None:
        lang=self.config.get("language","zh-CN")
        if lang=="en":
            DocumentDialog(t("dialog.about_title", lang),t("docs.about", lang),self).exec();return
        DocumentDialog(t("dialog.about_title", lang),theme.read_docs("ABOUT.md",dl("关于文档")),self).exec()

    def check_updates(self) -> None:
        """帮助 → 检查更新（S2-3）：只查版本、只开下载页，**不做静默自更新**。

        没有代码签名时做自动替换可执行文件，等于给程序开一条可被中间人替换的
        更新通道（签名落地是 S2-1）。所以这里只把用户送到下载页，装哪个包、
        什么时候装，由用户自己决定。

        请求走 `_request_json_async`：GitHub API 在慢网下要几秒，同步调用会把
        菜单卡住。结论一律由 `version_check.evaluate` 算 —— 与单测同一条代码。
        """
        lang = self.config.get("language", "zh-CN")
        english = lang == "en"

        def present(payload: object) -> None:
            result = version_check.evaluate(payload, __version__)
            if result.status == version_check.STATUS_ERROR:
                QMessageBox.warning(self, "检查更新失败" if not english else "Update check failed",
                                    ("更新信息无法解析，请稍后再试。" if not english
                                     else "Could not read the update manifest."))
                return
            info = result.info
            if result.status == version_check.STATUS_UPDATE and info is not None:
                box = QMessageBox(self)
                box.setWindowTitle("发现新版本" if not english else "Update available")
                box.setText((f"当前版本 {__version__}，最新版本 {info.label}"
                             if not english else f"Current {__version__}, latest {info.label}"))
                if info.notes:
                    box.setInformativeText(info.notes[:500])
                open_button = box.addButton("打开下载页" if not english else "Open download page",
                                            QMessageBox.ButtonRole.AcceptRole)
                box.addButton("以后再说" if not english else "Later", QMessageBox.ButtonRole.RejectRole)
                box.exec()
                if box.clickedButton() is open_button:
                    QDesktopServices.openUrl(QUrl(info.url or version_check.DOWNLOAD_PAGE))
                return
            QMessageBox.information(self, "已是最新版本" if not english else "Up to date",
                                    (f"当前版本 {__version__} 已是最新。" if not english
                                     else f"You are on the latest version ({__version__})."))

        def failed(message: str) -> None:
            QMessageBox.warning(self, "检查更新失败" if not english else "Update check failed",
                                ("没能连上更新服务器：\n" if not english
                                 else "Could not reach the update server:\n") + str(message))

        self._request_json_async(version_check.RELEASES_URL, on_done=present, on_error=failed)

    def account_sync(self) -> None:
        base=self.config.get("server_url","http://127.0.0.1:8000").rstrip("/");token=self.config.get("account_token","")
        try:
            if not token:
                mode,ok=QInputDialog.getItem(self,dl("账号"),dl("选择操作"),[dl("登录"),dl("注册")],0,False)
                if not ok:return
                username,ok=QInputDialog.getText(self,dl("账号"),dl("用户名"))
                if not ok:return
                password,ok=QInputDialog.getText(self,dl("账号"),dl("密码"),QLineEdit.EchoMode.Password)
                if not ok:return
                display=username
                if mode==dl("注册"):display,_=QInputDialog.getText(self,dl("账号"),dl("显示名称"),QLineEdit.EchoMode.Normal,username)
                data=self.request_json(base+("/api/auth/register" if mode==dl("注册") else "/api/auth/login"),{"username":username,"password":password,"displayName":display},"POST")
                cloud_to_desktop={"boardTheme":"theme","pageBackground":"background","pieceStyle":"piece_style","font":"font","language":"language","flipped":"flipped","musicStyle":"music_style","volume":"sound_volume","animation":"animations","selection":"selection_highlight","legalTargets":"legal_targets","captureHints":"capture_hints","autosave":"autosave","initialMinutes":"initial_minutes","countdownSeconds":"countdown_seconds"}
                self.config["account_token"]=data["token"];self.config["account_display_name"]=data["account"]["displayName"];self.config["account_avatar_url"]=data["account"].get("avatarUrl","")
                for cloud_key,value in data.get("preferences",{}).items():
                    local_key=cloud_to_desktop.get(cloud_key,cloud_key)
                    if local_key in self.config:self.config[local_key]=value
                save_config(self.config);QMessageBox.information(self,dl("账号"),dlf("已登录：{name}", name=data['account']['displayName']));return
            action,ok=QInputDialog.getItem(self,dl("云同步"),dl("选择操作"),[dl("修改资料与头像"),dl("上传当前棋局"),dl("同步外观偏好"),dl("查看云端棋谱"),dl("退出登录")],0,False)
            if not ok:return
            if action==dl("退出登录"):self.request_json(base+"/api/auth/logout",{},"POST",token);self.config["account_token"]="";save_config(self.config);return
            if action==dl("修改资料与头像"):
                current=self.request_json(base+"/api/me",None,"GET",token)["account"]
                display,ok=QInputDialog.getText(self,dl("账号资料"),dl("显示名称"),QLineEdit.EchoMode.Normal,current["displayName"])
                if not ok or not display.strip():return
                choices=[dl("默认头像"),*[dlf("内置头像 {index}", index=index+1) for index in range(len(BUILTIN_AVATARS))],dl("外部 URL")]
                choice,ok=QInputDialog.getItem(self,dl("账号头像"),dl("选择头像"),choices,0,False)
                if not ok:return
                if choice==dl("外部 URL"):avatar,_=QInputDialog.getText(self,dl("账号头像"),dl("头像 URL"),QLineEdit.EchoMode.Normal,current.get("avatarUrl","") if current.get("avatarUrl","").startswith("http") else "")
                elif choice==dl("默认头像"):avatar=""
                else:avatar=f"builtin:{BUILTIN_AVATARS[choices.index(choice)-1]}"
                updated=self.request_json(base+"/api/me/profile",{"displayName":display.strip(),"avatarUrl":avatar.strip()},"PUT",token)["account"]
                self.config["account_display_name"]=updated["displayName"];self.config["account_avatar_url"]=updated.get("avatarUrl","");save_config(self.config);self.refresh();return
            if action==dl("上传当前棋局"):
                if not self.game:return
                self.request_json(base+"/api/me/games",{"document":game_document(self.game),"title":dlf("{profile} · {plies} 手", profile=self.game.profile.title, plies=len(self.game.state.history))},"POST",token);QMessageBox.information(self,dl("云同步"),dl("当前棋局已上传"))
            elif action==dl("同步外观偏好"):
                mapping={"boardTheme":"theme","pageBackground":"background","pieceStyle":"piece_style","font":"font","language":"language","flipped":"flipped","musicStyle":"music_style","volume":"sound_volume","animation":"animations","selection":"selection_highlight","legalTargets":"legal_targets","captureHints":"capture_hints","autosave":"autosave","initialMinutes":"initial_minutes","countdownSeconds":"countdown_seconds"}
                preferences={cloud:self.config.get(local) for cloud,local in mapping.items()};self.request_json(base+"/api/me/preferences",{"preferences":preferences},"PUT",token);QMessageBox.information(self,dl("云同步"),dl("偏好设置已同步"))
            else:
                games=self.request_json(base+"/api/me/games",None,"GET",token);DocumentDialog(dl("云端棋谱"),"\n".join(f"{item['title']} · {dl('已收藏') if item['favorite'] else dl('未收藏')}" for item in games) or dl("暂无云端棋谱"),self).exec()
        except Exception as exc:QMessageBox.warning(self,dl("云同步失败"),str(exc))

    @staticmethod
    def request_json(url: str, payload: object = None, method: str = "GET", token: str = "") -> object:
        # ⚠️ 同步阻塞版，仍在 GUI 线程跑。**仅 account_sync 使用**（7 处）。
        # account_sync 是「对话框与多个请求交错的链式流程」，异步化需要把整条链改成
        # 回调（阶段1 的 net/http_client.py + session 抽取，见
        # docs/DESKTOP_ITERATION_PLAN_1.7.0.md S1-1 / S6）。阶段0 已把更常用的
        # 建连三入口（create/join/spectate）与复盘分析迁到线程池。
        # 新代码请用 self._request_json_async(...)。
        # S1-1：阻塞实现已下沉到 net.request_json（可注入 transport，已被单测覆盖）。
        return net.request_json(url, payload, method, token)

    def server_base(self) -> str | None:
        lang=self.config.get("language","zh-CN")
        value,ok=QInputDialog.getText(self,"服务器地址" if lang!="en" else "Server URL","FastAPI 服务地址" if lang!="en" else "FastAPI server URL",QLineEdit.EchoMode.Normal,self.config.get("server_url","http://127.0.0.1:8000"))
        if not ok:return None
        self.config["server_url"]=value.rstrip("/");save_config(self.config);return self.config["server_url"]

    def _request_json_async(self, url: str, payload: object = None, method: str = "GET",
                            token: str = "", on_done: Callable[[object], None] | None = None,
                            on_error: Callable[[str], None] | None = None) -> None:
        """阶段0 S0-C：把阻塞 HTTP 请求移到 QThreadPool，避免 GUI 冻结（urlopen timeout 15s）。

        on_done(data) / on_error(message) 都经 Signal 回到 **GUI 线程**执行
        （跨线程发射 + AutoConnection，Qt 官方语义）。用法与 start_ai 同一模式。
        """
        worker=HttpWorker(url,payload,method,token)
        if on_done is not None:worker.signals.finished.connect(on_done)
        if on_error is not None:worker.signals.failed.connect(on_error)
        else:worker.signals.failed.connect(lambda message:QMessageBox.warning(self,dl("网络请求失败"),str(message)))
        self.pool.start(worker)

    def create_online(self) -> None:
        base=self.server_base()
        if not base:return
        setup=self.current_setup();lang=self.config.get("language","zh-CN")
        name=self.config.get("account_display_name") or ("桌面玩家" if lang!="en" else "Desktop Player")
        payload={"profileId":self.config["profile"],"mode":"online","playerName":name,"avatarUrl":self.config.get("account_avatar_url",""),"playerColor":self.config["human_color"],"options":self.config.get("rule_options",{}),"initialMinutes":self.config["initial_minutes"],"language":lang,"firstMove":setup["firstMove"],"redSlots":setup["redSlots"],"blackSlots":setup["blackSlots"],"tauntsEnabled":self.config.get("taunts",True)}
        def _created(data: dict[str, object]) -> None:
            self.open_network(base,data)
            QMessageBox.information(self,"房间已创建" if lang!="en" else "Room created",f"{'房间号' if lang!='en' else 'Room code'}：{data['roomId']}")
        # 阶段0 S0-C：建连请求移到线程池 —— 服务不可达时窗口不再冻结最长 15s
        self._request_json_async(base+"/api/rooms",payload,"POST",on_done=_created,
            on_error=lambda message:QMessageBox.warning(self,"创建失败" if lang!="en" else "Create failed",str(message)))

    def join_online(self) -> None:
        base=self.server_base()
        if not base:return
        lang=self.config.get("language","zh-CN")
        room,ok=QInputDialog.getText(self,"加入房间" if lang!="en" else "Join room","房间号" if lang!="en" else "Room code")
        if not ok or not room:return
        name=self.config.get("account_display_name") or ("桌面玩家" if lang!="en" else "Desktop Player")
        def _joined(data: dict[str, object]) -> None:self.open_network(base,data)
        # 阶段0 S0-C：建连请求移到线程池 —— 服务不可达时窗口不再冻结最长 8s
        self._request_json_async(f"{base}/api/rooms/{room.strip().upper()}/join",{"playerName":name,"avatarUrl":self.config.get("account_avatar_url",""),"language":lang},"POST",on_done=_joined,
            on_error=lambda message:QMessageBox.warning(self,"加入失败" if lang!="en" else "Join failed",str(message)))

    def spectate_online(self) -> None:
        base=self.server_base()
        if not base:return
        room,ok=QInputDialog.getText(self,dl("观战房间"),dl("房间号"))
        if not ok or not room:return
        def _spectating(data: dict[str, object]) -> None:self.open_network(base,data,True)
        # 阶段0 S0-C：建连请求移到线程池
        self._request_json_async(f"{base}/api/rooms/{room.strip().upper()}/spectate",{"displayName":dl("桌面观众")},"POST",on_done=_spectating,
            on_error=lambda message:QMessageBox.warning(self,dl("观战失败"),str(message)))

    def open_network(self, base: str, data: dict[str, object], spectator: bool = False) -> None:
        self.cancel.set();self.network_base=base;self.room_id=data["roomId"];self.token=data["token"];self.spectator=spectator;self.revision=data["snapshot"]["revision"];self.network_reconnect_attempts=0;self.network_closing=False;self.apply_network_state(data["snapshot"]);self._connect_network()

    def _connect_network(self) -> None:
        if not self.room_id or not self.token or not self.network_base:return
        lang=self.config.get("language","zh-CN");ws=net.ws_url(self.network_base,self.room_id,self.token,self.spectator)
        socket=QWebSocket();self.network=socket;socket.textMessageReceived.connect(self.network_message);socket.connected.connect(lambda:self._network_connected(socket));socket.disconnected.connect(lambda:self._network_disconnected(socket));socket.open(QUrl(ws));self.statusBar().showMessage(f"{'房间' if lang!='en' else 'Room'} {self.room_id} · {'正在连接' if lang!='en' else 'Connecting'}")

    def _network_connected(self, socket: QWebSocket) -> None:
        if socket is not self.network:return
        self.network_reconnect_attempts=0;lang=self.config.get("language","zh-CN");self.statusBar().showMessage("网络已恢复" if lang!="en" else "Network restored",5000)

    def _network_disconnected(self, socket: QWebSocket) -> None:
        if socket is not self.network:return
        code=int(socket.closeCode());socket.deleteLater();self.network=None;lang=self.config.get("language","zh-CN")
        # S1-1：终止条件判定下沉到 net.should_reconnect（纯函数，已被单测覆盖三种终止码）
        if not net.should_reconnect(code,self.network_closing,self.room_id):
            self.statusBar().showMessage("网络已断开" if lang!="en" else "Network disconnected");return
        if self.network_reconnect_attempts>=net.MAX_RECONNECT_ATTEMPTS:
            self.statusBar().showMessage("自动重连失败，请重新加入房间" if lang!="en" else "Reconnect failed; join the room again");return
        delay=net.reconnect_delay(self.network_reconnect_attempts);self.network_reconnect_attempts+=1;self.statusBar().showMessage(f"{'网络中断，正在重连' if lang!='en' else 'Disconnected, reconnecting'} ({self.network_reconnect_attempts}/{net.MAX_RECONNECT_ATTEMPTS})");QTimer.singleShot(delay,self._connect_network)

    def network_message(self, text: str) -> None:
        message=net.decode_message(text)
        lang=self.config.get("language","zh-CN")
        if message["type"]=="error":QMessageBox.warning(self,"服务器拒绝" if lang!="en" else "Server rejected",message["payload"]["message"]);self.apply_network_state(message["payload"].get("state",{}))
        elif message["type"]=="chat":
            payload=message["payload"]
            if payload.get("automated") and not self.config.get("taunts",True):return
            self.chat_messages.addItem(f"{payload.get('sender',dl('玩家'))}：{payload.get('text','')}");self.chat_messages.scrollToBottom()
        elif message["type"]=="state":
            snapshot=message["payload"];game_data=snapshot["game"]
            self.apply_network_state(snapshot)
            draw_key=(game_data.get("pendingDrawOffer"),len(game_data.get("history",[])))
            if draw_key[0] and draw_key[0]!=self.config["human_color"] and draw_key!=self._handled_draw_offer:self._handled_draw_offer=draw_key;self.send_network("draw_response",{"accept":QMessageBox.question(self,t("action.draw", lang),t("dialog.pending_draw", lang))==QMessageBox.StandardButton.Yes})
            undo_key=(game_data.get("pendingUndoOffer"),len(game_data.get("history",[])))
            if undo_key[0] and undo_key[0]!=self.config["human_color"] and undo_key!=self._handled_undo_offer:self._handled_undo_offer=undo_key;self.send_network("undo_response",{"accept":QMessageBox.question(self,t("action.undo", lang),t("dialog.pending_undo", lang))==QMessageBox.StandardButton.Yes})

    def apply_network_state(self, snapshot: dict[str, object] | None) -> None:
        if not snapshot:return
        game_data=snapshot["game"];self.revision=snapshot["revision"];self.config["human_color"]=snapshot.get("youAre") or self.config["human_color"];self.network_players={item["color"]:item for item in snapshot.get("players",[])};self.puzzle_session=None;self.game=Game.from_state(GameState.from_dict(game_data),game_data["profile"]["options"],game_data.get("setup"));self._reset_ui_cache();replay=game_data.get("replay",[]);self.game._snapshots=[item for item in replay[:-1] if isinstance(item,dict)];self.board.set_game(self.game,Color(self.config["human_color"]),False);self.board.interactive=not self.spectator;self.configure_board();self.board.locked=False
        if not self.game.state.history:self._stats_recorded=False;self._autosaved=False
        lang=self.config.get("language","zh-CN")
        self.statusBar().showMessage(f"{'房间' if lang!='en' else 'Room'} {snapshot['roomId']} · {'状态版本' if lang!='en' else 'revision'} {self.revision}");self.refresh()

    def send_network(self, type_: str, payload: object = None) -> None:
        if not self.network or not self.network.isValid():QMessageBox.information(self,dl("网络"),dl("连接尚未建立"));return
        self.network.sendTextMessage(net.encode_message(type_,self.room_id,self.revision,payload))

    def send_chat(self, quick: bool = False) -> None:
        if not self.network:
            QMessageBox.information(self,dl("聊天"),dl("聊天仅在联机房间中可用"))
            return
        text=self.chat_quick.currentData() if quick else self.chat_input.text().strip()
        if not text:return
        self.send_network("chat",{"text":text,"quick":bool(quick)})
        if not quick:self.chat_input.clear()

    def close_network(self) -> None:
        self.network_closing=True;socket=self.network;self.network=None;self.room_id=None;self.token=None;self.network_base=None;self.spectator=False;self.network_reconnect_attempts=0
        if socket:socket.close();socket.deleteLater()
        if hasattr(self,"board"):self.board.interactive=True

    def refresh(self) -> None:
        """按需刷新界面（250ms 定时器回调）。

        P1-B：此前这里是 12 件事的大杂烩 —— 每 tick 无条件 `history.clear()+addItems`、
        重拼阵亡文本、全盘重绘，还把战绩落盘／自动存档／终局弹窗三个副作用混在中间。
        现在拆成若干只做一件事的小方法，并对**没变化**的部分跳过重建；
        三个副作用集中到 `_settle_finished()`，由哨兵保证各只发生一次。
        """
        if not self.game:
            return
        if not self.network:
            self.game.tick()
        state = self.game.state
        lang = self.config.get("language", "zh-CN")
        history_key = tuple(record.notation for record in state.history)
        self._update_banner(state, lang)
        self._pulse_check_if_needed(state)
        self._update_player_labels(state, lang)
        self._update_clock_warning(state)
        self._update_history(history_key)
        self._update_captured(state, lang)
        self._update_board_if_needed(state, history_key)
        self._update_controls(state, lang)
        self._settle_finished(state, lang)

    def _update_banner(self, state: GameState, lang: str) -> None:
        # 优先级**写死**：终局 > 暂停 > 将军 > 行棋。
        # 将军前缀只在 `state.turn` 的一方被将时出现，判断走 `_check_state()` 的
        # 盘面指纹缓存 —— 解开将军后的第一次 refresh 就已经是 False，不会残留一帧。
        if state.finished:
            text = t("status.game_over", lang)
        elif state.paused:
            text = t("status.paused", lang)
        else:
            text = t("status.turn", lang,
                     color=t("common.red" if state.turn is Color.RED else "common.black", lang))
            # 将军提到横幅：盘内那两个字在九宫附近常被棋子盖住，横幅是最稳的位置。
            # 用现成的 `status.check` + `status.turn` 拼接（两词条中英都已存在）。
            if self._check_state(state):
                text = f"{t('status.check', lang)} · {text}"
        # S2-7 配套：题目模式下横幅要说明「在练哪道题、走到第几手」——
        # 否则玩家分不清这是普通对局还是残局训练。
        session = getattr(self, "puzzle_session", None)
        if session is not None:
            step = min(session.cursor + 1, session.total)
            text += (f"　·　训练《{session.puzzle.title}》第 {step}/{session.total} 手" if lang != "en"
                     else f"　·　Puzzle “{session.puzzle.title}” step {step}/{session.total}")
        if self.banner.text() != text:
            self.banner.setText(text)
        # 将军时横幅**加粗 + 换警示色**（与棋盘外框脉冲、王格红圈同一时刻出现）。
        # `_check_state` 有局面指纹缓存，这里再调一次不会重复算 `in_check`。
        checking = (not state.finished) and self._check_state(state)
        style = "font-weight:700; color:#b21f1f;" if checking else ""
        if self.banner.styleSheet() != style:
            self.banner.setStyleSheet(style)

    def _check_state(self, state: GameState) -> bool:
        """轮到的一方是否被将（**同一局面只算一次**，横幅与脉冲共用）。

        `in_check()` 是全盘扫描（`capturable_squares`），不能每 250ms 跑一次：
        只在「局面可能变了」（走子数 / 轮到谁 / 棋子数 / 暂停 / 终局）时才真的去算。
        横幅和棋盘脉冲都要这个结论，所以收成一个入口，避免算两遍。
        """
        # 签名里必须含**盘面指纹**（不能只看走子数/子数）：将军可能在"子数不变、
        # 走子数不变"的情况下被解开（例如同一次结算里挪动了子、或回放/编辑直接改盘面）。
        # `position_key` 是纯字符串拼接，62 枚子约 20µs，远低于 `in_check` 的 0.4ms。
        signature = (self.game.rules.position_key(state), state.paused, state.finished)
        if signature != self._last_check_signature:
            self._last_check_signature = signature
            self._last_check_value = (not state.finished
                                      and self.game.rules.in_check(state, state.turn))
            # 只在「新局面上第一次判定为将军」时闪一次，同一局面反复 refresh 不重复触发。
            if self._last_check_value:
                self.board.pulse_check()
        return self._last_check_value

    def _pulse_check_if_needed(self, state: GameState) -> None:
        """将军时闪一下棋盘（判定与缓存都在 `_check_state` 里）。"""
        self._check_state(state)

    def _update_player_labels(self, state: GameState, lang: str) -> None:
        for color, label in ((Color.RED, self.red), (Color.BLACK, self.black)):
            player = getattr(self, "network_players", {}).get(color.value, {}) if self.network else {}
            name = player.get("name") or t("common.red" if color is Color.RED else "common.black", lang)
            asset = avatar_asset_name(player.get("avatarUrl", "") if player else "")
            prefix = (f'<img src="{theme.resource("avatars", asset).as_posix()}" '
                      f'width="34" height="34"> ') if asset else ""
            text = f"{prefix}{name}  {self._clock(state.clocks_ms[color])}"
            # 时钟每 250ms 被读一次，但只有「秒数变了」才会真的不同 —— 不比对的话
            # 每秒要做 4 次富文本 setText（会触发重新布局）。
            if label.text() != text:
                label.setText(text)

    def _update_clock_warning(self, state: GameState) -> None:
        threshold = max(0, int(self.config.get("countdown_seconds", 30))) * 1000
        for color, label in ((Color.RED, self.red), (Color.BLACK, self.black)):
            warn = bool(threshold) and state.clocks_ms[color] <= threshold and not state.paused
            style = "color:#b21f1f;font-weight:bold" if warn else ""
            if label.styleSheet() != style:
                label.setStyleSheet(style)

    def _update_history(self, history_key: tuple[str, ...]) -> None:
        """棋谱列表只在走子序列变化时重建。

        P1-B 的重点：原来是每 tick `clear()+addItems(全部)`，一局 200 手时
        每秒重建 4 次列表，滚动位置也会被打断。
        """
        if history_key == self._last_history_key:
            return
        self._last_history_key = history_key
        self.history.clear()
        self.history.addItems(list(history_key))

    def _update_captured(self, state: GameState, lang: str) -> None:
        red = tuple(theme.NAMES[p.color][p.type] for p in state.captured[Color.RED])
        black = tuple(theme.NAMES[p.color][p.type] for p in state.captured[Color.BLACK])
        key = (red, black, lang)
        if key == self._last_captured_key:
            return
        self._last_captured_key = key
        self.captured.setText(f"{t('common.red', lang)}：" + " ".join(red)
                              + f"\n{t('common.black', lang)}：" + " ".join(black))

    def _update_board_if_needed(self, state: GameState, history_key: tuple[str, ...]) -> None:
        """棋盘只在「画面可能不同」时重绘。

        走子动画有自己的 25ms 定时器并自行 `update()`，不需要这里代劳；
        这里负责的是落子、吃子、暂停/锁定遮罩、终局这类由状态驱动的整盘重绘。
        """
        key = (history_key, len(state.pieces), state.turn.value,
               state.paused, self.board.locked, state.finished)
        if key == self._last_board_key:
            return
        self._last_board_key = key
        self.board.update()

    def _update_controls(self, state: GameState, lang: str) -> None:
        pause_text = t("action.resume" if state.paused else "action.pause", lang)
        if self.pause.text() != pause_text:
            self.pause.setText(pause_text)
        self.pause.setEnabled(not state.finished)
        self.undo.setEnabled(bool(state.history) and not state.paused)
        self.draw.setEnabled(not state.finished and not state.paused)
        self.resign.setEnabled(not state.finished)
        self.resurrect.setEnabled(not state.finished and not state.paused)
        again_text = t("action.play_again", lang)
        if self.again.text() != again_text:
            self.again.setText(again_text)
        self.again.setEnabled(self.can_play_again() and not self._play_again_pending)

    def can_play_again(self) -> bool:
        """「再来一局」是否可用。

        只有两种局面不给入口：**残局题**（重开会丢掉题目会话）、
        **联机局**（新局要双方重新进房，不是本地能决定的）。
        **未终局也允许**——用户要的是"随时重开"，未结束时由 `trigger_play_again`
        弹一次确认，避免误点丢棋。
        """
        if self.game is None:
            return False
        if self.puzzle_session is not None:
            return False
        if self.network:
            return False
        return True

    def _confirm_restart_unfinished(self) -> bool:
        """未终局时重开的二次确认（单独成方法，便于测试 patch）。"""
        lang = self.config.get("language", "zh-CN")
        title = "确认" if lang != "en" else "Confirm"
        return QMessageBox.question(
            self, title, t("dialog.confirm_restart", lang),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes

    def trigger_play_again(self) -> None:
        """「再来一局」的唯一入口：右键、结果弹窗、Enter 都走这里。

        - 连点保护：`_play_again_pending` 立刻置位，第二次点击直接被吃掉；
        - **延迟到事件循环**再开新局：结果弹窗是在 `refresh()` 链上弹的，
          直接在弹窗回调里 `new_game()` 会重入刷新。
        """
        if self._play_again_pending or not self.can_play_again():
            return
        if self.game is not None and not self.game.state.finished:
            if not self._confirm_restart_unfinished():
                return
        self._play_again_pending = True
        self.again.setEnabled(False)
        QTimer.singleShot(0, self._play_again_now)

    def _play_again_now(self) -> None:
        self._play_again_pending = False
        self.new_game()

    def keyPressEvent(self, event: object) -> None:
        """Enter / Return = 再来一局（仅终局、且没有模态框时）。

        为什么不是 Ctrl+R：那是「复盘」的快捷键；Ctrl+N 仍是菜单的「新建」。
        """
        key = getattr(event, "key", lambda: None)()
        if (key in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and self.game is not None and self.game.state.finished
                and QApplication.activeModalWidget() is None):
            self.trigger_play_again()
            event.accept()
            return
        super().keyPressEvent(event)

    def _settle_finished(self, state: GameState, lang: str) -> None:
        """终局三件事：战绩落盘、自动存档、结果弹窗。各只发生一次。

        `_stats_recorded` / `_autosaved` / `_shown_result` 是三个哨兵 —— 它们
        原先散落在 `refresh()` 末尾，和界面刷新混在一起，看不出「只在第一次
        终局时执行」这层意思。集中到这里之后，`refresh()` 可以按需重复调用。
        """
        if not state.finished:
            self._shown_result = False
            return
        if not self._stats_recorded:
            record_result(self.game, self.config["human_color"])
            self._stats_recorded = True
        if self.config.get("autosave", True) and not self._autosaved:
            try:
                path = autosave_game(self.game)
                self.statusBar().showMessage(
                    ("棋谱已自动保存：" if lang != "en" else "Replay auto-saved: ") + f"{path}", 8000)
            except OSError as exc:
                self.statusBar().showMessage(
                    ("自动保存失败：" if lang != "en" else "Auto-save failed: ") + f"{exc}", 8000)
            self._autosaved = True
        if not self._shown_result:
            self._shown_result = True
            winner = (t("result.draw", lang) if state.draw else
                      t("result.victory", lang,
                        color=t("common.red" if state.winner is Color.RED else "common.black", lang)))
            if show_result_dialog(self, t("dialog.result_title", lang), winner, lang,
                                  allow_again=self.can_play_again()):
                # 延迟一帧再开新局：本函数在 refresh 链上，直接调会重入
                QTimer.singleShot(0, self.trigger_play_again)

    def _reset_ui_cache(self) -> None:
        """换了对局之后清掉刷新快照。

        不做的话，两局若「走子数、棋子数、轮到谁」恰好相同，棋盘会被判定成
        「没变化」而不重绘 —— 屏幕上留着上一局的子。所有替换 `self.game` 的地方
        都要调它。
        """
        self._last_check_signature = None
        self._last_check_value = False
        self._last_history_key = None
        self._last_captured_key = None
        self._last_board_key = None

    @staticmethod
    def _clock(ms: int) -> str:seconds=max(0,ms//1000);return f"{seconds//60:02d}:{seconds%60:02d}"

    def closeEvent(self, event: object) -> None:self.cancel.set();self.close_network();self.audio.stop();save_config(self.config);super().closeEvent(event)


def run() -> None:
    app=QApplication(sys.argv);app.setApplicationName(t("app.name"))
    icon_path=theme.resource("icon.ico")
    if icon_path.exists():app.setWindowIcon(QIcon(str(icon_path)))
    theme.load_bundled_fonts();window=MainWindow();window.show();sys.exit(app.exec())


if __name__ == "__main__":run()
