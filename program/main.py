import pygame
import time

from controllers.game_config_manager import MODE_PVC, CAMP_RED
from game import ChessGame
from lan.network_game import NetworkChessGame
from ui.network_connect_screen import NetworkConnectScreen
from ui.mode_selection_screen import ModeSelectionScreen
from ui.camp_selection_screen import CampSelectionScreen
from ui.rules_screen import RulesScreen
from ui.settings_screen import SettingsScreen
from ui.dialogs import StatisticsDialog
from lan.xhlan import SimpleAPI

# 初始化PyGame
pygame.init()
pygame.mixer.init()  # 初始化音频模块


def main():
    """主函数，处理游戏流程"""
    # 首先显示模式选择界面
    mode_screen = ModeSelectionScreen()
    game_mode = mode_screen.run()

    # 运行游戏循环
    while True:
        settings_result = None  # 初始化settings_result变量

        if game_mode == "settings":  # 如果选择了设置界面
            settings_screen = SettingsScreen()
            settings_result = settings_screen.run()

            if settings_result == "back":
                # 返回到模式选择界面
                mode_screen = ModeSelectionScreen()
                game_mode = mode_screen.run()
                continue
            else:
                # 保存设置并返回到模式选择界面
                # 这里可以保存设置到全局变量或文件
                mode_screen = ModeSelectionScreen()
                game_mode = mode_screen.run()
                continue

        if game_mode == "rules":  # 如果选择了规则界面
            rules_viewer = RulesScreen()
            rules_viewer.run()
            # 返回到模式选择界面
            mode_screen = ModeSelectionScreen()
            game_mode = mode_screen.run()
            continue

        if game_mode == "stats":  # 如果选择了统计界面
            # 创建并显示统计对话框
            stats_dialog = StatisticsDialog()

            # 获取当前显示表面以获取屏幕尺寸
            current_screen = pygame.display.get_surface()
            if current_screen is None:
                # 如果没有当前表面，创建一个
                current_screen = pygame.display.set_mode((1200, 900), pygame.RESIZABLE)

            clock = pygame.time.Clock()

            running = True
            while running:
                mouse_pos = pygame.mouse.get_pos()

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False

                    result = stats_dialog.handle_event(event, mouse_pos)
                    if result == "close":
                        running = False
                    elif result == "reset":
                        # 重置统计数据
                        from program.controllers.statistics_manager import statistics_manager
                        statistics_manager.reset_statistics()
                        # 重新创建对话框以更新显示
                        stats_dialog = StatisticsDialog()

                # 绘制统计对话框
                stats_dialog.draw(current_screen)
                pygame.display.flip()
                clock.tick(60)

            # 返回到模式选择界面
            mode_screen = ModeSelectionScreen()
            game_mode = mode_screen.run()
            continue

        # 处理网络对战模式
        if game_mode == "network":
            network_screen = NetworkConnectScreen()
            network_choice, ip_address = network_screen.run()

            if network_choice == "back":
                # 返回到模式选择界面
                mode_screen = ModeSelectionScreen()
                game_mode = mode_screen.run()
                continue
            elif network_choice == "host":
                # 初始化网络API
                SimpleAPI.init('SERVER')
                print("服务器模式：等待客户端连接...")
                # 创建网络对战游戏，作为主机
                game = NetworkChessGame(is_host=True)
                game.run()
            elif network_choice == "join":
                # 初始化网络API
                SimpleAPI.init('CLIENT')
                # 检查连接状态
                time.sleep(1)  # 等待连接建立
                if not SimpleAPI.is_connected():
                    print(f"无法连接到服务器 {ip_address if ip_address else '127.0.0.1'}，请确保服务器正在运行")
                    # 显示错误信息并返回主菜单
                    import tkinter as tk
                    from tkinter import messagebox
                    root = tk.Tk()
                    root.withdraw()  # 隐藏主窗口
                    messagebox.showerror("连接错误",
                                         f"无法连接到服务器 {ip_address if ip_address else '127.0.0.1'}\n请确保服务器正在运行")
                    root.destroy()
                    # 返回到模式选择界面
                    mode_screen = ModeSelectionScreen()
                    game_mode = mode_screen.run()
                    continue
                # 加入网络对战游戏
                game = NetworkChessGame(is_host=False)
                game.run()

            # 如果网络对战结束，返回模式选择
            mode_screen = ModeSelectionScreen()
            game_mode = mode_screen.run()
            continue

        # 检查是否为传统象棋模式
        # 如果游戏模式不是network, MODE_PVC, MODE_PVP，也不是特殊菜单选项，
        # 则假定已在模式选择界面处理了传统象棋模式
        
        # 如果是人机对战模式，显示阵营选择界面
        if game_mode == MODE_PVC:
            camp_screen = CampSelectionScreen()
            camp_selection_result = camp_screen.run()
            
            # 如果阵营选择界面返回None（表示用户点击了返回按钮），则返回到模式选择界面
            if camp_selection_result is None:
                mode_screen = ModeSelectionScreen()
                game_mode = mode_screen.run()
                continue

            player_camp = camp_selection_result["camp"]
            ai_difficulty_info = camp_selection_result["ai_difficulty"]
        else:
            player_camp = CAMP_RED  # 默认玩家执红
            ai_difficulty_info = None

        # 根据选择的模式和阵营创建游戏，传递设置
        game = ChessGame(game_mode, player_camp,
                         game_settings=settings_result if isinstance(settings_result, dict) else None)
                         
        # 如果是人机模式，设置AI信息
        if game_mode == MODE_PVC and ai_difficulty_info:
            game.game_screen.set_ai_info(ai_difficulty_info)
        result = game.run()

        # 如果返回到菜单，重新显示模式选择界面
        if result == "back_to_menu":
            mode_screen = ModeSelectionScreen()
            game_mode = mode_screen.run()


if __name__ == "__main__":
    main()
