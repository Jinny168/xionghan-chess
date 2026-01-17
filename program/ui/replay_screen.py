"""复盘界面，用于控制棋局复盘过程"""
import pygame
from program.ui.button import Button
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
        
        # 初始化界面元素
        self.init_ui_elements()
        
        # 标志位
        self.running = True
    
    def init_ui_elements(self):
        """初始化界面元素"""
        # 获取屏幕尺寸
        info = pygame.display.Info()
        screen_width, screen_height = info.current_w, info.current_h
        
        # 按钮尺寸和间距
        button_width = 100
        button_height = 40
        button_spacing = 10
        
        # 计算按钮区域总宽度
        total_buttons_width = 4 * button_width + 3 * button_spacing
        start_x = (screen_width - total_buttons_width) // 2
        button_y = screen_height - 120  # 距离底部一定距离
        
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
        
        # 进度条相关参数
        self.progress_bar_x = start_x
        self.progress_bar_y = button_y - 40
        self.progress_bar_width = total_buttons_width
        self.progress_bar_height = 15
        self.dragging_progress = False  # 是否正在拖拽进度条
    
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
        # 绘制背景
        draw_background(screen)
        
        # 绘制棋盘（使用游戏状态）
        self.draw_board(screen)
        
        # 绘制控制按钮
        self.beginning_button.draw(screen)
        self.previous_button.draw(screen)
        self.next_button.draw(screen)
        self.end_button.draw(screen)
        
        # 绘制进度条
        self.draw_progress_bar(screen)
        
        # 绘制步骤信息
        self.draw_step_info(screen)
    
    def draw_board(self, screen):
        """绘制棋盘（使用现有的棋盘绘制逻辑）"""
        # 获取屏幕尺寸
        screen_width, screen_height = screen.get_size()
        
        # 计算棋盘尺寸和位置
        board_size = min(screen_width * 0.8, screen_height * 0.8)
        board_x = (screen_width - board_size) // 2
        board_y = 100  # 距离顶部一定距离
        
        # 计算每个格子的尺寸
        grid_size = board_size / 12  # 12个间隔，因为是13x13的棋盘
        
        # 绘制棋盘网格
        line_color = (0, 0, 0)  # 黑色线条
        
        # 绘制垂直线
        for i in range(13):
            start_pos = (int(board_x + i * grid_size), int(board_y))
            end_pos = (int(board_x + i * grid_size), int(board_y + 12 * grid_size))
            pygame.draw.line(screen, line_color, start_pos, end_pos, 1)
        
        # 绘制水平线
        for i in range(13):
            start_pos = (int(board_x), int(board_y + i * grid_size))
            end_pos = (int(board_x + 12 * grid_size), int(board_y + i * grid_size))
            pygame.draw.line(screen, line_color, start_pos, end_pos, 1)
        
        # 绘制特殊标记线（如楚河汉界等）
        # 绘制"楚河汉界"区域
        mid_x = board_x + 6 * grid_size
        pygame.draw.line(screen, line_color, (int(mid_x), int(board_y)), 
                         (int(mid_x), int(board_y + 12 * grid_size)), 1)
        
        # 在楚河汉界中间添加文字
        font = load_font(int(grid_size * 0.4))
        if font:
            river_text = font.render("楚 河 汉 界", True, (0, 0, 0))
            river_rect = river_text.get_rect(center=(int(mid_x), int(board_y + 6 * grid_size)))
            screen.blit(river_text, river_rect)
        
        # 绘制棋子
        for piece in self.game_state.pieces:
            row, col = piece.row, piece.col
            center_x = int(board_x + col * grid_size)
            center_y = int(board_y + row * grid_size)
            
            # 根据棋子颜色设置颜色
            color = (255, 0, 0) if piece.color == "red" else (0, 0, 0)  # 红色或黑色
            
            # 绘制棋子圆形
            pygame.draw.circle(screen, (240, 240, 240), (center_x, center_y), int(grid_size * 0.4))
            pygame.draw.circle(screen, color, (center_x, center_y), int(grid_size * 0.4), 2)
            
            # 绘制棋子文字
            font = load_font(int(grid_size * 0.3))
            if font:
                text_surface = font.render(piece.name, True, color if piece.color == "red" else (255, 255, 255))
                text_rect = text_surface.get_rect(center=(center_x, center_y))
                screen.blit(text_surface, text_rect)
    
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
            screen.blit(text_surface, (screen.get_width() // 2 - text_surface.get_width() // 2, 
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