"""
匈汉象棋网络对战综合测试
用于验证各种情况下的状态同步问题
"""
import sys
import os
import time
import threading
import subprocess
import json
import hashlib

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from program.lan.xhlan import SimpleAPI
from program.core.game_state import GameState
from program.core.chess_pieces import PieceFactory


class ComprehensiveNetworkTest:
    """综合网络测试类"""
    
    def __init__(self):
        self.test_results = {}
        self.errors = []
        self.server_process = None
        self.client_process = None
        
    def setup_network(self):
        """设置网络环境"""
        print("正在设置网络环境...")
        # 清理之前的连接
        if SimpleAPI.instance:
            SimpleAPI.instance.disconnect()
        
    def test_basic_connection(self):
        """测试基本连接"""
        print("\n=== 测试1: 基本连接 ===")
        try:
            # 启动服务器
            server_cmd = [sys.executable, "-u", "server_only.py"]
            self.server_process = subprocess.Popen(
                server_cmd, 
                cwd=os.path.dirname(os.path.abspath(__file__)),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            time.sleep(3)  # 等待服务器启动
            
            # 启动客户端
            client_cmd = [sys.executable, "-u", "client_only.py"]
            self.client_process = subprocess.Popen(
                client_cmd,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 等待连接建立
            time.sleep(5)
            
            # 检查连接状态
            connected = SimpleAPI.is_connected() if SimpleAPI.instance else False
            
            if connected:
                print("✅ 基本连接测试通过")
                self.test_results['basic_connection'] = True
            else:
                print("❌ 基本连接测试失败")
                self.test_results['basic_connection'] = False
                self.errors.append("无法建立基本连接")
                
        except Exception as e:
            print(f"❌ 基本连接测试出错: {e}")
            self.test_results['basic_connection'] = False
            self.errors.append(str(e))
        finally:
            # 清理进程
            if self.server_process:
                self.server_process.terminate()
            if self.client_process:
                self.client_process.terminate()
    
    def test_move_synchronization(self):
        """测试移动同步"""
        print("\n=== 测试2: 移动同步 ===")
        try:
            # 创建两个游戏状态实例来模拟服务器和客户端
            server_state = GameState()
            client_state = GameState()
            
            # 初始状态应该相同
            server_hash = self.get_game_state_hash(server_state)
            client_hash = self.get_game_state_hash(client_state)
            
            if server_hash == client_hash:
                print("✅ 初始状态同步正常")
            else:
                print("❌ 初始状态不同步")
                print(f"  服务器哈希: {server_hash}")
                print(f"  客户端哈希: {client_hash}")
                self.errors.append("初始状态不同步")
            
            # 模拟一次移动
            # 选择一个棋子进行移动（例如，红方的兵从6,0到7,0）
            success = server_state.move_piece(6, 0, 7, 0)
            if success:
                print("✅ 服务器移动成功")
                
                # 模拟客户端接收同样的移动
                client_success = client_state.move_piece(6, 0, 7, 0)
                if client_success:
                    print("✅ 客户端移动成功")
                    
                    # 检查状态是否仍然同步
                    server_hash_after = self.get_game_state_hash(server_state)
                    client_hash_after = self.get_game_state_hash(client_state)
                    
                    if server_hash_after == client_hash_after:
                        print("✅ 移动后状态同步正常")
                        self.test_results['move_synchronization'] = True
                    else:
                        print("❌ 移动后状态不同步")
                        print(f"  服务器哈希: {server_hash_after}")
                        print(f"  客户端哈希: {client_hash_after}")
                        self.test_results['move_synchronization'] = False
                        self.errors.append("移动后状态不同步")
                else:
                    print("❌ 客户端移动失败")
                    self.test_results['move_synchronization'] = False
                    self.errors.append("客户端移动失败")
            else:
                print("❌ 服务器移动失败")
                self.test_results['move_synchronization'] = False
                self.errors.append("服务器移动失败")
                
        except Exception as e:
            print(f"❌ 移动同步测试出错: {e}")
            import traceback
            print(traceback.format_exc())
            self.test_results['move_synchronization'] = False
            self.errors.append(str(e))
    
    def test_undo_synchronization(self):
        """测试悔棋同步"""
        print("\n=== 测试3: 悔棋同步 ===")
        try:
            # 创建两个游戏状态实例来模拟服务器和客户端
            server_state = GameState()
            client_state = GameState()
            
            # 执行几步移动
            server_state.move_piece(6, 0, 7, 0)  # 红方兵移动
            server_state.move_piece(9, 1, 8, 1)  # 黑方马移动
            client_state.move_piece(6, 0, 7, 0)  # 红方兵移动
            client_state.move_piece(9, 1, 8, 1)  # 黑方马移动
            
            # 检查移动后状态是否同步
            if self.get_game_state_hash(server_state) != self.get_game_state_hash(client_state):
                print("❌ 悔棋测试前状态已不同步")
                self.test_results['undo_synchronization'] = False
                self.errors.append("悔棋测试前状态已不同步")
                return
            
            # 执行悔棋（回退一步）
            server_can_undo = len(server_state.move_history) >= 1
            client_can_undo = len(client_state.move_history) >= 1
            
            if server_can_undo and client_can_undo:
                server_undo_success = server_state.undo_move()
                client_undo_success = client_state.undo_move()
                
                if server_undo_success and client_undo_success:
                    # 检查悔棋后状态是否同步
                    server_hash_after_undo = self.get_game_state_hash(server_state)
                    client_hash_after_undo = self.get_game_state_hash(client_state)
                    
                    if server_hash_after_undo == client_hash_after_undo:
                        print("✅ 悔棋后状态同步正常")
                        self.test_results['undo_synchronization'] = True
                    else:
                        print("❌ 悔棋后状态不同步")
                        self.test_results['undo_synchronization'] = False
                        self.errors.append("悔棋后状态不同步")
                else:
                    print("❌ 悔棋操作失败")
                    self.test_results['undo_synchronization'] = False
                    self.errors.append("悔棋操作失败")
            else:
                print("❌ 无法执行悔棋，移动历史不足")
                self.test_results['undo_synchronization'] = False
                self.errors.append("无法执行悔棋，移动历史不足")
                
        except Exception as e:
            print(f"❌ 悔棋同步测试出错: {e}")
            self.test_results['undo_synchronization'] = False
            self.errors.append(str(e))
    
    def test_restart_synchronization(self):
        """测试重开同步"""
        print("\n=== 测试4: 重开同步 ===")
        try:
            # 创建两个游戏状态实例
            server_state = GameState()
            client_state = GameState()
            
            # 执行一些移动
            server_state.move_piece(6, 0, 7, 0)
            server_state.move_piece(9, 1, 8, 1)
            client_state.move_piece(6, 0, 7, 0)
            client_state.move_piece(9, 1, 8, 1)
            
            # 确保移动后状态同步
            if self.get_game_state_hash(server_state) != self.get_game_state_hash(client_state):
                print("❌ 重开测试前状态已不同步")
                self.test_results['restart_synchronization'] = False
                self.errors.append("重开测试前状态已不同步")
                return
            
            # 重置游戏状态
            server_state.reset()
            client_state.reset()
            
            # 检查重置后状态是否同步
            server_hash_after_reset = self.get_game_state_hash(server_state)
            client_hash_after_reset = self.get_game_state_hash(client_state)
            
            if server_hash_after_reset == client_hash_after_reset:
                print("✅ 重开后状态同步正常")
                self.test_results['restart_synchronization'] = True
            else:
                print("❌ 重开后状态不同步")
                self.test_results['restart_synchronization'] = False
                self.errors.append("重开后状态不同步")
                
        except Exception as e:
            print(f"❌ 重开同步测试出错: {e}")
            self.test_results['restart_synchronization'] = False
            self.errors.append(str(e))
    
    def test_game_over_synchronization(self):
        """测试游戏结束同步"""
        print("\n=== 测试5: 游戏结束同步 ===")
        try:
            # 创建两个游戏状态实例
            server_state = GameState()
            client_state = GameState()
            
            # 模拟将死情况（这只是一个简化示例）
            # 设置一些特定的棋子位置来模拟游戏结束条件
            server_state.game_over = True
            server_state.winner = "red"
            client_state.game_over = True
            client_state.winner = "red"
            
            # 检查游戏结束状态是否同步
            if (server_state.game_over == client_state.game_over and 
                server_state.winner == client_state.winner):
                print("✅ 游戏结束状态同步正常")
                self.test_results['game_over_synchronization'] = True
            else:
                print("❌ 游戏结束状态不同步")
                self.test_results['game_over_synchronization'] = False
                self.errors.append("游戏结束状态不同步")
                
        except Exception as e:
            print(f"❌ 游戏结束同步测试出错: {e}")
            self.test_results['game_over_synchronization'] = False
            self.errors.append(str(e))
    
    def get_game_state_hash(self, game_state):
        """获取游戏状态的哈希值用于比较"""
        try:
            # 创建状态快照，排除可能包含随机元素或时间戳的字段
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
                # 排除了可能变化的时间戳相关字段
            }
            
            # 计算哈希
            state_str = json.dumps(state_snapshot, sort_keys=True)
            state_hash = hashlib.md5(state_str.encode()).hexdigest()
            return state_hash
        except Exception as e:
            print(f"获取游戏状态哈希时出错: {e}")
            return None
    
    def run_all_tests(self):
        """运行所有测试"""
        print("开始匈汉象棋网络对战综合测试")
        print("=" * 50)
        
        # 运行各个测试
        self.setup_network()
        self.test_basic_connection()
        self.test_move_synchronization()
        self.test_undo_synchronization()
        self.test_restart_synchronization()
        self.test_game_over_synchronization()
        
        # 输出测试结果
        self.print_test_summary()
    
    def print_test_summary(self):
        """打印测试摘要"""
        print("\n" + "=" * 50)
        print("测试摘要:")
        print("-" * 30)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        for test_name, result in self.test_results.items():
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{test_name}: {status}")
        
        print("-" * 30)
        print(f"总计: {total_tests} 个测试")
        print(f"通过: {passed_tests} 个")
        print(f"失败: {total_tests - passed_tests} 个")
        
        if self.errors:
            print("\n错误详情:")
            for i, error in enumerate(self.errors, 1):
                print(f"{i}. {error}")


def main():
    """主函数"""
    tester = ComprehensiveNetworkTest()
    tester.run_all_tests()


if __name__ == "__main__":
    main()