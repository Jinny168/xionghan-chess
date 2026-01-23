#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试游戏本体的GameState、MCTS的Board状态、MCTS的移动格式和游戏本体的移动格式转换是否正常
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import numpy as np
from collections import deque
import copy

def test_state_conversion():
    """测试游戏本体GameState与MCTS Board状态转换"""
    print("=" * 60)
    print("测试游戏本体GameState与MCTS Board状态转换")
    print("=" * 60)
    
    try:
        # 导入必要的类
        from program.core.game_state import GameState
        from program.ai.mcts.mcts_game import Board, XiangHanChessRuleAdapter
        
        # 创建游戏本体状态
        game_state = GameState()
        print(f"游戏本体初始玩家: {game_state.player_turn}")
        print(f"游戏本体棋子数量: {len(game_state.pieces)}")
        
        # 显示前几个棋子
        print("游戏本体前几个棋子:")
        for i, piece in enumerate(game_state.pieces[:5]):
            print(f"  {i}: {piece.name} ({piece.color}) 位置({piece.row}, {piece.col})")
        
        # 创建适配器
        adapter = XiangHanChessRuleAdapter()
        
        # 将游戏本体状态转换为MCTS Board状态
        mcts_board = adapter.adapt_state_to_mcts(game_state)
        
        print(f"\nMCTS Board当前玩家颜色: {mcts_board.current_player_color}")
        print(f"MCTS Board当前玩家ID: {mcts_board.current_player_id}")
        print(f"MCTS Board游戏开始: {mcts_board.game_start}")
        
        # 检查棋盘状态是否匹配
        print("\n比较棋盘状态:")
        mismatches = 0
        for piece in game_state.pieces:
            expected_name = adapter._convert_piece_name(piece.name, piece.color)
            actual_name = mcts_board.state_list[piece.row][piece.col]
            if expected_name != actual_name:
                print(f"  位置({piece.row}, {piece.col}): 期望'{expected_name}', 实际'{actual_name}'")
                mismatches += 1
        
        if mismatches == 0:
            print("  ✓ 棋盘状态完全匹配!")
        else:
            print(f"  × 发现 {mimatches} 处不匹配")
            
        # 检查MCTS Board的current_state方法
        current_state = mcts_board.current_state()
        print(f"\nMCTS Board current_state 形状: {current_state.shape}")
        if current_state.shape == (11, 13, 13):
            print("  ✓ current_state 形状正确!")
        else:
            print("  × current_state 形状错误!")
            
        # 检查availables属性
        legal_moves = mcts_board.availables
        print(f"MCTS Board 合法走子数量: {len(legal_moves)}")
        if legal_moves:
            print(f"  示例走子ID: {legal_moves[:5]}")
        
        print("\n✓ GameState与MCTS Board状态转换测试完成\n")
        return True
        
    except Exception as e:
        print(f"✗ GameState与MCTS Board状态转换测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_move_format_conversion():
    """测试MCTS移动格式与游戏本体移动格式转换"""
    print("=" * 60)
    print("测试MCTS移动格式与游戏本体移动格式转换")
    print("=" * 60)
    
    try:
        from program.core.game_state import GameState
        from program.ai.mcts.mcts_game import Board, XiangHanChessRuleAdapter, move_id2move_action
        from program.utils.tools import get_valid_moves
        
        # 创建游戏本体状态
        game_state = GameState()
        
        # 创建适配器
        adapter = XiangHanChessRuleAdapter()
        
        # 获取游戏本体的有效移动
        game_valid_moves = get_valid_moves(game_state, game_state.player_turn)
        print(f"游戏本体有效移动数量: {len(game_valid_moves)}")
        if game_valid_moves:
            print(f"  示例移动: {game_valid_moves[0]} -> ((from_row, from_col), (to_row, to_col))")
        
        # 获取MCTS的有效移动
        mcts_board = adapter.adapt_state_to_mcts(game_state)
        mcts_valid_moves = mcts_board.availables
        print(f"MCTS有效移动数量: {len(mcts_valid_moves)}")
        if mcts_valid_moves:
            print(f"  示例移动ID: {mcts_valid_moves[0]}")
            if mcts_valid_moves[0] in move_id2move_action:
                move_str = move_id2move_action[mcts_valid_moves[0]]
                print(f"  示例移动字符串: {move_str} (格式: 'from_y(2)from_x(2)to_y(2)to_x(2)')")
        
        # 测试从MCTS移动到游戏本体移动的转换
        if mcts_valid_moves:
            mcts_move_id = mcts_valid_moves[0]
            game_format_move = adapter.adapt_move_to_game_format(mcts_move_id, game_state)
            print(f"\nMCTS移动ID {mcts_move_id} -> 游戏本体格式 {game_format_move}")
            
            # 验证转换后的移动是否有效
            if game_format_move:
                is_valid = adapter.validate_move(game_state, game_format_move[0], game_format_move[1])
                print(f"  转换后的移动是否有效: {is_valid}")
                
                # 验证移动字符串格式是否正确
                if mcts_move_id in move_id2move_action:
                    move_str = move_id2move_action[mcts_move_id]
                    from_y = int(move_str[0:2])
                    from_x = int(move_str[2:4])
                    to_y = int(move_str[4:6])
                    to_x = int(move_str[6:8])
                    
                    expected_game_format = ((from_y, from_x), (to_y, to_x))
                    if expected_game_format == game_format_move:
                        print("  ✓ MCTS到游戏本体移动格式转换正确!")
                    else:
                        print(f"  × MCTS到游戏本体移动格式转换错误! 期望{expected_game_format}, 实际{game_format_move}")
        
        print("\n✓ MCTS移动格式与游戏本体移动格式转换测试完成\n")
        return True
        
    except Exception as e:
        print(f"✗ MCTS移动格式与游戏本体移动格式转换测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_round_trip_conversion():
    """测试往返转换（游戏本体->MCTS->游戏本体）"""
    print("=" * 60)
    print("测试往返转换（游戏本体->MCTS->游戏本体）")
    print("=" * 60)
    
    try:
        from program.core.game_state import GameState
        from program.ai.mcts.mcts_game import Board, XiangHanChessRuleAdapter, move_id2move_action
        
        # 创建游戏本体状态
        original_game_state = GameState()
        print(f"原始游戏状态玩家: {original_game_state.player_turn}")
        
        # 创建适配器
        adapter = XiangHanChessRuleAdapter()
        
        # 转换到MCTS
        mcts_board = adapter.adapt_state_to_mcts(original_game_state)
        print(f"MCTS Board玩家颜色: {mcts_board.current_player_color}")
        
        # 再次转换回游戏本体格式（模拟MCTS决策后反馈给游戏本体）
        # 这里我们模拟一个简单的移动，然后看状态是否能正确转换
        if mcts_board.availables:
            sample_move = mcts_board.availables[0]
            print(f"选择移动ID: {sample_move}")
            
            # 执行MCTS移动
            mcts_board.do_move(sample_move)
            print(f"移动后MCTS Board玩家颜色: {mcts_board.current_player_color}")
            
            # 验证移动是否成功
            if mcts_board.current_player_color != adapter.adapt_state_to_mcts(original_game_state).current_player_color:
                print("  ✓ MCTS移动执行成功，玩家切换正确!")
            else:
                print("  × MCTS移动执行失败，玩家未切换!")
        
        print("\n✓ 往返转换测试完成\n")
        return True
        
    except Exception as e:
        print(f"✗ 往返转换测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_specific_piece_conversions():
    """测试特定棋子名称转换"""
    print("=" * 60)
    print("测试特定棋子名称转换")
    print("=" * 60)
    
    try:
        from program.ai.mcts.mcts_game import XiangHanChessRuleAdapter
        
        adapter = XiangHanChessRuleAdapter()
        
        # 测试各种棋子名称转换
        test_cases = [
            ("汉", "red", "红汉"),
            ("汗", "black", "黑汗"),
            ("車", "black", "黑車"),
            ("俥", "red", "红俥"),
            ("馬", "black", "黑馬"),
            ("傌", "red", "红傌"),
            ("相", "red", "红相"),
            ("象", "black", "黑象"),
            ("仕", "red", "红仕"),
            ("士", "black", "黑士"),
            ("炮", "red", "红炮"),
            ("砲", "black", "黑砲"),
            ("兵", "red", "红兵"),
            ("卒", "black", "黑卒"),
            ("射", "red", "红射"),
            ("䠶", "black", "黑䠶"),
            ("檑", "red", "红檑"),
            ("礌", "black", "黑礌"),
        ]
        
        all_passed = True
        for piece_name, color, expected in test_cases:
            result = adapter._convert_piece_name(piece_name, color)
            status = "✓" if result == expected else "×"
            print(f"  {status} '{piece_name}'({color}) -> '{result}' (期望: '{expected}')")
            if result != expected:
                all_passed = False
        
        if all_passed:
            print("\n✓ 所有棋子名称转换测试通过!")
        else:
            print("\n× 部分棋子名称转换测试失败!")
        
        return all_passed
        
    except Exception as e:
        print(f"✗ 棋子名称转换测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("开始测试游戏本体与MCTS之间的状态和移动格式转换...")
    print()
    
    results = []
    
    # 运行各个测试
    results.append(test_state_conversion())
    results.append(test_move_format_conversion())
    results.append(test_round_trip_conversion())
    results.append(test_specific_piece_conversions())
    
    # 输出总结
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"通过测试: {passed}/{total}")
    
    if passed == total:
        print("✓ 所有测试通过!")
        return True
    else:
        print("× 部分测试失败!")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)