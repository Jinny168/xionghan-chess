"""传统象棋网络模式实现"""

from program.core.game_state import GameState
from program.lan.network_game import NetworkChessGame
from program.ui.traditional_game_screen import TraditionalGameScreen


class TraditionalNetworkGame(NetworkChessGame):
    """传统象棋网络对战类，继承自NetworkChessGame"""
    
    def __init__(self, is_host=True):
        """
        初始化传统象棋网络对战
        :param is_host: 是否为主机
        """

        
        # 先调用父类的初始化方法，使用传统象棋模式
        super().__init__(is_host=is_host)
        
        # 替换为传统象棋的游戏状态
        self.game_state = GameState()
        # 替换为传统象棋的游戏界面
        self.game_screen = TraditionalGameScreen(self.window_width, self.window_height, "TRADITIONAL_NETWORK", self.player_camp)





