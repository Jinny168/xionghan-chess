import pygame
import time
import sys
from typing import Optional, Tuple, Any

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
from program.ui.dialogs import ToastNotification

# 初始化PyGame
pygame.init()
pygame.mixer.init()  # 初始化音频模块

class GameStateManager:
    """游戏状态管理器"""
    def __init__(self):
        self.mode_screen = ModeSelectionScreen()
        self.current_mode = None
    
    def get_mode(self) -> str:
        """获取游戏模式"""
        self.current_mode = self.mode_screen.run()
        return self.current_mode
    
    def reset_mode_screen(self):
        """重置模式选择界面"""
        self.mode_screen = ModeSelectionScreen()

def show_error_message(title: str, message: str):
    """安全显示错误消息"""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        messagebox.showerror(title, message)
        root.destroy()
    except Exception as msg_error:
        print(f"显示错误消息失败: {msg_error}")
        print(f"{title}: {message}")

def handle_settings_flow(settings_screen: SettingsScreen, state_manager: GameStateManager) -> Tuple[str, Optional[Any]]:
    """处理设置流程"""
    settings_result = settings_screen.run()
    
    if settings_result == "back":
        state_manager.reset_mode_screen()
        return state_manager.get_mode(), None
    elif settings_result == "confirm":
        # 创建提示通知
        try:
            toast = ToastNotification("设置已生效", duration=2000)
            screen_surface = pygame.display.get_surface()
            if screen_surface:
                toast.prepare(screen_surface)
                toast.draw(screen_surface)
                pygame.display.flip()
                while not toast.is_expired():
                    pygame.time.wait(10)
        except Exception as toast_error:
            print(f"显示设置提示失败: {toast_error}")
        return "settings", None
    else:
        print(f"警告：未知的设置结果 {settings_result}，回退到模式选择")
        state_manager.reset_mode_screen()
        return state_manager.get_mode(), None

def handle_stats_flow(state_manager: GameStateManager) -> str:
    """处理统计界面流程"""
    stats_dialog = StatisticsDialog()
    current_screen = pygame.display.get_surface()
    
    if current_screen is None:
        # 使用配置管理器获取默认分辨率
        from controllers.game_config_manager import DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT
        current_screen = pygame.display.set_mode((DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT), pygame.RESIZABLE)
    
    clock = pygame.time.Clock()
    running = True
    
    try:
        while running:
            mouse_pos = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                
                result = stats_dialog.handle_event(event, mouse_pos)
                if result == "close":
                    running = False
                elif result == "reset":
                    try:
                        from program.controllers.statistics_manager import statistics_manager
                        statistics_manager.reset_statistics()
                        stats_dialog = StatisticsDialog()  # 重新创建对话框
                    except Exception as reset_error:
                        print(f"重置统计数据失败: {reset_error}")
            
            stats_dialog.draw(current_screen)
            pygame.display.flip()
            clock.tick(30)  # 降低刷新率以节省资源
    except Exception as stats_error:
        print(f"统计界面出现错误: {stats_error}")
    finally:
        # 确保返回到模式选择
        state_manager.reset_mode_screen()
        return state_manager.get_mode()

def handle_network_flow(network_screen: NetworkConnectScreen, state_manager: GameStateManager) -> str:
    """处理网络对战流程"""
    try:
        network_choice, ip_address = network_screen.run()
        
        if network_choice == "back":
            state_manager.reset_mode_screen()
            return state_manager.get_mode()
        elif network_choice == "host":
            SimpleAPI.init('SERVER')
            print("服务器模式：等待客户端连接...")
            game = NetworkChessGame(is_host=True)
            game.run()
        elif network_choice == "join":
            SimpleAPI.init('CLIENT')
            # 使用非阻塞方式检查连接
            start_time = time.time()
            while time.time() - start_time < 2.0:  # 2秒超时
                if SimpleAPI.is_connected():
                    break
                time.sleep(0.1)
            
            if not SimpleAPI.is_connected():
                error_msg = f"无法连接到服务器 {ip_address if ip_address else '127.0.0.1'}，请确保服务器正在运行"
                print(error_msg)
                show_error_message("连接错误", f"{error_msg}\n请确保服务器正在运行")
                state_manager.reset_mode_screen()
                return state_manager.get_mode()
            
            game = NetworkChessGame(is_host=False)
            game.run()
        
        # 网络对战结束
        state_manager.reset_mode_screen()
        return state_manager.get_mode()
        
    except Exception as network_error:
        print(f"网络对战出现错误: {network_error}")
        state_manager.reset_mode_screen()
        return state_manager.get_mode()

def handle_game_creation(game_mode: str, player_camp: str, ai_difficulty_info: Optional[dict], 
                        settings_result: Optional[Any]) -> Optional[str]:
    """处理游戏创建和运行"""
    try:
        game = ChessGame(game_mode, player_camp,
                        game_settings=settings_result if isinstance(settings_result, dict) else None)
        
        if game_mode == MODE_PVC and ai_difficulty_info:
            game.game_screen.set_ai_info(ai_difficulty_info)
        
        return game.run()
    except Exception as game_error:
        print(f"游戏运行出现错误: {game_error}")
        return None

def main():
    """主函数，处理游戏流程"""
    state_manager = GameStateManager()
    game_mode = state_manager.get_mode()

    # 运行游戏循环
    while True:
        settings_result = None

        try:
            if game_mode == "settings":
                settings_screen = SettingsScreen()
                game_mode, settings_result = handle_settings_flow(settings_screen, state_manager)
                if game_mode != "settings":
                    continue
                    
            elif game_mode == "rules":
                rules_viewer = RulesScreen()
                rules_viewer.run()
                state_manager.reset_mode_screen()
                game_mode = state_manager.get_mode()
                continue

            elif game_mode == "stats":
                game_mode = handle_stats_flow(state_manager)
                continue

            elif game_mode == "network":
                network_screen = NetworkConnectScreen()
                game_mode = handle_network_flow(network_screen, state_manager)
                continue

            # 处理游戏模式选择
            player_camp = CAMP_RED
            ai_difficulty_info = None
            
            if game_mode == MODE_PVC:
                camp_screen = CampSelectionScreen()
                camp_selection_result = camp_screen.run()
                
                if camp_selection_result is None:
                    state_manager.reset_mode_screen()
                    game_mode = state_manager.get_mode()
                    continue

                player_camp = camp_selection_result["camp"]
                ai_difficulty_info = camp_selection_result["ai_difficulty"]

            # 创建并运行游戏

            print(f"开始游戏模式: {game_mode}")
            result = handle_game_creation(game_mode, player_camp, ai_difficulty_info, settings_result)
            
            # 处理游戏返回结果
            if result == "back_to_menu":
                state_manager.reset_mode_screen()
                game_mode = state_manager.get_mode()
            elif result == "quit" or result is None:
                break
                
        except KeyboardInterrupt:
            print("用户中断程序")
            break
        except Exception as main_loop_error:
            print(f"主循环出现未预期错误: {main_loop_error}")
            # 安全回退
            state_manager.reset_mode_screen()
            game_mode = state_manager.get_mode()


if __name__ == "__main__":
    try:
        main()
    except Exception as startup_error:
        print(f"程序启动失败: {startup_error}")
        sys.exit(1)
    finally:
        # 确保清理资源
        try:
            pygame.quit()
        except Exception as cleanup_error:
            print(f"清理Pygame资源时出错: {cleanup_error}")
            pass
