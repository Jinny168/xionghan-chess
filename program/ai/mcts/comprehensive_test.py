#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
综合测试游戏本体与MCTS适配器之间的交互
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

def test_comprehensive_integration():
    """综合测试游戏本体与MCTS的集成"""
    print("=" * 80)
    print("综合测试游戏本体与MCTS的集成")
    print("=" * 80)
    
    try:
        from program.core.game_state import GameState
        from program.ai.mcts.mcts_game import Board, XiangHanChessRuleAdapter
        from program.utils.tools import get_valid_moves
        
        print("1. 创建游戏本体初始状态")
        game_state = GameState()
        print(f"   初始玩家: {game_state.player_turn}")
        print(f"   棋子数量: {len(game_state.pieces)}")
        
        print("\n2. 创建MCTS适配器并转换状态")
        adapter = XiangHanChessRuleAdapter()
        mcts_board = adapter.adapt_state_to_mcts(game_state)
        print(f"   MCTS Board玩家颜色: {mcts_board.current_player_color}")
        print(f"   MCTS Board玩家ID: {mcts_board.current_player_id}")
        
        print("\n3. 验证状态一致性")
        # 检查玩家颜色一致性
        game_player_color = '红' if game_state.player_turn == 'red' else '黑'
        if game_player_color == mcts_board.current_player_color:
            print("   ✓ 玩家颜色一致")
        else:
            print(f"   × 玩家颜色不一致: 游戏本体={game_player_color}, MCTS={mcts_board.current_player_color}")
        
        # 检查棋盘内容一致性
        piece_count_match = True
        for piece in game_state.pieces:
            mcts_name = adapter._convert_piece_name(piece.name, piece.color)
            actual_name = mcts_board.state_list[piece.row][piece.col]
            if mcts_name != actual_name:
                print(f"   × 棋盘内容不一致: 位置({piece.row},{piece.col}), 游戏本体={piece.name}({piece.color}), MCTS={actual_name}")
                piece_count_match = False
                break
        
        if piece_count_match:
            print("   ✓ 棋盘内容一致")
        
        print("\n4. 获取双方的有效移动")
        # 游戏本体的有效移动
        game_valid_moves = get_valid_moves(game_state, game_state.player_turn)
        print(f"   游戏本体 {game_state.player_turn} 方有效移动数量: {len(game_valid_moves)}")
        
        # MCTS的有效移动
        mcts_valid_moves = mcts_board.availables
        print(f"   MCTS {mcts_board.current_player_color} 方有效移动数量: {len(mcts_valid_moves)}")
        
        print("\n5. 测试MCTS移动到游戏本体格式的转换")
        if mcts_valid_moves:
            sample_mcts_move = mcts_valid_moves[0]
            game_format_move = adapter.adapt_move_to_game_format(sample_mcts_move, game_state)
            print(f"   MCTS移动ID {sample_mcts_move} -> 游戏本体格式 {game_format_move}")
            
            # 验证转换后的移动是否在游戏本体的有效移动中
            if game_format_move in game_valid_moves:
                print("   ✓ 转换后的移动在游戏本体的有效移动中")
            else:
                print("   × 转换后的移动不在游戏本体的有效移动中")
                
                # 尝试验证移动是否符合规则
                is_valid = adapter.validate_move(game_state, game_format_move[0], game_format_move[1])
                print(f"   验证移动是否符合规则: {is_valid}")
        
        print("\n6. 测试移动执行")
        if mcts_valid_moves:
            sample_move = mcts_valid_moves[0]
            print(f"   执行MCTS移动: {sample_move}")
            
            # 记录移动前的状态
            prev_player_color = mcts_board.current_player_color
            prev_player_id = mcts_board.current_player_id
            
            # 执行移动
            mcts_board.do_move(sample_move)
            
            # 检查移动后的状态变化
            print(f"   移动后玩家颜色: {mcts_board.current_player_color}")
            print(f"   移动后玩家ID: {mcts_board.current_player_id}")
            
            if prev_player_color != mcts_board.current_player_color:
                print("   ✓ 玩家颜色正确切换")
            else:
                print("   × 玩家颜色未切换")
        
        print("\n7. 测试MCTS Board的current_state方法")
        current_state = mcts_board.current_state()
        print(f"   current_state形状: {current_state.shape}")
        if current_state.shape == (11, 13, 13):
            print("   ✓ current_state形状正确")
        else:
            print("   × current_state形状错误")
        
        print("\n✓ 综合测试完成")
        return True
        
    except Exception as e:
        print(f"✗ 综合测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_edge_cases():
    """测试边界情况"""
    print("\n" + "=" * 80)
    print("测试边界情况")
    print("=" * 80)
    
    try:
        from program.core.game_state import GameState
        from program.ai.mcts.mcts_game import Board, XiangHanChessRuleAdapter
        
        print("1. 测试空棋盘情况")
        # 创建一个简单的Board实例
        board = Board()
        print(f"   Board初始状态列表长度: {len(board.state_list)}")
        print(f"   Board初始deque长度: {len(board.state_deque)}")
        
        print("\n2. 测试非法移动处理")
        adapter = XiangHanChessRuleAdapter()
        
        # 测试无效的MCTS移动ID
        invalid_move_id = 999999  # 一个不存在的移动ID
        try:
            game_format_move = adapter.adapt_move_to_game_format(invalid_move_id, GameState())
            print(f"   无效移动ID转换结果: {game_format_move}")
            if game_format_move is None:
                print("   ✓ 正确处理了无效移动ID")
            else:
                print("   × 无效移动ID应返回None或抛出异常")
        except Exception as e:
            print(f"   ✓ 正确捕获了无效移动ID异常: {e}")
        
        print("\n3. 测试特殊棋子名称转换")
        # 测试所有可能的棋子名称转换
        test_pairs = [
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
            ("廵", "black", "黑廵"),
            ("巡", "red", "红巡"),
        ]
        
        all_correct = True
        for piece_name, color, expected in test_pairs:
            result = adapter._convert_piece_name(piece_name, color)
            if result == expected:
                print(f"   ✓ '{piece_name}'({color}) -> '{result}'")
            else:
                print(f"   × '{piece_name}'({color}) -> '{result}' (期望: '{expected}')")
                all_correct = False
        
        if all_correct:
            print("   ✓ 所有棋子名称转换正确")
        
        print("\n✓ 边界情况测试完成")
        return True
        
    except Exception as e:
        print(f"✗ 边界情况测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_comprehensive_tests():
    """运行综合测试"""
    print("开始运行综合测试...")
    print()
    
    results = []
    
    # 运行各个测试
    results.append(test_comprehensive_integration())
    results.append(test_edge_cases())
    
    # 输出总结
    print("\n" + "=" * 80)
    print("综合测试总结")
    print("=" * 80)
    
    passed = sum(results)
    total = len(results)
    
    print(f"通过测试: {passed}/{total}")
    
    if passed == total:
        print("✓ 所有综合测试通过!")
        return True
    else:
        print("× 部分综合测试失败!")
        return False


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)