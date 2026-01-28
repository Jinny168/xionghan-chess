import sys

import pygame

from program.controllers.game_config_manager import (
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
        self.black_button = None
        self.red_button = None
        self.back_button = None
        self.window_width = DEFAULT_WINDOW_WIDTH
        self.window_height = DEFAULT_WINDOW_HEIGHT
        self.is_fullscreen = False
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("匈汉象棋 - 选择阵营")

        # 使用全局声音管理器
        self.sound_manager = sound_manager

        # 添加阵营选择滚动框
        self.camp_options = ["执红先行", "执黑后行"]
        self.current_camp_index = 0  # 默认选择执红先行

        # 添加AI难度选择滚动框
        self.ai_difficulty_options = [
            {"name": "菜鸟", "algorithm": "minimax", "desc": "Minimax搜索算法"},
            {"name": "入门", "algorithm": "negamax", "desc": "Negamax搜索算法"},
            {"name": "专家", "algorithm": "alpha-beta", "desc": "Alpha-Beta剪枝算法"},
            {"name": "大师", "algorithm": "mcts", "desc": "MCTS+神经网络算法"}
        ]
        self.current_ai_index = 0  # 默认选择菜鸟

        # 添加左右箭头按钮
        self.left_arrow_button = None
        self.right_arrow_button = None
        self.ai_left_arrow_button = None
        self.ai_right_arrow_button = None

        # 添加确认按钮
        self.confirm_button = None

        self.update_layout()
        self.selected_camp = None
        self.selected_ai_difficulty = None

    def update_layout(self):
        """根据当前窗口尺寸更新布局"""
        # 按钮尺寸
        button_width = 40
        button_height = 60
        arrow_button_width = 50
        arrow_button_height = 50
        confirm_button_width = 120
        confirm_button_height = 40

        center_x = self.window_width // 2
        center_y = self.window_height // 2

        # 计算阵营选择箭头位置 - 基于文本中心对齐
        current_camp = self.camp_options[self.current_camp_index]
        from program.utils.utils import load_font
        camp_font = load_font(32, bold=True)
        camp_text = camp_font.render(current_camp, True, GOLD)
        camp_text_x = center_x - camp_text.get_width() // 2
        camp_text_y = 250  # 文字绘制的Y位置
        camp_arrow_y = camp_text_y + (camp_text.get_height() // 2) - (arrow_button_height // 2)  # 箭头按钮Y位置，垂直居中文本
        
        # 左箭头在文本左边，右箭头在文本右边
        left_arrow_x = camp_text_x - arrow_button_width - 10  # 在文本左侧留出10像素间距
        right_arrow_x = camp_text_x + camp_text.get_width() + 10  # 在文本右侧留出10像素间距
        
        self.left_arrow_button = StyledButton(
            left_arrow_x,
            camp_arrow_y,
            arrow_button_width,
            arrow_button_height,
            "<",
            30,
            10
        )

        self.right_arrow_button = StyledButton(
            right_arrow_x,
            camp_arrow_y,
            arrow_button_width,
            arrow_button_height,
            ">",
            30,
            10
        )

        # 计算AI难度选择箭头位置 - 基于文本中心对齐
        current_ai = self.ai_difficulty_options[self.current_ai_index]
        ai_name_font = load_font(32, bold=True)
        ai_name_text = ai_name_font.render(current_ai["name"], True, GOLD)
        ai_text_x = center_x - ai_name_text.get_width() // 2
        ai_text_y = 390  # 文字绘制的Y位置
        ai_arrow_y = ai_text_y + (ai_name_text.get_height() // 2) - (arrow_button_height // 2)  # 箭头按钮Y位置，垂直居中文本
        
        # 左箭头在文本左边，右箭头在文本右边
        ai_left_arrow_x = ai_text_x - arrow_button_width - 10  # 在文本左侧留出10像素间距
        ai_right_arrow_x = ai_text_x + ai_name_text.get_width() + 10  # 在文本右侧留出10像素间距
        
        self.ai_left_arrow_button = StyledButton(
            ai_left_arrow_x,
            ai_arrow_y,
            arrow_button_width,
            arrow_button_height,
            "<",
            30,
            10
        )

        self.ai_right_arrow_button = StyledButton(
            ai_right_arrow_x,
            ai_arrow_y,
            arrow_button_width,
            arrow_button_height,
            ">",
            30,
            10
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

        # 添加确认按钮
        self.confirm_button = StyledButton(
            center_x - confirm_button_width // 2,
            center_y + 120,  # 确认按钮Y位置
            confirm_button_width,
            confirm_button_height,
            "确认选择",
            18,
            10
        )

    def toggle_fullscreen(self):
        """切换全屏模式"""
        # 使用通用的全屏切换函数
        self.screen, self.window_width, self.window_height, self.is_fullscreen, self.windowed_size = \
            tools.toggle_fullscreen(self.window_width, self.window_height, self.is_fullscreen,
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

        while self.selected_camp is None or self.selected_ai_difficulty is None:
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
                    # 阵营选择箭头按钮
                    if self.left_arrow_button.is_clicked(mouse_pos, event):
                        self.sound_manager.play_sound('button')  # 播放按钮音效
                        self.current_camp_index = (self.current_camp_index - 1) % len(self.camp_options)
                        self.update_layout()  # 更新布局以重新定位箭头
                    elif self.right_arrow_button.is_clicked(mouse_pos, event):
                        self.sound_manager.play_sound('button')  # 播放按钮音效
                        self.current_camp_index = (self.current_camp_index + 1) % len(self.camp_options)
                        self.update_layout()  # 更新布局以重新定位箭头
                    
                    # AI难度选择箭头按钮
                    elif self.ai_left_arrow_button.is_clicked(mouse_pos, event):
                        self.sound_manager.play_sound('button')  # 播放按钮音效
                        self.current_ai_index = (self.current_ai_index - 1) % len(self.ai_difficulty_options)
                        self.update_layout()  # 更新布局以重新定位箭头
                    elif self.ai_right_arrow_button.is_clicked(mouse_pos, event):
                        self.sound_manager.play_sound('button')  # 播放按钮音效
                        self.current_ai_index = (self.current_ai_index + 1) % len(self.ai_difficulty_options)
                        self.update_layout()  # 更新布局以重新定位箭头
                    
                    # 确认按钮
                    elif self.confirm_button.is_clicked(mouse_pos, event):
                        self.sound_manager.play_sound('button')  # 播放按钮音效
                        # 根据选择的阵营文本确定阵营
                        if self.camp_options[self.current_camp_index] == "执红先行":
                            self.selected_camp = CAMP_RED
                        else:
                            self.selected_camp = CAMP_BLACK
                        
                        # 设置AI难度和算法
                        self.selected_ai_difficulty = self.ai_difficulty_options[self.current_ai_index]
                        
                    elif self.back_button.is_clicked(mouse_pos, event):
                        print("[DEBUG] 返回模式选择界面")
                        self.sound_manager.play_sound('button')  # 播放按钮音效
                        # 返回到上一级界面（模式选择界面）
                        return None  # 返回None表示返回上级界面

            # 更新按钮悬停状态
            self.left_arrow_button.check_hover(mouse_pos)
            self.right_arrow_button.check_hover(mouse_pos)
            self.ai_left_arrow_button.check_hover(mouse_pos)
            self.ai_right_arrow_button.check_hover(mouse_pos)
            self.confirm_button.check_hover(mouse_pos)
            self.back_button.check_hover(mouse_pos)

            # 绘制界面
            self.draw()
            pygame.display.flip()
            clock.tick(FPS)

        # 返回阵营和AI难度信息
        return {"camp": self.selected_camp, "ai_difficulty": self.selected_ai_difficulty}

    def draw(self):
        """绘制选择界面"""
        # 使用统一的背景绘制函数
        draw_background(self.screen)

        # 绘制标题
        title_font = load_font(40)  # 缩小标题字体
        title_text = "选择您的阵营与AI难度"
        title_surface = title_font.render(title_text, True, BLACK)
        title_rect = title_surface.get_rect(center=(self.window_width // 2, 100))  # 上移标题
        self.screen.blit(title_surface, title_rect)

        # 绘制金色装饰线
        line_y = title_rect.bottom + 20  # 调整线条位置
        pygame.draw.line(
            self.screen,
            GOLD,
            (self.window_width // 4, line_y),
            (self.window_width * 3 // 4, line_y),
            3
        )

        # 绘制阵营选择标题
        camp_title_font = load_font(24)
        camp_title = camp_title_font.render("选择阵营:", True, BLACK)
        self.screen.blit(camp_title, (self.window_width // 2 - camp_title.get_width() // 2, 200))

        # 绘制当前阵营选择
        current_camp = self.camp_options[self.current_camp_index]
        camp_font = load_font(32, bold=True)
        camp_text = camp_font.render(current_camp, True, GOLD)
        camp_text_x = self.window_width // 2 - camp_text.get_width() // 2
        self.screen.blit(camp_text, (camp_text_x, 250))

        # 绘制阵营选择箭头按钮
        self.left_arrow_button.draw(self.screen)
        self.right_arrow_button.draw(self.screen)

        # 绘制AI难度选择标题
        ai_title_font = load_font(24)
        ai_title = ai_title_font.render("选择AI难度:", True, BLACK)
        self.screen.blit(ai_title, (self.window_width // 2 - ai_title.get_width() // 2, 340))

        # 绘制当前AI难度选择
        current_ai = self.ai_difficulty_options[self.current_ai_index]
        ai_name_font = load_font(32, bold=True)
        ai_name_text = ai_name_font.render(current_ai["name"], True, GOLD)
        ai_text_x = self.window_width // 2 - ai_name_text.get_width() // 2
        self.screen.blit(ai_name_text, (ai_text_x, 390))

        # 绘制AI算法说明
        ai_desc_font = load_font(18)
        ai_desc_text = ai_desc_font.render(current_ai["desc"], True, BLACK)
        self.screen.blit(ai_desc_text, (self.window_width // 2 - ai_desc_text.get_width() // 2, 440))

        # 绘制AI难度选择箭头按钮
        self.ai_left_arrow_button.draw(self.screen)
        self.ai_right_arrow_button.draw(self.screen)

        # 绘制确认按钮
        self.confirm_button.draw(self.screen)

        # 绘制返回按钮
        self.back_button.draw(self.screen)