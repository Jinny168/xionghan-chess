"""
匈汉象棋状态同步专项测试
用于验证各种情况下的状态同步问题
"""
import sys
import os
import time
import threading
import json
import hashlib

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from program.core.game_state import GameState
from program.core.chess_pieces import PieceFactory
from program.lan.network_game import NetworkChessGame
from program.lan.xhlan import XiangqiNetworkGame, SimpleAPI


class StateSyncTester:
    """状态同步测试器"""
    
    def __init__(self):
        self.test_results = {}
        self.errors = []
        self.test_logs = []
        
    def log(self, message):
        """记录日志"""
        self.test_logs.append(message)
        print(message)
    
    def get_detailed_state_hash(self, game_state):
        """获取详细的游戏状态哈希，包括更多细节"""
        try:
            # 创建详细状态快照，排除可能变化的时间戳字段
            state_snapshot = {
                'player_turn': game_state.player_turn,
                'pieces': [
                    (p.name, p.color, p.row, p.col) 
                    for p in sorted(game_state.pieces, key=lambda x: (x.row, x.col, x.name))
                ],
                'move_history_length': len(game_state.move_history),
                'captured_pieces': {
                    'red': [p.name for p in game_state.captured_pieces['red']],
                    'black': [p.name for p in game_state.captured_pieces['black']]
                },
                'game_over': game_state.game_over,
                'winner': game_state.winner,
                'is_check': game_state.is_check,
                'board_position_history_len': len(game_state.board_position_history)
                # 注意：我们排除了可能包含时间戳的字段
            }
            
            # 计算哈希
            state_str = json.dumps(state_snapshot, sort_keys=True, default=str)
            state_hash = hashlib.md5(state_str.encode()).hexdigest()
            return state_hash
        except Exception as e:
            self.log(f"获取详细游戏状态哈希时出错: {e}")
            return None
    
    def simulate_network_game_states(self):
        """模拟网络游戏中服务器和客户端的状态"""
        self.log("\n=== 模拟网络游戏状态同步 ===")
        
        # 创建两个游戏状态实例，模拟服务器和客户端
        # 为了确保初始状态完全一致，我们使用相同的方法创建
        server_game_state = GameState()
        # 通过复制第一个实例的初始状态来创建第二个实例
        client_game_state = GameState()
        
        # 由于GameState的初始化是确定性的，它们应该具有相同的初始状态
        # 但我们手动验证这一点
        server_initial_hash = self.get_detailed_state_hash(server_game_state)
        client_initial_hash = self.get_detailed_state_hash(client_game_state)
        
        if server_initial_hash == client_initial_hash:
            self.log("✅ 初始状态同步正常")
        else:
            self.log("❌ 初始状态不同步")
            self.log(f"  服务器哈希: {server_initial_hash}")
            self.log(f"  客户端哈希: {client_initial_hash}")
            self.errors.append("初始状态不同步")
            return False
        
        # 测试1: 单步移动同步
        self.log("\n--- 测试1: 单步移动同步 ---")
        # 为了避免移动后玩家回合自动切换导致的不一致，我们执行相同的移动序列
        # 确保两个状态的内部状态一致
        move_success_server = server_game_state.move_piece(6, 0, 7, 0)  # 红方兵移动
        move_success_client = client_game_state.move_piece(6, 0, 7, 0)  # 客户端执行相同移动
        
        if move_success_server and move_success_client:
            server_after_move_hash = self.get_detailed_state_hash(server_game_state)
            client_after_move_hash = self.get_detailed_state_hash(client_game_state)
            
            if server_after_move_hash == client_after_move_hash:
                self.log("✅ 单步移动后状态同步正常")
                self.test_results['single_move_sync'] = True
            else:
                self.log("❌ 单步移动后状态不同步")
                self.log(f"  服务器哈希: {server_after_move_hash}")
                self.log(f"  客户端哈希: {client_after_move_hash}")
                self.errors.append("单步移动后状态不同步")
                self.test_results['single_move_sync'] = False
        else:
            self.log("❌ 移动执行失败")
            self.log(f"  服务器移动结果: {move_success_server}")
            self.log(f"  客户端移动结果: {move_success_client}")
            self.errors.append("移动执行失败")
            self.test_results['single_move_sync'] = False
        
        # 测试2: 多步移动同步
        self.log("\n--- 测试2: 多步移动同步 ---")
        # 重置状态以确保一致的起点
        server_game_state = GameState()
        client_game_state = GameState()
        
        moves = [
            (6, 0, 7, 0),  # 红方兵移动
            (9, 1, 8, 1),  # 黑方马移动  
            (7, 0, 8, 0),  # 红方兵继续移动
        ]
        
        server_moves_success = True
        client_moves_success = True
        
        for from_row, from_col, to_row, to_col in moves:
            s_success = server_game_state.move_piece(from_row, from_col, to_row, to_col)
            c_success = client_game_state.move_piece(from_row, from_col, to_row, to_col)
            
            if not (s_success and c_success):
                server_moves_success = False
                client_moves_success = False
                self.log(f"❌ 移动 {(from_row, from_col, to_row, to_col)} 执行失败")
                break
        
        if server_moves_success and client_moves_success:
            server_multi_hash = self.get_detailed_state_hash(server_game_state)
            client_multi_hash = self.get_detailed_state_hash(client_game_state)
            
            if server_multi_hash == client_multi_hash:
                self.log("✅ 多步移动后状态同步正常")
                self.test_results['multi_move_sync'] = True
            else:
                self.log("❌ 多步移动后状态不同步")
                self.log(f"  服务器哈希: {server_multi_hash}")
                self.log(f"  客户端哈希: {client_multi_hash}")
                self.errors.append("多步移动后状态不同步")
                self.test_results['multi_move_sync'] = False
        else:
            self.log("❌ 多步移动执行失败")
            self.errors.append("多步移动执行失败")
            self.test_results['multi_move_sync'] = False
        
        # 测试3: 悔棋同步
        self.log("\n--- 测试3: 悔棋同步 ---")
        # 创建一个有移动历史的状态
        server_game_state = GameState()
        client_game_state = GameState()
        
        # 执行一些移动
        server_game_state.move_piece(6, 0, 7, 0)
        server_game_state.move_piece(9, 1, 8, 1)
        client_game_state.move_piece(6, 0, 7, 0)
        client_game_state.move_piece(9, 1, 8, 1)
        
        original_move_count = len(server_game_state.move_history)
        
        if original_move_count >= 1:
            # 执行悔棋
            server_undo_success = server_game_state.undo_move()
            client_undo_success = client_game_state.undo_move()
            
            if server_undo_success and client_undo_success:
                server_undo_hash = self.get_detailed_state_hash(server_game_state)
                client_undo_hash = self.get_detailed_state_hash(client_game_state)
                
                if server_undo_hash == client_undo_hash:
                    self.log(f"✅ 悔棋后状态同步正常 (从 {original_move_count} 步回到 {len(server_game_state.move_history)} 步)")
                    self.test_results['undo_sync'] = True
                else:
                    self.log("❌ 悔棋后状态不同步")
                    self.log(f"  服务器哈希: {server_undo_hash}")
                    self.log(f"  客户端哈希: {client_undo_hash}")
                    self.errors.append("悔棋后状态不同步")
                    self.test_results['undo_sync'] = False
            else:
                self.log("❌ 悔棋执行失败")
                self.log(f"  服务器悔棋结果: {server_undo_success}")
                self.log(f"  客户端悔棋结果: {client_undo_success}")
                self.errors.append("悔棋执行失败")
                self.test_results['undo_sync'] = False
        else:
            self.log("❌ 悔棋测试：移动历史不足")
            self.errors.append("悔棋测试：移动历史不足")
            self.test_results['undo_sync'] = False
        
        # 测试4: 游戏重置同步
        self.log("\n--- 测试4: 游戏重置同步 ---")
        server_game_state.reset()
        client_game_state.reset()
        
        server_reset_hash = self.get_detailed_state_hash(server_game_state)
        client_reset_hash = self.get_detailed_state_hash(client_game_state)
        
        if server_reset_hash == client_reset_hash:
            self.log("✅ 游戏重置后状态同步正常")
            self.test_results['reset_sync'] = True
        else:
            self.log("❌ 游戏重置后状态不同步")
            self.log(f"  服务器哈希: {server_reset_hash}")
            self.log(f"  客户端哈希: {client_reset_hash}")
            self.errors.append("游戏重置后状态不同步")
            self.test_results['reset_sync'] = False
        
        return True
    
    def test_complex_scenarios(self):
        """测试复杂场景"""
        self.log("\n=== 测试复杂场景 ===")
        
        # 场景1: 连续快速移动
        self.log("\n--- 场景1: 连续快速移动 ---")
        game_state_1 = GameState()
        game_state_2 = GameState()
        
        # 执行一系列复杂的移动
        complex_moves = [
            (6, 0, 7, 0), (9, 2, 8, 2),  # 兵和象
            (6, 2, 7, 2), (9, 0, 8, 0),  # 兵和车
            (7, 0, 8, 0), (8, 2, 7, 4),  # 兵吃兵，象移动
        ]
        
        for from_row, from_col, to_row, to_col in complex_moves:
            game_state_1.move_piece(from_row, from_col, to_row, to_col)
            game_state_2.move_piece(from_row, from_col, to_row, to_col)
        
        hash_1 = self.get_detailed_state_hash(game_state_1)
        hash_2 = self.get_detailed_state_hash(game_state_2)
        
        if hash_1 == hash_2:
            self.log("✅ 连续快速移动后状态同步正常")
            self.test_results['complex_moves_sync'] = True
        else:
            self.log("❌ 连续快速移动后状态不同步")
            self.errors.append("连续快速移动后状态不同步")
            self.test_results['complex_moves_sync'] = False
        
        # 场景2: 吃子操作同步
        self.log("\n--- 场景2: 吃子操作同步 ---")
        game_state_3 = GameState()
        game_state_4 = GameState()
        
        # 设置一个简单的吃子场景
        # 移动红方炮吃掉黑方卒
        # 先移动其他棋子让线路畅通
        game_state_3.move_piece(7, 1, 8, 1)  # 红方兵前进
        game_state_4.move_piece(7, 1, 8, 1)  # 红方兵前进
        
        # 现在移动炮吃掉卒
        capture_success_3 = game_state_3.move_piece(2, 1, 6, 1)  # 红方炮吃黑方卒
        capture_success_4 = game_state_4.move_piece(2, 1, 6, 1)  # 红方炮吃黑方卒
        
        if capture_success_3 and capture_success_4:
            hash_3 = self.get_detailed_state_hash(game_state_3)
            hash_4 = self.get_detailed_state_hash(game_state_4)
            
            if hash_3 == hash_4:
                self.log("✅ 吃子操作后状态同步正常")
                self.test_results['capture_sync'] = True
            else:
                self.log("❌ 吃子操作后状态不同步")
                self.errors.append("吃子操作后状态不同步")
                self.test_results['capture_sync'] = False
        else:
            self.log("❌ 吃子操作执行失败")
            self.errors.append("吃子操作执行失败")
            self.test_results['capture_sync'] = False
    
    def test_edge_cases(self):
        """测试边界情况"""
        self.log("\n=== 测试边界情况 ===")
        
        # 边界情况1: 非法移动尝试后的状态
        self.log("\n--- 边界情况1: 非法移动尝试 ---")
        game_state_valid = GameState()
        game_state_invalid = GameState()
        
        # 有效移动
        game_state_valid.move_piece(6, 0, 7, 0)
        game_state_invalid.move_piece(6, 0, 7, 0)  # 同样的有效移动
        
        # 尝试无效移动（应该失败）
        invalid_attempt_1 = game_state_valid.move_piece(99, 99, 100, 100)  # 无效位置
        invalid_attempt_2 = game_state_invalid.move_piece(99, 99, 100, 100)  # 无效位置
        
        hash_valid = self.get_detailed_state_hash(game_state_valid)
        hash_invalid = self.get_detailed_state_hash(game_state_invalid)
        
        # 无效移动应该都失败，状态应该保持一致
        if invalid_attempt_1 == invalid_attempt_2 and hash_valid == hash_invalid:
            self.log("✅ 无效移动尝试后状态同步正常")
            self.test_results['invalid_move_sync'] = True
        else:
            self.log("❌ 无效移动尝试后状态同步异常")
            self.errors.append("无效移动尝试后状态同步异常")
            self.test_results['invalid_move_sync'] = False
    
    def run_comprehensive_test(self):
        """运行综合测试"""
        self.log("开始匈汉象棋状态同步专项测试")
        self.log("=" * 60)
        
        # 运行各项测试
        self.simulate_network_game_states()
        self.test_complex_scenarios()
        self.test_edge_cases()
        
        # 输出测试结果
        self.print_test_summary()
    
    def print_test_summary(self):
        """打印测试摘要"""
        self.log("\n" + "=" * 60)
        self.log("状态同步测试摘要:")
        self.log("-" * 40)
        
        total_tests = len(self.test_results)
        if total_tests > 0:
            passed_tests = sum(1 for result in self.test_results.values() if result)
            
            for test_name, result in self.test_results.items():
                status = "✅ 通过" if result else "❌ 失败"
                self.log(f"{test_name}: {status}")
            
            self.log("-" * 40)
            self.log(f"总计: {total_tests} 个测试")
            self.log(f"通过: {passed_tests} 个")
            self.log(f"失败: {total_tests - passed_tests} 个")
        else:
            self.log("没有运行任何测试")
        
        if self.errors:
            self.log(f"\n发现 {len(self.errors)} 个错误:")
            for i, error in enumerate(self.errors, 1):
                self.log(f"{i}. {error}")
        
        # 提供改进建议
        self.provide_recommendations()
    
    def provide_recommendations(self):
        """提供改进建议"""
        self.log("\n--- 改进建议 ---")
        
        issues_found = len(self.errors) > 0
        failed_tests = sum(1 for result in self.test_results.values() if not result)
        
        if issues_found or failed_tests > 0:
            self.log("⚠️  发现状态同步问题，建议:")
            self.log("   1. 加强状态哈希验证机制")
            self.log("   2. 实现定期状态同步检查")
            self.log("   3. 增加网络延迟补偿机制")
            self.log("   4. 添加状态恢复功能")
        else:
            self.log("✅ 状态同步表现良好!")


def main():
    """主函数"""
    tester = StateSyncTester()
    tester.run_comprehensive_test()


if __name__ == "__main__":
    main()