"""
测试复盘控制器功能
"""
import os
import sys
import unittest

# 添加项目路径以导入模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from program.controllers.replay_controller import ReplayController


class TestGameState:
    """模拟游戏状态用于测试"""
    
    def __init__(self):
        self.pieces = []
        self.player_turn = "red"
        self.game_over = False
        self.winner = None
        self.is_check = False
        self.move_history = []
        self.captured_pieces = {"red": [], "black": []}
        self.board_position_history = []
        self.repetition_count = {}
        self.moves_count = 0
        self.red_time = 0
        self.black_time = 0
        self.total_time = 0


class TestReplayControllerIntegration(unittest.TestCase):
    """测试复盘控制器集成"""
    
    def setUp(self):
        """设置测试环境"""
        self.game_state = TestGameState()
        self.controller = ReplayController(self.game_state)
    
    def test_controller_initialization(self):
        """测试控制器初始化"""
        self.assertIsNotNone(self.controller.game_state)
        # 根据经验教训，复盘控制器应该是独立实现的，不依赖base_controller
        # self.assertIsNotNone(self.controller.base_controller)
        self.assertFalse(self.controller.is_replay_mode)
        self.assertEqual(self.controller.current_step, 0)
        self.assertEqual(self.controller.max_steps, 0)
    
    def test_start_replay(self):
        """测试开始复盘"""
        self.controller.start_replay()
        
        self.assertTrue(self.controller.is_replay_mode)
        self.assertEqual(self.controller.current_step, 0)
    
    def test_navigation_functions(self):
        """测试导航功能"""
        self.controller.start_replay()
        
        # 测试跳转到开局
        self.controller.go_to_end()
        max_steps_before = self.controller.max_steps
        
        self.controller.go_to_beginning()
        self.assertEqual(self.controller.current_step, 0)
        
        # 测试上一步/下一步（如果存在步骤）
        if max_steps_before > 0:
            self.controller.go_to_end()
            initial_step = self.controller.current_step
            self.controller.go_to_previous()
            if initial_step > 0:
                self.assertLess(self.controller.current_step, initial_step)
    
    def test_progress_control(self):
        """测试进度控制"""
        self.controller.start_replay()
        
        # 测试设置进度
        self.controller.set_progress(50)
        progress = self.controller.get_progress_percentage()
        
        # 验证进度控制功能存在
        self.assertIsInstance(progress, int)
    
    def test_properties_access(self):
        """测试属性访问"""
        self.controller.start_replay()
        
        # 测试属性访问
        current_step = self.controller.current_step
        max_steps = self.controller.max_steps
        
        self.assertIsInstance(current_step, int)
        self.assertIsInstance(max_steps, int)


if __name__ == '__main__':
    unittest.main()