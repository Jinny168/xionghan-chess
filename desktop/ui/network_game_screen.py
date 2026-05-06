import math

import pygame

from desktop.controllers.game_config_manager import (
    RED, BLACK, theme_manager, game_config
)
from desktop.ui.button import Button
from desktop.ui.chess_board import ChessBoard
from desktop.ui.game_screen import BaseGameScreen
from desktop.utils.tools import load_font, draw_background


class NetworkGameScreen(BaseGameScreen):
    """网络对战模式的UI界面类"""

    def __init__(self, window_width, window_height, game_mode, player_camp):
        """初始化网络对战界面组件"""
        self.window_width = window_width
        self.window_height = window_height
        self.game_mode = game_mode
        self.player_camp = player_camp

        # 初始化界面组件
        self.board = None
        self.red_avatar = None
        self.black_avatar = None
        self.timer_font = None

        # 按钮组件
        self.back_button = None
        self.restart_button = None
        self.exit_button = None
        self.undo_button = None
        self.fullscreen_button = None
        self.audio_settings_button = None

        # 布局参数
        self.left_panel_width = None
        self.board_margin_top = None

        # 初始化所有UI组件
        self.init_ui_components()

    def init_ui_components(self):
        """初始化所有UI组件"""
        self.update_layout()

    def update_layout(self):
        """根据当前窗口尺寸更新布局 - 网络对战模式特化版本"""
        # 计算左侧面板宽度和棋盘边距
        from desktop.controllers.game_config_manager import LEFT_PANEL_WIDTH_RATIO, BOARD_MARGIN_TOP_RATIO
        self.left_panel_width = int(LEFT_PANEL_WIDTH_RATIO * self.window_width)
        self.board_margin_top = int(BOARD_MARGIN_TOP_RATIO * self.window_height)

        # 更新棋盘
        self.board = ChessBoard(
            self.window_width - self.left_panel_width,
            self.window_height,
            self.left_panel_width,
            self.board_margin_top,
            traditional_mode=game_config.get_setting('traditional_mode', False)  # 从配置获取是否使用传统模式
        )

        button_width = 120
        button_height = 40
        button_y = self.window_height - 60

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
            "全屏",
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

        # 更新头像位置
        avatar_radius = 40
        panel_center_x = self.left_panel_width // 2
        black_y = self.window_height // 3 - 50
        red_y = self.window_height * 2 // 3

        # 更新头像位置
        if hasattr(self, 'black_avatar') and self.black_avatar:
            self.black_avatar.update_position(panel_center_x, black_y, avatar_radius)
        else:
            from desktop.ui.avatar import Avatar
            self.black_avatar = Avatar(panel_center_x, black_y, avatar_radius, (245, 245, 235), "黑方", False)

        if hasattr(self, 'red_avatar') and self.red_avatar:
            self.red_avatar.update_position(panel_center_x, red_y, avatar_radius)
        else:
            from desktop.ui.avatar import Avatar
            self.red_avatar = Avatar(panel_center_x, red_y, avatar_radius, (255, 255, 240), "红方", True)

        # 计时器的字体
        self.timer_font = load_font(18)

    def draw(self, screen, game_state, last_move=None, last_move_notation="",
             popup=None, confirm_dialog=None, pawn_resurrection_dialog=None,
             promotion_dialog=None, audio_settings_dialog=None):
        """绘制网络对战界面"""
        # 使用统一的背景绘制函数
        theme_colors = theme_manager.get_theme_colors()
        
        # 绘制主背景
        draw_background(screen, theme_colors["background"])

        # 绘制左侧面板背景
        left_panel_surface = pygame.Surface((self.left_panel_width, self.window_height))
        
        # 绘制主题背景
        draw_background(left_panel_surface, theme_colors["panel"])
        
        # 应用更美观渐变效果或纹理覆盖
        overlay = pygame.Surface((self.left_panel_width, self.window_height), pygame.SRCALPHA)
        # 创建渐变效果，使左侧面板更具层次感
        for y in range(self.window_height):
            # 根据y位置计算透明度，创建垂直渐变效果
            alpha = 20 + int(10 * abs(math.sin(y / 100.0)))  # 轻微垂直变化
            overlay_color = (255, 255, 255, alpha)
            pygame.draw.line(overlay, overlay_color, (0, y), (self.left_panel_width, y))
        
        left_panel_surface.blit(overlay, (0, 0))

        # 应用到主界面
        screen.blit(left_panel_surface, (0, 0))

        # 添加分隔线
        pygame.draw.line(screen, theme_colors["panel_border"], (self.left_panel_width, 0),
                         (self.left_panel_width, self.window_height), 2)

        # 绘制棋盘和棋子
        self.board.draw(screen, game_state.pieces, game_state)

        # 如果有上一步走法，在棋盘上标记出来
        if last_move:
            from_row, from_col, to_row, to_col = last_move
            self.board.highlight_last_move(screen, from_row, from_col, to_row, to_col)

        # 将军/绝杀提示将在游戏主循环中绘制

        # 绘制游戏信息面板
        self.draw_info_panel(screen, game_state, last_move_notation)

        # 绘制悔棋按钮、重来按钮、退出按钮、全屏按钮和音效设置按钮
        # 注意：在网络对战模式中，我们不绘制返回按钮
        # 悔棋按钮总是绘制，但根据启用状态显示不同外观
        if hasattr(self, 'undo_button') and self.undo_button:
            self.undo_button.draw(screen)
        if hasattr(self, 'restart_button') and self.restart_button:
            self.restart_button.draw(screen)
        if hasattr(self, 'exit_button') and self.exit_button:
            self.exit_button.draw(screen)
        if hasattr(self, 'fullscreen_button') and self.fullscreen_button:
            self.fullscreen_button.draw(screen)
        if hasattr(self, 'audio_settings_button') and self.audio_settings_button:
            self.audio_settings_button.draw(screen)

        # 绘制玩家头像
        self.red_avatar.draw(screen)
        self.black_avatar.draw(screen)

        # 绘制计时器信息
        self.draw_timers(screen, game_state)

        # 在左侧面板中添加VS标志
        vs_font = load_font(36, bold=True)
        vs_text = "VS"
        vs_surface = vs_font.render(vs_text, True, (100, 100, 100))
        vs_rect = vs_surface.get_rect(center=(self.left_panel_width // 2, self.window_height // 2))
        screen.blit(vs_surface, vs_rect)

        # 绘制 captured pieces（阵亡棋子）
        self.draw_captured_pieces(screen, game_state, self.window_width)

        # 绘制棋谱历史记录
        self.draw_move_history(screen, game_state, self.window_width)

        # 如果游戏结束，显示弹窗
        if game_state.game_over and popup:
            popup.draw(screen)

        # 如果有确认对话框，显示它
        if confirm_dialog:
            confirm_dialog.draw(screen)

        # 如果有兵/卒复活对话框，显示它
        if pawn_resurrection_dialog:
            pawn_resurrection_dialog.draw(screen)

        # 如果有升变对话框，显示它
        if promotion_dialog:
            promotion_dialog.draw(screen)

        # 如果有音效设置对话框，显示它
        if audio_settings_dialog:
            audio_settings_dialog.draw(screen)

    def draw_info_panel(self, screen, game_state, last_move_notation):
        """绘制游戏信息面板"""
        # 当游戏进行中，在左上角显示当前回合
        if not game_state.game_over:
            # 创建回合信息文本
            from desktop.controllers.game_config_manager import RED, BLACK
            turn_color = RED if game_state.player_turn == "red" else BLACK
            turn_text = f"当前回合: {'红方' if game_state.player_turn == 'red' else '黑方'}"

            # 计算位置 - 在左上角，对局时长下方
            font = load_font(20)
            text_surface = font.render(turn_text, True, turn_color)
            # 位于对局时长信息的下方
            text_rect = text_surface.get_rect(
                topleft=(10, 40)  # 在左上角，对局时长下方
            )
            screen.blit(text_surface, text_rect)

        # 在左侧面板中添加VS标志
        vs_font = load_font(36, bold=True)
        vs_text = "VS"
        vs_surface = vs_font.render(vs_text, True, (100, 100, 100))
        vs_rect = vs_surface.get_rect(center=(self.left_panel_width // 2, self.window_height // 2))
        screen.blit(vs_surface, vs_rect)

        # 如果有上一步走法的记录，显示它
        if last_move_notation:
            move_font = load_font(18)
            move_text = f"上一步: {last_move_notation}"
            from desktop.controllers.game_config_manager import BLACK  # 确保BLACK在此作用域内可用
            move_surface = move_font.render(move_text, True, BLACK)
            # 显示在左侧面板底部
            move_rect = move_surface.get_rect(center=(self.left_panel_width // 2, self.window_height - 80))
            screen.blit(move_surface, move_rect)

    def draw_timers(self, screen, game_state):
        """绘制计时器信息"""
        # 获取当前的时间状态
        red_time, black_time = game_state.update_times()
        total_time = game_state.total_time

        # 转换为分钟:秒格式
        red_time_str = f"{int(red_time // 60):02}:{int(red_time % 60):02}"
        black_time_str = f"{int(black_time // 60):02}:{int(black_time % 60):02}"
        total_time_str = f"{int(total_time // 60):02}:{int(total_time % 60):02}"

        # 绘制红方时间 - 在红方头像下方
        red_time_surface = self.timer_font.render(f"用时: {red_time_str}", True, RED)
        red_time_rect = red_time_surface.get_rect(
            center=(self.left_panel_width // 2, self.red_avatar.y + self.red_avatar.radius + 50)
        )
        screen.blit(red_time_surface, red_time_rect)

        # 绘制黑方时间 - 在黑方头像下方
        black_time_surface = self.timer_font.render(f"用时: {black_time_str}", True, BLACK)
        black_time_rect = black_time_surface.get_rect(
            center=(self.left_panel_width // 2, self.black_avatar.y + self.black_avatar.radius + 50)
        )
        screen.blit(black_time_surface, black_time_rect)

        # 绘制总时间 - 在左侧面板顶部
        total_time_surface = self.timer_font.render(f"对局时长: {total_time_str}", True, BLACK)
        screen.blit(total_time_surface, (10, 10))

    def update_avatars(self, game_state, is_host):
        """更新头像状态"""
        is_red_turn = game_state.player_turn == "red"
        self.red_avatar.set_active(is_red_turn)
        self.black_avatar.set_active(not is_red_turn)

        # 更新玩家标识
        if is_host:  # 主机方
            self.red_avatar.player_name = "玩家1(主机)"
            self.black_avatar.player_name = "玩家2(客户端)"
        else:  # 客户端方
            self.red_avatar.player_name = "玩家1(主机)"
            self.black_avatar.player_name = "玩家2(客户端)"

    def update_button_states(self, mouse_pos):
        """更新按钮悬停状态"""
        if hasattr(self, 'undo_button'):
            self.undo_button.check_hover(mouse_pos)
        if hasattr(self, 'restart_button'):
            self.restart_button.check_hover(mouse_pos)
        if hasattr(self, 'exit_button'):
            self.exit_button.check_hover(mouse_pos)
        if hasattr(self, 'fullscreen_button'):
            self.fullscreen_button.check_hover(mouse_pos)
        if hasattr(self, 'audio_settings_button'):
            self.audio_settings_button.check_hover(mouse_pos)

    def update_fullscreen_button_text(self, is_fullscreen):
        """更新全屏按钮的文本"""
        if hasattr(self, 'fullscreen_button'):
            self.fullscreen_button.text = "窗口" if is_fullscreen else "全屏"

