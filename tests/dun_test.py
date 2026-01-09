"""盾棋子保护机制测试文件"""

import sys
import os

# 修正路径设置
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from program.chess_pieces import *
from program.game_rules import GameRules


def test_shield_immunity_to_capture():
    """测试盾不可被吃的功能"""
    print("测试1: 盾不可被吃的功能")

    # 创建棋子 - 测试己方棋子不能移动到己方棋子位置
    pieces = [
        Ju("red", 0, 0),  # 红车
        Dun("red", 0, 2),  # 红盾
        King("black", 2, 0),  # 黑将
        Dun("black", 2, 2)  # 黑盾
    ]

    # 测试红车能否吃掉红盾（同一颜色，应不允许）
    result = GameRules.is_valid_move(pieces, pieces[0], 0, 0, 0, 2)
    assert not result, "错误：己方棋子不能移动到己方棋子位置"
    
    # 创建新棋子列表，测试敌方棋子不能吃盾
    pieces = [
        Ju("red", 0, 0),  # 红车
        Dun("black", 0, 2),  # 黑盾
        King("black", 2, 0),  # 黑将
    ]
    
    result = GameRules.is_valid_move(pieces, pieces[0], 0, 0, 0, 2)
    assert not result, "错误：任何棋子都不能吃盾"
    print("✓ 盾不可被吃的功能正常")


def test_shield_vs_jia_capture():
    """测试盾免疫甲/胄吃子的功能"""
    print("\n测试2: 盾免疫甲/胄吃子的功能")

    # 创建一个三子连线，其中包含盾，测试甲/胄不能吃子
    pieces = [
        Jia("red", 0, 0),  # 红甲
        Dun("red", 0, 1),  # 红盾
        Pawn("black", 0, 2),  # 黑兵
        King("black", 2, 0)  # 黑将
    ]

    # 查找甲/胄的吃子移动
    captures = GameRules.find_jia_capture_moves(pieces, pieces[0])

    # 应该没有吃子，因为连线中有盾
    assert len(captures) == 0, "错误：甲/胄不应能吃子，因为连线中有盾"
    print("✓ 盾阻止甲/胄吃子的功能正常")


def test_shield_vs_ci_exchange():
    """测试盾免疫刺兑子的功能"""
    print("\n测试3: 盾免疫刺兑子的功能")

    # 测试当刺移动时，如果起始位置的反方向有盾，则不能兑子
    pieces = [
        Dun("black", 0, 1),  # 黑盾（在刺起始位置的反方向）
        Ci("red", 1, 1),     # 红刺
        King("black", 2, 0)  # 黑将
    ]

    # 刺从(1,1)移动到(2,1)，起始位置(1,1)的反方向是(0,1)，那里有盾，应该不允许移动
    result = GameRules.is_valid_move(pieces, pieces[1], 1, 1, 2, 1)
    assert not result, "错误：刺不能与盾兑子"
    print("✓ 刺不能与盾兑子的功能正常")


def test_shield_affecting_ci_nearby():
    """测试刺与敌方盾8邻域相邻时无法触发拖吃"""
    print("\n测试4: 刺与敌方盾8邻域相邻时无法触发拖吃")

    # 测试刺与敌方盾8邻域相邻时的移动限制
    # 刺在(1,1)，敌方盾在(1,2) - 这两个位置是相邻的（8邻域）
    pieces = [
        Ci("red", 1, 1),      # 红刺
        Dun("black", 1, 2),   # 黑盾（与刺8邻域相邻）
        King("black", 3, 3)   # 黑将
    ]

    # 刺从(1,1)移动到(2,1)，此时刺的起始位置(1,1)的反方向是(0,1)，那里没有敌方棋子
    # 所以不是兑子移动，应该允许（只要路径上没有阻挡）
    result = GameRules.is_valid_move(pieces, pieces[0], 1, 1, 2, 1)
    assert result, "当刺不触发兑子条件时，基本移动应该有效"
    
    # 现在测试当刺试图移动使得其起始位置的反方向有敌方棋子（兑子），但刺与敌方盾相邻时
    # 刺在(1,1)，敌方盾在(1,2)，现在添加一个敌方棋子在(0,1)作为反方向棋子
    pieces2 = [
        Pawn("black", 0, 1),  # 敌方棋子（反方向棋子，可能触发兑子）
        Ci("red", 1, 1),      # 红刺
        Dun("black", 1, 2),   # 敌方盾（与刺8邻域相邻）
        King("black", 3, 3)   # 黑将
    ]
    
    # 刺从(1,1)移动到(2,1)，起始位置(1,1)的反方向是(0,1)，那里有敌方棋子
    # 但因为刺与敌方盾(1,2)在8邻域相邻，根据规则不能触发兑子，所以移动应该被拒绝
    result = GameRules.is_valid_move(pieces2, pieces2[1], 1, 1, 2, 1)
    assert not result, "错误：当刺与敌方盾8邻域相邻时，不能触发兑子"
    
    # 验证刺与敌方盾相邻时的正常移动（不触发兑子的情况下）
    # 刺在(1,1)，敌方盾在(1,2)，刺移动到(0,1)（向上移动）
    result = GameRules.is_valid_move(pieces, pieces[0], 1, 1, 0, 1)
    assert result, "当刺与敌方盾相邻但不触发兑子时，基本移动应该有效"
    
    print("✓ 刺与敌方盾相邻时无法触发兑子的功能正常")


def test_jia_vs_shield_connection():
    """测试盾阻止甲/胄连线吃子的功能"""
    print("\n测试5: 盾阻止甲/胄连线吃子的功能")

    # 测试水平连线：甲 - 盾 - 敌子
    pieces = [
        Jia("red", 0, 0),    # 红甲
        Dun("red", 0, 1),    # 红盾
        Pawn("black", 0, 2), # 黑兵
        King("black", 2, 0)  # 黑将
    ]
    
    captures = GameRules.find_jia_capture_moves(pieces, pieces[0])
    assert len(captures) == 0, "错误：甲/胄连线中有盾时不应能吃子"
    
    # 测试垂直连线：甲
    #     盾
    #     敌子
    pieces2 = [
        Jia("red", 0, 0),    # 红甲
        Dun("red", 1, 0),    # 红盾
        Pawn("black", 2, 0), # 黑兵
        King("black", 5, 5)  # 黑将
    ]
    
    captures = GameRules.find_jia_capture_moves(pieces2, pieces2[0])
    assert len(captures) == 0, "错误：甲/胄垂直连线中有盾时不应能吃子"
    
    # 测试对角线连线
    pieces3 = [
        Jia("red", 0, 0),    # 红甲
        Dun("red", 1, 1),    # 红盾
        Pawn("black", 2, 2), # 黑兵
        King("black", 5, 5)  # 黑将
    ]
    
    captures = GameRules.find_jia_capture_moves(pieces3, pieces3[0])
    assert len(captures) == 0, "错误：甲/胄对角线连线中有盾时不应能吃子"
    
    print("✓ 盾阻止甲/胄各种连线吃子的功能正常")


def run_all_tests():
    """运行所有测试"""
    print("开始测试盾棋子的保护机制...")
    
    try:
        test_shield_immunity_to_capture()
        test_shield_vs_jia_capture()
        test_shield_vs_ci_exchange()
        test_shield_affecting_ci_nearby()
        test_jia_vs_shield_connection()
        
        print("\n✅ 所有测试通过！盾的保护机制实现正确。")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 测试过程中出现异常: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = run_all_tests()
    if not success:
        sys.exit(1)