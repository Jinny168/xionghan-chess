"""全局配置管理模块"""

class GameConfig:
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