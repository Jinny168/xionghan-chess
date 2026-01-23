"""
测试匈汉象棋对局复盘功能
"""
import unittest
import pygame
from unittest.mock import Mock, MagicMock
import sys
import os

# 添加项目路径以导入模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from program.ui.replay_screen import ReplayScreen


class TestReplayController:
    """模拟复盘控制器用于测试"""
    
    def __init__(self):
        self.current_step = 0
        self.max_steps = 10
        self.progress_percentage = 0
    
    def go_to_beginning(self):
        self.current_step = 0
        self.progress_percentage = 0
    
    def go_to_previous(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.progress_percentage = (self.current_step / self.max_steps) * 100
    
    def go_to_next(self):
        if self.current_step < self.max_steps:
            self.current_step += 1
            self.progress_percentage = (self.current_step / self.max_steps) * 100
    
    def go_to_end(self):
        self.current_step = self.max_steps
        self.progress_percentage = 100
    
    def set_progress(self, percentage):
        self.progress_percentage = percentage
        self.current_step = int((percentage / 100) * self.max_steps)
    
    def get_progress_percentage(self):
        return self.progress_percentage
    
    def restore_original_state(self):
        pass


class TestGameState:
    """模拟游戏状态用于测试"""
    
    def __init__(self):
        self.pieces = []  # 模拟棋子列表


class TestReplayScreen(unittest.TestCase):
    """测试复盘界面功能"""
    
    @classmethod
    def setUpClass(cls):
        """初始化pygame"""
        pygame.init()
    
    @classmethod
    def tearDownClass(cls):
        """清理pygame"""
        pygame.quit()
    
    def setUp(self):
        """设置测试环境"""
        self.game_state = TestGameState()
        self.replay_controller = TestReplayController()
        self.screen = pygame.display.set_mode((1200, 900))
        self.replay_screen = ReplayScreen(self.game_state, self.replay_controller)
    
    def test_initialization(self):
        """测试复盘界面初始化"""
        self.assertIsNotNone(self.replay_screen.game_state)
        self.assertIsNotNone(self.replay_screen.controller)
        self.assertTrue(self.replay_screen.running)
        
        # 验证按钮是否正确创建
        self.assertIsNotNone(self.replay_screen.beginning_button)
        self.assertIsNotNone(self.replay_screen.previous_button)
        self.assertIsNotNone(self.replay_screen.next_button)
        self.assertIsNotNone(self.replay_screen.end_button)
        self.assertIsNotNone(self.replay_screen.return_button)  # 新增的返回按钮
        
        # 验证进度条参数是否正确初始化
        self.assertFalse(self.replay_screen.dragging_progress)
    
    def test_button_creation(self):
        """测试控制按钮创建"""
        # 验证按钮文本
        self.assertEqual(self.replay_screen.beginning_button.text, "开局")
        self.assertEqual(self.replay_screen.previous_button.text, "上一步")
        self.assertEqual(self.replay_screen.next_button.text, "下一步")
        self.assertEqual(self.replay_screen.end_button.text, "终局")
        self.assertEqual(self.replay_screen.return_button.text, "返回")  # 新增的返回按钮
        
        # 验证按钮位置（基本验证是否设置了坐标）
        self.assertGreaterEqual(self.replay_screen.beginning_button.rect.x, 0)
        self.assertGreaterEqual(self.replay_screen.beginning_button.rect.y, 0)
        self.assertGreater(self.replay_screen.beginning_button.rect.width, 0)
        self.assertGreater(self.replay_screen.beginning_button.rect.height, 0)
    
    def test_progress_bar_parameters(self):
        """测试进度条参数初始化"""
        self.assertGreaterEqual(self.replay_screen.progress_bar_x, 0)
        self.assertGreaterEqual(self.replay_screen.progress_bar_y, 0)
        self.assertGreater(self.replay_screen.progress_bar_width, 0)
        self.assertGreater(self.replay_screen.progress_bar_height, 0)
    
    def test_handle_beginning_button_click(self):
        """测试开局按钮点击事件"""
        # 设置初始状态
        self.replay_controller.current_step = 5
        self.replay_controller.progress_percentage = 50
        
        # 模拟鼠标点击开局按钮位置
        mock_event = Mock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.button = 1  # 左键
        
        # 获取开局按钮的位置信息
        button_x = self.replay_screen.beginning_button.rect.x + 10  # 按钮中心偏移
        button_y = self.replay_screen.beginning_button.rect.y + 10
        mouse_pos = (button_x, button_y)
        
        # 创建事件列表
        events = [mock_event]
        pygame.mouse.get_pos = Mock(return_value=mouse_pos)
        
        # 处理事件
        self.replay_screen.handle_events(events)
        
        # 验证是否跳转到开头
        self.assertEqual(self.replay_controller.current_step, 0)
        self.assertEqual(self.replay_controller.progress_percentage, 0)
    
    def test_handle_previous_button_click(self):
        """测试上一步按钮点击事件"""
        # 设置初始状态
        self.replay_controller.current_step = 5
        self.replay_controller.progress_percentage = 50
        
        # 模拟鼠标点击上一步按钮位置
        mock_event = Mock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.button = 1  # 左键
        
        # 获取上一步按钮的位置信息
        button_x = self.replay_screen.previous_button.rect.x + 10
        button_y = self.replay_screen.previous_button.rect.y + 10
        mouse_pos = (button_x, button_y)
        
        # 创建事件列表
        events = [mock_event]
        pygame.mouse.get_pos = Mock(return_value=mouse_pos)
        
        # 处理事件
        self.replay_screen.handle_events(events)
        
        # 验证是否执行了上一步操作
        self.assertEqual(self.replay_controller.current_step, 4)
        self.assertLess(self.replay_controller.progress_percentage, 50)
    
    def test_handle_next_button_click(self):
        """测试下一步按钮点击事件"""
        # 设置初始状态
        self.replay_controller.current_step = 5
        self.replay_controller.progress_percentage = 50
        
        # 模拟鼠标点击下一步按钮位置
        mock_event = Mock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.button = 1  # 左键
        
        # 获取下一步按钮的位置信息
        button_x = self.replay_screen.next_button.rect.x + 10
        button_y = self.replay_screen.next_button.rect.y + 10
        mouse_pos = (button_x, button_y)
        
        # 创建事件列表
        events = [mock_event]
        pygame.mouse.get_pos = Mock(return_value=mouse_pos)
        
        # 处理事件
        self.replay_screen.handle_events(events)
        
        # 验证是否执行了下一步操作
        self.assertEqual(self.replay_controller.current_step, 6)
        self.assertGreater(self.replay_controller.progress_percentage, 50)
    
    def test_handle_end_button_click(self):
        """测试终局按钮点击事件"""
        # 设置初始状态
        self.replay_controller.current_step = 5
        self.replay_controller.progress_percentage = 50
        
        # 模拟鼠标点击终局按钮位置
        mock_event = Mock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.button = 1  # 左键
        
        # 获取终局按钮的位置信息
        button_x = self.replay_screen.end_button.rect.x + 10  # 按钮中心偏移
        button_y = self.replay_screen.end_button.rect.y + 10
        mouse_pos = (button_x, button_y)
        
        # 创建事件列表
        events = [mock_event]
        pygame.mouse.get_pos = Mock(return_value=mouse_pos)
        
        # 处理事件
        self.replay_screen.handle_events(events)
        
        # 验证是否跳转到结尾
        self.assertEqual(self.replay_controller.current_step, self.replay_controller.max_steps)
        self.assertEqual(self.replay_controller.progress_percentage, 100)
    
    def test_handle_return_button_click(self):
        """测试返回按钮点击事件"""
        # 模拟鼠标点击返回按钮位置
        mock_event = Mock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.button = 1  # 左键
        
        # 获取返回按钮的位置信息
        button_x = self.replay_screen.return_button.rect.x + 10
        button_y = self.replay_screen.return_button.rect.y + 10
        mouse_pos = (button_x, button_y)
        
        # 创建事件列表
        events = [mock_event]
        pygame.mouse.get_pos = Mock(return_value=mouse_pos)
        
        # 处理事件
        self.replay_screen.handle_events(events)
        
        # 验证是否退出复盘模式
        self.assertFalse(self.replay_screen.running)
    
    def test_progress_bar_drag(self):
        """测试进度条拖拽功能"""
        # 设置拖拽状态
        self.replay_screen.dragging_progress = True
        
        # 模拟鼠标拖拽事件
        mock_event = Mock()
        mock_event.type = pygame.MOUSEMOTION
        
        # 计算拖拽到一半位置
        half_progress_x = self.replay_screen.progress_bar_x + self.replay_screen.progress_bar_width // 2
        mouse_y = self.replay_screen.progress_bar_y + 5  # 进度条中心
        mouse_pos = (half_progress_x, mouse_y)
        
        # 创建事件列表
        events = [mock_event]
        pygame.mouse.get_pos = Mock(return_value=mouse_pos)
        
        # 处理事件
        self.replay_screen.handle_events(events)
        
        # 验证进度是否更新到大约50%
        expected_progress = 50  # 由于整数计算，可能略有偏差
        self.assertAlmostEqual(self.replay_controller.progress_percentage, expected_progress, delta=5)
    
    def test_progress_bar_click(self):
        """测试进度条点击跳转功能"""
        # 模拟点击进度条中间位置
        mock_event = Mock()
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.button = 1  # 左键
        
        # 计算进度条中间位置
        middle_x = self.replay_screen.progress_bar_x + self.replay_screen.progress_bar_width // 2
        mouse_y = self.replay_screen.progress_bar_y + 5
        mouse_pos = (middle_x, mouse_y)
        
        # 创建事件列表
        events = [mock_event]
        pygame.mouse.get_pos = Mock(return_value=mouse_pos)
        
        # 处理事件前记录初始值
        initial_progress = self.replay_controller.progress_percentage
        
        # 处理事件
        self.replay_screen.handle_events(events)
        
        # 验证进度是否更新到大约50%
        expected_progress = 50
        self.assertNotEqual(initial_progress, self.replay_controller.progress_percentage)
        self.assertAlmostEqual(self.replay_controller.progress_percentage, expected_progress, delta=5)
        # 验证拖拽状态是否被设置
        self.assertTrue(self.replay_screen.dragging_progress)
    
    def test_quit_event_handling(self):
        """测试退出事件处理"""
        # 模拟退出事件
        mock_event = Mock()
        mock_event.type = pygame.QUIT
        
        events = [mock_event]
        
        # 处理事件
        result = self.replay_screen.handle_events(events)
        
        # 验证是否正确处理退出事件
        self.assertFalse(result)
        self.assertFalse(self.replay_screen.running)
    
    def test_draw_method_calls(self):
        """测试绘制方法调用"""
        # 由于直接测试绘制比较困难，我们验证方法是否会正常执行而不抛出异常
        try:
            self.replay_screen.draw(self.screen)
            success = True
        except Exception as e:
            success = False
            print(f"绘制方法失败: {e}")
        
        self.assertTrue(success)
    
    def test_exit_replay(self):
        """测试退出复盘功能"""
        self.replay_screen.exit_replay()
        
        # 验证运行状态是否被设置为False
        self.assertFalse(self.replay_screen.running)
        
        # 验证是否调用了恢复原始状态的方法
        # 这里只验证不会抛出异常，具体行为由mock的restore_original_state处理


if __name__ == '__main__':
    unittest.main()