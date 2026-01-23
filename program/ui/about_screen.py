"""匈汉象棋关于界面"""

import pygame
from program.utils.utils import load_font, draw_background
from program.ui.button import Button


class AboutScreen:
    """关于界面，显示游戏和作者信息"""
    
    def __init__(self, window_width=None, window_height=None):
        # 如果提供了窗口尺寸，使用提供的尺寸；否则获取当前屏幕尺寸
        if window_width and window_height:
            self.window_width = window_width
            self.window_height = window_height
        else:
            # 获取当前屏幕尺寸
            info = pygame.display.Info()
            self.window_width = min(info.current_w, 800)  # 设置较小的窗口宽度
            self.window_height = min(info.current_h, 600)  # 设置较小的窗口高度
        
        # 字体
        self.title_font = load_font(28, bold=True)
        self.subtitle_font = load_font(24, bold=True)
        self.text_font = load_font(18)
        self.small_font = load_font(16)
        
        # 从about.md读取关于内容
        self.content = self._load_about_content()
        
        # 返回按钮
        button_width = 100
        button_height = 40
        margin = 20
        self.back_button = Button(
            self.window_width // 2 - button_width // 2,
            self.window_height - button_height - margin,
            button_width,
            button_height,
            "返回",
            18
        )
    
    def _load_about_content(self):
        """从about.md加载关于内容"""
        try:
            import os
            about_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "about.md")
            with open(about_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 解析about.md内容
            lines = content.split('\n')
            about_content = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('# '):  # 主标题
                    about_content.append(("title", line[2:]))  # 去掉 '# ' 前缀
                elif line.startswith('## '):  # 副标题
                    about_content.append(("subtitle", line[3:]))  # 去掉 '## ' 前缀
                elif line.startswith('- '):  # 列表项
                    # 去掉 '- ' 前缀并去除markdown格式符号
                    clean_line = line[2:].replace('*', '').replace('_', '').strip()
                    about_content.append(("text", clean_line))
                elif line.startswith('• '):  # 特色列表
                    about_content.append(("text", line))
                elif line and not line.startswith('#'):  # 普通文本行
                    # 去除markdown格式符号
                    clean_line = line.replace('*', '').replace('_', '').strip()
                    if clean_line:  # 只添加非空行
                        about_content.append(("text", clean_line))
            
            return about_content
        except Exception as e:
            # 如果读取文件失败，使用默认内容
            return [
                ("title", "匈汉象棋 (XiongHan Chess)"),
                ("text", ""),
                ("subtitle", "游戏简介"),
                ("text", "匈汉象棋是一款融合中国传统象棋与匈牙利文化元素的创新棋类游戏。"),
                ("text", ""),
                ("subtitle", "开发者信息"),
                ("text", "开发者: 靳中原"),
                ("text", ""),
                ("subtitle", "游戏特色"),
                ("text", "• 融合中国传统象棋与匈牙利文化元素"),
                ("text", "• 支持双人对战和人机对战"),
                ("text", "• 拥有美观的界面和智能AI"),
                ("text", "• 包含多种特色棋子和创新规则")
            ]
    
    def handle_event(self, event, mouse_pos):
        """处理事件"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.back_button.is_clicked(mouse_pos, event):
                return "back"
        
        # 键盘事件
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "back"
        
        return None
    
    def draw(self, screen):
        """绘制关于界面"""
        # 绘制背景
        draw_background(screen)
        
        # 绘制标题
        title = self.title_font.render("关于 匈汉象棋", True, (0, 0, 0))
        title_rect = title.get_rect(center=(self.window_width // 2, 50))
        screen.blit(title, title_rect)
        
        # 绘制装饰线
        pygame.draw.line(screen, (218, 165, 32), 
                        (self.window_width // 4, 90), 
                        (self.window_width * 3 // 4, 90), 3)
        
        # 绘制内容
        y_pos = 120  # 起始Y位置
        line_height = 28  # 行高
        
        for item_type, content in self.content:
            if item_type == 'title':
                # 主标题
                surface = self.title_font.render(content, True, (0, 0, 0))
                screen.blit(surface, (self.window_width // 2 - surface.get_width() // 2, y_pos))
                y_pos += line_height + 10
            elif item_type == 'subtitle':
                # 副标题
                surface = self.subtitle_font.render(content, True, (0, 0, 0))
                screen.blit(surface, (50, y_pos))
                y_pos += line_height + 8
            else:  # text
                # 普通文本
                surface = self.text_font.render(content, True, (0, 0, 0))
                if content.strip() == "":  # 空行
                    y_pos += line_height // 2
                else:
                    screen.blit(surface, (70, y_pos))
                    y_pos += line_height + 5
        
        # 更新按钮状态并绘制
        mouse_pos = pygame.mouse.get_pos()
        self.back_button.check_hover(mouse_pos)
        self.back_button.draw(screen)
    
    def run(self):
        """运行关于界面"""
        # 注意：这里我们不再创建新的窗口，而是假设在当前屏幕上显示
        # 这个方法只是作为兼容性保留，实际调用draw方法即可
        return "back"
    
    def update_size(self, new_width, new_height):
        """更新窗口尺寸"""
        self.window_width = new_width
        self.window_height = new_height
        
        # 更新返回按钮位置
        button_width = 100
        button_height = 40
        margin = 20
        self.back_button = Button(
            self.window_width // 2 - button_width // 2,
            self.window_height - button_height - margin,
            button_width,
            button_height,
            "返回",
            18
        )