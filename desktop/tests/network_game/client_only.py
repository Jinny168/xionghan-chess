"""
仅客户端模式 - 用于单机测试联机功能
"""
import time
import sys
import os
import pygame

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入所需的模块
try:
    from desktop.lan.network_game import NetworkChessGame
    from desktop.lan.xhlan import SimpleAPI
    from desktop.controllers.game_config_manager import ADDRESS, PORT
except ImportError as e:
    print(f"导入错误: {e}")
    # 尝试直接从相对路径导入
    sys.path.append(os.path.join(project_root))
    from desktop.lan.network_game import NetworkChessGame
    from desktop.lan.xhlan import SimpleAPI
    from desktop.controllers.game_config_manager import ADDRESS, PORT


def run_client():
    print("正在连接到服务器...")
    
    # 等待服务器启动
    print("等待服务器准备就绪...")
    time.sleep(3)
    
    # 初始化网络API作为客户端
    # 在这里初始化SimpleAPI，但注意不要与游戏实例中的初始化冲突
    SimpleAPI.init('CLIENT', '127.0.0.1')  # 传递服务器地址
    print("客户端模式初始化")
    
    # 初始化pygame用于显示连接界面
    pygame.init()
    screen = pygame.display.set_mode((600, 400))
    pygame.display.set_caption("匈汉象棋客户端 - 正在连接")
    clock = pygame.time.Clock()
    
    # 设置字体
    title_font = pygame.font.SysFont(None, 48)
    font = pygame.font.SysFont(None, 32)
    info_font = pygame.font.SysFont(None, 24)
    
    # 等待连接建立
    max_wait_time = 15  # 增加等待时间到15秒
    wait_time = 0
    
    running = True
    connecting = True
    
    while running and connecting and wait_time < max_wait_time:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                connecting = False
        
        # 检查连接状态
        connected = SimpleAPI.is_connected()
        
        # 绘制背景渐变色
        for y in range(400):
            color_value = 50 + int(50 * (y / 400))  # 从深蓝到浅蓝的渐变
            pygame.draw.line(screen, (color_value, 100, color_value), (0, y), (600, y))
        
        # 绘制标题
        title_text = title_font.render("匈汉象棋客户端", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(300, 100))
        screen.blit(title_text, title_rect)
        
        # 绘制装饰边框
        pygame.draw.rect(screen, (255, 215, 0), (50, 140, 500, 120), 3, border_radius=15)
        
        # 显示连接状态
        if connected:
            status_text = font.render("✅ 成功连接到服务器！", True, (0, 255, 0))
            connecting = False  # 连接成功，停止连接循环
        else:
            status_text = font.render(f"⏳ 连接中... ({wait_time}/{max_wait_time})", True, (255, 255, 0))
            wait_time += 1
        
        status_rect = status_text.get_rect(center=(300, 180))
        screen.blit(status_text, status_rect)
        
        # 显示连接信息
        info_text = info_font.render(f"🌐 服务器地址: 127.0.0.1:{PORT}", True, (200, 200, 255))
        screen.blit(info_text, (180, 230))
        
        info_text2 = info_font.render("📋 等待连接完成...", True, (200, 200, 255))
        screen.blit(info_text2, (180, 260))
        
        # 显示额外的提示信息
        info_text3 = info_font.render("⚠️ 如果连接失败，请检查服务器状态", True, (255, 100, 100))
        screen.blit(info_text3, (120, 300))
        
        pygame.display.flip()
        clock.tick(60)
        time.sleep(1)  # 等待1秒再检查连接状态
    
    if not running:
        pygame.quit()
        return
    
    if not SimpleAPI.is_connected():
        print("无法连接到服务器，请确保服务器正在运行")
        
        # 显示连接失败的信息
        failed_text = font.render("❌ 连接服务器失败", True, (255, 0, 0))
        screen.blit(failed_text, (150, 340))
        pygame.display.flip()
        time.sleep(3)
        pygame.quit()
        return
    
    print("成功连接到服务器，启动游戏...")
    
    # 显示连接成功的信息
    success_text = font.render("成功连接到服务器，游戏即将开始...", True, (0, 255, 0))
    screen.blit(success_text, (50, 340))
    pygame.display.flip()
    time.sleep(2)
    
    # 关闭临时的连接等待窗口
    pygame.quit()
    
    # 创建客户端游戏实例
    # 在创建游戏实例之前，XiangqiNetworkGame.game_instance应该已经被设置
    game = NetworkChessGame(is_host=False)
    game.run()

if __name__ == "__main__":
    run_client()
