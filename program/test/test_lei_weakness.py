"""测试檑/礌削弱功能：扩大落单判定范围"""

from program.core.chess_pieces import *
from program.core.game_rules import GameRules

def test_old_vs_new_logic():
    """对比旧逻辑和新逻辑的差异"""
    print("=== 对比旧逻辑和新逻辑 ===")
    
    # 场景：一个敌方棋子旁边有己方非檑棋子
    pieces = [
        Lei("red", 5, 5),  # 我方檑
        Pawn("black", 4, 4),  # 敌方棋子
        Pawn("red", 4, 5),  # 己方棋子与敌方棋子相邻
    ]
    
    target_piece = pieces[1]  # 黑卒
    lei_piece = pieces[0]     # 红檑
    
    print(f"场景：黑卒(4,4)旁边有红兵(4,5)")
    
    # 根据新逻辑：黑卒旁边有红兵，不是孤立的
    is_isolated_new = GameRules.is_isolated(target_piece, pieces)
    can_attack_new = GameRules.can_lei_attack(lei_piece, target_piece, pieces)
    print(f"新逻辑 - 是否孤立: {is_isolated_new}, 能否攻击: {can_attack_new}")
    
    # 模拟旧逻辑：只检查同色棋子
    def old_is_isolated(piece, pieces):
        """旧的孤立判断逻辑：只检查周围是否有同色棋子"""
        if not piece:
            return False
        
        # 检查四个方向：上、下、左、右
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        row, col = piece.row, piece.col
        
        # 检查每个方向是否有同色棋子
        for dr, dc in directions:
            adjacent_row, adjacent_col = row + dr, col + dc
            
            # 检查相邻位置是否在棋盘范围内
            if 0 <= adjacent_row < 13 and 0 <= adjacent_col < 13:
                adjacent_piece = GameRules.get_piece_at(pieces, adjacent_row, adjacent_col)
                # 如果相邻位置有棋子且颜色相同，则目标棋子不是孤立的
                if adjacent_piece and adjacent_piece.color == piece.color:
                    return False  # 发现相邻的同色棋子，不是孤立的
        
        # 四个方向都没有同色棋子，说明是孤立的
        return True
    
    is_isolated_old = old_is_isolated(target_piece, pieces)
    # 旧逻辑下的攻击判断
    can_attack_old = is_isolated_old and (
        abs(lei_piece.row - target_piece.row) <= 1 and 
        abs(lei_piece.col - target_piece.col) <= 1 and 
        (lei_piece.row != target_piece.row or lei_piece.col != target_piece.col)
    )
    print(f"旧逻辑 - 是否孤立: {is_isolated_old}, 能否攻击: {can_attack_old}")
    
    print(f"结论：新逻辑限制了檑的能力，以前能攻击的情况现在不能攻击了")


def test_lei_weakness():
    """测试檑/礌的落单判定修改"""
    print("\n=== 测试檑/礌削弱功能 ===")
    
    # 测试1：原来不落单的棋子，现在应该仍然不落单
    print("\n测试1: 敌方棋子与己方非檑棋子相邻，不应被檑吃掉")
    pieces = [
        Lei("red", 5, 5),  # 我方檑
        Pawn("black", 4, 4),  # 敌方棋子
        Pawn("red", 4, 5),  # 己方棋子与敌方棋子相邻
    ]
    
    is_isolated = GameRules.is_isolated(pieces[1], pieces)  # 检查黑卒
    can_attack = GameRules.can_lei_attack(pieces[0], pieces[1], pieces)  # 檙能否攻击黑卒
    print(f"黑卒是否孤立: {is_isolated}")
    print(f"檑能否攻击黑卒: {can_attack}")
    print(f"预期结果: 黑卒不应被檑吃掉 (孤立=False, 攻击=False)")
    
    # 测试2：敌方棋子与敌方棋子相邻，不应被檑吃掉
    print("\n测试2: 敌方棋子与敌方棋子相邻，不应被檑吃掉")
    pieces2 = [
        Lei("red", 5, 5),  # 我方檑
        Pawn("black", 4, 4),  # 敌方棋子1
        Pawn("black", 4, 5),  # 敌方棋子2 与棋子1相邻
    ]
    
    is_isolated2 = GameRules.is_isolated(pieces2[1], pieces2)  # 检查黑卒
    can_attack2 = GameRules.can_lei_attack(pieces2[0], pieces2[1], pieces2)  # 檑能否攻击黑卒
    print(f"黑卒是否孤立: {is_isolated2}")
    print(f"檑能否攻击黑卒: {can_attack2}")
    print(f"预期结果: 黑卒不应被檑吃掉 (孤立=False, 攻击=False)")
    
    # 测试3：敌方棋子与敌方檑相邻，不应被檑吃掉
    print("\n测试3: 敌方棋子与敌方檑相邻，不应被檑吃掉")
    pieces3 = [
        Lei("red", 5, 5),  # 我方檑
        Pawn("black", 4, 4),  # 敌方棋子
        Lei("black", 4, 5),  # 敌方檑与敌方棋子相邻
    ]
    
    is_isolated3 = GameRules.is_isolated(pieces3[1], pieces3)  # 检查黑卒
    can_attack3 = GameRules.can_lei_attack(pieces3[0], pieces3[1], pieces3)  # 檑能否攻击黑卒
    print(f"黑卒是否孤立: {is_isolated3}")
    print(f"檑能否攻击黑卒: {can_attack3}")
    print(f"预期结果: 黑卒不应被檑吃掉 (孤立=False, 攻击=False)")
    
    # 测试4：完全孤立的敌方棋子，应该能被檑吃掉
    print("\n测试4: 完全孤立的敌方棋子，应该能被檑吃掉")
    pieces4 = [
        Lei("red", 5, 5),  # 我方檑
        Pawn("black", 2, 2),  # 敌方棋子，完全孤立（与檑距离较远）
    ]
    
    is_isolated4 = GameRules.is_isolated(pieces4[1], pieces4)  # 检查黑卒
    can_attack4 = GameRules.can_lei_attack(pieces4[0], pieces4[1], pieces4)  # 檑能否攻击黑卒
    print(f"黑卒是否孤立: {is_isolated4}")
    print(f"檑能否攻击黑卒: {can_attack4}")
    print(f"预期结果: 黑卒不能被檑吃掉 (孤立=True, 攻击=False) 因为距离太远")
    
    # 测试5：敌方棋子旁边只有同色的檑，应该能被檑吃掉
    print("\n测试5: 敌方棋子旁边只有同色的檑，应该能被檑吃掉")
    pieces5 = [
        Lei("red", 2, 5),  # 我方檑（攻击者，距离较远）
        Lei("black", 4, 5),  # 黑方檑（与目标同色，即目标自己的檑）
        Pawn("black", 4, 4),  # 敌方棋子（实际是黑方棋子）
    ]
    
    is_isolated5 = GameRules.is_isolated(pieces5[2], pieces5)  # 检查黑卒
    can_attack5 = GameRules.can_lei_attack(pieces5[0], pieces5[2], pieces5)  # 红檑能否攻击黑卒
    print(f"黑卒是否孤立: {is_isolated5}")
    print(f"檑能否攻击黑卒: {can_attack5}")
    print(f"预期结果: 黑卒应该被檑吃掉 (孤立=True, 攻击=False) 因为旁边只有同色的檑，但距离攻击者太远")


if __name__ == "__main__":
    test_old_vs_new_logic()
    test_lei_weakness()