"""
历史记录管理器 - 负责走子历史和局面记录
从GameState中提取的历史管理逻辑
"""
from typing import List, Tuple, Optional, Dict
from desktop.core.chess_pieces import ChessPiece
from desktop.core.game_rules import GameRules


class MoveRecord:
    """走子记录数据类"""
    
    def __init__(self, piece: ChessPiece, from_row: int, from_col: int,
                 to_row: int, to_col: int, captured_piece: Optional[ChessPiece] = None,
                 jia_captures: Optional[List[ChessPiece]] = None,
                 ci_captures: Optional[List[ChessPiece]] = None):
        self.piece = piece
        self.from_row = from_row
        self.from_col = from_col
        self.to_row = to_row
        self.to_col = to_col
        self.captured_piece = captured_piece
        self.jia_captures = jia_captures or []
        self.ci_captures = ci_captures or []
    
    @property
    def from_pos(self) -> Tuple[int, int]:
        return (self.from_row, self.from_col)
    
    @property
    def to_pos(self) -> Tuple[int, int]:
        return (self.to_row, self.to_col)
    
    def to_tuple(self) -> tuple:
        """转换为元组格式（兼容旧代码）"""
        return (
            self.piece,
            self.from_row,
            self.from_col,
            self.to_row,
            self.to_col,
            self.captured_piece,
            self.jia_captures[:],
            self.ci_captures[:]
        )
    
    def __repr__(self):
        return (f"MoveRecord({self.piece.name}, "
                f"{self.from_pos}->{self.to_pos}, "
                f"captured={self.captured_piece is not None})")


class HistoryManager:
    """
    历史记录管理器
    封装所有与走子历史、局面记录和悔棋相关的逻辑
    """
    
    def __init__(self, max_history: int = 100):
        """
        初始化历史记录管理器
        
        Args:
            max_history: 最大历史记录数
        """
        self.max_history = max_history
        self.move_history: List[MoveRecord] = []
        
        # 局面历史记录（用于检测重复局面）
        self.board_position_history: List[str] = []
        self.repetition_count: Dict[str, int] = {}
    
    def record_move(self, piece: ChessPiece, from_row: int, from_col: int,
                   to_row: int, to_col: int, captured_piece: Optional[ChessPiece] = None,
                   jia_captures: Optional[List[ChessPiece]] = None,
                   ci_captures: Optional[List[ChessPiece]] = None):
        """
        记录一次走子
        
        Args:
            piece: 移动的棋子
            from_row, from_col: 起始位置
            to_row, to_col: 目标位置
            captured_piece: 被吃掉的棋子
            jia_captures: 甲/胄连线吃掉的棋子列表
            ci_captures: 刺兑子涉及的棋子列表
        """
        record = MoveRecord(
            piece=piece,
            from_row=from_row,
            from_col=from_col,
            to_row=to_row,
            to_col=to_col,
            captured_piece=captured_piece,
            jia_captures=jia_captures,
            ci_captures=ci_captures
        )
        
        self.move_history.append(record)
        
        # 限制历史记录大小
        if len(self.move_history) > self.max_history:
            self.move_history.pop(0)
    
    def get_last_move(self) -> Optional[MoveRecord]:
        """
        获取最后一次走子记录
        
        Returns:
            MoveRecord或None
        """
        return self.move_history[-1] if self.move_history else None
    
    def pop_last_move(self) -> Optional[MoveRecord]:
        """
        弹出并返回最后一次走子记录
        
        Returns:
            MoveRecord或None
        """
        return self.move_history.pop() if self.move_history else None
    
    def can_undo(self) -> bool:
        """
        检查是否可以悔棋
        
        Returns:
            bool: 是否有历史记录
        """
        return len(self.move_history) > 0
    
    def get_move_count(self) -> int:
        """
        获取走子总数
        
        Returns:
            int: 走子数
        """
        return len(self.move_history)
    
    def clear_history(self):
        """清空历史记录"""
        self.move_history.clear()
        self.clear_board_history()
    
    def record_board_position(self, pieces: List[ChessPiece]):
        """
        记录当前局面（用于检测重复局面）
        
        Args:
            pieces: 当前棋盘上的所有棋子
        """
        board_hash = GameRules.get_board_hash(pieces)
        self.board_position_history.append(board_hash)
        
        # 更新重复计数
        if board_hash in self.repetition_count:
            self.repetition_count[board_hash] += 1
        else:
            self.repetition_count[board_hash] = 1
    
    def undo_board_position(self):
        """撤销局面记录（用于悔棋）"""
        if self.board_position_history:
            removed_hash = self.board_position_history.pop()
            
            # 更新重复计数
            if removed_hash in self.repetition_count:
                self.repetition_count[removed_hash] -= 1
                if self.repetition_count[removed_hash] <= 0:
                    del self.repetition_count[removed_hash]
    
    def clear_board_history(self):
        """清空局面历史"""
        self.board_position_history.clear()
        self.repetition_count.clear()
    
    def is_repeated_position(self, min_repetitions: int = 3) -> bool:
        """
        检查是否出现重复局面
        
        Args:
            min_repetitions: 最小重复次数
            
        Returns:
            bool: 是否重复
        """
        if not self.board_position_history:
            return False
        
        current_hash = self.board_position_history[-1]
        return self.repetition_count.get(current_hash, 0) >= min_repetitions
    
    def get_repetition_count(self) -> Dict[str, int]:
        """
        获取所有局面的重复次数
        
        Returns:
            dict: {hash: count}
        """
        return self.repetition_count.copy()
    
    def get_history_summary(self) -> dict:
        """
        获取历史记录摘要
        
        Returns:
            dict: 包含各种统计信息
        """
        return {
            'total_moves': len(self.move_history),
            'board_positions_recorded': len(self.board_position_history),
            'unique_positions': len(self.repetition_count),
            'max_repetition': max(self.repetition_count.values()) if self.repetition_count else 0
        }
    
    def __repr__(self):
        return (f"HistoryManager(moves={len(self.move_history)}, "
                f"positions={len(self.board_position_history)})")

