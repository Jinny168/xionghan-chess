"""核心模块 - 包含游戏核心逻辑组件"""

# 命令模式
from desktop.core.commands import (
    Command,
    MoveCommand,
    SimpleMoveCommand,
    JiaCaptureCommand,
    CiExchangeCommand,
    PromotionCommand,
    ResurrectionCommand,
    MoveData,
)

# 命令调用者
from desktop.core.command_invoker import CommandInvoker

# 状态机
from desktop.core.game_state_machine import GameStateMachine, GamePhase, StateTransition

# 移动验证器
from desktop.core.move_validator import MoveValidator

# 棋盘管理器
from desktop.core.board_manager import BoardManager

# 历史记录管理器
from desktop.core.history_manager import HistoryManager, MoveRecord

# 游戏组件工厂
from desktop.core.game_component_factory import GameComponentFactory, create_game_components

__all__ = [
    # 命令
    'Command',
    'MoveCommand',
    'SimpleMoveCommand',
    'JiaCaptureCommand',
    'CiExchangeCommand',
    'PromotionCommand',
    'ResurrectionCommand',
    'MoveData',
    
    # 命令调用者
    'CommandInvoker',
    
    # 状态机
    'GameStateMachine',
    'GamePhase',
    'StateTransition',
    
    # 移动验证器
    'MoveValidator',
    
    # 棋盘管理器
    'BoardManager',
    
    # 历史记录管理器
    'HistoryManager',
    'MoveRecord',
    
    # 游戏组件工厂
    'GameComponentFactory',
    'create_game_components',
]

