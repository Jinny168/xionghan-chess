"""测试射棋子的斜向夹逼区域阻挡功能"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from program.core.game_rules import GameRules
from program.core.chess_pieces import She, Pawn, Ju, Ma


def test_she_pinch_block():
    """测试射棋子的夹逼阻挡功能"""
    print("开始测试射棋子的夹逼阻挡功能...")
    
    # 创建棋盘和棋子
    pieces = []
    
    # 在(0,0)放置一个射
    she = She("red", 0, 0)
    pieces.append(she)
    
    # 在(1,2)和(2,1)放置两个棋子形成夹逼
    pawn1 = Pawn("black", 1, 2)
    pawn2 = Pawn("black", 2, 1)
    pieces.append(pawn1)
    pieces.append(pawn2)
    
    # 测试射从(0,0)到(1,1)的移动（应该允许，因为夹逼点在更远的位置）
    result = GameRules.is_valid_she_move(pieces, 0, 0, 1, 1)
    print(f"射从(0,0)到(1,1)的移动是否合法: {result}")
    
    # 测试射从(0,0)到(2,2)的移动（应该被阻挡，因为经过(1,1)后，(1,2)和(2,1)形成夹逼）
    result = GameRules.is_valid_she_move(pieces, 0, 0, 2, 2)
    print(f"射从(0,0)到(2,2)的移动是否合法: {result}")
    
    # 测试射从(0,0)到(3,3)的移动（应该被阻挡）
    result = GameRules.is_valid_she_move(pieces, 0, 0, 3, 3)
    print(f"射从(0,0)到(3,3)的移动是否合法: {result}")
    
    # 再添加一个测试场景：在不同方向上测试夹逼
    pieces2 = []
    she2 = She("red", 5, 5)
    pieces2.append(she2)
    
    # 在(4,6)和(6,4)放置两个棋子，对射从(5,5)向(5,5)方向移动形成夹逼
    pawn3 = Pawn("black", 4, 6)
    pawn4 = Pawn("black", 6, 4)
    pieces2.append(pawn3)
    pieces2.append(pawn4)
    
    # 测试射从(5,5)到(6,6)的移动（应该被阻挡）
    result = GameRules.is_valid_she_move(pieces2, 5, 5, 6, 6)
    print(f"射从(5,5)到(6,6)的移动是否合法: {result}")
    
    # 测试射从(5,5)到(4,4)的移动（应该被阻挡）
    result = GameRules.is_valid_she_move(pieces2, 5, 5, 4, 4)
    print(f"射从(5,5)到(4,4)的移动是否合法: {result}")
    
    # 测试非夹逼情况
    pieces3 = []
    she3 = She("red", 0, 0)
    pieces3.append(she3)
    
    # 只在(1,2)放一个棋子，没有形成夹逼
    pawn5 = Pawn("black", 1, 2)
    pieces3.append(pawn5)
    
    # 测试射从(0,0)到(3,3)的移动（应该允许，因为没有形成夹逼）
    result = GameRules.is_valid_she_move(pieces3, 0, 0, 3, 3)
    print(f"射从(0,0)到(3,3)的移动（无夹逼）是否合法: {result}")
    
    print("测试完成！")


if __name__ == "__main__":
    test_she_pinch_block()