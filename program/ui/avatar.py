import pygame
from program.utils.utils import load_font

class Avatar:
    """玩家头像框类"""
    def __init__(self, x, y, radius, color, player_name, is_red=True):
        self.piece_font = None
        self.name_font = None
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.player_name = player_name
        self.is_red = is_red
        self.active = False  # 是否是当前活跃玩家
        
        # 加载飘逸字体 - 尝试加载几种可能的字体
        self.update_font()
        
    def update_font(self):
        """根据当前头像尺寸更新字体"""
        font_size = int(self.radius * 1.2)
        try:
            self.piece_font = load_font(font_size, bold=True)
        except (OSError, FileNotFoundError, RuntimeError):
            # 如果加载特定字体失败，使用默认字体
            self.piece_font = load_font(font_size, bold=True)
        
        # 名称字体使用普通字体
        self.name_font = load_font(18)
        
    def draw(self, screen):
        # 绘制外圆框
        border_color = (200, 100, 100) if self.is_red else (60, 60, 80)
        border_width = 3 if self.active else 2
        
        # 如果是当前活跃玩家，添加光晕效果
        if self.active:
            # 绘制光晕
            for i in range(5):
                glow_radius = self.radius + 3 + i
                alpha = 100 - i * 20
                glow_color = (255, 50, 50, alpha) if self.is_red else (50, 50, 100, alpha)
                # 创建临时表面用于光晕效果
                temp_surface = pygame.Surface((glow_radius*2, glow_radius*2), pygame.SRCALPHA)
                pygame.draw.circle(temp_surface, glow_color, (glow_radius, glow_radius), glow_radius, 2)
                screen.blit(temp_surface, (self.x - glow_radius, self.y - glow_radius))
        
        # 绘制头像背景 - 使用渐变效果
        pygame.draw.circle(screen, self.color, (self.x, self.y), self.radius)
        
        # 添加内部装饰圆圈，增强视觉效果
        inner_radius = self.radius - 5
        if self.is_red:
            inner_color = (255, 200, 200)  # 红方内部浅红色
        else:
            inner_color = (200, 200, 220)  # 黑方内部浅蓝色
        pygame.draw.circle(screen, inner_color, (self.x, self.y), inner_radius)
        
        # 绘制边框
        pygame.draw.circle(screen, border_color, (self.x, self.y), self.radius, border_width)
        
        # 绘制简单的玩家标识
        if self.is_red:
            # 红方标识 - 绘制"汉"字
            text = "汉"
            text_color = (180, 30, 30)
        else:  # black
            # 黑方标识 - 绘制"匈"字
            text = "匈"
            text_color = (30, 30, 30)
        
        # 添加文字阴影效果，提高可读性
        shadow_color = (120, 20, 20) if self.is_red else (10, 10, 10)
        shadow_offset = 1
        
        # 先绘制阴影
        text_shadow = self.piece_font.render(text, True, shadow_color)
        text_shadow_rect = text_shadow.get_rect(center=(self.x + shadow_offset, self.y + shadow_offset))
        screen.blit(text_shadow, text_shadow_rect)
        
        # 再绘制主要文字
        text_surface = self.piece_font.render(text, True, text_color)
        text_rect = text_surface.get_rect(center=(self.x, self.y))
        screen.blit(text_surface, text_rect)
        
        # 绘制玩家名称 - 添加背景矩形，提高可读性
        name_surface = self.name_font.render(self.player_name, True, (20, 20, 20))
        name_rect = name_surface.get_rect(center=(self.x, self.y + self.radius + 25))
        
        # 绘制名称背景矩形
        name_bg_rect = pygame.Rect(name_rect.left - 8, name_rect.top - 4, 
                                   name_rect.width + 16, name_rect.height + 8)
        name_bg_color = (255, 255, 255, 180)  # 半透明白色背景
        temp_surface = pygame.Surface((name_bg_rect.width, name_bg_rect.height), pygame.SRCALPHA)
        temp_surface.fill(name_bg_color)
        screen.blit(temp_surface, (name_bg_rect.x, name_bg_rect.y))
        
        screen.blit(name_surface, name_rect)
        
    def set_active(self, active):
        """设置是否是当前活跃玩家"""
        self.active = active
        
    def update_position(self, x, y, radius=None):
        """更新头像位置和大小"""
        self.x = x
        self.y = y
        if radius:
            self.radius = radius
            self.update_font()  # 如果大小变化，需要更新字体