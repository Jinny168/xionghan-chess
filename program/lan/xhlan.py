"""
匈汉象棋局域网功能
"""

import json
import time
from socket import socket
from threading import Thread

from program.config.config import ADDRESS, PORT, BUFFER_SIZE


class _Base:
    """ 基本功能 """

    def __init__(self) -> None:
        self.socket = socket()  # 套接字
        self.connection: socket | None = None  # 连接对象
        self.flag = False

    def send(self, **kw) -> int:
        """ 发送消息 """
        try:
            # 使用JSON序列化确保数据格式一致
            message = json.dumps(kw)
            if self.connection:
                return self.connection.send(message.encode('utf-8'))
            return self.socket.send(message.encode('utf-8'))
        except ConnectionResetError:
            pass
        except OSError:
            pass

    def recv(self, __bufsize: int = BUFFER_SIZE) -> dict:
        """ 接收消息 """
        try:
            if self.connection:
                data = self.connection.recv(__bufsize).decode('utf-8')
                return json.loads(data)
            data = self.socket.recv(__bufsize).decode('utf-8')
            return json.loads(data)
        except ConnectionResetError:
            pass
        except json.JSONDecodeError:
            pass
        except OSError:
            pass
        except UnicodeDecodeError:
            pass
        return {}

    def close(self) -> None:
        """ 关闭联机功能 """
        self.flag = True
        if self.socket:
            try:
                self.socket.close()
            except OSError:
                pass


class Server(_Base):
    """ 服务端 """

    def __init__(self) -> None:
        _Base.__init__(self)
        # 绑定到所有可用接口
        self.client_address = None
        self.bound = False
        try:
            # 绑定到所有接口，这样客户端可以用127.0.0.1连接
            self.socket.bind(('0.0.0.0', PORT))
            self.socket.listen(1)
            self.bound = True
            print(f"服务器正在监听 {ADDRESS}:{PORT}")
            # 启动接受连接的线程
            self.accept_thread = Thread(target=self.accept, daemon=True)
            self.accept_thread.start()
        except Exception as e:
            print(f"服务器绑定失败: {e}")

    def accept(self) -> None:
        try:
            # 设置超时以避免无限阻塞
            self.socket.settimeout(120)  # 120秒超时
            self.connection, self.client_address = self.socket.accept()
            print(f"客户端已连接: {self.client_address}")
        except Exception as e:
            print(f"接受连接时出错: {e}")
            self.flag = True

    def identify(self) -> None:
        """ 身份确认 """
        if self.connection:
            self.send(msg='OK')
            try:
                response = self.recv()
                if 'msg' in response:
                    # 设置游戏模式为局域网模式
                    XiangqiNetworkGame.set_network_mode('SERVER', self)
            except Exception as e:
                print(f"身份确认失败: {e}")


class Client(_Base):
    """ 客户端 """

    def __init__(self, server_addr: str = "127.0.0.1") -> None:
        _Base.__init__(self)
        self.server_addr = server_addr
        self.connected = False  # 添加连接状态标志
        self.connect_thread = Thread(target=self.connect_client, daemon=True)
        self.connect_thread.start()

    def connect_client(self) -> None:
        """ 连接到服务器 """
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries and not self.connected:
            try:
                # 设置超时以避免无限阻塞
                self.socket.settimeout(10)  # 10秒超时
                self.socket.connect((self.server_addr, PORT))
                self.connected = True
                print(f"成功连接到服务器 {self.server_addr}:{PORT}")
                break
            except Exception as e:
                retry_count += 1
                print(f"连接服务器失败 (尝试 {retry_count}/{max_retries}): {e}")
                time.sleep(2)  # 等待2秒后重试
        
        if not self.connected:
            print(f"无法连接到服务器 {self.server_addr}:{PORT}，请确保服务器正在运行")

    def identify(self) -> None:
        """ 身份确认 """
        try:
            response = self.recv()
            if response and 'msg' in response and response['msg'] == 'OK':
                # 获取当前设置参数
                code = [1, 0, 0, 0, 0]  # 示例设置: [先手, 经典模式, 巡登场等]
                
                self.send(msg=''.join(map(str, code)))
                XiangqiNetworkGame.set_network_mode('CLIENT', self)
        except Exception as e:
            print(f"身份确认失败: {e}")


class SimpleAPI:
    """ 简化的API接口，不依赖tkintertools """

    instance: Server | Client | None = None

    @classmethod
    def init(cls, role: str, connection_obj=None) -> None:
        if role == 'SERVER':
            cls.instance = Server()
        else:
            cls.instance = Client(connection_obj)

    @classmethod
    def send(cls, **kw) -> int:
        """ 发送信息 """
        if cls.instance:
            return cls.instance.send(**kw)
        return 0

    @classmethod
    def recv(cls, __bufsize: int = BUFFER_SIZE) -> dict:
        """ 接收消息 """
        if cls.instance:
            return cls.instance.recv(__bufsize)
        return {}

    @classmethod
    def close(cls) -> None:
        """ 关闭套接字 """
        if cls.instance:
            cls.instance.close()
        
    @classmethod
    def is_server(cls) -> bool:
        """ 判断是否为服务器端 """
        return isinstance(cls.instance, Server) if cls.instance else False

    @classmethod
    def is_connected(cls) -> bool:
        """ 检查是否已连接 """
        if isinstance(cls.instance, Client):
            return cls.instance.connected
        return cls.instance is not None  # 服务端认为总是连接的


class XiangqiNetworkGame:
    """ 匈汉象棋网络对战功能 """
    
    # 添加类级别的静态变量
    game_instance = None
    
    def __init__(self, game_instance):
        # 设置静态变量，让类方法可以访问游戏实例
        XiangqiNetworkGame.game_instance = game_instance
        self.is_host = False  # 是否为主机（服务器端）
        self.network_enabled = False
        self.opponent_ready = False
        self.api_instance = None
        self.game_started = False
        # 添加状态跟踪，避免重复处理
        self.has_processed_undo_request = False
        self.has_processed_restart_request = False

    @classmethod
    def set_network_mode(cls, role: str, api_instance):
        """ 设置网络对战模式 """
        cls.api_instance = api_instance
        cls.is_host = role == 'SERVER'
        cls.network_enabled = True
        
        # 启动网络监听线程
        thread = Thread(target=cls._listen_for_moves, daemon=True)
        thread.start()
        
        # 根据角色设置玩家阵营
        if cls.is_host:
            # 作为主机，通常先手
            cls.local_player_color = "red"
            cls.remote_player_color = "black"
        else:
            # 作为客户端，通常后手
            cls.local_player_color = "black"
            cls.remote_player_color = "red"
            
        # 发送游戏开始信号
        cls.send_game_start()

    @classmethod
    def _listen_for_moves(cls):
        """ 监听来自对手的移动信息 """
        print(f"开始监听对手移动，角色: {'服务器' if cls.is_host else '客户端'}")
        while cls.network_enabled:
            try:
                if cls.api_instance:
                    data = cls.api_instance.recv()
                    if data and 'move' in data:
                        # 接收到对手的移动信息
                        from_row, from_col, to_row, to_col = data['move']
                        print(f"收到对手移动: {from_row},{from_col} -> {to_row},{to_col}")
                        cls.execute_remote_move(from_row, from_col, to_row, to_col)
                    elif data and 'ready' in data:
                        cls.opponent_ready = True
                    elif data and 'resign' in data:
                        # 对手认输
                        cls.handle_opponent_resign()
                    elif data and 'game_start' in data:
                        # 游戏开始信号
                        cls.game_started = True
                    elif data and 'chat' in data:
                        # 聊天消息
                        cls.handle_chat_message(data['chat'])
                    elif data and 'undo_request' in data:
                        # 对手请求悔棋
                        cls.handle_undo_request()
                    elif data and 'undo_response' in data:
                        # 对手对悔棋请求的回复
                        cls.handle_undo_response(data['undo_response'])
                    elif data and 'restart_request' in data:
                        # 对手请求重新开始
                        cls.handle_restart_request()
                    elif data and 'restart_response' in data:
                        # 对手对重新开始请求的回复
                        cls.handle_restart_response(data['restart_response'])
                    elif data and 'leave_game' in data:
                        # 对手离开游戏
                        cls.handle_opponent_leave()
                    elif data and 'game_restart_confirmed' in data:
                        # 游戏重新开始确认
                        cls.handle_game_restart_confirmation()
            except Exception as e:
                # 添加短暂延时以避免过于频繁的异常处理
                print(f"监听移动时出错: {e}")
                time.sleep(0.1)
                continue

    @classmethod
    def execute_remote_move(cls, from_row, from_col, to_row, to_col):
        """ 执行远程玩家的移动 """
        # 这里需要更新游戏状态，模拟对手的移动
        if cls.game_instance:
            # 直接调用游戏实例的方法来处理对手的移动
            print(f"执行远程移动: {from_row},{from_col} -> {to_row},{to_col}")
            cls.game_instance.receive_network_move(from_row, from_col, to_row, to_col)
        else:
            print("[DEBUG] 网络游戏实例未设置")

    @classmethod
    def send_move(cls, from_row, from_col, to_row, to_col):
        """ 发送本地玩家的移动到对手 """
        if cls.network_enabled and cls.api_instance:
            try:
                print(f"发送本地移动: {from_row},{from_col} -> {to_row},{to_col}")
                cls.api_instance.send(move=(from_row, from_col, to_row, to_col))
            except Exception as e:
                print(f"发送移动信息失败: {e}")

    @classmethod
    def handle_opponent_resign(cls):
        """ 处理对手认输 """
        print("对手认输，您获得胜利！")
        # 在实际游戏中，这里会更新游戏状态为胜利
        if cls.game_instance:
            cls.game_instance.handle_opponent_win()

    @classmethod
    def send_ready(cls):
        """ 发送准备就绪信号 """
        if cls.network_enabled and cls.api_instance:
            cls.api_instance.send(ready=True)

    @classmethod
    def send_resign(cls):
        """ 发送认输信号 """
        if cls.network_enabled and cls.api_instance:
            cls.api_instance.send(resign=True)
            cls.network_enabled = False

    @classmethod
    def send_game_start(cls):
        """ 发送游戏开始信号 """
        if cls.network_enabled and cls.api_instance:
            cls.api_instance.send(game_start=True)
    
    @classmethod
    def send_undo_request(cls):
        """ 发送悔棋请求 """
        if cls.network_enabled and cls.api_instance:
            cls.api_instance.send(undo_request=True)
    
    @classmethod
    def send_undo_response(cls, accepted):
        """ 发送悔棋请求的回复 """
        if cls.network_enabled and cls.api_instance:
            cls.api_instance.send(undo_response=accepted)
    
    @classmethod
    def send_restart_request(cls):
        """ 发送重新开始请求 """
        if cls.network_enabled and cls.api_instance:
            cls.api_instance.send(restart_request=True)
    
    @classmethod
    def send_restart_response(cls, accepted):
        """ 发送重新开始请求的回复 """
        if cls.network_enabled and cls.api_instance:
            cls.api_instance.send(restart_response=accepted)
    
    @classmethod
    def handle_undo_request(cls):
        """ 处理对手的悔棋请求 """
        print("收到对手的悔棋请求")
        # 在实际游戏中，这里会询问本地玩家是否同意悔棋
        if cls.game_instance:
            # 显示一个确认对话框询问本地玩家是否同意悔棋
            cls.game_instance.request_undo_confirmation()
    
    @classmethod
    def handle_undo_response(cls, accepted):
        """ 处理对手对悔棋请求的回复 """
        print(f"对手对悔棋请求的回复: {'同意' if accepted else '拒绝'}")
        if cls.game_instance:
            cls.game_instance.handle_undo_response(accepted)
    
    @classmethod
    def handle_restart_request(cls):
        """ 处理对手的重新开始请求 """
        print("收到对手的重新开始请求")
        # 在实际游戏中，这里会询问本地玩家是否同意重新开始
        if cls.game_instance:
            # 显示一个确认对话框询问本地玩家是否同意重新开始
            cls.game_instance.request_restart_confirmation()
    
    @classmethod
    def handle_restart_response(cls, accepted):
        """ 处理对手对重新开始请求的回复 """
        print(f"对手对重新开始请求的回复: {'同意' if accepted else '拒绝'}")
        if accepted:
            # 如果对手同意重新开始，发送确认信号，确保双方状态同步
            cls.send_game_restart_confirmation()
        if cls.game_instance:
            cls.game_instance.handle_restart_response(accepted)
    
    @classmethod
    def send_game_restart_confirmation(cls):
        """ 发送游戏重新开始确认信号，确保双方状态同步 """
        if cls.network_enabled and cls.api_instance:
            cls.api_instance.send(game_restart_confirmed=True)
    
    @classmethod
    def handle_game_restart_confirmation(cls):
        """ 处理游戏重新开始确认信号 """
        print("收到游戏重新开始确认，确保状态同步")
        if cls.game_instance:
            # 确保游戏状态完全同步
            cls.game_instance.on_game_restarted()
    
    @classmethod
    def send_leave_game(cls):
        """ 发送离开游戏信号 """
        if cls.network_enabled and cls.api_instance:
            cls.api_instance.send(leave_game=True)
            cls.network_enabled = False
    
    @classmethod
    def handle_opponent_leave(cls):
        """ 处理对手离开游戏 """
        print("对手离开了游戏")
        if cls.game_instance:
            cls.game_instance.handle_opponent_leave()

    @classmethod
    def handle_chat_message(cls, message):
        """ 处理聊天消息 """
        print(f"收到聊天消息: {message}")
        # 在游戏中显示聊天消息
        if cls.game_instance:
            cls.game_instance.display_chat_message(message)
