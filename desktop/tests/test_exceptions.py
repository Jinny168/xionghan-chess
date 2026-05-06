"""
单元测试 - 异常体系测试
"""
import pytest
from desktop.exceptions.game_exceptions import (
    ChessGameError,
    InvalidMoveError,
    PositionOutOfBoundsError,
    AITimeoutError,
    ResourceLoadError,
)


class TestChessGameError:
    """基础异常测试"""
    
    def test_basic_exception(self):
        """测试基础异常"""
        error = ChessGameError("测试错误")
        assert str(error) == "测试错误"
        assert error.message == "测试错误"
    
    def test_exception_with_code(self):
        """测试带错误码的异常"""
        error = ChessGameError("测试错误", error_code="TEST_CODE")
        assert "[TEST_CODE]" in str(error)
        assert error.error_code == "TEST_CODE"
    
    def test_exception_inheritance(self):
        """测试异常继承关系"""
        error = InvalidMoveError((0, 0), (1, 1))
        assert isinstance(error, ChessGameError)
        assert isinstance(error, Exception)


class TestMoveExceptions:
    """移动相关异常测试"""
    
    def test_invalid_move_error(self):
        """测试非法移动异常"""
        error = InvalidMoveError(
            from_pos=(0, 0),
            to_pos=(1, 1),
            reason="路径被阻挡"
        )
        
        assert error.from_pos == (0, 0)
        assert error.to_pos == (1, 1)
        assert error.reason == "路径被阻挡"
        assert "从(0, 0)到(1, 1)" in str(error)
    
    def test_position_out_of_bounds(self):
        """测试位置越界异常"""
        error = PositionOutOfBoundsError(row=15, col=15, board_size=13)
        
        assert error.row == 15
        assert error.col == 15
        assert error.board_size == 13
        assert "超出棋盘范围" in str(error)


class TestAIExceptions:
    """AI相关异常测试"""
    
    def test_ai_timeout_error(self):
        """测试AI超时异常"""
        error = AITimeoutError(timeout_ms=10000)
        
        assert error.timeout_ms == 10000
        assert "10000ms" in str(error)
        assert error.error_code == "AI_TIMEOUT"


class TestResourceExceptions:
    """资源相关异常测试"""
    
    def test_resource_load_error(self):
        """测试资源加载异常"""
        error = ResourceLoadError(
            resource_type="图片",
            resource_path="test.png",
            reason="文件不存在"
        )
        
        assert error.resource_type == "图片"
        assert error.resource_path == "test.png"
        assert error.reason == "文件不存在"
        assert "图片" in str(error)
        assert "test.png" in str(error)
    
    def test_exception_catch_hierarchy(self):
        """测试异常捕获层次"""
        # 应该能够用基类捕获子类异常
        try:
            raise InvalidMoveError((0, 0), (1, 1))
        except ChessGameError as e:
            assert isinstance(e, InvalidMoveError)
        
        # 应该能够用Exception捕获
        try:
            raise AITimeoutError(5000)
        except Exception as e:
            assert isinstance(e, AITimeoutError)


class TestExceptionMessages:
    """异常消息格式测试"""
    
    def test_error_code_format(self):
        """测试错误码格式"""
        error = InvalidMoveError((0, 0), (1, 1))
        message = str(error)
        
        # 应该包含错误码
        assert "[INVALID_MOVE]" in message
    
    def test_custom_message(self):
        """测试自定义消息"""
        error = ChessGameError("自定义错误信息")
        assert str(error) == "自定义错误信息"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

