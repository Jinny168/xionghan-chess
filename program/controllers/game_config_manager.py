"""全局配置管理模块"""

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

# 棋盘尺寸常量
BOARD_SIZE = 13
# 窗口常量
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 900

# 布局常量
LEFT_PANEL_WIDTH_RATIO = 130 / 850  # 左侧面板宽度比例
BOARD_MARGIN_TOP_RATIO = 50 / 850   # 棋盘顶部边距比例
FPS = 60

# 颜色常量
BACKGROUND_COLOR = (240, 217, 181)  # 背景颜色
PANEL_COLOR = (230, 210, 185)       # 面板颜色
PANEL_BORDER = (160, 140, 110)      # 面板边框颜色
BLACK = (0, 0, 0)                   # 黑色
RED = (180, 30, 30)                 # 红色
GREEN = (0, 128, 0)                 # 绿色
WHITE = (255, 255, 255)             # 白色
POPUP_BG = (250, 240, 230)          # 弹窗背景色
BUTTON_COLOR = (100, 100, 200)      # 按钮颜色
BUTTON_HOVER = (120, 120, 220)      # 按钮悬停颜色
BUTTON_TEXT = (240, 240, 255)       # 按钮文字颜色
GOLD = (218, 165, 32)               # 金色
LAST_MOVE_SOURCE = (0, 200, 80, 100)  # 上一步移动起始位置高亮
LAST_MOVE_TARGET = (0, 200, 80, 150)  # 上一步移动目标位置高亮

# 游戏模式常量
MODE_PVP = "pvp"
MODE_PVC = "pvc"
CAMP_RED = "red"
CAMP_BLACK = "black"

class GameConfigManager:
    """游戏配置管理类"""
    def __init__(self):
        # 初始化默认设置
        self.settings = {
            # 汉/汗设置
            "king_can_leave_palace": True,  # 汉/汗是否可以出九宫
            "king_lose_diagonal_outside_palace": True,  # 汉/汗出九宫后是否失去斜走能力
            "king_can_diagonal_in_palace": True,  # 汉/汗在九宫内是否可以斜走
            
            # 士设置
            "shi_can_leave_palace": True,  # 士是否可以出九宫
            "shi_gain_straight_outside_palace": True,  # 士出九宫后是否获得直走能力
            
            # 相设置
            "xiang_can_cross_river": True,  # 相是否可以过河
            "xiang_gain_jump_two_outside_river": True,  # 相过河后是否获得隔两格吃子能力
            
            # 马设置
            "ma_can_straight_three": True,  # 马是否可以获得直走三格的能力
            
            # 棋子登场设置
            "ju_appear": True,      # 車/车登场
            "ma_appear": True,      # 馬/马登场
            "xiang_appear": True,   # 相/象登场
            "shi_appear": True,     # 士/仕登场
            "king_appear": True,    # 将/帅/汉/汗登场
            "pao_appear": True,     # 炮/砲登场
            "pawn_appear": True,    # 兵/卒登场
            "pawn_resurrection_enabled": True,  # 兵/卒复活机制启用
            "pawn_promotion_enabled": True,     # 兵/卒升变机制启用
            "pawn_backward_at_base_enabled": True,  # 兵/卒底线后退能力
            "pawn_full_movement_at_base_enabled": True,  # 兵/卒底线完整移动能力
            "wei_appear": True,     # 尉/衛登场
            "she_appear": True,     # 射/䠶登场
            "lei_appear": True,     # 檑/礌登场
            "jia_appear": True,     # 甲/胄登场
            "ci_appear": True,      # 刺登场
            "dun_appear": True,     # 盾登场
            "xun_appear": True,     # 巡/廵登场
            # 游戏模式设置
            "classic_mode": False,  # 经典模式
            # AI设置
            "ai_algorithm": "negamax",  # AI算法类型: negamax, minimax, alpha-beta
        }
    
    def get_setting(self, key, default=None):
        """获取设置值"""
        # 确保只返回已定义的配置键
        if key not in self.settings:
            return default
        return self.settings.get(key, default)
    
    def set_setting(self, key, value):
        """设置值"""
        # 确保只设置已定义的配置键
        if key in self.settings:
            self.settings[key] = value
    
    def get_all_settings(self):
        """获取所有设置"""
        return self.settings.copy()
    
    def update_settings(self, new_settings):
        """批量更新设置"""
        if isinstance(new_settings, dict):
            for key, value in new_settings.items():
                # 确保只更新已定义的配置键，防止添加意外的配置项
                if key in self.settings:
                    self.settings[key] = value

# 创建全局配置实例
game_config = GameConfigManager()