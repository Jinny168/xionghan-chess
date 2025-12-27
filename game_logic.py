"""游戏逻辑模块，包含游戏核心逻辑和交互处理"""
import pygame
from config import CAMP_RED, MODE_PVP, MODE_PVC
from dialogs import ConfirmDialog, PopupDialog
from ui_elements import Button


class GameLogic:
    """处理游戏核心逻辑"""
    def __init__(self, game_instance):
        self.game = game_instance
        self.selected_piece = None
        self.last_move = None
        self.last_move_notation = ""

    def handle_click(self, pos):
        """处理鼠标点击事件"""
        # 获取点击的棋盘位置
        grid_pos = self.game.board.get_grid_position(pos)
        if not grid_pos:
            return

        row, col = grid_pos

        # 选择棋子或移动棋子
        if self.selected_piece is None:
            # 尝试选择棋子
            piece = self.game.game_state.get_piece_at(row, col)
            if piece and piece.color == self.game.game_state.player_turn:
                self.selected_piece = (row, col)
                self.game.board.highlight_position(row, col)

                # 计算可能的移动位置
                possible_moves, capturable = self.game.game_state.calculate_possible_moves(row, col)
                self.game.board.set_possible_moves(possible_moves)
                self.game.board.set_capturable_positions(capturable)
        else:
            sel_row, sel_col = self.selected_piece

            # 检查是否点击了同一个棋子（取消选择）
            if sel_row == row and sel_col == col:
                self.selected_piece = None
                self.game.board.clear_highlights()
                return

            # 检查是否选择了另一个己方棋子（更换选择）
            new_piece = self.game.game_state.get_piece_at(row, col)
            if new_piece and new_piece.color == self.game.game_state.player_turn:
                self.selected_piece = (row, col)
                self.game.board.highlight_position(row, col)

                # 计算新选择棋子的可能移动
                possible_moves, capturable = self.game.game_state.calculate_possible_moves(row, col)
                self.game.board.set_possible_moves(possible_moves)
                self.game.board.set_capturable_positions(capturable)
                return

            # 已选择棋子，尝试移动
            captured_piece = self.game.game_state.get_piece_at(row, col)
            move_successful = self.game.game_state.move_piece(sel_row, sel_col, row, col)

            if move_successful:
                # 记录上一步走法
                self.last_move = (sel_row, sel_col, row, col)

                # 生成上一步走法的中文表示
                piece = self.game.game_state.get_piece_at(row, col)
                if piece:
                    self.last_move_notation = self.game.generate_move_notation(piece, sel_row, sel_col, row, col)

                # 播放移动音效
                if captured_piece:
                    try:
                        self.game.sound_manager.play_capture_sound()
                    except:
                        pass
                else:
                    try:
                        self.game.sound_manager.play_move_sound()
                    except:
                        pass

                # 更新头像状态
                self.game.update_avatars()

                # 如果新的状态是将军，播放将军音效
                if self.game.game_state.is_check:
                    try:
                        self.game.sound_manager.play_check_sound()
                    except:
                        pass

                # 检查游戏是否结束
                if self.game.game_state.game_over:
                    winner_text = self.game.game_state.get_winner_text()

                    # 更新时间数据，确保获取最终值
                    red_time, black_time = self.game.game_state.update_times()
                    total_time = self.game.game_state.total_time

                    # 创建弹窗并传入时间信息
                    self.game.popup = PopupDialog(
                        400, 320,  # 增加高度以适应更多内容
                        winner_text,
                        total_time,
                        red_time,
                        black_time
                    )
                # 如果是人机模式且轮到AI走子，触发AI移动
                elif self.game.game_mode == MODE_PVC and self.game.game_state.player_turn != self.game.player_camp:
                    self.game.schedule_ai_move()
                else:
                    # 立即刷新界面，确保玩家的移动能立刻显示
                    pygame.display.flip()
            else:
                # 移动失败，可能是由于会导致送将，取消选择但不执行移动
                self.selected_piece = None
                self.game.board.clear_highlights()

            # 无论如何都取消选择状态
            self.selected_piece = None
            self.game.board.clear_highlights()

    def handle_board_click(self, mouse_pos):
        """处理棋盘点击事件"""
        if self.game.game_state.is_game_over:
            return

        # 如果AI正在思考，忽略玩家点击
        if self.game.ai_thinking:
            return

        # 获取点击位置对应的棋盘坐标
        row, col = self.game.board.get_board_position(mouse_pos)

        # 如果没有选中棋子，尝试选中棋子
        if not self.selected_piece:
            piece = self.game.game_state.get_piece_at(row, col)
            if piece and piece.camp == self.game.game_state.player_turn:
                self.selected_piece = piece
                return

        # 如果已经选中棋子，尝试移动棋子
        if self.selected_piece:
            move = (self.selected_piece.row, self.selected_piece.col, row, col)
            if self.game.game_state.is_valid_move(move):
                self.make_move(move)
                self.selected_piece = None
                return

        # 如果点击位置无效，取消选中
        self.selected_piece = None

    def make_move(self, move):
        """执行走法"""
        from_row, from_col, to_row, to_col = move

        # 执行走法
        self.game.game_state.make_move(move)

        # 更新棋盘上的棋子位置
        self.game.board.update_pieces(self.game.game_state.pieces)

        # 更新上一步走法记录
        self.last_move = move
        self.last_move_notation = self.game.game_state.get_move_notation(move)

        # 播放音效
        if self.game.game_state.is_check:
            self.game.sound_manager.play_check_sound()
        elif self.game.game_state.is_capture:
            self.game.sound_manager.play_capture_sound()
        else:
            self.game.sound_manager.play_move_sound()

        # 检查游戏是否结束
        if self.game.game_state.is_game_over:
            self.game.show_game_over_popup()
            return

        # 如果是人机对战，启动AI
        if self.game.game_mode == MODE_PVC and self.game.game_state.player_turn != self.game.player_camp:
            self.game.ai_thinking = True
            pygame.time.set_timer(pygame.USEREVENT, 1000)  # 1秒后启动AI

    def handle_undo(self):
        """处理悔棋操作"""
        # 如果AI正在思考，不允许悔棋
        if self.game.ai_thinking:
            return False

        # 如果游戏已经结束，先清除状态
        if self.game.game_state.game_over:
            self.game.popup = None
            self.game.game_state.game_over = False

        if self.game.game_mode == MODE_PVP:
            # 人人模式直接悔棋
            if self.game.game_state.undo_move():
                # 悔棋成功
                self.selected_piece = None
                self.game.board.clear_highlights()
                self.game.update_avatars()

                # 清除上一步记录
                self.last_move = None
                self.last_move_notation = ""

                # 如果还有移动历史，更新上一步记录
                if hasattr(self.game.game_state, 'move_history') and len(self.game.game_state.move_history) > 0:
                    last_history = self.game.game_state.move_history[-1]
                    if 'from_pos' in last_history and 'to_pos' in last_history:
                        from_row, from_col = last_history['from_pos']
                        to_row, to_col = last_history['to_pos']
                        self.last_move = (from_row, from_col, to_row, to_col)
                        piece = self.game.game_state.get_piece_at(to_row, to_col)
                        if piece:
                            self.last_move_notation = self.game.generate_move_notation(
                                piece, from_row, from_col, to_row, to_col
                            )

                return True
        else:  # 人机模式
            # 首先停止任何AI计时器
            pygame.time.set_timer(pygame.USEREVENT + 1, 0)
            pygame.time.set_timer(pygame.USEREVENT + 2, 0)
            self.game.ai_thinking = False

            # 移动历史为空，没有步骤可以悔棋
            if not hasattr(self.game.game_state, 'move_history') or len(self.game.game_state.move_history) == 0:
                return False

            # 判断当前是玩家回合还是AI回合
            is_player_turn = self.game.game_state.player_turn == self.game.player_camp

            if is_player_turn:
                # 玩家回合 - 需要悔两步（玩家和AI各一步）
                if len(self.game.game_state.move_history) >= 1:
                    # 至少有一步可以悔棋
                    self.game.game_state.undo_move()  # 悔掉玩家上一步

                    # 如果还有更多步骤，尝试悔掉AI的上一步
                    if len(self.game.game_state.move_history) >= 1:
                        self.game.game_state.undo_move()  # 悔掉AI上一步

                    self.selected_piece = None
                    self.game.board.clear_highlights()
                    self.game.update_avatars()
                    return True
            else:
                # AI回合 - 悔一步（AI刚下的或上一个玩家步骤）
                if len(self.game.game_state.move_history) >= 1:
                    self.game.game_state.undo_move()
                    self.selected_piece = None
                    self.game.board.clear_highlights()
                    self.game.update_avatars()

                    # 如果悔棋后轮到AI行动，延迟1秒
                    if self.game.game_state.player_turn != self.game.player_camp:
                        self.game.ai_thinking = True
                        pygame.time.set_timer(pygame.USEREVENT + 2, 1000)

                    return True

        # 重置滚动位置
        self.game.history_scroll_y = 0

        return False


class GameUI:
    """处理游戏界面和用户交互"""
    def __init__(self, game_instance):
        self.game = game_instance
        self.init_ui_elements()

    def init_ui_elements(self):
        """初始化界面元素"""
        button_width = 120
        button_height = 40
        button_y = self.game.window_height - 60

        # 创建返回按钮
        self.game.back_button = Button(
            self.game.left_panel_width + 80,
            button_y,
            button_width,
            button_height,
            "返回",
            22
        )

        # 创建重新开始按钮
        self.game.restart_button = Button(
            self.game.left_panel_width + 80 + button_width + 10,  # 紧挨着返回按钮
            button_y,
            button_width,
            button_height,
            "重来",
            22
        )
        # 创建退出游戏按钮
        self.game.exit_button = Button(
            self.game.window_width - button_width - 80 - button_width - 10,
            button_y,
            button_width,
            button_height,
            "退出游戏",
            22
        )
        # 创建悔棋按钮
        self.game.undo_button = Button(
            self.game.window_width - button_width - 80,
            button_y,
            button_width,
            button_height,
            "悔棋",
            22
        )

        # 创建全屏切换按钮
        self.game.fullscreen_button = Button(
            self.game.window_width - 100,
            10,
            80,
            30,
            "全屏" if not self.game.is_fullscreen else "窗口",
            14
        )

    def update_ui_elements(self):
        """更新界面元素位置"""
        button_width = 120
        button_height = 40
        button_y = self.game.window_height - 60

        # 更新返回按钮位置
        self.game.back_button = Button(
            self.game.left_panel_width + 80,
            button_y,
            button_width,
            button_height,
            "返回",
            22
        )

        # 更新重新开始按钮位置
        self.game.restart_button = Button(
            self.game.left_panel_width + 80 + button_width + 10,  # 紧挨着返回按钮
            button_y,
            button_width,
            button_height,
            "重来",
            22
        )

        # 更新退出游戏按钮位置
        self.game.exit_button = Button(
            self.game.window_width - button_width - 80 - button_width - 10,
            button_y,
            button_width,
            button_height,
            "退出游戏",
            22
        )

        # 更新悔棋按钮位置
        self.game.undo_button = Button(
            self.game.window_width - button_width - 80,
            button_y,
            button_width,
            button_height,
            "悔棋",
            22
        )

        # 更新全屏按钮位置
        self.game.fullscreen_button = Button(
            self.game.window_width - 100,
            10,
            80,
            30,
            "全屏" if not self.game.is_fullscreen else "窗口",
            14
        )

    def handle_event(self, event, mouse_pos):
        """处理界面事件"""
        # 处理窗口大小变化
        if event.type == pygame.VIDEORESIZE:
            if not self.game.is_fullscreen:  # 只在窗口模式下处理大小变化
                self.game.handle_resize((event.w, event.h))

        # 处理键盘事件
        if event.type == pygame.KEYDOWN:
            # F11或Alt+Enter切换全屏
            if event.key == pygame.K_F11 or (
                    event.key == pygame.K_RETURN and
                    pygame.key.get_mods() & pygame.KMOD_ALT
            ):
                self.game.toggle_fullscreen()

        # 处理鼠标滚轮事件（用于棋谱滚动）
        if event.type == pygame.MOUSEWHEEL:
            # 检查鼠标是否在棋谱区域
            right_panel_x = self.game.window_width - 350  # 与绘制位置保持一致
            # 检查鼠标是否在右侧信息面板区域内
            if mouse_pos[0] >= right_panel_x and mouse_pos[1] >= 300 and mouse_pos[0] <= self.game.window_width - 10:
                # 滚动棋谱
                self.game.history_scroll_y = max(0, self.game.history_scroll_y - event.y)
                # 确保不会滚动过多
                total_moves = len(self.game.game_state.move_history)
                max_scroll = max(0, total_moves - self.game.history_max_visible_lines)
                self.game.history_scroll_y = min(self.game.history_scroll_y, max_scroll)

        # 处理鼠标点击
        if event.type == pygame.MOUSEBUTTONDOWN:
            # 检查是否点击了全屏按钮
            if self.game.fullscreen_button.is_clicked(mouse_pos, event):
                self.game.toggle_fullscreen()

            # 检查是否点击了悔棋按钮
            elif self.game.undo_button.is_clicked(mouse_pos, event):
                self.game.game_logic.handle_undo()

            # 检查是否点击了退出游戏按钮
            elif self.game.exit_button.is_clicked(mouse_pos, event):
                # 显示确认对话框确认退出游戏
                self.game.confirm_dialog = ConfirmDialog(
                    400, 200, "是否要退出游戏？\n这将结束当前对局。"
                )

            # 处理棋子操作，只有在当前回合是玩家回合时才处理
            elif not self.game.ai_thinking and (self.game.game_mode == MODE_PVP or
                                           self.game.game_state.player_turn == self.game.player_camp):
                self.game.game_logic.handle_click(mouse_pos)

    def draw_ui_elements(self):
        """绘制界面元素"""
        # 绘制悔棋按钮、重来按钮、返回按钮、退出按钮和全屏按钮
        self.game.undo_button.draw(self.game.screen)
        self.game.restart_button.draw(self.game.screen)
        self.game.back_button.draw(self.game.screen)
        self.game.exit_button.draw(self.game.screen)
        self.game.fullscreen_button.draw(self.game.screen)