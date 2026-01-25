"""综合测试射棋子的斜向夹逼区域阻挡功能"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from program.core.game_rules import GameRules
from program.core.chess_pieces import She, Pawn, Ju, Ma


def test_comprehensive_she_pinch():
    """综合测试射棋子的夹逼阻挡功能"""
    print("开始综合测试射棋子的夹逼阻挡功能...")
    
    # 测试案例1：原始示例 - 射在(0,0)，夹逼点在(1,2)和(2,1)
    print("\n测试案例1：射在(0,0)，夹逼点在(1,2)和(2,1)")
    pieces = []
    she = She("red", 0, 0)
    pieces.append(she)
    pawn1 = Pawn("black", 1, 2)
    pawn2 = Pawn("black", 2, 1)
    pieces.append(pawn1)
    pieces.append(pawn2)
    
    # 射只能移动到(1,1)，不能移动到(2,2)及更远
    result1 = GameRules.is_valid_she_move(pieces, 0, 0, 1, 1)
    result2 = GameRules.is_valid_she_move(pieces, 0, 0, 2, 2)
    result3 = GameRules.is_valid_she_move(pieces, 0, 0, 3, 3)
    print(f"  射从(0,0)到(1,1)的移动: {result1} (应为True)")
    print(f"  射从(0,0)到(2,2)的移动: {result2} (应为False)")
    print(f"  射从(0,0)到(3,3)的移动: {result3} (应为False)")
    
    # 测试案例2：不同方向的移动 - 射在(5,5)到(3,3)，夹逼点在(4,2)和(2,4)
    print("\n测试案例2：射在(5,5)往(-1,-1)方向移动，夹逼点在(4,2)和(2,4)")
    pieces2 = []
    she2 = She("red", 5, 5)
    pieces2.append(she2)
    pawn3 = Pawn("black", 4, 2)
    pawn4 = Pawn("black", 2, 4)
    pieces2.append(pawn3)
    pieces2.append(pawn4)
    
    result4 = GameRules.is_valid_she_move(pieces2, 5, 5, 4, 4)
    result5 = GameRules.is_valid_she_move(pieces2, 5, 5, 3, 3)
    result6 = GameRules.is_valid_she_move(pieces2, 5, 5, 2, 2)
    print(f"  射从(5,5)到(4,4)的移动: {result4} (应为False，因为(4,2)和(2,4)形成夹逼)")
    print(f"  射从(5,5)到(3,3)的移动: {result5} (应为False)")
    print(f"  射从(5,5)到(2,2)的移动: {result6} (应为False)")
    
    # 实际上，(4,4)相对于(5,5)的方向是(-1,-1)，夹逼点应该是(4+0,4+(-1))=(4,3)和(4+(-1),4+0)=(3,4)
    # 让我们修正测试案例2
    print("\n测试案例2修正：射在(5,5)往(-1,-1)方向移动")
    pieces2_correct = []
    she2_correct = She("red", 5, 5)
    pieces2_correct.append(she2_correct)
    # 夹逼(4,4)的点应该是(4,4)+(0,-1)=(4,3)和(4,4)+(-1,0)=(3,4)
    pawn5 = Pawn("black", 4, 3)
    pawn6 = Pawn("black", 3, 4)
    pieces2_correct.append(pawn5)
    pieces2_correct.append(pawn6)
    
    result4_correct = GameRules.is_valid_she_move(pieces2_correct, 5, 5, 4, 4)
    result5_correct = GameRules.is_valid_she_move(pieces2_correct, 5, 5, 3, 3)
    print(f"  射从(5,5)到(4,4)的移动: {result4_correct} (应为False，因为(4,3)和(3,4)形成夹逼)")
    print(f"  射从(5,5)到(3,3)的移动: {result5_correct} (应为False)")
    
    # 测试案例3：射在(0,12)往(1,-1)方向移动，夹逼点在(1,11)和(2,10)
    print("\n测试案例3：射在(0,12)往(1,-1)方向移动，夹逼点在(1,11)和(2,10)")
    pieces3 = []
    she3 = She("red", 0, 12)
    pieces3.append(she3)
    pawn7 = Pawn("black", 1, 11)  # (0,12)到(1,11)方向是(1,-1)，夹逼点之一
    pawn8 = Pawn("black", 2, 10)  # (0,12)到(2,10)方向是(2,-2)，但(1,11)的夹逼点之一
    pieces3.append(pawn7)
    pieces3.append(pawn8)
    
    # 对于射从(0,12)移动到(1,11)，路径上没有中间点，所以不会触发夹逼
    # 但对于射从(0,12)移动到(2,10)，路径经过(1,11)，夹逼点应该是(1,11)+(0,1)=(1,12)和(1,11)+(1,0)=(2,11)
    # 实际夹逼点是(1,10)和(2,11)？让我重新分析
    # 射从(0,12)到(2,10)，step_row=1, step_col=-1
    # 路径点(1,11)，i=1
    # 夹逼点：(1+0,11+1)=(1,12) 和 (1+(-1),11+0)=(0,11)
    # 但我们需要的夹逼点是(1,11)+(1,0)=(2,11) 和 (1,11)+(0,-1)=(1,10)
    
    # 根据公式，对于移动方向(1,-1)，夹逼点应该是：
    # (check_row + 0, check_col + 1) 和 (check_row - 1, check_col + 0)
    # 即 (check_row, check_col + 1) 和 (check_row - 1, check_col)
    pieces3_correct = []
    she3_correct = She("red", 0, 12)
    pieces3_correct.append(she3_correct)
    # 对于路径点(1,11)，夹逼点是(1,11+1)=(1,12)和(1-1,11)=(0,11)
    pawn9 = Pawn("black", 1, 12)
    pawn10 = Pawn("black", 0, 11)
    pieces3_correct.append(pawn9)
    pieces3_correct.append(pawn10)
    
    result7 = GameRules.is_valid_she_move(pieces3_correct, 0, 12, 1, 11)
    result8 = GameRules.is_valid_she_move(pieces3_correct, 0, 12, 2, 10)
    print(f"  射从(0,12)到(1,11)的移动: {result7} (应为False，因为(1,12)和(0,11)形成夹逼)")
    print(f"  射从(0,12)到(2,10)的移动: {result8} (应为False)")
    
    # 测试案例4：无夹逼情况
    print("\n测试案例4：无夹逼情况，射在(6,6)")
    pieces4 = []
    she4 = She("red", 6, 6)
    pieces4.append(she4)
    # 添加一些棋子，但不形成夹逼
    pawn11 = Pawn("black", 7, 8)  # 不构成夹逼
    pawn12 = Pawn("black", 8, 7)  # 不构成夹逼
    pieces4.append(pawn11)
    pieces4.append(pawn12)
    
    result9 = GameRules.is_valid_she_move(pieces4, 6, 6, 9, 9)
    print(f"  射从(6,6)到(9,9)的移动: {result9} (应为True，无夹逼)")
    
    print("\n综合测试完成！")


if __name__ == "__main__":
    test_comprehensive_she_pinch()