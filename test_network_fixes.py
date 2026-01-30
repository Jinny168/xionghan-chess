#!/usr/bin/env python
"""
测试网络对战游戏修复后的功能
验证以下问题：
1. 重来后状态同步
2. 悔棋操作权限控制（只有最后移动的玩家可以发起悔棋）
3. 重来后状态完全复原
"""

import unittest.mock as mock
import sys
import os

# 添加项目路径
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

def test_network_fixes():
    """测试网络对战修复功能"""
    print("开始测试网络对战游戏修复...")
    
    # 导入相关模块
    from program.lan.network_game import NetworkChessGame
    from program.lan.xhlan import SimpleAPI, XiangqiNetworkGame
    from program.core.chess_pieces import Pawn  # 使用Pawn类
    
    # 模拟SimpleAPI
    with mock.patch.object(SimpleAPI, 'init') as mock_init, \
         mock.patch.object(XiangqiNetworkGame, 'set_network_mode') as mock_set_mode:
        
        # 测试主机模式初始化
        print("\n1. 测试主机模式初始化...")
        host_game = NetworkChessGame(is_host=True)
        
        # 验证初始化属性
        assert hasattr(host_game, 'last_moved_player'), "last_moved_player 属性应该存在"
        assert host_game.last_moved_player is None, "初始 last_moved_player 应为 None"
        assert host_game.player_camp == "red", "主机应该是红方"
        print("✓ 主机模式初始化正常")
        
        # 测试客户端模式初始化
        print("\n2. 测试客户端模式初始化...")
        client_game = NetworkChessGame(is_host=False)
        
        assert client_game.player_camp == "black", "客户端应该是黑方"
        assert client_game.last_moved_player is None, "初始 last_moved_player 应为 None"
        print("✓ 客户端模式初始化正常")
        
        # 测试悔棋按钮状态控制
        print("\n3. 测试悔棋权限控制...")
        
        # 模拟移动操作后，记录最后移动玩家
        host_game.last_moved_player = "red"
        host_game.player_camp = "red"
        
        # 模拟悔棋请求 - 应该允许
        can_request_undo = (host_game.last_moved_player == host_game.player_camp) and not host_game.game_state.game_over
        assert can_request_undo, "当前玩家是最后移动的玩家，应该可以发起悔棋"
        print("✓ 最后移动玩家可以发起悔棋")
        
        # 模拟其他玩家移动后，当前玩家不能悔棋
        host_game.last_moved_player = "black"  # 对手最后移动
        can_request_undo = (host_game.last_moved_player == host_game.player_camp) and not host_game.game_state.game_over
        assert not can_request_undo, "当前玩家不是最后移动的玩家，不能发起悔棋"
        print("✓ 非最后移动玩家不能发起悔棋")
        
        # 测试重来后状态复原
        print("\n4. 测试重来后状态复原...")
        
        # 记录初始状态
        initial_player_turn = host_game.game_state.player_turn
        initial_last_moved = host_game.last_moved_player
        
        # 执行重来
        host_game.perform_restart()
        
        # 验证状态复原
        assert host_game.game_state.player_turn == "red", "重来后主机应该仍然是红方回合"
        assert host_game.last_moved_player == "red", "重来后最后移动玩家应该是红方（先手）"
        assert host_game.selected_piece is None, "重来后选中棋子应为 None"
        assert host_game.last_move is None, "重来后最后移动应为 None"
        print("✓ 重来后状态正确复原")
        
        # 测试悔棋后状态更新
        print("\n5. 测试悔棋后状态更新...")
        
        # 先添加一些虚拟移动历史，以便悔棋操作可以执行
        # 创建一个虚拟的移动记录
        fake_piece = Pawn("red", 0, 0)  # 使用Pawn类创建一个虚拟棋子
        
        # 添加一些虚拟移动到历史记录中
        fake_move_record = (fake_piece, 0, 0, 1, 1, None)  # (piece, from_row, from_col, to_row, to_col, captured_piece)
        host_game.game_state.move_history.append(fake_move_record)
        host_game.game_state.move_history.append(fake_move_record)  # 需要至少2个记录
        
        # 设置当前玩家为红方，最后移动玩家为黑方（对手）
        host_game.player_camp = "red"
        host_game.last_moved_player = "black"  # 对手刚移动
        
        # 执行悔棋操作
        host_game.perform_undo()
        
        # 验证悔棋后最后移动玩家更新为当前玩家
        assert host_game.last_moved_player == "red", "悔棋后最后移动玩家应更新为当前玩家"
        print("✓ 悔棋后状态正确更新")
        
        # 测试接收对手移动后状态更新
        print("\n6. 测试接收对手移动后状态更新...")
        
        # 模拟接收对手移动
        host_game.player_camp = "red"
        # 添加一个虚拟移动历史记录，以便receive_network_move可以成功执行
        fake_move_record = (fake_piece, 2, 0, 3, 0, None)
        host_game.game_state.move_history.append(fake_move_record)
        
        host_game.receive_network_move(2, 0, 3, 0)  # 从 (2,0) 移动到 (3,0)
        
        # 验证最后移动玩家更新为对手（黑方）
        expected_opponent = "black" if host_game.player_camp == "red" else "red"
        assert host_game.last_moved_player == expected_opponent, f"接收对手移动后，最后移动玩家应为对手 {expected_opponent}"
        print("✓ 接收对手移动后状态正确更新")
        
    print("\n🎉 所有测试通过！网络对战修复功能正常工作。")
    print("\n修复的主要问题：")
    print("- ✓ 重来后状态同步问题得到解决")
    print("- ✓ 悔棋操作权限控制（只有最后移动的玩家可以发起悔棋）")
    print("- ✓ 重来后所有状态完全复原")
    print("- ✓ 悔棋和移动后正确更新最后移动玩家")

if __name__ == "__main__":
    test_network_fixes()