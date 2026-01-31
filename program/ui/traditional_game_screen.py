"""传统象棋游戏界面UI管理模块"""
import pygame
from program.controllers.game_config_manager import (
    LEFT_PANEL_WIDTH_RATIO, BOARD_MARGIN_TOP_RATIO,
    RED, BLACK, theme_manager
)
from program.controllers.sound_manager import sound_manager
from program.ui.avatar import Avatar
from program.ui.button import Button, StyledButton
from program.ui.game_screen import GameScreen, draw_info_panel
from program.ui.traditional_chess_board import TraditionalChessBoard
from program.utils.utils import load_font, draw_background


class TraditionalGameScreen(GameScreen):
    """管理传统象棋游戏界面的UI组件和绘制逻辑，继承自GameScreen"""
    
    def __init__(self, window_width, window_height, game_mode, player_camp):
        """初始化传统象棋游戏界面组件"""
        # 调用父类构造函数
        super().__init__(window_width, window_height, game_mode, player_camp)
        
        self.window_width = window_width
        self.window_height = window_height
        self.game_mode = game_mode
        self.player_camp = player_camp
        
        # 重新初始化棋盘为传统象棋棋盘
        self.update_traditional_board()
        
        # 计时器相关（传统象棋计时器）
        self.start_time = pygame.time.get_ticks()  # 游戏开始时间
        self.red_time = 0  # 红方累计用时
        self.black_time = 0  # 黑方累计用时
        self.current_player_start_time = self.start_time  # 当前玩家开始用时
        self._last_player = "red"  # 上一个玩家
        
    def update_traditional_board(self):
        """更新为传统象棋棋盘"""
        self.board = TraditionalChessBoard(
            self.window_width - self.left_panel_width - 40,  # 增加更多右边距
            self.window_height,
            self.left_panel_width + 30,  # 棋盘起始位置右移更多
            self.board_margin_top  # 使用调整后的顶部边距
        )
        
    def init_ui_components(self):
        """初始化所有UI组件"""
        self.update_layout()
        # 初始化菜单系统
        self.init_menus()
        # 初始化操作面板
        self.init_operation_panel()
        # 初始化嘲讽动画
        self.init_taunt_animation()

    def init_menus(self):
        """初始化菜单系统"""
        # 选项菜单 - 放在左上角，避开左侧面板
        # 确保菜单不会遮挡其他界面元素
        self.option_menu = Menu(10, 10, 150, "选项", collapsed=True)
        self.option_menu.add_item("导入棋局")
        self.option_menu.add_item("导出棋局")
        self.option_menu.add_item("", separator=True)  # 分隔符
        self.option_menu.add_item("音效设置")
        self.option_menu.add_item("", separator=True)  # 分隔符
        self.option_menu.add_item("窗口切换")
        self.option_menu.add_item("", separator=True)  # 分隔符
        self.option_menu.add_item("主题切换")
        self.option_menu.add_item("", separator=True)  # 分隔符
        self.option_menu.add_item("统计数据")
        
        # 帮助菜单 - 紧邻选项菜单，但需要确保不遮挡其他元素
        self.help_menu = Menu(170, 10, 150, "帮助", collapsed=True)
        self.help_menu.add_item("游戏规则")
        self.help_menu.add_item("关于")
        
    def init_operation_panel(self):
        """初始化操作面板"""
        self.operation_panel = OperationPanel(
            self.window_width - self.left_panel_width,  # 棋盘右侧
            self.window_height
        )
        
    def init_taunt_animation(self):
        """初始化嘲讽动画"""
        self.taunt_animation = TauntAnimation(self.window_width, self.window_height)

    def set_ai_info(self, ai_difficulty_info):
        """设置AI难度和算法信息"""
        self.ai_difficulty_info = ai_difficulty_info

    def update_layout(self):
        """根据当前窗口尺寸更新布局"""
        # 计算左侧面板宽度和棋盘边距
        old_width, old_height = getattr(self, 'left_panel_width', 0), getattr(self, 'window_height', 0)
        
        self.left_panel_width = int(LEFT_PANEL_WIDTH_RATIO * self.window_width)
        self.board_margin_top = int(BOARD_MARGIN_TOP_RATIO * self.window_height)
        
        # 确保棋盘和其他组件有足够的间距
        adjusted_board_margin_top = max(self.board_margin_top, 50)  # 确保有足够空间
        
        # 如果窗口尺寸发生变化，清除缓存的Surface
        if old_width != self.left_panel_width or old_height != self.window_height:
            self.left_panel_surface_cache = None
            self.left_panel_overlay_cache = None

        # 更新棋盘 - 整体右移，确保不被菜单遮挡
        self.board = TraditionalChessBoard(
            self.window_width - self.left_panel_width - 40,  # 增加更多右边距
            self.window_height,
            self.left_panel_width + 30,  # 棋盘起始位置右移更多
            adjusted_board_margin_top  # 使用调整后的顶部边距
        )

        # 不再更新全屏和音效设置按钮，因为功能已在菜单中
        # 更新头像
        avatar_radius = 40
        panel_center_x = self.left_panel_width // 2
        black_y = self.window_height // 3 - 50
        red_y = self.window_height * 2 // 3 + 30

        self.black_avatar = Avatar(panel_center_x, black_y, avatar_radius, (245, 245, 235), "黑方", False)
        self.red_avatar = Avatar(panel_center_x, red_y, avatar_radius, (255, 255, 240), "红方", True)

        # 计时器的字体
        self.timer_font = load_font(18)

    def handle_undo(self, game):
        """处理悔棋操作"""
        # 如果AI正在思考，不允许悔棋
        if hasattr(game, 'is_ai_thinking') and game.is_ai_thinking():
            return False

        # 如果游戏已经结束，先清除状态
        if game.state.game_over:
            game.popup = None
            game.state.game_over = False

        if game.game_type == "pvp":  # 人人模式直接悔棋
            if game.undo_move():
                # 悔棋成功
                game.selected_piece = None
                self.board.clear_highlights()
                self.update_avatars(game.state)

                # 清除上一步记录
                game.last_move = None
                game.last_move_notation = ""

                # 如果还有移动历史，更新上一步记录
                if hasattr(game.state, 'move_history') and len(game.state.move_history) > 0:
                    last_history = game.state.move_history[-1]
                    if 'from_pos' in last_history and 'to_pos' in last_history:
                        from_row, from_col = last_history['from_pos']
                        to_row, to_col = last_history['to_pos']
                        game.last_move = (from_row, from_col, to_row, to_col)
                        piece = game.state.get_piece_at(to_row, to_col)
                        if piece:
                            from program.utils import tools
                            game.last_move_notation = tools.generate_move_notation(
                                piece, from_row, from_col, to_row, to_col
                            )

                return True
        else:  # 人机模式
            # 首先停止任何AI计时器
            import pygame
            pygame.time.set_timer(pygame.USEREVENT + 1, 0)
            pygame.time.set_timer(pygame.USEREVENT + 2, 0)
            if hasattr(game, 'ai_manager'):
                game.ai_manager.reset_ai_state()

            # 移动历史为空，没有步骤可以悔棋
            if not hasattr(game.state, 'move_history') or len(game.state.move_history) == 0:
                return False

            # 判断当前是玩家回合还是AI回合
            is_player_turn = game.state.current_player == game.player_camp

            if is_player_turn:
                # 玩家回合 - 需要悔两步（玩家和AI各一步）
                if len(game.state.move_history) >= 1:
                    # 至少有一步可以悔棋
                    game.undo_move()  # 悔掉玩家上一步

                    # 如果还有更多步骤，尝试悔掉AI的上一步
                    if len(game.state.move_history) >= 1:
                        game.undo_move()  # 悔掉AI上一步

                    game.selected_piece = None
                    self.board.clear_highlights()
                    self.update_avatars(game.state)
                    return True
            else:
                # AI回合 - 悔一步（AI刚下的或上一个玩家步骤）
                if len(game.state.move_history) >= 1:
                    game.undo_move()
                    game.selected_piece = None
                    self.board.clear_highlights()
                    self.update_avatars(game.state)

                    # 如果悔棋后轮到AI行动，延迟1秒
                    if game.state.current_player != game.player_camp:
                        if hasattr(game, 'ai_manager'):
                            game.ai_manager.start_ai_thinking()
                        pygame.time.set_timer(pygame.USEREVENT + 2, 1000)

                    return True

        # 重置滚动位置
        if hasattr(game, 'history_scroll_y'):
            game.history_scroll_y = 0

        return False

    def _draw_background_and_side_panel(self, screen):
        """绘制背景和左侧边栏"""
        # 获取当前主题颜色
        theme_colors = theme_manager.get_theme_colors()
        
        # 如果有加载的背景图片，则绘制背景图片
        if self.loaded_background:
            screen.blit(self.loaded_background, (0, 0))
        else:
            # 使用统一的背景绘制函数
            draw_background(screen, theme_colors["background"])
        
        # 绘制左侧面板背景
        # 检查缓存的Surface是否仍然有效（大小匹配）
        if (self.left_panel_surface_cache is None or 
            self.left_panel_surface_cache.get_size() != (self.left_panel_width, self.window_height)):
            # 创建新的缓存Surface
            self.left_panel_surface_cache = pygame.Surface((self.left_panel_width, self.window_height))
            self.left_panel_overlay_cache = pygame.Surface((self.left_panel_width, self.window_height), pygame.SRCALPHA)
            
            # 绘制背景到缓存Surface
            draw_background(self.left_panel_surface_cache, theme_colors["panel"])
            
            # 应用更美观的渐变效果或纹理覆盖
            overlay = pygame.Surface((self.left_panel_width, self.window_height), pygame.SRCALPHA)
            # 创建渐变效果，使左侧面板更具层次感
            for y in range(self.window_height):
                # 根据y位置计算透明度，创建垂直渐变效果
                alpha = 20 + int(10 * abs(pygame.time.get_ticks() / 1000 * 0.1 - y / 100.0))  # 轻微的垂直变化
                overlay_color = (255, 255, 255, alpha)
                pygame.draw.line(overlay, overlay_color, (0, y), (self.left_panel_width, y))
            
            self.left_panel_surface_cache.blit(overlay, (0, 0))
        
        # 应用到主界面
        screen.blit(self.left_panel_surface_cache, (0, 0))
        
        # 添加分隔线
        pygame.draw.line(screen, theme_colors["panel_border"], (self.left_panel_width, 0),
                         (self.left_panel_width, self.window_height), 2)
        
    def create_buttons(self):
        """创建所有按钮"""
        button_width = 80
        button_height = 30
        
        # 创建全屏切换按钮 - 使用pygame.display.get_desktop_sizes()替代pygame.display.Info()
        try:
            # 尝试获取桌面尺寸
            desktop_sizes = pygame.display.get_desktop_sizes()
            current_w = desktop_sizes[0][0] if desktop_sizes else 1920  # 默认值
        except:
            current_w = 1920  # 默认值
            
        self.fullscreen_button = Button(
            self.window_width - button_width - 10,
            10,
            button_width,
            button_height,
            "全屏" if self.window_width != current_w else "窗口",
            14
        )
        # 音效设置按钮放在全屏按钮下方
        self.audio_settings_button = Button(
            self.window_width - button_width - 10,
            50,
            button_width,
            button_height,
            "音效",
            14
        )

    def create_avatars(self):
        """创建玩家头像"""
        avatar_radius = 40
        panel_center_x = self.left_panel_width // 2
        # 调整头像位置，避免与菜单栏重叠
        black_y = self.window_height // 3 - 50  # 增加顶部间距
        red_y = self.window_height * 2 // 3 + 30  # 增加与黑方头像的间距

        # 创建头像
        self.black_avatar = Avatar(panel_center_x, black_y, avatar_radius, (245, 245, 235), "黑方", False)
        self.red_avatar = Avatar(panel_center_x, red_y, avatar_radius, (255, 255, 240), "红方", True)

    def update_avatars(self, game_state):
        """更新头像状态和计时器"""
        # 检查是否需要更新计时器
        # （仅在玩家切换时更新，避免每帧都计算）
        if hasattr(self, '_last_player') and self._last_player != game_state.current_player:
            # 玩家发生了切换，更新之前的玩家用时
            current_time = pygame.time.get_ticks()
            elapsed_time = current_time - self.current_player_start_time
            
            if self._last_player == "red":
                self.red_time += elapsed_time
            else:
                self.black_time += elapsed_time
            
            # 重置当前玩家开始时间
            self.current_player_start_time = current_time
        
        # 更新当前玩家
        self._last_player = game_state.current_player
        
        # 更新头像激活状态
        is_red_turn = game_state.current_player == "red"
        self.red_avatar.set_active(is_red_turn)
        self.black_avatar.set_active(not is_red_turn)

        # 更新玩家标识
        if self.game_mode == "pvc":  # 人机模式
            if self.player_camp == "red":
                self.red_avatar.player_name = "玩家"
                self.black_avatar.player_name = "电脑"
            else:
                self.red_avatar.player_name = "电脑"
                self.black_avatar.player_name = "玩家"
        else:
            self.red_avatar.player_name = "红方"
            self.black_avatar.player_name = "黑方"

    def update_button_states(self, mouse_pos):
        """更新按钮悬停状态 - 不再更新已移除的按钮"""
        # 不再更新全屏和音效设置按钮悬停状态，因为按钮已被移除
        pass

    def draw(self, screen, game_state, last_move=None, 
             popup=None, confirm_dialog=None):
        """绘制整个游戏界面"""
        # 绘制完整的界面背景
        self._draw_background_and_side_panel(screen)

        # 绘制棋盘和棋子 - 已经右移以避免被菜单遮挡
        self.board.draw(screen, game_state.pieces, game_state)

        # 如果有上一步走法，在棋盘上标记出来
        if last_move:
            from_row, from_col, to_row, to_col = last_move
            self.board_highlight_last_move(screen, from_row, from_col, to_row, to_col)

        # 绘制游戏信息面板
        # draw_info_panel(screen, game_state)  # 这个函数不在当前类中，可能需要另外处理

        # 绘制按钮
        self.draw_buttons(screen)

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

        # 如果是人机模式，显示模式和阵营提示
        if self.game_mode == "pvc":
            mode_font = load_font(18)
            if self.player_camp == "red":
                mode_text = "人机对战模式 - 您执红方"
            else:
                mode_text = "人机对战模式 - 您执黑方"
            mode_surface = mode_font.render(mode_text, True, BLACK)
            screen.blit(mode_surface, (
                self.left_panel_width + (self.window_width - self.left_panel_width) // 2 - mode_surface.get_width() // 2,
                15))
                
            # 显示AI难度信息
            if self.ai_difficulty_info:
                ai_info_font = load_font(16)
                ai_difficulty_text = f"AI难度: {self.ai_difficulty_info['name']}"
                
                ai_difficulty_surface = ai_info_font.render(ai_difficulty_text, True, BLACK)
                
                # 显示在模式提示下方
                screen.blit(ai_difficulty_surface, (
                    self.left_panel_width + (self.window_width - self.left_panel_width) // 2 - ai_difficulty_surface.get_width() // 2,
                    45))

        # 绘制 captured pieces（阵亡棋子）
        self.draw_captured_pieces(screen, game_state)

        # 绘制棋谱历史记录
        self.draw_move_history(screen, game_state)

        # 绘制菜单
        self.option_menu.draw(screen)
        self.help_menu.draw(screen)

        # 绘制操作面板
        if self.operation_panel:
            self.operation_panel.draw(screen)

        # 更新和绘制嘲讽动画
        if self.taunt_animation:
            self.taunt_animation.update()
            self.taunt_animation.draw(screen)

        # 如果游戏结束，显示弹窗
        if popup:
            popup.draw(screen)

        # 如果有确认对话框，显示它
        if confirm_dialog:
            confirm_dialog.draw(screen)

    def board_highlight_last_move(self, screen, from_row, from_col, to_row, to_col):
        """高亮显示上一步的走法
        
        Args:
            screen: 屏幕surface
            from_row: 起点行
            from_col: 起点列
            to_row: 终点行
            to_col: 终点列
        """
        # 计算起点的像素坐标
        from_x, from_y = self.board.get_position_center(from_row, from_col)
        to_x, to_y = self.board.get_position_center(to_row, to_col)
        
        # 计算方格大小
        grid_size = self.board.board_width / 8
        
        # 绘制半透明的起点标记
        from_surface = pygame.Surface((grid_size, grid_size), pygame.SRCALPHA)
        from_surface.fill((0, 200, 80, 100))  # 绿色半透明
        screen.blit(from_surface, (from_x - grid_size/2, from_y - grid_size/2))
        
        # 绘制半透明的终点标记（更明显一些）
        to_surface = pygame.Surface((grid_size, grid_size), pygame.SRCALPHA)
        to_surface.fill((0, 200, 80, 150))  # 绿色半透明但更深
        screen.blit(to_surface, (to_x - grid_size/2, to_y - grid_size/2))
        
        # 绘制连接线
        pygame.draw.line(screen, (0, 180, 80, 200), (from_x, from_y), (to_x, to_y), 2) 

    def draw_info_panel(self, screen, game_state):
        """绘制游戏信息面板"""
        # 当游戏进行中，在左上角显示当前回合
        if not game_state.game_over:
            # 创建回合信息文本
            turn_color = RED if game_state.current_player == "red" else BLACK
            turn_text = f"当前回合: {'红方' if game_state.current_player == 'red' else '黑方'}"

            # 计算位置 - 在左上角
            font = load_font(20)
            text_surface = font.render(turn_text, True, turn_color)
            # 位于对局时长信息的下方
            text_rect = text_surface.get_rect(
                topleft=(10, 75)  # 在左上角
            )
            screen.blit(text_surface, text_rect)

    def draw_timers(self, screen, game_state):
        """绘制计时器信息"""
        # 获取当前时间
        current_time = pygame.time.get_ticks()
        
        # 计算总游戏时间
        total_elapsed = current_time - self.start_time
        total_time_str = self.format_time(total_elapsed)
        
        # 如果当前玩家正在走棋，更新其累计用时
        if game_state.current_player == "red":
            current_red_time = self.red_time + (current_time - self.current_player_start_time)
            current_black_time = self.black_time
        else:
            current_red_time = self.red_time
            current_black_time = self.black_time + (current_time - self.current_player_start_time)
        
        red_time_str = self.format_time(current_red_time)
        black_time_str = self.format_time(current_black_time)
        
        # 绘制总时间 - 在左上角
        total_time_surface = self.timer_font.render(f"对局时长: {total_time_str}", True, BLACK)
        
        # 为总时间文本添加背景矩形
        total_time_rect = total_time_surface.get_rect(topleft=(10, 45))
        total_time_bg_rect = pygame.Rect(total_time_rect.left - 5, total_time_rect.top - 3, 
                                         total_time_rect.width + 10, total_time_rect.height + 6)
        pygame.draw.rect(screen, (255, 255, 255, 200), total_time_bg_rect)  # 半透明白色背景
        screen.blit(total_time_surface, (10, 45))

        # 绘制红方时间 - 在红方头像下方，添加背景矩形
        red_time_surface = self.timer_font.render(f"用时: {red_time_str}", True, RED)
        red_time_rect = red_time_surface.get_rect(
            center=(self.left_panel_width // 2, self.red_avatar.y + self.red_avatar.radius + 60)
        )
        
        # 为红方时间添加背景矩形
        red_time_bg_rect = pygame.Rect(red_time_rect.left - 8, red_time_rect.top - 4, 
                                       red_time_rect.width + 16, red_time_rect.height + 8)
        pygame.draw.rect(screen, (255, 200, 200, 180), red_time_bg_rect)  # 淡红色半透明背景
        screen.blit(red_time_surface, red_time_rect)

        # 绘制黑方时间 - 在黑方头像下方，添加背景矩形
        black_time_surface = self.timer_font.render(f"用时: {black_time_str}", True, BLACK)
        black_time_rect = black_time_surface.get_rect(
            center=(self.left_panel_width // 2, self.black_avatar.y + self.black_avatar.radius + 60)
        )
        
        # 为黑方时间添加背景矩形
        black_time_bg_rect = pygame.Rect(black_time_rect.left - 8, black_time_rect.top - 4, 
                                         black_time_rect.width + 16, black_time_rect.height + 8)
        pygame.draw.rect(screen, (200, 200, 220, 180), black_time_bg_rect)  # 淡蓝色半透明背景
        screen.blit(black_time_surface, black_time_rect)
    
    def format_time(self, milliseconds):
        """格式化时间为 MM:SS 格式"""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def draw_buttons(self, screen):
        """绘制所有按钮 - 实际上不再绘制任何按钮，因为功能已在菜单中"""
        # 不再绘制全屏和音效设置按钮，因为功能已在菜单中
        # 此方法保留为空，以便后续兼容性
        pass

    def draw_captured_pieces(self, screen, game_state):
        """绘制双方阵亡棋子"""
        # 绘制标题
        title_font = load_font(20, bold=True)
        red_title = title_font.render("红方阵亡:", True, RED)
        black_title = title_font.render("黑方阵亡:", True, BLACK)

        # 将阵亡棋子信息移到右侧
        right_panel_x = self.window_width - 250  # 右侧边栏起始x坐标
        screen.blit(red_title, (right_panel_x, 60))
        screen.blit(black_title, (right_panel_x, 180))

        # 定义颜色和位置配置
        configurations = [
            {"color": "red", "x_start": right_panel_x, "y_start": 90, "text_color": RED},
            {"color": "black", "x_start": right_panel_x, "y_start": 210, "text_color": BLACK}
        ]

        # 绘制阵亡棋子
        for config in configurations:
            x, y = config["x_start"], config["y_start"]
            for piece in game_state.captured_pieces[config["color"]] if hasattr(game_state, 'captured_pieces') else []:
                piece_text = title_font.render(piece.name, True, config["text_color"])
                # 减小右边距，提供更多空间给棋子显示
                if x + piece_text.get_width() > self.window_width - 40:
                    x = config["x_start"]
                    y += 25
                screen.blit(piece_text, (x, y))
                x += piece_text.get_width() + 5

    def draw_move_history(self, screen, game_state):
        """绘制棋谱历史记录"""
        # 只显示最近的棋谱记录
        if hasattr(game_state, 'move_history') and game_state.move_history:
            # 绘制标题
            title_font = load_font(20, bold=True)
            history_title = title_font.render("棋谱历史:", True, BLACK)
            screen.blit(history_title, (self.window_width - 250, 300))

            # 显示最近的10条记录
            recent_moves = game_state.move_history[-10:]
            start_y = 330  # 起始y坐标
            line_spacing = 25  # 行间距

            for i, move_record in enumerate(recent_moves):
                # 处理不同格式的历史记录
                if isinstance(move_record, dict):
                    # 新格式：包含piece, from, to, captured等信息
                    piece = move_record['piece']
                    from_pos = move_record['from']
                    to_pos = move_record['to']
                    
                    # 生成棋谱记号 - 简化版
                    notation = f"{piece.name}{from_pos[0]}{from_pos[1]}->{to_pos[0]}{to_pos[1]}"
                else:
                    # 旧格式：直接包含位置信息
                    try:
                        piece, from_row, from_col, to_row, to_col, captured_piece = move_record[:6]
                        # 生成棋谱记号 - 简化版
                        notation = f"{piece.name}{from_row}{from_col}->{to_row}{to_col}"
                    except (ValueError, TypeError):
                        continue  # 如果格式不匹配，跳过这条记录

                # 计算正确编号，避免负数
                move_index = max(0, len(game_state.move_history) - 10) + i + 1

                # 根据玩家颜色确定文字颜色
                if piece.color == "red":
                    move_text = f"{move_index}. {notation}"
                    text_surface = load_font(16).render(move_text, True, RED)
                else:
                    text_surface = load_font(16).render(f"{move_index}. {notation}", True, BLACK)

                # 绘制文本
                screen.blit(text_surface, (self.window_width - 250, start_y + i * line_spacing))

    def handle_event(self, event, mouse_pos, game):
        """处理界面事件"""
        # 处理窗口大小变化
        if event.type == pygame.VIDEORESIZE:
            if not hasattr(game, 'is_fullscreen') or not game.is_fullscreen:  # 只在窗口模式下处理大小变化
                self.handle_resize((event.w, event.h))

        # 处理键盘事件
        if event.type == pygame.KEYDOWN:
            # F11或Alt+Enter切换全屏
            if event.key == pygame.K_F11 or (
                    event.key == pygame.K_RETURN and
                    pygame.key.get_mods() & pygame.KMOD_ALT
            ):
                game.toggle_fullscreen()

        # 处理鼠标点击
        if event.type == pygame.MOUSEBUTTONDOWN:
            # 检查菜单点击事件
            option_menu_result = self.option_menu.handle_event(event, mouse_pos)
            if option_menu_result == "toggle":
                # 选项菜单切换展开/折叠，不需要进一步处理
                pass
            elif option_menu_result == "导入棋局":
                from program.controllers.game_io_controller import game_io_controller
                if game_io_controller.import_game(game.state):
                    # 进入复盘模式
                    from program.controllers.replay_controller import ReplayController
                    from program.ui.replay_screen import ReplayScreen
                    
                    replay_controller = ReplayController(game.state)
                    replay_controller.start_replay()
                    
                    replay_screen = ReplayScreen(game.state, replay_controller)
                    replay_screen.run()
                return "handled"
            elif option_menu_result == "导出棋局":
                from program.controllers.game_io_controller import game_io_controller
                game_io_controller.export_game(game.state)
                return "handled"
            elif option_menu_result == "音效设置":
                from program.ui.dialogs import AudioSettingsDialog
                game.audio_settings_dialog = AudioSettingsDialog(600, 400, game.sound_manager)
                return "handled"
            elif option_menu_result == "窗口切换":
                game.toggle_fullscreen()
                return "handled"
            elif option_menu_result == "统计数据":
                # 打开统计数据界面
                from program.ui.dialogs import StatisticsDialog
                game.stats_dialog = StatisticsDialog()
                return "handled"
            elif option_menu_result == "主题切换":
                # 切换主题
                from program.controllers.game_config_manager import theme_manager
                theme_manager.toggle_theme()
                return "handled"
            
            help_menu_result = self.help_menu.handle_event(event, mouse_pos)
            if help_menu_result == "toggle":
                # 帮助菜单切换展开/折叠，不需要进一步处理
                pass
            elif help_menu_result == "游戏规则":
                # 打开游戏规则界面
                from program.ui.rules_screen import RulesScreen
                rules_screen = RulesScreen()
                rules_screen.run()
                return "handled"
            elif help_menu_result == "关于":
                # 打开关于界面，显示作者信息
                from program.ui.about_screen import AboutScreen
                about_screen = AboutScreen(self.window_width, self.window_height)
                about_screen.run()
                return "handled"
            
            # 检查操作面板点击事件
            operation_result = self.operation_panel.handle_event(event, mouse_pos)
            if operation_result == "toggle":
                # 操作面板切换展开/折叠，不需要进一步处理
                pass
            elif operation_result == "undo":
                self.handle_undo(game)
                return "handled"
            elif operation_result == "restart":
                game.reset_game()
                return "handled"
            elif operation_result == "back":
                from program.ui.dialogs import ConfirmDialog
                game.confirm_dialog = ConfirmDialog(400, 200, "是否要返回主菜单？\n这将丢失您的当前对局信息。")
                return "handled"
            elif operation_result == "exit":
                from program.ui.dialogs import ConfirmDialog
                game.confirm_dialog = ConfirmDialog(400, 200, "是否要退出游戏？\n这将结束当前对局。")
                return "handled"
            elif operation_result == "taunt":
                if self.taunt_animation:
                    self.taunt_animation.start()
                return "handled"
            
            # 处理棋子操作，只有在当前回合是玩家回合时才处理
            elif not (hasattr(game, 'is_ai_thinking') and game.is_ai_thinking()) and (game.game_type == "pvp" or
                                   game.state.current_player == game.player_camp):
                self.board_handle_click(mouse_pos, game)

    def board_handle_click(self, pos, game):
        """处理棋盘点击事件"""
        # 获取点击的棋盘位置
        grid_pos = self.board.get_grid_position(pos)
        if not grid_pos:
            return

        row, col = grid_pos

        # 选择棋子或移动棋子
        if game.state.selected_piece is None:
            # 尝试选择棋子
            if game.select_piece(row, col):
                # 播放选子音效
                try:
                    sound_manager.play_sound('choose')
                except (pygame.error, KeyError, FileNotFoundError):
                    pass
        else:
            # 已选择棋子，尝试移动
            if game.move_piece(row, col):
                # 播放移动音效
                try:
                    sound_manager.play_sound('move')
                except (pygame.error, KeyError, FileNotFoundError):
                    pass

    def handle_resize(self, size):
        """处理窗口大小调整"""
        self.window_width, self.window_height = size
        self.update_layout()

    def update_layout(self):
        """根据当前窗口尺寸更新布局"""
        # 计算左侧面板宽度和棋盘边距
        old_width, old_height = getattr(self, 'left_panel_width', 0), getattr(self, 'window_height', 0)
        
        self.left_panel_width = int(LEFT_PANEL_WIDTH_RATIO * self.window_width)
        self.board_margin_top = int(BOARD_MARGIN_TOP_RATIO * self.window_height)
        
        # 确保棋盘和其他组件有足够的间距
        adjusted_board_margin_top = max(self.board_margin_top, 50)  # 确保有足够空间
        
        # 如果窗口尺寸发生变化，清除缓存的Surface
        if old_width != self.left_panel_width or old_height != self.window_height:
            self.left_panel_surface_cache = None
            self.left_panel_overlay_cache = None

        # 更新棋盘 - 整体右移，确保不被菜单遮挡
        self.board = TraditionalChessBoard(
            self.window_width - self.left_panel_width - 40,  # 增加更多右边距
            self.window_height,
            self.left_panel_width + 30,  # 棋盘起始位置右移更多
            adjusted_board_margin_top  # 使用调整后的顶部边距
        )

        # 不再更新全屏和音效设置按钮，因为功能已在菜单中
        # 更新头像
        avatar_radius = 40
        panel_center_x = self.left_panel_width // 2
        black_y = self.window_height // 3 - 50
        red_y = self.window_height * 2 // 3 + 30

        self.black_avatar = Avatar(panel_center_x, black_y, avatar_radius, (245, 245, 235), "黑方", False)
        self.red_avatar = Avatar(panel_center_x, red_y, avatar_radius, (255, 255, 240), "红方", True)

        # 计时器的字体
        self.timer_font = load_font(18)