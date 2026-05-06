"""
集成测试 - 测试重构后的核心组件协同工作
"""
import pytest
from program.core import (
    BoardManager,
    MoveValidator,
    HistoryManager,
    CommandInvoker,
    SimpleMoveCommand,
    MoveData,
    GameComponentFactory,
    create_game_components,
)
from program.core.chess_pieces import create_initial_pieces, Pawn


class TestBoardManager:
    """棋盘管理器测试"""
    
    def test_create_board_manager(self):
        """测试创建棋盘管理器"""
        pieces = create_initial_pieces()
        manager = BoardManager(pieces)
        
        assert manager.get_pieces_count() > 0
        assert not manager.is_empty()
    
    def test_get_piece_at(self):
        """测试获取指定位置的棋子"""
        pieces = create_initial_pieces()
        manager = BoardManager(pieces)
        
        # 红方车应该在(0, 0)
        piece = manager.get_piece_at(0, 0)
        assert piece is not None
    
    def test_move_piece(self):
        """测试移动棋子"""
        pieces = create_initial_pieces()
        manager = BoardManager(pieces)
        
        pawn = manager.get_piece_at(8, 0)  # 红兵
        if pawn:
            original_row = pawn.row
            manager.move_piece(pawn, 7, 0)
            assert pawn.row == 7
    
    def test_remove_and_add_piece(self):
        """测试移除和添加棋子"""
        pieces = create_initial_pieces()
        manager = BoardManager(pieces)
        
        initial_count = manager.get_pieces_count()
        piece = manager.get_piece_at(0, 0)
        
        if piece:
            manager.remove_piece(piece)
            assert manager.get_pieces_count() == initial_count - 1
            
            manager.add_piece(piece)
            assert manager.get_pieces_count() == initial_count
    
    def test_capture_piece(self):
        """测试吃子操作"""
        pieces = create_initial_pieces()
        manager = BoardManager(pieces)
        captured = {"red": [], "black": []}
        
        piece = manager.get_piece_at(0, 0)
        if piece:
            piece_type = manager.capture_piece(piece, captured)
            
            assert piece not in manager.pieces
            assert piece in captured[piece.color]
            assert isinstance(piece_type, str)


class TestMoveValidator:
    """移动验证器测试"""
    
    def test_create_validator(self):
        """测试创建移动验证器"""
        pieces = create_initial_pieces()
        validator = MoveValidator(pieces, "red")
        
        assert validator.player_turn == "red"
    
    def test_is_own_piece(self):
        """测试检查己方棋子"""
        pieces = create_initial_pieces()
        validator = MoveValidator(pieces, "red")
        
        red_piece = [p for p in pieces if p.color == "red"][0]
        black_piece = [p for p in pieces if p.color == "black"][0]
        
        assert validator.is_own_piece(red_piece) is True
        assert validator.is_own_piece(black_piece) is False
    
    def test_would_cause_game_over(self):
        """测试检查是否会导致游戏结束"""
        pieces = create_initial_pieces()
        validator = MoveValidator(pieces, "red")
        
        # 黑将的位置
        from program.core.chess_pieces import King
        king_pos = None
        for piece in pieces:
            if isinstance(piece, King) and piece.color == "black":
                king_pos = (piece.row, piece.col)
                break
        
        if king_pos:
            # 尝试移动到将的位置应该会触发游戏结束
            result = validator.would_cause_game_over(validator.pieces[0], king_pos[0], king_pos[1])
            assert result is True


class TestHistoryManager:
    """历史记录管理器测试"""
    
    def test_create_history_manager(self):
        """测试创建历史记录管理器"""
        manager = HistoryManager()
        
        assert manager.get_move_count() == 0
        assert manager.can_undo() is False
    
    def test_record_move(self):
        """测试记录走子"""
        manager = HistoryManager()
        piece = Pawn("red", 8, 0)
        
        manager.record_move(piece, 8, 0, 7, 0)
        
        assert manager.get_move_count() == 1
        assert manager.can_undo() is True
    
    def test_pop_last_move(self):
        """测试弹出最后一步"""
        manager = HistoryManager()
        piece = Pawn("red", 8, 0)
        
        manager.record_move(piece, 8, 0, 7, 0)
        last_move = manager.pop_last_move()
        
        assert last_move is not None
        assert manager.get_move_count() == 0
    
    def test_max_history_limit(self):
        """测试历史记录限制"""
        manager = HistoryManager(max_history=5)
        piece = Pawn("red", 8, 0)
        
        for i in range(10):
            manager.record_move(piece, 8-i, 0, 7-i, 0)
        
        assert manager.get_move_count() == 5
    
    def test_board_position_tracking(self):
        """测试局面记录"""
        manager = HistoryManager()
        pieces = create_initial_pieces()
        
        manager.record_board_position(pieces)
        manager.record_board_position(pieces)
        manager.record_board_position(pieces)
        
        assert manager.is_repeated_position(3) is True
    
    def test_undo_board_position(self):
        """测试撤销局面记录"""
        manager = HistoryManager()
        pieces = create_initial_pieces()
        
        manager.record_board_position(pieces)
        manager.undo_board_position()
        
        assert len(manager.board_position_history) == 0
    
    def test_get_history_summary(self):
        """测试获取历史摘要"""
        manager = HistoryManager()
        piece = Pawn("red", 8, 0)
        
        manager.record_move(piece, 8, 0, 7, 0)
        summary = manager.get_history_summary()
        
        assert summary['total_moves'] == 1


class TestGameComponentFactory:
    """游戏组件工厂测试"""
    
    def test_create_default_factory(self):
        """测试创建默认工厂"""
        factory = GameComponentFactory.create_default_factory()
        
        assert factory is not None
    
    def test_create_custom_factory(self):
        """测试创建自定义配置工厂"""
        config = {'max_history': 50}
        factory = GameComponentFactory.create_custom_factory(config)
        
        assert factory.config['max_history'] == 50
    
    def test_create_board_manager(self):
        """测试工厂创建棋盘管理器"""
        factory = GameComponentFactory()
        manager = factory.create_board_manager()
        
        assert isinstance(manager, BoardManager)
        assert manager.get_pieces_count() > 0
    
    def test_create_history_manager(self):
        """测试工厂创建历史记录管理器"""
        factory = GameComponentFactory()
        manager = factory.create_history_manager()
        
        assert isinstance(manager, HistoryManager)
    
    def test_create_command_invoker(self):
        """测试工厂创建命令调用者"""
        factory = GameComponentFactory()
        invoker = factory.create_command_invoker()
        
        assert isinstance(invoker, CommandInvoker)
    
    def test_create_state_machine(self):
        """测试工厂创建状态机"""
        factory = GameComponentFactory()
        sm = factory.create_state_machine()
        
        assert sm is not None
    
    def test_create_complete_components(self):
        """测试创建完整组件集合"""
        factory = GameComponentFactory()
        components = factory.create_complete_game_components()
        
        assert 'board_manager' in components
        assert 'history_manager' in components
        assert 'command_invoker' in components
        assert 'state_machine' in components
        assert 'move_validator' in components
        
        assert isinstance(components['board_manager'], BoardManager)
        assert isinstance(components['history_manager'], HistoryManager)
        assert isinstance(components['command_invoker'], CommandInvoker)
    
    def test_convenience_function(self):
        """测试便捷函数"""
        components = create_game_components()
        
        assert isinstance(components, dict)
        assert len(components) > 0


class TestIntegration:
    """集成测试 - 组件协同工作"""
    
    def test_full_move_workflow(self):
        """测试完整的走子流程"""
        # 创建组件
        factory = GameComponentFactory()
        components = factory.create_complete_game_components()
        
        board = components['board_manager']
        history = components['history_manager']
        invoker = components['command_invoker']
        
        # 获取一个棋子
        pawn = board.get_piece_at(8, 0)
        if pawn:
            # 创建移动命令
            move_data = MoveData(
                piece=pawn,
                from_row=8,
                from_col=0,
                to_row=7,
                to_col=0
            )
            command = SimpleMoveCommand(move_data, type('GameState', (), {
                'pieces': board.pieces,
                'captured_pieces': {"red": [], "black": []}
            })())
            
            # 执行命令
            success = invoker.execute_command(command)
            assert success is True
            
            # 验证棋子已移动
            assert pawn.row == 7
            
            # 记录历史
            history.record_move(pawn, 8, 0, 7, 0)
            assert history.get_move_count() == 1
            
            # 撤销
            invoker.undo()
            assert pawn.row == 8
    
    def test_component_independence(self):
        """测试组件独立性"""
        # 创建两个独立的组件集合
        components1 = create_game_components()
        components2 = create_game_components()
        
        # 修改第一个的棋盘不应该影响第二个
        board1 = components1['board_manager']
        board2 = components2['board_manager']
        
        initial_count = board2.get_pieces_count()
        if board1.pieces:
            board1.remove_piece(board1.pieces[0])
        
        assert board2.get_pieces_count() == initial_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
