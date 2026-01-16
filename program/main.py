import pygame
import time

from program.config.config import MODE_PVC, CAMP_RED
from program.game import ChessGame
from program.network_game import NetworkChessGame
from program.network_connect import NetworkConnectScreen
from program.ui.menu_screens import ModeSelectionScreen, RulesScreen, CampSelectionScreen
from program.config.settings import SettingsScreen
from program.xhlan import SimpleAPI

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
            rules_screen = RulesScreen()
            rules_screen.run()
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
                result = game.run()
            elif network_choice == "join":
                # 初始化网络API
                SimpleAPI.init('CLIENT', server_addr=ip_address if ip_address else "127.0.0.1")
                # 检查连接状态
                time.sleep(1)  # 等待连接建立
                if not SimpleAPI.is_connected():
                    print(f"无法连接到服务器 {ip_address if ip_address else '127.0.0.1'}，请确保服务器正在运行")
                    # 显示错误信息并返回主菜单
                    import tkinter as tk
                    from tkinter import messagebox
                    root = tk.Tk()
                    root.withdraw()  # 隐藏主窗口
                    messagebox.showerror("连接错误", f"无法连接到服务器 {ip_address if ip_address else '127.0.0.1'}\n请确保服务器正在运行")
                    root.destroy()
                    # 返回到模式选择界面
                    mode_screen = ModeSelectionScreen()
                    game_mode = mode_screen.run()
                    continue
                # 加入网络对战游戏
                game = NetworkChessGame(is_host=False)
                result = game.run()
            
            # 如果网络对战结束，返回模式选择
            mode_screen = ModeSelectionScreen()
            game_mode = mode_screen.run()
            continue
        
        player_camp = CAMP_RED  # 默认玩家执红
        
        # 如果是人机对战模式，显示阵营选择界面
        if game_mode == MODE_PVC:
            camp_screen = CampSelectionScreen()
            player_camp = camp_screen.run()
        
        # 根据选择的模式和阵营创建游戏，传递设置
        game = ChessGame(game_mode, player_camp, game_settings=settings_result if isinstance(settings_result, dict) else None)
        result = game.run()
        
        # 如果返回到菜单，重新显示模式选择界面
        if result == "back_to_menu":
            mode_screen = ModeSelectionScreen()
            game_mode = mode_screen.run()

if __name__ == "__main__":
    main()