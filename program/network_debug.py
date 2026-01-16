"""
网络调试工具 - 帮助诊断网络连接问题
"""
import socket
import threading
import time

def check_port_available(port):
    """检查端口是否可用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return True
        except OSError:
            return False

def start_simple_server():
    """启动一个简单的服务器用于测试"""
    print("启动测试服务器...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', 10087))
        server_socket.listen(1)
        print("服务器正在监听 0.0.0.0:10087")
        
        try:
            conn, addr = server_socket.accept()
            print(f"客户端已连接: {addr}")
            with conn:
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    print(f"收到数据: {data.decode()}")
                    conn.sendall(b"ACK")
        except Exception as e:
            print(f"服务器错误: {e}")

def test_connection():
    """测试连接"""
    time.sleep(2)  # 等待服务器启动
    print("尝试连接到服务器...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('127.0.0.1', 10087))
            s.sendall(b"Hello Server")
            data = s.recv(1024)
            print(f"从服务器收到: {data.decode()}")
            print("连接测试成功!")
    except Exception as e:
        print(f"连接测试失败: {e}")

if __name__ == "__main__":
    print("网络连接诊断工具")
    print(f"端口 10087 可用: {check_port_available(10087)}")
    
    server_thread = threading.Thread(target=start_simple_server)
    client_thread = threading.Thread(target=test_connection)
    
    server_thread.start()
    client_thread.start()
    
    client_thread.join()
    server_thread.join()