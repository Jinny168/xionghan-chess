"""匈汉象棋关于界面"""

import pygame
from program.utils.utils import load_font, draw_background
from program.ui.button import Button


class AboutScreen:
    """关于界面，显示游戏和作者信息，支持分页显示"""
    
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
        
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("匈汉象棋 - 关于")
        
        # 字体
        self.title_font = load_font(28, bold=True)
        self.subtitle_font = load_font(24, bold=True)
        self.text_font = load_font(18)
        self.small_font = load_font(16)
        
        # 读取about.md内容并分割成页面
        self.pages = self._parse_about_file()
        
        # 当前页面索引
        self.current_page = 0
        
        # 创建导航按钮
        self._create_navigation_buttons()
        
        # 页面信息
        self.page_info = self.small_font.render(
            f"{self.current_page + 1}/{len(self.pages)}", True, (0, 0, 0)
        )
    
    def _parse_about_file(self):
        """解析about.md文件，按章节分割成页面"""
        try:
            import os
            about_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "about.md")
            with open(about_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"读取 about.md 文件时出错: {e}")
            # 如果出现错误，使用默认内容
            content = """# 匈汉象棋 (XiongHan Chess)

## 游戏简介
匈汉象棋是一款融合中国传统象棋与匈牙利文化元素的创新棋类游戏。

## 开发者信息
开发者: 靳中原

## 游戏特色
• 融合中国传统象棋与匈牙利文化元素
• 支持双人对战和人机对战
• 拥有美观的界面和智能AI
• 包含多种特色棋子和创新规则

## 技术特点
• 使用Python和Pygame开发
• 支持多种游戏模式
• 具备现代化UI界面
• 内置传统AI和MCTS AI

# 版本信息

## 当前版本
v1.0.0

## 更新日志
• 实现基础游戏逻辑
• 添加双人对战模式
• 集成人机对战AI
• 设计美观的用户界面

# 致谢

## 开源技术
• Python编程语言
• Pygame游戏库
• 开源字体资源

## 支持者
感谢所有参与测试和提供反馈的用户
"""
        
        # 按行分割内容
        lines = content.strip().split('\n')
        
        # 分割成页面，以##或#为章节分隔符
        pages = []
        current_page = []
        
        for line in lines:
            if line.startswith('# ') or line.startswith('## '):
                # 如果当前页不为空，先保存当前页
                if current_page:
                    pages.append(current_page[:])
                # 开始新的页面，包含当前标题
                current_page = [line]
            else:
                # 非标题行添加到当前页
                current_page.append(line)
        
        # 添加最后一页
        if current_page:
            pages.append(current_page)
        
        # 将每页的行转换为渲染过的表面
        rendered_pages = []
        for page in pages:
            rendered_page = []
            for line in page:
                if line.startswith('# '):
                    # 主标题
                    surface = self.title_font.render(line[2:], True, (0, 0, 0))
                    rendered_page.append(('title', surface))
                elif line.startswith('## '):
                    # 副标题
                    surface = self.subtitle_font.render(line[3:], True, (0, 0, 0))
                    rendered_page.append(('subtitle', surface))
                elif line.startswith('- ') or line.startswith('• '):
                    # 列表项
                    surface = self.text_font.render(line, True, (0, 0, 0))
                    rendered_page.append(('list', surface))
                elif line.strip() == '':
                    # 空行
                    surface = self.text_font.render(' ', True, (0, 0, 0))
                    rendered_page.append(('empty', surface))
                else:
                    # 普通文本
                    surface = self.text_font.render(line, True, (0, 0, 0))
                    rendered_page.append(('text', surface))
            rendered_pages.append(rendered_page)
        
        return rendered_pages
    
    def _create_navigation_buttons(self):
        """创建导航按钮"""
        button_width = 100
        button_height = 40
        margin = 20
        
        # 上一页按钮
        self.prev_button = Button(
            margin,
            self.window_height - button_height - margin,
            button_width,
            button_height,
            "上一页",
            18
        )
        
        # 下一页按钮
        self.next_button = Button(
            self.window_width - button_width - margin,
            self.window_height - button_height - margin,
            button_width,
            button_height,
            "下一页",
            18
        )
        
        # 返回按钮
        self.back_button = Button(
            self.window_width // 2 - 50,
            self.window_height - button_height - margin,
            100,
            button_height,
            "返回",
            18
        )
    
    def handle_event(self, event, mouse_pos):
        """处理事件"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.prev_button.is_clicked(mouse_pos, event) and self.current_page > 0:
                self.current_page -= 1
                self._update_page_info()
                self._create_navigation_buttons()  # 重新创建按钮以适应可能的窗口大小变化
                return "prev"
            elif self.next_button.is_clicked(mouse_pos, event) and self.current_page < len(self.pages) - 1:
                self.current_page += 1
                self._update_page_info()
                self._create_navigation_buttons()  # 重新创建按钮以适应可能的窗口大小变化
                return "next"
            elif self.back_button.is_clicked(mouse_pos, event):
                return "back"
        
        # 键盘事件
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT and self.current_page > 0:
                self.current_page -= 1
                self._update_page_info()
                self._create_navigation_buttons()
                return "prev"
            elif event.key == pygame.K_RIGHT and self.current_page < len(self.pages) - 1:
                self.current_page += 1
                self._update_page_info()
                self._create_navigation_buttons()
                return "next"
            elif event.key == pygame.K_ESCAPE:
                return "back"
        
        return None
    
    def _update_page_info(self):
        """更新页面信息文本"""
        self.page_info = self.small_font.render(
            f"{self.current_page + 1}/{len(self.pages)}", True, (0, 0, 0)
        )
    
    def draw(self, screen):
        """绘制关于页面"""
        # 绘制背景
        draw_background(screen)
        
        # 绘制标题
        title = self.title_font.render("关于 匈汉象棋", True, (0, 0, 0))
        title_rect = title.get_rect(center=(self.window_width // 2, 60))
        screen.blit(title, title_rect)
        
        # 绘制装饰线
        pygame.draw.line(screen, (218, 165, 32), 
                        (self.window_width // 4, 100), 
                        (self.window_width * 3 // 4, 100), 3)
        
        # 获取当前页内容
        current_page_content = self.pages[self.current_page]
        
        # 绘制页面内容
        y_pos = 130  # 起始Y位置
        line_height = 30  # 行高
        
        for item_type, surface in current_page_content:
            if item_type == 'title':
                # 主标题使用更大的行高
                y_pos += 10
                screen.blit(surface, (50, y_pos))
                y_pos += line_height + 15
            elif item_type == 'subtitle':
                # 副标题
                y_pos += 10
                screen.blit(surface, (60, y_pos))
                y_pos += line_height + 10
            elif item_type == 'list':
                # 列表项
                screen.blit(surface, (80, y_pos))
                y_pos += line_height + 5
            elif item_type == 'empty':
                # 空行
                y_pos += line_height // 2
            else:
                # 普通文本
                screen.blit(surface, (70, y_pos))
                y_pos += line_height + 3
        
        # 绘制页面信息
        page_info_rect = self.page_info.get_rect(
            center=(self.window_width // 2, self.window_height - 60)
        )
        screen.blit(self.page_info, page_info_rect)
        
        # 更新按钮状态并绘制
        mouse_pos = pygame.mouse.get_pos()
        self.prev_button.check_hover(mouse_pos)
        self.next_button.check_hover(mouse_pos)
        self.back_button.check_hover(mouse_pos)
        
        # 根据当前页调整按钮可用性
        if self.current_page == 0:
            self.prev_button.enabled = False
        else:
            self.prev_button.enabled = True
            
        if self.current_page == len(self.pages) - 1:
            self.next_button.enabled = False
        else:
            self.next_button.enabled = True
        
        self.prev_button.draw(screen)
        self.next_button.draw(screen)
        self.back_button.draw(screen)
    
    def run(self):
        """运行关于界面"""
        clock = pygame.time.Clock()
        
        running = True
        while running:
            mouse_pos = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                # 处理窗口大小变化
                if event.type == pygame.VIDEORESIZE:
                    self.window_width, self.window_height = event.w, event.h
                    self.screen = pygame.display.set_mode(
                        (self.window_width, self.window_height), pygame.RESIZABLE
                    )
                    self._create_navigation_buttons()
                
                result = self.handle_event(event, mouse_pos)
                if result == "back":
                    running = False
            
            # 绘制界面
            self.draw(self.screen)
            pygame.display.flip()
            clock.tick(60)
        
        return "back"
    
    def update_size(self, new_width, new_height):
        """更新窗口尺寸"""
        self.window_width = new_width
        self.window_height = new_height
        
        # 更新导航按钮
        self._create_navigation_buttons()