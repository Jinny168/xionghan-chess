"""
棋盘管理器 - 负责棋盘的维护和棋子管理
从GameState中提取的棋盘管理逻辑
"""
from typing import List, Optional, Dict
from desktop.core.chess_pieces import ChessPiece, King
from desktop.core.game_rules import GameRules


class BoardManager:
    """
    棋盘管理器
    封装所有与棋盘状态和棋子管理相关的逻辑
    """
    
    def __init__(self, pieces: List[ChessPiece]):
        """
        初始化棋盘管理器
        
        Args:
            pieces: 初始棋子列表
        """
        self.pieces = pieces.copy()  # 使用副本避免外部修改
    
    def get_piece_at(self, row: int, col: int) -> Optional[ChessPiece]:
        """
        获取指定位置的棋子
        
        Args:
            row, col: 位置坐标
            
        Returns:
            棋子对象或None
        """
        return GameRules.get_piece_at(self.pieces, row, col)
    
    def move_piece(self, piece: ChessPiece, to_row: int, to_col: int):
        """
        移动棋子到新位置
        
        Args:
            piece: 要移动的棋子
            to_row, to_col: 目标位置
        """
        piece.move_to(to_row, to_col)
    
    def remove_piece(self, piece: ChessPiece) -> bool:
        """
        从棋盘移除棋子
        
        Args:
            piece: 要移除的棋子
            
        Returns:
            bool: 是否成功移除
        """
        if piece in self.pieces:
            self.pieces.remove(piece)
            return True
        return False
    
    def add_piece(self, piece: ChessPiece):
        """
        添加棋子到棋盘
        
        Args:
            piece: 要添加的棋子
        """
        self.pieces.append(piece)
    
    def capture_piece(self, piece: ChessPiece, captured_pieces: Dict[str, List[ChessPiece]]):
        """
        吃掉棋子并记录到阵亡列表
        
        Args:
            piece: 被吃掉的棋子
            captured_pieces: 阵亡棋子字典 {color: [pieces]}
            
        Returns:
            str: 棋子类型名称
        """
        self.remove_piece(piece)
        captured_pieces[piece.color].append(piece)
        return piece.__class__.__name__.lower()
    
    def restore_captured_piece(self, piece: ChessPiece, captured_pieces: Dict[str, List[ChessPiece]]):
        """
        恢复被吃掉的棋子（用于悔棋）
        
        Args:
            piece: 要恢复的棋子
            captured_pieces: 阵亡棋子字典
        """
        # 从阵亡列表中移除
        if piece in captured_pieces[piece.color]:
            captured_pieces[piece.color].remove(piece)
        
        # 添加到棋盘
        self.add_piece(piece)
    
    def get_all_pieces_of_color(self, color: str) -> List[ChessPiece]:
        """
        获取指定颜色的所有棋子
        
        Args:
            color: 颜色 ('red' or 'black')
            
        Returns:
            棋子列表
        """
        return [p for p in self.pieces if p is not None and p.color == color]
    
    def get_king_position(self, color: str) -> Optional[tuple]:
        """
        获取指定颜色的将/帅位置
        
        Args:
            color: 颜色
            
        Returns:
            (row, col) 或 None
        """
        for piece in self.pieces:
            # 防御性检查：确保piece不为None
            if piece is None:
                continue
            if isinstance(piece, King) and piece.color == color:
                return (piece.row, piece.col)
        return None
    
    def has_king(self, color: str) -> bool:
        """
        检查指定颜色是否还有将/帅
        
        Args:
            color: 颜色
            
        Returns:
            bool: 是否有将/帅
        """
        return any(p is not None and isinstance(p, King) and p.color == color for p in self.pieces)
    
    def get_pieces_count(self) -> int:
        """
        获取棋盘上棋子总数
        
        Returns:
            int: 棋子数量
        """
        return len(self.pieces)
    
    def get_pieces_by_type(self) -> Dict[str, int]:
        """
        统计各种类型棋子的数量
        
        Returns:
            dict: {type_name: count}
        """
        counts = {}
        for piece in self.pieces:
            # 防御性检查：确保piece不为None
            if piece is None:
                continue
            type_name = piece.__class__.__name__
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts
    
    def clear_board(self):
        """清空棋盘"""
        self.pieces.clear()
    
    def reset_pieces(self, new_pieces: List[ChessPiece]):
        """
        重置棋盘上的棋子
        
        Args:
            new_pieces: 新的棋子列表
        """
        self.pieces = new_pieces.copy()
    
    def get_board_state(self) -> List[ChessPiece]:
        """
        获取当前棋盘状态的副本
        
        Returns:
            棋子列表副本
        """
        return self.pieces.copy()
    
    def is_empty(self) -> bool:
        """
        检查棋盘是否为空
        
        Returns:
            bool: 是否为空
        """
        return len(self.pieces) == 0
    
    def __repr__(self):
        return f"BoardManager(pieces={len(self.pieces)})"

