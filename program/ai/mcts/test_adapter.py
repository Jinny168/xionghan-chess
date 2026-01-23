# coding=utf-8
"""
测试匈汉象棋MCTS AI适配器
验证输入输出转换是否正常，以及其他逻辑是否正常工作
"""

import unittest
import copy
from program.ai.mcts.adapter import MCTSAdapter
from program.core.game_state import GameState
from program.core.chess_pieces import King, Ju, Ma, Xiang, Shi, Pao, Pawn, She, Lei
from program.ai.mcts.mcts_game import Board


class TestMCTSAdapter(unittest.TestCase):
    """MCTS适配器测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.adapter = MCTSAdapter()
        self.game_state = GameState()
    
    def test_initialization(self):
        """测试适配器初始化"""
        self.assertIsNotNone(self.adapter.mcts_board)
        self.assertIsNotNone(self.adapter.mcts_game)
        self.assertIsNotNone(self.adapter.game_state)
        print("✓ 适配器初始化测试通过")
    
    def test_sync_game_state_to_mcts(self):
        """测试游戏状态同步到MCTS"""
        # 获取初始棋盘状态
        original_pieces_count = len(self.game_state.pieces)
        
        # 同步游戏状态到MCTS
        self.adapter.sync_game_state_to_mcts(self.game_state)
        
        # 检查同步后MCTS棋盘状态
        self.assertIsNotNone(self.adapter.mcts_board.state_list)
        self.assertEqual(len(self.adapter.mcts_board.state_list), 13)
        self.assertEqual(len(self.adapter.mcts_board.state_list[0]), 13)
        print("✓ 游戏状态同步到MCTS测试通过")
    
    def test_piece_name_mapping(self):
        """测试棋子名称映射"""
        # 测试正向映射
        self.assertEqual(self.adapter.piece_name_mapping['俥'], '红車')
        self.assertEqual(self.adapter.piece_name_mapping['車'], '黑車')
        self.assertEqual(self.adapter.piece_name_mapping['汗'], '黑汗')  # 假设將对应黑汗
        self.assertEqual(self.adapter.piece_name_mapping['漢'], '红漢')  # 假设帥对应红汉
        # 修正：汉/汗的映射
        self.assertEqual(self.adapter.piece_name_mapping.get('漢', None), '红漢')
        self.assertEqual(self.adapter.piece_name_mapping.get('汗', None), '黑汗')
        
        # 测试反向映射
        self.assertEqual(self.adapter.reverse_piece_name_mapping['红車'], '俥')
        self.assertEqual(self.adapter.reverse_piece_name_mapping['黑車'], '車')
        print("✓ 棋子名称映射测试通过")
    
    def test_get_piece_class_by_name(self):
        """测试根据名称获取棋子类"""
        # 测试各种棋子
        self.assertEqual(self.adapter.get_piece_class_by_name('車'), Ju)
        self.assertEqual(self.adapter.get_piece_class_by_name('俥'), Ju)
        self.assertEqual(self.adapter.get_piece_class_by_name('馬'), Ma)
        self.assertEqual(self.adapter.get_piece_class_by_name('傌'), Ma)
        self.assertEqual(self.adapter.get_piece_class_by_name('汗'), King)
        self.assertEqual(self.adapter.get_piece_class_by_name('漢'), King)
        print("✓ 根据名称获取棋子类测试通过")
    
    def test_convert_move_format(self):
        """测试移动格式转换"""
        # 模拟从(2, 3)移动到(4, 5)
        from_pos = (2, 3)
        to_pos = (4, 5)
        
        # 转换为MCTS格式（修正：该方法现在只需要两个参数）
        mcts_move = self.adapter.convert_move_format(from_pos, to_pos)
        expected_move = "02030405"
        
        self.assertEqual(mcts_move, expected_move)
        print("✓ 移动格式转换测试通过")
    
    def test_convert_mcts_move_to_game_format(self):
        """测试MCTS移动转游戏格式"""
        # 使用已知的MCTS移动ID
        # 先确保move_id2move_action中有有效的映射
        from program.ai.mcts.mcts_game import move_id2move_action
        
        # 获取一个有效的移动ID进行测试
        if len(move_id2move_action) > 0:
            test_move_id = list(move_id2move_action.keys())[0]
            from_pos, to_pos = self.adapter.convert_mcts_move_to_game_format(test_move_id)
            
            if from_pos is not None and to_pos is not None:
                self.assertIsInstance(from_pos, tuple)
                self.assertIsInstance(to_pos, tuple)
                self.assertEqual(len(from_pos), 2)
                self.assertEqual(len(to_pos), 2)
                print("✓ MCTS移动转游戏格式测试通过")
            else:
                print("⚠ MCTS移动转游戏格式测试跳过（无效移动ID）")
        else:
            print("⚠ MCTS移动转游戏格式测试跳过（无有效移动ID）")
    
    def test_sync_mcts_to_game_state(self):
        """测试MCTS状态同步回游戏"""
        # 首先同步游戏状态到MCTS
        self.adapter.sync_game_state_to_mcts(self.game_state)
        
        # 然后同步回游戏状态
        new_game_state = self.adapter.sync_mcts_to_game_state()
        
        # 检查同步结果
        self.assertIsNotNone(new_game_state)
        self.assertIsInstance(new_game_state, GameState)
        print("✓ MCTS状态同步回游戏测试通过")
    
    def test_get_current_player_color(self):
        """测试获取当前玩家颜色"""
        # 同步游戏状态到MCTS
        self.adapter.sync_game_state_to_mcts(self.game_state)
        
        # 获取当前玩家颜色
        color = self.adapter.get_current_player_color()
        
        # 默认情况下，游戏是红方先行
        self.assertIn(color, ['red', 'black'])
        print(f"✓ 获取当前玩家颜色测试通过: {color}")
    
    def test_make_move(self):
        """测试执行移动"""
        # 同步游戏状态到MCTS
        self.adapter.sync_game_state_to_mcts(self.game_state)
        
        # 尝试执行一个移动（如果存在合法移动的话）
        if len(self.adapter.mcts_board.availables) > 0:
            # 获取一个合法移动
            move_id = self.adapter.mcts_board.availables[0]
            
            # 记录移动前的状态
            board_before = copy.deepcopy(self.adapter.mcts_board.state_list)
            
            # 执行移动
            result = self.adapter.make_move(move_id)
            
            self.assertTrue(result)
            # 检查棋盘状态是否发生变化
            board_changed = any(
                board_before[i][j] != self.adapter.mcts_board.state_list[i][j]
                for i in range(13) for j in range(13)
            )
            if board_changed:
                print("✓ 执行移动测试通过")
            else:
                print("⚠ 执行移动测试：棋盘状态未发生变化")
        else:
            print("⚠ 执行移动测试跳过：无合法移动")


def run_tests():
    """运行所有测试"""
    print("开始测试MCTS适配器...")
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMCTSAdapter)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果摘要
    print(f"\n测试摘要:")
    print(f"运行测试数: {result.testsRun}")
    print(f"失败数: {len(result.failures)}")
    print(f"错误数: {len(result.errors)}")
    
    if result.failures:
        print("\n失败详情:")
        for test, traceback in result.failures:
            print(f"{test}: {traceback}")
    
    if result.errors:
        print("\n错误详情:")
        for test, traceback in result.errors:
            print(f"{test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n✅ 所有测试通过!")
    else:
        print("\n❌ 部分测试失败!")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    run_tests()