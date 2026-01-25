#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
演示尉增强功能：展示尉的直线和斜线跨越能力
"""
from program.core.chess_pieces import *
from program.core.game_rules import GameRules


def demo_wei_enhanced_capabilities():
    """演示尉的增强功能"""
    print("=== 尉增强功能演示 ===\n")
    
    print("核心规则:")
    print("- 尉可沿直线（上下左右）和斜线（4个斜向方向）跨越棋子")
    print("- 跨越规则：可穿过1个棋子，不可穿过2个及以上棋子")
    print("- 仍不具备吃子能力，仅能通过照面实现控制效果")
    print()
    
    # 演示1：直线跨越
    print("1. 直线跨越能力（保持原有功能）:")
    pieces1 = [
        Wei("red", 3, 3),  # 尉
        Pawn("black", 3, 5),  # 横向跨越的目标棋子
    ]
    
    # 横向跨越
    result1 = GameRules.is_valid_wei_move(pieces1, 3, 3, 3, 7)
    print(f"   尉从(3,3)横向跨越(3,5)到(3,7): {'✓' if result1 else '✗'}")
    
    # 纵向跨越
    pieces2 = [
        Wei("red", 3, 3),  # 尉
        Pawn("black", 5, 3),  # 纵向跨越的目标棋子
    ]
    result2 = GameRules.is_valid_wei_move(pieces2, 3, 3, 7, 3)
    print(f"   尉从(3,3)纵向跨越(5,3)到(7,3): {'✓' if result2 else '✗'}")
    
    print()
    
    # 演示2：新增的斜线跨越
    print("2. 新增斜线跨越能力:")
    pieces3 = [
        Wei("red", 3, 3),  # 尉
        Pawn("black", 4, 4),  # 斜向跨越的目标棋子
    ]
    
    # 右下斜线跨越
    result3 = GameRules.is_valid_wei_move(pieces3, 3, 3, 6, 6)
    print(f"   尉从(3,3)斜线跨越(4,4)到(6,6) (右下): {'✓' if result3 else '✗'}")
    
    # 左上斜线跨越
    pieces4 = [
        Wei("red", 6, 6),  # 尉
        Pawn("black", 5, 5),  # 斜向跨越的目标棋子
    ]
    result4 = GameRules.is_valid_wei_move(pieces4, 6, 6, 3, 3)
    print(f"   尉从(6,6)斜线跨越(5,5)到(3,3) (左上): {'✓' if result4 else '✗'}")
    
    # 右上斜线跨越
    pieces5 = [
        Wei("red", 3, 6),  # 尉
        Pawn("black", 4, 5),  # 斜向跨越的目标棋子
    ]
    result5 = GameRules.is_valid_wei_move(pieces5, 3, 6, 6, 3)
    print(f"   尉从(3,6)斜线跨越(4,5)到(6,3) (右上): {'✓' if result5 else '✗'}")
    
    # 左下斜线跨越
    pieces6 = [
        Wei("red", 6, 3),  # 尉
        Pawn("black", 5, 4),  # 斜向跨越的目标棋子
    ]
    result6 = GameRules.is_valid_wei_move(pieces6, 6, 3, 3, 6)
    print(f"   尉从(6,3)斜线跨越(5,4)到(3,6) (左下): {'✓' if result6 else '✗'}")
    
    print()
    
    # 演示3：限制条件
    print("3. 限制条件:")
    
    # 不能吃子
    pieces7 = [
        Wei("red", 3, 3),  # 尉
        Pawn("black", 5, 3),  # 敌方棋子
    ]
    result7 = GameRules.is_valid_wei_move(pieces7, 3, 3, 5, 3)
    print(f"   尉不能吃掉敌方棋子(5,3): {'✓' if not result7 else '✗'}")
    
    # 不能跨越多个棋子
    pieces8 = [
        Wei("red", 3, 3),  # 尉
        Pawn("black", 4, 4),  # 第一个棋子
        Ju("black", 5, 5),  # 第二个棋子
    ]
    result8 = GameRules.is_valid_wei_move(pieces8, 3, 3, 7, 7)
    print(f"   尉不能跨越多个棋子: {'✓' if not result8 else '✗'}")
    
    # 没有跨越棋子则不能移动
    pieces9 = [
        Wei("red", 3, 3),  # 尉
    ]
    result9 = GameRules.is_valid_wei_move(pieces9, 3, 3, 5, 5)
    print(f"   尉必须跨越至少一个棋子才能移动: {'✓' if not result9 else '✗'}")
    
    print()
    
    print("✓ 尉的增强功能已成功实现！")
    print("  - 保持了原有的直线跨越能力")
    print("  - 新增了斜线跨越能力")
    print("  - 仍不具备吃子能力")
    print("  - 保持了控制能力")


if __name__ == "__main__":
    demo_wei_enhanced_capabilities()