"""
完整的走子命令实现 - 支持熊汉象棋所有特殊规则
"""
from typing import List, Optional
from desktop.core.commands import MoveCommand, MoveData
from desktop.core.chess_pieces import Jia, Ci, Dun, King, Pawn


class XionghanMoveCommand(MoveCommand):
    """
    熊汉象棋完整走子命令
    支持所有特殊规则：甲/胄连线吃子、刺兑子、兵卒升变等
    """
    
    def __init__(self, move_data: MoveData, game_state_ref):
        super().__init__(move_data, game_state_ref)
        
        # 保存执行前的状态（用于撤销）
        self._saved_pieces_state = None
        self._saved_captured_state = None
        self._saved_player_turn = None
        self._saved_game_over = None
        self._saved_winner = None
        
        # 记录实际被移除的棋子（用于撤销时恢复）
        self._removed_pieces = []
        self._added_to_captured = []
    
    def _do_execute(self) -> bool:
        """
        执行完整的熊汉象棋走子逻辑
        
        Returns:
            bool: 是否执行成功
        """
        piece = self.move_data.piece
        from_row = self.move_data.from_row
        from_col = self.move_data.from_col
        to_row = self.move_data.to_row
        to_col = self.move_data.to_col
        
        # 1. 保存当前状态（用于撤销）
        self._save_state()
        
        # 2. 处理直接吃子（目标位置的棋子）
        if self.move_data.captured_piece:
            self._capture_piece(self.move_data.captured_piece)
            
            # 检查是否吃掉将/帅，游戏结束
            if isinstance(self.move_data.captured_piece, King):
                self._end_game(piece.color)
                return True
        
        # 3. 执行移动
        piece.move_to(to_row, to_col)
        
        # 4. 处理甲/胄连线吃子
        jia_captures = self._handle_jia_capture(piece)
        
        # 5. 处理刺兑子
        ci_captures = self._handle_ci_exchange(piece, from_row, from_col, to_row, to_col)
        
        # 6. 检查是否需要升变
        self._check_promotion(piece, to_row)
        
        # 7. 切换玩家回合（如果不是升变状态）
        if not self.game_state.needs_promotion:
            self._switch_turn()
        
        return True
    
    def _do_undo(self) -> bool:
        """
        撤销走子
        
        Returns:
            bool: 是否撤销成功
        """
        if not self._saved_pieces_state:
            return False
        
        # 恢复棋子位置
        piece = self.move_data.piece
        piece.move_to(self.move_data.from_row, self.move_data.from_col)
        
        # 恢复被吃掉的棋子
        self._restore_captured_pieces()
        
        # 恢复游戏状态
        self._restore_state()
        
        return True
    
    def _save_state(self):
        """保存当前游戏状态"""
        import copy
        self._saved_pieces_state = [
            (p, p.row, p.col) for p in self.game_state.pieces
        ]
        self._saved_captured_state = {
            'red': self.game_state.captured_pieces['red'][:],
            'black': self.game_state.captured_pieces['black'][:]
        }
        self._saved_player_turn = self.game_state.player_turn
        self._saved_game_over = self.game_state.game_over
        self._saved_winner = self.game_state.winner
    
    def _restore_state(self):
        """恢复游戏状态"""
        self.game_state.player_turn = self._saved_player_turn
        self.game_state.game_over = self._saved_game_over
        self.game_state.winner = self._saved_winner
    
    def _capture_piece(self, piece):
        """吃掉棋子"""
        if piece in self.game_state.pieces:
            self.game_state.pieces.remove(piece)
            self.game_state.captured_pieces[piece.color].append(piece)
            self._removed_pieces.append(piece)
            self._added_to_captured.append((piece, piece.color))
    
    def _restore_captured_pieces(self):
        """恢复被吃掉的棋子"""
        # 从棋盘中移除后来添加的棋子
        for piece in self._removed_pieces:
            if piece in self.game_state.pieces:
                self.game_state.pieces.remove(piece)
        
        # 从阵亡列表中移除
        for piece, color in self._added_to_captured:
            if piece in self.game_state.captured_pieces[color]:
                self.game_state.captured_pieces[color].remove(piece)
        
        # 恢复原始棋子列表
        self.game_state.pieces.clear()
        for piece, row, col in self._saved_pieces_state:
            piece.move_to(row, col)
            self.game_state.pieces.append(piece)
        
        # 恢复阵亡列表
        self.game_state.captured_pieces['red'] = self._saved_captured_state['red'][:]
        self.game_state.captured_pieces['black'] = self._saved_captured_state['black'][:]
        
        # 清空跟踪列表
        self._removed_pieces.clear()
        self._added_to_captured.clear()
    
    def _handle_jia_capture(self, piece) -> List:
        """
        处理甲/胄连线吃子
        
        Returns:
            List: 被吃掉的棋子列表
        """
        if not isinstance(piece, Jia):
            return []
        
        from desktop.core.game_rules import GameRules
        captures = GameRules.find_jia_capture_moves(self.game_state.pieces, piece)
        
        for captured in captures:
            self._capture_piece(captured)
            
            # 检查是否吃掉将/帅
            if isinstance(captured, King):
                self._end_game(piece.color)
        
        return captures
    
    def _handle_ci_exchange(self, piece, from_row, from_col, to_row, to_col) -> List:
        """
        处理刺兑子
        
        Returns:
            List: 参与兑子的棋子列表
        """
        if not isinstance(piece, Ci):
            return []
        
        from desktop.core.game_state import GameState
        from desktop.core.game_rules import GameRules
        
        # 计算反方向
        row_diff = to_row - from_row
        col_diff = to_col - from_col
        reverse_row = from_row - row_diff
        reverse_col = from_col - col_diff
        
        # 检查反方向是否有敌棋
        if not GameState.is_position_on_board(reverse_row, reverse_col):
            return []
        
        reverse_piece = GameRules.get_piece_at(self.game_state.pieces, reverse_row, reverse_col)
        
        # 检查兑子条件
        if not reverse_piece or reverse_piece.color == piece.color:
            return []
        
        # 盾不可被兑子
        if isinstance(reverse_piece, Dun):
            return []
        
        # 检查是否有敌方盾相邻
        if self._is_shield_nearby(piece, to_row, to_col):
            return []
        
        # 执行兑子
        captures = []
        
        # 移除刺本身
        if piece in self.game_state.pieces:
            self.game_state.pieces.remove(piece)
            self.game_state.captured_pieces[piece.color].append(piece)
            captures.append(piece)
        
        # 移除反方向的敌棋
        if reverse_piece in self.game_state.pieces:
            self.game_state.pieces.remove(reverse_piece)
            self.game_state.captured_pieces[reverse_piece.color].append(reverse_piece)
            captures.append(reverse_piece)
            
            # 检查是否兑掉将/帅
            if isinstance(reverse_piece, King):
                self._end_game(piece.color)
        
        return captures
    
    def _is_shield_nearby(self, piece, row, col) -> bool:
        """检查是否有敌方盾相邻"""
        for p in self.game_state.pieces:
            # 防御性检查：确保p不为None
            if p is None:
                continue
            if isinstance(p, Dun) and p.color != piece.color:
                row_diff = abs(p.row - row)
                col_diff = abs(p.col - col)
                if row_diff <= 1 and col_diff <= 1 and (row_diff != 0 or col_diff != 0):
                    return True
        return False
    
    def _check_promotion(self, piece, to_row):
        """检查是否需要升变"""
        if not isinstance(piece, Pawn):
            return
        
        from desktop.utils import tools
        from desktop.controllers.game_config_manager import game_config
        
        if (tools.is_pawn_at_opponent_base(piece, to_row) and
                game_config.get_setting("pawn_promotion_enabled", True)):
            self.game_state.needs_promotion = True
            self.game_state.promotion_pawn = piece
            self.game_state.available_promotion_pieces = \
                self.game_state.get_available_promotion_pieces(piece.color)
    
    def _switch_turn(self):
        """切换玩家回合"""
        opponent_color = "black" if self.game_state.player_turn == "red" else "red"
        
        # 检查将军
        from desktop.core.game_rules import GameRules
        self.game_state.is_check = GameRules.is_check(self.game_state.pieces, opponent_color)
        
        if self.game_state.is_check:
            import time
            self.game_state.check_animation_time = time.time()
        
        # 检查游戏结束
        game_over, winner = GameRules.is_game_over(self.game_state.pieces, self.game_state.player_turn)
        
        if game_over:
            self._end_game(winner)
        else:
            # 检查和棋
            if self.game_state.is_draw():
                self.game_state.game_over = True
                self.game_state.winner = None
            else:
                # 切换回合
                self.game_state.player_turn = opponent_color
                import time
                self.game_state.current_turn_start_time = time.time()
    
    def _end_game(self, winner: str):
        """结束游戏"""
        self.game_state.game_over = True
        self.game_state.winner = winner
        
        import time
        self.game_state.total_time = max(0.0, time.time() - self.game_state.start_time)

