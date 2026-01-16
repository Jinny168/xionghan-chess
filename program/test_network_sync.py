"""
匈汉象棋网络对战同步功能测试
"""
import pygame
import threading
import time
import sys

from program.network_game import NetworkChessGame
from program.xhlan import SimpleAPI

def run_server():
    """运行服务器端（主机）"""
    print("启动匈汉象棋服务器...")
    # 初始化API作为服务器
    SimpleAPI.init('SERVER', None)
    
    # 创建网络游戏实例（主机）
    game = NetworkChessGame(is_host=True)
    
    # 等待客户端连接
    print("等待客户端连接...")
    connected = False
    for i in range(15):  # 最多等待15次
        if SimpleAPI.is_connected():
            connected = True
            break
        print(f"等待连接... ({i+1}/15)")
        time.sleep(1)
    
    if not connected:
        print("连接超时")
        return
    
    print("客户端已连接，启动游戏...")
    try:
        game.run()
    except Exception as e:
        print(f"服务器游戏运行出错: {e}")
        import traceback
        traceback.print_exc()


def run_client():
    """运行客户端"""
    print("启动匈汉象棋客户端...")
    # 初始化API作为客户端
    SimpleAPI.init('CLIENT', None, "127.0.0.1")
    
    # 等待连接建立
    print("正在连接到服务器...")
    connected = False
    for i in range(15):  # 最多等待15次
        if hasattr(SimpleAPI.instance, 'connected') and SimpleAPI.instance.connected:
            connected = True
            break
        print(f"等待服务器准备就绪... ({i+1}/15)")
        time.sleep(1)
    
    if not connected:
        print("客户端连接失败")
        return
    
    print("成功连接到服务器，启动游戏...")
    # 创建网络游戏实例（客户端）
    game = NetworkChessGame(is_host=False)
    try:
        game.run()
    except Exception as e:
        print(f"客户端游戏运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("匈汉象棋网络对战同步测试")
    print("即将启动服务器和客户端...")
    print("请先关闭任何已运行的游戏实例")
    input("按回车键开始测试...")

    # 启动服务器和客户端线程
    server_thread = threading.Thread(target=run_server, daemon=True)
    client_thread = threading.Thread(target=run_client, daemon=True)

    server_thread.start()
    time.sleep(2)  # 稍微延迟启动客户端
    client_thread.start()

    # 等待线程完成
    server_thread.join()
    client_thread.join()

    print("测试完成")