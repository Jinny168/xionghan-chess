"""
测试网络对战中的状态同步机制改进
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from program.lan.network_game import NetworkChessGame
from program.lan.xhlan import XiangqiNetworkGame, SimpleAPI
from unittest.mock import Mock, patch


def test_state_sync_mechanism():
    """测试状态同步机制"""
    print("开始测试状态同步机制...")
    
    # 创建一个模拟的SimpleAPI实例
    mock_api = Mock()
    SimpleAPI.instance = mock_api
    
    # 创建网络游戏实例（作为主机）
    game = NetworkChessGame(is_host=True)
    
    # 测试状态哈希生成
    print("\n1. 测试状态哈希生成...")
    try:
        game.send_state_sync_confirmation()
        print("✓ 状态哈希生成成功")
    except Exception as e:
        print(f"✗ 状态哈希生成失败: {e}")
    
    # 测试状态同步处理
    print("\n2. 测试状态同步处理...")
    try:
        mock_state_data = {
            'hash': 'test_hash',
            'snapshot': {
                'player_turn': 'red',
                'pieces': [('漢', 'red', 11, 6), ('汗', 'black', 1, 6)],
                'move_history_length': 0,
                'captured_pieces': {'red': [], 'black': []},
                'last_moved_player': 'red'
            }
        }
        game.handle_state_sync_confirmation(mock_state_data)
        print("✓ 状态同步处理成功")
    except Exception as e:
        print(f"✗ 状态同步处理失败: {e}")
    
    # 测试完整状态同步
    print("\n3. 测试完整状态同步...")
    try:
        mock_full_state_data = {
            'snapshot': {
                'player_turn': 'black',
                'pieces': [('漢', 'red', 11, 6), ('汗', 'black', 1, 6)],
                'move_history_length': 0,
                'captured_pieces': {'red': [], 'black': []},
                'last_moved_player': 'red'
            }
        }
        game.handle_full_state_sync(mock_full_state_data)
        print("✓ 完整状态同步成功")
    except Exception as e:
        print(f"✗ 完整状态同步失败: {e}")
    
    print("\n状态同步机制测试完成!")


def test_undo_sync_mechanism():
    """测试悔棋同步机制"""
    print("\n开始测试悔棋同步机制...")
    
    # 创建一个模拟的SimpleAPI实例
    mock_api = Mock()
    SimpleAPI.instance = mock_api
    
    # 创建网络游戏实例（作为主机）
    game = NetworkChessGame(is_host=True)
    
    # 测试悔棋功能
    print("\n1. 测试悔棋功能...")
    try:
        # 先进行几步移动
        # 注意：这里我们只是测试悔棋功能的代码路径，不实际移动棋子
        game.perform_undo()
        print("✓ 悔棋功能执行成功")
    except Exception as e:
        print(f"✗ 悔棋功能执行失败: {e}")
    
    print("\n悔棋同步机制测试完成!")


def test_restart_sync_mechanism():
    """测试重来同步机制"""
    print("\n开始测试重来同步机制...")
    
    # 创建一个模拟的SimpleAPI实例
    mock_api = Mock()
    SimpleAPI.instance = mock_api
    
    # 创建网络游戏实例（作为主机）
    game = NetworkChessGame(is_host=True)
    
    # 测试重来功能
    print("\n1. 测试重来功能...")
    try:
        game.perform_restart()
        print("✓ 重来功能执行成功")
    except Exception as e:
        print(f"✗ 重来功能执行失败: {e}")
    
    print("\n重来同步机制测试完成!")


if __name__ == "__main__":
    print("匈汉象棋网络对战状态同步机制测试")
    print("=" * 50)
    
    test_state_sync_mechanism()
    test_undo_sync_mechanism()
    test_restart_sync_mechanism()
    
    print("\n" + "=" * 50)
    print("所有测试完成!")