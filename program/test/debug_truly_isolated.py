"""测试真正孤立的棋子"""

from program.core.chess_pieces import *
from program.core.game_rules import GameRules

def test_truly_isolated():
    """测试真正孤立的棋子"""
    print("测试真正孤立的棋子...")
    
    # 创建一个真正孤立的棋子（周围没有任何棋子）
    pieces = [
        Lei("red", 5, 5),  # 我方檑
        Pawn("black", 2, 2),  # 敌方棋子，完全孤立（与檑距离较远）
    ]
    
    target_piece = pieces[1]  # 黑卒，位置(2,2)
    lei_piece = pieces[0]     # 红檑，位置(5,5)
    
    print(f"檑位置: ({lei_piece.row}, {lei_piece.col})")
    print(f"目标棋子位置: ({target_piece.row}, {target_piece.col})")
    
    # 检查目标棋子周围8个方向是否有棋子
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    print("检查目标棋子周围8个方向:")
    for i, (dr, dc) in enumerate(directions):
        adjacent_row, adjacent_col = target_piece.row + dr, target_piece.col + dc
        print(f"  方向{i+1}: ({dr}, {dc}) -> 位置({adjacent_row}, {adjacent_col})", end="")
        
        if 0 <= adjacent_row < 13 and 0 <= adjacent_col < 13:
            adjacent_piece = GameRules.get_piece_at(pieces, adjacent_row, adjacent_col)
            if adjacent_piece:
                print(f" -> 有棋子: {adjacent_piece.name}")
            else:
                print(" -> 无棋子")
        else:
            print(" -> 超出棋盘边界")
    
    # 检查距离（檑是否在攻击范围内）
    row_diff = abs(lei_piece.row - target_piece.row)
    col_diff = abs(lei_piece.col - target_piece.col)
    print(f"\n距离检查 - 行差: {row_diff}, 列差: {col_diff}")
    in_range = row_diff <= 1 and col_diff <= 1 and (row_diff != 0 or col_diff != 0)
    print(f"在檑的攻击范围内: {in_range}")
    
    # 调用is_isolated函数
    result = GameRules.is_isolated(target_piece, pieces)
    print(f"\nis_isolated结果: {result}")
    
    # 檧能否攻击这个棋子？
    attack_result = GameRules.can_lei_attack(lei_piece, target_piece, pieces)
    print(f"can_lei_attack结果: {attack_result}")
    
    print(f"\n预期结果:")
    print(f"- 黑卒应该孤立: True (因为它周围没有任何棋子)")
    print(f"- 檬能攻击黑卒: False (因为距离太远，不在攻击范围内)")

def test_isolated_with_my_lei():
    """测试旁边有我方檑的棋子"""
    print("\n" + "="*50)
    print("测试旁边有我方檑的棋子...")
    
    # 黑棋旁边有黑檑（我方檑）
    pieces = [
        Lei("black", 4, 4),  # 黑方檑（我方）
        Pawn("black", 4, 5),  # 黑方棋子，旁边有我方檑
        Lei("red", 5, 5),    # 敌方檑
    ]
    
    target_piece = pieces[1]  # 黑卒，位置(4,5)
    lei_piece = pieces[2]     # 红檑，位置(5,5)，用来攻击
    
    print(f"红檑位置: ({lei_piece.row}, {lei_piece.col})")
    print(f"目标棋子位置: ({target_piece.row}, {target_piece.col})")
    print(f"目标棋子旁边有我方檑: 位置({pieces[0].row}, {pieces[0].col})")
    
    # 检查目标棋子周围8个方向是否有棋子（除了我方檑）
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    print("检查目标棋子周围8个方向:")
    for i, (dr, dc) in enumerate(directions):
        adjacent_row, adjacent_col = target_piece.row + dr, target_piece.col + dc
        print(f"  方向{i+1}: ({dr}, {dc}) -> 位置({adjacent_row}, {adjacent_col})", end="")
        
        if 0 <= adjacent_row < 13 and 0 <= adjacent_col < 13:
            adjacent_piece = GameRules.get_piece_at(pieces, adjacent_row, adjacent_col)
            if adjacent_piece:
                is_my_lei = isinstance(adjacent_piece, Lei) and adjacent_piece.color == target_piece.color
                print(f" -> 有棋子: {adjacent_piece.name} ({'我方檑' if is_my_lei else '其他'})")
            else:
                print(" -> 无棋子")
        else:
            print(" -> 超出棋盘边界")
    
    # 检查距离（檑是否在攻击范围内）
    row_diff = abs(lei_piece.row - target_piece.row)
    col_diff = abs(lei_piece.col - target_piece.col)
    print(f"\n距离检查 - 行差: {row_diff}, 列差: {col_diff}")
    in_range = row_diff <= 1 and col_diff <= 1 and (row_diff != 0 or col_diff != 0)
    print(f"在檑的攻击范围内: {in_range}")
    
    # 调用is_isolated函数
    result = GameRules.is_isolated(target_piece, pieces)
    print(f"\nis_isolated结果: {result}")
    
    # 檧能否攻击这个棋子？
    attack_result = GameRules.can_lei_attack(lei_piece, target_piece, pieces)
    print(f"can_lei_attack结果: {attack_result}")
    
    print(f"\n预期结果:")
    print(f"- 黑卒应该孤立: True (因为它旁边虽然有棋子，但只有我方檑，不算数)")
    print(f"- 檬能攻击黑卒: True (在攻击范围内且孤立)")

if __name__ == "__main__":
    test_truly_isolated()
    test_isolated_with_my_lei()