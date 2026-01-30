"""
匈汉象棋局域网对战游戏类
"""
import pygame

from program.controllers.game_config_manager import (
    FPS,
    CAMP_RED, )
from program.controllers.game_config_manager import game_config
from program.controllers.replay_controller import ReplayController
from program.game import ChessGame
from program.lan.xhlan import XiangqiNetworkGame, SimpleAPI
from program.ui.dialogs import PopupDialog, ConfirmDialog
from program.ui.dialogs import PromotionDialog
from program.ui.network_game_screen import NetworkGameScreen
from program.utils import tools


class NetworkChessGame(ChessGame):
    """网络对战模式的匈汉象棋游戏"""
    
    def __init__(self, is_host=True):
        # 设置网络模式
        self.history_max_visible_lines = 15
        self.black_avatar = None
        self.is_host = is_host
        self.network_enabled = True
        self.opponent_connected = False
        
        # 根据是否为主机设置阵营
        self.player_camp = CAMP_RED if is_host else "black"
        
        # 先调用父类的初始化方法
        super().__init__(game_mode="NETWORK", player_camp=self.player_camp, game_settings=game_config.get_all_settings())
        
        self.game_mode = "NETWORK"  # 网络对战模式
        
        # 确保所有必要的对话框属性都被初始化
        self.pawn_resurrection_dialog = None
        self.promotion_dialog = None
        self.audio_settings_dialog = None
        
        # 添加网络对战状态跟踪
        self.undo_requested = False  # 是否已请求悔棋
        self.restart_requested = False  # 是否已请求重新开始
        self.processing_undo_request = False  # 是否正在处理悔棋请求
        self.processing_restart_request = False  # 是否正在处理重新开始请求
        
        # 记录最后移动的玩家，用于悔棋权限控制
        # 游戏开始时，如果是主机（红方），则红方先走，所以最后移动玩家设为红方；
        # 如果是客户端（黑方），则等待红方先走，所以最后移动玩家设为红方
        self.last_moved_player = "red"  # 红方总是先走
        
        # 初始化网络功能 - 在这里我们不初始化SimpleAPI实例，因为已在外部完成
        # 我们直接设置XiangqiNetworkGame的game_instance
        XiangqiNetworkGame.game_instance = self
        self.network_game = XiangqiNetworkGame(self)  # 传递当前实例给网络类
        self.setup_network()
        
        # 使用专门的网络对战界面
        self.game_screen = NetworkGameScreen(self.window_width, self.window_height, self.game_mode, self.player_camp)
        
        # 更新全屏按钮的文本以反映当前状态
        self.game_screen.update_fullscreen_button_text(self.is_fullscreen)

    def setup_network(self):
        """设置网络连接"""
        # 设置网络模式，使用已存在的SimpleAPI实例
        role = 'SERVER' if self.is_host else 'CLIENT'
        XiangqiNetworkGame.set_network_mode(role, SimpleAPI.instance)
        print(f"{'主机' if self.is_host else '客户端'}模式初始化完成")
    
    def toggle_fullscreen(self):
        """切换全屏模式"""
        # 使用通用的全屏切换函数
        self.screen, self.window_width, self.window_height, self.is_fullscreen, self.windowed_size = \
            tools.toggle_fullscreen(self.window_width, self.window_height, self.is_fullscreen, self.windowed_size)

        # 更新界面布局
        self.game_screen.update_layout()
        
        # 更新全屏按钮的文本
        self.game_screen.update_fullscreen_button_text(self.is_fullscreen)

    def draw(self):
        """绘制游戏界面 - 网络对战模式特化版本"""
        # 使用专门的网络对战界面绘制
        self.game_screen.draw(
            self.screen, self.game_state, self.last_move, self.last_move_notation,
            self.popup, self.confirm_dialog, self.pawn_resurrection_dialog,
            self.promotion_dialog, self.audio_settings_dialog
        )

    def handle_click(self, pos):
        """处理鼠标点击事件 - 网络对战专用"""
        if self.game_state.game_over:
            return

        # 如果不是轮到本地玩家，忽略点击
        if self.game_state.player_turn != self.player_camp:
            return

        # 获取点击的棋盘位置
        grid_pos = self.game_screen.board.get_grid_position(pos)
        if not grid_pos:
            return

        row, col = grid_pos

        # 如果正在等待升变选择，不处理棋盘点击
        if hasattr(self, 'promotion_dialog') and self.promotion_dialog:
            return

        # 检查是否点击了空闲的兵/卒起始位置，触发复活对话框
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
                        from program.ui.dialogs import PawnResurrectionDialog
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
                self.game_screen.board.highlight_position(row, col)

                # 计算可能的移动位置
                possible_moves, capturable = self.game_state.calculate_possible_moves(row, col)
                self.game_screen.board.set_possible_moves(possible_moves)
                self.game_screen.board.set_capturable_positions(capturable)
        else:
            sel_row, sel_col = self.selected_piece

            # 检查是否点击了同一个棋子（取消选择）
            if sel_row == row and sel_col == col:
                self.selected_piece = None
                self.game_screen.board.clear_highlights()
                return

            # 检查是否选择了另一个己方棋子（更换选择）
            new_piece = self.game_state.get_piece_at(row, col)
            if new_piece and new_piece.color == self.game_state.player_turn:
                self.selected_piece = (row, col)
                self.game_screen.board.highlight_position(row, col)

                # 计算新选择棋子的可能移动
                possible_moves, capturable = self.game_state.calculate_possible_moves(row, col)
                self.game_screen.board.set_possible_moves(possible_moves)
                self.game_screen.board.set_capturable_positions(capturable)
                return

            # 已选择棋子，尝试移动
            captured_piece = self.game_state.get_piece_at(row, col)
            move_successful = self.game_state.move_piece(sel_row, sel_col, row, col)

            if move_successful:
                print(f"[DEBUG] 移动成功: {sel_row},{sel_col} -> {row},{col}")
                
                # 发送移动到对手
                self.send_network_move(sel_row, sel_col, row, col)
                
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
                    from program.utils import tools
                    self.last_move_notation = tools.generate_move_notation(piece, sel_row, sel_col, row, col)

                # 播放选子音效
                if self.selected_piece and not captured_piece:
                    try:
                        self.sound_manager.play_sound('choose')
                    except (AttributeError, KeyError):
                        pass
                
                # 播放移动音效
                if captured_piece:
                    try:
                        self.sound_manager.play_sound('eat')
                    except (AttributeError, KeyError):
                        pass
                else:
                    try:
                        self.sound_manager.play_sound('drop')
                    except (AttributeError, KeyError):
                        pass

                # 记录最后移动的玩家（当前玩家）
                self.last_moved_player = self.player_camp
                print(f"[DEBUG] 记录最后移动玩家: {self.player_camp}")
                
                # 切换玩家回合（本地玩家移动后，轮到对手）
                # 在网络游戏中，本地玩家移动后，应该将回合交给对手
                # 注意：这里要确保切换到非本地玩家的阵营
                opponent_color = "black" if self.player_camp == "red" else "red"
                self.game_state.player_turn = opponent_color
                print(f"[DEBUG] 移动后切换玩家: {opponent_color} (当前玩家阵营: {self.player_camp})")
                
                # 更新头像状态
                self.update_avatars()

                # 播放将军/绝杀音效
                self.check_sound_play()

                # 移动完成后清除所有高亮显示
                self.game_screen.board.clear_highlights()
                self.selected_piece = None

                # 检查游戏是否结束
                if self.game_state.game_over:
                    winner_text = self.game_state.get_winner_text()

                    # 更新时间数据，确保获取最终值
                    red_time, black_time = self.game_state.update_times()
                    total_time = self.game_state.total_time

                    # 创建弹窗并传入时间信息
                    self.popup = PopupDialog(
                        400, 320,
                        winner_text,
                        total_time,
                        red_time,
                        black_time
                    )
            else:
                # 移动失败，可能是由于会导致送将，取消选择但不执行移动
                self.selected_piece = None
                self.game_screen.board.clear_highlights()

            # 无论如何都取消选择状态
            self.selected_piece = None
            self.game_screen.board.clear_highlights()

    def check_sound_play(self):
        # 检查游戏是否结束
        if self.game_state.game_over:
            return
        
        # 使用SoundManager中的通用方法播放将军/绝杀音效
        self.sound_manager.check_and_play_game_sound(self.game_state)

    @staticmethod
    def send_network_move(from_row, from_col, to_row, to_col):
        """发送移动到网络对手"""
        print(f"发送本地移动: {from_row},{from_col} -> {to_row},{to_col}")
        # 调用网络接口发送移动
        try:
            XiangqiNetworkGame.send_move(from_row, from_col, to_row, to_col)
        except (ConnectionError, TimeoutError, RuntimeError) as e:
            print(f"发送网络移动失败: {e}")

    def receive_network_move(self, from_row, from_col, to_row, to_col):
        """接收来自网络对手的移动"""
        print(f"[DEBUG] 接收对手移动: {from_row},{from_col} -> {to_row},{to_col}")
        print(f"[DEBUG] 接收前玩家回合: {self.game_state.player_turn}, 本地玩家阵营: {self.player_camp}")
        
        # 记录最后移动的玩家（对手）
        self.last_moved_player = "black" if self.player_camp == "red" else "red"
        
        # 执行对手的移动
        success = self.game_state.move_piece(from_row, from_col, to_row, to_col)
        if success:
            print(f"[DEBUG] 对手移动成功执行: {from_row},{from_col} -> {to_row},{to_col}")
            
            # 记录上一步走法
            self.last_move = (from_row, from_col, to_row, to_col)

            # 生成上一步走法的中文表示
            piece = self.game_state.get_piece_at(to_row, to_col)
            if piece:
                from program.utils import tools
                self.last_move_notation = tools.generate_move_notation(piece, from_row, from_col, to_row, to_col)

            # 播放音效
            captured_piece = self.game_state.get_piece_at(to_row, to_col)
            if captured_piece:
                try:
                    self.sound_manager.play_sound('eat')
                except (AttributeError, KeyError):
                    pass
            else:
                try:
                    self.sound_manager.play_sound('drop')
                except :
                    pass

            # 更新头像状态
            self.update_avatars()

            # 播放将军/绝杀音效
            self.check_sound_play()

            # 切换玩家回合（这是对手的移动，所以现在轮到本地玩家走棋）
            # 关键：接收到对手的移动后，应该切换到本地玩家的回合
            self.game_state.player_turn = self.player_camp
            print(f"[DEBUG] 收到对手移动后切换到本地玩家: {self.player_camp}")
            self.update_avatars()
        else:
            print(f"[DEBUG] 对手移动执行失败: {from_row},{from_col} -> {to_row},{to_col}")
            # 移动失败可能是因为违反了游戏规则或导致送将等情况
            # 在这种情况下，需要谨慎处理状态，避免与正在进行的重启请求冲突
            if not self.processing_restart_request:  # 如果没有在处理重启请求
                # 如果移动失败，说明对手的移动不合法，但我们仍应切换到本地玩家回合
                # 因为对手尝试了一次移动，只是这次移动不合法
                self.game_state.player_turn = self.player_camp
                print(f"[DEBUG] 移动失败，但仍切换到本地玩家: {self.player_camp}")
                self.update_avatars()
            else:
                print("[DEBUG] 移动失败但正在处理重启请求，跳过玩家切换")

    def handle_opponent_win(self):
        """处理对手胜利的情况"""
        self.game_state.game_over = True
        self.game_state.winner = "black" if self.player_camp == "red" else "red"
        
        winner_text = self.game_state.get_winner_text()
        # 更新时间数据
        red_time, black_time = self.game_state.update_times()
        total_time = self.game_state.total_time

        # 创建弹窗并传入时间信息
        self.popup = PopupDialog(400, 320,
            winner_text,
            total_time,
            red_time,
            black_time
        )

    def perform_restart(self):
        """执行重新开始游戏"""
        self._reset_common_game_state()
        
        # 重新设置玩家回合
        if self.is_host:
            self.game_state.player_turn = "red"  # 主机执红
            self.last_moved_player = "red"  # 主机先走
        else:
            self.game_state.player_turn = "black"  # 客户端执黑
            self.last_moved_player = "red"  # 红方先走，所以黑方等待红方走棋
        
        # 更新悔棋按钮状态
        self.update_undo_button_state()

    def perform_undo(self):
        """执行悔棋操作"""
        # 悔棋操作通常会回退到上一个状态
        if len(self.game_state.move_history) >= 2:
            # 回退两步（对手的移动和自己的上一步）
            self.game_state.undo_move()
            self.game_state.undo_move()
            
            # 切换回本地玩家的回合，因为悔棋后应该轮到本地玩家走棋
            self.game_state.player_turn = self.player_camp
            
            # 更新最后移动的玩家为当前玩家（因为悔棋后轮到当前玩家走棋）
            self.last_moved_player = self.player_camp
            
            # 更新悔棋按钮状态
            self.update_undo_button_state()
            
            # 更新界面
            self.selected_piece = None
            self.last_move = None
            self.last_move_notation = ""
            
            # 更新头像状态
            self.update_avatars()

    def _reset_common_game_state(self):
        """重置游戏状态的公共方法"""
        # 重置游戏状态
        self.game_state.reset()
        
        # 重置相关变量
        self.selected_piece = None
        self.last_move = None
        self.last_move_notation = ""
        self.popup = None
        self.confirm_dialog = None
        self.pawn_resurrection_dialog = None
        self.promotion_dialog = None
        self.undo_requested = False
        self.restart_requested = False
        
        # 重置最后移动玩家为红方（游戏开始时红方先走）
        self.last_moved_player = "red"
        
        # 重置界面状态
        self.game_screen.board.clear_highlights()
        self.game_screen.board.set_possible_moves([])
        self.game_screen.board.set_capturable_positions([])
        
        # 重置头像状态
        self.update_avatars()

    @staticmethod
    def display_chat_message(message):
        """显示聊天消息"""
        print(f"收到聊天消息: {message}")

    def handle_event(self, event, mouse_pos):
        """处理游戏事件 - 网络对战专用"""
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

        # 处理鼠标滚轮事件
        if event.type == pygame.MOUSEWHEEL:
            # 检查鼠标是否在棋谱区域
            right_panel_x = self.window_width - 350
            if right_panel_x <= mouse_pos[0] <= self.window_width - 10 and mouse_pos[1] >= 300:
                # 滚动棋谱
                self.history_scroll_y = max(0, self.history_scroll_y - event.y)
                total_moves = len(self.game_state.move_history)
                max_scroll = max(0, total_moves - self.history_max_visible_lines)
                self.history_scroll_y = min(self.history_scroll_y, max_scroll)

        # 处理鼠标点击
        if event.type == pygame.MOUSEBUTTONDOWN:
            # 检查是否点击了全屏按钮
            if hasattr(self.game_screen, 'fullscreen_button') and self.game_screen.fullscreen_button.is_clicked(mouse_pos, event):
                self.toggle_fullscreen()
            
            # 检查是否点击了音效设置按钮
            elif hasattr(self.game_screen, 'audio_settings_button') and self.game_screen.audio_settings_button.is_clicked(mouse_pos, event):
                from program.ui.dialogs import AudioSettingsDialog
                self.audio_settings_dialog = AudioSettingsDialog(500, 350, self.sound_manager)

            # 检查是否点击了悔棋按钮
            elif (hasattr(self.game_screen, 'undo_button') and self.game_screen.undo_button and 
                  self.game_screen.undo_button.is_clicked(mouse_pos, event) and 
                  hasattr(self.game_screen.undo_button, 'enabled') and self.game_screen.undo_button.enabled):
                # 悔棋只能由最后移动的玩家发起
                if self.last_moved_player != self.player_camp:
                    print("只有最后移动的玩家才能发起悔棋")
                    return
                
                # 检查是否已经发起了悔棋请求
                if hasattr(self, 'undo_requested') and self.undo_requested:
                    print("已有悔棋请求在处理中，请稍候...")
                    return  # 避免重复请求
                
                # 设置请求标志
                self.undo_requested = True
                # 网络模式下需要请求对手同意悔棋
                print("请求对手同意悔棋...")
                # 发送悔棋请求到对手
                try:
                    XiangqiNetworkGame.send_undo_request()
                except (ConnectionError, TimeoutError) as e:
                    print(f"发送悔棋请求失败: {e}")
                    self.undo_requested = False  # 重置标志，以便可以重试
            
            # 检查是否点击了重新开始按钮
            elif hasattr(self.game_screen, 'restart_button') and self.game_screen.restart_button and self.game_screen.restart_button.is_clicked(mouse_pos, event):
                # 检查是否已经发起了重新开始请求
                if hasattr(self, 'restart_requested') and self.restart_requested:
                    print("已有重新开始请求在处理中，请稍候...")
                    return  # 避免重复请求
                
                # 检查是否正在处理重启请求
                if hasattr(self, 'processing_restart_request') and self.processing_restart_request:
                    print("正在处理重启请求，请稍候...")
                    return  # 避免重复请求
                
                # 设置请求标志
                self.restart_requested = True
                # 网络模式下需要请求对手同意重新开始
                print("请求对手同意重新开始...")
                # 发送重新开始请求到对手
                try:
                    XiangqiNetworkGame.send_restart_request()
                    print("已发送重新开始请求")
                except Exception as e:
                    print(f"发送重新开始请求失败: {e}")
                    self.restart_requested = False  # 重置标志，以便可以重试
            
            # 检查是否点击了退出游戏按钮
            elif hasattr(self.game_screen, 'exit_button') and self.game_screen.exit_button and self.game_screen.exit_button.is_clicked(mouse_pos, event):
                # 检查是否已经存在确认对话框，避免重复创建
                if self.confirm_dialog is None:
                    # 显示确认对话框确认退出游戏
                    self.confirm_dialog = ConfirmDialog(
                        400, 200, "是否要退出网络对局？\n这将视为认输。"
                    )
                    self.confirm_dialog.type = "exit_game"  # 标记为退出游戏对话框

            # 处理棋盘点击
            elif not self.game_state.game_over:
                self.handle_click(mouse_pos)

    def run(self):
        """网络对战游戏主循环"""
        while True:
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # 发送认输信号
                    try:
                        XiangqiNetworkGame.send_resign()
                    except (ConnectionError, TimeoutError):
                        pass
                    self.sound_manager.stop_background_music()
                    return "back_to_menu"

                # 处理各种事件
                if hasattr(self, 'promotion_dialog') and self.promotion_dialog is not None:
                    result = self.promotion_dialog.handle_event(event, mouse_pos)
                    if result is not None:
                        if isinstance(result, tuple) and result[0]:
                            # 执行升变
                            selected_index = result[1]
                            self.game_state.perform_promotion(selected_index)
                            
                            # 清除升变对话框
                            self.promotion_dialog = None

                            # 记录最后移动的玩家（当前玩家）
                            self.last_moved_player = self.player_camp
                            print(f"[DEBUG] 兵升变后记录最后移动玩家: {self.player_camp}")
                            
                            # 切换玩家回合 - 升变完成后，轮到对手走棋
                            # 在网络游戏中，升变后同样需要切换到对手
                            opponent_color = "black" if self.player_camp == "red" else "red"
                            self.game_state.player_turn = opponent_color
                            print(f"[DEBUG] 兵升变后切换玩家: {self.player_camp} -> {opponent_color}")
                            self.update_avatars()
                            
                            # 跳过后续事件处理，防止同时处理其他操作
                            continue
                        elif result is False:
                            # 取消升变
                            self.promotion_dialog = None
        
                            # 切换玩家回合 - 即使取消升变，走子机会也已消耗，轮到对手
                            opponent_color = "black" if self.player_camp == "red" else "red"
                            self.game_state.player_turn = opponent_color
                            print(f"[DEBUG] 兵升变取消后切换玩家: {self.player_camp} -> {opponent_color}")
                            self.update_avatars()
                            
                            # 跳过后续事件处理，防止同时处理其他操作
                            continue
                elif hasattr(self, 'pawn_resurrection_dialog') and self.pawn_resurrection_dialog is not None:
                    result = self.pawn_resurrection_dialog.handle_event(event, mouse_pos)
                    if result is not None:  # 用户已做出选择
                        if result:  # 确认复活
                            # 执行复活逻辑
                            current_player = self.game_state.player_turn
                            # 获取复活位置
                            resurrection_pos = self.pawn_resurrection_dialog.position
                        
                            # 执行复活
                            self.game_state.perform_pawn_resurrection(current_player, resurrection_pos)
                            
                            # 清除复活对话框
                            self.pawn_resurrection_dialog = None
                        
                            # 记录最后移动的玩家（当前玩家）
                            self.last_moved_player = self.player_camp
                            print(f"[DEBUG] 兵复活后记录最后移动玩家: {self.player_camp}")
                            
                            # 切换玩家回合 - 复活棋子后，轮到对手走棋
                            opponent_color = "black" if self.player_camp == "red" else "red"
                            self.game_state.player_turn = opponent_color
                            print(f"[DEBUG] 兵复活后切换玩家: {self.player_camp} -> {opponent_color}")
                            self.update_avatars()
                            
                            # 跳过后续事件处理，防止同时处理其他操作
                            continue
                        else:  # 取消
                            # 清除复活对话框
                            self.pawn_resurrection_dialog = None
                        
                            # 记录最后移动的玩家（当前玩家）
                            self.last_moved_player = self.player_camp
                            print(f"[DEBUG] 兵复活取消后记录最后移动玩家: {self.player_camp}")
                            
                            # 即使取消复活，也应切换回合（因为点击了复活位置）
                            opponent_color = "black" if self.player_camp == "red" else "red"
                            self.game_state.player_turn = opponent_color
                            print(f"[DEBUG] 兵复活取消后切换玩家: {self.player_camp} -> {opponent_color}")
                            self.update_avatars()
                            
                            # 跳过后续事件处理，防止同时处理其他操作
                            continue
                elif hasattr(self, 'confirm_dialog') and self.confirm_dialog:
                    result = self.confirm_dialog.handle_event(event, mouse_pos)
                    if result is not None:
                        if result:
                            # 检查确认对话框的类型
                            dialog_type = getattr(self.confirm_dialog, 'type', None)
                            
                            if dialog_type == "undo_request":
                                # 同意悔棋请求
                                XiangqiNetworkGame.send_undo_response(True)
                                self.perform_undo()
                                self.confirm_dialog = None  # 清除对话框
                            elif dialog_type == "restart_request":
                                # 同意重新开始请求
                                XiangqiNetworkGame.send_restart_response(True)
                                self.perform_restart()
                                self.confirm_dialog = None  # 清除对话框
                            elif dialog_type == "exit_game":
                                # 退出游戏确认
                                self.confirm_dialog = None
                                # 发送认输信号并退出
                                try:
                                    XiangqiNetworkGame.send_resign()
                                except (ConnectionError, TimeoutError):
                                    pass
                                self.sound_manager.stop_background_music()
                                return "back_to_menu"
                            else:
                                # 普通确认对话框（如退出游戏）
                                self.confirm_dialog = None
                                # 发送认输信号并退出
                                try:
                                    XiangqiNetworkGame.send_resign()
                                except (ConnectionError, TimeoutError):
                                    pass
                                self.sound_manager.stop_background_music()
                                return "back_to_menu"
                        else:
                            # 用户点击了"否"或取消
                            dialog_type = getattr(self.confirm_dialog, 'type', None)
                            
                            if dialog_type == "undo_request":
                                # 拒绝悔棋请求
                                XiangqiNetworkGame.send_undo_response(False)
                                self.confirm_dialog = None  # 清除对话框
                            elif dialog_type == "restart_request":
                                # 拒绝重新开始请求
                                XiangqiNetworkGame.send_restart_response(False)
                                self.confirm_dialog = None  # 清除对话框
                            elif dialog_type == "exit_game":
                                # 取消退出游戏
                                self.confirm_dialog = None
                            else:
                                self.confirm_dialog = None
                elif self.game_state.game_over:
                    # 即使没有弹窗，也要检查是否需要创建
                    if self.popup is None:
                        print("[DEBUG] 网络对战模式 - 游戏已结束，但弹窗尚未创建，正在创建弹窗")
                        # 创建弹窗
                        winner_text = self.game_state.get_winner_text()
                        red_time, black_time = self.game_state.update_times()
                        total_time = self.game_state.total_time
                        self.popup = PopupDialog(400, 320, winner_text, total_time, red_time, black_time)
                    # 处理弹窗事件
                    if self.popup:
                        popup_result = self.popup.handle_event(event, mouse_pos)
                        if popup_result == "restart":
                            # 网络对局结束后返回主菜单
                            self.sound_manager.stop_background_music()
                            return "back_to_menu"
                        elif popup_result == "replay":
                            # 进入复盘模式

                            from program.ui.replay_screen import ReplayScreen
                        
                            # 创建复盘控制器
                            replay_controller = ReplayController.enter_replay_mode(self.game_state)
                            
                            # 创建并运行复盘界面
                            replay_screen = ReplayScreen(self.game_state, replay_controller)
                            replay_screen.run()
                            
                            # 复盘结束后可能需要一些清理工作
                            # （例如，可能需要重新绘制游戏界面）
                        elif popup_result == "return":
                            # 返回主菜单
                            self.sound_manager.stop_background_music()
                            return "back_to_menu"
                elif self.audio_settings_dialog:
                    result = self.audio_settings_dialog.handle_event(event, mouse_pos)
                    if result == "ok":  # 确认设置
                        self.audio_settings_dialog = None
                    elif result == "cancel":  # 取消设置
                        self.audio_settings_dialog = None
                    elif result == "reset":  # 重置设置
                        # 对话框保持打开，但重置值
                        pass
                    elif result == "volume_changed" or result == "style_changed":  # 音量改变或风格切换
                        # 对话框保持打开
                        pass
                    # 不管返回什么结果，都要跳过后续的事件处理，防止同时处理其他操作
                    continue  # 跳过后续的事件处理，防止同时处理其他操作
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # 检查是否点击了全屏按钮
                    if hasattr(self.game_screen, 'fullscreen_button') and self.game_screen.fullscreen_button.is_clicked(mouse_pos, event):
                        self.toggle_fullscreen()
                    
                    # 检查是否点击了音效设置按钮
                    elif hasattr(self.game_screen, 'audio_settings_button') and self.game_screen.audio_settings_button.is_clicked(mouse_pos, event):
                        from program.ui.dialogs import AudioSettingsDialog
                        self.audio_settings_dialog = AudioSettingsDialog(500, 350, self.sound_manager)

                    # 检查是否点击了悔棋按钮
                    elif (hasattr(self.game_screen, 'undo_button') and self.game_screen.undo_button and 
                          self.game_screen.undo_button.is_clicked(mouse_pos, event) and 
                          hasattr(self.game_screen.undo_button, 'enabled') and self.game_screen.undo_button.enabled):
                        # 悔棋只能由最后移动的玩家发起
                        if self.last_moved_player != self.player_camp:
                            print("只有最后移动的玩家才能发起悔棋")
                            continue
                    
                        # 检查是否已经发起了悔棋请求
                        if hasattr(self, 'undo_requested') and self.undo_requested:
                            print("已有悔棋请求在处理中，请稍候...")
                            continue  # 避免重复请求
                        
                        # 设置请求标志
                        self.undo_requested = True
                        # 网络模式下需要请求对手同意悔棋
                        print("请求对手同意悔棋...")
                        # 发送悔棋请求到对手
                        try:
                            XiangqiNetworkGame.send_undo_request()
                        except (ConnectionError, TimeoutError, RuntimeError) as e:
                            print(f"发送悔棋请求失败: {e}")
                            self.undo_requested = False  # 重置标志，以便可以重试
                    
                    # 检查是否点击了重新开始按钮
                    elif hasattr(self.game_screen, 'restart_button') and self.game_screen.restart_button and self.game_screen.restart_button.is_clicked(mouse_pos, event):
                        # 检查是否已经发起了重新开始请求
                        if hasattr(self, 'restart_requested') and self.restart_requested:
                            print("已有重新开始请求在处理中，请稍候...")
                            continue  # 避免重复请求
                        
                        # 检查是否正在处理重启请求
                        if hasattr(self, 'processing_restart_request') and self.processing_restart_request:
                            print("正在处理重启请求，请稍候...")
                            continue  # 避免重复请求
                        
                        # 设置请求标志
                        self.restart_requested = True
                        # 网络模式下需要请求对手同意重新开始
                        print("请求对手同意重新开始...")
                        # 发送重新开始请求到对手
                        try:
                            XiangqiNetworkGame.send_restart_request()
                            print("已发送重新开始请求")
                        except (ConnectionError, TimeoutError, RuntimeError) as e:
                            print(f"发送重新开始请求失败: {e}")
                            self.restart_requested = False  # 重置标志，以便可以重试
                    
                    # 检查是否点击了退出游戏按钮
                    elif hasattr(self.game_screen, 'exit_button') and self.game_screen.exit_button and self.game_screen.exit_button.is_clicked(mouse_pos, event):
                        # 检查是否已经存在确认对话框，避免重复创建
                        if self.confirm_dialog is None:
                            # 显示确认对话框确认退出游戏
                            self.confirm_dialog = ConfirmDialog(
                                400, 200, "是否要退出网络对局？\n这将视为认输。"
                            )
                            self.confirm_dialog.type = "exit_game"  # 标记为退出游戏对话框

                    # 处理棋盘点击
                    elif not self.game_state.game_over:
                        self.handle_click(mouse_pos)

            # 更新按钮的悬停状态
            self.game_screen.update_button_states(mouse_pos)
            
            # 更新悔棋按钮的状态
            self.update_undo_button_state()

            # 绘制画面
            self.draw()
            # 绘制将军/绝杀提示
            self.check_checkmate_tip_manager.draw_tip(self.screen, self.game_state, self.game_screen.board)
            pygame.display.flip()
            self.clock.tick(FPS)
    
    def request_undo_confirmation(self):
        """请求本地玩家确认是否同意悔棋"""
        # 检查是否已经在处理悔棋请求
        if hasattr(self, 'processing_undo_request') and self.processing_undo_request:
            return  # 避免重复请求
        
        # 设置处理标志
        self.processing_undo_request = True
        
        # 显示一个确认对话框
        self.confirm_dialog = ConfirmDialog(
            400, 200, "对手请求悔棋，\n是否同意？"
        )
        # 特殊标记这个对话框是悔棋请求
        self.confirm_dialog.type = "undo_request"
    
    def handle_undo_response(self, accepted):
        """处理对手对悔棋请求的回复"""
        if accepted:
            print("对手同意悔棋，执行悔棋操作")
            # 执行悔棋操作
            self.perform_undo()
            # 重置悔棋请求状态
            self.undo_requested = False
            self.processing_undo_request = False
        else:
            print("对手拒绝悔棋请求")
            # 重置悔棋请求状态
            self.undo_requested = False
            self.processing_undo_request = False
            # 可以显示提示信息
            pass
    
    def request_restart_confirmation(self):
        """请求本地玩家确认是否同意重新开始"""
        # 检查是否已经在处理重新开始请求
        if hasattr(self, 'processing_restart_request') and self.processing_restart_request:
            return  # 避免重复请求
        
        # 设置处理标志
        self.processing_restart_request = True
        
        # 显示一个确认对话框
        self.confirm_dialog = ConfirmDialog(
            400, 200, "对手请求重新开始，\n是否同意？"
        )
        # 特殊标记这个对话框是重新开始请求
        self.confirm_dialog.type = "restart_request"
    
    def handle_restart_response(self, accepted):
        """处理对手对重新开始请求的回复"""
        if accepted:
            print("对手同意重新开始，执行重新开始操作")
            # 执行重新开始操作
            self.perform_restart()
            # 重置重新开始请求状态
            self.restart_requested = False
            self.processing_restart_request = False
        else:
            print("对手拒绝重新开始请求")
            # 重置重新开始请求状态
            self.restart_requested = False
            self.processing_restart_request = False
            # 可以显示提示信息
            pass

    def handle_game_restart_confirmation(self):
        """处理游戏重新开始确认信号 - 确保双方状态同步"""
        print("收到游戏重新开始确认，确保状态同步")
        # 确保游戏状态完全同步
        self.perform_restart()
    
    def update_avatars(self):
        """更新头像状态"""
        self.game_screen.update_avatars(self.game_state, self.is_host)
        
    def update_undo_button_state(self):
        """更新悔棋按钮的可用性状态"""
        if hasattr(self.game_screen, 'undo_button') and self.game_screen.undo_button:
            # 悔棋按钮只有在是最后移动的玩家时才可用
            can_request_undo = (self.last_moved_player == self.player_camp) and not self.game_state.game_over
            
            # 添加一个enabled属性到按钮对象，如果不存在的话
            if not hasattr(self.game_screen.undo_button, 'enabled'):
                self.game_screen.undo_button.enabled = True
            
            self.game_screen.undo_button.enabled = can_request_undo