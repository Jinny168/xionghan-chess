"""
游戏组件工厂 - 提供依赖注入支持
集中管理游戏核心组件的创建和配置
"""
from typing import Optional, Dict, Any
from desktop.core.chess_pieces import create_initial_pieces
from desktop.core.board_manager import BoardManager
from desktop.core.move_validator import MoveValidator
from desktop.core.history_manager import HistoryManager
from desktop.core.command_invoker import CommandInvoker
from desktop.core.game_state_machine import GameStateMachine


class GameComponentFactory:
    """
    游戏组件工厂
    负责创建和配置游戏的核心组件，支持依赖注入
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化工厂
        
        Args:
            config: 配置字典，可包含各种组件的配置参数
        """
        self.config = config or {}
    
    def create_board_manager(self, pieces=None) -> BoardManager:
        """
        创建棋盘管理器
        
        Args:
            pieces: 初始棋子列表（可选，默认使用标准开局）
            
        Returns:
            BoardManager实例
        """
        if pieces is None:
            pieces = create_initial_pieces()
        
        return BoardManager(pieces)
    
    def create_move_validator(self, board_manager: BoardManager, 
                             player_turn: str) -> MoveValidator:
        """
        创建移动验证器
        
        Args:
            board_manager: 棋盘管理器实例
            player_turn: 当前回合玩家
            
        Returns:
            MoveValidator实例
        """
        return MoveValidator(board_manager.pieces, player_turn)
    
    def create_history_manager(self, max_history: Optional[int] = None) -> HistoryManager:
        """
        创建历史记录管理器
        
        Args:
            max_history: 最大历史记录数（可选，默认100）
            
        Returns:
            HistoryManager实例
        """
        max_hist = max_history or self.config.get('max_history', 100)
        return HistoryManager(max_history=max_hist)
    
    def create_command_invoker(self, max_history: Optional[int] = None) -> CommandInvoker:
        """
        创建命令调用者
        
        Args:
            max_history: 最大命令历史数（可选，默认100）
            
        Returns:
            CommandInvoker实例
        """
        max_hist = max_history or self.config.get('command_max_history', 100)
        return CommandInvoker(max_history=max_hist)
    
    def create_state_machine(self) -> GameStateMachine:
        """
        创建状态机
        
        Returns:
            GameStateMachine实例
        """
        return GameStateMachine()
    
    def create_complete_game_components(self) -> Dict[str, Any]:
        """
        创建完整的游戏组件集合
        
        Returns:
            dict: 包含所有核心组件的字典
        """
        board_manager = self.create_board_manager()
        history_manager = self.create_history_manager()
        command_invoker = self.create_command_invoker()
        state_machine = self.create_state_machine()
        
        return {
            'board_manager': board_manager,
            'history_manager': history_manager,
            'command_invoker': command_invoker,
            'state_machine': state_machine,
            'move_validator': lambda turn: self.create_move_validator(board_manager, turn)
        }
    
    @staticmethod
    def create_default_factory() -> 'GameComponentFactory':
        """
        创建使用默认配置的工厂
        
        Returns:
            GameComponentFactory实例
        """
        return GameComponentFactory()
    
    @staticmethod
    def create_custom_factory(config: Dict[str, Any]) -> 'GameComponentFactory':
        """
        创建使用自定义配置的工厂
        
        Args:
            config: 自定义配置字典
            
        Returns:
            GameComponentFactory实例
        """
        return GameComponentFactory(config)


# 便捷函数
def create_game_components(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    便捷函数：创建完整的游戏组件集合
    
    Args:
        config: 可选的配置字典
        
    Returns:
        dict: 包含所有核心组件的字典
    """
    factory = GameComponentFactory(config)
    return factory.create_complete_game_components()

