"""
游戏常量定义 - 集中管理所有魔法数字和配置值
"""
import pygame


class GameConstants:
    """游戏全局常量"""
    
    # ==================== 棋盘配置 ====================
    BOARD_SIZE_XIONGHAN = 13      # 匈汉象棋棋盘尺寸
    BOARD_SIZE_TRADITIONAL = 9    # 传统象棋列数
    BOARD_ROWS_TRADITIONAL = 10   # 传统象棋行数
    
    # ==================== 窗口配置 ====================
    DEFAULT_WINDOW_WIDTH = 1200
    DEFAULT_WINDOW_HEIGHT = 900
    MIN_WINDOW_WIDTH = 800
    MIN_WINDOW_HEIGHT = 600
    
    # ==================== FPS配置 ====================
    NORMAL_FPS = 60               # 正常游戏FPS
    AI_THINKING_FPS = 15          # AI思考时FPS（降低CPU占用）
    DIALOG_FPS = 30               # 对话框显示时FPS
    REPLAY_FPS = 30               # 复盘模式FPS
    
    # ==================== 时间配置（毫秒）====================
    AI_THINK_TIMEOUT_MS = 10000           # AI思考超时时间（10秒）
    AI_MOVE_DELAY_MS = 800                # AI移动延迟（让玩家看清）
    CHECK_ANIMATION_DURATION_S = 4.0      # 将军动画持续时间（秒）
    TOAST_NOTIFICATION_DURATION_MS = 2000 # 提示通知显示时间
    
    # ==================== Pygame事件ID ====================
    EVENT_AI_TIMEOUT = pygame.USEREVENT + 1       # AI超时事件
    EVENT_AI_MOVE_COMPLETE = pygame.USEREVENT + 2 # AI移动完成事件
    
    # ==================== 布局比例 ====================
    LEFT_PANEL_WIDTH_RATIO = 130 / 850   # 左侧面板宽度比例
    BOARD_MARGIN_TOP_RATIO = 50 / 850    # 棋盘顶部边距比例
    RIGHT_PANEL_WIDTH_RATIO = 0.2        # 右侧面板宽度比例
    
    # ==================== 颜色常量 ====================
    # 基础颜色
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    RED = (180, 30, 30)
    GREEN = (0, 128, 0)
    GOLD = (218, 165, 32)
    
    # UI颜色
    BACKGROUND_COLOR = (240, 217, 181)
    PANEL_COLOR = (230, 210, 185)
    PANEL_BORDER = (160, 140, 110)
    POPUP_BG = (250, 240, 230)
    
    # 按钮颜色
    BUTTON_COLOR = (100, 100, 200)
    BUTTON_HOVER = (120, 120, 220)
    BUTTON_TEXT = (240, 240, 255)
    
    # 高亮颜色
    LAST_MOVE_SOURCE = (0, 200, 80, 100)   # 上一步起始位置
    LAST_MOVE_TARGET = (0, 200, 80, 150)   # 上一步目标位置
    SELECTED_PIECE_HIGHLIGHT = (255, 255, 0, 128)  # 选中棋子高亮
    VALID_MOVE_HIGHLIGHT = (0, 255, 0, 100)        # 合法移动高亮
    
    # ==================== 游戏模式常量 ====================
    MODE_PVP = "pvp"        # 双人对战
    MODE_PVC = "pvc"        # 人机对战
    MODE_NETWORK = "network" # 网络对战
    
    CAMP_RED = "red"        # 红方
    CAMP_BLACK = "black"    # 黑方
    
    # ==================== AI难度等级 ====================
    AI_DIFFICULTY_EASY = "easy"
    AI_DIFFICULTY_MEDIUM = "medium"
    AI_DIFFICULTY_HARD = "hard"
    AI_DIFFICULTY_EXPERT = "expert"
    
    # ==================== AI算法类型 ====================
    AI_ALGORITHM_NEGAMAX = "negamax"
    AI_ALGORITHM_MCTS = "mcts"
    
    # ==================== 音效类型 ====================
    SOUND_MOVE = "drop"         # 移动音效
    SOUND_CAPTURE = "eat"       # 吃子音效
    SOUND_CHECK = "warn"        # 将军音效
    SOUND_VICTORY = "victory"   # 胜利音效
    SOUND_DEFEAT = "defeat"     # 失败音效
    SOUND_BUTTON = "button"     # 按钮点击音效
    SOUND_SELECT = "choose"     # 选择音效
    
    # ==================== 文件路径 ====================
    CONFIG_DIR = "assets/docs"
    SOUND_DIR = "assets/sounds"
    FONT_DIR = "assets/fonts"
    IMAGE_DIR = "assets/pics"
    
    # 配置文件
    GAME_CONFIG_FILE = "game_config.json"
    THEME_CONFIG_FILE = "theme_config.json"
    STATISTICS_FILE = "statistics.json"
    TAUNTS_FILE = "taunts.json"
    
    # ==================== 字体配置 ====================
    DEFAULT_FONT_SIZE = 24
    TITLE_FONT_SIZE = 36
    SMALL_FONT_SIZE = 18
    LARGE_FONT_SIZE = 48
    
    # ==================== 网络配置 ====================
    NETWORK_DEFAULT_PORT = 10087
    NETWORK_BUFFER_SIZE = 1024
    NETWORK_CONNECTION_TIMEOUT_S = 2.0
    
    # 网络消息类型
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
    
    # ==================== 历史记录限制 ====================
    MAX_MOVE_HISTORY = 1000       # 最大移动历史记录数
    MAX_BOARD_POSITION_HISTORY = 100  # 最大局面历史记录数
    
    # ==================== 兵卒复活配置 ====================
    PAWN_INITIAL_COUNT = 7        # 初始兵卒数量
    PAWN_RESURRECTION_ROW_RED = 8    # 红方兵复活行
    PAWN_RESURRECTION_ROW_BLACK = 4  # 黑方兵复活行
    
    # ==================== 升变配置 ====================
    MAX_PROMOTION_OPTIONS = 10    # 最大升变选项数
    
    # ==================== 调试配置 ====================
    DEBUG_MODE = False            # 调试模式开关
    SHOW_DEBUG_INFO = False       # 显示调试信息
    LOG_LEVEL = "INFO"            # 日志级别
    
    # ==================== 性能优化配置 ====================
    ENABLE_DIRTY_RECT_RENDERING = True  # 启用脏矩形渲染
    CACHE_VALID_MOVES = True            # 缓存合法移动计算
    OBJECT_POOL_SIZE = 100              # 对象池大小
    
    @classmethod
    def get_board_size(cls, traditional_mode: bool = False) -> int:
        """
        获取棋盘尺寸
        
        Args:
            traditional_mode: 是否为传统模式
            
        Returns:
            int: 棋盘尺寸
        """
        return cls.BOARD_SIZE_TRADITIONAL if traditional_mode else cls.BOARD_SIZE_XIONGHAN
    
    @classmethod
    def get_fps(cls, ai_thinking: bool = False, dialog_showing: bool = False) -> int:
        """
        获取当前应该使用的FPS
        
        Args:
            ai_thinking: AI是否正在思考
            dialog_showing: 是否显示对话框
            
        Returns:
            int: FPS值
        """
        if dialog_showing:
            return cls.DIALOG_FPS
        elif ai_thinking:
            return cls.AI_THINKING_FPS
        else:
            return cls.NORMAL_FPS
