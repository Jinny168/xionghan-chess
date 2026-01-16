"""
匈汉象棋局域网对战游戏类
"""
import pygame

from program.config.config import (
    LEFT_PANEL_WIDTH_RATIO, BOARD_MARGIN_TOP_RATIO, FPS,
    PANEL_BORDER, BLACK, CAMP_RED
)
from program.config.config import game_config
from program.core.game_state import GameState
from program.game import ChessGame
from program.ui.avatar import Avatar
from program.ui.button import Button
from program.ui.chess_board import ChessBoard
from program.ui.dialogs import PopupDialog, ConfirmDialog
from program.utils.utils import load_font, draw_background
from program.lan.xhlan import XiangqiNetworkGame, SimpleAPI


class NetworkChessGame(ChessGame):
    """网络对战模式的匈汉象棋游戏"""
    
    def __init__(self, is_host=True):
        # 设置网络模式
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
        
        # 初始化网络功能 - 在这里我们不初始化SimpleAPI，因为已在外部完成
        # 我们直接设置XiangqiNetworkGame的game_instance
        XiangqiNetworkGame.game_instance = self
        self.network_game = XiangqiNetworkGame(self)  # 传递当前实例给网络类
        self.setup_network()

    def setup_network(self):
        """设置网络连接"""
        # 设置网络模式，使用已存在的SimpleAPI实例
        role = 'SERVER' if self.is_host else 'CLIENT'
        XiangqiNetworkGame.set_network_mode(role, SimpleAPI.instance)
        print(f"{'主机' if self.is_host else '客户端'}模式初始化完成")

    def init_board_and_ui(self):
        """初始化棋盘和界面元素 - 网络对战模式特化版本"""
        button_width=120
        button_height = 40
        button_y = self.window_height - 60

        # 调用父类的update_layout方法设置基本布局
        self.update_layout()

        # 在网络对战模式中，不创建返回按钮
        # self.back_button = Button(
        #     self.left_panel_width + 80,
        #     button_y,
        #     button_width,
        #     button_height,
        #     "返回",
        #     22
        # )

        # 创建重新开始按钮
        self.restart_button = Button(
            self.left_panel_width + 80,  # 调整位置
            button_y,
            button_width,
            button_height,
            "重来",
            22
        )
        
        # 创建悔棋按钮
        self.undo_button = Button(
            self.left_panel_width + 80 + button_width + 10,  # 紧挨着重来按钮
            button_y,
            button_width,
            button_height,
            "悔棋",
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
        
        # 创建全屏切换按钮
        self.fullscreen_button = Button(
            self.window_width - 100,
            10,
            80,
            30,
            "全屏" if not self.is_fullscreen else "窗口",
            14
        )
        
        # 创建音效设置按钮
        self.audio_settings_button = Button(
            self.window_width - 100,
            50,
            80,
            30,
            "音效设置",
            14
        )

    def update_layout(self):
        """根据当前窗口尺寸更新布局 - 网络对战模式特化版本"""
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

        button_width = 120
        button_height = 40
        button_y = self.window_height - 60

        # 更新重新开始按钮位置
        self.restart_button = Button(
            self.left_panel_width + 80,  # 调整位置
            button_y,
            button_width,
            button_height,
            "重来",
            22
        )
        
        # 更新悔棋按钮位置
        self.undo_button = Button(
            self.left_panel_width + 80 + button_width + 10,  # 紧挨着重来按钮
            button_y,
            button_width,
            button_height,
            "悔棋",
            22
        )
        
        # 更新退出游戏按钮位置
        self.exit_button = Button(
            self.window_width - button_width - 80 - button_width - 10,
            button_y,
            button_width,
            button_height,
            "退出游戏",
            22
        )

        # 更新全屏按钮位置
        self.fullscreen_button = Button(
            self.window_width - 100,
            10,
            80,
            30,
            "全屏" if not self.is_fullscreen else "窗口",
            14
        )
        
        # 更新音效设置按钮位置
        self.audio_settings_button = Button(
            self.window_width - 100,
            50,
            80,
            30,
            "音效设置",
            14
        )

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

    def draw(self, mouse_pos):
        """绘制游戏界面 - 网络对战模式特化版本"""
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

        # 绘制悔棋按钮、重来按钮、退出按钮、全屏按钮和音效设置按钮
        # 注意：在网络对战模式中，我们不绘制返回按钮
        self.undo_button.draw(self.screen)
        self.restart_button.draw(self.screen)
        # self.back_button.draw(self.screen)  # 不绘制返回按钮
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
        # 网络对战模式下不显示这些提示
        # if self.game_mode == MODE_PVC:
        #     mode_font = load_font(18)
        #     if self.player_camp == CAMP_RED:
        #         mode_text = "人机对战模式 - 您执红方"
        #     else:
        #         mode_text = "人机对战模式 - 您执黑方"
        #     mode_surface = mode_font.render(mode_text, True, BLACK)
        #     self.screen.blit(mode_surface, (
        #     self.left_panel_width + (self.window_width - self.left_panel_width) // 2 - mode_surface.get_width() // 2,
        #     15))

        # 如果AI正在思考，显示提示
        # 网络对战模式下不需要显示AI思考提示

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

    def handle_click(self, pos):
        """处理鼠标点击事件 - 网络对战专用"""
        if self.game_state.game_over:
            return

        # 如果不是轮到本地玩家，忽略点击
        if self.game_state.player_turn != self.player_camp:
            return

        # 获取点击的棋盘位置
        grid_pos = self.board.get_grid_position(pos)
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
                
                # 发送移动到对手
                self.send_network_move(sel_row, sel_col, row, col)
                
                # 检查是否需要升变（兵/卒到达对方底线）
                if self.game_state.needs_promotion:
                    # 获取兵的颜色
                    pawn_color = self.game_state.promotion_pawn.color if self.game_state.promotion_pawn else self.game_state.player_turn
                    print(f"[DEBUG] 需要升变: {pawn_color}方兵到达底线")
                    # 自动弹出升变选择对话框
                    from program.ui.dialogs import PromotionDialog
                    self.promotion_dialog = PromotionDialog(
                        500, 400, pawn_color, (row, col), self.game_state.available_promotion_pieces
                    )

                # 记录上一步走法
                self.last_move = (sel_row, sel_col, row, col)

                # 生成上一步走法的中文表示
                piece = self.game_state.get_piece_at(row, col)
                if piece:
                    self.last_move_notation = self.generate_move_notation(piece, sel_row, sel_col, row, col)

                # 播放选子音效
                if self.selected_piece and not captured_piece:
                    try:
                        self.sound_manager.play_sound('choose')
                    except:
                        pass
                
                # 播放移动音效
                if captured_piece:
                    try:
                        self.sound_manager.play_sound('eat')
                    except:
                        pass
                else:
                    try:
                        self.sound_manager.play_sound('drop')
                    except:
                        pass

                # 切换玩家回合（本地玩家移动后，轮到对手）
                # 在网络游戏中，本地玩家移动后，应该将回合交给对手
                # 注意：这里要确保切换到非本地玩家的阵营
                opponent_color = "black" if self.player_camp == "red" else "red"
                self.game_state.player_turn = opponent_color
                print(f"[DEBUG] 移动后切换玩家: {opponent_color} (当前玩家阵营: {self.player_camp})")
                
                # 更新头像状态
                self.update_avatars()

                # 播放将军/绝杀音效
                if self.game_state.is_checkmate():
                    try:
                        self.sound_manager.play_sound('warn')
                        self.sound_manager.play_sound('check')
                    except:
                        pass
                elif self.game_state.is_check:
                    try:
                        self.sound_manager.play_sound('warn')
                        self.sound_manager.play_sound('capture')
                    except:
                        pass

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
                self.board.clear_highlights()

            # 无论如何都取消选择状态
            self.selected_piece = None
            self.board.clear_highlights()

    def send_network_move(self, from_row, from_col, to_row, to_col):
        """发送移动到网络对手"""
        print(f"发送本地移动: {from_row},{from_col} -> {to_row},{to_col}")
        # 调用网络接口发送移动
        try:
            XiangqiNetworkGame.send_move(from_row, from_col, to_row, to_col)
        except Exception as e:
            print(f"发送网络移动失败: {e}")

    def receive_network_move(self, from_row, from_col, to_row, to_col):
        """接收来自网络对手的移动"""
        print(f"[DEBUG] 接收对手移动: {from_row},{from_col} -> {to_row},{to_col}")
        print(f"[DEBUG] 接收前玩家回合: {self.game_state.player_turn}, 本地玩家阵营: {self.player_camp}")
        
        # 执行对手的移动
        success = self.game_state.move_piece(from_row, from_col, to_row, to_col)
        if success:
            print(f"[DEBUG] 对手移动成功执行: {from_row},{from_col} -> {to_row},{to_col}")
            
            # 记录上一步走法
            self.last_move = (from_row, from_col, to_row, to_col)

            # 生成上一步走法的中文表示
            piece = self.game_state.get_piece_at(to_row, to_col)
            if piece:
                self.last_move_notation = self.generate_move_notation(piece, from_row, from_col, to_row, to_col)

            # 播放音效
            captured_piece = self.game_state.get_piece_at(to_row, to_col)
            if captured_piece:
                try:
                    self.sound_manager.play_sound('eat')
                except:
                    pass
            else:
                try:
                    self.sound_manager.play_sound('drop')
                except:
                    pass

            # 更新头像状态
            self.update_avatars()

            # 播放将军/绝杀音效
            if self.game_state.is_checkmate():
                try:
                    self.sound_manager.play_sound('warn')
                    self.sound_manager.play_sound('check')
                except:
                    pass
            elif self.game_state.is_check:
                try:
                    self.sound_manager.play_sound('warn')
                    self.sound_manager.play_sound('capture')
                except:
                    pass

            # 切换玩家回合（这是对手的移动，所以现在轮到本地玩家走棋）
            # 关键：接收到对手的移动后，应该切换到本地玩家的回合
            self.game_state.player_turn = self.player_camp
            print(f"[DEBUG] 收到对手移动后切换到本地玩家: {self.player_camp}")
            self.update_avatars()
        else:
            print(f"[DEBUG] 对手移动执行失败: {from_row},{from_col} -> {to_row},{to_col}")
            # 即使移动失败，也要确保状态正确
            # 如果移动失败，仍应轮到本地玩家走棋（因为对手的移动无效）
            self.game_state.player_turn = self.player_camp
            print(f"[DEBUG] 移动失败，但仍切换到本地玩家: {self.player_camp}")

    def handle_opponent_win(self):
        """处理对手胜利的情况"""
        self.game_state.game_over = True
        self.game_state.winner = "black" if self.player_camp == "red" else "red"
        
        winner_text = self.game_state.get_winner_text()
        # 更新时间数据
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

    def display_chat_message(self, message):
        """显示聊天消息"""
        print(f"收到聊天消息: {message}")
        # 在实际游戏中，这里会在界面上显示聊天消息

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
            if mouse_pos[0] >= right_panel_x and mouse_pos[1] >= 300 and mouse_pos[0] <= self.window_width - 10:
                # 滚动棋谱
                self.history_scroll_y = max(0, self.history_scroll_y - event.y)
                total_moves = len(self.game_state.move_history)
                max_scroll = max(0, total_moves - self.history_max_visible_lines)
                self.history_scroll_y = min(self.history_scroll_y, max_scroll)

        # 处理鼠标点击
        if event.type == pygame.MOUSEBUTTONDOWN:
            # 检查是否点击了全屏按钮
            if hasattr(self, 'fullscreen_button') and self.fullscreen_button.is_clicked(mouse_pos, event):
                self.toggle_fullscreen()
            
            # 检查是否点击了音效设置按钮
            elif hasattr(self, 'audio_settings_button') and self.audio_settings_button.is_clicked(mouse_pos, event):
                from program.ui.dialogs import AudioSettingsDialog
                self.audio_settings_dialog = AudioSettingsDialog(500, 350, self.sound_manager)

            # 检查是否点击了悔棋按钮
            elif hasattr(self, 'undo_button') and self.undo_button.is_clicked(mouse_pos, event):
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
                except:
                    print("发送悔棋请求失败")
                    self.undo_requested = False  # 重置标志，以便可以重试
            
            # 检查是否点击了重新开始按钮
            elif hasattr(self, 'restart_button') and self.restart_button.is_clicked(mouse_pos, event):
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
            
            # 检查是否点击了返回主菜单按钮
            # 在网络对战模式中，我们使用退出按钮代替返回按钮
            # elif self.back_button.is_clicked(mouse_pos, event):
            #     # 发送离开游戏信号并返回主菜单
            #     try:
            #         XiangqiNetworkGame.send_leave_game()
            #     except:
            #         pass
            #     # 返回主菜单而不是退出游戏
            #     self.sound_manager.stop_background_music()
            #     return "back_to_menu"
            
            # 检查是否点击了退出游戏按钮
            elif hasattr(self, 'exit_button') and self.exit_button.is_clicked(mouse_pos, event):
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
            current_time = pygame.time.get_ticks()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # 发送认输信号
                    try:
                        XiangqiNetworkGame.send_resign()
                    except:
                        pass
                    self.sound_manager.stop_background_music()
                    return "back_to_menu"

                # 处理各种事件
                if hasattr(self, 'promotion_dialog') and self.promotion_dialog:
                    result = self.promotion_dialog.handle_event(event, mouse_pos)
                    if result is not None:
                        if isinstance(result, tuple) and result[0]:
                            # 执行升变
                            selected_index = result[1]
                            self.game_state.perform_promotion(selected_index)
                            
                            # 清除升变对话框
                            self.promotion_dialog = None
            
                            # 切换玩家回合 - 升变完成后，轮到对手走棋
                            # 在网络游戏中，升变后同样需要切换到对手
                            opponent_color = "black" if self.player_camp == "red" else "red"
                            self.game_state.player_turn = opponent_color
                            print(f"[DEBUG] 兵升变后切换玩家: {self.player_camp} -> {opponent_color}")
                            self.update_avatars()
                        elif result is False:
                            # 取消升变
                            self.promotion_dialog = None
            
                            # 切换玩家回合 - 即使取消升变，走子机会也已消耗，轮到对手
                            opponent_color = "black" if self.player_camp == "red" else "red"
                            self.game_state.player_turn = opponent_color
                            print(f"[DEBUG] 兵升变取消后切换玩家: {self.player_camp} -> {opponent_color}")
                            self.update_avatars()
                elif hasattr(self, 'pawn_resurrection_dialog') and self.pawn_resurrection_dialog:
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
                            
                            # 切换玩家回合 - 复活棋子后，轮到对手走棋
                            opponent_color = "black" if self.player_camp == "red" else "red"
                            self.game_state.player_turn = opponent_color
                            print(f"[DEBUG] 兵复活后切换玩家: {self.player_camp} -> {opponent_color}")
                            self.update_avatars()
                        else:  # 取消
                            # 清除复活对话框
                            self.pawn_resurrection_dialog = None
                            
                            # 即使取消复活，也应切换回合（因为点击了复活位置）
                            opponent_color = "black" if self.player_camp == "red" else "red"
                            self.game_state.player_turn = opponent_color
                            print(f"[DEBUG] 兵复活取消后切换玩家: {self.player_camp} -> {opponent_color}")
                            self.update_avatars()
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
                                except:
                                    pass
                                self.sound_manager.stop_background_music()
                                return "back_to_menu"
                            else:
                                # 普通确认对话框（如退出游戏）
                                self.confirm_dialog = None
                                # 发送认输信号并退出
                                try:
                                    XiangqiNetworkGame.send_resign()
                                except:
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
                elif self.game_state.game_over and self.popup:
                    if self.popup.handle_event(event, mouse_pos):
                        # 网络对局结束后返回主菜单
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
                    if hasattr(self, 'fullscreen_button') and self.fullscreen_button.is_clicked(mouse_pos, event):
                        self.toggle_fullscreen()
                    
                    # 检查是否点击了音效设置按钮
                    elif hasattr(self, 'audio_settings_button') and self.audio_settings_button.is_clicked(mouse_pos, event):
                        from program.ui.dialogs import AudioSettingsDialog
                        self.audio_settings_dialog = AudioSettingsDialog(500, 350, self.sound_manager)

                    # 检查是否点击了悔棋按钮
                    elif hasattr(self, 'undo_button') and self.undo_button.is_clicked(mouse_pos, event):
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
                        except:
                            print("发送悔棋请求失败")
                            self.undo_requested = False  # 重置标志，以便可以重试
                    
                    # 检查是否点击了重新开始按钮
                    elif hasattr(self, 'restart_button') and self.restart_button.is_clicked(mouse_pos, event):
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
                    elif hasattr(self, 'exit_button') and self.exit_button.is_clicked(mouse_pos, event):
                        # 显示确认对话框确认退出游戏
                        self.confirm_dialog = ConfirmDialog(
                            400, 200, "是否要退出网络对局？\n这将视为认输。"
                        )
                        self.confirm_dialog.type = "exit_game"  # 标记为退出游戏对话框

                    # 处理棋盘点击
                    elif not self.game_state.game_over:
                        self.handle_click(mouse_pos)

            # 更新按钮的悬停状态
            self.undo_button.check_hover(mouse_pos)
            # self.back_button.check_hover(mouse_pos)  # 在网络对战模式中不使用返回按钮
            self.restart_button.check_hover(mouse_pos)
            self.exit_button.check_hover(mouse_pos)
            self.fullscreen_button.check_hover(mouse_pos)
            if hasattr(self, 'audio_settings_button'):
                self.audio_settings_button.check_hover(mouse_pos)

            # 绘制画面
            self.draw(mouse_pos)
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
    
    def perform_undo(self):
        """执行悔棋操作"""
        # 在网络对战中，悔棋需要双方同意
        # 这里需要实现具体的悔棋逻辑
        try:
            # 尝试悔棋操作
            if self.game_state.undo_move():
                print("悔棋成功")
                # 悔棋成功后，GameState的undo_move方法已经处理了回合切换
                # 我们只需更新头像状态即可
                self.update_avatars()
            else:
                print("悔棋失败 - 可能没有足够的移动历史")
        except AttributeError:
            print("悔棋失败 - GameState不支持undo_move方法")
        except Exception as e:
            print(f"悔棋失败 - 错误: {e}")
    
    def perform_restart(self):
        """执行重新开始操作"""
        # 重新开始游戏
        self.game_state = GameState()
        self.selected_piece = None
        self.last_move = None
        self.last_move_notation = ""
        self.popup = None
        self.pawn_resurrection_dialog = None
        self.promotion_dialog = None
        self.audio_settings_dialog = None
        self.confirm_dialog = None
        self.ai_thinking = False
        
        # 重置网络对战特定的状态
        self.undo_requested = False
        self.restart_requested = False
        self.processing_undo_request = False
        self.processing_restart_request = False
        
        # 重置玩家回合（根据玩家阵营）
        self.game_state.player_turn = self.player_camp
        
        # 重置界面元素
        self.board = ChessBoard(
            self.window_width - self.left_panel_width,
            self.window_height,
            self.left_panel_width,
            self.board_margin_top
        )
        
        # 更新头像状态
        self.update_avatars()
        
        print("游戏已重新开始")
    
    def handle_opponent_leave(self):
        """处理对手离开游戏"""
        # 显示提示信息
        self.popup = PopupDialog(
            400, 320,
            "对手离开了游戏",
            0,
            0,
            0
        )
    
    def on_game_restarted(self):
        """当收到游戏重新开始确认时，确保本地状态同步"""
        # 确保界面状态与游戏状态同步
        self.update_avatars()
        
        # 重置任何可能的临时状态
        self.selected_piece = None
        self.last_move = None
        self.last_move_notation = ""
        
        # 清除可能存在的对话框
        self.popup = None
        self.pawn_resurrection_dialog = None
        self.promotion_dialog = None
        self.audio_settings_dialog = None
        self.confirm_dialog = None
        
        # 确保棋盘高亮清除
        if hasattr(self, 'board'):
            self.board.clear_highlights()
