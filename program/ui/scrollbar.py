import pygame


class ScrollBar:
    """自定义滚动条类"""
    def __init__(self, x, y, width, height, content_height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.content_height = content_height
        self.scroll_pos = 0
        self.dragging = False
        self.drag_offset = 0
        
        # 计算滑块高度
        if content_height > 0:
            self.ratio = height / content_height
            self.slider_height = max(20, int(height * self.ratio))
        else:
            self.ratio = 0
            self.slider_height = 20
        self.slider_y = y
        
    def draw(self, screen):
        # 绘制滚动条背景
        pygame.draw.rect(screen, (200, 200, 200), (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, (100, 100, 100), (self.x, self.y, self.width, self.height), 2)
        
        # 绘制滑块
        slider_rect = pygame.Rect(self.x + 2, self.slider_y, self.width - 4, self.slider_height)
        pygame.draw.rect(screen, (180, 180, 180), slider_rect)
        pygame.draw.rect(screen, (100, 100, 100), slider_rect, 2)
        
    def handle_event(self, event, mouse_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.x <= mouse_pos[0] <= self.x + self.width and self.y <= mouse_pos[1] <= self.y + self.height:
                # 检查是否点击滑块
                if self.slider_y <= mouse_pos[1] <= self.slider_y + self.slider_height:
                    self.dragging = True
                    self.drag_offset = mouse_pos[1] - self.slider_y
                else:
                    # 点击滚动条其他部分，调整滚动位置
                    if mouse_pos[1] < self.slider_y:
                        # 向上滚动
                        self.scroll_pos = max(0, self.scroll_pos - self.height // 2)
                    else:
                        # 向下滚动
                        self.scroll_pos = min(max(0, self.content_height - self.height), self.scroll_pos + self.height // 2)
                    # 根据新的滚动位置更新滑块位置
                    self._update_slider_position()
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            new_y = mouse_pos[1] - self.drag_offset
            # 限制滑块在滚动条范围内
            new_y = max(self.y, min(new_y, self.y + self.height - self.slider_height))
            self.slider_y = new_y
            # 更新滚动位置，基于滑块的新位置
            if self.height > self.slider_height and self.content_height > self.height:
                ratio = (new_y - self.y) / (self.height - self.slider_height)
                self.scroll_pos = int(ratio * (self.content_height - self.height))
                # 确保滚动位置在有效范围内
                self.scroll_pos = max(0, min(self.scroll_pos, max(0, self.content_height - self.height)))
            else:
                self.scroll_pos = 0
        
    def _update_slider_position(self):
        # 根据滚动位置更新滑块位置
        if self.content_height > self.height:
            self.slider_y = self.y + int(self.scroll_pos * (self.height - self.slider_height) / (self.content_height - self.height))
        else:
            self.slider_y = self.y
        
    def get_scroll_offset(self):
        return self.scroll_pos