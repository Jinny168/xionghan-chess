"""全局配置管理模块"""

# 窗口常量
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 900

# 布局常量
LEFT_PANEL_WIDTH_RATIO = 130 / 850
BOARD_MARGIN_TOP_RATIO = 50 / 850
FPS = 60

# 颜色常量
BACKGROUND_COLOR = (240, 217, 181)
PANEL_COLOR = (230, 210, 185)
PANEL_BORDER = (160, 140, 110)
BLACK = (0, 0, 0)
RED = (180, 30, 30)
GREEN = (0, 128, 0)
WHITE = (255, 255, 255)
POPUP_BG = (250, 240, 230)
BUTTON_COLOR = (100, 100, 200)
BUTTON_HOVER = (120, 120, 220)
BUTTON_TEXT = (240, 240, 255)
GOLD = (218, 165, 32)
LAST_MOVE_SOURCE = (0, 200, 80, 100)
LAST_MOVE_TARGET = (0, 200, 80, 150)

# 游戏模式常量
MODE_PVP = "pvp"
MODE_PVC = "pvc"
CAMP_RED = "red"
CAMP_BLACK = "black"

class GameConfig:
    """游戏配置管理类"""
    def __init__(self):
        # 初始化默认设置
        self.settings = {
            # 汉/汗设置
            "king_can_leave_palace": False,  # 汉/汗是否可以出九宫
            "king_lose_diagonal_outside_palace": False,  # 汉/汗出九宫后是否失去斜走能力
            "king_can_diagonal_in_palace": False,  # 汉/汗在九宫内是否可以斜走
            
            # 士设置
            "shi_can_leave_palace": False,  # 士是否可以出九宫
            "shi_gain_straight_outside_palace": False,  # 士出九宫后是否获得直走能力
            
            # 相设置
            "xiang_can_cross_river": False,  # 相是否可以过河
            "xiang_gain_jump_two_outside_river": False,  # 相过河后是否获得隔两格吃子能力
            
            # 马设置
            "ma_can_straight_three": False,  # 马是否可以获得直走三格的能力
        }
    
    def get_setting(self, key, default=None):
        """获取设置值"""
        return self.settings.get(key, default)
    
    def set_setting(self, key, value):
        """设置值"""
        self.settings[key] = value
    
    def get_all_settings(self):
        """获取所有设置"""
        return self.settings.copy()
    
    def update_settings(self, new_settings):
        """批量更新设置"""
        if isinstance(new_settings, dict):
            for key, value in new_settings.items():
                if key in self.settings:
                    self.settings[key] = value

# 创建全局配置实例
game_config = GameConfig()