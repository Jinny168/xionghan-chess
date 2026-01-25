"""验证檑/礌新规则逻辑"""

from program.core.chess_pieces import *
from program.core.game_rules import GameRules

def verify_logic():
    """验证新规则逻辑"""
    print("=== 验证檑/礌新规则逻辑 ===")
    
    # 情况1：目标棋子周围只有攻击的檑，应该能被攻击
    print("\n情况1: 目标棋子周围只有发起攻击的檑")
    pieces1 = [
        Lei("red", 5, 5),  # 攻击的檑
        Pawn("black", 4, 4),  # 目标棋子
    ]
    
    # 检查目标棋子周围
    target = pieces1[1]  # 黑卒
    attacker = pieces1[0]  # 红檑
    
    print(f"   攻击檑位置: ({attacker.row}, {attacker.col})")
    print(f"   目标棋子位置: ({target.row}, {target.col})")
    
    # 检查黑卒周围是否有其他棋子（除了发起攻击的檑）
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    print("   检查黑卒周围8个位置:")
    for dr, dc in directions:
        adj_row, adj_col = target.row + dr, target.col + dc
        adj_piece = GameRules.get_piece_at(pieces1, adj_row, adj_col)
        if adj_piece:
            is_attacker = (adj_piece == attacker)
            print(f"     ({adj_row}, {adj_col}): {adj_piece.name} ({'攻击者' if is_attacker else '其他'})")
        else:
            print(f"     ({adj_row}, {adj_col}): 无棋子")
    
    can_attack = GameRules.can_lei_attack(attacker, target, pieces1)
    print(f"   能否攻击: {can_attack}")
    print(f"   预期: True (目标周围只有攻击者)")
    
    # 情况2：目标棋子周围有其他棋子，不应该被攻击
    print("\n情况2: 目标棋子周围有其他棋子")
    pieces2 = [
        Lei("red", 5, 5),  # 攻击的檑
        Pawn("black", 4, 4),  # 目标棋子
        Pawn("red", 4, 5),   # 其他棋子
    ]
    
    target2 = pieces2[1]  # 黑卒
    attacker2 = pieces2[0]  # 红檑
    
    print(f"   攻击檑位置: ({attacker2.row}, {attacker2.col})")
    print(f"   目标棋子位置: ({target2.row}, {target2.col})")
    print(f"   目标棋子旁边有其他棋子: 红兵在({pieces2[2].row}, {pieces2[2].col})")
    
    can_attack2 = GameRules.can_lei_attack(attacker2, target2, pieces2)
    print(f"   能否攻击: {can_attack2}")
    print(f"   预期: False (目标周围有其他棋子)")
    
    # 情况3：目标棋子周围有其他檑，不应该被攻击
    print("\n情况3: 目标棋子周围有其他檑")
    pieces3 = [
        Lei("red", 5, 5),  # 攻击的檑
        Pawn("black", 4, 4),  # 目标棋子
        Lei("black", 4, 5),   # 其他檑
    ]
    
    target3 = pieces3[1]  # 黑卒
    attacker3 = pieces3[0]  # 红檑
    
    print(f"   攻击檑位置: ({attacker3.row}, {attacker3.col})")
    print(f"   目标棋子位置: ({target3.row}, {target3.col})")
    print(f"   目标棋子旁边有其他檑: 黑檑在({pieces3[2].row}, {pieces3[2].col})")
    
    can_attack3 = GameRules.can_lei_attack(attacker3, target3, pieces3)
    print(f"   能否攻击: {can_attack3}")
    print(f"   预期: False (目标周围有其他檑)")
    
    print("\n=== 验证完成 ===")

if __name__ == "__main__":
    verify_logic()