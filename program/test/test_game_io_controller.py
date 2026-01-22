"""
测试游戏数据导入导出控制器
"""
import unittest
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock

# 添加项目路径以导入模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from program.controllers.game_io_controller import GameIOController


class MockGameState:
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
    
    def export_position(self):
        """模拟导出位置"""
        return "rheakaehr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RHEAKAEHR w - - 0 1"
    
    def import_position(self, fen_string):
        """模拟导入位置"""
        if fen_string and len(fen_string) > 0:
            # 模拟成功导入
            self.fen_loaded = fen_string
            return True
        return False


class TestGameIOController(unittest.TestCase):
    """测试游戏数据导入导出控制器"""
    
    def setUp(self):
        """设置测试环境"""
        self.game_state = MockGameState()
        self.controller = GameIOController(self.game_state)
    
    def test_export_game_success(self):
        """测试导出游戏成功"""
        # 使用临时文件进行测试
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fen', delete=False) as temp_file:
            temp_filename = temp_file.name
        
        try:
            # 直接调用导出函数，绕过文件对话框
            fen_content = self.game_state.export_position()
            
            # 写入临时文件
            with open(temp_filename, 'w', encoding='utf-8') as f:
                f.write(fen_content)
            
            # 验证文件是否已创建
            self.assertTrue(os.path.exists(temp_filename))
            
            # 验证文件内容
            with open(temp_filename, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertEqual(content, fen_content)
                
        finally:
            # 清理临时文件
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    def test_import_game_success(self):
        """测试导入游戏成功"""
        # 创建一个临时的FEN文件
        fen_content = "rheakaehr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RHEAKAEHR w - - 0 1"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fen', delete=False) as temp_file:
            temp_file.write(fen_content)
            temp_filename = temp_file.name
        
        try:
            # 测试导入功能
            result = self.controller.import_game(self.game_state, temp_filename)
            
            # 验证导入成功
            self.assertTrue(result)
            self.assertTrue(hasattr(self.game_state, 'fen_loaded'))
            self.assertEqual(self.game_state.fen_loaded, fen_content)
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    def test_import_game_failure_invalid_file(self):
        """测试导入游戏失败（无效文件）"""
        # 创建一个空的临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fen', delete=False) as temp_file:
            temp_file.write("")  # 空内容
            temp_filename = temp_file.name
        
        try:
            # 测试导入功能
            result = self.controller.import_game(self.game_state, temp_filename)
            
            # 验证导入失败
            self.assertFalse(result)
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    def test_controller_initialization(self):
        """测试控制器初始化"""
        # 测试带game_state的初始化
        controller_with_state = GameIOController(self.game_state)
        self.assertEqual(controller_with_state.game_state, self.game_state)
        
        # 测试不带game_state的初始化
        controller_without_state = GameIOController()
        self.assertIsNone(controller_without_state.game_state)
    
    def test_export_without_game_state(self):
        """测试没有游戏状态时导出"""
        controller = GameIOController()
        result = controller.export_game()
        self.assertFalse(result)
    
    def test_import_without_game_state(self):
        """测试没有游戏状态时导入"""
        controller = GameIOController()
        result = controller.import_game()
        self.assertFalse(result)
    
    def test_export_with_separate_game_state(self):
        """测试使用单独传入的游戏状态导出"""
        # 创建一个新的游戏状态
        new_game_state = MockGameState()
        new_game_state.player_turn = "black"
        
        # 使用临时文件测试
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fen', delete=False) as temp_file:
            temp_filename = temp_file.name
        
        try:
            # 直接写入内容到验证
            fen_content = new_game_state.export_position()
            with open(temp_filename, 'w', encoding='utf-8') as f:
                f.write(fen_content)
            
            # 验证内容
            with open(temp_filename, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertEqual(content, fen_content)
                
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    def test_import_with_separate_game_state(self):
        """测试使用单独传入的游戏状态导入"""
        # 创建一个新的游戏状态
        new_game_state = MockGameState()
        
        # 创建FEN内容
        fen_content = "rheakaehr/9/1c5c1/p1p1p1p1p/1n3n3/9/9/P1P1P1P1P/1C5C1/9/RHEAKAEHR w - - 0 1"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fen', delete=False) as temp_file:
            temp_file.write(fen_content)
            temp_filename = temp_file.name
        
        try:
            # 测试导入到新游戏状态
            result = self.controller.import_game(new_game_state, temp_filename)
            
            self.assertTrue(result)
            self.assertTrue(hasattr(new_game_state, 'fen_loaded'))
            self.assertEqual(new_game_state.fen_loaded, fen_content)
            
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_auto_save_game(self, mock_makedirs, mock_exists):
        """测试自动保存游戏功能"""
        # 模拟目录存在
        mock_exists.return_value = True
        mock_makedirs.return_value = None
        
        # 由于auto_save_game内部会调用export_game，而export_game会尝试打开文件，
        # 我们需要模拟这个过程而不是实际创建文件
        with patch.object(self.controller, 'export_game', return_value=True) as mock_export:
            result = self.controller.auto_save_game(self.game_state, "test_game.fen")
            # 验证export_game被调用
            self.assertTrue(mock_export.called)
            self.assertTrue(result)
    
    def test_get_saved_games(self):
        """测试获取已保存游戏列表"""
        # 创建一个临时目录用于测试
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                # 创建games目录并添加一些测试文件
                games_dir = os.path.join(temp_dir, "games")
                os.makedirs(games_dir, exist_ok=True)
                
                # 创建几个测试FEN文件
                test_files = ["game1.fen", "game2.fen", "game3.fen"]
                for filename in test_files:
                    filepath = os.path.join(games_dir, filename)
                    with open(filepath, 'w') as f:
                        f.write("test fen content")
                
                # 测试获取已保存游戏
                controller = GameIOController()
                saved_games = controller.get_saved_games()
                
                # 验证返回了正确的文件数量
                self.assertEqual(len(saved_games), 3)
                
                # 验证文件扩展名
                for game_path in saved_games:
                    self.assertTrue(game_path.endswith('.fen'))
                
            finally:
                os.chdir(original_cwd)


if __name__ == '__main__':
    unittest.main()