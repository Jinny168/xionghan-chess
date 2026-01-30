"""
匈汉象棋网络连接界面
"""
import sys
import time
from tkinter import Tk
from tkinter.simpledialog import askstring

import pygame

from program.controllers.game_config_manager import DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT, FPS
from program.ui.button import Button
from program.utils.utils import load_font, draw_gradient_background
from program.lan.xhlan import SimpleAPI
from program.lan.network_game import NetworkChessGame


class NetworkConnectScreen:
    """网络连接界面"""

    def __init__(self):
        self.window_width = DEFAULT_WINDOW_WIDTH
        self.window_height = DEFAULT_WINDOW_HEIGHT
        self.is_fullscreen = False
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("匈汉象棋 - 网络连接")

        self.update_layout()
        self.connection_type = None  # 'host' 或 'join'
        self.ip_address = ""
        
        # 添加取消按钮，用于在连接过程中取消
        self.cancel_button = None

    def update_layout(self):
        """更新布局"""
        button_width = 240
        button_height = 60
        button_spacing = 40
        center_x = self.window_width // 2
        center_y = self.window_height // 2 - 30

        # 创建按钮 - 使用更现代的颜色方案
        self.host_button = Button(
            center_x - button_width // 2,
            center_y - button_height - button_spacing,
            button_width,
            button_height,
            "创建房间",
            28,
            bg_color=(70, 130, 180),  # Steel Blue
            hover_color=(100, 149, 237),  # Cornflower Blue
            text_color=(255, 255, 255),
            border_radius=15
        )

        self.join_button = Button(
            center_x - button_width // 2,
            center_y,
            button_width,
            button_height,
            "加入房间",
            28,
            bg_color=(50, 150, 50),  # Green
            hover_color=(34, 139, 34),  # Forest Green
            text_color=(255, 255, 255),
            border_radius=15
        )

        self.back_button = Button(
            center_x - button_width // 2,
            center_y + button_height + button_spacing,
            button_width,
            button_height,
            "返回",
            28,
            bg_color=(180, 70, 70),  # Reddish
            hover_color=(220, 100, 100),
            text_color=(255, 255, 255),
            border_radius=15
        )

    def toggle_fullscreen(self):
        """切换全屏模式"""
        self.is_fullscreen = not self.is_fullscreen

        if self.is_fullscreen:
            # 获取显示器信息
            info = pygame.display.Info()
            # 保存窗口模式的尺寸
            self.windowed_size = (self.window_width, self.window_height)
            # 切换到全屏模式
            self.screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
            self.window_width = info.current_w
            self.window_height = info.current_h
        else:
            # 恢复窗口模式
            self.window_width, self.window_height = self.windowed_size
            self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)

        # 更新布局
        self.update_layout()

    def handle_resize(self, new_size):
        """处理窗口大小变化"""
        self.window_width, self.window_height = new_size
        # 更新布局
        self.update_layout()

    def show_ip_input_dialog(self):
        """显示IP输入对话框"""
        root = Tk()
        root.withdraw()  # 隐藏主窗口
        ip = askstring("加入房间", "请输入房间IP地址:", initialvalue="127.0.0.1")
        root.destroy()
        return ip

    def run_connection_process(self, mode, ip_address=None):
        """运行连接过程，显示连接状态"""
        clock = pygame.time.Clock()
        connection_status = "正在初始化..."
        status_messages = []
        status_messages.append("初始化网络模块...")

        # 显示连接过程界面
        start_time = time.time()
        max_wait_time = 30  # 最大等待时间30秒

        if mode == "host":
            # 作为服务器启动
            connection_status = "正在启动服务器..."
            status_messages.append("正在启动服务器...")

            # 初始化API
            SimpleAPI.init('SERVER')
            status_messages.append("服务器初始化完成")
            connection_status = "服务器已启动，等待客户端连接..."
            status_messages.append("服务器已启动，等待客户端连接...")

            # 等待连接
            connected = False
            wait_start = time.time()
            cancelled = False
            while time.time() - wait_start < 30 and not connected and not cancelled:  # 等待30秒
                # 检查是否有客户端连接
                if (SimpleAPI.instance and
                    hasattr(SimpleAPI.instance, 'connection') and
                    SimpleAPI.instance.connection is not None):
                    connected = True
                    status_messages.append("客户端已连接！")
                    connection_status = "客户端已连接，正在启动游戏..."
                else:
                    # 继续等待
                    pass

                # 检查退出事件
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = pygame.mouse.get_pos()
                        if self.cancel_button and self.cancel_button.is_clicked(mouse_pos, event):
                            cancelled = True
                            status_messages.append("用户取消了连接")
                            connection_status = "连接已被取消..."

                # 更新按钮悬停状态
                if self.cancel_button:
                    self.cancel_button.check_hover(pygame.mouse.get_pos())

                # 绘制连接状态
                self.draw_connection_status(connection_status, status_messages, mode)
                pygame.display.flip()
                clock.tick(FPS)

            if cancelled:
                status_messages.append("连接被用户取消")
                connection_status = "连接已取消，返回主菜单..."
                time.sleep(1)
                return "back_to_menu", None
                
            if connected:
                # 等待一小段时间让客户端准备好
                time.sleep(1)
                # 启动游戏
                try:
                    game = NetworkChessGame(is_host=True)
                    return game.run()
                except Exception as e:
                    status_messages.append(f"游戏启动失败: {str(e)}")
                    connection_status = "游戏启动失败，返回主菜单..."
                    time.sleep(2)
                    return "back_to_menu", None
            else:
                status_messages.append("等待客户端连接超时")
                connection_status = "连接超时，请检查网络设置..."
                time.sleep(3)
                return "back_to_menu", None

        elif mode == "join":
            # 作为客户端连接
            connection_status = "正在连接到服务器..."
            status_messages.append(f"正在连接到服务器: {ip_address or '127.0.0.1'}")

            # 初始化API
            SimpleAPI.init('CLIENT')
            status_messages.append("客户端初始化完成")
            connection_status = f"尝试连接到服务器: {ip_address or '127.0.0.1'}"

            # 等待连接建立
            connected = False
            wait_start = time.time()
            max_wait_time = 15
            cancelled = False
            while time.time() - wait_start < max_wait_time and not connected and not cancelled:
                # 检查连接状态
                if SimpleAPI.is_connected():
                    connected = True
                    status_messages.append("成功连接到服务器！")
                    connection_status = "连接成功，正在启动游戏..."
                else:
                    time.sleep(0.5)  # 短暂延迟，避免过度占用CPU

                # 检查退出事件
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = pygame.mouse.get_pos()
                        if self.cancel_button and self.cancel_button.is_clicked(mouse_pos, event):
                            cancelled = True
                            status_messages.append("用户取消了连接")
                            connection_status = "连接已被取消..."

                # 更新按钮悬停状态
                if self.cancel_button:
                    self.cancel_button.check_hover(pygame.mouse.get_pos())

                # 更新状态
                self.draw_connection_status(connection_status, status_messages, mode)
                pygame.display.flip()
                clock.tick(FPS)

            if cancelled:
                status_messages.append("连接被用户取消")
                connection_status = "连接已取消，返回主菜单..."
                time.sleep(1)
                return "back_to_menu", None
                
            if connected:
                # 等待一小段时间确保连接稳定
                time.sleep(1)
                # 启动游戏
                try:
                    game = NetworkChessGame(is_host=False)
                    return game.run()
                except Exception as e:
                    status_messages.append(f"游戏启动失败: {str(e)}")
                    connection_status = "游戏启动失败，返回主菜单..."
                    time.sleep(2)
                    return "back_to_menu", None
            else:
                status_messages.append(f"无法连接到服务器: {ip_address or '127.0.0.1'}")
                connection_status = "连接失败，请检查IP地址和网络..."
                time.sleep(3)
                return "back_to_menu", None

    def draw_connection_status(self, current_status, status_messages, mode):
        """绘制连接状态界面"""
        # 使用渐变背景
        draw_gradient_background(self.screen)

        # 绘制半透明覆盖层
        overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 200))  # 半透明白色覆盖层
        self.screen.blit(overlay, (0, 0))

        # 绘制标题
        title_font = load_font(48)
        title_text = "网络连接状态"
        title_surface = title_font.render(title_text, True, (50, 50, 100))
        title_rect = title_surface.get_rect(center=(self.window_width//2, 80))
        self.screen.blit(title_surface, title_rect)

        # 绘制连接模式
        mode_text = f"模式: {'服务器(房主)' if mode == 'host' else '客户端(加入者)'}"
        mode_font = load_font(28)
        mode_surface = mode_font.render(mode_text, True, (70, 70, 120))
        mode_rect = mode_surface.get_rect(center=(self.window_width//2, 140))
        self.screen.blit(mode_surface, mode_rect)

        # 绘制当前状态
        status_font = load_font(32)
        status_surface = status_font.render(current_status, True, 
                                          (0, 150, 0) if "成功" in current_status or "连接" in current_status 
                                          else (200, 0, 0) if "失败" in current_status or "取消" in current_status 
                                          else (200, 150, 0))
        status_rect = status_surface.get_rect(center=(self.window_width//2, 190))
        self.screen.blit(status_surface, status_rect)

        # 绘制状态历史
        history_font = load_font(20)
        y_offset = 250
        # 只显示最新的几条消息
        recent_messages = status_messages[-8:]  # 只显示最近8条消息
        for i, msg in enumerate(recent_messages):
            color = (80, 80, 80)  # 默认灰色
            if "成功" in msg or "连接" in msg:
                color = (0, 150, 0)  # 成功状态绿色
            elif "失败" in msg or "超时" in msg or "错误" in msg or "取消" in msg:
                color = (200, 0, 0)  # 错误状态红色
            elif "等待" in msg:
                color = (200, 150, 0)  # 等待状态黄色

            msg_surface = history_font.render(f"• {msg}", True, color)
            self.screen.blit(msg_surface, (self.window_width//2 - 250, y_offset + i * 35))

        # 创建取消按钮（在连接状态界面显示）
        button_width = 160
        button_height = 45
        cancel_button_x = self.window_width // 2 - button_width // 2
        cancel_button_y = self.window_height - 100  # 底部位置
        
        if self.cancel_button is None:
            self.cancel_button = Button(
                cancel_button_x,
                cancel_button_y,
                button_width,
                button_height,
                "取消连接",
                22,
                bg_color=(180, 70, 70),
                hover_color=(220, 100, 100),
                text_color=(255, 255, 255),
                border_radius=10
            )
        else:
            # 更新按钮位置（以防窗口大小改变）
            self.cancel_button.x = cancel_button_x
            self.cancel_button.y = cancel_button_y
            
        # 绘制取消按钮
        self.cancel_button.draw(self.screen)

    def run(self):
        """运行网络连接界面"""
        clock = pygame.time.Clock()

        while self.connection_type is None:
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
                    if self.host_button.is_clicked(mouse_pos, event):
                        # 创建房间 - 开始连接过程
                        result, _ = self.run_connection_process("host")
                        if result == "back_to_menu":
                            return "back", None
                    elif self.join_button.is_clicked(mouse_pos, event):
                        # 弹出IP输入对话框
                        ip = self.show_ip_input_dialog()
                        if ip:
                            self.ip_address = ip
                            # 开始连接过程
                            result, _ = self.run_connection_process("join", ip)
                            if result == "back_to_menu":
                                return "back", None
                    elif self.back_button.is_clicked(mouse_pos, event):
                        self.connection_type = "back"

            # 更新按钮悬停状态
            self.host_button.check_hover(mouse_pos)
            self.join_button.check_hover(mouse_pos)
            self.back_button.check_hover(mouse_pos)

            # 绘制界面
            self.draw()
            pygame.display.flip()
            clock.tick(FPS)

        return self.connection_type, self.ip_address

    def draw(self):
        """绘制界面"""
        # 使用渐变背景
        draw_gradient_background(self.screen)

        # 绘制半透明覆盖层
        overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 180))  # 半透明白色覆盖层
        self.screen.blit(overlay, (0, 0))

        # 绘制标题
        title_font = load_font(56)
        title_text = "网络对战"
        title_surface = title_font.render(title_text, True, (50, 50, 100))
        title_rect = title_surface.get_rect(center=(self.window_width//2, 150))
        self.screen.blit(title_surface, title_rect)

        # 绘制装饰元素
        pygame.draw.line(self.screen, (100, 150, 200), 
                         (self.window_width//2 - 150, 190), 
                         (self.window_width//2 + 150, 190), 3)

        # 绘制副标题
        subtitle_font = load_font(28)
        subtitle_text = "请选择网络对战方式"
        subtitle_surface = subtitle_font.render(subtitle_text, True, (80, 80, 120))
        subtitle_rect = subtitle_surface.get_rect(center=(self.window_width//2, 220))
        self.screen.blit(subtitle_surface, subtitle_rect)

        # 绘制装饰图标
        icon_font = load_font(36)
        server_icon = icon_font.render("🏠", True, (70, 130, 180))
        client_icon = icon_font.render("👤", True, (50, 150, 50))
        self.screen.blit(server_icon, (self.window_width//2 - 180, self.host_button.y + 10))
        self.screen.blit(client_icon, (self.window_width//2 - 180, self.join_button.y + 10))

        # 绘制按钮
        self.host_button.draw(self.screen)
        self.join_button.draw(self.screen)
        self.back_button.draw(self.screen)