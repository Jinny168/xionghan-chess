"""最终测试檑/礌削弱功能"""

from program.core.chess_pieces import *
from program.core.game_rules import GameRules

def final_test():
    """最终测试"""
    print("=== 最终测试檑/礌削弱功能 ===")
    
    # 测试：真正孤立的棋子（周围8格都没有棋子）
    print("\n1. 测试完全孤立的棋子:")
    pieces1 = [
        Lei("red", 5, 5),  # 我方檑，位置(5,5)
        Pawn("black", 2, 2),  # 敌方棋子，位置(2,2)，与檑距离较远
    ]
    
    target = pieces1[1]  # 黑卒
    lei = pieces1[0]     # 红檑
    
    print(f"   檬位置: ({lei.row}, {lei.col})")
    print(f"   黑卒位置: ({target.row}, {target.col})")
    
    # 检查黑卒周围是否有棋子
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    print("   检查黑卒周围8格:")
    for dr, dc in directions:
        adj_row, adj_col = target.row + dr, target.col + dc
        adj_piece = GameRules.get_piece_at(pieces1, adj_row, adj_col)
        print(f"     ({adj_row}, {adj_col}): {'无棋子' if adj_piece is None else f'{adj_piece.name}'}")
    
    is_iso = GameRules.is_isolated(target, pieces1)
    can_att = GameRules.can_lei_attack(lei, target, pieces1)
    print(f"   是否孤立: {is_iso}")
    print(f"   能否攻击: {can_att}")
    print(f"   预期: 孤立=True (周围无棋子), 攻击=False (距离太远)")
    
    # 测试：棋子旁边有我方檑（应该算孤立）
    print("\n2. 测试旁边有我方檑的棋子:")
    pieces2 = [
        Lei("red", 5, 5),  # 我方檑，位置(5,5)
        Lei("red", 5, 4),  # 我方檑，位置(5,4)，与目标相邻
        Pawn("black", 4, 4),  # 敌方棋子，位置(4,4)
    ]
    
    target2 = pieces2[2]  # 黑卒
    lei2 = pieces2[0]     # 主攻击檑
    
    print(f"   主檑位置: ({lei2.row}, {lei2.col})")
    print(f"   黑卒位置: ({target2.row}, {target2.col})")
    print(f"   黑卒旁边有我方檑: 位置({pieces2[1].row}, {pieces2[1].col})")
    
    # 检查黑卒周围是否有非我方檑的棋子
    print("   检查黑卒周围8格:")
    for dr, dc in directions:
        adj_row, adj_col = target2.row + dr, target2.col + dc
        adj_piece = GameRules.get_piece_at(pieces2, adj_row, adj_col)
        if adj_piece:
            is_my_lei = isinstance(adj_piece, Lei) and adj_piece.color == target2.color
            print(f"     ({adj_row}, {adj_col}): {adj_piece.name} ({'我方檑' if is_my_lei else '其他'})")
        else:
            print(f"     ({adj_row}, {adj_col}): 无棋子")
    
    is_iso2 = GameRules.is_isolated(target2, pieces2)
    can_att2 = GameRules.can_lei_attack(lei2, target2, pieces2)
    print(f"   是否孤立: {is_iso2}")
    print(f"   能否攻击: {can_att2}")
    print(f"   预期: 孤立=True (只有我方檑相邻), 攻击=True (在范围内且孤立)")
    
    # 测试：棋子旁边有敌方檑或其他棋子（不应该算孤立）
    print("\n3. 测试旁边有敌方檑的棋子:")
    pieces3 = [
        Lei("red", 5, 5),  # 我方檑，位置(5,5)
        Lei("black", 4, 5),  # 敌方檑，位置(4,5)，与目标相邻
        Pawn("black", 4, 4),  # 敌方棋子，位置(4,4)
    ]
    
    target3 = pieces3[2]  # 黑卒
    lei3 = pieces3[0]     # 主攻击檑
    
    print(f"   主檑位置: ({lei3.row}, {lei3.col})")
    print(f"   黑卒位置: ({target3.row}, {target3.col})")
    print(f"   黑卒旁边有敌方檑: 位置({pieces3[1].row}, {pieces3[1].col})")
    
    is_iso3 = GameRules.is_isolated(target3, pieces3)
    can_att3 = GameRules.can_lei_attack(lei3, target3, pieces3)
    print(f"   是否孤立: {is_iso3}")
    print(f"   能否攻击: {can_att3}")
    print(f"   预期: 孤立=False (敌方檑相邻), 攻击=False (不是孤立)")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    final_test()