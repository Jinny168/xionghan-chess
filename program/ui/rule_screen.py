import pygame

from program.config.config import (
    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT,
    BLACK, FPS
)
from program.controllers.sound_manager import sound_manager
from program.ui.network_mode_screen import StyledButton
from program.utils import tools
from program.utils.utils import load_font, draw_background


class RulesScreen:
    def __init__(self):
        self.windowed_size = None
        self.window_width = DEFAULT_WINDOW_WIDTH
        self.window_height = DEFAULT_WINDOW_HEIGHT
        self.is_fullscreen = False
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("匈汉象棋 - 游戏规则")

        # 使用全局声音管理器
        self.sound_manager = sound_manager

        # 规则文本
        self.rules_text = [
            "匈汉象棋游戏规则：",
            "",
            "1. 棋盘：13x13格棋盘，中间为长城阴山区域",
            "2. 棋子：包括汉/汗(王)、仕(士)、相(象)、马、车、炮、兵(卒)、",
            "      尉(衛)、射(䠶)、檑(礌)、甲(胄)、刺(拖吃者)、盾",
            "",
            "各棋子走法：",
            "- 将(汉/汗)：在九宫内移动，可横竖斜走，出九宫后失去斜走能力",
            "- 仕(士)：在九宫内斜走，出九宫后增加直走能力",
            "- 相(象)：走田字，无塞象眼限制，可过河，过河后增加横竖两格跳跃能力",
            "- 马：走日字，可走直线(直三走法)",
            "- 车：横竖直线移动，无距离限制",
            "- 炮：移动同车，吃子需隔一子",
            "- 兵(卒)：未过河只能前进，过河后可横移",
            "- 尉(衛)：跳跃过棋子后在碰撞前的区间内移动，与其照面的敌方棋子禁止移动和攻击",
            "- 射(䠶)：斜向移动，最多移动3格，不可越子",
            "- 檑(礌)：可攻击周围落单的敌方棋子，落单即不与同色棋子横竖相连",
            "- 甲(胄)：移动同车，落子后形成2己1敌三子连线吃敌子",
            "- 刺(拖吃者)：只能直走，移动路径上必须完全无阻挡，目标位置必须为空，",
            "            当移动前起始位置的反方向一格有敌棋时，可兑掉那个敌棋",
            "- 盾：只能直线跨越移动(移动规则同尉)，不可被吃，与盾相连的敌方棋子",
            "      禁止执行吃子操作",
            "",
            "特殊规则：",
            "- 汉/汗进入敌方九宫直接获胜",
            "",
            "胜负判定：",
            "- 将死对方将/帅",
            "- 汉/汗进入敌方九宫",
            "- 对方将/帅被照面(违规)"
        ]

        # 滚动参数
        self.scroll_y = 0
        self.scroll_speed = 20

        # 预渲染规则文本以提高性能
        self.rendered_lines = []
        text_font = load_font(24)
        for line in self.rules_text:
            text_surface = text_font.render(line, True, BLACK)
            self.rendered_lines.append(text_surface)

        # 返回按钮
        button_width = 100
        button_height = 35
        self.back_button = StyledButton(  # 使用StyledButton替代Button
            self.window_width - button_width - 20,
            20,
            button_width,
            button_height,
            "返回",
            18,
            8  # 圆角
        )

    def run(self):
        """运行规则界面"""
        clock = pygame.time.Clock()

        running = True
        while running:
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

                # 处理窗口大小变化
                if event.type == pygame.VIDEORESIZE:
                    if not self.is_fullscreen:  # 只在窗口模式下处理大小变化
                        self.window_width, self.window_height = event.w, event.h
                        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
                        # 更新返回按钮位置
                        self.back_button = StyledButton(
                            self.window_width - 100 - 20,
                            20,
                            100,
                            35,
                            "返回",
                            18,
                            8  # 圆角
                        )

                # 处理键盘事件
                if event.type == pygame.KEYDOWN:
                    # F11或Alt+Enter切换全屏
                    if event.key == pygame.K_F11 or (
                            event.key == pygame.K_RETURN and
                            pygame.key.get_mods() & pygame.KMOD_ALT
                    ):
                        self.toggle_fullscreen()

                    # 滚动控制
                    if event.key == pygame.K_UP:
                        self.scroll_y = min(self.scroll_y + self.scroll_speed, 0)
                    elif event.key == pygame.K_DOWN:
                        self.scroll_y = max(self.scroll_y - self.scroll_speed,
                                            -(len(self.rules_text) * 30) + self.window_height - 100)

                # 处理鼠标滚轮
                if event.type == pygame.MOUSEWHEEL:
                    if event.y > 0:  # 向上滚动
                        self.scroll_y = min(self.scroll_y + self.scroll_speed, 0)
                    else:  # 向下滚动
                        self.scroll_y = max(self.scroll_y - self.scroll_speed,
                                            -(len(self.rules_text) * 30) + self.window_height - 100)

                # 处理鼠标点击
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.back_button.is_clicked(mouse_pos, event):
                        self.sound_manager.play_sound('button')  # 播放按钮音效
                        running = False

            # 更新按钮悬停状态
            self.back_button.check_hover(mouse_pos)

            # 绘制界面
            self.draw()
            pygame.display.flip()
            clock.tick(FPS)

    def draw(self):
        """绘制规则界面"""
        # 使用统一的背景绘制函数
        draw_background(self.screen)

        # 绘制标题
        title_font = load_font(48)
        title_text = "游戏规则"
        title_surface = title_font.render(title_text, True, BLACK)
        title_rect = title_surface.get_rect(center=(self.window_width // 2, 60))
        self.screen.blit(title_surface, title_rect)

        # 绘制规则文本（使用预渲染的文本）
        y_pos = 120 + self.scroll_y  # 添加滚动偏移

        # 只绘制可见范围内的文本行，提高性能
        line_height = 30
        start_line = max(0, -y_pos // line_height)
        end_line = min(len(self.rendered_lines), (self.window_height - 120 - y_pos + line_height) // line_height)

        for i in range(start_line, end_line):
            self.screen.blit(self.rendered_lines[i], (50, 120 + self.scroll_y + i * line_height))

        # 绘制返回按钮
        self.back_button.draw(self.screen)

    def toggle_fullscreen(self):
        """切换全屏模式"""
        # 使用通用的全屏切换函数
        self.screen, self.window_width, self.window_height, self.is_fullscreen, self.windowed_size = \
            tools.toggle_fullscreen(self.screen, self.window_width, self.window_height, self.is_fullscreen,
                                    self.windowed_size)

        # 更新返回按钮位置
        button_width = 100
        button_height = 35
        self.back_button = StyledButton(
            self.window_width - button_width - 20,
            20,
            button_width,
            button_height,
            "返回",
            18,
            8  # 圆角
        )
