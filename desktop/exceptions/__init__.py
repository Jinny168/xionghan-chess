"""异常模块初始化"""
from desktop.exceptions.game_exceptions import (
    # 基础异常
    ChessGameError,
    
    # 游戏状态异常
    GameStateError,
    GameNotStartedError,
    GameAlreadyOverError,
    InvalidTurnError,
    
    # 移动异常
    MoveError,
    InvalidMoveError,
    PieceNotFoundError,
    WrongPieceColorError,
    SelfCheckError,
    
    # 棋盘异常
    BoardError,
    PositionOutOfBoundsError,
    PositionOccupiedError,
    
    # 规则异常
    RuleError,
    PromotionError,
    ResurrectionError,
    
    # AI异常
    AIError,
    AITimeoutError,
    AINotInitializedError,
    
    # 资源异常
    ResourceError,
    ResourceLoadError,
    FontNotFoundError,
    ImageNotFoundError,
    SoundNotFoundError,
    
    # 配置异常
    ConfigError,
    ConfigFileNotFoundError,
    InvalidConfigValueError,
    
    # 网络异常
    NetworkError,
    ConnectionFailedError,
    DisconnectedError,
    NetworkTimeoutError,
    
    # 存档异常
    SaveLoadError,
    SaveGameError,
    LoadGameError,
    InvalidSaveDataError,
)

__all__ = [
    'ChessGameError',
    'GameStateError', 'GameNotStartedError', 'GameAlreadyOverError', 'InvalidTurnError',
    'MoveError', 'InvalidMoveError', 'PieceNotFoundError', 'WrongPieceColorError', 'SelfCheckError',
    'BoardError', 'PositionOutOfBoundsError', 'PositionOccupiedError',
    'RuleError', 'PromotionError', 'ResurrectionError',
    'AIError', 'AITimeoutError', 'AINotInitializedError',
    'ResourceError', 'ResourceLoadError', 'FontNotFoundError', 'ImageNotFoundError', 'SoundNotFoundError',
    'ConfigError', 'ConfigFileNotFoundError', 'InvalidConfigValueError',
    'NetworkError', 'ConnectionFailedError', 'DisconnectedError', 'NetworkTimeoutError',
    'SaveLoadError', 'SaveGameError', 'LoadGameError', 'InvalidSaveDataError',
]

