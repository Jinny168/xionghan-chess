"""
单元测试 - 状态机测试
"""
import pytest
from desktop.core.game_state_machine import GameStateMachine, GamePhase


class TestGamePhase:
    """游戏阶段枚举测试"""
    
    def test_game_phase_values(self):
        """测试游戏阶段枚举值"""
        assert GamePhase.INITIALIZING is not None
        assert GamePhase.MENU is not None
        assert GamePhase.GAME_RUNNING is not None
        assert GamePhase.GAME_OVER is not None
    
    def test_game_phase_uniqueness(self):
        """测试枚举值唯一性"""
        phases = list(GamePhase)
        assert len(phases) == len(set(phases))


class TestGameStateMachine:
    """游戏状态机测试"""
    
    def test_initial_state(self):
        """测试初始状态"""
        sm = GameStateMachine()
        assert sm.get_current_state() == GamePhase.INITIALIZING
        assert sm.get_previous_state() is None
    
    def test_transition_to_menu(self):
        """测试转换到菜单状态"""
        sm = GameStateMachine()
        
        success = sm.transition_to(GamePhase.MENU)
        
        assert success is True
        assert sm.get_current_state() == GamePhase.MENU
        assert sm.get_previous_state() == GamePhase.INITIALIZING
    
    def test_same_state_transition(self):
        """测试相同状态转换（应该失败）"""
        sm = GameStateMachine()
        sm.transition_to(GamePhase.MENU)
        
        success = sm.transition_to(GamePhase.MENU)
        
        assert success is False
    
    def test_invalid_transition(self):
        """测试无效转换"""
        sm = GameStateMachine()
        
        # 从INITIALIZING直接到GAME_OVER（没有定义这个转换）
        success = sm.transition_to(GamePhase.GAME_OVER)
        
        assert success is False
    
    def test_is_in_state(self):
        """测试状态检查"""
        sm = GameStateMachine()
        
        assert sm.is_in_state(GamePhase.INITIALIZING) is True
        assert sm.is_in_state(GamePhase.MENU) is False
        
        sm.transition_to(GamePhase.MENU)
        assert sm.is_in_state(GamePhase.MENU) is True
    
    def test_is_in_any_of(self):
        """测试多状态检查"""
        sm = GameStateMachine()
        sm.transition_to(GamePhase.MENU)
        
        states = [GamePhase.MENU, GamePhase.GAME_RUNNING]
        assert sm.is_in_any_of(states) is True
        
        states = [GamePhase.GAME_RUNNING, GamePhase.GAME_OVER]
        assert sm.is_in_any_of(states) is False
    
    def test_can_transition_to(self):
        """测试转换可能性检查"""
        sm = GameStateMachine()
        
        # INITIALIZING -> MENU 是允许的
        assert sm.can_transition_to(GamePhase.MENU) is True
        
        # INITIALIZING -> GAME_OVER 不允许
        assert sm.can_transition_to(GamePhase.GAME_OVER) is False
    
    def test_reset(self):
        """测试重置状态机"""
        sm = GameStateMachine()
        sm.transition_to(GamePhase.MENU)
        sm.transition_to(GamePhase.GAME_RUNNING)
        
        sm.reset()
        
        assert sm.get_current_state() == GamePhase.INITIALIZING
    
    def test_state_history(self):
        """测试状态历史"""
        sm = GameStateMachine()
        
        sm.transition_to(GamePhase.MENU)
        assert sm.get_previous_state() == GamePhase.INITIALIZING
        
        sm.transition_to(GamePhase.GAME_RUNNING)
        assert sm.get_previous_state() == GamePhase.MENU
    
    def test_repr(self):
        """测试字符串表示"""
        sm = GameStateMachine()
        repr_str = repr(sm)
        
        assert "GameStateMachine" in repr_str
        assert "INITIALIZING" in repr_str


class TestStateTransitions:
    """状态转换流程测试"""
    
    def test_full_game_flow(self):
        """测试完整游戏流程"""
        sm = GameStateMachine()
        
        # 初始化 -> 菜单
        assert sm.transition_to(GamePhase.MENU) is True
        
        # 菜单 -> 模式选择
        assert sm.transition_to(GamePhase.MODE_SELECTION) is True
        
        # 模式选择 -> 阵营选择
        assert sm.transition_to(GamePhase.CAMP_SELECTION) is True
        
        # 阵营选择 -> 游戏运行
        assert sm.transition_to(GamePhase.GAME_RUNNING) is True
        
        # 游戏运行 -> 暂停
        assert sm.transition_to(GamePhase.PAUSED) is True
        
        # 暂停 -> 游戏运行
        assert sm.transition_to(GamePhase.GAME_RUNNING) is True
        
        # 游戏运行 -> 游戏结束
        assert sm.transition_to(GamePhase.GAME_OVER) is True
        
        # 游戏结束 -> 菜单
        assert sm.transition_to(GamePhase.MENU) is True
    
    def test_ai_thinking_flow(self):
        """测试AI思考流程"""
        sm = GameStateMachine()
        sm.transition_to(GamePhase.MENU)
        sm.transition_to(GamePhase.GAME_RUNNING)
        
        # 游戏运行 -> AI思考
        assert sm.transition_to(GamePhase.THINKING) is True
        
        # AI思考 -> 游戏运行
        assert sm.transition_to(GamePhase.GAME_RUNNING) is True
    
    def test_promotion_flow(self):
        """测试升变流程"""
        sm = GameStateMachine()
        sm.transition_to(GamePhase.MENU)
        sm.transition_to(GamePhase.GAME_RUNNING)
        
        # 游戏运行 -> 升变
        assert sm.transition_to(GamePhase.PROMOTION) is True
        
        # 升变 -> 游戏运行
        assert sm.transition_to(GamePhase.GAME_RUNNING) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

