"""
匈汉象棋网络对战常量
"""
from socket import gethostbyname, gethostname

# 当前地址
ADDRESS = gethostbyname(gethostname())
# 默认端口
PORT = 10087  # 使用不同的端口避免冲突

# 网络通信协议相关常量
MSG_TYPE_MOVE = "move"
MSG_TYPE_READY = "ready"
MSG_TYPE_RESIGN = "resign"
MSG_TYPE_GAME_START = "game_start"
MSG_TYPE_CHAT = "chat"

# 网络状态
NETWORK_STATUS_CONNECTING = "connecting"
NETWORK_STATUS_CONNECTED = "connected"
NETWORK_STATUS_DISCONNECTED = "disconnected"
NETWORK_STATUS_ERROR = "error"

# 数据包大小
BUFFER_SIZE = 1024