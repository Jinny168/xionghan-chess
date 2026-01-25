#!/usr/bin/env python
"""
验证匈汉象棋将军/绝杀逻辑修复
解决用户提到的问题：
1. 将军提示位置错误
2. 绝杀时未正确显示结束界面
"""

from program.core.game_state import GameState
from program.core.game_rules import GameRules
from program.core.chess_pieces import *

def test_issue_fixed():
    """验证原始问题是否已修复"""
    print("验证匈汉象棋将军/绝杀逻辑修复")
    print("=" * 50)
    
    # 模拟用户描述的问题场景
    print("1. 测试将军提示位置是否正确")
    
    game_state = GameState()
    game_state.pieces.clear()
    
    # 设置一个将军场景
    red_king = King('red', 9, 6)  # 红将在九宫中心
    black_ju = Ju('black', 7, 6)  # 黑车在下方将军
    
    game_state.pieces = [red_king, black_ju]
    game_state.player_turn = 'black'  # 黑方回合
    
    # 模拟移动后的情况
    is_red_in_check = GameRules.is_check(game_state.pieces, 'red')
    game_state.is_check = is_red_in_check
    
    # 测试被将军的王的位置获取
    king_pos = game_state.get_checked_king_position()
    print(f"   被将军的王的位置: {king_pos}")
    print(f"   预期位置: (9, 6)")
    
    if king_pos == (9, 6):
        print("   ✓ 将军提示位置正确")
    else:
        print("   ✗ 将军提示位置错误")
    
    print("\n2. 测试绝杀时不会显示将军动画")
    
    # 设置一个绝杀场景
    game_state2 = GameState()
    game_state2.pieces.clear()
    
    red_king2 = King('red', 9, 6)
    black_ju2 = Ju('black', 8, 6)
    # 完全封锁红将的所有逃跑路线
    blocker1 = Ju('black', 8, 5)  # 左上
    blocker2 = Ju('black', 8, 7)  # 右上
    blocker3 = Ju('black', 10, 5) # 左下
    blocker4 = Ju('black', 10, 6) # 正下
    blocker5 = Ju('black', 10, 7) # 右下
    blocker6 = Ju('black', 9, 5)  # 左
    blocker7 = Ju('black', 9, 7)  # 右
    
    game_state2.pieces = [red_king2, black_ju2, blocker1, blocker2, blocker3, blocker4, blocker5, blocker6, blocker7]
    game_state2.player_turn = 'black'
    
    is_red_in_check2 = GameRules.is_check(game_state2.pieces, 'red')
    is_red_in_checkmate2 = GameRules.is_checkmate(game_state2.pieces, 'red')
    
    # 模拟游戏结束情况
    game_over, winner = GameRules.is_game_over(game_state2.pieces, 'black')
    game_state2.game_over = game_over
    game_state2.winner = winner
    game_state2.is_check = is_red_in_check2  # 即使被将军，但由于游戏结束，不应显示动画
    
    print(f"   红方被将军: {is_red_in_check2}")
    print(f"   红方被将死: {is_red_in_checkmate2}")
    print(f"   游戏结束: {game_over}")
    
    # 测试在游戏结束状态下是否还会返回被将军的王的位置
    king_pos2 = game_state2.get_checked_king_position()
    print(f"   游戏结束后被将军的王的位置: {king_pos2}")
    
    if game_over and king_pos2 is None:
        print("   ✓ 绝杀时不会显示将军动画（正确）")
    elif game_over and king_pos2 is not None:
        print("   ✗ 绝杀时仍显示将军动画（错误）")
    else:
        print("   ? 非绝杀情况")
    
    print("\n3. 测试绝杀时游戏结束界面是否正确触发")
    
    # 检查绝杀时游戏是否正确结束
    if is_red_in_checkmate2 and game_over and winner == 'black':
        print("   ✓ 绝杀时游戏正确结束并确定获胜方")
    else:
        print("   ✗ 绝杀时游戏结束逻辑有误")
    
    print("\n4. 测试将军动画显示条件")
    
    # 测试普通将军情况下（非绝杀）是否正确显示
    game_state3 = GameState()
    game_state3.pieces.clear()
    
    red_king3 = King('red', 9, 6)
    black_ju3 = Ju('black', 7, 6)
    # 只有一个将军者，不构成绝杀
    game_state3.pieces = [red_king3, black_ju3]
    game_state3.player_turn = 'black'
    
    is_red_in_check3 = GameRules.is_check(game_state3.pieces, 'red')
    is_red_in_checkmate3 = GameRules.is_checkmate(game_state3.pieces, 'red')
    game_state3.is_check = is_red_in_check3
    game_state3.game_over = False  # 确保游戏未结束
    
    should_show_anim = game_state3.should_show_check_animation()
    king_pos3 = game_state3.get_checked_king_position()
    
    print(f"   普通将军: {is_red_in_check3}, 是否绝杀: {is_red_in_checkmate3}")
    print(f"   游戏结束: {game_state3.game_over}")
    print(f"   应该显示将军动画: {should_show_anim}")
    print(f"   被将军王的位置: {king_pos3}")
    
    if is_red_in_check3 and not is_red_in_checkmate3 and not game_state3.game_over and king_pos3 is not None:
        print("   ✓ 普通将军时正确显示将军动画")
    else:
        print("   ✗ 普通将军时显示错误")
    
    print("\n" + "=" * 50)
    print("验证完成!")
    
    # 总结
    all_checks_pass = (
        king_pos == (9, 6) and  # 将军位置正确
        ((game_over and king_pos2 is None) or not game_over) and  # 绝杀时无将军动画
        (is_red_in_checkmate2 and game_over and winner == 'black') and  # 绝杀结束游戏
        (is_red_in_check3 and not is_red_in_checkmate3 and not game_state3.game_over and king_pos3 is not None)  # 普通将军正确显示
    )
    
    if all_checks_pass:
        print("✓ 所有修复验证通过！将军/绝杀逻辑已正确修复。")
    else:
        print("✗ 部分验证未通过，请检查代码。")

if __name__ == "__main__":
    test_issue_fixed()