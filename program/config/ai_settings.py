"""
AI设置模块，处理AI算法选择等设置
"""
import pygame

from .config import game_config, BLACK


class AISettings:
    """AI设置类"""
    
    def __init__(self):
        # AI算法设置
        self.ai_algorithm = game_config.get_setting("ai_algorithm", "negamax")
        self.available_algorithms = ["negamax", "minimax", "alpha-beta"]
        
        # 算法选择复选框
        self.algorithm_checkboxes = {}
        for i, alg in enumerate(self.available_algorithms):
            self.algorithm_checkboxes[alg] = pygame.Rect(0, 0, 20, 20)  # 位置将在创建UI时设置
    
    def create_ai_items(self, y_offset):
        """创建AI设置项"""
        items = []
        
        # AI算法选择标题
        items.append((
            pygame.Rect(0, 0, 0, 0),  # 无复选框
            (0, y_offset),
            False,
            "AI算法选择",
            "",
            True  # 表示这是标题
        ))
        
        # 为每个算法创建单选按钮样式的选择
        for i, alg in enumerate(self.available_algorithms):
            y_pos = y_offset + (i + 1) * 30  # 每个选项间隔30像素
            checkbox_rect = pygame.Rect(0, y_pos, 20, 20)  # 位置将在绘制时更新
            items.append((
                checkbox_rect,
                (30, y_pos),  # 标签位置
                self.ai_algorithm == alg,  # 是否选中
                f"使用 {alg.upper()} 算法",
                f"选择{alg}算法进行AI对战",
                False  # 不是标题
            ))
        
        return items
    
    def handle_ai_settings_click(self, items, adjusted_mouse_pos, y_position):
        """处理AI设置点击事件"""
        item_y = y_position + 30  # 从第一个选项开始
        
        for i, alg in enumerate(self.available_algorithms):
            checkbox_x = 50  # 根据draw_category中的位置计算
            checkbox_y = item_y + (i * 30) - 5  # 调整垂直位置
            actual_checkbox = pygame.Rect(
                checkbox_x,
                checkbox_y,
                20, 
                20
            )
            
            # 检查鼠标是否点击了这个复选框
            if actual_checkbox.collidepoint(adjusted_mouse_pos):
                # 更新AI算法设置
                self.ai_algorithm = alg
                game_config.set_setting("ai_algorithm", alg)
                return True  # 表示已处理点击
        
        return False  # 未处理点击
    
    def draw_ai_settings(self, screen, scroll_y, window_width, option_font, desc_font, y_offset):
        """绘制AI设置"""
        # AI算法选择标题
        title_surface = option_font.render("AI算法选择", True, BLACK)
        screen.blit(title_surface, (60, y_offset - scroll_y))
        
        # 绘制算法选项
        for i, alg in enumerate(self.available_algorithms):
            y_pos = y_offset + (i + 1) * 30 - scroll_y
            is_selected = self.ai_algorithm == alg
            
            # 绘制单选按钮样式的圆圈
            radio_x = 50
            radio_y = y_pos + 10
            pygame.draw.circle(screen, BLACK, (radio_x, radio_y), 10, 2)  # 圆圈边框
            
            # 如果选中，填充圆圈
            if is_selected:
                pygame.draw.circle(screen, BLACK, (radio_x, radio_y), 6)  # 填充圆
            
            # 绘制标签
            label_surface = option_font.render(f"使用 {alg.upper()} 算法", True, BLACK)
            screen.blit(label_surface, (70, y_pos))
            
            # 绘制描述
            desc_surface = desc_font.render(f"选择{alg}算法进行AI对战", True, (100, 100, 100))
            screen.blit(desc_surface, (70, y_pos + 20))