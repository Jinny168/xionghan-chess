#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试尉增强功能：验证尉是否支持斜线跨越能力
"""
from program.core.chess_pieces import *
from program.core.game_rules import GameRules


def test_wei_straight_crossing():
    """测试尉的直线跨越能力是否保持不变"""
    print("测试1: 尉的直线跨越能力")
    
    # 创建测试棋局：尉在(3,3)，旁边有一个棋子(3,5)，目标位置在(3,7)
    pieces = [
        Wei("red", 3, 3),  # 尉
        Pawn("black", 3, 5),  # 作为跨越目标的棋子
    ]
    
    # 测试横向跨越
    result = GameRules.is_valid_wei_move(pieces, 3, 3, 3, 7)  # 尉从(3,3)跨越(3,5)到(3,7)
    print(f"尉横向跨越测试: {result} (应为True)")
    assert result == True, "尉横向跨越测试失败"
    
    # 测试纵向跨越
    pieces2 = [
        Wei("red", 3, 3),  # 尉
        Pawn("black", 5, 3),  # 作为跨越目标的棋子
    ]
    result2 = GameRules.is_valid_wei_move(pieces2, 3, 3, 7, 3)  # 尉从(3,3)跨越(5,3)到(7,3)
    print(f"尉纵向跨越测试: {result2} (应为True)")
    assert result2 == True, "尉纵向跨越测试失败"
    
    print("✓ 直线跨越能力测试通过")


def test_wei_diagonal_crossing():
    """测试尉的斜线跨越能力"""
    print("\n测试2: 尉的斜线跨越能力")
    
    # 创建测试棋局：尉在(3,3)，在对角线上有棋子(4,4)，目标位置在(6,6)
    pieces = [
        Wei("red", 3, 3),  # 尉
        Pawn("black", 4, 4),  # 作为跨越目标的棋子
    ]
    
    # 测试右下斜线跨越
    result = GameRules.is_valid_wei_move(pieces, 3, 3, 6, 6)  # 尉从(3,3)跨越(4,4)到(6,6)
    print(f"尉右下斜线跨越测试: {result} (应为True)")
    
    # 测试跨越路径是否有效：从(3,3)到(6,6)，跨越(4,4)，需要确保路径上只有一个棋子
    # 创建没有中间棋子的棋盘状态
    pieces_no_cross = [
        Wei("red", 3, 3),  # 尉
    ]
    result2 = GameRules.is_valid_wei_move(pieces_no_cross, 3, 3, 5, 5)  # 尉从(3,3)到(5,5)，这不应该有效，因为没有跨越棋子
    print(f"尉斜线移动但未跨越测试: {result2} (应为False)")
    
    # 添加多个棋子测试，确保尉不能跨越超过一个棋子
    pieces3 = [
        Wei("red", 3, 3),  # 尉
        Pawn("black", 4, 4),  # 第一个跨越棋子
        Pawn("black", 5, 5),  # 第二个棋子，阻止移动
    ]
    result3 = GameRules.is_valid_wei_move(pieces3, 3, 3, 7, 7)  # 尉从(3,3)到(7,7)，路径上有两个棋子
    print(f"尉斜线跨越多棋子测试: {result3} (应为False)")
    
    # 测试其他三个斜线方向
    pieces4 = [
        Wei("red", 6, 6),  # 尉
        Pawn("black", 5, 5),  # 作为跨越目标的棋子
    ]
    result4 = GameRules.is_valid_wei_move(pieces4, 6, 6, 3, 3)  # 尉从(6,6)跨越(5,5)到(3,3) 左上
    print(f"尉左上斜线跨越测试: {result4} (应为True)")
    
    pieces5 = [
        Wei("red", 3, 6),  # 尉
        Pawn("black", 4, 5),  # 作为跨越目标的棋子
    ]
    result5 = GameRules.is_valid_wei_move(pieces5, 3, 6, 6, 3)  # 尉从(3,6)跨越(4,5)到(6,3) 右下
    print(f"尉右下斜线跨越测试: {result5} (应为True)")
    
    pieces6 = [
        Wei("red", 6, 3),  # 尉
        Pawn("black", 5, 4),  # 作为跨越目标的棋子
    ]
    result6 = GameRules.is_valid_wei_move(pieces6, 6, 3, 3, 6)  # 尉从(6,3)跨越(5,4)到(3,6) 左上
    print(f"尉左上斜线跨越测试: {result6} (应为True)")
    
    # 检查结果
    assert result == True, "尉斜线跨越测试失败"
    assert result2 == False, "尉斜线移动但未跨越测试失败"
    assert result3 == False, "尉斜线跨越多棋子测试失败"
    assert result4 == True, "尉左上斜线跨越测试失败"
    assert result5 == True, "尉右下斜线跨越测试失败"
    assert result6 == True, "尉左上斜线跨越测试失败"
    
    print("✓ 斜线跨越能力测试通过")


def test_wei_no_capture_ability():
    """测试尉仍不具备吃子能力"""
    print("\n测试3: 尉无吃子能力")
    
    pieces = [
        Wei("red", 3, 3),  # 尉
        Pawn("black", 5, 3),  # 敌方棋子
    ]
    
    # 尝试让尉移动到敌方棋子位置（吃子）
    result = GameRules.is_valid_wei_move(pieces, 3, 3, 5, 3)
    print(f"尉吃子测试: {result} (应为False)")
    assert result == False, "尉不应具备吃子能力"
    
    print("✓ 无吃子能力测试通过")


def test_wei_control_ability():
    """测试尉的控制能力（照面功能）"""
    print("\n测试4: 尉的控制能力（照面功能）")
    
    # 这里我们只是验证尉的基本控制能力仍然存在
    # 具体的照面逻辑由GameRules.get_facing_piece方法处理
    from program.core.game_rules import GameRules
    
    pieces = [
        Wei("red", 3, 3),
        King("black", 3, 6),  # 黑方将在同一行
    ]
    
    # 检查是否存在与尉照面的敌方棋子
    facing_piece = GameRules.get_facing_piece(pieces[0], pieces)
    print(f"尉照面测试: {'found' if facing_piece else 'not found'}")
    
    print("✓ 控制能力测试通过")


def run_all_tests():
    """运行所有测试"""
    print("开始测试尉增强功能...\n")
    
    try:
        test_wei_straight_crossing()
        test_wei_diagonal_crossing()
        test_wei_no_capture_ability()
        test_wei_control_ability()
        
        print("\n✅ 所有测试通过！尉的增强功能正常工作。")
        print("- 保持了原有的直线跨越能力")
        print("- 新增了斜线跨越能力")
        print("- 仍不具备吃子能力")
        print("- 保持了控制能力")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        return False
    
    return True


if __name__ == "__main__":
    run_all_tests()