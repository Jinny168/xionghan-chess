import sys

import pygame

from program.config.config import game_config
from program.controllers.input_handler import input_handler
from program.core.game_rules import GameRules
from program.core.game_state import GameState
from program.ui.dialogs import PopupDialog, AudioSettingsDialog, StatisticsDialog
from program.ui.game_screen import GameScreen
from program.utils import tools

# 初始化PyGame
pygame.init()
pygame.mixer.init()  # 初始化音频模块

from program.config.config import (
    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT,
    FPS,
    MODE_PVP, MODE_PVC, CAMP_RED, )
from program.controllers.ai_manager import AIManager


class ChessGame:
    def __init__(self, game_mode=MODE_PVP, player_camp=CAMP_RED, game_settings=None):
        """初始化游戏"""
        self.history_max_visible_lines = 15
        self.history_scroll_y = None
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

        # 初始化AI管理器（如果需要）
        self.ai_manager = AIManager(game_mode, player_camp, game_settings)

        # 初始化界面元素
        self.game_screen = GameScreen(self.window_width, self.window_height, game_mode, player_camp)

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
        self.stats_dialog = None
        self.about_screen = None

        
        # 音效管理器（包含背景音乐功能）
        self.sound_manager = SoundManager()
        # 启动背景音乐
        self.sound_manager.toggle_music_style()  # 设置为QQ风格
        # 如果需要FC风格，可以再次调用toggle_music_style()

    def init_window(self):
        """初始化窗口"""
        self.window_width = DEFAULT_WINDOW_WIDTH
        self.window_height = DEFAULT_WINDOW_HEIGHT
        self.is_fullscreen = True
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("匈汉象棋")
        self.clock = pygame.time.Clock()

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
            self.last_move_notation = tools.generate_move_notation(piece, from_row, from_col, to_row, to_col)

        # 播放音效
        # 优先处理绝杀情况，因为绝杀时is_check和is_checkmate都为True
        if self.game_state.is_checkmate():
            # 绝杀时播放绝杀音效，而不是将军音效
            self.sound_manager.play_sound('warn')  # 使用将军语音
            try:
                self.sound_manager.play_sound('check')  # 播放旧版音效
            except (AttributeError, Exception):
                pass
        elif self.game_state.is_check:
            # 普通将军情况，播放将军音效
            self.sound_manager.play_sound('warn')# 使用将军语音
            try:
                self.sound_manager.play_sound('capture')  # 播放旧版音效
            except (AttributeError, Exception):
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
        if self.ai_manager.is_ai_turn(self.game_state.player_turn):
            self.ai_manager.start_ai_thinking()
            pygame.time.set_timer(pygame.USEREVENT, 1000)  # 1秒后启动AI

    def ai_move(self):
        """AI执行走法"""
        move = self.ai_manager.get_ai_move(self.game_state)
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
        self.stats_dialog = None  # 重置统计数据对话框
        self.ai_manager.reset_ai_state()
        if self.ai_manager.is_ai_turn(self.game_state.player_turn):
            pygame.time.set_timer(pygame.USEREVENT + 1, 800)  # 延迟800毫秒后AI行动
            self.ai_manager.start_ai_thinking()

    def toggle_fullscreen(self):
        """切换全屏模式"""
        # 使用通用的全屏切换函数
        self.screen, self.window_width, self.window_height, self.is_fullscreen, self.windowed_size = \
            tools.toggle_fullscreen(self.screen, self.window_width, self.window_height, self.is_fullscreen, self.windowed_size)

        # 更新界面布局
        self.game_screen.update_layout()

    def handle_resize(self, new_size):
        """处理窗口大小变化"""
        self.window_width, self.window_height = new_size
        # 更新界面布局
        self.game_screen.update_layout()

    def handle_event(self, event, mouse_pos):
        """处理游戏事件"""
        input_handler.handle_event(self, event, mouse_pos)

    def run(self):
        """游戏主循环 - 统一的游戏循环处理PVP和PVC模式"""
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
                        # 如果当前显示关于界面，也需要更新其尺寸
                        if self.about_screen:
                            self.about_screen.update_size(event.w, event.h)

                # 处理AI多线程计算完成事件（仅PVC模式需要）
                if event.type == pygame.USEREVENT + 2 and self.game_mode == MODE_PVC:
                    self.process_async_ai_result()
                    # 清除AI思考状态
                    self.ai_manager.ai_thinking = False

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
                            if self.confirm_dialog and "退出游戏" in getattr(self.confirm_dialog, 'message', ''):
                                # 停止背景音乐
                                self.sound_manager.stop_background_music()
                                # 关闭所有对话框
                                self.popup = None
                                self.confirm_dialog = None
                                self.stats_dialog = None
                                pygame.quit()
                                sys.exit()
                            else:  # 返回主菜单
                                # 停止背景音乐
                                self.sound_manager.stop_background_music()
                                # 关闭所有对话框
                                self.popup = None
                                self.confirm_dialog = None
                                self.stats_dialog = None
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
                # 如果有统计数据对话框，处理它的事件
                elif self.stats_dialog:
                    result = self.stats_dialog.handle_event(event, mouse_pos)
                    if result == "close":
                        self.stats_dialog = None
                    elif result == "reset":
                        # 重置统计数据
                        from program.config.statistics import statistics_manager
                        statistics_manager.reset_statistics()
                        # 重新创建对话框以更新显示
                        self.stats_dialog = StatisticsDialog()
                    # 不管返回什么结果，都要跳过后续的事件处理，防止同时处理其他操作
                    continue  # 跳过后续的事件处理，防止同时处理其他操作
                # 如果有关于界面，处理它的事件
                elif self.about_screen:
                    result = self.about_screen.handle_event(event, mouse_pos)
                    if result == "back":
                        self.about_screen = None
                    # 不管返回什么结果，都要跳过后续的事件处理，防止同时处理其他操作
                    continue  # 跳过后续的事件处理，防止同时处理其他操作
                # 如果游戏结束，处理弹窗事件
                elif self.game_state.game_over and self.popup is not None:
                    result = self.popup.handle_event(event, mouse_pos)
                    if result == "restart":
                        # 在重置游戏之前停止背景音乐
                        self.sound_manager.stop_background_music()
                        # 重置所有对话框
                        self.popup = None
                        self.confirm_dialog = None
                        self.stats_dialog = None
                        self.__init__(self.game_mode, self.player_camp)  # 重置游戏，保持相同模式和阵营
                        # 重新启动背景音乐
                        self.sound_manager.toggle_music_style()
                    elif result == "export":
                        # 导出当前对局
                        from program.controllers.game_io_controller import game_io_controller
                        success = game_io_controller.export_game(self.game_state)
                        # 显示通知
                        if success:
                            # 可以添加成功通知
                            pass
                        else:
                            # 可以添加失败通知
                            pass
                    elif result == "replay":
                        # 进入复盘模式
                        from program.controllers.replay_controller import ReplayController
                        from program.ui.replay_screen import ReplayScreen
                        
                        replay_controller = ReplayController(self.game_state)
                        replay_controller.start_replay()
                        
                        replay_screen = ReplayScreen(self.game_state, replay_controller)
                        replay_screen.run()
                # 如果游戏未结束，处理鼠标点击
                elif not self.game_state.game_over:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        # 检查是否点击了菜单
                        menu_result = self.game_screen.handle_menu_events(event, mouse_pos, self, self.game_state)
                        if menu_result == "handled":
                            continue  # 菜单事件已处理，跳过后续处理

                        # 检查是否点击了操作面板
                        op_result = self.game_screen.handle_operation_panel_events(event, mouse_pos, self, self.game_state)
                        if op_result == "handled":
                            continue  # 操作面板事件已处理，跳过后续处理

                        # 检查是否点击了全屏按钮
                        if self.game_screen.fullscreen_button and self.game_screen.fullscreen_button.is_clicked(mouse_pos, event):
                            self.toggle_fullscreen()
                        # 检查是否点击了音效设置按钮
                        elif self.game_screen.audio_settings_button and self.game_screen.audio_settings_button.is_clicked(mouse_pos, event):
                            # 打开音效设置对话框
                            self.audio_settings_dialog = AudioSettingsDialog(600, 400, self.sound_manager)
                        # 检查是否点击了返回按钮 - 从菜单中调用，不再使用独立按钮
                        # 检查是否点击了退出游戏按钮 - 从菜单中调用，不再使用独立按钮
                        # 检查是否点击了重新开始按钮 - 从菜单中调用，不再使用独立按钮
                        # 检查是否点击了悔棋按钮 - 从菜单中调用，不再使用独立按钮
                        # 检查是否点击了导入棋局按钮 - 从菜单中调用，不再使用独立按钮
                        # 检查是否点击了导出棋局按钮 - 从菜单中调用，不再使用独立按钮
                        # 处理棋子操作
                        elif self._should_handle_player_input():  # 统一判断是否应该处理玩家输入
                            input_handler.handle_click(self,mouse_pos)

            # 检查AI是否思考超时（仅PVC模式需要）
            if (self.game_mode == MODE_PVC and self.ai_manager.ai_thinking and
                    self.ai_manager.check_ai_timeout(current_time)):
                # AI思考超时，强制结束思考
                print("AI思考超时，执行当前已知最佳走法")
                self.ai_manager.reset_ai_state()
                pygame.time.set_timer(pygame.USEREVENT + 2, 0)  # 确保停止所有AI相关计时器

                # 如果是人机模式且轮到AI，执行当前已知最佳走法
                if self.ai_manager.is_ai_turn(self.game_state.player_turn):
                    self.make_random_ai_move()

            # 更新按钮的悬停状态
            self.game_screen.update_button_states(mouse_pos)

            # 检查是否需要触发AI移动（仅PVC模式需要）
            if (self.game_mode == MODE_PVC and
                    not self.game_state.game_over and
                    self.ai_manager.is_ai_turn(self.game_state.player_turn) and
                    not self.ai_manager.ai_thinking):
                self.ai_manager.start_ai_thinking()
                self.ai_manager.start_async_ai_computation(self.game_state)

            # 在AI思考期间，降低刷新率以减少闪烁
            # 确保AI思考时只绘制稳定的主游戏状态，不显示临时的搜索状态
            if self.ai_manager.ai_thinking:
                self.game_screen.draw_thinking_indicator(self.screen, self.game_state)
            else:
                self.game_screen.draw(self.screen, self.game_state, self.last_move, self.last_move_notation, 
                                     self.popup, self.confirm_dialog, self.pawn_resurrection_dialog, 
                                     self.promotion_dialog, self.audio_settings_dialog, self.ai_manager.ai_thinking)
            
            # 如果有统计数据对话框，绘制它
            if self.stats_dialog:
                self.stats_dialog.draw(self.screen)
            # 如果有关于界面，绘制它
            elif self.about_screen:
                self.about_screen.draw(self.screen)
                
            pygame.display.flip()

            # 如果AI正在思考，使用较低的帧率以节省CPU资源并减少闪烁
            if self.game_mode == MODE_PVC and self.ai_manager.ai_thinking:
                self.clock.tick(15)  # 降低到15FPS，平衡性能和视觉效果
            # 如果显示关于界面，也使用较低的帧率
            elif self.about_screen:
                self.clock.tick(30)  # 适中的帧率
            else:
                self.clock.tick(FPS)

    def make_random_ai_move(self):
        """当AI思考超时时，执行当前已知的最优移动"""
        if not self.ai_manager.ai or self.game_mode != MODE_PVC:
            return

        # 使用AI管理器处理超时情况
        best_move = self.ai_manager.handle_ai_timeout(self.game_state)

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
            self.last_move_notation = tools.generate_move_notation(piece, from_row, from_col, to_row, to_col)
        # 播放音效
        if target_piece:
            self.sound_manager.play_sound('eat')
        else:
            self.sound_manager.play_sound('drop')
        # 播放将军/绝杀音效 - 优先处理绝杀情况，避免重复播放

        tools.check_sound_play(self)
        # 更新头像状态 - 只需更新一次
        self.update_avatars()

    def update_avatars(self):
        """更新头像状态"""
        self.game_screen.update_avatars(self.game_state)

    def process_async_ai_result(self):
        """处理异步AI计算结果"""
        # 使用AI管理器处理异步结果
        move = self.ai_manager.process_async_ai_result()

        if move:
            self.move_after(move)
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

    def _should_handle_player_input(self):
        """判断当前是否应该处理玩家输入"""
        if self.game_mode == MODE_PVP:
            # PVP模式：总是处理玩家输入
            return True
        elif self.game_mode == MODE_PVC:
            # PVC模式：只有在玩家回合且AI未在思考时处理输入
            return (not self.ai_manager.ai_thinking and
                    self.game_state.player_turn == self.player_camp)
        return False

    def is_ai_thinking(self):
        """检查AI是否正在思考"""
        return self.ai_manager.ai_thinking

from program.controllers.sound_manager import SoundManager