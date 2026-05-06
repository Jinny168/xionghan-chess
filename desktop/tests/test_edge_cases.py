"""
边界情况测试 - 测试各种异常和边界条件
"""
import pytest
from desktop.core import (
    BoardManager,
    MoveValidator,
    HistoryManager,
    CommandInvoker,
)
from desktop.core.chess_pieces import create_initial_pieces, Pawn, King


class TestBoardManagerEdgeCases:
    """棋盘管理器边界情况测试"""
    
    def test_empty_board(self):
        """测试空棋盘"""
        manager = BoardManager([])
        
        assert manager.is_empty() is True
        assert manager.get_pieces_count() == 0
    
    def test_get_piece_at_invalid_position(self):
        """测试获取无效位置的棋子"""
        pieces = create_initial_pieces()
        manager = BoardManager(pieces)
        
        # 超出棋盘范围
        piece = manager.get_piece_at(100, 100)
        assert piece is None
        
        # 负数坐标
        piece = manager.get_piece_at(-1, -1)
        assert piece is None
    
    def test_remove_nonexistent_piece(self):
        """测试移除不存在的棋子"""
        pieces = create_initial_pieces()
        manager = BoardManager(pieces)
        
        initial_count = manager.get_pieces_count()
        fake_piece = Pawn("red", 0, 0)
        
        success = manager.remove_piece(fake_piece)
        assert success is False
        assert manager.get_pieces_count() == initial_count
    
    def test_add_duplicate_piece(self):
        """测试添加重复棋子"""
        pieces = create_initial_pieces()
        manager = BoardManager(pieces)
        
        pawn = Pawn("red", 8, 0)
        initial_count = manager.get_pieces_count()
        
        manager.add_piece(pawn)
        manager.add_piece(pawn)  # 添加两次
        
        assert manager.get_pieces_count() == initial_count + 2


class TestMoveValidatorEdgeCases:
    """移动验证器边界情况测试"""
    
    def test_none_piece(self):
        """测试None棋子"""
        pieces = create_initial_pieces()
        validator = MoveValidator(pieces, "red")
        
        # 不应该崩溃
        result = validator.is_own_piece(None)
        assert result is False
    
    def test_empty_pieces_list(self):
        """测试空棋子列表"""
        validator = MoveValidator([], "red")
        
        assert validator.player_turn == "red"
        assert len(validator.pieces) == 0
    
    def test_validate_move_out_of_bounds(self):
        """测试验证超出边界的移动"""
        pieces = create_initial_pieces()
        validator = MoveValidator(pieces, "red")
        
        pawn = [p for p in pieces if isinstance(p, Pawn) and p.color == "red"][0]
        
        # 移动到棋盘外
        result = validator.is_valid_move(pawn, pawn.row, pawn.col, 100, 100)
        assert result is False


class TestHistoryManagerEdgeCases:
    """历史记录管理器边界情况测试"""
    
    def test_pop_from_empty_history(self):
        """测试从空历史中弹出"""
        manager = HistoryManager()
        
        move = manager.pop_last_move()
        assert move is None
    
    def test_undo_with_no_history(self):
        """测试没有历史时悔棋"""
        manager = HistoryManager()
        
        assert manager.can_undo() is False
    
    def test_max_history_zero(self):
        """测试最大历史为0"""
        manager = HistoryManager(max_history=0)
        piece = Pawn("red", 8, 0)
        
        manager.record_move(piece, 8, 0, 7, 0)
        
        # 应该立即被清除
        assert manager.get_move_count() == 0
    
    def test_record_same_position_multiple_times(self):
        """测试记录相同局面多次"""
        manager = HistoryManager()
        pieces = create_initial_pieces()
        
        # 记录相同局面10次
        for _ in range(10):
            manager.record_board_position(pieces)
        
        assert manager.is_repeated_position(3) is True
        assert manager.repetition_count[manager.board_position_history[-1]] == 10
    
    def test_clear_history_when_empty(self):
        """测试清空空历史"""
        manager = HistoryManager()
        
        # 不应该崩溃
        manager.clear_history()
        assert manager.get_move_count() == 0


class TestCommandInvokerEdgeCases:
    """命令调用者边界情况测试"""
    
    def test_execute_none_command(self):
        """测试执行None命令"""
        invoker = CommandInvoker()
        
        result = invoker.execute_command(None)
        assert result is False
    
    def test_undo_with_empty_stack(self):
        """测试空栈时撤销"""
        invoker = CommandInvoker()
        
        result = invoker.undo()
        assert result is False
    
    def test_redo_with_empty_stack(self):
        """测试空栈时重做"""
        invoker = CommandInvoker()
        
        result = invoker.redo()
        assert result is False
    
    def test_execute_failing_command(self):
        """测试执行失败的命令"""
        from unittest.mock import Mock
        invoker = CommandInvoker()
        
        command = Mock()
        command.execute.return_value = False
        
        result = invoker.execute_command(command)
        assert result is False
        assert invoker.can_undo() is False
    
    def test_undo_failing_command(self):
        """测试撤销失败的命令"""
        from unittest.mock import Mock
        invoker = CommandInvoker()
        
        command = Mock()
        command.execute.return_value = True
        command.undo.return_value = False
        
        invoker.execute_command(command)
        result = invoker.undo()
        
        assert result is False
        # 撤销失败，命令应该还在撤销栈中
        assert invoker.can_undo() is True
    
    def test_max_history_one(self):
        """测试最大历史为1"""
        invoker = CommandInvoker(max_history=1)
        
        from unittest.mock import Mock
        for i in range(5):
            command = Mock()
            command.execute.return_value = True
            invoker.execute_command(command)
        
        # 只保留最后一个
        assert invoker.get_undo_stack_size() == 1


class TestIntegrationEdgeCases:
    """集成边界情况测试"""
    
    def test_components_isolation(self):
        """测试组件隔离性"""
        board1 = BoardManager(create_initial_pieces())
        board2 = BoardManager(create_initial_pieces())
        
        # 修改board1不应该影响board2
        initial_count = board2.get_pieces_count()
        if board1.pieces:
            board1.clear_board()
        
        assert board2.get_pieces_count() == initial_count
        assert board1.is_empty() is True
    
    def test_validator_with_modified_board(self):
        """测试验证器与修改后的棋盘"""
        pieces = create_initial_pieces()
        board = BoardManager(pieces)
        
        # 移除一些棋子
        if board.pieces:
            board.remove_piece(board.pieces[0])
        
        # 创建验证器使用修改后的棋盘
        validator = MoveValidator(board.pieces, "red")
        
        # 不应该崩溃
        assert validator.player_turn == "red"
    
    def test_history_with_rapid_moves(self):
        """测试快速连续走子"""
        manager = HistoryManager(max_history=100)
        piece = Pawn("red", 8, 0)
        
        # 快速记录1000步
        for i in range(1000):
            row = 8 - (i % 8)
            manager.record_move(piece, row, 0, row - 1, 0)
        
        # 应该限制在max_history
        assert manager.get_move_count() <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

