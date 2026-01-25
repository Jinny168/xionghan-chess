"""调试is_isolated函数"""

from program.core.chess_pieces import *
from program.core.game_rules import GameRules

def debug_isolated():
    """调试落单判断函数"""
    print("调试is_isolated函数...")
    
    # 创建一个完全孤立的敌方棋子
    pieces = [
        Lei("red", 5, 5),  # 我方檑
        Pawn("black", 4, 4),  # 敌方棋子，完全孤立
    ]
    
    target_piece = pieces[1]  # 黑卒
    print(f"目标棋子: {target_piece.name} at ({target_piece.row}, {target_piece.col}), color: {target_piece.color}")
    
    # 检查周围8个方向是否有棋子
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    print("检查周围8个方向:")
    for i, (dr, dc) in enumerate(directions):
        adjacent_row, adjacent_col = target_piece.row + dr, target_piece.col + dc
        print(f"  方向{i+1}: ({dr}, {dc}) -> 位置({adjacent_row}, {adjacent_col})", end="")
        
        if 0 <= adjacent_row < 13 and 0 <= adjacent_col < 13:
            adjacent_piece = GameRules.get_piece_at(pieces, adjacent_row, adjacent_col)
            if adjacent_piece:
                print(f" -> 有棋子: {adjacent_piece.name} ({adjacent_piece.color}, is_Lei={isinstance(adjacent_piece, Lei)})", end="")
                # 检查是否是我方檑
                is_my_lei = isinstance(adjacent_piece, Lei) and adjacent_piece.color == target_piece.color
                print(f", is_my_lei={is_my_lei}")
            else:
                print(" -> 无棋子")
        else:
            print(" -> 超出棋盘边界")
    
    # 调用is_isolated函数
    result = GameRules.is_isolated(target_piece, pieces)
    print(f"\nis_isolated结果: {result}")
    
    # 檧能否攻击这个棋子？
    lei_piece = pieces[0]  # 红檑
    attack_result = GameRules.can_lei_attack(lei_piece, target_piece, pieces)
    print(f"can_lei_attack结果: {attack_result}")
    
    # 检查距离
    row_diff = abs(lei_piece.row - target_piece.row)
    col_diff = abs(lei_piece.col - target_piece.col)
    print(f"距离检查 - 行差: {row_diff}, 列差: {col_diff}")
    in_range = row_diff <= 1 and col_diff <= 1 and (row_diff != 0 or col_diff != 0)
    print(f"在攻击范围内: {in_range}")

if __name__ == "__main__":
    debug_isolated()