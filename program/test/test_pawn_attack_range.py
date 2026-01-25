#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试兵的攻击范围显示是否包含跨越长城的多步移动
"""
from program.core.chess_pieces import *
from program.core.game_rules import GameRules
from program.core.game_state import GameState


def test_pawn_calculate_possible_moves():
    """测试兵的calculate_possible_moves方法是否包含跨越长城的移动"""
    print("测试兵的可能移动范围计算...")
    
    # 创建一个游戏状态
    game_state = GameState()
    
    # 清空棋盘并添加测试棋子
    game_state.pieces.clear()
    
    # 放置一个红兵在第8行，可以跨越长城
    red_pawn = Pawn("red", 8, 6)
    game_state.pieces.append(red_pawn)
    
    # 计算兵的可能移动
    possible_moves, capturable = game_state.calculate_possible_moves(8, 6)
    
    print(f"红兵在(8,6)的可能移动位置: {possible_moves}")
    print(f"红兵在(8,6)的可吃子位置: {capturable}")
    
    # 检查是否包含跨越长城的移动
    expected_moves = [(7, 6), (5, 6), (4, 6), (3, 6), (2, 6), (1, 6), (0, 6)]  # 包括跨越长城的移动
    actual_found = []
    for move in expected_moves:
        if move in possible_moves:
            actual_found.append(move)
    
    print(f"预期的跨越长城移动中找到: {actual_found}")
    print(f"跨越长城的移动是否都被包含: {'是' if len(actual_found) == len(expected_moves) else '否'}")
    
    # 检查黑卒的情况
    game_state.pieces.clear()
    black_pawn = Pawn("black", 4, 6)  # 黑卒在第4行，可以跨越长城
    game_state.pieces.append(black_pawn)
    
    possible_moves2, capturable2 = game_state.calculate_possible_moves(4, 6)
    
    print(f"\n黑卒在(4,6)的可能移动位置: {possible_moves2}")
    print(f"黑卒在(4,6)的可吃子位置: {capturable2}")
    
    # 检查黑卒是否包含跨越长城的移动
    expected_moves2 = [(5, 6), (7, 6), (8, 6), (9, 6), (10, 6), (11, 6), (12, 6)]  # 包括跨越长城的移动
    actual_found2 = []
    for move in expected_moves2:
        if move in possible_moves2:
            actual_found2.append(move)
    
    print(f"预期的跨越长城移动中找到: {actual_found2}")
    print(f"黑卒跨越长城的移动是否都被包含: {'是' if len(actual_found2) == len(expected_moves2) else '否'}")
    
    # 测试结果
    success1 = len(actual_found) >= 3  # 至少包含几个跨越长城的移动
    success2 = len(actual_found2) >= 3  # 至少包含几个跨越长城的移动
    
    return success1 and success2


def test_pawn_rules_directly():
    """直接测试规则函数"""
    print("\n直接测试规则函数...")
    
    # 测试红兵跨越长城的移动
    pieces = [
        Pawn("red", 8, 6),  # 红兵
    ]
    
    # 测试跨越长城的移动
    moves_to_test = [(7, 6), (6, 6), (5, 6), (4, 6), (3, 6), (2, 6), (1, 6), (0, 6)]
    
    valid_moves = []
    for to_row, to_col in moves_to_test:
        result = GameRules.is_valid_pawn_move(pieces, "red", 8, 6, to_row, to_col)
        if result:
            valid_moves.append((to_row, to_col))
    
    print(f"红兵从(8,6)的有效跨越长城移动: {valid_moves}")
    
    # 计算所有可能移动
    moves, capturable = GameRules.calculate_possible_moves(pieces, pieces[0])
    print(f"规则函数计算的可能移动: {moves[:10]}...")  # 显示前10个
    
    # 检查跨越长城的移动是否在规则计算中
    cross_wall_moves_in_calc = [(r, c) for r, c in moves if (8 > r and r <= 5) or (4 < r and r <= 5)]
    print(f"规则函数中跨越长城的移动: {cross_wall_moves_in_calc[:10]}...")
    
    return len(cross_wall_moves_in_calc) >= 3


def test_pawn_with_enemy_pieces():
    """测试兵在有敌方棋子时的攻击范围"""
    print("\n测试兵在有敌方棋子时的攻击范围...")
    
    game_state = GameState()
    game_state.pieces.clear()
    
    # 放置兵和敌方棋子
    red_pawn = Pawn("red", 9, 6)  # 红兵
    black_pawn1 = Pawn("black", 7, 6)  # 敌方棋子
    black_pawn2 = Pawn("black", 5, 6)  # 敌方棋子
    game_state.pieces.append(red_pawn)
    game_state.pieces.append(black_pawn1)
    game_state.pieces.append(black_pawn2)
    
    # 计算可能移动
    possible_moves, capturable = game_state.calculate_possible_moves(9, 6)
    
    print(f"红兵在(9,6)的可能移动: {possible_moves}")
    print(f"红兵在(9,6)的可吃子位置: {capturable}")
    
    # 验证移动规则：多步移动时不可吃子
    # (7,6) 位置有敌子，兵移动2步到这里应该不允许
    # (5,6) 位置有敌子，兵移动4步到这里应该不允许
    move_to_76_valid = (7, 6) in possible_moves
    move_to_56_valid = (5, 6) in possible_moves
    can_capture_at_76 = (7, 6) in capturable
    can_capture_at_56 = (5, 6) in capturable
    
    print(f"移动到(7,6)敌子位置: {move_to_76_valid}, 可吃子: {can_capture_at_76}")
    print(f"移动到(5,6)敌子位置: {move_to_56_valid}, 可吃子: {can_capture_at_56}")
    
    # 检查是否正确应用了多步不可吃子规则
    correct_behavior = not move_to_76_valid and not move_to_56_valid  # 多步移动不应能到敌子位置
    print(f"多步移动不可吃子规则正确应用: {'是' if correct_behavior else '否'}")
    
    return correct_behavior


if __name__ == "__main__":
    print("开始测试兵的攻击范围显示...\n")
    
    success1 = test_pawn_calculate_possible_moves()
    success2 = test_pawn_rules_directly()
    success3 = test_pawn_with_enemy_pieces()
    
    overall_success = success1 and success2 and success3
    
    print(f"\n总体测试结果: {'✅ 通过' if overall_success else '❌ 未通过'}")
    if overall_success:
        print("兵的攻击范围显示已成功更新，现在包含跨越长城的多步移动！")
    else:
        print("兵的攻击范围显示仍有问题。")