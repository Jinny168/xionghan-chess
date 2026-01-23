"""
游戏导入导出功能集成测试
"""
import unittest
import tempfile
import os
import sys

# 添加项目路径以导入模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from program.controllers.game_io_controller import GameIOController


class MockGameState:
    """模拟游戏状态用于测试"""
    
    def __init__(self, initial_fen="rheakaehr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RHEAKAEHR w - - 0 1"):
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
        self.initial_fen = initial_fen
    
    def export_position(self):
        """模拟导出位置"""
        return self.initial_fen
    
    def import_position(self, fen_string):
        """模拟导入位置"""
        if fen_string and len(fen_string) > 0:
            # 模拟成功导入
            self.fen_loaded = fen_string
            self.loaded_from_fen = True
            return True
        return False


class TestGameIOIntegration(unittest.TestCase):
    """测试游戏导入导出功能集成"""
    
    def test_export_then_import_cycle(self):
        """测试导出然后导入的完整周期"""
        # 创建控制器和游戏状态
        game_state = MockGameState()
        controller = GameIOController()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fen', delete=False) as temp_file:
            temp_filename = temp_file.name
            # 写入初始FEN数据
            initial_fen = game_state.export_position()
            temp_file.write(initial_fen)
        
        try:
            # 验证初始状态
            self.assertFalse(hasattr(game_state, 'loaded_from_fen'))
            
            # 创建新的游戏状态用于导入测试
            new_game_state = MockGameState()
            
            # 执行导入
            success = controller.import_game(new_game_state, temp_filename)
            
            # 验证导入成功
            self.assertTrue(success)
            self.assertTrue(hasattr(new_game_state, 'loaded_from_fen'))
            self.assertTrue(new_game_state.loaded_from_fen)
            self.assertEqual(new_game_state.fen_loaded, initial_fen)
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    def test_random_generated_game_export_import(self):
        """测试随机生成的棋局导出导入功能"""
        import random
        import string
        
        # 生成随机的FEN字符串（模拟随机棋局）
        chars = string.ascii_letters + string.digits + '/- '
        random_fen = ''.join(random.choice(chars) for _ in range(50))
        random_fen = random_fen.replace(' ', ' w - - 0 1')  # 添加标准结尾
        
        # 创建带有随机FEN的游戏状态
        game_state = MockGameState(initial_fen=random_fen)
        controller = GameIOController()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fen', delete=False) as temp_file:
            temp_filename = temp_file.name
            temp_file.write(random_fen)
        
        try:
            # 创建新游戏状态用于导入
            imported_game_state = MockGameState()
            
            # 执行导入
            success = controller.import_game(imported_game_state, temp_filename)
            
            # 验证导入成功
            self.assertTrue(success)
            self.assertEqual(imported_game_state.fen_loaded, random_fen)
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    def test_controller_with_bound_game_state(self):
        """测试绑定了游戏状态的控制器"""
        initial_fen = "rheakaehr/9/1c5c1/p1p1p1p1p/9/1n3n3/9/P1P1P1P1P/1C5C1/9/RHEAKAEHR b - - 5 3"
        game_state = MockGameState(initial_fen=initial_fen)
        controller = GameIOController(game_state)
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fen', delete=False) as temp_file:
            temp_filename = temp_file.name
            temp_file.write(initial_fen)
        
        try:
            # 使用控制器的绑定游戏状态进行导入
            success = controller.import_game(filename=temp_filename)
            
            # 验证导入成功到绑定的游戏状态
            self.assertTrue(success)
            self.assertEqual(game_state.fen_loaded, initial_fen)
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    def test_error_handling(self):
        """测试错误处理"""
        controller = GameIOController()
        
        # 测试无效文件路径
        result = controller.import_game(MockGameState(), "nonexistent_file.fen")
        self.assertFalse(result)
        
        # 测试空游戏状态
        result = controller.import_game(None, "nonexistent_file.fen")
        self.assertFalse(result)
    
    def test_multiple_exports_and_imports(self):
        """测试多次导出和导入"""
        controller = GameIOController()
        
        # 准备不同的游戏状态
        game_states = [
            MockGameState("rheakaehr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RHEAKAEHR w - - 0 1"),
            MockGameState("rheakaehr/9/1c5c1/p1p1p1p1p/9/1n3n3/9/P1P1P1P1P/1C5C1/9/RHEAKAEHR b - - 5 3"),
            MockGameState("rheakaehr/9/1c5c1/p1p1p1p1p/n7n/9/9/P1P1P1P1P/1C5C1/9/RHEAKAEHR w - - 10 6")
        ]
        
        temp_files = []
        
        try:
            # 为每个游戏状态创建临时文件
            for i, game_state in enumerate(game_states):
                with tempfile.NamedTemporaryFile(mode='w', suffix=f'_test{i}.fen', delete=False) as temp_file:
                    temp_file.write(game_state.export_position())
                    temp_files.append(temp_file.name)
            
            # 验证每个状态都可以被正确导入
            for i, (original_state, temp_file) in enumerate(zip(game_states, temp_files)):
                new_game_state = MockGameState()
                success = controller.import_game(new_game_state, temp_file)
                
                self.assertTrue(success, f"导入游戏状态 {i} 失败")
                self.assertEqual(new_game_state.fen_loaded, original_state.export_position())
        
        finally:
            # 清理所有临时文件
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)


if __name__ == '__main__':
    unittest.main()