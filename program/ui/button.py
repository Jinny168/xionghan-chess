
import pygame
from program.utils.tools import load_font

class Button:
    def __init__(self, x, y, width, height, text, font_size=24):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = load_font(font_size)
        self.is_hovered = False
        self.enabled = True  # 添加启用/禁用状态

    def draw(self, screen):
        # 绘制按钮（带悬停效果和禁用状态）
        if not self.enabled:
            # 禁用状态：灰色
            color = (100, 100, 100)
            border_color = (80, 80, 80)
            text_color = (180, 180, 180)
        else:
            # 正常状态
            color = (120, 120, 220) if self.is_hovered else (100, 100, 200)
            border_color = (0, 0, 0)
            text_color = (240, 240, 255)
            
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, border_color, self.rect, 2)  # 边框

        # 绘制文本
        text_surface = self.font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered

    def is_clicked(self, pos, event):
        # 只有启用状态下才能点击
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(pos):
            return True
        return False

    def update_position(self, x, y):
        """更新按钮位置"""
        self.rect.x = x
        self.rect.y = y


class StyledButton:
    """美化版按钮，带有渐变效果和圆角"""

    def __init__(self, x, y, width, height, text, font_size=24, corner_radius=8):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = load_font(font_size)
        self.is_hovered = False
        self.enabled = True  # 添加启用/禁用状态
        self.corner_radius = corner_radius  # 圆角半径

    def draw(self, screen):
        # 定义颜色
        if not self.enabled:
            # 禁用状态：灰色
            color1 = (100, 100, 100)
            color2 = (80, 80, 80)
            border_color = (60, 60, 60)
            text_color = (180, 180, 180)
        elif self.is_hovered:
            # 悬停时使用较亮的颜色
            color1 = (150, 150, 255)
            color2 = (100, 100, 220)
            border_color = (80, 80, 180)
            text_color = (255, 255, 255)
        else:
            # 默认颜色
            color1 = (120, 120, 220)
            color2 = (80, 80, 180)
            border_color = (60, 60, 140)
            text_color = (255, 255, 255)

        # 绘制带圆角的按钮背景（带渐变效果）
        # 首先绘制圆角矩形背景
        pygame.draw.rect(screen, color1, self.rect, border_radius=self.corner_radius)

        # 绘制渐变效果（垂直渐变）
        for i in range(self.rect.height):
            # 计算垂直渐变
            ratio = i / self.rect.height
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            pygame.draw.line(screen, (r, g, b),
                             (self.rect.left, self.rect.top + i),
                             (self.rect.right, self.rect.top + i),
                             1)

        # 绘制圆角边框
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=self.corner_radius)

        # 添加轻微阴影效果
        shadow_rect = pygame.Rect(self.rect.x + 2, self.rect.y + 2, self.rect.width, self.rect.height)
        pygame.draw.rect(screen, (40, 40, 80, 100), shadow_rect, 2, border_radius=self.corner_radius)

        # 绘制带描边的文字
        # 先绘制描边（黑色）
        outline_offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        for offset_x, offset_y in outline_offsets:
            outline_text = self.font.render(self.text, True, (0, 0, 0))  # 黑色描边
            outline_rect = outline_text.get_rect(center=(self.rect.centerx + offset_x, self.rect.centery + offset_y))
            screen.blit(outline_text, outline_rect)

        # 再绘制主体文字（根据状态选择颜色）
        text_surface = self.font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered

    def is_clicked(self, pos, event):
        # 只有启用状态下才能点击
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(pos):
            return True
        return False

    def update_position(self, x, y):
        """更新按钮位置"""
        self.rect.x = x
        self.rect.y = y
