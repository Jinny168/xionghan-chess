"""通用的设置界面分类绘制函数"""

import pygame


def draw_category(screen, category_background_color, category_border_color, category_padding,
                  category_title_height, category_title_font, checkbox_size, scroll_y,
                  window_width, option_font, desc_font, draw_piece_icon,
                  piece_display_char, piece_display_name, items, y_position=0):
    """
    通用的棋子分类绘制函数
    
    Args:
        screen: pygame屏幕对象
        category_background_color: 分类背景色
        category_border_color: 分类边框色
        category_padding: 分类内边距
        category_title_height: 分类标题高度
        category_title_font: 分类标题字体
        checkbox_size: 复选框大小
        scroll_y: 当前滚动位置
        window_width: 窗口宽度
        option_font: 选项字体
        desc_font: 描述字体
        draw_piece_icon: 绘制棋子图标的函数
        piece_display_char: 棋子显示字符
        piece_display_name: 棋子显示名称
        items: 选项列表，每个元素包含 (checkbox, label, value, text, desc, is_disabled)
        y_position: 分类在内容中的Y位置
    """
    # 计算分类区域的尺寸
    category_width = window_width - 100  # 留出边距
    items_count = len(items)  # 该分类下的设置项数量
    category_height = items_count * 60 + category_title_height + 2 * category_padding  # 包含标题高度和内边距
    
    # 绘制分类背景
    # 使用分类的实际位置减去滚动偏移来确定显示位置
    category_rect = pygame.Rect(50, y_position - scroll_y - category_padding, category_width, category_height)
    pygame.draw.rect(screen, category_background_color, category_rect)
    pygame.draw.rect(screen, category_border_color, category_rect, 2)
    
    # 绘制分类标题和图标 - 更紧密的组合
    title_y = y_position - scroll_y  # 考虑滚动偏移
    icon_x = 65
    icon_y = title_y + category_title_height // 2
    title_text_x = 90
    
    # 绘制图标
    draw_piece_icon(piece_display_char, icon_x, icon_y)
    # 绘制标题文字
    title_surface = category_title_font.render(piece_display_name, True, (0, 0, 0))
    screen.blit(title_surface, (title_text_x, title_y))
    
    # 在标题下方添加一条分割线，增强视觉分组
    separator_y = title_y + category_title_height - 2
    pygame.draw.line(screen, (180, 180, 180), (category_rect.left + 5, separator_y), 
                     (category_rect.right - 5, separator_y), 1)
    
    # 绘制分类内容
    item_y = title_y + category_title_height + category_padding
    
    for index, item in enumerate(items):
        checkbox, label, value, text, desc, is_disabled = item
        
        # 绘制每项的背景框，形成更强的视觉分组
        item_rect = pygame.Rect(category_rect.left + 10, item_y - 5, category_rect.width - 20, 55)
        item_bg_color = (245, 245, 245) if is_disabled else (250, 250, 250)
        pygame.draw.rect(screen, item_bg_color, item_rect, border_radius=5)
        pygame.draw.rect(screen, (200, 200, 200), item_rect, 1, border_radius=5)
        
        # 计算复选框位置 - 确保复选框在背景框内
        checkbox_x = item_rect.left + 10  # 在背景框内留出一些边距
        checkbox_y = item_rect.top + (item_rect.height - checkbox_size) // 2  # 垂直居中
        adjusted_checkbox = pygame.Rect(
            checkbox_x,
            checkbox_y,
            checkbox_size,
            checkbox_size
        )
        
        if is_disabled:
            pygame.draw.rect(screen, (150, 150, 150), adjusted_checkbox, 2)  # 灰色边框
            if True:  # 对于禁用的复选框，使用固定的值（通常是True）
                pygame.draw.line(screen, (100, 100, 100),
                                 (adjusted_checkbox.left + 4, adjusted_checkbox.centery),
                                 (adjusted_checkbox.centerx - 2, adjusted_checkbox.bottom - 4), 2)
                pygame.draw.line(screen, (100, 100, 100),
                                 (adjusted_checkbox.centerx - 2, adjusted_checkbox.bottom - 4),
                                 (adjusted_checkbox.right - 4, adjusted_checkbox.top + 4), 2)
        else:
            pygame.draw.rect(screen, (0, 0, 0), adjusted_checkbox, 2)
            if value:
                pygame.draw.line(screen, (0, 0, 0),
                                 (adjusted_checkbox.left + 4, adjusted_checkbox.centery),
                                 (adjusted_checkbox.centerx - 2, adjusted_checkbox.bottom - 4), 2)
                pygame.draw.line(screen, (0, 0, 0),
                                 (adjusted_checkbox.centerx - 2, adjusted_checkbox.bottom - 4),
                                 (adjusted_checkbox.right - 4, adjusted_checkbox.top + 4), 2)
        
        # 绘制标签（主标题）
        # 标签位置基于复选框调整，确保在背景框内
        label_x = adjusted_checkbox.right + 5
        # 确保标签文本垂直居中对齐
        label_y = item_rect.top + (item_rect.height - option_font.get_height()) // 2
        label_color = (100, 100, 100) if is_disabled else (0, 0, 0)
        label_surface = option_font.render(text, True, label_color)
        screen.blit(label_surface, (label_x, label_y))
        
        # 绘制描述（辅助说明）
        desc_x = label_x
        desc_y = label_y + option_font.get_height() + 2
        # 确保描述不超出背景框范围
        if desc_y + desc_font.get_height() <= item_rect.bottom:
            desc_color = (150, 150, 150) if is_disabled else (100, 100, 100)
            desc_surface = desc_font.render(desc, True, desc_color)
            screen.blit(desc_surface, (desc_x, desc_y))
        
        # 添加一个小的连接线，表明复选框和标签的关联
        checkbox_right = adjusted_checkbox.right + 2
        label_left = label_x - 2
        line_start_y = label_y + label_surface.get_height() // 2
        line_end_y = line_start_y
        pygame.draw.line(screen, (200, 200, 200), (checkbox_right, line_start_y), (label_left, line_end_y), 1)
        
        item_y += 60
    
    return category_height