import sys

import pygame

from program.config.config import (
    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT,
    BLACK, GOLD, CAMP_RED, CAMP_BLACK, FPS
)
from program.controllers.sound_manager import sound_manager
from program.ui.button import StyledButton
from program.utils import tools
from program.utils.utils import load_font, draw_background


class CampSelectionScreen:
    """阵营选择界面，让玩家选择执红方还是黑方"""

    def __init__(self):
        # 初始化窗口尺寸和模式
        self.window_width = DEFAULT_WINDOW_WIDTH
        self.window_height = DEFAULT_WINDOW_HEIGHT
        self.is_fullscreen = False
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("匈汉象棋 - 选择阵营")

        # 使用全局声音管理器
        self.sound_manager = sound_manager

        self.update_layout()
        self.selected_camp = None

    def update_layout(self):
        """根据当前窗口尺寸更新布局"""
        button_width = 160  # 进一步缩小按钮
        button_height = 40
        button_spacing = 20
        center_x = self.window_width // 2
        center_y = self.window_height // 2

        # 创建按钮
        self.red_button = StyledButton(
            center_x - button_width // 2,
            center_y - button_height - button_spacing // 2,
            button_width,
            button_height,
            "执红先行",
            20,  # 进一步缩小字体
            12  # 增加圆角
        )

        self.black_button = StyledButton(
            center_x - button_width // 2,
            center_y + button_spacing // 2,
            button_width,
            button_height,
            "执黑后行",
            20,  # 进一步缩小字体
            12  # 增加圆角
        )

        # 添加返回按钮
        back_button_width = 80
        back_button_height = 35
        self.back_button = StyledButton(
            20,  # 左上角位置
            20,  # 左上角位置
            back_button_width,
            back_button_height,
            "返回",
            16,  # 字体大小
            10  # 增加圆角
        )

    def toggle_fullscreen(self):
        """切换全屏模式"""
        # 使用通用的全屏切换函数
        self.screen, self.window_width, self.window_height, self.is_fullscreen, self.windowed_size = \
            tools.toggle_fullscreen(self.screen, self.window_width, self.window_height, self.is_fullscreen,
                                    self.windowed_size)

        # 更新布局
        self.update_layout()

    def handle_resize(self, new_size):
        """处理窗口大小变化"""
        self.window_width, self.window_height = new_size
        # 更新布局
        self.update_layout()

    def run(self):
        """运行阵营选择界面"""
        clock = pygame.time.Clock()

        while self.selected_camp is None:
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                # 处理窗口大小变化
                if event.type == pygame.VIDEORESIZE:
                    if not self.is_fullscreen:  # 只在窗口模式下处理大小变化
                        self.handle_resize((event.w, event.h))

                # 处理键盘事件
                if event.type == pygame.KEYDOWN:
                    # F11或Alt+Enter切换全屏
                    if event.key == pygame.K_F11 or (
                            event.key == pygame.K_RETURN and
                            pygame.key.get_mods() & pygame.KMOD_ALT
                    ):
                        self.toggle_fullscreen()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.red_button.is_clicked(mouse_pos, event):
                        self.sound_manager.play_sound('button')  # 播放按钮音效
                        self.selected_camp = CAMP_RED
                    elif self.black_button.is_clicked(mouse_pos, event):
                        self.sound_manager.play_sound('button')  # 播放按钮音效
                        self.selected_camp = CAMP_BLACK
                    elif self.back_button.is_clicked(mouse_pos, event):
                        self.sound_manager.play_sound('button')  # 播放按钮音效
                        # 返回到上一级界面（模式选择界面）
                        return None  # 返回None表示返回上级界面

            # 更新按钮悬停状态
            self.red_button.check_hover(mouse_pos)
            self.black_button.check_hover(mouse_pos)
            self.back_button.check_hover(mouse_pos)

            # 绘制界面
            self.draw()
            pygame.display.flip()
            clock.tick(FPS)

        return self.selected_camp

    def draw(self):
        """绘制选择界面"""
        # 使用统一的背景绘制函数
        draw_background(self.screen)

        # 绘制标题
        title_font = load_font(40)  # 缩小标题字体
        title_text = "选择您的阵营"
        title_surface = title_font.render(title_text, True, BLACK)
        title_rect = title_surface.get_rect(center=(self.window_width // 2, 100))  # 上移标题
        self.screen.blit(title_surface, title_rect)

        # 绘制提示文字
        hint_font = load_font(18)  # 缩小提示文字
        hint_text = "在匈汉象棋中，红方先行"
        hint_surface = hint_font.render(hint_text, True, BLACK)
        hint_rect = hint_surface.get_rect(center=(self.window_width // 2, 140))  # 调整位置
        self.screen.blit(hint_surface, hint_rect)

        # 绘制金色装饰线
        line_y = title_rect.bottom + 20  # 调整线条位置
        pygame.draw.line(
            self.screen,
            GOLD,
            (self.window_width // 4, line_y),
            (self.window_width * 3 // 4, line_y),
            3
        )

        # 绘制按钮
        self.red_button.draw(self.screen)
        self.black_button.draw(self.screen)
        self.back_button.draw(self.screen)  # 绘制返回按钮
