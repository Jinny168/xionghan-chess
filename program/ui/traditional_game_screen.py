"""传统象棋游戏界面UI管理模块"""
import pygame

from program.ui.game_screen import GameScreen
from program.ui.traditional_chess_board import TraditionalChessBoard


class TraditionalGameScreen(GameScreen):
    """管理传统象棋游戏界面的UI组件和绘制逻辑，继承自GameScreen"""
    
    def __init__(self, window_width, window_height, game_mode, player_camp):
        """初始化传统象棋游戏界面组件"""
        # 调用父类构造函数
        super().__init__(window_width, window_height, game_mode, player_camp)
        
        self.window_width = window_width
        self.window_height = window_height
        self.game_mode = game_mode
        self.player_camp = player_camp
        
        # 重新初始化棋盘为传统象棋棋盘
        self.update_traditional_board()
        
        # 计时器相关（传统象棋计时器）
        self.start_time = pygame.time.get_ticks()  # 游戏开始时间
        self.red_time = 0  # 红方累计用时
        self.black_time = 0  # 黑方累计用时
        self.current_player_start_time = self.start_time  # 当前玩家开始用时
        self._last_player = "red"  # 上一个玩家
        
    def update_traditional_board(self):
        """更新为传统象棋棋盘"""
        self.board = TraditionalChessBoard(
            self.window_width - self.left_panel_width - 40,  # 增加更多右边距
            self.window_height,
            self.left_panel_width + 30,  # 棋盘起始位置右移更多
            self.board_margin_top  # 使用调整后的顶部边距
        )
