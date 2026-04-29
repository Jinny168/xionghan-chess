"""
游戏自定义异常体系 - 提供清晰的错误分类和错误信息
"""


class ChessGameError(Exception):
    """
    游戏基础异常类
    所有游戏相关异常的基类
    """
    
    def __init__(self, message: str = "游戏发生错误", error_code: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
    
    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


# ==================== 游戏状态异常 ====================

class GameStateError(ChessGameError):
    """游戏状态错误"""
    
    def __init__(self, message: str = "游戏状态异常"):
        super().__init__(message, error_code="GAME_STATE_ERROR")


class GameNotStartedError(GameStateError):
    """游戏未开始异常"""
    
    def __init__(self, message: str = "游戏尚未开始"):
        super().__init__(message, error_code="GAME_NOT_STARTED")


class GameAlreadyOverError(GameStateError):
    """游戏已结束异常"""
    
    def __init__(self, message: str = "游戏已经结束"):
        super().__init__(message, error_code="GAME_ALREADY_OVER")


class InvalidTurnError(GameStateError):
    """无效回合异常"""
    
    def __init__(self, current_turn: str, expected_turn: str):
        message = f"当前是{current_turn}方回合，但期望是{expected_turn}方"
        super().__init__(message, error_code="INVALID_TURN")
        self.current_turn = current_turn
        self.expected_turn = expected_turn


# ==================== 棋子移动异常 ====================

class MoveError(ChessGameError):
    """移动相关错误基类"""
    
    def __init__(self, message: str = "移动错误", error_code: str = "MOVE_ERROR"):
        super().__init__(message, error_code=error_code)


class InvalidMoveError(MoveError):
    """非法移动异常"""
    
    def __init__(self, from_pos: tuple, to_pos: tuple, reason: str = "未知原因"):
        message = f"从{from_pos}到{to_pos}的移动非法: {reason}"
        super().__init__(message, error_code="INVALID_MOVE")
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.reason = reason


class PieceNotFoundError(MoveError):
    """棋子不存在异常"""
    
    def __init__(self, position: tuple):
        message = f"位置{position}没有棋子"
        super().__init__(message, error_code="PIECE_NOT_FOUND")
        self.position = position


class WrongPieceColorError(MoveError):
    """棋子颜色错误异常"""
    
    def __init__(self, piece_color: str, expected_color: str):
        message = f"不能移动{piece_color}方棋子，当前应该是{expected_color}方"
        super().__init__(message, error_code="WRONG_PIECE_COLOR")
        self.piece_color = piece_color
        self.expected_color = expected_color


class SelfCheckError(MoveError):
    """送将异常（移动后自己被将军）"""
    
    def __init__(self, position: tuple):
        message = f"移动到{position}会导致自己被将军"
        super().__init__(message, error_code="SELF_CHECK")
        self.position = position


# ==================== 棋盘相关异常 ====================

class BoardError(ChessGameError):
    """棋盘相关错误基类"""
    
    def __init__(self, message: str = "棋盘错误", error_code: str = "BOARD_ERROR"):
        super().__init__(message, error_code=error_code)


class PositionOutOfBoundsError(BoardError):
    """位置越界异常"""
    
    def __init__(self, row: int, col: int, board_size: int):
        message = f"位置({row}, {col})超出棋盘范围(0-{board_size-1})"
        super().__init__(message, error_code="POSITION_OUT_OF_BOUNDS")
        self.row = row
        self.col = col
        self.board_size = board_size


class PositionOccupiedError(BoardError):
    """位置被占用异常"""
    
    def __init__(self, position: tuple, occupying_piece: str):
        message = f"位置{position}已被{occupying_piece}占用"
        super().__init__(message, error_code="POSITION_OCCUPIED")
        self.position = position
        self.occupying_piece = occupying_piece


# ==================== 游戏规则异常 ====================

class RuleError(ChessGameError):
    """规则相关错误基类"""
    
    def __init__(self, message: str = "规则错误", error_code: str = "RULE_ERROR"):
        super().__init__(message, error_code=error_code)


class PromotionError(RuleError):
    """升变异常"""
    
    def __init__(self, message: str = "升变失败"):
        super().__init__(message, error_code="PROMOTION_ERROR")


class ResurrectionError(RuleError):
    """复活异常"""
    
    def __init__(self, message: str = "复活失败"):
        super().__init__(message, error_code="RESURRECTION_ERROR")


# ==================== AI相关异常 ====================

class AIError(ChessGameError):
    """AI相关错误基类"""
    
    def __init__(self, message: str = "AI错误", error_code: str = "AI_ERROR"):
        super().__init__(message, error_code=error_code)


class AITimeoutError(AIError):
    """AI超时异常"""
    
    def __init__(self, timeout_ms: int):
        message = f"AI思考超时（{timeout_ms}ms）"
        super().__init__(message, error_code="AI_TIMEOUT")
        self.timeout_ms = timeout_ms


class AINotInitializedError(AIError):
    """AI未初始化异常"""
    
    def __init__(self, message: str = "AI未初始化"):
        super().__init__(message, error_code="AI_NOT_INITIALIZED")


# ==================== 资源加载异常 ====================

class ResourceError(ChessGameError):
    """资源相关错误基类"""
    
    def __init__(self, message: str = "资源错误", error_code: str = "RESOURCE_ERROR"):
        super().__init__(message, error_code=error_code)


class ResourceLoadError(ResourceError):
    """资源加载失败异常"""
    
    def __init__(self, resource_type: str, resource_path: str, reason: str = None):
        message = f"加载{resource_type}失败: {resource_path}"
        if reason:
            message += f" - {reason}"
        super().__init__(message, error_code="RESOURCE_LOAD_ERROR")
        self.resource_type = resource_type
        self.resource_path = resource_path
        self.reason = reason


class FontNotFoundError(ResourceLoadError):
    """字体文件未找到异常"""
    
    def __init__(self, font_path: str):
        super().__init__("字体", font_path, "文件不存在")


class ImageNotFoundError(ResourceLoadError):
    """图片文件未找到异常"""
    
    def __init__(self, image_path: str):
        super().__init__("图片", image_path, "文件不存在")


class SoundNotFoundError(ResourceLoadError):
    """音效文件未找到异常"""
    
    def __init__(self, sound_path: str):
        super().__init__("音效", sound_path, "文件不存在")


# ==================== 配置相关异常 ====================

class ConfigError(ChessGameError):
    """配置相关错误基类"""
    
    def __init__(self, message: str = "配置错误", error_code: str = "CONFIG_ERROR"):
        super().__init__(message, error_code=error_code)


class ConfigFileNotFoundError(ConfigError):
    """配置文件未找到异常"""
    
    def __init__(self, config_path: str):
        message = f"配置文件不存在: {config_path}"
        super().__init__(message, error_code="CONFIG_FILE_NOT_FOUND")
        self.config_path = config_path


class InvalidConfigValueError(ConfigError):
    """无效配置值异常"""
    
    def __init__(self, key: str, value, expected_type: str):
        message = f"配置项'{key}'的值无效: {value} (期望类型: {expected_type})"
        super().__init__(message, error_code="INVALID_CONFIG_VALUE")
        self.key = key
        self.value = value
        self.expected_type = expected_type


# ==================== 网络相关异常 ====================

class NetworkError(ChessGameError):
    """网络相关错误基类"""
    
    def __init__(self, message: str = "网络错误", error_code: str = "NETWORK_ERROR"):
        super().__init__(message, error_code=error_code)


class ConnectionFailedError(NetworkError):
    """连接失败异常"""
    
    def __init__(self, host: str, port: int, reason: str = None):
        message = f"连接到{host}:{port}失败"
        if reason:
            message += f" - {reason}"
        super().__init__(message, error_code="CONNECTION_FAILED")
        self.host = host
        self.port = port
        self.reason = reason


class DisconnectedError(NetworkError):
    """连接断开异常"""
    
    def __init__(self, message: str = "网络连接已断开"):
        super().__init__(message, error_code="DISCONNECTED")


class NetworkTimeoutError(NetworkError):
    """网络超时异常"""
    
    def __init__(self, operation: str, timeout_s: float):
        message = f"网络操作'{operation}'超时（{timeout_s}秒）"
        super().__init__(message, error_code="NETWORK_TIMEOUT")
        self.operation = operation
        self.timeout_s = timeout_s


# ==================== 数据持久化异常 ====================

class SaveLoadError(ChessGameError):
    """保存/加载错误基类"""
    
    def __init__(self, message: str = "保存/加载错误", error_code: str = "SAVE_LOAD_ERROR"):
        super().__init__(message, error_code=error_code)


class SaveGameError(SaveLoadError):
    """保存游戏失败异常"""
    
    def __init__(self, reason: str = None):
        message = "保存游戏失败"
        if reason:
            message += f" - {reason}"
        super().__init__(message, error_code="SAVE_GAME_ERROR")
        self.reason = reason


class LoadGameError(SaveLoadError):
    """加载游戏失败异常"""
    
    def __init__(self, file_path: str, reason: str = None):
        message = f"加载游戏失败: {file_path}"
        if reason:
            message += f" - {reason}"
        super().__init__(message, error_code="LOAD_GAME_ERROR")
        self.file_path = file_path
        self.reason = reason


class InvalidSaveDataError(SaveLoadError):
    """无效的存档数据异常"""
    
    def __init__(self, reason: str = "数据格式不正确"):
        message = f"存档数据无效: {reason}"
        super().__init__(message, error_code="INVALID_SAVE_DATA")
        self.reason = reason
