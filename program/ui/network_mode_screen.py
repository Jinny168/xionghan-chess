import sys

import pygame

from program.controllers.game_config_manager import (
    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT,
    BLACK, FPS
)
from program.controllers.sound_manager import sound_manager
from program.ui.button import StyledButton
from program.utils import tools
from program.utils.utils import load_font, draw_background


class NetworkModeScreen:
    """网络对战模式选择界面"""
    
    def __init__(self):
        self.windowed_size = None
        self.back_button = None
        self.join_button = None
        self.host_button = None
        self.window_width = DEFAULT_WINDOW_WIDTH
        self.window_height = DEFAULT_WINDOW_HEIGHT
        self.is_fullscreen = False
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("匈汉象棋 - 网络对战")
        
        # 初始化声音管理器
        self.sound_manager = sound_manager
        
        self.update_layout()
        self.selected_option = None
        
    def update_layout(self):
        """更新布局"""
        button_width = 200  # 进一步缩小按钮
        button_height = 50
        button_spacing = 25
        center_x = self.window_width // 2
        center_y = self.window_height // 2
        
        # 创建按钮
        self.host_button = StyledButton(  # 使用StyledButton替代Button
            center_x - button_width // 2,
            center_y - button_height - button_spacing,
            button_width,
            button_height,
            "创建房间",
            24,
            10  # 圆角
        )
        
        self.join_button = StyledButton(  # 使用StyledButton替代Button
            center_x - button_width // 2,
            center_y,
            button_width,
            button_height,
            "加入房间",
            24,
            10  # 圆角
        )
        
        self.back_button = StyledButton(  # 使用StyledButton替代Button
            center_x - button_width // 2,
            center_y + button_height + button_spacing,
            button_width,
            button_height,
            "返回",
            24,
            10  # 圆角
        )
    
    def run(self):
        """运行网络模式选择界面"""
        clock = pygame.time.Clock()
        
        while self.selected_option is None:
            mouse_pos = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                # 处理窗口大小变化
                if event.type == pygame.VIDEORESIZE:
                    if not self.is_fullscreen:  # 只在窗口模式下处理大小变化
                        self.window_width, self.window_height = event.w, event.h
                        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
                        self.update_layout()
                
                # 处理键盘事件
                if event.type == pygame.KEYDOWN:
                    # F11或Alt+Enter切换全屏
                    if event.key == pygame.K_F11 or (
                        event.key == pygame.K_RETURN and 
                        pygame.key.get_mods() & pygame.KMOD_ALT
                    ):
                        self.toggle_fullscreen()
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.host_button.is_clicked(mouse_pos, event):
                        self.selected_option = "host"
                    elif self.join_button.is_clicked(mouse_pos, event):
                        self.selected_option = "join"
                    elif self.back_button.is_clicked(mouse_pos, event):
                        self.selected_option = "back"
            
            # 更新按钮悬停状态
            self.host_button.check_hover(mouse_pos)
            self.join_button.check_hover(mouse_pos)
            self.back_button.check_hover(mouse_pos)
            
            # 绘制界面
            self.draw()
            pygame.display.flip()
            clock.tick(FPS)
        
        return self.selected_option
    
    def draw(self):
        """绘制界面"""
        # 使用统一的背景绘制函数
        draw_background(self.screen)
        
        # 绘制标题
        title_font = load_font(48)
        title_text = "网络对战"
        title_surface = title_font.render(title_text, True, BLACK)
        title_rect = title_surface.get_rect(center=(self.window_width//2, 150))
        self.screen.blit(title_surface, title_rect)
        
        # 绘制副标题
        subtitle_font = load_font(24)
        subtitle_text = "请选择网络对战方式"
        subtitle_surface = subtitle_font.render(subtitle_text, True, BLACK)
        subtitle_rect = subtitle_surface.get_rect(center=(self.window_width//2, 200))
        self.screen.blit(subtitle_surface, subtitle_rect)
        
        # 绘制按钮
        self.host_button.draw(self.screen)
        self.join_button.draw(self.screen)
        self.back_button.draw(self.screen)
        
        # 移除说明文字，减少界面拥挤
    
    def toggle_fullscreen(self):
        """切换全屏模式"""
        # 使用通用的全屏切换函数
        self.screen, self.window_width, self.window_height, self.is_fullscreen, self.windowed_size = \
            tools.toggle_fullscreen(self.window_width, self.window_height, self.is_fullscreen, self.windowed_size)
        
        # 更新布局
        self.update_layout()

