"""
匈汉象棋网络对战集成测试
用于验证真实网络环境中的状态同步问题
"""
import sys
import os
import time
import threading
import json
import hashlib
import queue

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from program.lan.network_game import NetworkChessGame
from program.lan.xhlan import XiangqiNetworkGame, SimpleAPI
from program.core.game_state import GameState


class NetworkIntegrationTester:
    """网络集成测试器"""
    
    def __init__(self):
        self.test_results = {}
        self.errors = []
        self.test_logs = []
        self.message_queue = queue.Queue()
        
    def log(self, message):
        """记录日志"""
        self.test_logs.append(message)
        print(f"[{time.strftime('%H:%M:%S')}] {message}")
    
    def setup_test_environment(self):
        """设置测试环境"""
        self.log("设置网络测试环境...")
        
        # 确保没有现有连接
        if SimpleAPI.instance:
            SimpleAPI.instance.disconnect()
        
        # 重置网络游戏实例
        XiangqiNetworkGame.game_instance = None
        
        time.sleep(1)  # 等待清理完成
    
    def test_real_network_scenario(self):
        """测试真实网络场景"""
        self.log("\n=== 测试真实网络场景 ===")
        
        # 创建服务器和客户端游戏实例
        try:
            # 服务器游戏实例
            self.log("创建服务器游戏实例...")
            server_game = NetworkChessGame(is_host=True)
            
            # 模拟客户端游戏实例（在实际环境中，这是在另一台机器上）
            self.log("创建客户端游戏实例...")
            client_game = NetworkChessGame(is_host=False)
            
            # 检查初始状态是否一致
            server_initial_hash = self.get_game_state_hash(server_game.game_state)
            client_initial_hash = self.get_game_state_hash(client_game.game_state)
            
            if server_initial_hash == client_initial_hash:
                self.log("✅ 初始状态同步正常")
                self.test_results['initial_sync'] = True
            else:
                self.log("❌ 初始状态不同步")
                self.log(f"  服务器哈希: {server_initial_hash}")
                self.log(f"  客户端哈希: {client_initial_hash}")
                self.errors.append("初始状态不同步")
                self.test_results['initial_sync'] = False
                return False
            
            # 重置游戏状态以确保一致性
            server_game.game_state = GameState()
            client_game.game_state = GameState()
            
            # 验证重置后的状态
            server_reset_hash = self.get_game_state_hash(server_game.game_state)
            client_reset_hash = self.get_game_state_hash(client_game.game_state)
            
            if server_reset_hash != client_reset_hash:
                self.log("❌ 重置后状态仍不同步")
                self.errors.append("重置后状态仍不同步")
                self.test_results['initial_sync'] = False
                return False
            
            # 模拟几轮移动
            self.log("\n--- 模拟游戏移动 ---")
            
            # 服务器方移动（红方）
            move_1_success = server_game.game_state.move_piece(6, 0, 7, 0)
            if move_1_success:
                self.log("✅ 服务器移动成功: 6,0 -> 7,0")
                
                # 模拟客户端接收移动
                client_move_1_success = client_game.game_state.move_piece(6, 0, 7, 0)
                if client_move_1_success:
                    self.log("✅ 客户端移动成功: 6,0 -> 7,0")
                else:
                    self.log("❌ 客户端移动失败")
                    self.errors.append("客户端移动失败")
            else:
                self.log("❌ 服务器移动失败")
                self.errors.append("服务器移动失败")
            
            # 客户端方移动（黑方）
            move_2_success = client_game.game_state.move_piece(9, 1, 8, 1)
            if move_2_success:
                self.log("✅ 客户端移动成功: 9,1 -> 8,1")
                
                # 模拟服务器接收移动
                server_move_2_success = server_game.game_state.move_piece(9, 1, 8, 1)
                if server_move_2_success:
                    self.log("✅ 服务器移动成功: 9,1 -> 8,1")
                else:
                    self.log("❌ 服务器移动失败")
                    self.errors.append("服务器移动失败")
            else:
                self.log("❌ 客户端移动失败")
                self.errors.append("客户端移动失败")
            
            # 检查移动后状态是否同步
            server_after_moves_hash = self.get_game_state_hash(server_game.game_state)
            client_after_moves_hash = self.get_game_state_hash(client_game.game_state)
            
            if server_after_moves_hash == client_after_moves_hash:
                self.log("✅ 移动后状态同步正常")
                self.test_results['moves_sync'] = True
            else:
                self.log("❌ 移动后状态不同步")
                self.log(f"  服务器哈希: {server_after_moves_hash}")
                self.log(f"  客户端哈希: {client_after_moves_hash}")
                self.errors.append("移动后状态不同步")
                self.test_results['moves_sync'] = False
            
            # 测试悔棋功能
            self.log("\n--- 测试悔棋功能 ---")
            
            # 悔棋前检查是否有足够的移动历史
            if len(server_game.game_state.move_history) >= 1 and len(client_game.game_state.move_history) >= 1:
                server_undo_success = server_game.game_state.undo_move()
                client_undo_success = client_game.game_state.undo_move()
                
                if server_undo_success and client_undo_success:
                    server_after_undo_hash = self.get_game_state_hash(server_game.game_state)
                    client_after_undo_hash = self.get_game_state_hash(client_game.game_state)
                    
                    if server_after_undo_hash == client_after_undo_hash:
                        self.log("✅ 悔棋后状态同步正常")
                        self.test_results['undo_sync'] = True
                    else:
                        self.log("❌ 悔棋后状态不同步")
                        self.log(f"  服务器哈希: {server_after_undo_hash}")
                        self.log(f"  客户端哈希: {client_after_undo_hash}")
                        self.errors.append("悔棋后状态不同步")
                        self.test_results['undo_sync'] = False
                else:
                    self.log(f"❌ 悔棋执行失败, 服务端成功: {server_undo_success}, 客户端成功: {client_undo_success}")
                    self.errors.append("悔棋执行失败")
                    self.test_results['undo_sync'] = False
            else:
                self.log("❌ 悔棋测试：移动历史不足")
                self.errors.append("悔棋测试：移动历史不足")
                self.test_results['undo_sync'] = False
            
            # 测试游戏重置
            self.log("\n--- 测试游戏重置 ---")
            server_game._reset_common_game_state()
            client_game._reset_common_game_state()
            
            server_reset_hash = self.get_game_state_hash(server_game.game_state)
            client_reset_hash = self.get_game_state_hash(client_game.game_state)
            
            if server_reset_hash == client_reset_hash:
                self.log("✅ 重置后状态同步正常")
                self.test_results['reset_sync'] = True
            else:
                self.log("❌ 重置后状态不同步")
                self.log(f"  服务器哈希: {server_reset_hash}")
                self.log(f"  客户端哈希: {client_reset_hash}")
                self.errors.append("重置后状态不同步")
                self.test_results['reset_sync'] = False
            
            return True
            
        except Exception as e:
            self.log(f"❌ 网络场景测试出错: {e}")
            import traceback
            self.log(f"详细错误: {traceback.format_exc()}")
            self.errors.append(f"网络场景测试出错: {e}")
            self.test_results['network_scenario'] = False
            return False
    
    def test_state_sync_methods(self):
        """测试状态同步方法"""
        self.log("\n=== 测试状态同步方法 ===")
        
        # 创建一个游戏实例
        game = NetworkChessGame(is_host=True)
        
        try:
            # 测试 send_state_sync_confirmation 方法
            self.log("测试 send_state_sync_confirmation 方法...")
            try:
                game.send_state_sync_confirmation()
                self.log("✅ send_state_sync_confirmation 方法执行成功")
                self.test_results['send_sync_method'] = True
            except Exception as e:
                self.log(f"❌ send_state_sync_confirmation 方法执行失败: {e}")
                self.errors.append(f"send_state_sync_confirmation 失败: {e}")
                self.test_results['send_sync_method'] = False
            
            # 测试 handle_state_sync_confirmation 方法
            self.log("测试 handle_state_sync_confirmation 方法...")
            try:
                # 创建一个模拟的状态数据
                mock_state_data = {
                    'hash': 'test_hash',
                    'snapshot': {
                        'player_turn': 'red',
                        'pieces': [],
                        'move_history_length': 0,
                        'captured_pieces': {'red': [], 'black': []},
                        'last_moved_player': 'red',
                        'game_over': False,
                        'winner': None,
                        'needs_promotion': False,
                        'promotion_pawn': None,
                        'available_promotion_pieces': []
                    }
                }
                game.handle_state_sync_confirmation(mock_state_data)
                self.log("✅ handle_state_sync_confirmation 方法执行成功")
                self.test_results['handle_sync_method'] = True
            except Exception as e:
                self.log(f"❌ handle_state_sync_confirmation 方法执行失败: {e}")
                self.errors.append(f"handle_state_sync_confirmation 失败: {e}")
                self.test_results['handle_sync_method'] = False
            
            # 测试 handle_full_state_sync 方法
            self.log("测试 handle_full_state_sync 方法...")
            try:
                mock_full_state_data = {
                    'snapshot': {
                        'player_turn': 'red',
                        'pieces': [('pawn', 'red', 6, 0)],
                        'move_history_length': 0,
                        'captured_pieces': {'red': [], 'black': []},
                        'last_moved_player': 'red',
                        'game_over': False,
                        'winner': None,
                        'needs_promotion': False,
                        'promotion_pawn': None,
                        'available_promotion_pieces': []
                    }
                }
                game.handle_full_state_sync(mock_full_state_data)
                self.log("✅ handle_full_state_sync 方法执行成功")
                self.test_results['full_sync_method'] = True
            except Exception as e:
                self.log(f"❌ handle_full_state_sync 方法执行失败: {e}")
                self.errors.append(f"handle_full_state_sync 失败: {e}")
                self.test_results['full_sync_method'] = False
                
        except Exception as e:
            self.log(f"❌ 状态同步方法测试出错: {e}")
            self.errors.append(f"状态同步方法测试出错: {e}")
            self.test_results['state_sync_methods'] = False
    
    def get_game_state_hash(self, game_state):
        """获取游戏状态的哈希值"""
        try:
            # 创建状态快照，排除可能随时间变化的字段
            state_snapshot = {
                'player_turn': game_state.player_turn,
                'pieces': [(p.name, p.color, p.row, p.col) for p in sorted(game_state.pieces, key=lambda x: (x.row, x.col, x.name))],
                'move_history_length': len(game_state.move_history),
                'captured_pieces': {
                    'red': [p.name for p in game_state.captured_pieces['red']],
                    'black': [p.name for p in game_state.captured_pieces['black']]
                },
                'game_over': game_state.game_over,
                'winner': game_state.winner,
                'is_check': game_state.is_check
                # 排除了时间相关的字段以确保一致性
            }
            
            # 计算哈希
            state_str = json.dumps(state_snapshot, sort_keys=True)
            state_hash = hashlib.md5(state_str.encode()).hexdigest()
            return state_hash
        except Exception as e:
            self.log(f"获取游戏状态哈希时出错: {e}")
            return None
    
    def run_integration_test(self):
        """运行集成测试"""
        self.log("开始匈汉象棋网络对战集成测试")
        self.log("=" * 60)
        
        # 设置测试环境
        self.setup_test_environment()
        
        # 运行测试
        self.test_real_network_scenario()
        self.test_state_sync_methods()
        
        # 输出测试结果
        self.print_test_summary()
    
    def print_test_summary(self):
        """打印测试摘要"""
        self.log("\n" + "=" * 60)
        self.log("网络集成测试摘要:")
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
        
        # 总体评估
        overall_pass = all(self.test_results.values()) if self.test_results else False
        if overall_pass:
            self.log("\n🎉 所有网络集成测试通过!")
        else:
            self.log("\n⚠️  存在网络集成问题需要修复")


def main():
    """主函数"""
    tester = NetworkIntegrationTester()
    tester.run_integration_test()


if __name__ == "__main__":
    main()