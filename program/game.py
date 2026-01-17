import random
import sys

import pygame

from program.ai.chess_ai import ChessAI
from program.config.config import game_config
from program.core.game_rules import GameRules
from program.core.game_state import GameState
from program.ui.avatar import Avatar
from program.ui.button import Button
from program.ui.chess_board import ChessBoard
from program.ui.dialogs import PopupDialog, ConfirmDialog, PawnResurrectionDialog, PromotionDialog, AudioSettingsDialog
from program.utils.utils import load_font, draw_background, SoundManager

# 初始化PyGame
pygame.init()
pygame.mixer.init()  # 初始化音频模块

from program.config.config import (
    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT,
    LEFT_PANEL_WIDTH_RATIO, BOARD_MARGIN_TOP_RATIO, FPS,
    PANEL_BORDER, BLACK, RED, MODE_PVP, MODE_PVC, CAMP_RED, )


class ChessGame:
    def __init__(self, game_mode=MODE_PVP, player_camp=CAMP_RED, game_settings=None):
        """初始化游戏"""
        self.board = None
        self.history_scroll_y = None
        self.timer_font = None
        self.red_avatar = None
        self.board_margin_top = None
        self.black_avatar = None
        self.audio_settings_button = None
        self.undo_button = None
        self.exit_button = None
        self.restart_button = None
        self.back_button = None
        self.fullscreen_button = None
        self.left_panel_width = None
        self.clock = None
        self.screen = None
        self.is_fullscreen = None
        self.window_width = None
        self.window_height = None
        self.windowed_size = (1200, 900)
        pygame.init()

        # 初始化窗口
        self.init_window()

        # 游戏模式和玩家阵营
        self.game_mode = game_mode
        self.player_camp = player_camp

        # 应用游戏设置
        if game_settings:
            GameRules.set_game_settings(game_settings)
        else:
            # 如果没有传入特定设置，应用全局配置
            GameRules.set_game_settings(game_config.get_all_settings())

        # 初始化游戏状态
        self.game_state = GameState()

        # 初始化AI（如果需要）
        # 从游戏设置中获取AI算法类型，默认为negamax
        ai_algorithm = game_settings.get('ai_algorithm', 'negamax') if game_settings else 'negamax'
        self.ai = ChessAI(ai_algorithm, "hard", "black") if game_mode == MODE_PVC else None
        self.ai_thinking = False  # AI是否正在思考
        self.ai_think_start_time = 0  # AI开始思考的时间
        self.async_ai_move = None  # 异步AI计算结果

        # AI超时设置（毫秒）- 设置更长的时间以匹配AI的思考时间
        self.ai_timeout = 10000  # 3秒超时，与AI内部限制一致
        self.ai_thread = None  # AI计算线程

        # 初始化棋盘和界面元素
        self.init_board_and_ui()

        # 选中的棋子
        self.selected_piece = None

        # 上一步走法记录 (from_row, from_col, to_row, to_col)
        self.last_move = None

        # 上一步走法的中文表示
        self.last_move_notation = ""

        # 弹窗和确认对话框
        self.popup = None
        self.confirm_dialog = None
        self.pawn_resurrection_dialog = None
        self.promotion_dialog = None
        self.audio_settings_dialog = None

        # 音效
        self.load_sounds()
        
        # 音效管理器（包含背景音乐功能）
        self.sound_manager = SoundManager()
        # 启动背景音乐
        self.sound_manager.toggle_music_style()  # 设置为QQ风格
        # 如果需要FC风格，可以再次调用toggle_music_style()
    
    def toggle_background_music(self):
        """切换背景音乐风格"""
        return self.sound_manager.toggle_music_style()
    
    def set_sound_volume(self, volume):
        """设置音效音量"""
        self.sound_manager.set_sound_volume(volume)
    
    def set_music_volume(self, volume):
        """设置背景音乐音量"""
        self.sound_manager.set_music_volume(volume)

    def init_window(self):
        """初始化窗口"""
        self.window_width = DEFAULT_WINDOW_WIDTH
        self.window_height = DEFAULT_WINDOW_HEIGHT
        self.is_fullscreen = True
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("匈汉象棋")
        self.clock = pygame.time.Clock()

    def init_board_and_ui(self):

        button_width=120
        button_height = 40
        button_y = self.window_height - 60

        """初始化棋盘和界面元素"""
        self.update_layout()  # 初始化布局
        

        self.create_button(button_height, button_width, button_y)

        # 如果是人机对战且AI先行，设置延迟启动AI
        if self.game_mode == MODE_PVC and self.game_state.player_turn != self.player_camp:
            self.ai_thinking = True
            pygame.time.set_timer(pygame.USEREVENT, 500)  # 0.5秒后启动AI，更快响应

    def create_button(self, button_height, button_width, button_y):
        # 创建返回按钮
        self.back_button = Button(
            self.left_panel_width + 80,
            button_y,
            button_width,
            button_height,
            "返回",
            22
        )
        # 创建重新开始按钮
        self.restart_button = Button(
            self.left_panel_width + 80 + button_width + 10,  # 紧挨着返回按钮
            button_y,
            button_width,
            button_height,
            "重来",
            22
        )
        # 创建退出游戏按钮
        self.exit_button = Button(
            self.window_width - button_width - 80 - button_width - 10,
            button_y,
            button_width,
            button_height,
            "退出游戏",
            22
        )
        # 创建悔棋按钮
        self.undo_button = Button(
            self.window_width - button_width - 80,
            button_y,
            button_width,
            button_height,
            "悔棋",
            22
        )
        # 创建全屏切换按钮
        self.fullscreen_button = Button(
            self.window_width - 100,
            10,
            80,
            30,
            "全屏" if not self.is_fullscreen else "窗口",
            14
        )
        self.audio_settings_button = Button(
            self.window_width - 100,
            50,
            80,
            30,
            "音效设置",
            14
        )

    def handle_board_click(self, mouse_pos):
        """处理棋盘点击事件"""
        if self.game_state.game_over:
            return

        # 如果AI正在思考，忽略玩家点击
        if self.ai_thinking:
            return

        # 获取点击位置对应的棋盘坐标
        row, col = self.board.get_grid_position(mouse_pos)

        # 如果没有选中棋子，尝试选中棋子
        if not self.selected_piece:
            piece = self.game_state.get_piece_at(row, col)
            if piece and piece.camp == self.game_state.player_turn:
                self.selected_piece = piece
                return

        # 如果已经选中棋子，尝试移动棋子
        if self.selected_piece:
            move = (self.selected_piece.row, self.selected_piece.col, row, col)
            # 使用GameRules来检查移动是否合法
            piece = self.game_state.get_piece_at(self.selected_piece.row, self.selected_piece.col)
            if piece and GameRules.is_valid_move(self.game_state.pieces, piece, self.selected_piece.row, self.selected_piece.col, row, col):
                self.make_move(move)
                self.selected_piece = None
                return

        # 如果点击位置无效，取消选中
        self.selected_piece = None

    def make_move(self, move):
        """执行走法"""
        from_row, from_col, to_row, to_col = move
        
        # 检查目标位置是否有棋子（吃子）
        captured_piece = self.game_state.get_piece_at(to_row, to_col)
        
        self.game_state.move_piece(from_row, from_col, to_row, to_col)

        # 更新棋盘上的棋子位置
        # 棋子位置已在game_state中更新，无需单独更新棋盘

        # 更新上一步走法记录
        self.last_move = move
        # 生成走法的中文表示
        from_row, from_col, to_row, to_col = move
        piece = self.game_state.get_piece_at(to_row, to_col)
        if piece:
            self.last_move_notation = self.generate_move_notation(piece, from_row, from_col, to_row, to_col)

        # 播放音效
        # 优先处理绝杀情况，因为绝杀时is_check和is_checkmate都为True
        if self.game_state.is_checkmate():
            # 绝杀时播放绝杀音效，而不是将军音效
            self.sound_manager.play_sound('warn')  # 使用将军语音
            try:
                self.sound_manager.play_sound('check')  # 播放旧版音效
            except:
                pass
        elif self.game_state.is_check:
            # 普通将军情况，播放将军音效
            self.sound_manager.play_sound('warn')# 使用将军语音
            try:
                self.sound_manager.play_sound('capture')  # 播放旧版音效
            except:
                pass
        # 检查是否有棋子被吃掉
        elif captured_piece:
            self.sound_manager.play_sound('eat')
        else:
            self.sound_manager.play_sound('drop')

        # 检查游戏是否结束
        if self.game_state.game_over:
            self.show_game_over_popup()
            return

        # 如果是人机对战，启动AI
        if self.game_mode == MODE_PVC and self.game_state.player_turn != self.player_camp:
            self.ai_thinking = True
            pygame.time.set_timer(pygame.USEREVENT, 1000)  # 1秒后启动AI

    def ai_move(self):
        """AI执行走法"""
        move = self.ai.get_best_move(self.game_state)
        if move:
            self.make_move(move)

    def show_game_over_popup(self):
        """显示游戏结束弹窗"""
        winner = self.game_state.winner
        if winner == "red":
            message = "红方胜利！"
        elif winner == "black":
            message = "黑方胜利！"
        else:  # winner is None, indicating a draw
            message = "平局！"

        total_time = self.game_state.total_time
        red_time = self.game_state.red_time
        black_time = self.game_state.black_time

        self.popup = PopupDialog(400, 320, message, total_time, red_time, black_time)  # 增加高度以适应更多信息
        
        # 根据胜负播放相应的音效
        if self.game_mode == MODE_PVC:  # 人机模式
            if self.player_camp == winner:  # 玩家获胜
                self.sound_manager.play_victory_sound()
            elif winner is not None:  # AI获胜
                self.sound_manager.play_defeat_sound()
            # 平局时不播放音效

    def restart_game(self):
        """重新开始游戏"""
        # 重新初始化游戏状态，确保使用当前设置
        self.game_state = GameState()
        self.selected_piece = None
        self.last_move = None
        self.last_move_notation = ""
        self.popup = None
        self.confirm_dialog = None
        self.ai_thinking = False
        if self.game_mode == MODE_PVC and self.game_state.player_turn != self.player_camp:
            pygame.time.set_timer(pygame.USEREVENT + 1, 800)  # 延迟800毫秒后AI行动
            self.ai_thinking = True

    def load_sounds(self):
        """加载音效 - 现在由SoundManager统一管理"""
        # 音效现在由self.sound_manager统一管理
        pass

    def update_layout(self):
        """根据当前窗口尺寸更新布局"""
        # 计算左侧面板宽度和棋盘边距
        self.left_panel_width = int(LEFT_PANEL_WIDTH_RATIO * self.window_width)
        self.board_margin_top = int(BOARD_MARGIN_TOP_RATIO * self.window_height)

        # 更新棋盘
        self.board = ChessBoard(
            self.window_width - self.left_panel_width,
            self.window_height,
            self.left_panel_width,
            self.board_margin_top
        )

        # 更新按钮位置
        button_width = 120
        button_height = 40
        button_y = self.window_height - 60

        # 创建按钮
        self.create_button(button_height, button_width, button_y)

        # 更新头像位置
        avatar_radius = 40
        panel_center_x = self.left_panel_width // 2
        black_y = self.window_height // 3 - 50
        red_y = self.window_height * 2 // 3

        # 创建头像
        self.black_avatar = Avatar(panel_center_x, black_y, avatar_radius, (245, 245, 235), "黑方", False)
        self.red_avatar = Avatar(panel_center_x, red_y, avatar_radius, (255, 255, 240), "红方", True)

        # 设置当前玩家的头像为活跃状态
        if hasattr(self, 'game_state'):
            is_red_turn = self.game_state.player_turn == "red"
            self.red_avatar.set_active(is_red_turn)
            self.black_avatar.set_active(not is_red_turn)

        # 计时器的字体
        self.timer_font = load_font(18)

    def toggle_fullscreen(self):
        """切换全屏模式"""
        self.is_fullscreen = not self.is_fullscreen

        if self.is_fullscreen:
            # 获取显示器信息
            info = pygame.display.Info()
            # 保存窗口模式的尺寸
            self.windowed_size = (self.window_width, self.window_height)
            # 切换到全屏模式
            self.screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
            self.window_width = info.current_w
            self.window_height = info.current_h
        else:
            # 恢复窗口模式
            self.window_width, self.window_height = self.windowed_size
            self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)

        # 更新布局
        self.update_layout()

    def handle_resize(self, new_size):
        """处理窗口大小变化"""
        self.window_width, self.window_height = new_size
        # 更新布局
        self.update_layout()

    def handle_event(self, event, mouse_pos):
        """处理游戏事件"""
        # 处理窗口大小变化
        if event.type == pygame.VIDEORESIZE:
            if not self.is_fullscreen:  # 只在窗口模式下处理大小变化
                self.handle_resize((event.w, event.h))

        # 处理键盘事件
        if event.type == pygame.KEYDOWN:
            # F11或Alt+Enter切换全屏
            if event.key == pygame.K_F11 or (
                    event.key == pygame.K_RETURN and
                    pygame.key.get_mods() & pygame.KMOD_ALT
            ):
                self.toggle_fullscreen()

        # 处理鼠标滚轮事件（用于棋谱滚动）
        if event.type == pygame.MOUSEWHEEL:
            # 检查鼠标是否在棋谱区域
            right_panel_x = self.window_width - 350  # 与绘制位置保持一致
            # 检查鼠标是否在右侧信息面板区域内
            if mouse_pos[0] >= right_panel_x and mouse_pos[1] >= 300 and mouse_pos[0] <= self.window_width - 10:
                # 滚动棋谱
                self.history_scroll_y = max(0, self.history_scroll_y - event.y)
                # 确保不会滚动过多
                total_moves = len(self.game_state.move_history)
                max_scroll = max(0, total_moves - self.history_max_visible_lines)
                self.history_scroll_y = min(self.history_scroll_y, max_scroll)

        # 处理鼠标点击
        if event.type == pygame.MOUSEBUTTONDOWN:
            # 检查是否点击了全屏按钮
            if self.fullscreen_button.is_clicked(mouse_pos, event):
                self.toggle_fullscreen()
            
            # 检查是否点击了音效设置按钮
            elif self.audio_settings_button.is_clicked(mouse_pos, event):
                # 打开音效设置对话框
                self.audio_settings_dialog = AudioSettingsDialog(500, 350, self.sound_manager)

            # 检查是否点击了悔棋按钮
            elif self.undo_button.is_clicked(mouse_pos, event):
                self.handle_undo()
            
            # 检查是否点击了退出游戏按钮
            elif self.exit_button.is_clicked(mouse_pos, event):
                # 显示确认对话框确认退出游戏
                self.confirm_dialog = ConfirmDialog(
                    400, 200, "是否要退出游戏？\n这将结束当前对局。"
                )

            # 处理棋子操作，只有在当前回合是玩家回合时才处理
            elif not self.ai_thinking and (self.game_mode == MODE_PVP or
                                           self.game_state.player_turn == self.player_camp):
                self.handle_click(mouse_pos)

    def run(self):
        """游戏主循环 - 根据游戏模式选择适当的循环"""
        if self.game_mode == MODE_PVP:
            return self._run_pvp_mode()
        else:  # MODE_PVC
            return self._run_pvc_mode()

    def _run_pvp_mode(self):
        """双人模式游戏循环"""
        while True:
            mouse_pos = pygame.mouse.get_pos()
            current_time = pygame.time.get_ticks()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # 停止背景音乐
                    self.sound_manager.stop_background_music()
                    pygame.quit()
                    sys.exit()

                # 处理窗口大小变化
                if event.type == pygame.VIDEORESIZE:
                    if not self.is_fullscreen:  # 只在窗口模式下处理大小变化
                        self.handle_resize((event.w, event.h))

                # 处理键盘事件
                if event.type == pygame.KEYDOWN:
                    # F11或Alt+Enter切换全屏
                    if event.key == pygame.K_F11 or (
                            event.key == pygame.K_RETURN and
                            pygame.key.get_mods() & pygame.KMOD_ALT
                    ):
                        self.toggle_fullscreen()

                # 如果有升变对话框，优先处理它的事件
                if self.promotion_dialog:
                    result = self.promotion_dialog.handle_event(event, mouse_pos)
                    if result is not None:  # 用户已做出选择
                        if isinstance(result, tuple) and result[0]:  # 确认升变
                            print(f"[DEBUG] 兵升变确认: 当前玩家 {self.game_state.player_turn}")
                            # 执行升变逻辑
                            selected_index = result[1]
                            self.game_state.perform_promotion(selected_index)
                            
                            # 清除升变对话框
                            self.promotion_dialog = None
                            
                            # 切换玩家回合（消耗走子机会）
                            current_player = self.game_state.player_turn
                            opponent_color = "black" if current_player == "red" else "red"
                            self.game_state.player_turn = opponent_color
                            print(f"[DEBUG] 兵升变后切换玩家: {current_player} -> {opponent_color}")
                            # 更新头像状态
                            self.update_avatars()
                        elif result is False:  # 取消
                            print(f"[DEBUG] 兵升变取消: 当前玩家 {self.game_state.player_turn}")
                            # 清除升变对话框
                            self.promotion_dialog = None
                            
                            # 切换玩家回合（即使取消升变，走子机会也已消耗）
                            current_player = self.game_state.player_turn
                            opponent_color = "black" if current_player == "red" else "red"
                            self.game_state.player_turn = opponent_color
                            print(f"[DEBUG] 兵升变取消后切换玩家: {current_player} -> {opponent_color}")

                            # 更新头像状态
                            self.update_avatars()
                # 如果有复活对话框，优先处理它的事件
                elif self.pawn_resurrection_dialog:
                    result = self.pawn_resurrection_dialog.handle_event(event, mouse_pos)
                    if result is not None:  # 用户已做出选择
                        if result:  # 确认
                            # 执行复活逻辑
                            current_player = self.game_state.player_turn
                            # 获取复活位置
                            resurrection_pos = self.pawn_resurrection_dialog.position
                            
                            # 执行复活
                            self.game_state.perform_pawn_resurrection(current_player, resurrection_pos)
                            
                            # 清除复活对话框
                            self.pawn_resurrection_dialog = None
                            
                            # 切换玩家回合（消耗走子机会）
                            opponent_color = "black" if current_player == "red" else "red"
                            self.game_state.player_turn = opponent_color
                            
                            # 更新头像状态
                            self.update_avatars()
                        else:  # 取消
                            # 清除复活对话框
                            self.pawn_resurrection_dialog = None
                # 如果有确认对话框，优先处理它的事件
                elif self.confirm_dialog:
                    result = self.confirm_dialog.handle_event(event, mouse_pos)
                    if result is not None:  # 用户已做出选择
                        if result:  # 确认
                            self.confirm_dialog = None
                            # 检查是返回主菜单还是退出游戏
                            # 在这里我们可以根据上下文决定行为
                            # 如果是退出游戏对话框，直接退出程序
                            if self.confirm_dialog and "退出游戏" in self.confirm_dialog.message:
                                # 停止背景音乐
                                self.sound_manager.stop_background_music()
                                pygame.quit()
                                sys.exit()
                            else:  # 返回主菜单
                                # 停止背景音乐
                                self.sound_manager.stop_background_music()
                                return "back_to_menu"
                        else:  # 取消
                            self.confirm_dialog = None

                # 如果有音效设置对话框，优先处理它的事件
                if self.audio_settings_dialog:
                    result = self.audio_settings_dialog.handle_event(event, mouse_pos)
                    if result == "ok":  # 确认设置
                        self.audio_settings_dialog = None
                    elif result == "cancel":  # 取消设置
                        self.audio_settings_dialog = None
                    elif result == "reset":  # 重置设置
                        # 对话框保持打开，但重置值
                        pass
                    elif result == "volume_changed":  # 音量改变
                        # 对话框保持打开
                        pass
                    # 不管返回什么结果，都要跳过后续的事件处理，防止同时处理其他操作
                    continue  # 跳过后续的事件处理，防止同时处理其他操作
                # 如果游戏结束，处理弹窗事件
                elif self.game_state.game_over and self.popup:
                    if self.popup.handle_event(event, mouse_pos):
                        # 在重置游戏之前停止背景音乐
                        self.sound_manager.stop_background_music()
                        self.__init__(self.game_mode, self.player_camp)  # 重置游戏，保持相同模式和阵营
                        # 重新启动背景音乐
                        self.sound_manager.toggle_music_style()
                # 如果游戏未结束，处理鼠标点击
                elif not self.game_state.game_over:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        # 检查是否点击了全屏按钮
                        if self.fullscreen_button.is_clicked(mouse_pos, event):
                            self.toggle_fullscreen()
                        # 检查是否点击了音效设置按钮
                        elif self.audio_settings_button.is_clicked(mouse_pos, event):
                            # 打开音效设置对话框
                            self.audio_settings_dialog = AudioSettingsDialog(600, 400, self.sound_manager)
                        # 检查是否点击了返回按钮
                        elif self.back_button.is_clicked(mouse_pos, event):
                            # 显示确认对话框而不是直接返回
                            self.confirm_dialog = ConfirmDialog(
                                400, 200, "是否要返回主菜单？\n这将丢失您的当前对局信息。"
                            )
                        # 检查是否点击了退出游戏按钮
                        elif self.exit_button.is_clicked(mouse_pos, event):
                            # 显示确认对话框确认退出游戏
                            self.confirm_dialog = ConfirmDialog(
                                400, 200, "是否要退出游戏？\n这将结束当前对局。"
                            )
                        # 检查是否点击了重新开始按钮
                        elif self.restart_button.is_clicked(mouse_pos, event):
                            self.restart_game()
                        # 检查是否点击了悔棋按钮
                        elif self.undo_button.is_clicked(mouse_pos, event):
                            self.handle_undo()
                        # 双人模式，处理棋子操作
                        else:
                            self.handle_click(mouse_pos)

            # 更新按钮的悬停状态
            self.undo_button.check_hover(mouse_pos)
            self.back_button.check_hover(mouse_pos)
            self.restart_button.check_hover(mouse_pos)
            self.exit_button.check_hover(mouse_pos)
            self.fullscreen_button.check_hover(mouse_pos)
            self.audio_settings_button.check_hover(mouse_pos)

            # 绘制画面
            self.draw(mouse_pos)
            pygame.display.flip()
            self.clock.tick(FPS)

    def _run_pvc_mode(self):
        """人机对战模式游戏循环"""
        while True:
            mouse_pos = pygame.mouse.get_pos()
            current_time = pygame.time.get_ticks()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                # 处理窗口大小变化
                if event.type == pygame.VIDEORESIZE:
                    if not self.is_fullscreen:  # 只在窗口模式下处理大小变化
                        self.handle_resize((event.w, event.h))

                # 处理AI多线程计算完成事件
                if event.type == pygame.USEREVENT + 2:
                    self.process_async_ai_result()
                    # 清除AI思考状态
                    self.ai_thinking = False

                # 处理键盘事件
                if event.type == pygame.KEYDOWN:
                    # F11或Alt+Enter切换全屏
                    if event.key == pygame.K_F11 or (
                            event.key == pygame.K_RETURN and
                            pygame.key.get_mods() & pygame.KMOD_ALT
                    ):
                        self.toggle_fullscreen()

                # 如果有升变对话框，优先处理它的事件
                if self.promotion_dialog:
                    result = self.promotion_dialog.handle_event(event, mouse_pos)
                    if result is not None:  # 用户已做出选择
                        if isinstance(result, tuple) and result[0]:  # 确认升变
                            print(f"[DEBUG] 兵升变确认: 当前玩家 {self.game_state.player_turn}")
                            # 执行升变逻辑
                            selected_index = result[1]
                            self.game_state.perform_promotion(selected_index)
                            
                            # 清除升变对话框
                            self.promotion_dialog = None
                        
                            # 切换玩家回合（消耗走子机会）
                            current_player = self.game_state.player_turn
                            opponent_color = "black" if current_player == "red" else "red"
                            self.game_state.player_turn = opponent_color
                            print(f"[DEBUG] 兵升变后切换玩家: {current_player} -> {opponent_color}")
                            
                            # 更新头像状态
                            self.update_avatars()
                        elif result is False:  # 取消
                            print(f"[DEBUG] 兵升变取消: 当前玩家 {self.game_state.player_turn}")
                            # 清除升变对话框
                            self.promotion_dialog = None
                            
                            # 切换玩家回合（即使取消升变，走子机会也已消耗）
                            current_player = self.game_state.player_turn
                            opponent_color = "black" if current_player == "red" else "red"
                            self.game_state.player_turn = opponent_color
                            print(f"[DEBUG] 兵升变取消后切换玩家: {current_player} -> {opponent_color}")
                            
                            # 更新头像状态
                            self.update_avatars()
                # 如果有复活对话框，优先处理它的事件
                elif self.pawn_resurrection_dialog:
                    result = self.pawn_resurrection_dialog.handle_event(event, mouse_pos)
                    if result is not None:  # 用户已做出选择
                        if result:  # 确认
                            # 执行复活逻辑
                            current_player = self.game_state.player_turn
                            # 获取复活位置
                            resurrection_pos = self.pawn_resurrection_dialog.position
                            
                            # 执行复活
                            self.game_state.perform_pawn_resurrection(current_player, resurrection_pos)
                            
                            # 清除复活对话框
                            self.pawn_resurrection_dialog = None
                            
                            # 切换玩家回合（消耗走子机会）
                            opponent_color = "black" if current_player == "red" else "red"
                            self.game_state.player_turn = opponent_color
                            
                            # 更新头像状态
                            self.update_avatars()
                        else:  # 取消
                            # 清除复活对话框
                            self.pawn_resurrection_dialog = None
                # 如果有音效设置对话框，优先处理它的事件
                if self.audio_settings_dialog:
                    result = self.audio_settings_dialog.handle_event(event, mouse_pos)
                    if result == "ok":  # 确认设置
                        self.audio_settings_dialog = None
                    elif result == "cancel":  # 取消设置
                        self.audio_settings_dialog = None
                    elif result == "reset":  # 重置设置
                        # 对话框保持打开，但重置值
                        pass
                    elif result == "volume_changed":  # 音量改变
                        # 对话框保持打开
                        pass
                    # 不管返回什么结果，都要跳过后续的事件处理，防止同时处理其他操作
                    continue  # 跳过后续的事件处理，防止同时处理其他操作
                # 如果有确认对话框，优先处理它的事件
                elif self.confirm_dialog:
                    result = self.confirm_dialog.handle_event(event, mouse_pos)
                    if result is not None:  # 用户已做出选择
                        if result:  # 确认
                            self.confirm_dialog = None
                            # 检查是返回主菜单还是退出游戏
                            # 在这里我们可以根据上下文决定行为
                            # 如果是退出游戏对话框，直接退出程序
                            if self.confirm_dialog and "退出游戏" in self.confirm_dialog.message:
                                pygame.quit()
                                sys.exit()
                            else:  # 返回主菜单
                                return "back_to_menu"
                        else:  # 取消
                            self.confirm_dialog = None

                # 如果游戏结束，处理弹窗事件
                elif self.game_state.game_over and self.popup:
                    if self.popup.handle_event(event, mouse_pos):
                        self.__init__(self.game_mode, self.player_camp)  # 重置游戏，保持相同模式和阵营

                # 如果游戏未结束，处理鼠标点击
                elif not self.game_state.game_over:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        # 检查是否点击了全屏按钮
                        if self.fullscreen_button.is_clicked(mouse_pos, event):
                            self.toggle_fullscreen()
                        # 检查是否点击了音效设置按钮
                        elif self.audio_settings_button.is_clicked(mouse_pos, event):
                            # 打开音效设置对话框
                            self.audio_settings_dialog = AudioSettingsDialog(600, 400, self.sound_manager)
                        # 检查是否点击了返回按钮
                        elif self.back_button.is_clicked(mouse_pos, event):
                            # 显示确认对话框而不是直接返回
                            self.confirm_dialog = ConfirmDialog(
                                400, 200, "是否要返回主菜单？\n这将丢失您的当前对局信息。"
                            )
                        # 检查是否点击了退出游戏按钮
                        elif self.exit_button.is_clicked(mouse_pos, event):
                            # 显示确认对话框确认退出游戏
                            self.confirm_dialog = ConfirmDialog(
                                400, 200, "是否要退出游戏？\n这将结束当前对局。"
                            )
                        # 检查是否点击了重新开始按钮
                        elif self.restart_button.is_clicked(mouse_pos, event):
                            self.restart_game()
                        # 检查是否点击了悔棋按钮
                        elif self.undo_button.is_clicked(mouse_pos, event):
                            self.handle_undo()
                        # 处理棋子操作，只有在当前回合是玩家回合时才处理
                        elif not self.ai_thinking and self.game_state.player_turn == self.player_camp:
                            self.handle_click(mouse_pos)

            # 检查AI是否思考超时
            if self.ai_thinking and current_time - self.ai_think_start_time > self.ai_timeout:
                # AI思考超时，强制结束思考
                print("AI思考超时，执行当前已知最佳走法")
                self.ai_thinking = False
                pygame.time.set_timer(pygame.USEREVENT + 2, 0)  # 确保停止所有AI相关计时器

                # 如果是人机模式且轮到AI，执行当前已知最佳走法
                if self.game_mode == MODE_PVC and self.game_state.player_turn != self.player_camp:
                    self.make_random_ai_move()

            # 更新按钮的悬停状态
            self.undo_button.check_hover(mouse_pos)
            self.back_button.check_hover(mouse_pos)
            self.restart_button.check_hover(mouse_pos)
            self.exit_button.check_hover(mouse_pos)
            self.fullscreen_button.check_hover(mouse_pos)
            self.audio_settings_button.check_hover(mouse_pos)

            # 检查是否需要触发AI移动（例如游戏开始或重新开始后）
            if (self.game_mode == MODE_PVC and
                    not self.game_state.game_over and
                    self.game_state.player_turn != self.player_camp and
                    not self.ai_thinking):
                self.schedule_ai_move()

            # 在AI思考期间，降低刷新率以减少闪烁
            # 确保AI思考时只绘制稳定的主游戏状态，不显示临时的搜索状态
            if self.ai_thinking:
                self.draw_thinking_indicator(mouse_pos)  # 使用优化的思考指示器绘制
            else:
                self.draw(mouse_pos)
            pygame.display.flip()
            
            # 如果AI正在思考，使用较低的帧率以节省CPU资源并减少闪烁
            if self.ai_thinking:
                self.clock.tick(15)  # 降低到15FPS，平衡性能和视觉效果
            else:
                self.clock.tick(FPS)

    def draw(self, mouse_pos):
        """绘制游戏界面"""
        # 使用统一的背景绘制函数
        draw_background(self.screen)

        # 绘制左侧面板背景 - 使用与主界面一致的纹理
        left_panel_rect = pygame.Rect(0, 0, self.left_panel_width, self.window_height)

        # 先绘制与主背景一致的纹理
        left_panel_surface = pygame.Surface((self.left_panel_width, self.window_height))
        draw_background(left_panel_surface)  # 使用相同的背景绘制函数

        # 稍微调亮左侧面板使其有区分度
        overlay = pygame.Surface((self.left_panel_width, self.window_height), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 30))  # 半透明白色覆盖，轻微增亮
        left_panel_surface.blit(overlay, (0, 0))

        # 应用到主界面
        self.screen.blit(left_panel_surface, (0, 0))

        # 添加分隔线
        pygame.draw.line(self.screen, PANEL_BORDER, (self.left_panel_width, 0),
                         (self.left_panel_width, self.window_height), 2)

        # 绘制棋盘和棋子 - 先绘制这些
        # 在AI思考期间，确保使用稳定的游戏状态绘制棋子
        self.board.draw(self.screen, self.game_state.pieces, self.game_state)

        # 如果有上一步走法，在棋盘上标记出来
        if self.last_move:
            from_row, from_col, to_row, to_col = self.last_move
            self.board.highlight_last_move(self.screen, from_row, from_col, to_row, to_col)

        # 检查是否需要显示将军动画 - 在棋子之上显示动画
        if self.game_state.should_show_check_animation():
            king_pos = self.game_state.get_checked_king_position()
            if king_pos:
                self.board.draw_check_animation(self.screen, king_pos)

        # 绘制游戏信息面板
        self.draw_info_panel()

        # 绘制悔棋按钮、重来按钮、返回按钮、退出按钮、全屏按钮和音效设置按钮
        self.undo_button.draw(self.screen)
        self.restart_button.draw(self.screen)
        self.back_button.draw(self.screen)
        self.exit_button.draw(self.screen)
        self.fullscreen_button.draw(self.screen)
        self.audio_settings_button.draw(self.screen)

        # 绘制玩家头像
        self.red_avatar.draw(self.screen)
        self.black_avatar.draw(self.screen)

        # 绘制计时器信息
        self.draw_timers()

        # 在左侧面板中添加VS标志
        vs_font = load_font(36, bold=True)
        vs_text = "VS"
        vs_surface = vs_font.render(vs_text, True, (100, 100, 100))
        vs_rect = vs_surface.get_rect(center=(self.left_panel_width // 2, self.window_height // 2))
        self.screen.blit(vs_surface, vs_rect)

        # 如果有上一步走法的记录，显示它
        if self.last_move_notation:
            move_font = load_font(18)
            move_text = f"上一步: {self.last_move_notation}"
            move_surface = move_font.render(move_text, True, BLACK)
            # 显示在左侧面板底部
            move_rect = move_surface.get_rect(center=(self.left_panel_width // 2, self.window_height - 80))
            self.screen.blit(move_surface, move_rect)

        # 如果是人机模式，显示模式和阵营提示
        if self.game_mode == MODE_PVC:
            mode_font = load_font(18)
            if self.player_camp == CAMP_RED:
                mode_text = "人机对战模式 - 您执红方"
            else:
                mode_text = "人机对战模式 - 您执黑方"
            mode_surface = mode_font.render(mode_text, True, BLACK)
            self.screen.blit(mode_surface, (
            self.left_panel_width + (self.window_width - self.left_panel_width) // 2 - mode_surface.get_width() // 2,
            15))

            # 如果AI正在思考，显示提示
            if self.ai_thinking:
                thinking_font = load_font(24)
                thinking_text = "电脑思考中..."
                thinking_surface = thinking_font.render(thinking_text, True, RED)
                thinking_rect = thinking_surface.get_rect(center=(self.window_width // 2, 45))
                self.screen.blit(thinking_surface, thinking_rect)

        # 绘制 captured pieces（阵亡棋子）
        self.draw_captured_pieces()

        # 绘制棋谱历史记录
        self.draw_move_history()

        # 如果游戏结束，显示弹窗
        if self.game_state.game_over and self.popup:
            self.popup.draw(self.screen)

        # 如果有确认对话框，显示它
        if self.confirm_dialog:
            self.confirm_dialog.draw(self.screen)

        # 如果有兵/卒复活对话框，显示它
        if self.pawn_resurrection_dialog:
            self.pawn_resurrection_dialog.draw(self.screen)
            
        # 如果有升变对话框，显示它
        if self.promotion_dialog:
            self.promotion_dialog.draw(self.screen)
            
        # 如果有音效设置对话框，显示它
        if self.audio_settings_dialog:
            self.audio_settings_dialog.draw(self.screen)

    def draw_thinking_indicator(self, mouse_pos):
        """绘制AI思考时的指示器，减少闪烁"""
        # 绘制稳定的背景
        draw_background(self.screen)

        # 绘制左侧面板背景
        left_panel_surface = pygame.Surface((self.left_panel_width, self.window_height))
        draw_background(left_panel_surface)
        overlay = pygame.Surface((self.left_panel_width, self.window_height), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 30))
        left_panel_surface.blit(overlay, (0, 0))
        self.screen.blit(left_panel_surface, (0, 0))

        # 添加分隔线
        pygame.draw.line(self.screen, PANEL_BORDER, (self.left_panel_width, 0),
                         (self.left_panel_width, self.window_height), 2)

        # 绘制棋盘和棋子（使用稳定的游戏状态）
        self.board.draw(self.screen, self.game_state.pieces, self.game_state)

    def draw_timers(self):
        """绘制计时器信息"""
        # 获取当前的时间状态
        red_time, black_time = self.game_state.update_times()
        total_time = self.game_state.total_time

        # 转换为分钟:秒格式
        red_time_str = f"{int(red_time // 60):02}:{int(red_time % 60):02}"
        black_time_str = f"{int(black_time // 60):02}:{int(black_time % 60):02}"
        total_time_str = f"{int(total_time // 60):02}:{int(total_time % 60):02}"

        # 绘制红方时间 - 在红方头像下方
        red_time_surface = self.timer_font.render(f"用时: {red_time_str}", True, RED)
        red_time_rect = red_time_surface.get_rect(
            center=(self.left_panel_width // 2, self.red_avatar.y + self.red_avatar.radius + 50)
        )
        self.screen.blit(red_time_surface, red_time_rect)

        # 绘制黑方时间 - 在黑方头像下方
        black_time_surface = self.timer_font.render(f"用时: {black_time_str}", True, BLACK)
        black_time_rect = black_time_surface.get_rect(
            center=(self.left_panel_width // 2, self.black_avatar.y + self.black_avatar.radius + 50)
        )
        self.screen.blit(black_time_surface, black_time_rect)

        # 绘制总时间 - 在左侧面板顶部
        total_time_surface = self.timer_font.render(f"对局时长: {total_time_str}", True, BLACK)
        self.screen.blit(total_time_surface, (10, 10))

    def draw_info_panel(self):
        """绘制游戏信息面板"""
        # 当游戏进行中，在左上角显示当前回合
        if not self.game_state.game_over:
            # 创建回合信息文本
            turn_color = RED if self.game_state.player_turn == "red" else BLACK
            turn_text = f"当前回合: {'红方' if self.game_state.player_turn == 'red' else '黑方'}"

            # 计算位置 - 在左上角，对局时长下方
            font = load_font(20)
            text_surface = font.render(turn_text, True, turn_color)
            # 位于对局时长信息的下方
            text_rect = text_surface.get_rect(
                topleft=(10, 40)  # 在左上角，对局时长下方
            )
            self.screen.blit(text_surface, text_rect)

        # 绘制 captured pieces（阵亡棋子）
        self.draw_captured_pieces()

        # 绘制棋谱历史记录
        self.draw_move_history()

    def draw_captured_pieces(self):
        """绘制双方阵亡棋子"""
        # 绘制标题
        title_font = load_font(20, bold=True)
        red_title = title_font.render("红方阵亡:", True, RED)
        black_title = title_font.render("黑方阵亡:", True, BLACK)

        # 将阵亡棋子信息移到右侧
        right_panel_x = self.window_width - 250  # 右侧边栏起始x坐标
        self.screen.blit(red_title, (right_panel_x, 60))
        self.screen.blit(black_title, (right_panel_x, 180))

        # 绘制红方阵亡棋子
        x_start, y_start = right_panel_x, 90
        x, y = x_start, y_start
        for piece in self.game_state.captured_pieces["red"]:
            piece_text = title_font.render(piece.name, True, RED)
            # 减小右边距，提供更多空间给棋子显示
            if x + piece_text.get_width() > self.window_width - 40:
                x = x_start
                y += 25
            self.screen.blit(piece_text, (x, y))
            x += piece_text.get_width() + 5

        # 绘制黑方阵亡棋子
        x_start, y_start = right_panel_x, 210
        x, y = x_start, y_start
        for piece in self.game_state.captured_pieces["black"]:
            piece_text = title_font.render(piece.name, True, BLACK)
            # 减小右边距，提供更多空间给棋子显示
            if x + piece_text.get_width() > self.window_width - 40:
                x = x_start
                y += 25
            self.screen.blit(piece_text, (x, y))
            x += piece_text.get_width() + 5

    def draw_move_history(self):
        """绘制棋谱历史记录"""
        # 只显示最近的棋谱记录
        if hasattr(self.game_state, 'move_history') and self.game_state.move_history:
            # 绘制标题
            title_font = load_font(20, bold=True)
            history_title = title_font.render("棋谱历史:", True, BLACK)
            self.screen.blit(history_title, (self.window_width - 250, 300))

            # 显示最近的10条记录
            recent_moves = self.game_state.move_history[-10:]
            start_y = 330  # 起始y坐标
            line_spacing = 25  # 行间距

            for i, move_record in enumerate(recent_moves):
                # 处理新旧格式的历史记录
                if len(move_record) == 8:  # 新格式：包含甲/胄吃子信息和刺兑子信息
                    piece, from_row, from_col, to_row, to_col, captured_piece, jia_captured_pieces, ci_captured_pieces = move_record
                elif len(move_record) == 7:  # 新格式：包含甲/胄吃子信息
                    piece, from_row, from_col, to_row, to_col, captured_piece, jia_captured_pieces = move_record
                   
                else:  # 旧格式：6个元素
                    piece, from_row, from_col, to_row, to_col, captured_piece = move_record

                # 生成棋谱记号
                notation = self.generate_move_notation(piece, from_row, from_col, to_row, to_col)
                
                # 计算正确的编号，避免负数
                move_index = max(0, len(self.game_state.move_history) - 10) + i + 1
                
                # 根据玩家颜色确定文字颜色
                if piece.color == "red":
                    move_text = f"{move_index}. {notation}"
                    text_surface = load_font(16).render(move_text, True, RED)
                else:
                    text_surface = load_font(16).render(f"{move_index}. {notation}", True, BLACK)
                
                # 绘制文本
                self.screen.blit(text_surface, (self.window_width - 250, start_y + i * line_spacing))

    def handle_click(self, pos):
        """处理鼠标点击事件"""
        # 获取点击的棋盘位置
        grid_pos = self.board.get_grid_position(pos)
        if not grid_pos:
            return

        row, col = grid_pos

        # 如果正在等待升变选择，不处理棋盘点击
        if self.promotion_dialog:
            return

        # 检查是否点击了空闲的兵/卒起始位置，触发复活对话框
        # 首先检查当前玩家是否有兵/卒在局数量不足7个，且点击位置是初始兵/卒位置且为空
        current_player = self.game_state.player_turn
        if self.selected_piece is None:  # 如果没有选中任何棋子
            # 检查是否点击了兵/卒初始位置且该位置为空
            if ((current_player == "red" and row == 8) or (current_player == "black" and row == 4)) and \
               self.game_state.get_piece_at(row, col) is None:
                # 检查当前玩家在局的兵/卒数量是否小于7
                if self.game_state.get_pawn_count(current_player) < 7:
                    # 检查是否满足复活条件
                    resurrection_positions = self.game_state.get_resurrection_positions()
                    if (row, col) in resurrection_positions[current_player]:
                        # 弹出复活确认对话框
                        self.pawn_resurrection_dialog = PawnResurrectionDialog(
                            500, 200, current_player, (row, col)
                        )
                        return

        # 选择棋子或移动棋子
        if self.selected_piece is None:
            # 尝试选择棋子
            piece = self.game_state.get_piece_at(row, col)
            if piece and piece.color == self.game_state.player_turn:
                self.selected_piece = (row, col)
                self.board.highlight_position(row, col)

                # 计算可能的移动位置
                possible_moves, capturable = self.game_state.calculate_possible_moves(row, col)
                self.board.set_possible_moves(possible_moves)
                self.board.set_capturable_positions(capturable)
        else:
            sel_row, sel_col = self.selected_piece

            # 检查是否点击了同一个棋子（取消选择）
            if sel_row == row and sel_col == col:
                self.selected_piece = None
                self.board.clear_highlights()
                return

            # 检查是否选择了另一个己方棋子（更换选择）
            new_piece = self.game_state.get_piece_at(row, col)
            if new_piece and new_piece.color == self.game_state.player_turn:
                self.selected_piece = (row, col)
                self.board.highlight_position(row, col)

                # 计算新选择棋子的可能移动
                possible_moves, capturable = self.game_state.calculate_possible_moves(row, col)
                self.board.set_possible_moves(possible_moves)
                self.board.set_capturable_positions(capturable)
                return

            # 已选择棋子，尝试移动
            captured_piece = self.game_state.get_piece_at(row, col)
            move_successful = self.game_state.move_piece(sel_row, sel_col, row, col)

            if move_successful:
                print(f"[DEBUG] 移动成功: {sel_row},{sel_col} -> {row},{col}")
                # 检查是否需要升变（兵/卒到达对方底线）
                if self.game_state.needs_promotion:
                    # 获取兵的颜色
                    pawn_color = self.game_state.promotion_pawn.color if self.game_state.promotion_pawn else self.game_state.player_turn
                    print(f"[DEBUG] 需要升变: {pawn_color}方兵到达底线")
                    # 自动弹出升变选择对话框
                    self.promotion_dialog = PromotionDialog(
                        500, 400, pawn_color, (row, col), self.game_state.available_promotion_pieces
                    )

                # 记录上一步走法
                self.last_move = (sel_row, sel_col, row, col)

                # 生成上一步走法的中文表示
                piece = self.game_state.get_piece_at(row, col)
                if piece:
                    self.last_move_notation = self.generate_move_notation(piece, sel_row, sel_col, row, col)

                # 播放选子音效（当选择棋子时）
                if self.selected_piece and not captured_piece:
                    try:
                        self.sound_manager.play_sound('choose')  # 使用chess-master的选子音效
                    except:
                        pass
                
                # 播放移动音效
                if captured_piece:
                    try:
                        self.sound_manager.play_sound('eat')  # 使用chess-master的吃子音效
                    except:
                        pass
                else:
                    try:
                        self.sound_manager.play_sound('drop')  # 使用chess-master的落子音效
                    except:
                        pass

                # 更新头像状态
                self.update_avatars()

                # 播放将军/绝杀音效 - 优先处理绝杀情况，避免重复播放
                if self.game_state.is_checkmate():
                    try:
                        self.sound_manager.play_sound('warn')  # 使用将军语音
                        self.sound_manager.play_sound('check')  # 播放旧版音效
                    except:
                        pass
                elif self.game_state.is_check:
                    try:
                        self.sound_manager.play_sound('warn')  # 使用将军语音
                        self.sound_manager.play_sound('capture')  # 播放旧版音效
                    except:
                        pass

                # 检查游戏是否结束
                if self.game_state.game_over:
                    self.game_over_after()
                # 如果是人机模式且轮到AI走子，触发AI移动
                elif self.game_mode == MODE_PVC and self.game_state.player_turn != self.player_camp:
                    self.schedule_ai_move()
                else:
                    # 立即刷新界面，确保玩家的移动能立刻显示
                    pygame.display.flip()
            else:
                # 移动失败，可能是由于会导致送将，取消选择但不执行移动
                self.selected_piece = None
                self.board.clear_highlights()

            # 无论如何都取消选择状态
            self.selected_piece = None
            self.board.clear_highlights()

    @staticmethod
    def generate_move_notation(piece, from_row, from_col, to_row, to_col):
        """生成走法的中文表示，如"炮二平五"、"马8进7"等"""
        from program.core.chess_pieces import King, Shi, Xiang, Ma, Ju, Pao, Pawn, Wei, She, Lei, Jia

        piece_names = {
            "king": "汉" if piece.color == "red" else "汗",
            "advisor": "仕" if piece.color == "red" else "士",
            "elephant": "相" if piece.color == "red" else "象",
            "horse": "馬" if piece.color == "red" else "马",
            "rook": "車" if piece.color == "red" else "车",
            "cannon": "炮" if piece.color == "red" else "砲",
            "pawn": "兵" if piece.color == "red" else "卒",
            "wei": "尉" if piece.color == "red" else "衛",
            "she": "射" if piece.color == "red" else "䠶",
            "lei": "檑" if piece.color == "red" else "礌",
            "jia": "甲" if piece.color == "red" else "胄"
        }

        # 获取棋子名称
        if isinstance(piece, King):
            piece_name = piece_names["king"]
        elif isinstance(piece, Shi):
            piece_name = piece_names["advisor"]
        elif isinstance(piece, Xiang):
            piece_name = piece_names["elephant"]
        elif isinstance(piece, Ma):
            piece_name = piece_names["horse"]
        elif isinstance(piece, Ju):
            piece_name = piece_names["rook"]
        elif isinstance(piece, Pao):
            piece_name = piece_names["cannon"]
        elif isinstance(piece, Pawn):
            piece_name = piece_names["pawn"]
        elif isinstance(piece, Wei):
            piece_name = piece_names["wei"]
        elif isinstance(piece, She):
            piece_name = piece_names["she"]
        elif isinstance(piece, Lei):
            piece_name = piece_names["lei"]
        elif isinstance(piece, Jia):
            piece_name = piece_names["jia"]
        else:
            piece_name = piece.name  # 直接使用棋子名称

        # 转换列数为中文数字或数字 - 从右至左标识
        # 红方用一至十三标识，黑方用1-13标识
        col_names_red = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二", "十三"]
        col_names_black = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"]

        # 根据棋子颜色选择合适的列名表示
        col_names = col_names_red if piece.color == "red" else col_names_black

        # 计算棋盘坐标到列标识的映射（从右到左）
        col_index = 12 - from_col  # 从右到左映射 (0-12 -> 12-0)
        from_col_name = col_names[col_index]

        # 判断移动方向
        if to_row < from_row:  # 向上移动
            direction = "进" if piece.color == "red" else "退"
        elif to_row > from_row:  # 向下移动
            direction = "退" if piece.color == "red" else "进"
        else:  # 水平移动
            direction = "平"

        # 获取目标位置
        if direction == "平":
            # 平移表示目标列
            to_col_index = 12 - to_col  # 从右到左映射
            to_col_name = col_names[to_col_index]
            notation = f"{piece_name}{from_col_name}{direction}{to_col_name}"
        else:
            # 进退表示移动的距离或目标列
            # 检查是否是马、象、士或新增的对角线移动棋子
            is_diagonal_piece = (isinstance(piece, Ma) or isinstance(piece, Xiang) or
                                 isinstance(piece, Shi) or isinstance(piece, She) or
                                 isinstance(piece, Wei))

            if is_diagonal_piece:
                # 马、象、士、射、尉用目标列表示
                to_col_index = 12 - to_col  # 从右到左映射
                to_col_name = col_names[to_col_index]
                notation = f"{piece_name}{from_col_name}{direction}{to_col_name}"
            else:
                # 其他棋子用移动距离表示
                distance = abs(from_row - to_row)
                # 确保距离在有效范围内
                if distance < 1:
                    distance = 1
                elif distance > 12:  # 最大可能距离是12格（从第0行到第12行）
                    distance = 12

                if piece.color == "black" and direction == "进":
                    # 黑方前进和红方后退是增加行号
                    # 确保索引在有效范围内
                    index = min(distance - 1, len(col_names_black) - 1)
                    distance_str = col_names_black[index]
                elif piece.color == "black" and direction == "退":
                    # 黑方后退和红方前进是减少行号
                    # 确保索引在有效范围内
                    index = min(distance - 1, len(col_names_black) - 1)
                    distance_str = col_names_black[index]
                else:
                    # 红方使用汉字数字表示距离
                    # 确保索引在有效范围内
                    # 扩展红方距离表示以适应13x13棋盘
                    red_distance_names = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"]
                    index = min(distance - 1, len(red_distance_names) - 1)
                    distance_str = red_distance_names[index]
                notation = f"{piece_name}{from_col_name}{direction}{distance_str}"

        return notation

    def handle_undo(self):
        """处理悔棋操作"""
        # 如果AI正在思考，不允许悔棋
        if self.ai_thinking:
            return False

        # 如果游戏已经结束，先清除状态
        if self.game_state.game_over:
            self.popup = None
            self.game_state.game_over = False

        if self.game_mode == MODE_PVP:
            # 人人模式直接悔棋
            if self.game_state.undo_move():
                # 悔棋成功
                self.selected_piece = None
                self.board.clear_highlights()
                self.update_avatars()

                # 清除上一步记录
                self.last_move = None
                self.last_move_notation = ""

                # 如果还有移动历史，更新上一步记录
                if hasattr(self.game_state, 'move_history') and len(self.game_state.move_history) > 0:
                    last_history = self.game_state.move_history[-1]
                    if 'from_pos' in last_history and 'to_pos' in last_history:
                        from_row, from_col = last_history['from_pos']
                        to_row, to_col = last_history['to_pos']
                        self.last_move = (from_row, from_col, to_row, to_col)
                        piece = self.game_state.get_piece_at(to_row, to_col)
                        if piece:
                            self.last_move_notation = self.generate_move_notation(
                                piece, from_row, from_col, to_row, to_col
                            )

                return True
        else:  # 人机模式
            # 首先停止任何AI计时器
            pygame.time.set_timer(pygame.USEREVENT + 1, 0)
            pygame.time.set_timer(pygame.USEREVENT + 2, 0)
            self.ai_thinking = False

            # 移动历史为空，没有步骤可以悔棋
            if not hasattr(self.game_state, 'move_history') or len(self.game_state.move_history) == 0:
                return False

            # 判断当前是玩家回合还是AI回合
            is_player_turn = self.game_state.player_turn == self.player_camp

            if is_player_turn:
                # 玩家回合 - 需要悔两步（玩家和AI各一步）
                if len(self.game_state.move_history) >= 1:
                    # 至少有一步可以悔棋
                    self.game_state.undo_move()  # 悔掉玩家上一步

                    # 如果还有更多步骤，尝试悔掉AI的上一步
                    if len(self.game_state.move_history) >= 1:
                        self.game_state.undo_move()  # 悔掉AI上一步

                    self.selected_piece = None
                    self.board.clear_highlights()
                    self.update_avatars()
                    return True
            else:
                # AI回合 - 悔一步（AI刚下的或上一个玩家步骤）
                if len(self.game_state.move_history) >= 1:
                    self.game_state.undo_move()
                    self.selected_piece = None
                    self.board.clear_highlights()
                    self.update_avatars()

                    # 如果悔棋后轮到AI行动，延迟1秒
                    if self.game_state.player_turn != self.player_camp:
                        self.ai_thinking = True
                        pygame.time.set_timer(pygame.USEREVENT + 2, 1000)

                    return True

        # 重置滚动位置
        self.history_scroll_y = 0

        return False

    def make_random_ai_move(self):
        """当AI思考超时时，执行当前已知的最优移动"""
        if not self.ai or self.game_mode != MODE_PVC:
            return

        # 首先尝试获取AI已计算出的最佳走法
        best_move = self.ai.get_computed_move()
        if best_move is None:
            # 如果没有计算出的走法，则使用AI内部保存的最佳走法
            best_move = self.ai.best_move_so_far

        if best_move is None:
            # 如果仍然没有最佳走法，则随机选择一个移动
            ai_color = "black" if self.player_camp == CAMP_RED else "red"
            valid_moves = []

            for piece in self.game_state.pieces:
                if piece.color == ai_color:
                    possible_moves, _ = self.game_state.calculate_possible_moves(piece.row, piece.col)
                    for to_row, to_col in possible_moves:
                        valid_moves.append(((piece.row, piece.col), (to_row, to_col)))

            if valid_moves:
                best_move = random.choice(valid_moves)

        if best_move:
            self.move_after(best_move)

            # 检查游戏是否结束
            if self.game_state.game_over:
                winner_text = self.game_state.get_winner_text()

                # 更新时间数据，确保获取最终值
                red_time, black_time = self.game_state.update_times()
                total_time = self.game_state.total_time

                # 创建弹窗并传入时间信息
                self.popup = PopupDialog(
                    400, 320,  # 增加高度以适应更多内容
                    winner_text,
                    total_time,
                    red_time,
                    black_time
                )

    def move_after(self, best_move):
        from_pos, to_pos = best_move
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        # 检查目标位置是否有棋子（吃子）
        target_piece = self.game_state.get_piece_at(to_row, to_col)
        # 执行移动
        self.game_state.move_piece(from_row, from_col, to_row, to_col)
        # 记录上一步走法
        self.last_move = (from_row, from_col, to_row, to_col)
        # 生成上一步走法的中文表示
        piece = self.game_state.get_piece_at(to_row, to_col)
        if piece:
            self.last_move_notation = self.generate_move_notation(piece, from_row, from_col, to_row, to_col)
        # 播放音效
        if target_piece:
            try:
                self.sound_manager.play_sound('eat')
            except:
                pass
        else:
            try:
                self.sound_manager.play_sound('drop')
            except:
                pass
        # 播放将军/绝杀音效 - 优先处理绝杀情况，避免重复播放
        if self.game_state.is_checkmate():
            try:
                self.sound_manager.play_sound('warn')  # 使用chess-master的将军音效
                self.sound_manager.play_sound('check')  # 播放绝杀语音
            except:
                pass
        elif self.game_state.is_check:
            try:
                self.sound_manager.play_sound('warn')
                self.sound_manager.play_sound('capture')  # 播放将军语音
            except:
                pass
        # 更新头像状态 - 只需更新一次
        self.update_avatars()

    def update_avatars(self):
        """更新头像状态"""
        is_red_turn = self.game_state.player_turn == "red"
        self.red_avatar.set_active(is_red_turn)
        self.black_avatar.set_active(not is_red_turn)

        # 更新玩家标识
        if self.game_mode == MODE_PVC:
            if self.player_camp == CAMP_RED:
                self.red_avatar.player_name = "玩家"
                self.black_avatar.player_name = "电脑"
            else:
                self.red_avatar.player_name = "电脑"
                self.black_avatar.player_name = "玩家"
        else:
            self.red_avatar.player_name = "红方"
            self.black_avatar.player_name = "黑方"

    def schedule_ai_move(self):
        """安排AI移动"""
        # 设置AI思考开始时间
        self.ai_think_start_time = pygame.time.get_ticks()
        # 立即启动异步AI计算
        self.start_async_ai_computation()
        self.ai_thinking = True

    def start_async_ai_computation(self):
        """启动异步AI计算"""
        # 使用AI进行多线程计算
        # 确保传递的是当前游戏状态的副本或直接传递，AI内部会处理克隆
        self.ai.get_move_async(self.game_state)

    def _compute_ai_move(self):
        """在单独线程中计算AI移动"""
        # AI计算在AI类内部处理，这里不需要实现
        # AI类会通过get_move_async方法处理计算和事件通知
        pass

    def process_async_ai_result(self):
        """处理异步AI计算结果"""
        if not self.ai:
            self.ai_thinking = False
            return

        # 使用AI计算好的最佳走法
        move = self.ai.get_computed_move()

        if move:
            self.move_after(move)
            # from_pos, to_pos = move
            # from_row, from_col = from_pos
            # to_row, to_col = to_pos
            #
            # # 检查目标位置是否有棋子（吃子）
            # target_piece = self.game_state.get_piece_at(to_row, to_col)
            #
            # # 执行移动
            # self.game_state.move_piece(from_row, from_col, to_row, to_col)
            #
            # # 记录上一步走法
            # self.last_move = (from_row, from_col, to_row, to_col)
            #
            # # 生成上一步走法的中文表示
            # piece = self.game_state.get_piece_at(to_row, to_col)
            # if piece:
            #     self.last_move_notation = self.generate_move_notation(piece, from_row, from_col, to_row, to_col)
            #
            # # 播放音效
            # if target_piece:
            #     try:
            #         self.sound_manager.play_sound('eat')
            #     except:
            #         pass
            # else:
            #     try:
            #         self.sound_manager.play_sound('drop')
            #     except:
            #         pass
            #
            # # 播放将军/绝杀音效 - 优先处理绝杀情况，避免重复播放
            # if self.game_state.is_checkmate():
            #     try:
            #         self.sound_manager.play_sound('warn')  # 使用将军语音
            #         self.sound_manager.play_sound('check')  # 播放旧版音效
            #     except:
            #         pass
            # elif self.game_state.is_check:
            #     try:
            #         self.sound_manager.play_sound('warn')
            #         self.sound_manager.play_sound('capture')  # 播放旧版音效
            #     except:
            #         pass
            #
            # # 更新头像状态
            # self.update_avatars()

            # 检查游戏是否结束
            if self.game_state.game_over:
                self.game_over_after()

    def game_over_after(self):
        winner_text = self.game_state.get_winner_text()
        # 更新时间数据，确保获取最终值
        red_time, black_time = self.game_state.update_times()
        total_time = self.game_state.total_time
        # 创建弹窗并传入时间信息
        self.popup = PopupDialog(
            400, 320,  # 增加高度以适应更多内容
            winner_text,
            total_time,
            red_time,
            black_time
        )
        # 根据胜负播放相应的音效
        if self.game_mode == MODE_PVC:  # 人机模式
            if self.player_camp == self.game_state.winner:  # 玩家获胜
                self.sound_manager.play_victory_sound()
            elif self.game_state.winner is not None:  # AI获胜
                self.sound_manager.play_defeat_sound()
            # 平局时不播放音效
