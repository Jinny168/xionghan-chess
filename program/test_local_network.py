"""
单机网络对战测试脚本
此脚本可以在单台计算机上启动服务器和客户端进行测试
"""
import subprocess
import sys
import time
import threading
import os

def run_server():
    """运行服务器进程"""
    cmd = [sys.executable, "server_only.py"]
    subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))

def run_client():
    """运行客户端进程"""
    time.sleep(3)  # 等待服务器启动
    cmd = [sys.executable, "client_only.py"]
    subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))

def main():
    print("匈汉象棋单机网络对战测试")
    print("即将启动服务器和客户端...")
    print("请先关闭任何已运行的游戏实例")
    input("按回车键开始测试...")

    # 创建线程来运行服务器和客户端
    server_thread = threading.Thread(target=run_server)
    client_thread = threading.Thread(target=run_client)

    # 启动服务器线程
    server_thread.start()
    
    # 稍等一下再启动客户端线程
    time.sleep(2)
    client_thread.start()

    # 等待两个线程完成
    server_thread.join()
    client_thread.join()

    print("测试完成")

if __name__ == "__main__":
    main()