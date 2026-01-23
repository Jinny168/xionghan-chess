"""匈汉象棋游戏规则查看器 - 支持翻页功能"""

import pygame
from program.utils.utils import load_font, draw_background
from program.ui.button import Button


class RulesScreen:
    """游戏规则查看器，支持分页显示和翻页功能"""
    
    def __init__(self):
        # 获取当前屏幕尺寸
        info = pygame.display.Info()
        self.window_width = info.current_w if info.current_w <= 1200 else 1200
        self.window_height = info.current_h if info.current_h <= 900 else 900
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("匈汉象棋 - 游戏规则")
        
        # 字体
        self.title_font = load_font(28, bold=True)
        self.subtitle_font = load_font(24, bold=True)
        self.text_font = load_font(18)
        self.small_font = load_font(16)
        
        # 读取help.md文件内容并分割成页面
        self.pages = self._parse_help_file()
        
        # 当前页面索引
        self.current_page = 0
        
        # 创建导航按钮
        self._create_navigation_buttons()
        
        # 页面信息
        self.page_info = self.small_font.render(
            f"{self.current_page + 1}/{len(self.pages)}", True, (0, 0, 0)
        )
        
    def _parse_help_file(self):
        """解析help.md文件，按章节分割成页面"""
        # 使用绝对路径从当前文件所在的目录开始查找
        import os
        help_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "help.md")
        try:
            with open(help_file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            print(f"警告: 无法找到 help.md 文件于 {help_file_path}")
            # 如果文件不存在，使用默认内容
            content = """## 匈汉象棋游戏帮助

- 游戏简介：匈汉象棋是一种融合了中国传统象棋元素的创新棋类游戏，具有独特的棋盘布局和棋子规则。

- 棋盘与棋子：匈汉象棋使用13×13的方形格状棋盘，圆形棋子共有32个或更多。棋子分为红、黑两组，每组包括传统中国象棋的车、马、相、士、将/帅、炮、兵/卒，以及匈汉象棋特有的特色棋子。

### 传统棋子

- **汉/汗**：相当于传统中国象棋的将/帅，只能在"九宫"之内活动。
- **仕/士**：只能在九宫内走动，行棋路径只能是九宫内的斜线。
- **相/象**：走法是每次循对角线走两格，俗称"象飞田"。
- **俥/车**：威力最大，无论横线、竖线均可行走，步数不受限制。
- **炮/砲**：在不吃子的时候，走动与车完全相同，但吃子时，必须跳过一个棋子。
- **傌/马**：走动方法是一直一斜，即先横着或直着走一格，然后再斜着走一个对角线，俗称"马走日"。
- **兵/卒**：只能向前走，不能后退，在未过河前，不能横走。

### 特色棋子

- **射/䠶**：斜向移动至无碰撞点位，移动距离限制为至多斜向移动3格。
- **檑/礌**：移动规则类似国际象棋的皇后，但攻击规则特殊。
- **尉/衛**：可以跨越棋子移动，类似于跳棋中的跳跃规则。
- **甲/胄**：拥有特殊的"三子连线吃子"能力。
- **刺（拖吃者）**：具有兑子能力。
- **盾**：能够保护邻近的己方棋子。
- **巡/廵**：河界专属控场棋子。

## 游戏规则

### 基本行棋规定
- 对局时，双方轮流走一步。
- 轮到走棋的一方，将某个棋子从一个交叉点走到另一个交叉点。
- 双方各走一着，称为一个回合。

### 胜负判定
出现下列情况之一，本方算输，对方赢：
- 己方的汉/汗被对方棋子将死或吃掉
- 己方无子可走（被困毙）
- 对方汉/汗先进入己方九宫

### 和棋判定
出现下列情况之一，算和棋：
- 双方均无可能取胜的简单局势
- 双方走棋出现循环反复三次
- 任何导致无法继续进行下去的棋局状况

## 游戏模式说明

游戏提供了多种模式供玩家选择：

- **双人模式**：两个玩家在同一台设备上对局
- **人机模式**：玩家和电脑对局
- **经典模式**：使用接近传统中国象棋的布局
- **完整模式**：包含所有特色棋子和特殊规则
- **网络对战**：支持局域网联机对战

## 策略提示

- 有效利用特色棋子的独特能力
- 注意保护自己的重要棋子
- 灵活运用各种棋子的移动特性
- 观察棋盘局势，合理规划棋子的布局
"""
        except Exception as e:
            print(f"读取 help.md 文件时出错: {e}")
            # 如果出现其他错误，也使用默认内容
            content = """## 匈汉象棋游戏帮助

- 游戏简介：匈汉象棋是一种融合了中国传统象棋元素的创新棋类游戏，具有独特的棋盘布局和棋子规则。

- 棋盘与棋子：匈汉象棋使用13×13的方形格状棋盘，圆形棋子共有32个或更多。棋子分为红、黑两组，每组包括传统中国象棋的车、马、相、士、将/帅、炮、兵/卒，以及匈汉象棋特有的特色棋子。

### 传统棋子

- **汉/汗**：相当于传统中国象棋的将/帅，只能在"九宫"之内活动。
- **仕/士**：只能在九宫内走动，行棋路径只能是九宫内的斜线。
- **相/象**：走法是每次循对角线走两格，俗称"象飞田"。
- **俥/车**：威力最大，无论横线、竖线均可行走，步数不受限制。
- **炮/砲**：在不吃子的时候，走动与车完全相同，但吃子时，必须跳过一个棋子。
- **傌/马**：走动方法是一直一斜，即先横着或直着走一格，然后再斜着走一个对角线，俗称"马走日"。
- **兵/卒**：只能向前走，不能后退，在未过河前，不能横走。

### 特色棋子

- **射/䠶**：斜向移动至无碰撞点位，移动距离限制为至多斜向移动3格。
- **檑/礌**：移动规则类似国际象棋的皇后，但攻击规则特殊。
- **尉/衛**：可以跨越棋子移动，类似于跳棋中的跳跃规则。
- **甲/胄**：拥有特殊的"三子连线吃子"能力。
- **刺（拖吃者）**：具有兑子能力。
- **盾**：能够保护邻近的己方棋子。
- **巡/廵**：河界专属控场棋子。

## 游戏规则

### 基本行棋规定
- 对局时，双方轮流走一步。
- 轮到走棋的一方，将某个棋子从一个交叉点走到另一个交叉点。
- 双方各走一着，称为一个回合。

### 胜负判定
出现下列情况之一，本方算输，对方赢：
- 己方的汉/汗被对方棋子将死或吃掉
- 己方无子可走（被困毙）
- 对方汉/汗先进入己方九宫

### 和棋判定
出现下列情况之一，算和棋：
- 双方均无可能取胜的简单局势
- 双方走棋出现循环反复三次
- 任何导致无法继续进行下去的棋局状况

## 游戏模式说明

游戏提供了多种模式供玩家选择：

- **双人模式**：两个玩家在同一台设备上对局
- **人机模式**：玩家和电脑对局
- **经典模式**：使用接近传统中国象棋的布局
- **完整模式**：包含所有特色棋子和特殊规则
- **网络对战**：支持局域网联机对战

## 策略提示

- 有效利用特色棋子的独特能力
- 注意保护自己的重要棋子
- 灵活运用各种棋子的移动特性
- 观察棋盘局势，合理规划棋子的布局
"""
        
        # 按行分割内容
        lines = content.strip().split('\n')
        
        # 分割成页面，以##为章节分隔符
        pages = []
        current_page = []
        
        for line in lines:
            if line.startswith('## ') or line.startswith('# '):
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
                elif line.startswith('- '):
                    # 列表项
                    surface = self.text_font.render(line, True, (0, 0, 0))
                    rendered_page.append(('list', surface))
                elif line.startswith('### '):
                    # 三级标题
                    surface = self.text_font.render(line[4:], True, (0, 0, 0))
                    rendered_page.append(('subsubtitle', surface))
                elif line.strip() == '' or line.strip() == ' ':
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
        """绘制规则页面"""
        # 绘制背景
        draw_background(screen)
        
        # 绘制标题
        title = self.title_font.render("游戏规则", True, (0, 0, 0))
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
            elif item_type == 'subsubtitle':
                # 三级标题
                y_pos += 5
                screen.blit(surface, (70, y_pos))
                y_pos += line_height + 5
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
        """运行规则查看器"""
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