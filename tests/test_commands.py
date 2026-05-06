"""
单元测试 - 命令模式测试
"""
import pytest
from unittest.mock import Mock, MagicMock
from program.core.commands import (
    MoveData,
    SimpleMoveCommand,
    PromotionCommand,
    ResurrectionCommand,
)
from program.core.command_invoker import CommandInvoker
from program.core.chess_pieces import Pawn, King


class TestMoveData:
    """移动数据测试"""
    
    def test_create_move_data(self):
        """测试创建移动数据"""
        piece = Mock()
        move_data = MoveData(
            piece=piece,
            from_row=0,
            from_col=0,
            to_row=1,
            to_col=1
        )
        
        assert move_data.piece == piece
        assert move_data.from_pos == (0, 0)
        assert move_data.to_pos == (1, 1)
        assert move_data.captured_piece is None
    
    def test_move_data_with_captured(self):
        """测试带吃子的移动数据"""
        piece = Mock()
        captured = Mock()
        move_data = MoveData(
            piece=piece,
            from_row=0,
            from_col=0,
            to_row=1,
            to_col=1,
            captured_piece=captured
        )
        
        assert move_data.captured_piece == captured


class TestSimpleMoveCommand:
    """简单移动命令测试"""
    
    def test_execute_simple_move(self):
        """测试执行简单移动"""
        # 创建模拟对象
        piece = Mock()
        piece.row = 0
        piece.col = 0
        
        game_state = Mock()
        game_state.pieces = [piece]
        game_state.captured_pieces = {"red": [], "black": []}
        
        move_data = MoveData(
            piece=piece,
            from_row=0,
            from_col=0,
            to_row=1,
            to_col=1
        )
        
        command = SimpleMoveCommand(move_data, game_state)
        
        # 执行命令
        success = command.execute()
        
        assert success is True
        assert command.executed is True
        piece.move_to.assert_called_once_with(1, 1)
    
    def test_undo_simple_move(self):
        """测试撤销简单移动"""
        piece = Mock()
        piece.row = 1
        piece.col = 1
        
        captured = Mock()
        captured.color = "black"
        
        game_state = Mock()
        game_state.pieces = [piece]
        game_state.captured_pieces = {"red": [], "black": [captured]}
        
        move_data = MoveData(
            piece=piece,
            from_row=0,
            from_col=0,
            to_row=1,
            to_col=1,
            captured_piece=captured
        )
        
        command = SimpleMoveCommand(move_data, game_state)
        command._previous_position = (0, 0)
        command.executed = True
        
        # 撤销命令
        success = command.undo()
        
        assert success is True
        assert command.executed is False
        piece.move_to.assert_called_once_with(0, 0)


class TestCommandInvoker:
    """命令调用者测试"""
    
    def test_execute_command(self):
        """测试执行命令"""
        invoker = CommandInvoker()
        command = Mock()
        command.execute.return_value = True
        
        success = invoker.execute_command(command)
        
        assert success is True
        assert invoker.can_undo() is True
        assert invoker.can_redo() is False
        assert invoker.get_undo_stack_size() == 1
    
    def test_undo_command(self):
        """测试撤销命令"""
        invoker = CommandInvoker()
        command = Mock()
        command.execute.return_value = True
        command.undo.return_value = True
        
        invoker.execute_command(command)
        success = invoker.undo()
        
        assert success is True
        assert invoker.can_undo() is False
        assert invoker.can_redo() is True
    
    def test_redo_command(self):
        """测试重做命令"""
        invoker = CommandInvoker()
        command = Mock()
        command.execute.return_value = True
        command.undo.return_value = True
        command.redo.return_value = True
        
        invoker.execute_command(command)
        invoker.undo()
        success = invoker.redo()
        
        assert success is True
        assert invoker.can_undo() is True
        assert invoker.can_redo() is False
    
    def test_clear_history(self):
        """测试清空历史"""
        invoker = CommandInvoker()
        command = Mock()
        command.execute.return_value = True
        
        invoker.execute_command(command)
        invoker.clear_history()
        
        assert invoker.can_undo() is False
        assert invoker.can_redo() is False
        assert invoker.get_undo_stack_size() == 0
    
    def test_max_history_limit(self):
        """测试历史记录限制"""
        invoker = CommandInvoker(max_history=5)
        
        for i in range(10):
            command = Mock()
            command.execute.return_value = True
            invoker.execute_command(command)
        
        assert invoker.get_undo_stack_size() == 5
    
    def test_get_stats(self):
        """测试获取统计信息"""
        invoker = CommandInvoker()
        command = Mock()
        command.execute.return_value = True
        command.undo.return_value = True
        command.redo.return_value = True
        
        invoker.execute_command(command)
        invoker.undo()
        invoker.redo()
        
        stats = invoker.get_stats()
        
        assert stats['total_executed'] == 1
        assert stats['total_undone'] == 1
        assert stats['total_redone'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
