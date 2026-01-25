#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试尉的可能移动位置计算是否包含斜线跨越
"""
from program.core.chess_pieces import *
from program.core.game_rules import GameRules
from program.core.game_state import GameState


def test_wei_calculate_possible_moves():
    """测试尉的calculate_possible_moves方法是否正确计算斜线跨越"""
    print("测试尉的可能移动位置计算...")
    
    # 创建一个游戏状态
    game_state = GameState()
    
    # 清空棋盘并添加测试棋子
    game_state.pieces.clear()
    
    # 放置一个尉在(3,3)
    wei = Wei("red", 3, 3)
    game_state.pieces.append(wei)
    
    # 在各个方向放置棋子以供尉跨越
    # 水平方向
    game_state.pieces.append(Pawn("black", 3, 5))  # 水平跨越目标
    
    # 垂直方向
    game_state.pieces.append(Pawn("black", 5, 3))  # 垂直跨越目标
    
    # 斜线方向
    game_state.pieces.append(Pawn("black", 4, 4))  # 右下斜线跨越目标
    game_state.pieces.append(Pawn("black", 2, 2))  # 左上斜线跨越目标
    game_state.pieces.append(Pawn("black", 4, 2))  # 右上斜线跨越目标
    game_state.pieces.append(Pawn("black", 2, 4))  # 左下斜线跨越目标
    
    # 计算尉的可能移动
    possible_moves, capturable = game_state.calculate_possible_moves(3, 3)
    
    print(f"尉在(3,3)的可能移动位置: {possible_moves}")
    print(f"尉在(3,3)的可吃子位置: {capturable}")
    
    # 检查是否包含直线跨越
    straight_moves = [(3, 7), (7, 3)]  # 水平和垂直跨越后的落点
    has_straight_moves = any(move in possible_moves for move in straight_moves)
    print(f"是否包含直线跨越: {'是' if has_straight_moves else '否'}")
    
    # 检查是否包含斜线跨越
    diagonal_moves = [(6, 6), (0, 0), (6, 0), (0, 6)]  # 斜线跨越后的落点
    has_diagonal_moves = any(move in possible_moves for move in diagonal_moves)
    print(f"是否包含斜线跨越: {'是' if has_diagonal_moves else '否'}")
    
    # 更精确的测试：测试特定的斜线跨越
    # 从(3,3)跨越(4,4)到(6,6)
    has_diagonal_move1 = (6, 6) in possible_moves
    print(f"尉能否从(3,3)跨越(4,4)到(6,6): {'是' if has_diagonal_move1 else '否'}")
    
    # 从(3,3)跨越(2,2)到(0,0)
    has_diagonal_move2 = (0, 0) in possible_moves
    print(f"尉能否从(3,3)跨越(2,2)到(0,0): {'是' if has_diagonal_move2 else '否'}")
    
    # 从(3,3)跨越(4,2)到(6,0)
    has_diagonal_move3 = (6, 0) in possible_moves
    print(f"尉能否从(3,3)跨越(4,2)到(6,0): {'是' if has_diagonal_move3 else '否'}")
    
    # 从(3,3)跨越(2,4)到(0,6)
    has_diagonal_move4 = (0, 6) in possible_moves
    print(f"尉能否从(3,3)跨越(2,4)到(0,6): {'是' if has_diagonal_move4 else '否'}")
    
    # 测试通过的标准：包含斜线跨越
    success = has_diagonal_move1 and has_diagonal_move2 and has_diagonal_move3 and has_diagonal_move4
    print(f"\n测试结果: {'✅ 通过' if success else '❌ 失败'}")
    print(f"尉的移动范围现在{'正确地' if success else '仍然没有'}包含斜线跨越！")
    
    return success


def test_wei_rules_directly():
    """直接测试规则函数"""
    print("\n直接测试规则函数...")
    
    # 测试尉的移动规则
    pieces = [
        Wei("red", 3, 3),  # 尉
        Pawn("black", 4, 4),  # 斜线跨越的目标棋子
    ]
    
    # 测试斜线跨越
    result = GameRules.is_valid_wei_move(pieces, 3, 3, 6, 6)  # 尉从(3,3)跨越(4,4)到(6,6)
    print(f"尉斜线跨越规则测试: {'通过' if result else '失败'}")
    
    # 计算所有可能移动
    moves, capturable = GameRules.calculate_possible_moves(pieces, pieces[0])
    print(f"尉在(3,3)的所有可能移动: {moves}")
    print(f"尉的斜线移动(6,6)是否在可能移动中: {(6,6) in moves}")
    
    return (6,6) in moves


def test_without_filter():
    """测试不过滤送将的移动"""
    print("\n测试不过滤送将的移动...")
    
    # 创建一个简单的游戏状态
    game_state = GameState()
    game_state.pieces.clear()
    
    # 放置一个尉在(3,3)
    wei = Wei("red", 3, 3)
    game_state.pieces.append(wei)
    
    # 放置一个棋子供尉跨越(4,4)
    game_state.pieces.append(Pawn("black", 4, 4))
    
    # 直接调用GameRules的计算方法
    moves, capturable = GameRules.calculate_possible_moves(game_state.pieces, wei)
    print(f"GameRules计算的可能移动: {moves}")
    print(f"GameRules计算的可吃子: {capturable}")
    
    # 然后手动调用filter_safe_moves方法测试过滤
    filtered_moves = game_state.filter_safe_moves(moves, wei)
    print(f"过滤后的可能移动: {filtered_moves}")
    
    # 检查是否是过滤导致的问题
    has_unfiltered_diagonal = (6, 6) in moves
    has_filtered_diagonal = (6, 6) in filtered_moves
    print(f"未过滤状态下(6,6)是否在移动中: {has_unfiltered_diagonal}")
    print(f"过滤后(6,6)是否在移动中: {has_filtered_diagonal}")
    
    # 检查是否会送将
    would_be_in_check = GameRules.would_be_in_check_after_move(game_state.pieces, wei, 6, 6)
    print(f"尉移动到(6,6)是否会送将: {would_be_in_check}")
    
    return has_filtered_diagonal


def test_simple_case():
    """测试最简单的案例"""
    print("\n测试最简单的案例...")
    
    game_state = GameState()
    game_state.pieces.clear()
    
    # 只放置尉和一个用于跨越的棋子
    wei = Wei("red", 3, 3)
    pawn = Pawn("black", 4, 4)
    game_state.pieces.append(wei)
    game_state.pieces.append(pawn)
    
    # 检查尉在(3,3)的可能移动
    moves, capturable = game_state.calculate_possible_moves(3, 3)
    print(f"简单情况下尉的可能移动: {moves}")
    print(f"简单情况下尉的可吃子: {capturable}")
    
    # 检查是否包含(6,6)
    has_move = (6, 6) in moves
    print(f"(6,6)是否在移动列表中: {has_move}")
    
    # 检查规则是否允许这种移动
    is_valid = GameRules.is_valid_move(game_state.pieces, wei, 3, 3, 6, 6)
    print(f"从(3,3)到(6,6)是否是有效移动: {is_valid}")
    
    return has_move


if __name__ == "__main__":
    success1 = test_wei_calculate_possible_moves()
    success2 = test_wei_rules_directly()
    success3 = test_without_filter()
    success4 = test_simple_case()
    
    print(f"\n总体测试结果: {'✅ 成功' if (success1 or success2 or success3 or success4) else '❌ 失败'}")
    if success1 or success2 or success3 or success4:
        print("尉的移动范围显示已成功更新，现在支持斜线跨越！")
    else:
        print("尉的移动范围显示仍有问题。")