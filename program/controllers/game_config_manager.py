"""全局配置管理模块"""

"""
匈汉象棋网络对战常量
"""
import json
import os
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
BOARD_MARGIN_TOP_RATIO = 50 / 850  # 棋盘顶部边距比例
FPS = 60

# 颜色常量
BACKGROUND_COLOR = (240, 217, 181)  # 背景颜色
PANEL_COLOR = (230, 210, 185)  # 面板颜色
PANEL_BORDER = (160, 140, 110)  # 面板边框颜色
BLACK = (0, 0, 0)  # 黑色
RED = (180, 30, 30)  # 红色
GREEN = (0, 128, 0)  # 绿色
WHITE = (255, 255, 255)  # 白色
POPUP_BG = (250, 240, 230)  # 弹窗背景色
BUTTON_COLOR = (100, 100, 200)  # 按钮颜色
BUTTON_HOVER = (120, 120, 220)  # 按钮悬停颜色
BUTTON_TEXT = (240, 240, 255)  # 按钮文字颜色
GOLD = (218, 165, 32)  # 金色
LAST_MOVE_SOURCE = (0, 200, 80, 100)  # 上一步移动起始位置高亮
LAST_MOVE_TARGET = (0, 200, 80, 150)  # 上一步移动目标位置高亮

# 游戏模式常量
MODE_PVP = "pvp"
MODE_PVC = "pvc"
CAMP_RED = "red"
CAMP_BLACK = "black"

# 主题配置
THEME_CONFIG = {
    "origin": {  # 原始主题
        "background": (220, 179, 92),  # 背景颜色（棋盘木色）
        "panel": (230, 210, 185),  # 面板颜色
        "panel_border": (100, 60, 20),  # 面板边框颜色（深棕色）
        "board": {
            "base_color": (220, 179, 92),  # 棋盘底色（木色）
            "line_color": (0, 0, 0),  # 棋盘线条色（黑色）
            "grid_color": (200, 160, 80),  # 棋盘格子线色（木纹色）
            "checkerboard": [  # 棋盘格子交替配色
                (220, 179, 92), (200, 160, 80),
                (220, 179, 92), (200, 160, 80),
                (220, 179, 92), (200, 160, 80),
                (220, 179, 92), (200, 160, 80)
            ]
        },
        "pieces": {
            # 基础阵营棋子（原始主题-传统木质象棋配色）
            "light_side": {  # 浅色方/黑方
                "汗": (40, 40, 40),  # 汗（深黑色）
                "車": (40, 40, 40),  # 車（深黑色）
                "馬": (40, 40, 40),  # 馬（深黑色）
                "象": (40, 40, 40),  # 象（深黑色）
                "士": (40, 40, 40),  # 士（深黑色）
                "砲": (40, 40, 40),  # 砲（深黑色）
                "卒": (40, 40, 40),  # 卒（深黑色）
                "衛": (40, 40, 40),
                "䠶": (40, 40, 40),
                "礌": (40, 40, 40),
                "胄": (40, 40, 40),
                "伺": (40, 40, 40),
                "碷": (40, 40, 40),
                "廵": (40, 40, 40),
                "text_color": (255, 255, 255)  # 棋子文字色（白色）
            },
            "dark_side": {  # 深色方/红方
                "漢": (180, 30, 30),  # 漢（深红色）
                "俥": (180, 30, 30),  # 俥（深红色）
                "傌": (180, 30, 30),  # 傌（深红色）
                "相": (180, 30, 30),  # 相（深红色）
                "仕": (180, 30, 30),  # 仕（深红色）
                "炮": (180, 30, 30),  # 炮（深红色）
                "兵": (180, 30, 30),  # 兵（深红色）
                "尉": (180, 30, 30),
                "射": (180, 30, 30),
                "檑": (180, 30, 30),
                "甲": (180, 30, 30),
                "楯": (180, 30, 30),
                "刺": (180, 30, 30),
                "巡": (180, 30, 30),
                "text_color": (255, 255, 255)  # 棋子文字色（白色）
            },
            "text_border": (0, 0, 0)  # 棋子文字描边色（黑色）
        },
        "ui": {
            "text_color": (50, 50, 50),  # UI文字色（深灰色）
            "button_color": (100, 60, 20),  # 按钮色（深棕色）
            "button_border": (50, 30, 10)  # 按钮边框色（浅棕色）
        }
    },
    "day": {  # 白天主题
        "background": (240, 217, 181),  # 背景颜色
        "panel": (230, 210, 185),  # 面板颜色
        "panel_border": (160, 140, 110),  # 面板边框颜色
        "board": {
            "base_color": (220, 180, 120),  # 棋盘底色（浅木色）
            "line_color": (100, 60, 20),  # 棋盘线条色（深棕色）
            "grid_color": (245, 220, 180),  # 棋盘格子线色（浅米色）
            "checkerboard": [  # 棋盘格子交替配色
                (220, 180, 120), (245, 220, 180),
                (220, 180, 120), (245, 220, 180),
                (220, 180, 120), (245, 220, 180),
                (220, 180, 120), (245, 220, 180)
            ]
        },
        "pieces": {
            # 白天主题棋子配色
            "light_side": {  # 浅色方/黑方
                "汗": (30, 30, 30),  # 汗（深黑色）
                "車": (30, 30, 30),  # 車（深黑色）
                "馬": (30, 30, 30),  # 馬（深黑色）
                "象": (30, 30, 30),  # 象（深黑色）
                "士": (30, 30, 30),  # 士（深黑色）
                "砲": (30, 30, 30),  # 砲（深黑色）
                "卒": (30, 30, 30),  # 卒（深黑色）
                "衛": (30, 30, 30),
                "䠶": (30, 30, 30),
                "礌": (30, 30, 30),
                "胄": (30, 30, 30),
                "伺": (30, 30, 30),
                "碷": (30, 30, 30),
                "廵": (30, 30, 30),
                "text_color": (255, 255, 255)  # 棋子文字色（白色）
            },
            "dark_side": {  # 深色方/红方
                "漢": (180, 30, 30),  # 漢（深红色）
                "俥": (180, 30, 30),  # 俥（深红色）
                "傌": (180, 30, 30),  # 傌（深红色）
                "相": (180, 30, 30),  # 相（深红色）
                "仕": (180, 30, 30),  # 仕（深红色）
                "炮": (180, 30, 30),  # 炮（深红色）
                "兵": (180, 30, 30),  # 兵（深红色）
                "尉": (180, 30, 30),
                "射": (180, 30, 30),
                "檑": (180, 30, 30),
                "甲": (180, 30, 30),
                "楯": (180, 30, 30),
                "刺": (180, 30, 30),
                "巡": (180, 30, 30),
                "text_color": (255, 255, 255)  # 棋子文字色（白色）
            },
            "text_border": (0, 0, 0)  # 棋子文字描边色（黑色）
        },
        "ui": {
            "text_color": (50, 50, 50),  # UI文字色（深灰色）
            "button_color": (100, 60, 20),  # 按钮色（深棕色）
            "button_border": (50, 30, 10)  # 按钮边框色（浅棕色）
        }
    },
    "night": {  # 夜晚主题
        "background": (40, 40, 40),  # 背景色（深色）
        "panel": (60, 60, 60),  # 面板色（稍浅的深色）
        "panel_border": (100, 100, 100),  # 面板边框色（灰色）
        "board": {
            "base_color": (100, 70, 40),  # 棋盘底色（深檀木色）
            "line_color": (240, 220, 180),  # 棋盘线条色（米白色）
            "grid_color": (150, 100, 60),  # 棋盘格子线色（浅棕色）
            "checkerboard": [  # 棋盘格子交替配色
                (100, 70, 40), (150, 100, 60),
                (100, 70, 40), (150, 100, 60),
                (100, 70, 40), (150, 100, 60),
                (100, 70, 40), (150, 100, 60)
            ]
        },
        "pieces": {
            # 基础阵营棋子（夜晚主题-浅色系）
            "light_side": {  # 浅色方/白方
                "汗": (240, 220, 180),  # 汗（米白色）
                "車": (240, 220, 180),  # 車（米白色）
                "馬": (240, 220, 180),  # 馬（米白色）
                "象": (240, 220, 180),  # 象（米白色）
                "士": (240, 220, 180),  # 士（米白色）
                "砲": (240, 220, 180),  # 砲（米白色）
                "卒": (240, 220, 180),  # 卒（米白色）
                "衛": (240, 220, 180),
                "䠶": (240, 220, 180),
                "礌": (240, 220, 180),
                "胄": (240, 220, 180),
                "伺": (240, 220, 180),
                "碷": (240, 220, 180),
                "廵": (240, 220, 180),
                "text_color": (30, 30, 30)  # 棋子文字色（深黑色）
            },
            "dark_side": {  # 深色方/金方
                "漢": (255, 215, 0),  # 漢（金色）
                "俥": (255, 215, 0),  # 俥（金色）
                "傌": (255, 215, 0),  # 傌（金色）
                "相": (255, 215, 0),  # 相（金色）
                "仕": (255, 215, 0),  # 仕（金色）
                "炮": (255, 215, 0),  # 炮（金色）
                "兵": (255, 215, 0),  # 兵（金色）
                "尉": (255, 215, 0),
                "射": (255, 215, 0),
                "檑": (255, 215, 0),
                "甲": (255, 215, 0),
                "楯": (255, 215, 0),
                "刺": (255, 215, 0),
                "巡": (255, 215, 0),
                "text_color": (30, 30, 30)  # 棋子文字色（深黑色）
            },
            "text_border": (200, 200, 200)  # 棋子文字描边色（浅灰，增强可读性）
        },
        "ui": {
            "text_color": (220, 220, 220),  # UI文字色（浅灰色）
            "button_color": (240, 220, 180),  # 按钮色（米白色）
            "button_border": (200, 180, 140)  # 按钮边框色（浅棕色）
        }
    },
    "qq_chess": {  # QQ象棋主题
        "background": (245, 245, 245),  # 背景色（浅灰色）
        "panel": (230, 220, 200),  # 面板色（米黄色调）
        "panel_border": (180, 160, 130),  # 面板边框色（浅棕色）
        "board": {
            "base_color": (220, 180, 120),  # 棋盘底色（浅木色）
            "line_color": (80, 50, 20),  # 棋盘线条色（深棕色）
            "grid_color": (200, 160, 100),  # 棋盘格子线色（暖色调）
            "checkerboard": [  # 棋盘格子交替配色
                (220, 180, 120), (200, 160, 100),
                (220, 180, 120), (200, 160, 100),
                (220, 180, 120), (200, 160, 100),
                (220, 180, 120), (200, 160, 100)
            ]
        },
        "pieces": {
            # QQ象棋主题棋子配色
            "light_side": {  # 浅色方/黑方
                "汗": (50, 50, 50),  # 汗（深灰色）
                "車": (50, 50, 50),  # 車（深灰色）
                "馬": (50, 50, 50),  # 馬（深灰色）
                "象": (50, 50, 50),  # 象（深灰色）
                "士": (50, 50, 50),  # 士（深灰色）
                "砲": (50, 50, 50),  # 砲（深灰色）
                "卒": (50, 50, 50),  # 卒（深灰色）
                "衛": (50, 50, 50),
                "䠶": (50, 50, 50),
                "礌": (50, 50, 50),
                "胄": (50, 50, 50),
                "伺": (50, 50, 50),
                "碷": (50, 50, 50),
                "廵": (50, 50, 50),
                "text_color": (255, 255, 255)  # 棋子文字色（白色）
            },
            "dark_side": {  # 深色方/红方
                "漢": (200, 0, 0),  # 漢（鲜艳红色）
                "俥": (200, 0, 0),  # 俥（鲜艳红色）
                "傌": (200, 0, 0),  # 傌（鲜艳红色）
                "相": (200, 0, 0),  # 相（鲜艳红色）
                "仕": (200, 0, 0),  # 仕（鲜艳红色）
                "炮": (200, 0, 0),  # 炮（鲜艳红色）
                "兵": (200, 0, 0),  # 兵（鲜艳红色）
                "尉": (200, 0, 0),
                "射": (200, 0, 0),
                "檑": (200, 0, 0),
                "甲": (200, 0, 0),
                "楯": (200, 0, 0),
                "刺": (200, 0, 0),
                "巡": (200, 0, 0),
                "text_color": (255, 255, 255)  # 棋子文字色（白色）
            },
            "text_border": (0, 0, 0)  # 棋子文字描边色（黑色）
        },
        "ui": {
            "text_color": (60, 60, 60),  # UI文字色（中灰色）
            "button_color": (100, 150, 200),  # 按钮色（蓝色调）
            "button_border": (80, 120, 180)  # 按钮边框色（深蓝）
        }
    },
    "jj_chess": {  # JJ象棋主题
        "background": (230, 240, 230),  # 背景色（淡绿色，护眼）
        "panel": (220, 230, 210),  # 面板色（浅绿调）
        "panel_border": (150, 170, 140),  # 面板边框色（绿灰色）
        "board": {
            "base_color": (200, 180, 150),  # 棋盘底色（温润木色）
            "line_color": (60, 40, 20),  # 棋盘线条色（深棕褐色）
            "grid_color": (180, 160, 130),  # 棋盘格子线色（暖木色）
            "checkerboard": [  # 棋盘格子交替配色
                (200, 180, 150), (180, 160, 130),
                (200, 180, 150), (180, 160, 130),
                (200, 180, 150), (180, 160, 130),
                (200, 180, 150), (180, 160, 130)
            ]
        },
        "pieces": {
            # JJ象棋主题棋子配色
            "light_side": {  # 浅色方/黑方
                "汗": (40, 60, 80),  # 汗（深蓝灰色）
                "車": (40, 60, 80),  # 車（深蓝灰色）
                "馬": (40, 60, 80),  # 馬（深蓝灰色）
                "象": (40, 60, 80),  # 象（深蓝灰色）
                "士": (40, 60, 80),  # 士（深蓝灰色）
                "砲": (40, 60, 80),  # 砲（深蓝灰色）
                "卒": (40, 60, 80),  # 卒（深蓝灰色）
                "衛": (40, 60, 80),
                "䠶": (40, 60, 80),
                "礌": (40, 60, 80),
                "胄": (40, 60, 80),
                "伺": (40, 60, 80),
                "碷": (40, 60, 80),
                "廵": (40, 60, 80),
                "text_color": (255, 255, 255)  # 棋子文字色（白色）
            },
            "dark_side": {  # 深色方/红方
                "漢": (180, 40, 40),  # 漢（温和红色）
                "俥": (180, 40, 40),  # 俥（温和红色）
                "傌": (180, 40, 40),  # 傌（温和红色）
                "相": (180, 40, 40),  # 相（温和红色）
                "仕": (180, 40, 40),  # 仕（温和红色）
                "炮": (180, 40, 40),  # 炮（温和红色）
                "兵": (180, 40, 40),  # 兵（温和红色）
                "尉": (180, 40, 40),
                "射": (180, 40, 40),
                "檑": (180, 40, 40),
                "甲": (180, 40, 40),
                "楯": (180, 40, 40),
                "刺": (180, 40, 40),
                "巡": (180, 40, 40),
                "text_color": (255, 255, 255)  # 棋子文字色（白色）
            },
            "text_border": (30, 30, 30)  # 棋子文字描边色（深灰色）
        },
        "ui": {
            "text_color": (50, 70, 50),  # UI文字色（深绿色）
            "button_color": (80, 140, 80),  # 按钮色（绿色调）
            "button_border": (60, 120, 60)  # 按钮边框色（深绿）
        }
    }
}


def get_piece_color(piece_type: str, theme: str, side: str) -> tuple:
    """
    根据棋子类型、主题、阵营返回对应配色
    :param piece_type: 棋子类型（如"漢""射""檑"）
    :param theme: 主题（day/night/origin）
    :param side: 阵营（light_side/dark_side）
    :return: 棋子RGB配色元组
    """
    try:
        # 校验参数合法性
        if theme not in ["day", "night", "origin"]:
            theme = "origin"  # 默认原始主题
        if side not in ["light_side", "dark_side"]:
            side = "light_side"  # 默认浅色方

        # 获取对应配色
        color = THEME_CONFIG[theme]["pieces"][side].get(piece_type)
        if color is None:
            # 未知棋子类型，返回默认色
            default_colors = {
                "day": {"light_side": (30, 20, 10), "dark_side": (180, 0, 0)},
                "night": {"light_side": (240, 220, 180), "dark_side": (255, 215, 0)},
                "origin": {"light_side": (30, 20, 10), "dark_side": (180, 0, 0)}
            }
            color = default_colors[theme][side]
        return color
    except Exception as e:
        print(f"获取棋子配色失败：{e}")
        # 终极兜底配色
        return (150, 150, 150) if theme in ["day", "origin"] else (100, 100, 100)


def get_piece_text_color(theme: str, side: str) -> tuple:
    """获取棋子文字配色"""
    try:
        return THEME_CONFIG[theme]["pieces"][side]["text_color"]
    except:
        return (255, 255, 255) if theme in ["day", "origin", "qq_chess", "jj_chess"] else (0, 0, 0)


class ThemeManager:
    """主题管理类，处理日/夜主题配置和切换逻辑"""

    def __init__(self):
        self.config_file = "game_config.json"
        self.default_theme = "day"  # 默认主题为白天
        self.current_theme = self.load_theme()

        # 使用统一的主题配置
        self.themes = THEME_CONFIG

    def load_theme(self):
        """从配置文件加载主题"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    theme = config.get('theme', self.default_theme)
                    return theme if theme in ['day', 'night', 'origin'] else self.default_theme
        except Exception as e:
            print(f"加载主题配置失败: {e}")

        return self.default_theme

    def save_theme(self, theme):
        """保存主题到配置文件"""
        try:
            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            config['theme'] = theme
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)

            self.current_theme = theme
            return True
        except Exception as e:
            print(f"保存主题配置失败: {e}")
            return False

    def get_current_theme(self):
        """获取当前主题"""
        return self.current_theme

    def get_theme_colors(self):
        """获取当前主题的颜色配置"""
        return self.themes[self.current_theme]

    def toggle_theme(self):
        """切换主题"""
        # 在三个主题之间循环切换
        if self.current_theme == "day":
            new_theme = "night"
        elif self.current_theme == "night":
            new_theme = "origin"
        else:  # self.current_theme == "origin"
            new_theme = "day"
        self.save_theme(new_theme)
        return new_theme


theme_manager = ThemeManager()


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
            "ju_appear": True,  # 車/车登场
            "ma_appear": True,  # 馬/马登场
            "xiang_appear": True,  # 相/象登场
            "shi_appear": True,  # 士/仕登场
            "king_appear": True,  # 将/帅/汉/汗登场
            "pao_appear": True,  # 炮/砲登场
            "pawn_appear": True,  # 兵/卒登场
            "pawn_resurrection_enabled": True,  # 兵/卒复活机制启用
            "pawn_promotion_enabled": True,  # 兵/卒升变机制启用
            "pawn_backward_at_base_enabled": True,  # 兵/卒底线后退能力
            "pawn_full_movement_at_base_enabled": True,  # 兵/卒底线完整移动能力
            "wei_appear": True,  # 尉/衛登场
            "she_appear": True,  # 射/䠶登场
            "lei_appear": True,  # 檑/礌登场
            "jia_appear": True,  # 甲/胄登场
            "ci_appear": True,  # 刺登场
            "dun_appear": True,  # 盾登场
            "xun_appear": True,  # 巡/廵登场
            # 游戏模式设置
            "classic_mode": False,  # 决定匈汉象棋为经典模式还是狂暴模式
            "traditional_mode":False,  # 决定游玩中国象棋还是匈汉象棋
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
