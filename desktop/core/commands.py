"""
命令模式 - 走子命令系统
将走子操作封装为命令对象，支持撤销/重做
"""
from abc import ABC, abstractmethod
from typing import Optional, Tuple, List, Any
from dataclasses import dataclass, field

from desktop.core.chess_pieces import ChessPiece


@dataclass
class MoveData:
    """移动数据类"""
    piece: ChessPiece
    from_row: int
    from_col: int
    to_row: int
    to_col: int
    captured_piece: Optional[ChessPiece] = None
    jia_captures: List[ChessPiece] = field(default_factory=list)
    ci_captures: List[ChessPiece] = field(default_factory=list)
    
    @property
    def from_pos(self) -> Tuple[int, int]:
        return (self.from_row, self.from_col)
    
    @property
    def to_pos(self) -> Tuple[int, int]:
        return (self.to_row, self.to_col)


class Command(ABC):
    """命令基类"""
    
    def __init__(self, name: str = "Command"):
        self.name = name
        self.executed = False
    
    @abstractmethod
    def execute(self) -> bool:
        """执行命令"""
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        """撤销命令"""
        pass
    
    def redo(self) -> bool:
        """重做命令（默认重新执行）"""
        return self.execute()
    
    def __repr__(self):
        return f"{self.__class__.__name__}(executed={self.executed})"


class MoveCommand(Command):
    """
    走子命令基类
    封装棋子的移动操作，支持撤销/重做
    """
    
    def __init__(self, move_data: MoveData, game_state_ref: Any):
        super().__init__(name="MoveCommand")
        self.move_data = move_data
        self.game_state = game_state_ref
        
        # 保存撤销所需的状态
        self._previous_position: Optional[Tuple[int, int]] = None
        self._captured_piece_restored = False
        self._jia_pieces_restored = []
        self._ci_pieces_restored = []
    
    def execute(self) -> bool:
        """执行移动命令"""
        if self.executed:
            return False
        
        try:
            # 委托给GameState执行实际移动
            success = self._do_execute()
            if success:
                self.executed = True
            return success
        except Exception as e:
            print(f"执行移动命令失败: {e}")
            return False
    
    def undo(self) -> bool:
        """撤销移动命令"""
        if not self.executed:
            return False
        
        try:
            success = self._do_undo()
            if success:
                self.executed = False
            return success
        except Exception as e:
            print(f"撤销移动命令失败: {e}")
            return False
    
    @abstractmethod
    def _do_execute(self) -> bool:
        """执行移动的具体逻辑（子类实现）"""
        pass
    
    @abstractmethod
    def _do_undo(self) -> bool:
        """撤销移动的具体逻辑（子类实现）"""
        pass
    
    def __repr__(self):
        return (f"MoveCommand("
                f"piece={self.move_data.piece.name}, "
                f"from={self.move_data.from_pos}, "
                f"to={self.move_data.to_pos}, "
                f"executed={self.executed})")


class SimpleMoveCommand(MoveCommand):
    """
    简单移动命令
    处理普通的棋子移动（无特殊规则）
    """
    
    def _do_execute(self) -> bool:
        """执行简单移动"""
        piece = self.move_data.piece
        
        # 保存原始位置用于撤销
        self._previous_position = (piece.row, piece.col)
        
        # 执行移动
        piece.move_to(self.move_data.to_row, self.move_data.to_col)
        
        # 处理被吃掉的棋子
        if self.move_data.captured_piece:
            self.game_state.pieces.remove(self.move_data.captured_piece)
            self.game_state.captured_pieces[self.move_data.captured_piece.color].append(
                self.move_data.captured_piece
            )
            self._captured_piece_restored = False
        
        return True
    
    def _do_undo(self) -> bool:
        """撤销简单移动"""
        piece = self.move_data.piece
        
        # 恢复棋子位置
        if self._previous_position:
            piece.move_to(self._previous_position[0], self._previous_position[1])
        
        # 恢复被吃掉的棋子
        if self.move_data.captured_piece and not self._captured_piece_restored:
            captured = self.move_data.captured_piece
            if captured in self.game_state.captured_pieces[captured.color]:
                self.game_state.captured_pieces[captured.color].remove(captured)
            self.game_state.pieces.append(captured)
            self._captured_piece_restored = True
        
        return True


class JiaCaptureCommand(MoveCommand):
    """
    甲/胄连线吃子命令
    处理甲/胄的特殊吃子规则
    """
    
    def _do_execute(self) -> bool:
        """执行甲/胄吃子"""
        # 先执行基础移动
        base_success = super()._do_execute()
        if not base_success:
            return False
        
        # 处理甲/胄连线吃掉的棋子
        for captured in self.move_data.jia_captures:
            if captured in self.game_state.pieces:
                self.game_state.pieces.remove(captured)
                self.game_state.captured_pieces[captured.color].append(captured)
                self._jia_pieces_restored.append(captured)
        
        return True
    
    def _do_undo(self) -> bool:
        """撤销甲/胄吃子"""
        # 先恢复基础移动
        base_success = super()._do_undo()
        if not base_success:
            return False
        
        # 恢复甲/胄吃掉的棋子
        for captured in self._jia_pieces_restored:
            if captured in self.game_state.captured_pieces[captured.color]:
                self.game_state.captured_pieces[captured.color].remove(captured)
            if captured not in self.game_state.pieces:
                self.game_state.pieces.append(captured)
        
        self._jia_pieces_restored.clear()
        return True


class CiExchangeCommand(MoveCommand):
    """
    刺兑子命令
    处理刺的特殊兑子规则（双方都阵亡）
    """
    
    def _do_execute(self) -> bool:
        """执行刺兑子"""
        # 刺已经在移动中被移除（在_do_execute中）
        # 这里主要处理反方向的敌方棋子
        for captured in self.move_data.ci_captures:
            if captured != self.move_data.piece:  # 排除刺本身
                if captured in self.game_state.pieces:
                    self.game_state.pieces.remove(captured)
                    self.game_state.captured_pieces[captured.color].append(captured)
                    self._ci_pieces_restored.append(captured)
        
        return True
    
    def _do_undo(self) -> bool:
        """撤销刺兑子"""
        # 恢复刺本身
        piece = self.move_data.piece
        if piece not in self.game_state.pieces:
            self.game_state.pieces.append(piece)
            if piece in self.game_state.captured_pieces[piece.color]:
                self.game_state.captured_pieces[piece.color].remove(piece)
        
        # 恢复被兑掉的敌方棋子
        for captured in self._ci_pieces_restored:
            if captured in self.game_state.captured_pieces[captured.color]:
                self.game_state.captured_pieces[captured.color].remove(captured)
            if captured not in self.game_state.pieces:
                self.game_state.pieces.append(captured)
        
        self._ci_pieces_restored.clear()
        return True


class PromotionCommand(Command):
    """
    兵卒升变命令
    处理兵/卒到达底线后的升变操作
    """
    
    def __init__(self, pawn: ChessPiece, new_piece_class: type, game_state_ref: Any):
        super().__init__(name="PromotionCommand")
        self.pawn = pawn
        self.new_piece_class = new_piece_class
        self.game_state = game_state_ref
        
        self._promoted_piece: Optional[ChessPiece] = None
        self._pawn_was_in_list = True
    
    def execute(self) -> bool:
        """执行升变"""
        if self.executed:
            return False
        
        try:
            # 从棋盘中移除兵/卒
            if self.pawn in self.game_state.pieces:
                self.game_state.pieces.remove(self.pawn)
            else:
                self._pawn_was_in_list = False
            
            # 创建新棋子（保持原位置）
            self._promoted_piece = self.new_piece_class(
                self.pawn.color,
                self.pawn.row,
                self.pawn.col
            )
            self._promoted_piece.name = self.pawn.name  # 保持名称
            
            # 添加到棋盘
            self.game_state.pieces.append(self._promoted_piece)
            
            self.executed = True
            return True
        except Exception as e:
            print(f"执行升变命令失败: {e}")
            return False
    
    def undo(self) -> bool:
        """撤销升变"""
        if not self.executed:
            return False
        
        try:
            # 移除升变后的棋子
            if self._promoted_piece and self._promoted_piece in self.game_state.pieces:
                self.game_state.pieces.remove(self._promoted_piece)
            
            # 恢复兵/卒
            if self._pawn_was_in_list:
                self.game_state.pieces.append(self.pawn)
            
            self.executed = False
            return True
        except Exception as e:
            print(f"撤销升变命令失败: {e}")
            return False


class ResurrectionCommand(Command):
    """
    兵卒复活命令
    处理兵/卒的复活操作
    """
    
    def __init__(self, color: str, position: Tuple[int, int], game_state_ref: Any):
        super().__init__(name="ResurrectionCommand")
        self.color = color
        self.position = position
        self.game_state = game_state_ref
        
        self._resurrected_pawn: Optional[ChessPiece] = None
        self._removed_from_captured = False
    
    def execute(self) -> bool:
        """执行复活"""
        if self.executed:
            return False
        
        try:
            row, col = self.position
            
            # 从阵亡列表中移除一个兵/卒
            for captured in self.game_state.captured_pieces[self.color][:]:
                from desktop.core.chess_pieces import Pawn
                if isinstance(captured, Pawn):
                    self.game_state.captured_pieces[self.color].remove(captured)
                    self._removed_from_captured = True
                    break
            
            # 创建新的兵/卒
            from desktop.core.chess_pieces import Pawn
            self._resurrected_pawn = Pawn(self.color, row, col)
            self.game_state.pieces.append(self._resurrected_pawn)
            
            self.executed = True
            return True
        except Exception as e:
            print(f"执行复活命令失败: {e}")
            return False
    
    def undo(self) -> bool:
        """撤销复活"""
        if not self.executed:
            return False
        
        try:
            # 移除复活的兵/卒
            if self._resurrected_pawn and self._resurrected_pawn in self.game_state.pieces:
                self.game_state.pieces.remove(self._resurrected_pawn)
            
            # 恢复到阵亡列表
            if self._removed_from_captured and self._resurrected_pawn:
                from desktop.core.chess_pieces import Pawn
                pawn = Pawn(self.color, self.position[0], self.position[1])
                self.game_state.captured_pieces[self.color].append(pawn)
            
            self.executed = False
            return True
        except Exception as e:
            print(f"撤销复活命令失败: {e}")
            return False

