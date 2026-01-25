#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
演示兵/卒增强功能：展示跨越长城能力及移动步数优化
"""
from program.core.chess_pieces import *
from program.core.game_rules import GameRules


def demo_pawn_enhanced_capabilities():
    """演示兵/卒的增强功能"""
    print("=== 兵/卒增强功能演示 ===\n")
    
    print("核心规则:")
    print("- 兵/卒在未跨越长城前可进行远距离移动")
    print("- 移动多步时不可吃子，但移动1步时遵循原有规则")
    print("- 跨越长城后恢复原有移动规则")
    print("- 攻击范围始终为上下左右1格，与移动步数无关")
    print()
    
    # 演示1：红兵跨越长城能力
    print("1. 红兵跨越长城能力:")
    pieces1 = [
        Pawn("red", 8, 6),  # 红兵在第8行
    ]
    
    # 测试红兵的各种跨越能力
    moves = [
        (7, 6), (6, 6), (5, 6), (4, 6), (3, 6), (2, 6), (1, 6), (0, 6)
    ]
    
    valid_moves = []
    for to_row, to_col in moves:
        if GameRules.is_valid_pawn_move(pieces1, "red", 8, 6, to_row, to_col):
            steps = 8 - to_row
            valid_moves.append((to_row, to_col, steps))
    
    print(f"   红兵在(8,6)的有效移动:")
    for to_row, to_col, steps in valid_moves:
        print(f"     到({to_row},{to_col}), 移动{steps}步{'(跨越长城)' if to_row <= 5 else '(未跨越)'}")
    
    print()
    
    # 演示2：黑卒跨越长城能力
    print("2. 黑卒跨越长城能力:")
    pieces2 = [
        Pawn("black", 4, 6),  # 黑卒在第4行
    ]
    
    # 测试黑卒的各种跨越能力
    moves = [
        (5, 6), (6, 6), (7, 6), (8, 6), (9, 6), (10, 6), (11, 6), (12, 6)
    ]
    
    valid_moves = []
    for to_row, to_col in moves:
        if GameRules.is_valid_pawn_move(pieces2, "black", 4, 6, to_row, to_col):
            steps = to_row - 4
            valid_moves.append((to_row, to_col, steps))
    
    print(f"   黑卒在(4,6)的有效移动:")
    for to_row, to_col, steps in valid_moves:
        print(f"     到({to_row},{to_col}), 移动{steps}步{'(跨越长城)' if to_row >= 7 else '(未跨越)'}")
    
    print()
    
    # 演示3：不可吃子规则
    print("3. 移动多步时不可吃子规则:")
    
    # 红兵多步移动遇敌子
    pieces3 = [
        Pawn("red", 9, 6),  # 红兵在第9行
        Pawn("black", 7, 6),  # 敌方棋子在第7行
    ]
    
    result1 = GameRules.is_valid_pawn_move(pieces3, "red", 9, 6, 6, 6)  # 移动3步到敌子位置
    print(f"   红兵从(9,6)移动3步到(6,6)遇敌子: {'✗ 不可移动' if not result1 else '✓ 可移动'}")
    
    result2 = GameRules.is_valid_pawn_move(pieces3, "red", 9, 6, 8, 6)  # 移动1步
    print(f"   红兵从(9,6)移动1步到(8,6): {'✓ 可移动' if result2 else '✗ 不可移动'}")
    
    # 黑卒多步移动遇敌子
    pieces4 = [
        Pawn("black", 2, 6),  # 黑卒在第2行
        Pawn("red", 4, 6),  # 敌方棋子在第4行
    ]
    
    result3 = GameRules.is_valid_pawn_move(pieces4, "black", 2, 6, 5, 6)  # 移动3步到敌子位置
    print(f"   黑卒从(2,6)移动3步到(5,6)遇敌子: {'✗ 不可移动' if not result3 else '✓ 可移动'}")
    
    result4 = GameRules.is_valid_pawn_move(pieces4, "black", 2, 6, 3, 6)  # 移动1步
    print(f"   黑卒从(2,6)移动1步到(3,6): {'✓ 可移动' if result4 else '✗ 不可移动'}")
    
    print()
    
    # 演示4：路径阻挡处理
    print("4. 路径阻挡处理:")
    
    pieces5 = [
        Pawn("red", 10, 6),  # 红兵在第10行
        Pawn("black", 8, 6),  # 阻挡棋子在第8行
    ]
    
    result5 = GameRules.is_valid_pawn_move(pieces5, "red", 10, 6, 6, 6)  # 移动4步，路径有阻挡
    print(f"   红兵从(10,6)移动4步到(6,6)路径遇阻挡: {'✗ 不可移动' if not result5 else '✓ 可移动'}")
    
    result6 = GameRules.is_valid_pawn_move(pieces5, "red", 10, 6, 9, 6)  # 移动1步到空位
    print(f"   红兵从(10,6)移动1步到(9,6)空位: {'✓ 可移动' if result6 else '✗ 不可移动'}")
    
    result7 = GameRules.is_valid_pawn_move(pieces5, "red", 10, 6, 8, 6)  # 移动2步到阻挡位置
    print(f"   红兵从(10,6)移动2步到(8,6)阻挡位置: {'✗ 不可移动' if not result7 else '✓ 可移动'}")
    
    print()
    
    # 演示5：跨越长城后移动规则
    print("5. 跨越长城后移动规则:")
    
    pieces6 = [
        Pawn("red", 5, 6),  # 红兵已在敌方阵地
    ]
    
    # 测试已跨越长城后的移动
    moves_after_crossing = [
        (4, 6), (5, 5), (5, 7)  # 前、左、右
    ]
    
    for to_row, to_col in moves_after_crossing:
        result = GameRules.is_valid_pawn_move(pieces6, "red", 5, 6, to_row, to_col)
        direction = "前" if to_row < 5 else "左" if to_col < 6 else "右"
        print(f"   已跨越长城红兵向{direction}移动到({to_row},{to_col}): {'✓' if result else '✗'}")
    
    # 测试向后移动（不允许）
    result_back = GameRules.is_valid_pawn_move(pieces6, "red", 5, 6, 6, 6)
    print(f"   已跨越长城红兵向后移动到(6,6): {'✗ 不可移动' if not result_back else '✓ 可移动'}")
    
    print()
    
    print("✅ 兵/卒增强功能已成功实现！")
    print("  - 未跨越长城时可进行远距离移动")
    print("  - 移动多步时不可吃子")
    print("  - 正确处理路径阻挡")
    print("  - 跨越长城后恢复原有移动规则")


if __name__ == "__main__":
    demo_pawn_enhanced_capabilities()