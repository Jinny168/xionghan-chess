"""
匈汉象棋网络连接界面
"""
import sys
from tkinter import Tk
from tkinter.simpledialog import askstring

import pygame

from program.config.config import DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT, BLACK, FPS
from program.ui.button import Button
from program.utils.utils import load_font, draw_background


class NetworkConnectScreen:
    """网络连接界面"""
    
    def __init__(self):
        self.window_width = DEFAULT_WINDOW_WIDTH
        self.window_height = DEFAULT_WINDOW_HEIGHT
        self.is_fullscreen = False
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("匈汉象棋 - 网络连接")
        
        self.update_layout()
        self.connection_type = None  # 'host' 或 'join'
        self.ip_address = ""
        
    def update_layout(self):
        """更新布局"""
        button_width = 220  # 缩小按钮
        button_height = 50
        button_spacing = 25
        center_x = self.window_width // 2
        center_y = self.window_height // 2 - 30
        
        # 创建按钮
        self.host_button = Button(
            center_x - button_width // 2,
            center_y - button_height - button_spacing,
            button_width,
            button_height,
            "创建房间",
            24
        )
        
        self.join_button = Button(
            center_x - button_width // 2,
            center_y,
            button_width,
            button_height,
            "加入房间",
            24
        )
        
        self.back_button = Button(
            center_x - button_width // 2,
            center_y + button_height + button_spacing,
            button_width,
            button_height,
            "返回",
            24
        )
    
    def toggle_fullscreen(self):
        """切换全屏模式"""
        self.is_fullscreen = not self.is_fullscreen
        
        if self.is_fullscreen:
            # 获取显示器信息
            info = pygame.display.Info()
            # 保存窗口模式的尺寸
            self.windowed_size = (self.window_width, self.window_height)
            # 切换到全屏模式
            self.screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
            self.window_width = info.current_w
            self.window_height = info.current_h
        else:
            # 恢复窗口模式
            self.window_width, self.window_height = self.windowed_size
            self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        
        # 更新布局
        self.update_layout()
        
    def handle_resize(self, new_size):
        """处理窗口大小变化"""
        self.window_width, self.window_height = new_size
        # 更新布局
        self.update_layout()
    
    def show_ip_input_dialog(self):
        """显示IP输入对话框"""
        root = Tk()
        root.withdraw()  # 隐藏主窗口
        ip = askstring("加入房间", "请输入房间IP地址:", initialvalue="127.0.0.1")
        root.destroy()
        return ip
    
    def run(self):
        """运行网络连接界面"""
        clock = pygame.time.Clock()
        
        while self.connection_type is None:
            mouse_pos = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
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
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.host_button.is_clicked(mouse_pos, event):
                        # 创建房间 - 为了防止阻塞，立即返回
                        self.connection_type = "host"
                    elif self.join_button.is_clicked(mouse_pos, event):
                        # 弹出IP输入对话框
                        ip = self.show_ip_input_dialog()
                        if ip:
                            self.ip_address = ip
                            self.connection_type = "join"
                    elif self.back_button.is_clicked(mouse_pos, event):
                        self.connection_type = "back"
            
            # 更新按钮悬停状态
            self.host_button.check_hover(mouse_pos)
            self.join_button.check_hover(mouse_pos)
            self.back_button.check_hover(mouse_pos)
            
            # 绘制界面
            self.draw()
            pygame.display.flip()
            clock.tick(FPS)
        
        return self.connection_type, self.ip_address
    
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