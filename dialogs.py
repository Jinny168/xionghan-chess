import pygame
from ui_elements import Button
from utils import load_font

# 颜色定义
BLACK = (0, 0, 0)
RED = (180, 30, 30)
POPUP_BG = (250, 240, 230)  # 更亮的弹窗背景色
BUTTON_COLOR = (100, 100, 200)
BUTTON_HOVER = (120, 120, 220)
BUTTON_TEXT = (240, 240, 255)

class PopupDialog:
    def __init__(self, width, height, message, total_time=0, red_time=0, black_time=0):
        self.width = width
        self.height = height
        self.message = message
        self.total_time = total_time
        self.red_time = red_time
        self.black_time = black_time
        
        # 计算弹窗位置 - 会在绘制时动态计算
        self.x = 0
        self.y = 0
        
        # 创建"重新开始"按钮
        button_width = 160
        button_height = 50
        self.button_width = button_width
        self.button_height = button_height
        self.restart_button = None  # 会在绘制时动态创建
        
    def draw(self, screen):
        # 获取当前窗口尺寸
        window_width, window_height = screen.get_size()
        
        # 重新计算弹窗位置
        self.x = (window_width - self.width) // 2
        self.y = (window_height - self.height) // 2
        
        # 更新按钮位置
        button_x = self.x + (self.width - self.button_width) // 2
        button_y = self.y + self.height - self.button_height - 20
        self.restart_button = Button(button_x, button_y, self.button_width, self.button_height, "重新开始")
        
        # 绘制半透明背景
        overlay = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))  # 半透明黑色
        screen.blit(overlay, (0, 0))
        
        # 绘制弹窗主体
        pygame.draw.rect(screen, POPUP_BG, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, BLACK, (self.x, self.y, self.width, self.height), 3)
        
        # 添加装饰边框
        inner_margin = 10
        pygame.draw.rect(
            screen, 
            (180, 180, 180), 
            (self.x + inner_margin, self.y + inner_margin, 
             self.width - 2*inner_margin, self.height - 2*inner_margin), 
            2
        )
        
        # 绘制标题文本
        font_big = load_font(40)
        text_surface = font_big.render("游戏结束", True, BLACK)
        text_rect = text_surface.get_rect(center=(window_width//2, self.y + 50))
        screen.blit(text_surface, text_rect)
        
        # 绘制结果文本
        font = load_font(32)
        text_surface = font.render(self.message, True, RED)
        text_rect = text_surface.get_rect(center=(window_width//2, self.y + 110))
        screen.blit(text_surface, text_rect)
        
        # 绘制时间信息
        time_font = load_font(20)
        
        # 显示总用时
        total_time_str = f"{int(self.total_time//60):02}:{int(self.total_time%60):02}"
        total_time_text = f"对局总时长: {total_time_str}"
        total_time_surface = time_font.render(total_time_text, True, BLACK)
        total_time_rect = total_time_surface.get_rect(center=(window_width//2, self.y + 160))
        screen.blit(total_time_surface, total_time_rect)
        
        # 显示红方用时
        red_time_str = f"{int(self.red_time//60):02}:{int(self.red_time%60):02}"
        red_time_text = f"红方用时: {red_time_str}"
        red_time_surface = time_font.render(red_time_text, True, RED)
        red_time_rect = red_time_surface.get_rect(center=(window_width//2, self.y + 190))
        screen.blit(red_time_surface, red_time_rect)
        
        # 显示黑方用时
        black_time_str = f"{int(self.black_time//60):02}:{int(self.black_time%60):02}"
        black_time_text = f"黑方用时: {black_time_str}"
        black_time_surface = time_font.render(black_time_text, True, BLACK)
        black_time_rect = black_time_surface.get_rect(center=(window_width//2, self.y + 220))
        screen.blit(black_time_surface, black_time_rect)
        
        # 绘制按钮
        self.restart_button.draw(screen)
    
    def handle_event(self, event, mouse_pos):
        # 如果按钮尚未创建，返回False
        if not self.restart_button:
            return False
            
        # 处理鼠标悬停
        self.restart_button.check_hover(mouse_pos)
        
        # 检查按钮点击
        if self.restart_button.is_clicked(mouse_pos, event):
            return True
        return False

class ConfirmDialog:
    def __init__(self, width, height, message):
        self.width = width
        self.height = height
        self.message = message
        
        # 计算弹窗位置 - 会在绘制时动态计算
        self.x = 0
        self.y = 0
        
        # 按钮尺寸
        self.button_width = 120
        self.button_height = 40
        self.button_spacing = 30
        
        # 按钮会在绘制时动态创建
        self.confirm_button = None
        self.cancel_button = None
        
        # 结果
        self.result = None  # None = 未选择, True = 确认, False = 取消
        
    def draw(self, screen):
        # 获取当前窗口尺寸
        window_width, window_height = screen.get_size()
        
        # 重新计算弹窗位置
        self.x = (window_width - self.width) // 2
        self.y = (window_height - self.height) // 2
        
        # 更新按钮位置
        confirm_x = self.x + (self.width // 2) - self.button_width - (self.button_spacing // 2)
        confirm_y = self.y + self.height - self.button_height - 20
        self.confirm_button = Button(confirm_x, confirm_y, self.button_width, self.button_height, "确认")
        
        cancel_x = self.x + (self.width // 2) + (self.button_spacing // 2)
        cancel_y = self.y + self.height - self.button_height - 20
        self.cancel_button = Button(cancel_x, cancel_y, self.button_width, self.button_height, "取消")
        
        # 绘制半透明背景
        overlay = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))  # 半透明黑色
        screen.blit(overlay, (0, 0))
        
        # 绘制弹窗主体
        pygame.draw.rect(screen, POPUP_BG, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, BLACK, (self.x, self.y, self.width, self.height), 3)
        
        # 添加装饰边框
        inner_margin = 10
        pygame.draw.rect(
            screen, 
            (180, 180, 180), 
            (self.x + inner_margin, self.y + inner_margin, 
             self.width - 2*inner_margin, self.height - 2*inner_margin), 
            2
        )
        
        # 绘制标题文本
        font_big = load_font(36)
        text_surface = font_big.render("确认", True, BLACK)
        text_rect = text_surface.get_rect(center=(window_width//2, self.y + 40))
        screen.blit(text_surface, text_rect)
        
        # 绘制确认信息文本
        font = load_font(24)
        # 处理消息换行显示
        lines = self.message.split('\n')
        line_height = 30
        start_y = self.y + 90
        
        for i, line in enumerate(lines):
            text_surface = font.render(line, True, BLACK)
            text_rect = text_surface.get_rect(center=(window_width//2, start_y + i * line_height))
            screen.blit(text_surface, text_rect)
        
        # 绘制按钮
        self.confirm_button.draw(screen)
        self.cancel_button.draw(screen)
    
    def handle_event(self, event, mouse_pos):
        # 如果按钮尚未创建，返回None
        if not self.confirm_button or not self.cancel_button:
            return None
            
        # 处理鼠标悬停
        self.confirm_button.check_hover(mouse_pos)
        self.cancel_button.check_hover(mouse_pos)
        
        # 检查按钮点击
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.confirm_button.rect.collidepoint(mouse_pos):
                self.result = True
                return self.result
            elif self.cancel_button.rect.collidepoint(mouse_pos):
                self.result = False
                return self.result
        
        return None