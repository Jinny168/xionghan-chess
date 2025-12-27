"""游戏渲染模块，负责界面绘制功能"""
import pygame
from config import PANEL_BORDER, BLACK, RED, MODE_PVC, CAMP_RED
from utils import load_font, draw_background


class GameRenderer:
    """游戏渲染器"""
    def __init__(self, game_instance):
        self.game = game_instance

    def draw(self, mouse_pos):
        """绘制游戏界面"""
        # 使用统一的背景绘制函数
        draw_background(self.game.screen)

        # 绘制左侧面板背景 - 使用与主界面一致的纹理
        left_panel_rect = pygame.Rect(0, 0, self.game.left_panel_width, self.game.window_height)

        # 先绘制与主背景一致的纹理
        left_panel_surface = pygame.Surface((self.game.left_panel_width, self.game.window_height))
        draw_background(left_panel_surface)  # 使用相同的背景绘制函数

        # 稍微调亮左侧面板使其有区分度
        overlay = pygame.Surface((self.game.left_panel_width, self.game.window_height), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 30))  # 半透明白色覆盖，轻微增亮
        left_panel_surface.blit(overlay, (0, 0))

        # 应用到主界面
        self.game.screen.blit(left_panel_surface, (0, 0))

        # 添加分隔线
        pygame.draw.line(self.game.screen, PANEL_BORDER, (self.game.left_panel_width, 0),
                         (self.game.left_panel_width, self.game.window_height), 2)

        # 绘制棋盘和棋子 - 先绘制这些
        self.game.board.draw(self.game.screen, self.game.game_state.pieces)

        # 如果有上一步走法，在棋盘上标记出来
        if self.game.last_move:
            from_row, from_col, to_row, to_col = self.game.last_move
            self.game.board.highlight_last_move(self.game.screen, from_row, from_col, to_row, to_col)

        # 检查是否需要显示将军动画 - 在棋子之上显示动画
        if self.game.game_state.should_show_check_animation():
            king_pos = self.game.game_state.get_checked_king_position()
            if king_pos:
                self.game.board.draw_check_animation(self.game.screen, king_pos)

        # 绘制游戏信息面板
        self.draw_info_panel()

        # 绘制界面元素
        self.game.game_ui.draw_ui_elements()

        # 绘制玩家头像
        self.game.red_avatar.draw(self.game.screen)
        self.game.black_avatar.draw(self.game.screen)

        # 绘制计时器信息
        self.draw_timers()

        # 在左侧面板中添加VS标志
        vs_font = load_font(36, bold=True)
        vs_text = "VS"
        vs_surface = vs_font.render(vs_text, True, (100, 100, 100))
        vs_rect = vs_surface.get_rect(center=(self.game.left_panel_width // 2, self.game.window_height // 2))
        self.game.screen.blit(vs_surface, vs_rect)

        # 如果有上一步走法的记录，显示它
        if self.game.last_move_notation:
            move_font = load_font(18)
            move_text = f"上一步: {self.game.last_move_notation}"
            move_surface = move_font.render(move_text, True, BLACK)
            # 显示在左侧面板底部
            move_rect = move_surface.get_rect(center=(self.game.left_panel_width // 2, self.game.window_height - 80))
            self.game.screen.blit(move_surface, move_rect)

        # 如果是人机模式，显示模式和阵营提示
        if self.game.game_mode == self.game.MODE_PVC:
            mode_font = load_font(18)
            if self.game.player_camp == self.game.CAMP_RED:
                mode_text = "人机对战模式 - 您执红方"
            else:
                mode_text = "人机对战模式 - 您执黑方"
            mode_surface = mode_font.render(mode_text, True, BLACK)
            self.game.screen.blit(mode_surface, (
                self.game.left_panel_width + (self.game.window_width - self.game.left_panel_width) // 2 - mode_surface.get_width() // 2,
                15))

            # 如果AI正在思考，显示提示
            if self.game.ai_thinking:
                thinking_font = load_font(24)
                thinking_text = "电脑思考中..."
                thinking_surface = thinking_font.render(thinking_text, True, RED)
                thinking_rect = thinking_surface.get_rect(center=(self.game.window_width // 2, 45))
                self.game.screen.blit(thinking_surface, thinking_rect)

        # 绘制 captured pieces（阵亡棋子）
        self.draw_captured_pieces()

        # 绘制棋谱历史记录
        self.draw_move_history()

        # 如果游戏结束，显示弹窗
        if self.game.game_state.game_over and self.game.popup:
            self.game.popup.draw(self.game.screen)

        # 如果有确认对话框，显示它
        if self.game.confirm_dialog:
            self.game.confirm_dialog.draw(self.game.screen)

    def draw_timers(self):
        """绘制计时器信息"""
        # 获取当前的时间状态
        red_time, black_time = self.game.game_state.update_times()
        total_time = self.game.game_state.total_time

        # 转换为分钟:秒格式
        red_time_str = f"{int(red_time // 60):02}:{int(red_time % 60):02}"
        black_time_str = f"{int(black_time // 60):02}:{int(black_time % 60):02}"
        total_time_str = f"{int(total_time // 60):02}:{int(total_time % 60):02}"

        # 绘制红方时间 - 在红方头像下方
        red_time_surface = self.game.timer_font.render(f"用时: {red_time_str}", True, RED)
        red_time_rect = red_time_surface.get_rect(
            center=(self.game.left_panel_width // 2, self.game.red_avatar.y + self.game.red_avatar.radius + 50)
        )
        self.game.screen.blit(red_time_surface, red_time_rect)

        # 绘制黑方时间 - 在黑方头像下方
        black_time_surface = self.game.timer_font.render(f"用时: {black_time_str}", True, BLACK)
        black_time_rect = black_time_surface.get_rect(
            center=(self.game.left_panel_width // 2, self.game.black_avatar.y + self.game.black_avatar.radius + 50)
        )
        self.game.screen.blit(black_time_surface, black_time_rect)

        # 绘制总时间 - 在左侧面板顶部
        total_time_surface = self.game.timer_font.render(f"对局时长: {total_time_str}", True, BLACK)
        self.game.screen.blit(total_time_surface, (10, 10))

    def draw_info_panel(self):
        """绘制游戏信息面板"""
        # 当游戏进行中，在左上角显示当前回合
        if not self.game.game_state.game_over:
            # 创建回合信息文本
            turn_color = RED if self.game.game_state.player_turn == "red" else BLACK
            turn_text = f"当前回合: {'红方' if self.game.game_state.player_turn == 'red' else '黑方'}"

            # 计算位置 - 在左上角，对局时长下方
            font = load_font(20)
            text_surface = font.render(turn_text, True, turn_color)
            # 位于对局时长信息的下方
            text_rect = text_surface.get_rect(
                topleft=(10, 40)  # 在左上角，对局时长下方
            )
            self.game.screen.blit(text_surface, text_rect)

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
        right_panel_x = self.game.window_width - 250  # 右侧边栏起始x坐标
        self.game.screen.blit(red_title, (right_panel_x, 60))
        self.game.screen.blit(black_title, (right_panel_x, 180))

        # 绘制红方阵亡棋子
        x_start, y_start = right_panel_x, 90
        x, y = x_start, y_start
        for piece in self.game.game_state.captured_pieces["red"]:
            piece_text = title_font.render(piece.name, True, RED)
            # 减小右边距，提供更多空间给棋子显示
            if x + piece_text.get_width() > self.game.window_width - 40:
                x = x_start
                y += 25
            self.game.screen.blit(piece_text, (x, y))
            x += piece_text.get_width() + 5

        # 绘制黑方阵亡棋子
        x_start, y_start = right_panel_x, 210
        x, y = x_start, y_start
        for piece in self.game.game_state.captured_pieces["black"]:
            piece_text = title_font.render(piece.name, True, BLACK)
            # 减小右边距，提供更多空间给棋子显示
            if x + piece_text.get_width() > self.game.window_width - 40:
                x = x_start
                y += 25
            self.game.screen.blit(piece_text, (x, y))
            x += piece_text.get_width() + 5

    def draw_move_history(self):
        """绘制棋谱历史记录"""
        # 绘制标题
        title_font = load_font(20, bold=True)
        history_title = title_font.render("棋谱记录:", True, (0, 0, 0))

        # 将棋谱记录移到右侧
        right_panel_x = self.game.window_width - 250  # 右侧边栏起始x坐标
        self.game.screen.blit(history_title, (right_panel_x, 300))

        # 绘制历史记录（带滚动功能）
        history_font = load_font(18)
        y_start = 330
        line_height = self.game.history_line_height

        # 计算最大可见行数
        max_visible_lines = min(self.game.history_max_visible_lines,
                                (self.game.window_height - y_start - 50) // line_height)

        # 计算要显示的历史记录范围
        total_moves = len(self.game.game_state.move_history)
        start_index = max(0, total_moves - max_visible_lines - self.game.history_scroll_y)
        end_index = min(total_moves, start_index + max_visible_lines)

        # 显示历史记录
        y = y_start
        for i in range(start_index, end_index):
            move_record = self.game.game_state.move_history[i]
            piece, from_row, from_col, to_row, to_col, captured_piece = move_record

            # 生成记谱表示
            notation = self.game.generate_move_notation(piece, from_row, from_col, to_row, to_col)

            # 添加回合数
            move_number = i + 1
            move_text = f"{move_number:2d}. {notation}"

            # 如果有被吃子，添加标识
            if captured_piece:
                move_text += " (吃子)"

            text_surface = history_font.render(move_text, True, BLACK)
            # 限制文本宽度，避免超出边界
            max_text_width = 300
            if text_surface.get_width() > max_text_width:
                # 如果文本太长，截断并在末尾添加省略号
                move_text = move_text[:20] + "..."  # 简单截断
                text_surface = history_font.render(move_text, True, BLACK)
            self.game.screen.blit(text_surface, (right_panel_x + 5, y))
            y += line_height

        # 绘制滚动条（如果需要）
        if total_moves > max_visible_lines:
            # 滚动条背景
            scrollbar_x = self.game.window_width - 300  # 将滚动条向左移动，远离窗口边缘
            scrollbar_y = y_start
            scrollbar_height = max_visible_lines * line_height
            pygame.draw.rect(self.game.screen, (200, 200, 200),
                             (scrollbar_x, scrollbar_y, 15, scrollbar_height))  # 增加宽度到15像素

            # 滚动条滑块
            thumb_height = max(20, scrollbar_height * max_visible_lines // total_moves)
            max_scroll = total_moves - max_visible_lines
            if max_scroll > 0:  # 避免除零错误
                thumb_y = scrollbar_y + (self.game.history_scroll_y / max_scroll) * (scrollbar_height - thumb_height)
            else:
                thumb_y = scrollbar_y
            pygame.draw.rect(self.game.screen, (100, 100, 100),
                             (scrollbar_x, thumb_y, 15, thumb_height))  # 增加宽度到15像素