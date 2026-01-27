"""
仅客户端模式 - 用于单机测试联机功能
"""
import time
import sys
import os

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入所需的模块
try:
    from program.lan.network_game import NetworkChessGame
    from program.lan.xhlan import SimpleAPI
    from program.config.config import ADDRESS, PORT
except ImportError as e:
    print(f"导入错误: {e}")
    # 尝试直接从相对路径导入
    sys.path.append(os.path.join(project_root))
    from program.lan.network_game import NetworkChessGame
    from program.lan.xhlan import SimpleAPI
    from program.config.config import ADDRESS, PORT


def run_client():
    print("正在连接到服务器...")
    
    # 等待服务器启动
    print("等待服务器准备就绪...")
    time.sleep(3)
    
    # 初始化网络API作为客户端
    # 在这里初始化SimpleAPI，但注意不要与游戏实例中的初始化冲突
    SimpleAPI.init('CLIENT', '127.0.0.1')  # 传递服务器地址
    print("客户端模式初始化")
    
    # 等待连接建立
    max_wait_time = 15  # 增加等待时间到15秒
    wait_time = 0
    while not SimpleAPI.is_connected() and wait_time < max_wait_time:
        time.sleep(1)
        wait_time += 1
        print(f"等待连接... ({wait_time}/{max_wait_time})")
    
    if not SimpleAPI.is_connected():
        print("无法连接到服务器，请确保服务器正在运行")
        return
    
    print("成功连接到服务器，启动游戏...")
    
    # 创建客户端游戏实例
    # 在创建游戏实例之前，XiangqiNetworkGame.game_instance应该已经被设置
    game = NetworkChessGame(is_host=False)
    game.run()

if __name__ == "__main__":
    run_client()