#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
匈汉象棋将军/绝杀调试测试脚本
"""

def test_debug_output():
    """测试调试输出功能"""
    print("开始测试匈汉象棋将军/绝杀调试输出...")
    
    # 导入必要的模块
    from program.core.game_state import GameState
    from program.core.game_rules import GameRules
    from program.core.chess_pieces import King, Ju, Pao
    import time
    
    print("\n=== 测试1: 普通将军情况 ===")
    
    # 创建一个简单的将军局面
    game_state = GameState()
    
    # 清空棋盘并放置测试棋子
    game_state.pieces.clear()
    
    # 放置红方将（位于安全位置）
    red_king = King("red", 9, 6)  # 红方将位于九宫内
    game_state.pieces.append(red_king)
    
    # 放置黑方车，可以将军红将
    black_ju = Ju("black", 6, 6)  # 黑车位于红将正上方，可以将军
    game_state.pieces.append(black_ju)
    
    # 设置当前是黑方回合（即黑方刚走完，现在检查红方是否被将军）
    game_state.player_turn = "black"
    
    print(f"当前玩家: {game_state.player_turn}")
    print(f"棋子总数: {len(game_state.pieces)}")
    
    # 检查是否被将军
    is_red_in_check = GameRules.is_check(game_state.pieces, "red")
    print(f"红方是否被将军: {is_red_in_check}")
    
    # 设置游戏状态中的将军标志
    game_state.is_check = is_red_in_check
    game_state.check_animation_time = time.time()  # 设置动画时间
    
    print(f"\n--- 测试将军动画显示 ---")
    should_show_anim = game_state.should_show_check_animation()
    print(f"是否应该显示将军动画: {should_show_anim}")
    
    print(f"\n--- 测试被将军王位置 ---")
    king_pos = game_state.get_checked_king_position()
    print(f"被将军的王的位置: {king_pos}")
    
    print(f"\n=== 测试2: 绝杀情况 ===")
    
    # 创建一个绝杀局面：将被将军且无路可逃
    game_state2 = GameState()
    game_state2.pieces.clear()
    
    # 放置红方将
    red_king2 = King("red", 11, 6)  # 红将在最底行九宫中心
    game_state2.pieces.append(red_king2)
    
    # 放置黑方车将军
    black_ju2 = Ju("black", 8, 6)  # 黑车在红将上方将军
    game_state2.pieces.append(black_ju2)
    
    # 完全封锁红将的所有逃跑路线
    blocker1 = Ju('black', 10, 5)  # 左上
    blocker2 = Ju('black', 10, 7)  # 右上
    blocker4 = Ju('black', 11, 5) # 左
    blocker5 = Ju('black', 11, 7) # 右
    
    game_state2.pieces.extend([blocker1, blocker2, blocker4, blocker5])
    
    game_state2.player_turn = "black"  # 黑方刚走完，检查红方是否被将死
    
    print(f"当前玩家: {game_state2.player_turn}")
    print(f"棋子总数: {len(game_state2.pieces)}")
    
    is_check = GameRules.is_check(game_state2.pieces, "red")
    is_checkmate = GameRules.is_checkmate(game_state2.pieces, "red")
    
    print(f"红方被将军: {is_check}")
    print(f"红方被将死: {is_checkmate}")
    
    # 在绝杀情况下，我们希望先设置将军状态
    game_state2.is_check = is_check  # 设置为将军状态
    game_state2.check_animation_time = time.time()  # 设置动画时间
    
    print(f"\n--- 绝杀状态下的将军动画 ---")
    should_show_anim2 = game_state2.should_show_check_animation()
    print(f"绝杀状态下是否应该显示将军动画: {should_show_anim2}")
    
    print(f"\n--- 绝杀状态下的被将军王位置 ---")
    king_pos2 = game_state2.get_checked_king_position()
    print(f"绝杀状态下被将军王的位置: {king_pos2}")
    
    print(f"\n--- 绝杀状态下的is_checkmate()调用 ---")
    is_checkmate_state = game_state2.is_checkmate()
    print(f"游戏状态is_checkmate()结果: {is_checkmate_state}")
    
    print(f"\n--- 模拟游戏结束后的情况 ---")
    # 模拟游戏结束
    game_state2.game_over = True
    should_show_after_game_over = game_state2.should_show_check_animation()
    king_pos_after_game_over = game_state2.get_checked_king_position()
    print(f"游戏结束后是否应显示将军动画: {should_show_after_game_over}")
    print(f"游戏结束后是否返回将军位置: {king_pos_after_game_over is not None}")
    
    print("\n调试输出测试完成！")


def test_move_piece_debug():
    """测试move_piece函数的调试输出"""
    print("\n=== 测试3: move_piece函数调试输出 ===")
    
    from program.core.game_state import GameState
    from program.core.chess_pieces import King, Ju
    
    game_state = GameState()
    
    # 清空棋盘并放置测试棋子
    game_state.pieces.clear()
    
    # 放置红方将
    red_king = King("red", 9, 6)
    game_state.pieces.append(red_king)
    
    # 放置黑方车
    black_ju = Ju("black", 6, 6)
    game_state.pieces.append(black_ju)
    
    # 设置当前是红方回合
    game_state.player_turn = "red"
    
    print(f"移动前玩家: {game_state.player_turn}")
    
    # 尝试移动黑车将军
    success = game_state.move_piece(6, 6, 7, 6)  # 黑车从(6,6)移动到(7,6)
    print(f"移动是否成功: {success}")


def test_complete_game_flow():
    """测试完整的游戏流程"""
    print("\n=== 测试4: 完整游戏流程调试 ===")
    
    from program.core.game_state import GameState
    from program.core.chess_pieces import King, Ju
    
    # 创建一个将军局面
    game_state = GameState()
    game_state.pieces.clear()
    
    # 放置红将和黑车形成将军局面
    red_king = King("red", 9, 6)
    black_ju = Ju("black", 6, 6)
    game_state.pieces.extend([red_king, black_ju])
    
    game_state.player_turn = "black"
    
    print(f"当前玩家: {game_state.player_turn}")
    print(f"游戏结束: {game_state.game_over}, 胜者: {game_state.winner}")
    
    # 尝试移动黑车将军红将
    success = game_state.move_piece(6, 6, 8, 6)  # 黑车移动到红将上方形成将军
    print(f"将军移动是否成功: {success}")
    print(f"移动后玩家: {game_state.player_turn}")
    print(f"游戏结束: {game_state.game_over}, 胜者: {game_state.winner}")
    print(f"将军状态: {game_state.is_check}")
    print(f"被将军王位置: {game_state.get_checked_king_position()}")


if __name__ == "__main__":
    test_debug_output()
    test_move_piece_debug()
    test_complete_game_flow()