#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试匈汉象棋将军/绝杀逻辑修复
"""

def test_check_and_checkmate_logic():
    """测试将军和绝杀逻辑修复"""
    print("开始测试匈汉象棋将军/绝杀逻辑修复...")
    
    # 导入必要的模块
    from program.core.game_state import GameState
    from program.core.game_rules import GameRules
    from program.core.chess_pieces import King, Ju, Pao
    import time
    
    print("1. 测试将军位置逻辑修复...")
    
    # 测试场景1：创建一个简单的将军局面
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
    game_state.player_turn = "black"  # 在实际游戏中，player_turn在移动后会切换
    
    # 检查是否被将军
    is_red_in_check = GameRules.is_check(game_state.pieces, "red")
    print(f"   红方是否被将军: {is_red_in_check}")
    
    # 设置游戏状态中的将军标志
    game_state.is_check = is_red_in_check
    game_state.check_animation_time = time.time()  # 设置动画时间
    
    # 检查被将军的王的位置
    king_pos = game_state.get_checked_king_position()
    print(f"   被将军的王的位置: {king_pos}")
    
    if king_pos:
        row, col = king_pos
        piece_at_pos = game_state.get_piece_at(row, col)
        print(f"   位置({row}, {col})处的棋子: {piece_at_pos.name if piece_at_pos else 'None'}, 颜色: {piece_at_pos.color if piece_at_pos else 'N/A'}")
        
        if piece_at_pos and isinstance(piece_at_pos, King) and piece_at_pos.color == "red":
            print("   ✓ 正确返回了被将军的红方王的位置")
        else:
            print("   ✗ 错误：没有正确返回被将军的王的位置")
    else:
        print("   ✗ 没有返回被将军的王的位置")
    
    # 测试将军动画显示逻辑
    should_show_anim = game_state.should_show_check_animation()
    print(f"   应该显示将军动画: {should_show_anim}")
    
    print("\n2. 测试绝杀逻辑修复...")
    
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
    
    is_check = GameRules.is_check(game_state2.pieces, "red")
    is_checkmate = GameRules.is_checkmate(game_state2.pieces, "red")
    
    print(f"   红方被将军: {is_check}")
    print(f"   红方被将死: {is_checkmate}")
    
    # 在绝杀情况下，我们希望先设置将军状态，然后游戏结束
    game_state2.is_check = is_check  # 设置为将军状态
    game_state2.check_animation_time = time.time()  # 设置动画时间
    
    king_pos2 = game_state2.get_checked_king_position()
    print(f"   绝杀状态下被将军王的位置: {king_pos2}")
    
    # 检查绝杀时的将军动画显示（在游戏结束前）
    should_show_anim2 = game_state2.should_show_check_animation()
    print(f"   绝杀状态下（游戏结束前）应该显示将军动画: {should_show_anim2}")
    
    # 模拟游戏结束
    game_state2.game_over = True
    should_show_after_game_over = game_state2.should_show_check_animation()
    king_pos_after_game_over = game_state2.get_checked_king_position()
    print(f"   游戏结束后是否应显示将军动画: {should_show_after_game_over}")
    print(f"   游戏结束后是否返回将军位置: {king_pos_after_game_over is not None}")
    
    if is_checkmate and king_pos2 and isinstance(game_state2.get_piece_at(king_pos2[0], king_pos2[1]), King) and should_show_anim2:
        print("   ✓ 绝杀状态下正确返回将军王位置并显示动画")
    else:
        print("   ✗ 绝杀状态下返回将军王位置或显示动画错误")
    
    # 测试3：游戏结束状态下的将军显示逻辑
    print("\n3. 测试游戏结束状态下的将军显示逻辑:")
    
    # 模拟游戏结束情况
    game_state3 = GameState()
    game_state3.pieces.clear()
    
    # 放置棋子
    red_king3 = King("red", 10, 6)
    black_ju3 = Ju("black", 7, 6)
    game_state3.pieces.extend([red_king3, black_ju3])
    
    game_state3.player_turn = "black"
    game_state3.is_check = True  # 设置为将军状态
    game_state3.check_animation_time = time.time()  # 设置动画时间
    game_state3.game_over = True  # 但是游戏已结束
    
    # 在游戏结束后，不应该显示将军动画
    should_show_after_game_over = game_state3.should_show_check_animation()
    king_pos_after_game_over = game_state3.get_checked_king_position()
    
    print(f"   游戏结束后是否应显示将军动画: {should_show_after_game_over}")
    print(f"   游戏结束后是否返回将军位置: {king_pos_after_game_over is not None}")
    
    if not should_show_after_game_over and king_pos_after_game_over is None:
        print("   ✓ 游戏结束后正确不显示将军动画")
    else:
        print("   ✗ 游戏结束后错误显示将军动画")
    
    print("\n测试完成！")


if __name__ == "__main__":
    test_check_and_checkmate_logic()