"""盾棋子保护机制测试文件"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from program.chess_pieces import *
from program.game_rules import GameRules


def test_shield_immunity_to_capture():
    """测试盾不可被吃的功能"""
    print("测试1: 盾不可被吃的功能")

    # 创建棋子
    pieces = [
        Ju("red", 0, 0),  # 红车
        Dun("red", 0, 2),  # 红盾
        King("black", 2, 0),  # 黑将
        Dun("black", 2, 2)  # 黑盾
    ]

    # 测试红车能否吃掉红盾（同一颜色，应不允许）
    result = GameRules.is_valid_move(pieces, pieces[0], 0, 0, 0, 2)
    assert not result, "错误：己方棋子不能移动到己方棋子位置"

    # 更改盾为黑色，测试红车能否吃掉黑盾
    pieces[1].color = "black"
    pieces[1].row, pieces[1].col = 0, 2  # 确保位置正确

    # 重新创建棋子列表以确保位置正确
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

    # 创建刺和盾的位置，使得刺理论上可以兑子
    pieces = [
        Ci("red", 0, 0),  # 红刺
        Dun("black", 0, 1),  # 黑盾
        King("black", 2, 0)  # 黑将
    ]

    # 测试红刺能否移动到(0,2)，这样在移动前起始位置(0,0)的反方向一格就是(0,-1)，不在棋盘上
    # 我们测试刺能否移动到与盾相邻的位置，触发兑子条件
    result = GameRules.is_valid_move(pieces, pieces[0], 0, 0, 0, 2)

    # 这种情况下，(0,-1)位置没有棋子，因此不会触发兑子
    # 但我们应该测试当刺移动时，如果反方向有盾，则不能兑子
    # 设置一个情况：刺在(1,1)，盾在(0,1)，刺移动到(2,1)
    pieces2 = [
        Ci("red", 1, 1),  # 红刺
        Dun("black", 0, 1),  # 黑盾在刺的反方向
        King("black", 2, 0)  # 黑将
    ]

    # 刺从(1,1)移动到(2,1)，反方向是(0,1)，那里有盾，应该不允许移动
    result = GameRules.is_valid_move(pieces2, pieces2[0], 1, 1, 2, 1)
    assert not result, "错误：刺不能与盾兑子"
    print("✓ 刺不能与盾兑子的功能正常")


def test_shield_affecting_ci_nearby():
    """测试刺与敌方盾8邻域相邻时无法触发拖吃"""
    print("\n测试4: 刺与敌方盾8邻域相邻时无法触发拖吃")

    # 刺与敌方盾相邻的情况
    pieces = [
        Ci("red", 1, 1),  # 红刺
        Dun("black", 1, 2),  # 黑盾（与刺相邻）
        Pawn("black", 2, 1),  # 黑兵，在刺移动方向上
        King("black", 3, 3)  # 黑将
    ]

    # 刺从(1,1)向右移动到(1,3)，路径上经过(1,2)位置，但那里有黑盾
    # 实际上，我们需要测试刺与敌方盾相邻时，不能触发兑子
    # 刺移动到(1,0)或(1,2)或其他位置，但要验证当刺与敌方盾在8邻域时的限制
    result = GameRules.is_valid_move(pieces, pieces[0], 1, 1, 1, 0)  # 向左移动
    # 这应该允许移动，但不触发兑子，因为反方向没有敌子

    # 更精确的测试：刺在(1,1)，敌方盾在(1,2)，刺尝试移动
    # 当刺与敌方盾8邻域相邻时，不能触发拖吃
    result = GameRules.is_valid_move(pieces, pieces[0], 1, 1, 2, 1)  # 向下移动
    # 这个移动应该是有效的，因为它不是与盾相邻的移动
    assert result, "刺的基本移动应该有效"

    # 测试当刺移动到一个位置，使得其起始位置的反方向是敌方盾的情况
    pieces3 = [
        Ci("red", 2, 1),  # 红刺
        Dun("black", 0, 1),  # 黑盾（在刺起始位置反方向）
        King("black", 3, 3)  # 黑将
    ]

    # 刺从(2,1)移动到(3,1)，起始位置(2,1)的反方向是(1,1)，那里没有盾
    # 反方向是基于移动方向的：如果刺从(2,1)移动到(3,1)，移动向量是(1,0)
    # 起始位置的反方向是(2-1, 1-0)=(1,1)
    result = GameRules.is_valid_move(pieces3, pieces3[0], 2, 1, 3, 1)

    # 实际上，我们需要测试的是：如果反方向有盾，移动不应该被允许
    # 根据规则：如果反方向有敌方棋子，且不是盾，则可以移动（触发兑子）
    # 如果反方向是盾，则移动不应该被允许
    pieces4 = [
        Dun("black", 0, 1),  # 黑盾
        Ci("red", 1, 1),  # 红刺
        King("black", 3, 3)  # 黑将
    ]

    # 刺从(1,1)移动到(2,1)，反方向是(0,1)，那里是盾，移动应该被拒绝
    result = GameRules.is_valid_move(pieces4, pieces4[1], 1, 1, 2, 1)
    assert not result, "错误：刺不能与盾兑子"
    print("✓ 刺与敌方盾相邻时无法兑子的功能正常")


def test_jia_vs_shield_connection():
    """测试盾阻止甲/胄连线吃子的功能"""
    print("\n测试5: 盾阻止甲/胄连线吃子的功能")

    # 测试水平连线：甲 - 盾 - 敌子
    pieces = [
        Jia("red", 0, 0),  # 红甲
        Dun("red", 0, 1),  # 红盾
        Pawn("black", 0, 2),  # 黑兵
        King("black", 2, 0)  # 黑将
    ]

    captures = GameRules.find_jia_capture_moves(pieces, pieces[0])
    assert len(captures) == 0, "错误：甲/胄连线中有盾时不应能吃子"

    # 测试垂直连线：甲
    #     盾
    #     敌子
    pieces2 = [
        Jia("red", 0, 0),  # 红甲
        Dun("red", 1, 0),  # 红盾
        Pawn("black", 2, 0),  # 黑兵
        King("black", 5, 5)  # 黑将
    ]

    captures = GameRules.find_jia_capture_moves(pieces2, pieces2[0])
    assert len(captures) == 0, "错误：甲/胄垂直连线中有盾时不应能吃子"

    # 测试对角线连线
    pieces3 = [
        Jia("red", 0, 0),  # 红甲
        Dun("red", 1, 1),  # 红盾
        Pawn("black", 2, 2),  # 黑兵
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