"""
仅服务器模式 - 用于单机测试联机功能
"""
import pygame
from program.network_game import NetworkChessGame
from program.xhlan import SimpleAPI, XiangqiNetworkGame
import time

def run_server():
    print("启动匈汉象棋服务器...")
    print("请在另一个终端窗口中运行客户端：python client_only.py")
    
    # 初始化网络API作为服务器
    SimpleAPI.init('SERVER')
    print("服务器已启动，等待客户端连接...")
    print(f"服务器地址: 127.0.0.1:{10087}")
    
    # 等待一段时间让服务器完全启动
    time.sleep(2)
    
    # 等待客户端连接（显示简单界面）
    pygame.init()
    screen = pygame.display.set_mode((600, 400))
    pygame.display.set_caption("匈汉象棋服务器 - 等待连接")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)
    
    running = True
    conn_attempts = 0
    while running and not (hasattr(SimpleAPI.instance, 'connection') and SimpleAPI.instance.connection is not None):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        screen.fill((240, 240, 240))
        
        # 显示连接状态
        if hasattr(SimpleAPI.instance, 'connection') and SimpleAPI.instance.connection is not None:
            text = font.render("客户端已连接！", True, (0, 128, 0))
        else:
            text = font.render("等待客户端连接...", True, (0, 0, 0))
            conn_attempts += 1
        
        screen.blit(text, (150, 150))
        
        # 显示连接信息
        info_font = pygame.font.SysFont(None, 24)
        info_text = info_font.render(f"服务器地址: 127.0.0.1:{10087}", True, (0, 0, 0))
        screen.blit(info_text, (150, 200))
        
        info_text2 = info_font.render("请运行: python client_only.py", True, (0, 0, 0))
        screen.blit(info_text2, (150, 230))
        
        # 显示额外的提示信息
        info_text3 = info_font.render("如果连接失败，请检查防火墙设置", True, (255, 0, 0))
        screen.blit(info_text3, (50, 260))
        
        pygame.display.flip()
        clock.tick(60)
    
    if not running:
        pygame.quit()
        return
    
    print("客户端已连接，启动游戏...")
    # 这里可以启动游戏，但现在我们只显示连接状态
    game_text = font.render("客户端已连接，游戏即将开始...", True, (0, 128, 0))
    screen.blit(game_text, (50, 260))
    pygame.display.flip()
    
    # 等待一小段时间让客户端准备好
    time.sleep(2)
    
    # 启动游戏
    try:
        game = NetworkChessGame(is_host=True)
        game.run()
    except Exception as e:
        print(f"游戏运行出错: {e}")
    
    pygame.quit()

if __name__ == "__main__":
    run_server()