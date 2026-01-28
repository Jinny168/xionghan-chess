"""复盘界面，用于控制棋局复盘过程"""
import pygame

from program.controllers.game_config_manager import (
    LEFT_PANEL_WIDTH_RATIO, BOARD_MARGIN_TOP_RATIO,
    PANEL_BORDER, PANEL_COLOR
)
from program.ui.avatar import Avatar
from program.ui.button import Button
from program.ui.chess_board import ChessBoard
from program.utils.utils import load_font, draw_background


class ReplayScreen:
    """复盘界面类"""
    
    def __init__(self, game_state, replay_controller):
        """初始化复盘界面
        
        Args:
            game_state: 游戏状态对象
            replay_controller: 复盘控制器
        """
        self.game_state = game_state
        self.controller = replay_controller
        
        # 获取屏幕尺寸
        info = pygame.display.Info()
        self.screen_width = info.current_w
        self.screen_height = info.current_h
        
        # 左侧面板宽度
        self.left_panel_width = int(LEFT_PANEL_WIDTH_RATIO * self.screen_width)
        self.board_margin_top = int(BOARD_MARGIN_TOP_RATIO * self.screen_height)
        
        # 初始化界面元素
        self.init_ui_elements()
        self.create_avatars()
        
        # 标志位
        self.running = True
    
    def init_ui_elements(self):
        """初始化界面元素"""
        # 按钮尺寸和间距
        button_width = 100
        button_height = 40
        button_spacing = 10
        
        # 计算按钮区域总宽度
        total_buttons_width = 5 * button_width + 4 * button_spacing
        # 将按钮放在屏幕底部中央，但要避开左侧面板
        start_x = self.left_panel_width + (self.screen_width - self.left_panel_width - total_buttons_width) // 2
        button_y = self.screen_height - 100  # 距离底部一定距离
        
        # 创建控制按钮
        self.beginning_button = Button(
            start_x, button_y, button_width, button_height, "开局", 20
        )
        self.previous_button = Button(
            start_x + button_width + button_spacing, button_y, button_width, button_height, "上一步", 20
        )
        self.next_button = Button(
            start_x + 2 * (button_width + button_spacing), button_y, button_width, button_height, "下一步", 20
        )
        self.end_button = Button(
            start_x + 3 * (button_width + button_spacing), button_y, button_width, button_height, "终局", 20
        )
        # 返回按钮
        self.return_button = Button(
            start_x + 4 * (button_width + button_spacing), button_y, button_width, button_height, "返回", 20
        )
        
        # 进度条相关参数
        self.progress_bar_x = start_x
        self.progress_bar_y = button_y - 40
        self.progress_bar_width = total_buttons_width
        self.progress_bar_height = 15
        self.dragging_progress = False  # 是否正在拖拽进度条
    
    def create_avatars(self):
        """创建玩家头像"""
        avatar_radius = 40
        panel_center_x = self.left_panel_width // 2
        black_y = self.screen_height // 3 - 50
        red_y = self.screen_height * 2 // 3

        # 创建头像
        self.black_avatar = Avatar(panel_center_x, black_y, avatar_radius, (245, 245, 235), "黑方", False)
        self.red_avatar = Avatar(panel_center_x, red_y, avatar_radius, (255, 255, 240), "红方", True)
    
    def handle_events(self, events):
        """处理事件
        
        Args:
            events: pygame事件列表
            
        Returns:
            bool: 是否继续运行
        """
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
                return False
            
            mouse_pos = pygame.mouse.get_pos()
            
            # 处理按钮点击
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左键
                    # 检查是否点击了进度条
                    if (self.progress_bar_x <= mouse_pos[0] <= self.progress_bar_x + self.progress_bar_width and
                        self.progress_bar_y <= mouse_pos[1] <= self.progress_bar_y + self.progress_bar_height):
                        # 计算点击位置对应的进度百分比
                        click_percentage = max(0, min(100, 
                            int(((mouse_pos[0] - self.progress_bar_x) / self.progress_bar_width) * 100)))
                        self.controller.set_progress(click_percentage)
                        self.dragging_progress = True
                    elif self.beginning_button.is_clicked(mouse_pos, event):
                        self.controller.go_to_beginning()
                    elif self.previous_button.is_clicked(mouse_pos, event):
                        self.controller.go_to_previous()
                    elif self.next_button.is_clicked(mouse_pos, event):
                        self.controller.go_to_next()
                    elif self.end_button.is_clicked(mouse_pos, event):
                        self.controller.go_to_end()
                    elif self.return_button.is_clicked(mouse_pos, event):
                        self.exit_replay()
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.dragging_progress = False
            
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging_progress:
                    # 拖拽进度条
                    drag_percentage = max(0, min(100,
                        int(((mouse_pos[0] - self.progress_bar_x) / self.progress_bar_width) * 100)))
                    self.controller.set_progress(drag_percentage)
        
        return self.running
    
    def draw(self, screen):
        """绘制复盘界面
        
        Args:
            screen: pygame屏幕对象
        """
        # 绘制背景和左侧边栏
        self._draw_background_and_side_panel(screen)
        
        # 绘制棋盘（使用游戏主界面的棋盘绘制方式）
        self.draw_board(screen)
        
        # 绘制玩家头像
        self.red_avatar.draw(screen)
        self.black_avatar.draw(screen)
        
        # 在左侧面板中添加VS标志
        vs_font = load_font(36, bold=True)
        vs_text = "VS"
        vs_surface = vs_font.render(vs_text, True, (100, 100, 100))
        vs_rect = vs_surface.get_rect(center=(self.left_panel_width // 2, self.screen_height // 2))
        screen.blit(vs_surface, vs_rect)
        
        # 绘制控制按钮
        self.beginning_button.draw(screen)
        self.previous_button.draw(screen)
        self.next_button.draw(screen)
        self.end_button.draw(screen)
        self.return_button.draw(screen)  # 绘制返回按钮
        
        # 绘制进度条
        self.draw_progress_bar(screen)
        
        # 绘制步骤信息
        self.draw_step_info(screen)
    
    def _draw_background_and_side_panel(self, screen):
        """绘制背景和左侧边栏"""
        # 使用统一的背景绘制函数
        draw_background(screen)
        
        # 绘制左侧面板背景
        left_panel_surface = pygame.Surface((self.left_panel_width, self.screen_height))
        left_panel_surface.fill(PANEL_COLOR)
        screen.blit(left_panel_surface, (0, 0))
        
        # 添加分隔线
        pygame.draw.line(screen, PANEL_BORDER, (self.left_panel_width, 0),
                         (self.left_panel_width, self.screen_height), 2)
    
    def draw_board(self, screen):
        """绘制棋盘（使用游戏主界面的棋盘绘制逻辑）"""
        # 计算棋盘尺寸和位置 - 适应复盘界面
        board_width = self.screen_width - self.left_panel_width - 100  # 减去左边距和右边距
        board_height = min(board_width, self.screen_height - 100)  # 限制高度，避免超出屏幕
        board_x = self.left_panel_width + 50  # 从左侧面板右侧开始
        board_y = 50  # 顶部边距

        # 创建ChessBoard实例并绘制
        temp_board = ChessBoard(board_width, self.screen_height, board_x, board_y)
        # 安全地传递game_state，如果它有必要的方法则传递，否则只传递pieces
        if hasattr(self.game_state, 'get_resurrection_positions'):
            temp_board.draw(screen, self.game_state.pieces, self.game_state)
        else:
            # 如果game_state不包含所需方法，只传递pieces，不绘制复活标记
            temp_board.draw(screen, self.game_state.pieces)
    
    def draw_progress_bar(self, screen):
        """绘制进度条"""
        # 绘制进度条背景
        pygame.draw.rect(screen, (200, 200, 200), 
                         (self.progress_bar_x, self.progress_bar_y, 
                          self.progress_bar_width, self.progress_bar_height))
        
        # 绘制已填充部分
        filled_width = int((self.controller.get_progress_percentage() / 100) * self.progress_bar_width)
        pygame.draw.rect(screen, (0, 150, 255), 
                         (self.progress_bar_x, self.progress_bar_y, 
                          filled_width, self.progress_bar_height))
        
        # 绘制边框
        pygame.draw.rect(screen, (100, 100, 100), 
                         (self.progress_bar_x, self.progress_bar_y, 
                          self.progress_bar_width, self.progress_bar_height), 2)
        
        # 绘制滑块
        slider_x = self.progress_bar_x + filled_width
        pygame.draw.circle(screen, (0, 100, 200), 
                          (slider_x, self.progress_bar_y + self.progress_bar_height // 2), 
                          self.progress_bar_height // 2)
    
    def draw_step_info(self, screen):
        """绘制步骤信息"""
        font = load_font(20)
        if font:
            # 显示当前步骤和总步骤
            step_text = f"步骤: {self.controller.current_step} / {self.controller.max_steps}"
            text_surface = font.render(step_text, True, (0, 0, 0))
            screen.blit(text_surface, (self.screen_width // 2 - text_surface.get_width() // 2, 
                                      self.progress_bar_y - 30))
    
    def run(self):
        """运行复盘界面"""
        clock = pygame.time.Clock()
        
        # 获取当前显示的屏幕
        current_screen = pygame.display.get_surface()
        if current_screen is None:
            current_screen = pygame.display.set_mode((1200, 900), pygame.RESIZABLE)
        
        while self.running:
            events = pygame.event.get()
            
            # 处理事件
            if not self.handle_events(events):
                break
            
            # 绘制界面
            self.draw(current_screen)
            
            # 更新显示
            pygame.display.flip()
            clock.tick(60)  # 60 FPS
    
    def exit_replay(self):
        """退出复盘模式"""
        self.running = False
        # 恢复原始游戏状态
        self.controller.restore_original_state()