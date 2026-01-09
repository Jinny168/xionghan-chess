
import pygame
from program.utils.utils import load_font

class Button:
    def __init__(self, x, y, width, height, text, font_size=24):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = load_font(font_size)
        self.is_hovered = False

    def draw(self, screen):
        # 绘制按钮（带悬停效果）
        color = (120, 120, 220) if self.is_hovered else (100, 100, 200)
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)  # 边框

        # 绘制文本
        text_surface = self.font.render(self.text, True, (240, 240, 255))
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered

    def is_clicked(self, pos, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(pos):
            return True
        return False

    def update_position(self, x, y):
        """更新按钮位置"""
        self.rect.x = x
        self.rect.y = y