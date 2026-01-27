"""游戏输入事件处理器模块

此模块负责处理各种游戏输入事件，包括鼠标点击、窗口调整、游戏事件等
"""

import pygame

from program.config.config import MODE_PVP
from program.controllers.sound_manager import sound_manager
from program.ui.dialogs import AudioSettingsDialog, PawnResurrectionDialog, PromotionDialog
from program.utils import tools


class InputHandler:
    """输入事件处理器类"""
    @staticmethod
    def handle_resize(game_instance, new_size):
        """处理窗口大小变化"""
        game_instance.window_width, game_instance.window_height = new_size
        # 更新布局
        game_instance.update_layout()

    @staticmethod
    def handle_event(game_instance, event, mouse_pos):
        """处理游戏事件"""
        # 处理窗口大小变化
        if event.type == pygame.VIDEORESIZE:
            if not game_instance.is_fullscreen:  # 只在窗口模式下处理大小变化
                InputHandler.handle_resize(game_instance, (event.w, event.h))

        # 处理键盘事件
        if event.type == pygame.KEYDOWN:
            # F11或Alt+Enter切换全屏
            if event.key == pygame.K_F11 or (
                    event.key == pygame.K_RETURN and
                    pygame.key.get_mods() & pygame.KMOD_ALT
            ):
                game_instance.toggle_fullscreen()

        # 处理鼠标滚轮事件（用于棋谱滚动）
        if event.type == pygame.MOUSEWHEEL:
            # 检查鼠标是否在棋谱区域
            right_panel_x = game_instance.window_width - 350  # 与绘制位置保持一致
            # 检查鼠标是否在右侧信息面板区域内
            if right_panel_x <= mouse_pos[0] <= game_instance.window_width - 10 and mouse_pos[1] >= 300:
                # 滚动棋谱
                game_instance.history_scroll_y = max(0, game_instance.history_scroll_y - event.y)
                # 确保不会滚动过多
                total_moves = len(game_instance.game_state.move_history)
                max_scroll = max(0, total_moves - game_instance.history_max_visible_lines)
                game_instance.history_scroll_y = min(game_instance.history_scroll_y, max_scroll)

        # 处理鼠标点击
        if event.type == pygame.MOUSEBUTTONDOWN:
            # 检查是否点击了全屏按钮
            if game_instance.fullscreen_button.is_clicked(mouse_pos, event):
                game_instance.toggle_fullscreen()
            
            # 检查是否点击了音效设置按钮
            elif game_instance.audio_settings_button.is_clicked(mouse_pos, event):
                # 打开音效设置对话框
                game_instance.audio_settings_dialog = AudioSettingsDialog(500, 350, game_instance.sound_manager)

            # 检查是否点击了悔棋按钮
            elif game_instance.undo_button.is_clicked(mouse_pos, event):
                game_instance.handle_undo()
            
            # 检查是否点击了退出游戏按钮
            elif game_instance.exit_button.is_clicked(mouse_pos, event):
                # 显示确认对话框确认退出游戏
                from program.ui.dialogs import ConfirmDialog
                game_instance.confirm_dialog = ConfirmDialog(
                    400, 200, "是否要退出游戏？\n这将结束当前对局。"
                )

            # 处理棋子操作，只有在当前回合是玩家回合时才处理
            elif not game_instance.is_ai_thinking() and (game_instance.game_mode == MODE_PVP or
                                           game_instance.game_state.player_turn == game_instance.player_camp):
                game_instance.handle_click(mouse_pos)

    @staticmethod
    def handle_click(game_instance, pos):
        """处理鼠标点击事件"""
        # 获取点击的棋盘位置
        grid_pos = game_instance.game_screen.board.get_grid_position(pos)
        if not grid_pos:
            return

        row, col = grid_pos

        # 如果正在等待升变选择，不处理棋盘点击
        if game_instance.promotion_dialog:
            return

        # 检查是否点击了空闲的兵/卒起始位置，触发复活对话框
        # 首先检查当前玩家是否有兵/卒在局数量不足7个，且点击位置是初始兵/卒位置且为空
        current_player = game_instance.game_state.player_turn
        if game_instance.selected_piece is None:  # 如果没有选中任何棋子
            # 检查是否点击了兵/卒初始位置且该位置为空
            if ((current_player == "red" and row == 8) or (current_player == "black" and row == 4)) and \
               game_instance.game_state.get_piece_at(row, col) is None:
                # 检查当前玩家在局的兵/卒数量是否小于7
                if game_instance.game_state.get_pawn_count(current_player) < 7:
                    # 检查是否满足复活条件
                    resurrection_positions = game_instance.game_state.get_resurrection_positions()
                    if (row, col) in resurrection_positions[current_player]:
                        # 弹出复活确认对话框
                        game_instance.pawn_resurrection_dialog = PawnResurrectionDialog(
                            500, 200, current_player, (row, col)
                        )
                        return

        # 选择棋子或移动棋子
        if game_instance.selected_piece is None:
            # 尝试选择棋子
            piece = game_instance.game_state.get_piece_at(row, col)
            if piece and piece.color == game_instance.game_state.player_turn:
                game_instance.selected_piece = (row, col)
                game_instance.game_screen.board.highlight_position(row, col)

                # 计算可能的移动位置
                possible_moves, capturable = game_instance.game_state.calculate_possible_moves(row, col)
                game_instance.game_screen.board.set_possible_moves(possible_moves)
                game_instance.game_screen.board.set_capturable_positions(capturable)
        else:
            sel_row, sel_col = game_instance.selected_piece

            # 检查是否点击了同一个棋子（取消选择）
            if sel_row == row and sel_col == col:
                game_instance.selected_piece = None
                game_instance.game_screen.board.clear_highlights()
                return

            # 检查是否选择了另一个己方棋子（更换选择）
            new_piece = game_instance.game_state.get_piece_at(row, col)
            if new_piece and new_piece.color == game_instance.game_state.player_turn:
                game_instance.selected_piece = (row, col)
                game_instance.game_screen.board.highlight_position(row, col)

                # 计算新选择棋子的可能移动
                possible_moves, capturable = game_instance.game_state.calculate_possible_moves(row, col)
                game_instance.game_screen.board.set_possible_moves(possible_moves)
                game_instance.game_screen.board.set_capturable_positions(capturable)
                return

            # 已选择棋子，尝试移动
            captured_piece = game_instance.game_state.get_piece_at(row, col)
            move_successful = game_instance.game_state.move_piece(sel_row, sel_col, row, col)

            if move_successful:
                print(f"[DEBUG] 移动成功: {sel_row},{sel_col} -> {row},{col}")
                # 检查是否需要升变（兵/卒到达对方底线）
                if game_instance.game_state.needs_promotion:
                    # 获取兵的颜色
                    pawn_color = game_instance.game_state.promotion_pawn.color if game_instance.game_state.promotion_pawn else game_instance.game_state.player_turn
                    print(f"[DEBUG] 需要升变: {pawn_color}方兵到达底线")
                    # 自动弹出升变选择对话框
                    game_instance.promotion_dialog = PromotionDialog(
                        500, 400, pawn_color, (row, col), game_instance.game_state.available_promotion_pieces
                    )

                # 记录上一步走法
                game_instance.last_move = (sel_row, sel_col, row, col)

                # 生成上一步走法的中文表示
                piece = game_instance.game_state.get_piece_at(row, col)
                if piece:
                    game_instance.last_move_notation = tools.generate_move_notation(piece, sel_row, sel_col, row, col)

                # 播放选子音效（当选择棋子时）
                if game_instance.selected_piece and not captured_piece:
                    try:
                        sound_manager.play_sound('choose')  # 使用chess-master的选子音效
                    except (pygame.error, KeyError, FileNotFoundError):
                        pass
                
                # 播放移动音效
                if captured_piece:
                    try:
                        sound_manager.play_sound('eat')  # 使用chess-master的吃子音效
                    except (pygame.error, KeyError, FileNotFoundError):
                        pass
                else:
                    try:
                        sound_manager.play_sound('drop')  # 使用chess-master的落子音效
                    except (pygame.error, KeyError, FileNotFoundError):
                        pass

                # 更新头像状态
                game_instance.game_screen.update_avatars(game_instance.game_state)

                # 播放将军/绝杀音效 - 优先处理绝杀情况，避免重复播放
                sound_manager.check_and_play_game_sound(game_instance.game_state)

                # 移动完成后清除所有高亮显示
                game_instance.game_screen.board.clear_highlights()
                game_instance.selected_piece = None

    @staticmethod
    def handle_undo(game_instance):
        """处理悔棋操作"""
        # 如果AI正在思考，不允许悔棋
        if game_instance.is_ai_thinking():
            return False

        # 如果游戏已经结束，先清除状态
        if game_instance.game_state.game_over:
            game_instance.popup = None
            game_instance.game_state.game_over = False

        if game_instance.game_mode == MODE_PVP:
            # 人人模式直接悔棋
            if game_instance.game_state.undo_move():
                # 悔棋成功
                game_instance.selected_piece = None
                game_instance.game_screen.board.clear_highlights()
                game_instance.game_screen.update_avatars(game_instance.game_state)

                # 清除上一步记录
                game_instance.last_move = None
                game_instance.last_move_notation = ""

                # 如果还有移动历史，更新上一步记录
                if hasattr(game_instance.game_state, 'move_history') and len(game_instance.game_state.move_history) > 0:
                    last_history = game_instance.game_state.move_history[-1]
                    if 'from_pos' in last_history and 'to_pos' in last_history:
                        from_row, from_col = last_history['from_pos']
                        to_row, to_col = last_history['to_pos']
                        game_instance.last_move = (from_row, from_col, to_row, to_col)
                        piece = game_instance.game_state.get_piece_at(to_row, to_col)
                        if piece:
                            game_instance.last_move_notation = tools.generate_move_notation(
                                piece, from_row, from_col, to_row, to_col
                            )

                return True
        else:  # 人机模式
            # 首先停止任何AI计时器
            pygame.time.set_timer(pygame.USEREVENT + 1, 0)
            pygame.time.set_timer(pygame.USEREVENT + 2, 0)
            game_instance.ai_manager.reset_ai_state()

            # 移动历史为空，没有步骤可以悔棋
            if not hasattr(game_instance.game_state, 'move_history') or len(game_instance.game_state.move_history) == 0:
                return False

            # 判断当前是玩家回合还是AI回合
            is_player_turn = game_instance.game_state.player_turn == game_instance.player_camp

            if is_player_turn:
                # 玩家回合 - 需要悔两步（玩家和AI各一步）
                if len(game_instance.game_state.move_history) >= 1:
                    # 至少有一步可以悔棋
                    game_instance.game_state.undo_move()  # 悔掉玩家上一步

                    # 如果还有更多步骤，尝试悔掉AI的上一步
                    if len(game_instance.game_state.move_history) >= 1:
                        game_instance.game_state.undo_move()  # 悔掉AI上一步

                    game_instance.selected_piece = None
                    game_instance.game_screen.board.clear_highlights()
                    game_instance.game_screen.update_avatars(game_instance.game_state)
                    return True
            else:
                # AI回合 - 悔一步（AI刚下的或上一个玩家步骤）
                if len(game_instance.game_state.move_history) >= 1:
                    game_instance.game_state.undo_move()
                    game_instance.selected_piece = None
                    game_instance.game_screen.board.clear_highlights()
                    game_instance.game_screen.update_avatars(game_instance.game_state)

                    # 如果悔棋后轮到AI行动，延迟1秒
                    if game_instance.game_state.player_turn != game_instance.player_camp:
                        game_instance.ai_manager.start_ai_thinking()
                        pygame.time.set_timer(pygame.USEREVENT + 2, 1000)

                    return True

        # 重置滚动位置
        game_instance.history_scroll_y = 0

        return False

# 创建 InputHandler 实例供外部使用
input_handler = InputHandler()
