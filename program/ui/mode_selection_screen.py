import os
import sys

import pygame

from program.controllers.game_config_manager import (
    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT,
    GOLD, MODE_PVP, MODE_PVC, FPS
)
from program.controllers.sound_manager import sound_manager
from program.ui.button import Button, StyledButton
from program.utils import tools, utils
from program.utils.utils import load_font, draw_background


class BackgroundManager:
    """背景图管理类，处理模式选择界面的背景图切换逻辑"""
    
    def __init__(self):
        # 背景图配置
        self.background_config = {
            "images": [
                "assets/pics/4.jpg",   # 预设背景图1
                "assets/pics/3.jpg",   # 预设背景图2
                "assets/pics/2.jpg",   # 预设背景图3
                "assets/pics/1.jpg"    # 预设背景图4
            ],
            "default_bg_color": (200, 200, 200),  # 背景图加载失败时的默认纯色
            "button_style": {
                "position": (200, 30),              # 按钮位置（x:200, y:30）
                "size": (120, 40),                  # 按钮尺寸（宽120px，高40px）
                "border_color": (100, 100, 100),    # 按钮边框色（深灰色）
                "text_color": (50, 50, 50),         # 按钮文字色（深灰色）
                "text": "切换背景"                  # 按钮文字
            }
        }
        self.current_bg_index = 0  # 默认加载第一张背景图
        self.background_image = None

    def load_background(self, index):
        """根据索引加载背景图，捕获异常并返回默认背景"""
        try:
            bg_path = self.background_config["images"][index]
            bg_full_path = utils.resource_path(bg_path)
            if os.path.exists(bg_full_path):
                background = pygame.image.load(bg_full_path).convert()
                return background
            else:
                print(f"背景图片不存在: {bg_full_path}")
                return None
        except Exception as e:
            print(f"无法加载背景图片: {e}")
            return None

    def switch_background(self):
        """循环切换背景图索引，调用load_background()更新背景"""
        # 循环切换背景图索引
        self.current_bg_index = (self.current_bg_index + 1) % len(self.background_config["images"])
        # 加载新背景
        self.background_image = self.load_background(self.current_bg_index)
        return self.background_image

    def get_current_background(self):
        """获取当前背景图像"""
        if self.background_image is None:
            self.background_image = self.load_background(self.current_bg_index)
        return self.background_image


class ModeSelectionScreen:
    def __init__(self):
        # 初始化窗口尺寸和模式
        self.settings_menu_items = None
        self.settings_button = None
        self.pvc_button = None
        self.network_button = None
        self.pvp_button = None
        self.windowed_size = None
        self.window_width = DEFAULT_WINDOW_WIDTH
        self.window_height = DEFAULT_WINDOW_HEIGHT
        self.is_fullscreen = False
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("匈汉象棋 - 模式选择")

        # 使用全局声音管理器
        self.sound_manager = sound_manager

        # 背景相关
        self.background_image = None
        self.background_surface = None
        self.background_images = [
            "assets/pics/4.jpg",
            "assets/pics/3.jpg",
            "assets/pics/2.jpg",
            "assets/pics/1.jpg"
        ]
        self.current_bg_index = 0  # 添加这个缺失的属性
        self.load_background()
        
        # 设置菜单状态
        self.show_settings_menu = False
        self.settings_menu_opening = False
        self.settings_menu_closing = False
        self.settings_menu_animation_progress = 0.0  # 0.0 to 1.0
        self.animation_direction = 0  # 0=idle, 1=opening, -1=closing
        self.gear_rotation = 0  # 齿轮图标旋转角度

        # 添加游戏模式选择滚动框
        self.game_mode_options = ["经典匈汉", "狂暴匈汉", "传统象棋"]
        self.current_game_mode_index = 0  # 默认选择经典匈汉

        # 添加游戏类型选择滚动框
        self.game_type_options = ["双人对战", "人机对战", "网络对战"]
        self.current_game_type_index = 0  # 默认选择双人对战

        # 添加左右箭头按钮
        self.game_mode_left_arrow_button = None
        self.game_mode_right_arrow_button = None
        self.game_type_left_arrow_button = None
        self.game_type_right_arrow_button = None

        # 添加开始游戏按钮
        self.start_game_button = None

        # 添加传统象棋模式按钮
        self.traditional_chess_button = None
        
        # 初始化布局
        self.update_layout()
        self.selected_mode = None
        
    def load_background(self):
        """加载背景图片，如果没有则使用默认背景"""
        # 尝试加载当前背景图片
        if self.current_bg_index < len(self.background_images):
            bg_path = self.background_images[self.current_bg_index]
            try:
                # 使用resource_path处理资源路径
                bg_full_path = utils.resource_path(bg_path)
                if os.path.exists(bg_full_path):
                    self.background_image = pygame.image.load(bg_full_path).convert()
                else:
                    print(f"背景图片不存在: {bg_full_path}")
                    self.background_image = None
            except Exception as e:
                print(f"无法加载背景图片: {e}")
                self.background_image = None
        else:
            # 如果超出范围，尝试加载默认背景
            try:
                bg_path = utils.resource_path("assets/pics/4.jpg")
                if os.path.exists(bg_path):
                    self.background_image = pygame.image.load(bg_path).convert()
                else:
                    # 尝试其他常见背景图片路径
                    alt_paths = [
                        utils.resource_path("assets/pics/3.jpg"),
                        utils.resource_path("assets/pics/2.jpg"),
                        utils.resource_path("assets/pics/1.jpg")
                    ]
                    for path in alt_paths:
                        if os.path.exists(path):
                            self.background_image = pygame.image.load(path).convert()
                            break
            except Exception as e:
                print(f"无法加载背景图片: {e}")
                self.background_image = None

    def switch_background(self):
        """循环切换背景图"""
        # 循环切换背景图索引
        self.current_bg_index = (self.current_bg_index + 1) % len(self.background_images)
        # 加载新背景
        self.load_background()

    def update_layout(self):
        """根据当前窗口尺寸更新布局"""
        # 计算基准尺寸（以360px宽度为基准）
        base_width = 360
        scale_factor = self.window_width / base_width

        # 按钮尺寸 - 缩小按钮尺寸
        button_width = max(int(80 * scale_factor), 80)  # 基准80px (原100px)
        button_height = max(int(35 * scale_factor), 35)  # 基准35px (原40px)
        button_spacing = max(int(12 * scale_factor), 12)  # 基准12px (原15px)
        center_x = self.window_width // 2
        center_y = self.window_height // 2 - 30  # 调整中心位置

        # 添加游戏模式选择滚动框
        arrow_button_width = 50
        arrow_button_height = 50
        game_mode_center_y = 250  # 游戏模式选择的位置
        current_game_mode = self.game_mode_options[self.current_game_mode_index]
        from program.utils.utils import load_font
        game_mode_font = load_font(32, bold=True)
        game_mode_text = game_mode_font.render(current_game_mode, True, GOLD)
        game_mode_text_x = center_x - game_mode_text.get_width() // 2
        game_mode_text_y = game_mode_center_y
        game_mode_arrow_y = game_mode_text_y + (game_mode_text.get_height() // 2) - (arrow_button_height // 2)
        
        # 左箭头在文本左边，右箭头在文本右边
        game_mode_left_arrow_x = game_mode_text_x - arrow_button_width - 10
        game_mode_right_arrow_x = game_mode_text_x + game_mode_text.get_width() + 10
        
        self.game_mode_left_arrow_button = StyledButton(
            game_mode_left_arrow_x,
            game_mode_arrow_y,
            arrow_button_width,
            arrow_button_height,
            "<",
            30,
            10
        )

        self.game_mode_right_arrow_button = StyledButton(
            game_mode_right_arrow_x,
            game_mode_arrow_y,
            arrow_button_width,
            arrow_button_height,
            ">",
            30,
            10
        )

        # 添加游戏类型选择滚动框
        game_type_center_y = 390  # 游戏类型选择的位置
        current_game_type = self.game_type_options[self.current_game_type_index]
        game_type_font = load_font(32, bold=True)
        game_type_text = game_type_font.render(current_game_type, True, GOLD)
        game_type_text_x = center_x - game_type_text.get_width() // 2
        game_type_text_y = game_type_center_y
        game_type_arrow_y = game_type_text_y + (game_type_text.get_height() // 2) - (arrow_button_height // 2)
        
        # 左箭头在文本左边，右箭头在文本右边
        game_type_left_arrow_x = game_type_text_x - arrow_button_width - 10
        game_type_right_arrow_x = game_type_text_x + game_type_text.get_width() + 10
        
        self.game_type_left_arrow_button = StyledButton(
            game_type_left_arrow_x,
            game_type_arrow_y,
            arrow_button_width,
            arrow_button_height,
            "<",
            30,
            10
        )

        self.game_type_right_arrow_button = StyledButton(
            game_type_right_arrow_x,
            game_type_arrow_y,
            arrow_button_width,
            arrow_button_height,
            ">",
            30,
            10
        )

        # 添加开始游戏按钮
        start_button_width = 120
        start_button_height = 40
        self.start_game_button = StyledButton(
            center_x - start_button_width // 2,
            center_y + 200,  # 开始游戏按钮Y位置
            start_button_width,
            start_button_height,
            "开始游戏",
            18,
            10
        )
        
        # 添加传统象棋模式按钮
        self.traditional_chess_button = StyledButton(
            center_x - start_button_width // 2,
            center_y + 250,  # 传统象棋按钮Y位置
            start_button_width,
            start_button_height,
            "传统象棋",
            18,
            10
        )

        # 设置按钮（右下角，圆形按钮）
        settings_button_size = max(int(25 * scale_factor), 25)  # 进一步缩小设置按钮
        self.settings_button = StyledButton(
            self.window_width - settings_button_size - 10,  # 距离右边10px
            self.window_height - settings_button_size - 10,  # 距离底部10px
            settings_button_size,
            settings_button_size,
            "⚙️",  # 齿轮图标
            int(12 * scale_factor),  # 进一步缩小
            15  # 圆角，近似圆形
        )

        # 设置菜单项（隐藏状态）
        menu_item_width = max(int(50 * scale_factor), 50)  # 进一步缩小
        menu_item_height = max(int(16 * scale_factor), 16)  # 进一步缩小
        menu_spacing = 1  # 菜单项间距 (进一步缩小)

        # 计算菜单位置（在设置按钮上方，紧密对齐）
        menu_x = self.window_width - menu_item_width - 10
        menu_y = self.window_height - settings_button_size - 10 - (5 * menu_item_height + 4 * menu_spacing)

        self.settings_menu_items = []
        settings_options = [
            ("切换背景", "bg_switch"),
            ("自定义设置", "settings"),
            ("游戏规则", "rules"),
            ("游戏统计", "stats"),
            ("导入棋局", "load_game")
        ]

        for i, (text, mode) in enumerate(settings_options):
            item = StyledButton(
                menu_x,
                menu_y + i * (menu_item_height + menu_spacing),
                menu_item_width,
                menu_item_height,
                text,
                int(8 * scale_factor),  # 进一步缩小
                6  # 圆角
            )
            self.settings_menu_items.append((item, mode))

    def toggle_settings_menu(self):
        """切换设置菜单显示状态"""
        if self.show_settings_menu:
            # 关闭菜单
            self.settings_menu_closing = True
            self.animation_direction = -1
            self.settings_menu_opening = False
        else:
            # 打开菜单
            self.settings_menu_opening = True
            self.animation_direction = 1
            self.settings_menu_closing = False
        self.show_settings_menu = not self.show_settings_menu

    def update_settings_menu_animation(self, dt):
        """更新设置菜单动画"""
        if self.animation_direction != 0:
            # 动画速度：每秒1单位
            animation_speed = dt * 2.0  # 2秒完成整个动画

            if self.animation_direction == 1:  # 打开
                self.settings_menu_animation_progress += animation_speed
                if self.settings_menu_animation_progress >= 1.0:
                    self.settings_menu_animation_progress = 1.0
                    self.settings_menu_opening = False
                    self.animation_direction = 0
            else:  # 关闭
                self.settings_menu_animation_progress -= animation_speed
                if self.settings_menu_animation_progress <= 0.0:
                    self.settings_menu_animation_progress = 0.0
                    self.settings_menu_closing = False
                    self.animation_direction = 0

        # 更新齿轮旋转动画
        if self.show_settings_menu:
            self.gear_rotation = (self.gear_rotation + dt * 180) % 360  # 每秒180度
        else:
            self.gear_rotation = (self.gear_rotation - dt * 180) % 360  # 每秒180度

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
        """运行模式选择界面"""
        clock = pygame.time.Clock()
        last_time = pygame.time.get_ticks()

        while self.selected_mode is None:
            current_time = pygame.time.get_ticks()
            dt = (current_time - last_time) / 1000.0  # 时间差（秒）
            last_time = current_time

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
                    # 游戏模式选择箭头按钮
                    if self.game_mode_left_arrow_button.is_clicked(mouse_pos, event):
                        self.sound_manager.play_sound('button')  # 播放按钮音效
                        self.current_game_mode_index = (self.current_game_mode_index - 1) % len(self.game_mode_options)
                        self.update_layout()  # 更新布局以重新定位箭头
                    elif self.game_mode_right_arrow_button.is_clicked(mouse_pos, event):
                        self.sound_manager.play_sound('button')  # 播放按钮音效
                        self.current_game_mode_index = (self.current_game_mode_index + 1) % len(self.game_mode_options)
                        self.update_layout()  # 更新布局以重新定位箭头
                    
                    # 游戏类型选择箭头按钮
                    elif self.game_type_left_arrow_button.is_clicked(mouse_pos, event):
                        self.sound_manager.play_sound('button')  # 播放按钮音效
                        self.current_game_type_index = (self.current_game_type_index - 1) % len(self.game_type_options)
                        self.update_layout()  # 更新布局以重新定位箭头
                    elif self.game_type_right_arrow_button.is_clicked(mouse_pos, event):
                        self.sound_manager.play_sound('button')  # 播放按钮音效
                        self.current_game_type_index = (self.current_game_type_index + 1) % len(self.game_type_options)
                        self.update_layout()  # 更新布局以重新定位箭头
                    
                    # 开始游戏按钮
                    elif self.start_game_button.is_clicked(mouse_pos, event):
                        self.sound_manager.play_sound('button')  # 播放按钮音效
                        # 检查是否选择了传统象棋模式
                        selected_game_mode = self.game_mode_options[self.current_game_mode_index]
                        if selected_game_mode == "传统象棋":
                            # 设置传统象棋模式，禁用经典模式
                            from program.controllers.game_config_manager import game_config
                            game_config.set_setting("traditional_mode", True)
                            game_config.set_setting("classic_mode", False)
                        elif selected_game_mode == "经典匈汉":
                            # 设置经典匈汉模式，禁用传统模式
                            from program.controllers.game_config_manager import game_config
                            game_config.set_setting("traditional_mode", False)
                            game_config.set_setting("classic_mode", True)
                        elif selected_game_mode == "狂暴匈汉":
                            # 设置狂暴匈汉模式，禁用传统和经典模式
                            from program.controllers.game_config_manager import game_config
                            game_config.set_setting("traditional_mode", False)
                            game_config.set_setting("classic_mode", False)
                        # 根据选择的游戏类型设置最终模式
                        selected_type = self.game_type_options[self.current_game_type_index]
                        if selected_type == "双人对战":
                            self.selected_mode = MODE_PVP
                        elif selected_type == "人机对战":
                            self.selected_mode = MODE_PVC
                        elif selected_type == "网络对战":
                            self.selected_mode = "network"


                    elif self.settings_button.is_clicked(mouse_pos, event):
                        self.sound_manager.play_sound('button')  # 播放按钮音效
                        self.toggle_settings_menu()
                    elif self.show_settings_menu:
                        # 检查是否点击了设置菜单项
                        for button, mode in self.settings_menu_items:
                            if button.is_clicked(mouse_pos, event):
                                self.sound_manager.play_sound('button')  # 播放按钮音效
                                if mode == "bg_switch":
                                    # 切换背景
                                    self.switch_background()
                                    # 关闭设置菜单
                                    if self.show_settings_menu:
                                        self.toggle_settings_menu()
                                elif mode == "load_game":
                                    # 特殊处理：导入棋局
                                    from program.core.game_state import GameState
                                    from program.controllers.game_io_controller import GameIOController
                                    from program.ui.replay_screen import ReplayScreen
                                    from program.controllers.game_config_manager import game_config

                                    # 创建游戏状态
                                    game_state = GameState()

                                    # 从文件加载游戏
                                    io_controller = GameIOController()
                                    success = io_controller.import_game(game_state)

                                    if success:
                                        # 进入复盘模式
                                        from program.controllers.replay_controller import ReplayController
                                        replay_controller = ReplayController(game_state)
                                        replay_controller.start_replay()

                                        # 创建并运行复盘界面
                                        replay_screen = ReplayScreen(game_state, replay_controller)
                                        replay_screen.run()

                                    # 重新进入模式选择界面
                                    self.selected_mode = None
                                    # 关闭设置菜单
                                    if self.show_settings_menu:
                                        self.toggle_settings_menu()
                                else:
                                    self.selected_mode = mode
                                break
                        else:
                            # 点击了菜单外部区域，关闭菜单
                            if self.show_settings_menu:
                                self.sound_manager.play_sound('button')  # 播放按钮音效
                                self.toggle_settings_menu()

            # 更新按钮悬停状态
            self.game_mode_left_arrow_button.check_hover(mouse_pos)
            self.game_mode_right_arrow_button.check_hover(mouse_pos)
            self.game_type_left_arrow_button.check_hover(mouse_pos)
            self.game_type_right_arrow_button.check_hover(mouse_pos)
            self.start_game_button.check_hover(mouse_pos)
            self.settings_button.check_hover(mouse_pos)

            # 更新设置菜单项的悬停状态
            if self.show_settings_menu:
                for button, _ in self.settings_menu_items:
                    button.check_hover(mouse_pos)

            # 更新动画
            self.update_settings_menu_animation(dt)

            # 绘制界面
            self.draw()
            pygame.display.flip()
            clock.tick(FPS)

        return self.selected_mode

    def draw(self):
        """绘制选择界面"""
        # 绘制背景
        if self.background_image:
            # 缩放背景图片以适应窗口
            scaled_bg = pygame.transform.smoothscale(self.background_image, (self.window_width, self.window_height))
            self.screen.blit(scaled_bg, (0, 0))
            # 添加半透明遮罩
            overlay = pygame.Surface((self.window_width, self.window_height))
            overlay.set_alpha(100)  # 40% 透明度
            overlay.fill((44, 30, 22))  # 棕褐色遮罩
            self.screen.blit(overlay, (0, 0))
        else:
            # 使用默认背景
            draw_background(self.screen)

        # 绘制带火焰特效的标题
        title_font = load_font(max(40, int(40 * self.window_width / 360)), bold=True)  # 缩小标题字体
        if title_font:
            title_text = "匈汉象棋"

            # 绘制火焰光晕效果（橙红色到黄色的渐变效果）
            glow_offsets = [(i, j) for i in range(-4, 5) for j in range(-4, 5) if
                            abs(i) + abs(j) <= 4 and (i, j) != (0, 0)]
            for idx, (offset_x, offset_y) in enumerate(glow_offsets):
                # 创建随时间变化的动态火焰效果
                distance = abs(offset_x) + abs(offset_y)
                if distance <= 2:
                    color = (255, min(165, 100 + idx % 20), 0)  # 橙红色
                elif distance <= 4:
                    color = (255, min(140, 80 + idx % 15), 0)  # 较淡的橙色
                else:
                    color = (255, min(100, 60 + idx % 10), 0)  # 更淡的橙色

                alpha = 150 if distance <= 2 else 100 if distance <= 3 else 50

                glow_surface = title_font.render(title_text, True, color)
                glow_surface.set_alpha(alpha)
                glow_rect = glow_surface.get_rect(center=(self.window_width // 2 + offset_x, 100 + offset_y))
                self.screen.blit(glow_surface, glow_rect)

            # 绘制描边（深红色）
            outline_offsets = [(-2, -2), (-2, -1), (-2, 0), (-2, 1), (-2, 2),
                               (-1, -2), (-1, -1), (-1, 0), (-1, 1), (-1, 2),
                               (0, -2), (0, -1), (0, 1), (0, 2),
                               (1, -2), (1, -1), (1, 0), (1, 1), (1, 2),
                               (2, -2), (2, -1), (2, 0), (2, 1), (2, 2)]
            for offset_x, offset_y in outline_offsets:
                outline_surface = title_font.render(title_text, True, (139, 0, 0))  # 深红色描边
                outline_rect = outline_surface.get_rect(center=(self.window_width // 2 + offset_x, 100 + offset_y))
                self.screen.blit(outline_surface, outline_rect)

            # 绘制主体文字（金色）
            title_surface = title_font.render(title_text, True, (255, 215, 0))  # 金色主体文字
            title_rect = title_surface.get_rect(center=(self.window_width // 2, 100))  # 标题位置
            self.screen.blit(title_surface, title_rect)

            # 绘制金色装饰线
            line_y = title_rect.bottom + 10
            pygame.draw.line(
                self.screen,
                GOLD,
                (self.window_width // 4, line_y),
                (self.window_width * 3 // 4, line_y),
                3
            )

        # 绘制游戏模式选择标题
        game_mode_title_font = load_font(24)
        game_mode_title = game_mode_title_font.render("选择游戏模式:", True, (0, 0, 0))
        self.screen.blit(game_mode_title, (self.window_width // 2 - game_mode_title.get_width() // 2, 200))

        # 绘制当前游戏模式选择
        current_game_mode = self.game_mode_options[self.current_game_mode_index]
        game_mode_font = load_font(32, bold=True)
        game_mode_text = game_mode_font.render(current_game_mode, True, GOLD)
        game_mode_text_x = self.window_width // 2 - game_mode_text.get_width() // 2
        self.screen.blit(game_mode_text, (game_mode_text_x, 250))

        # 绘制游戏模式选择箭头按钮
        self.game_mode_left_arrow_button.draw(self.screen)
        self.game_mode_right_arrow_button.draw(self.screen)

        # 绘制游戏类型选择标题
        game_type_title_font = load_font(24)
        game_type_title = game_type_title_font.render("选择游戏类型:", True, (0, 0, 0))
        self.screen.blit(game_type_title, (self.window_width // 2 - game_type_title.get_width() // 2, 340))

        # 绘制当前游戏类型选择
        current_game_type = self.game_type_options[self.current_game_type_index]
        game_type_font = load_font(32, bold=True)
        game_type_text = game_type_font.render(current_game_type, True, GOLD)
        game_type_text_x = self.window_width // 2 - game_type_text.get_width() // 2
        self.screen.blit(game_type_text, (game_type_text_x, 390))

        # 绘制游戏类型选择箭头按钮
        self.game_type_left_arrow_button.draw(self.screen)
        self.game_type_right_arrow_button.draw(self.screen)

        # 绘制开始游戏按钮
        self.start_game_button.draw(self.screen)

        # 绘制设置按钮
        # 创建一个临时表面用于绘制旋转的图标
        if self.gear_rotation != 0:
            # 先绘制按钮
            self.settings_button.draw(self.screen)

            # 获取按钮字体大小（通过字体对象估算）
            # 使用按钮字体大小创建旋转文本
            button_font_size = self.settings_button.font.size('A')[1]  # 获取字符高度作为字体大小的近似值
            button_font = load_font(button_font_size)
            if button_font:
                text_surface = button_font.render(self.settings_button.text, True,
                                                  (240, 240, 255))  # 使用固定的颜色而不是悬停状态
                # 旋转文本
                rotated_text = pygame.transform.rotate(text_surface, self.gear_rotation)
                # 居中放置旋转后的文本
                text_rect = rotated_text.get_rect(center=self.settings_button.rect.center)
                self.screen.blit(rotated_text, text_rect)
        else:
            self.settings_button.draw(self.screen)

        # 绘制设置菜单
        if self.show_settings_menu or self.settings_menu_opening or self.settings_menu_closing:
            # 计算菜单透明度和位置动画
            alpha = min(255, int(200 * self.settings_menu_animation_progress))
            vertical_offset = int(
                10 * (1 - self.settings_menu_animation_progress)) if self.animation_direction == 1 else 0

            for i, (button, _) in enumerate(self.settings_menu_items):
                # 计算每个菜单项的显示进度
                item_progress = max(0, min(1.0,self.settings_menu_animation_progress * 4.0 - i * 0.25))
                if item_progress > 0:
                    # 绘制半透明背景
                    menu_surface = pygame.Surface((button.rect.width, button.rect.height))
                    menu_surface.set_alpha(int(200 * item_progress))  # 80% 透明度
                    menu_surface.fill((68, 68, 68))  # 深灰色
                    self.screen.blit(menu_surface, (button.rect.x, button.rect.y + vertical_offset))

                    # 由于Button类没有alpha参数的draw方法，我们创建一个临时按钮
                    temp_button = Button(button.rect.x, button.rect.y + vertical_offset,
                                         button.rect.width, button.rect.height, button.text)
                    # 手动绘制具有透明度的按钮
                    temp_color = (120, 120, 220) if temp_button.is_hovered else (100, 100, 200)
                    temp_surface = pygame.Surface((temp_button.rect.width, temp_button.rect.height))
                    temp_surface.set_alpha(int(255 * item_progress))
                    temp_surface.fill(temp_color)
                    pygame.draw.rect(temp_surface, (0, 0, 0), temp_surface.get_rect(), 2)  # 边框

                    # 绘制文本
                    text_surf = temp_button.font.render(temp_button.text, True, (240, 240, 255))
                    text_rect = text_surf.get_rect(center=temp_surface.get_rect().center)
                    temp_surface.blit(text_surf, text_rect)

                    self.screen.blit(temp_surface, (temp_button.rect.x, temp_button.rect.y))

        # 绘制版权信息
        copyright_text = "© 2026 靳中原"
        copyright_surface = load_font(28).render(copyright_text, True, (255, 255, 255))
        copyright_rect = copyright_surface.get_rect(
            center=(self.window_width // 2, self.window_height - 30)
        )
        self.screen.blit(copyright_surface, copyright_rect)