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
        
    def update_layout(self):
        """根据当前窗口尺寸更新布局，重写父类方法以保持传统棋盘"""
        # 计算左侧面板宽度和棋盘边距
        old_width, old_height = getattr(self, 'left_panel_width', 0), getattr(self, 'window_height', 0)
        
        self.left_panel_width = int(self.LEFT_PANEL_WIDTH_RATIO * self.window_width) if hasattr(self, 'LEFT_PANEL_WIDTH_RATIO') else int(130 / 850 * self.window_width)
        self.board_margin_top = int(self.BOARD_MARGIN_TOP_RATIO * self.window_height) if hasattr(self, 'BOARD_MARGIN_TOP_RATIO') else int(50 / 850 * self.window_height)
        
        # 确保棋盘和其他组件有足够的间距，避免被菜单遮挡
        # 为菜单栏预留空间，增加顶部边距
        adjusted_board_margin_top = max(self.board_margin_top, 80)  # 确保有足够空间给菜单
        
        # 如果窗口尺寸发生变化，清除缓存的Surface
        if old_width != self.left_panel_width or old_height != self.window_height:
            self.left_panel_surface_cache = None
            self.left_panel_overlay_cache = None

        # 更新棋盘为传统棋盘 - 这是关键的修改
        self.update_traditional_board()

        # 更新操作面板位置
        if self.operation_panel:
            self.operation_panel.update_positions()

        # 创建按钮
        self.create_buttons()

        # 创建头像
        self.create_avatars()

        # 计时器的字体
        self.timer_font = self.load_font(18)
        
        # 初始化缓存Surface
        self.left_panel_surface_cache = None
        self.left_panel_overlay_cache = None