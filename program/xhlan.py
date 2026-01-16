"""
匈汉象棋局域网功能
"""

import time
from socket import socket
from threading import Thread

# import tkintertools as tkt  # 移除tkintertools依赖
from program.network_constants import ADDRESS, PORT, BUFFER_SIZE


class _Base:
    """ 基本功能 """

    def __init__(self, toplevel: object) -> None:  # 修改参数类型注释
        self.socket = socket()  # 套接字
        self.connection: socket | None = None  # 连接对象
        self.flag = False

    def send(self, **kw) -> int:
        """ 发送消息 """
        try:
            if self.connection:
                return self.connection.send(kw.__repr__().encode('utf-8'))
            return self.socket.send(kw.__repr__().encode('utf-8'))
        except ConnectionResetError:
            pass
        except Exception:
            pass

    def recv(self, __bufsize: int = BUFFER_SIZE) -> dict:
        """ 接收消息 """
        try:
            if self.connection:
                return eval(self.connection.recv(__bufsize).decode('utf-8'))
            return eval(self.socket.recv(__bufsize).decode('utf-8'))
        except ConnectionResetError:
            pass
        except Exception:
            pass

    def close(self) -> None:
        """ 关闭联机功能 """
        self.flag = True
        if self.socket:
            try:
                self.socket.close()
            except:
                pass


class Server(_Base):
    """ 服务端 """

    def __init__(self, toplevel: object) -> None:
        _Base.__init__(self, toplevel)
        # 绑定到所有可用接口
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
                    code = response['msg']
                    # 设置游戏模式为局域网模式
                    XiangqiNetworkGame.set_network_mode('SERVER', self)
            except Exception as e:
                print(f"身份确认失败: {e}")


class Client(_Base):
    """ 客户端 """

    def __init__(self, toplevel: object, server_addr: str = "127.0.0.1") -> None:
        _Base.__init__(self, toplevel)
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
    def init(cls, role: str, connection_obj=None, server_addr: str = "127.0.0.1") -> None:
        if role == 'SERVER':
            cls.instance = Server(connection_obj)
        else:
            cls.instance = Client(connection_obj, server_addr)

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
    
    def __init__(self, game_instance):
        self.game_instance = game_instance
        self.is_host = False  # 是否为主机（服务器端）
        self.network_enabled = False
        self.opponent_ready = False
        self.api_instance = None
        self.game_started = False

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
        while cls.network_enabled:
            try:
                if cls.api_instance:
                    data = cls.api_instance.recv()
                    if data and 'move' in data:
                        # 接收到对手的移动信息
                        from_row, from_col, to_row, to_col = data['move']
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
            except Exception as e:
                # 添加短暂延时以避免过于频繁的异常处理
                time.sleep(0.1)
                continue

    @classmethod
    def execute_remote_move(cls, from_row, from_col, to_row, to_col):
        """ 执行远程玩家的移动 """
        # 这里需要更新游戏状态，模拟对手的移动
        if hasattr(cls, 'game_instance') and cls.game_instance:
            game_state = cls.game_instance.game_state
        else:
            from program.core.game_state import GameState
            game_state = GameState()
        
        # 模拟移动棋子
        success = game_state.move_piece(from_row, from_col, to_row, to_col)
        if success:
            print(f"[DEBUG] 远程移动成功: {from_row},{from_col} -> {to_row},{to_col}")
            # 更新游戏界面
            if hasattr(cls, 'game_instance') and cls.game_instance:
                # 更新棋盘显示
                cls.game_instance.receive_network_move(from_row, from_col, to_row, to_col)

    @classmethod
    def send_move(cls, from_row, from_col, to_row, to_col):
        """ 发送本地玩家的移动到对手 """
        if cls.network_enabled and cls.api_instance:
            try:
                cls.api_instance.send(move=(from_row, from_col, to_row, to_col))
            except Exception as e:
                print(f"发送移动信息失败: {e}")

    @classmethod
    def handle_opponent_resign(cls):
        """ 处理对手认输 """
        print("对手认输，您获得胜利！")
        # 在实际游戏中，这里会更新游戏状态为胜利
        if hasattr(cls, 'game_instance') and cls.game_instance:
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
    def handle_chat_message(cls, message):
        """ 处理聊天消息 """
        print(f"收到聊天消息: {message}")
        # 在游戏中显示聊天消息
        if hasattr(cls, 'game_instance') and cls.game_instance:
            cls.game_instance.display_chat_message(message)