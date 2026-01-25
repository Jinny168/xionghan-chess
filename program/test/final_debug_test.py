#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
匈汉象棋将军/绝杀最终调试测试脚本
"""

def test_final_debug():
    """最终调试测试"""
    print("=== 匈汉象棋将军/绝杀最终调试测试 ===")
    
    from program.core.game_state import GameState
    from program.core.game_rules import GameRules
    from program.core.chess_pieces import King, Ju
    import time
    
    print("\n1. 测试将军动画显示逻辑")
    
    # 测试普通将军情况
    game_state = GameState()
    game_state.pieces.clear()
    
    red_king = King("red", 9, 6)
    black_ju = Ju("black", 6, 6)
    game_state.pieces.extend([red_king, black_ju])
    game_state.player_turn = "black"
    
    is_check = GameRules.is_check(game_state.pieces, "red")
    game_state.is_check = is_check
    game_state.check_animation_time = time.time()
    
    print(f"   普通将军: {is_check}")
    print(f"   是否显示将军动画: {game_state.should_show_check_animation()}")
    print(f"   被将军王位置: {game_state.get_checked_king_position()}")
    
    print("\n2. 测试绝杀逻辑")
    
    # 测试绝杀情况
    game_state2 = GameState()
    game_state2.pieces.clear()
    
    red_king2 = King("red", 11, 6)
    black_ju2 = Ju("black", 8, 6)
    blocker1 = Ju('black', 10, 5)
    blocker2 = Ju('black', 10, 7)
    blocker3 = Ju('black', 11, 5)
    blocker4 = Ju('black', 11, 7)
    
    game_state2.pieces.extend([red_king2, black_ju2, blocker1, blocker2, blocker3, blocker4])
    game_state2.player_turn = "black"
    
    is_check2 = GameRules.is_check(game_state2.pieces, "red")
    is_checkmate2 = GameRules.is_checkmate(game_state2.pieces, "red")
    
    game_state2.is_check = is_check2
    game_state2.check_animation_time = time.time()
    
    print(f"   绝杀情况 - 被将军: {is_check2}")
    print(f"   绝杀情况 - 被将死: {is_checkmate2}")
    print(f"   绝杀时是否显示将军动画: {game_state2.should_show_check_animation()}")
    print(f"   绝杀时被将军王位置: {game_state2.get_checked_king_position()}")
    print(f"   绝杀时游戏状态is_checkmate(): {game_state2.is_checkmate()}")
    
    print("\n3. 测试游戏结束后的状态")
    
    # 模拟游戏结束后
    game_state2.game_over = True
    print(f"   游戏结束后是否显示将军动画: {game_state2.should_show_check_animation()}")
    print(f"   游戏结束后被将军王位置: {game_state2.get_checked_king_position()}")
    
    print("\n4. 测试将军/绝杀检测函数")
    
    # 检查GameRules的函数
    game_over, winner = GameRules.is_game_over(game_state2.pieces, game_state2.player_turn)
    print(f"   GameRules.is_game_over(): 游戏结束={game_over}, 胜者={winner}")
    
    print("\n=== 所有调试测试完成 ===")
    print("现在您可以使用这些调试信息来排除游戏中的bug。")


if __name__ == "__main__":
    test_final_debug()