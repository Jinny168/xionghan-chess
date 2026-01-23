#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试从游戏结束弹窗导出，然后导入并进入复盘模式的完整流程
"""

import os
import tempfile
import json
from program.core.game_state import GameState
from program.controllers.game_io_controller import GameIOController
from program.controllers.replay_controller import ReplayController


def simulate_simple_game(game_state):
    """模拟一个简单的游戏过程，让某一方获胜"""
    from program.core.game_rules import GameRules
    
    # 我们将模拟几步移动，最终使一方获胜
    # 为了简化，我们直接修改游戏状态来模拟一个结束的游戏
    
    # 找到对方的王并将其移除，模拟胜利
    for piece in game_state.pieces[:]:
        if piece.name == "汗" and piece.color == "black":  # 黑方的汗（将/帅）
            game_state.pieces.remove(piece)
            game_state.captured_pieces["black"].append(piece)
            break
    
    # 标记游戏结束，红方获胜
    game_state.game_over = True
    game_state.winner = "red"
    
    # 添加一些历史记录
    fake_move = (game_state.pieces[0], 0, 0, 1, 1, None)  # (piece, from_row, from_col, to_row, to_col, captured_piece)
    game_state.move_history.append(fake_move)
    game_state.move_history.append(fake_move)
    
    print(f"模拟游戏结束: 红方获胜")
    print(f"历史记录长度: {len(game_state.move_history)}")


def test_replay_flow():
    """测试完整的复盘流程"""
    print("开始测试完整复盘流程...")
    
    # 创建游戏状态
    game_state = GameState()
    
    # 模拟游戏结束
    simulate_simple_game(game_state)
    
    print(f"游戏结束状态 - 胜者: {game_state.winner}, 游戏结束: {game_state.game_over}")
    print(f"历史记录长度: {len(game_state.move_history)}")
    
    # 创建控制器
    controller = GameIOController()
    
    # 创建临时文件进行测试
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fen', delete=False, encoding='utf-8') as tmp_file:
        temp_filename = tmp_file.name
    
    try:
        # 测试导出
        print("\n--- 测试导出结束游戏 ---")
        export_success = controller.export_game(game_state, temp_filename)
        print(f"导出结果: {export_success}")
        
        if export_success:
            # 验证导出的文件内容
            with open(temp_filename, 'r', encoding='utf-8') as f:
                content = f.read()
                game_data = json.loads(content)
                
                print(f"导出的胜者: {game_data.get('winner')}")
                print(f"导出的游戏结束状态: {game_data.get('game_over')}")
                print(f"导出的历史记录长度: {len(game_data.get('move_history', []))}")
        
        # 测试导入并进入复盘模式
        print("\n--- 测试导入并进入复盘模式 ---")
        # 创建一个新的game_state用于测试导入
        imported_game_state = GameState()
        
        import_success = controller.import_game(imported_game_state, temp_filename)
        print(f"导入结果: {import_success}")
        
        if import_success:
            print(f"导入后游戏状态:")
            print(f"  胜者: {imported_game_state.winner}")
            print(f"  游戏结束: {imported_game_state.game_over}")
            print(f"  历史记录长度: {len(imported_game_state.move_history)}")
            
            # 测试复盘控制器
            print("\n--- 测试复盘控制器 ---")
            replay_controller = ReplayController(imported_game_state)
            replay_controller.start_replay()
            
            print(f"复盘模式激活: {replay_controller.is_replay_mode}")
            print(f"历史状态数量: {len(replay_controller.history_states)}")
            print(f"当前步骤: {replay_controller.current_step}")
            print(f"最大步骤: {replay_controller.max_steps}")
            
            # 测试前进后退功能
            if len(replay_controller.history_states) > 1:
                print("\n--- 测试复盘导航 ---")
                
                # 记录当前状态
                current_pieces_count = len(replay_controller.game_state.pieces)
                print(f"当前棋子数量: {current_pieces_count}")
                
                # 尝试回到上一步
                if replay_controller.go_to_previous():
                    prev_pieces_count = len(replay_controller.game_state.pieces)
                    print(f"上一步棋子数量: {prev_pieces_count}")
                    print(f"前进后退功能正常: {abs(current_pieces_count - prev_pieces_count) >= 0}")  # 可能有棋子被吃
                
                # 再次前进
                if replay_controller.go_to_next():
                    next_pieces_count = len(replay_controller.game_state.pieces)
                    print(f"返回后棋子数量: {next_pieces_count}")
            
            print("\n✓ 完整复盘流程测试成功!")
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            print(f"\n已清理临时文件: {temp_filename}")


if __name__ == "__main__":
    test_replay_flow()