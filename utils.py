import os
import pygame


def load_font(size, bold=False):
    """尝试加载本地字体文件，如果失败则使用默认字体"""
    font_paths = [
        'fonts/simkai.ttf',      # 楷体
        'fonts/kaiti.ttf',       # 楷体
        'fonts/fangsong.ttf',    # 仿宋
        'fonts/simhei.ttf',      # 黑体
        'fonts/xingkai.ttf',     # 行楷
        'fonts/msyh.ttc',        # 微软雅黑
    ]
    
    # 尝试加载游戏资源中的字体文件
    for font_path in font_paths:
        full_path = os.path.join(os.path.dirname(__file__), font_path)
        if os.path.exists(full_path):
            try:
                font = pygame.font.Font(full_path, size)
                if bold and hasattr(font, 'bold'):
                    font.bold = True
                return font
            except:
                continue
    
    # 如果没有找到资源字体，使用默认字体
    # 作为最后的备选方案，尝试直接使用本地字体文件
    try:
        return pygame.font.Font('fonts/simhei.ttf', size)
    except:
        try:
            return pygame.font.Font('fonts/simkai.ttf', size)
        except:
            try:
                return pygame.font.Font('fonts/fangsong.ttf', size)
            except:
                # 如果所有本地字体都加载失败，返回None表示失败
                return None